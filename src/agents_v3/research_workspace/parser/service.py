"""PDF 解析与分块核心服务"""

from __future__ import annotations

import os
import re
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import (
    ChunkType,
    Paper,
    PaperChunk,
    PaperStatus,
    ParseResult,
    Reference,
)
from src.agents_v3.research_workspace.parser.adapters import (
    DoclingAdapter,
    ParserAdapter,
    PdfMinerAdapter,
    PdfPlumberAdapter,
    PyMuPDF4LLMAdapter,
    PyMuPDFAdapter,
)
from src.agents_v3.research_workspace.parser.postprocess import (
    ChunkCleaner,
    TextPostProcessor,
    _SECTION_TO_CHUNK_TYPE,
    _SECTION_TYPE_MAP,
)
from src.agents_v3.research_workspace.storage import get_storage


class ParserService:
    """PDF 解析与分块"""

    def __init__(self, storage=None, enable_contextual_retrieval: bool = True):
        self.storage = storage or get_storage()
        self._adapters: list[ParserAdapter] = [
            PyMuPDF4LLMAdapter(),
            PdfPlumberAdapter(),
            PyMuPDFAdapter(),
            PdfMinerAdapter(),
            DoclingAdapter(),
        ]
        self._post_processor = TextPostProcessor()
        self._chunk_cleaner = ChunkCleaner()
        self._enable_contextual = enable_contextual_retrieval

    def download_pdf(self, paper_id: str) -> dict[str, Any]:
        """下载论文 PDF 到本地"""
        import urllib.request

        item = self.storage.get_item("papers", paper_id)
        if not item:
            return {"success": False, "error": "Paper not found"}

        paper = Paper(**item)
        pdf_url = paper.open_access.pdf_url if paper.open_access else ""

        if not pdf_url:
            pool_item = self.storage.get_item("papers_pool", paper_id)
            if pool_item:
                pdf_url = pool_item.get("pdf_url", "")

        if not pdf_url:
            return {"success": False, "error": "No PDF URL"}

        project_id = paper.project_id
        dest_dir = self.storage.data_dir / "files" / project_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{paper_id}.pdf"

        if dest_path.exists():
            self._update_pdf_path(paper_id, str(dest_path))
            self._mark_pool_pdf_downloaded(paper)
            return {"success": True, "pdf_path": str(dest_path), "skipped": True}

        try:
            logger.info(f"Downloading PDF: {pdf_url}")
            headers = {"User-Agent": "PaperAgent/1.0 (research-tool)"}
            req = urllib.request.Request(pdf_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(dest_path, "wb") as f:
                    f.write(resp.read())
            self._update_pdf_path(paper_id, str(dest_path))
            self._mark_pool_pdf_downloaded(paper)
            logger.info(f"Downloaded PDF: {dest_path}")
            return {"success": True, "pdf_path": str(dest_path)}
        except Exception as e:
            logger.error(f"PDF download failed: {e}")
            return {"success": False, "error": str(e)}

    def download_all_pdfs(self, project_id: str, max_workers: int | None = None) -> dict[str, Any]:
        """下载项目中所有有 PDF URL 但没有本地文件的论文（并行下载）"""
        if max_workers is None:
            max_workers = int(os.environ.get("PARALLEL_WORKERS", "4"))

        items = self.storage.query("papers", {"project_id": project_id})
        results = {"total": 0, "downloaded": 0, "skipped": 0, "failed": 0}

        to_download = []
        for item in items:
            paper = Paper(**item)
            pdf_url = paper.open_access.pdf_url if paper.open_access else ""
            if not pdf_url:
                pool_item = self.storage.get_item("papers_pool", paper.paper_id)
                if pool_item:
                    pdf_url = pool_item.get("pdf_url", "")
            if not pdf_url:
                continue
            if paper.pdf_path and Path(paper.pdf_path).exists():
                results["skipped"] += 1
                continue
            to_download.append(paper.paper_id)

        results["total"] = len(to_download)
        if not to_download:
            return results

        logger.info(f"Downloading {len(to_download)} PDFs with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.download_pdf, pid): pid for pid in to_download}
            for future in as_completed(futures):
                pid = futures[future]
                try:
                    result = future.result()
                    if result.get("success"):
                        results["downloaded"] += 1
                    else:
                        results["failed"] += 1
                        logger.warning(f"Download failed for {pid}: {result.get('error')}")
                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"Download exception for {pid}: {e}")

        return results

    def _update_pdf_path(self, paper_id: str, pdf_path: str) -> None:
        """更新论文的 pdf_path"""
        item = self.storage.get_item("papers", paper_id)
        if item:
            item["pdf_path"] = pdf_path
            self.storage.upsert_item("papers", paper_id, item)

    def parse_paper(self, paper_id: str, force: bool = False) -> dict[str, Any]:
        item = self.storage.get_item("papers", paper_id)
        if not item:
            return {"success": False, "error": "Paper not found"}

        paper = Paper(**item)

        if not force and paper.status in (
            PaperStatus.PARSED, PaperStatus.CARD_READY, PaperStatus.EVIDENCE_READY,
        ):
            existing_chunks = self.storage.query("paper_chunks", {"paper_id": paper_id})
            logger.info(f"Paper {paper_id} already parsed ({len(existing_chunks)} chunks), skipping")
            return {"success": True, "skipped": True, "chunk_count": len(existing_chunks)}

        pool_id = self._get_pool_id(paper)
        if pool_id:
            pool_item = self.storage.load_from_folder("papers_pool", pool_id)
            if pool_item and not pool_item.get("is_pdf_downloaded", False):
                logger.info(f"PDF not downloaded for {paper_id}, auto-downloading...")
                dl_result = self.download_pdf(paper_id)
                if not dl_result.get("success"):
                    return {"success": False, "error": f"PDF auto-download failed: {dl_result.get('error')}"}
                item = self.storage.get_item("papers", paper_id)
                if item:
                    paper = Paper(**item)

        self._update_status(paper_id, PaperStatus.PARSING)

        parse_result = ParseResult(
            paper_id=paper_id,
            parser_name="pdfplumber",
            status="parsing",
            started_at=datetime.now().isoformat(),
        )

        if not paper.pdf_path:
            return self._fail(paper_id, parse_result, "No PDF path")

        if not Path(paper.pdf_path).exists():
            return self._fail(paper_id, parse_result, "PDF file missing")

        pages_text, parser_name, quality_flags = self._extract_with_fallback(paper.pdf_path)

        if pages_text:
            pages_text = [(pn, self._post_processor.process(t)) for pn, t in pages_text]
            pages_text = self._post_processor.remove_headers_footers(pages_text)

        parse_result.parser_name = parser_name
        parse_result.page_count = len(pages_text)
        parse_result.quality_flags = quality_flags

        # 表格提取
        try:
            from src.agents_v3.research_workspace.parser.adapters import PdfPlumberAdapter
            tbl_adapter = PdfPlumberAdapter()
            if tbl_adapter.can_parse(paper.pdf_path):
                extracted_tables = tbl_adapter.extract_tables(paper.pdf_path)
                parse_result.table_count = len(extracted_tables)
        except Exception:
            pass

        if "scanned_pdf_suspected" in quality_flags:
            parse_result.quality_flags = quality_flags
            self.storage.upsert_item("parse_results", parse_result.parse_id, parse_result.model_dump())
            return self._fail(paper_id, parse_result, "Scanned PDF detected, no text extractable")

        if not pages_text:
            return self._fail(paper_id, parse_result, "No text extracted from PDF")

        chunks_data = self._chunk_by_sections(pages_text, paper_id)

        if self._enable_contextual:
            chunks_data = self._enrich_context(chunks_data, paper)

        chunks_data = self._chunk_cleaner.clean(chunks_data)
        chunks_data = self._create_parent_chunks(chunks_data, paper_id)

        if not chunks_data:
            return self._fail(paper_id, parse_result, "No text extracted from PDF")

        body_chunks = [c for c in chunks_data if c.get("chunk_type") != ChunkType.REFERENCE.value]
        ref_chunks = [c for c in chunks_data if c.get("chunk_type") == ChunkType.REFERENCE.value]

        parse_result.chunk_count = len(chunks_data)
        parse_result.body_chunk_count = len(body_chunks)
        parse_result.reference_count = len(ref_chunks)

        sections_set = {c.get("section_type", "") for c in chunks_data if c.get("section_type")}
        parse_result.section_count = len(sections_set)

        if ref_chunks:
            ref_text = "\n".join(c.get("text", "") for c in ref_chunks)
            references = self._extract_references(ref_text, paper_id)
            if references:
                self._save_references(paper_id, references)
                parse_result.reference_count = len(references)

        quality_flags, diagnostics = self._check_quality_enhanced(
            pages_text, parse_result.section_count, parse_result.chunk_count
        )
        parse_result.quality_flags = quality_flags
        parse_result.diagnostics = diagnostics

        sections = self._assemble_sections(paper_id, chunks_data)
        self._save_chunks(paper_id, chunks_data)
        self._save_sections(paper_id, sections)

        # 从解析文本中提取论文元数据（title/abstract/authors）
        self._extract_and_update_metadata(paper_id, pages_text, sections)

        parse_result.status = "success"
        parse_result.finished_at = datetime.now().isoformat()
        self.storage.upsert_item("parse_results", parse_result.parse_id, parse_result.model_dump())

        self._update_status(paper_id, PaperStatus.PARSED)
        self._mark_pool_parsed(paper)

        logger.info(f"Parsed paper {paper_id}: {len(body_chunks)} body chunks, {len(ref_chunks)} refs")

        # 解析成功后自动向量化（L0/L1/L2）
        try:
            embed_result = self.embed_paper(paper_id)
            if embed_result.get("success"):
                logger.info(f"Embedded paper {paper_id}: {embed_result.get('chunk_count')} chunks")
            else:
                logger.warning(f"Embed failed for {paper_id}: {embed_result.get('error')}")
        except Exception as e:
            logger.warning(f"Embed failed for {paper_id}, continuing without vectors: {e}")

        # 解析成功后自动提取实体/关系（知识图谱）
        try:
            from src.agents_v3.research_workspace.services.graph_extractor import GraphExtractor
            extractor = GraphExtractor(storage=self.storage)
            extraction_result = extractor.extract_from_paper(paper_id)
            logger.info(
                f"Extracted from paper {paper_id}: "
                f"{len(extraction_result.get('entities', []))} entities, "
                f"{extraction_result.get('sections_processed', 0)} sections"
            )
        except Exception as e:
            logger.warning(f"Entity extraction failed for {paper_id}, continuing: {e}")

        return {
            "success": True,
            "chunk_count": len(chunks_data),
            "body_chunk_count": len(body_chunks),
            "reference_count": len(ref_chunks),
            "page_count": parse_result.page_count,
            "section_count": len(sections),
            "quality_flags": quality_flags,
            "parse_id": parse_result.parse_id,
        }

    def _fail(self, paper_id: str, parse_result: ParseResult, error: str) -> dict[str, Any]:
        """统一失败处理"""
        self._update_status(paper_id, PaperStatus.FAILED, error)
        parse_result.status = "failed"
        parse_result.error_message = error
        parse_result.finished_at = datetime.now().isoformat()
        self.storage.upsert_item("parse_results", parse_result.parse_id, parse_result.model_dump())
        logger.error(f"Parse failed for {paper_id}: {error}")
        return {"success": False, "error": error, "parse_id": parse_result.parse_id}

    def parse_project_papers(
        self, project_id: str, only_unparsed: bool = True, max_workers: int | None = None
    ) -> dict[str, Any]:
        """解析项目中的所有论文（并行解析）"""
        if max_workers is None:
            max_workers = int(os.environ.get("PARALLEL_WORKERS", "4"))

        papers = self.storage.query("papers", {"project_id": project_id})
        results = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

        to_parse = []
        for p in papers:
            paper = Paper(**p)
            if only_unparsed and paper.status in (
                PaperStatus.PARSED,
                PaperStatus.CARD_READY,
                PaperStatus.EVIDENCE_READY,
            ):
                results["skipped"] += 1
                continue
            to_parse.append(paper.paper_id)

        results["total"] = len(to_parse)
        if not to_parse:
            return results

        logger.info(f"Parsing {len(to_parse)} papers with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.parse_paper, pid): pid for pid in to_parse}
            for future in as_completed(futures):
                pid = futures[future]
                try:
                    result = future.result()
                    if result.get("success"):
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                        logger.warning(f"Parse failed for {pid}: {result.get('error')}")
                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"Parse exception for {pid}: {e}")

        return results

    def get_chunks(
        self,
        paper_id: str,
        chunk_types: list[str] | None = None,
        exclude_types: list[str] | None = None,
    ) -> list[PaperChunk]:
        """获取论文 chunks，支持类型过滤"""
        chunks_data = self.storage.load_collection("paper_chunks")
        paper_chunks = [c for c in chunks_data if c.get("paper_id") == paper_id]

        if not paper_chunks:
            old_chunks = self.storage.load_collection(f"chunks_{paper_id}")
            if old_chunks:
                migrated = self._migrate_old_chunks(old_chunks, paper_id)
                paper_chunks = migrated

        if chunk_types:
            paper_chunks = [c for c in paper_chunks if c.get("chunk_type", "body") in chunk_types]
        if exclude_types:
            paper_chunks = [c for c in paper_chunks if c.get("chunk_type", "body") not in exclude_types]

        paper_chunks.sort(key=lambda c: c.get("chunk_index", 0))

        return [PaperChunk(**c) for c in paper_chunks]

    def get_body_chunks(self, paper_id: str) -> list[PaperChunk]:
        """只获取正文 chunks（排除 reference、table、figure_caption）"""
        exclude = [ChunkType.REFERENCE.value, ChunkType.TABLE.value, ChunkType.FIGURE_CAPTION.value]
        return self.get_chunks(paper_id, exclude_types=exclude)

    def get_parse_result(self, paper_id: str) -> ParseResult | None:
        """获取解析结果"""
        items = self.storage.query("parse_results", {"paper_id": paper_id})
        if items:
            return ParseResult(**items[-1])
        return None

    def embed_paper(self, paper_id: str) -> dict[str, Any]:
        """将已解析的论文向量化并存入 Qdrant"""
        from src.agents_v3.research_workspace.storage.vector import get_vector_storage

        chunks = self.get_chunks(paper_id)
        if not chunks:
            return {"success": False, "error": "No chunks found, run parse_paper first"}

        chunk_dicts = [c.model_dump() for c in chunks]

        try:
            vector_storage = get_vector_storage()
        except Exception as e:
            return {"success": False, "error": f"Failed to init vector storage: {e}"}

        try:
            vector_storage.delete_by_paper(paper_id)
        except Exception:
            pass

        texts = [c["text"] for c in chunk_dicts]
        logger.info(f"Embedding {len(texts)} chunks for paper {paper_id}")

        if vector_storage.use_inference:
            vector_storage.add_chunks(chunk_dicts, texts, sparse_embeddings=None)
        else:
            from src.agents_v3.research_workspace.storage.embedding_provider import get_embedding_provider
            embedding_service = get_embedding_provider()
            embeddings = embedding_service.embed_texts(texts)
            vector_storage.add_chunks(chunk_dicts, embeddings)

        paper = self.storage.get_item("papers", paper_id)
        project_id = paper.get("project_id", "") if paper else ""
        title = ""
        abstract = ""
        if paper:
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")
        if not title:
            pool_item = self.storage.get_item("papers_pool", paper_id)
            if pool_item:
                title = pool_item.get("title", "")
                abstract = pool_item.get("abstract", "")
        profile_text = f"{title}. {abstract}".strip()
        if profile_text and len(profile_text) > 10:
            if vector_storage.use_inference:
                vector_storage.add_paper_profiles(
                    paper_ids=[paper_id],
                    texts=[profile_text],
                    metadatas=[{"project_id": project_id, "title": title}],
                )
            else:
                profile_embedding = embedding_service.embed_query(profile_text)
                vector_storage.add_paper_profiles(
                    paper_ids=[paper_id],
                    texts=[profile_text],
                    metadatas=[{"project_id": project_id, "title": title}],
                    embeddings=[profile_embedding],
                )
            logger.info(f"Added paper profile for {paper_id}")

        # ── L1: 嵌入 paper_sections ──
        sections_data = self.storage.query("paper_sections", {"paper_id": paper_id})
        if sections_data:
            # 注入 section_id 到 chunks（JSONStorage 中的 chunks 可能没有 section_id）
            chunk_to_section: dict[str, str] = {}
            for sec in sections_data:
                for cid in sec.get("chunk_ids", []):
                    chunk_to_section[cid] = sec["section_id"]
            for c in chunk_dicts:
                if not c.get("section_id") and c["chunk_id"] in chunk_to_section:
                    c["section_id"] = chunk_to_section[c["chunk_id"]]

            # 筛选有 summary 或足够长 text 的 sections
            embeddable_sections = [
                s for s in sections_data
                if s.get("summary") or (s.get("text") and len(s.get("text", "").strip()) > 50)
            ]
            if embeddable_sections:
                try:
                    vector_storage.delete_by_paper(paper_id, collection="paper_sections")
                except Exception:
                    pass

                section_texts = [
                    s.get("summary") or s.get("text", "")[:500]
                    for s in embeddable_sections
                ]

                if vector_storage.use_inference:
                    vector_storage.add_paper_sections(embeddable_sections, embeddings=None, sparse_embeddings=None)
                else:
                    from src.agents_v3.research_workspace.storage.embedding_provider import get_embedding_provider
                    section_embeddings = get_embedding_provider().embed_texts(section_texts)
                    vector_storage.add_paper_sections(embeddable_sections, section_embeddings)

                logger.info(f"Added {len(embeddable_sections)} section vectors for {paper_id}")

        return {
            "success": True,
            "chunk_count": len(chunk_dicts),
            "cloud_inference": vector_storage.use_inference,
        }

    def search_chunks(
        self, query: str, paper_ids: list[str] | None = None, top_k: int = 5,
        return_parent: bool = True,
    ) -> list[dict[str, Any]]:
        """向量检索最相关的 chunks，支持返回父块"""
        from src.agents_v3.research_workspace.storage.embedding_provider import get_embedding_provider
        from src.agents_v3.research_workspace.storage.vector import get_vector_storage

        embedding_service = get_embedding_provider()
        vector_storage = get_vector_storage()

        query_embedding = embedding_service.embed_query(query)
        results = vector_storage.search_chunks(query_embedding, top_k=top_k, paper_ids=paper_ids)

        if not return_parent:
            return results

        parent_ids = set()
        for r in results:
            pid = r.get("metadata", {}).get("parent_id", "")
            if pid:
                parent_ids.add(pid)

        if not parent_ids:
            return results

        parent_map: dict[str, str] = {}
        try:
            all_chunks = self.storage.load_collection("paper_chunks")
            for c in all_chunks:
                if c.get("chunk_id") in parent_ids:
                    parent_map[c["chunk_id"]] = c.get("text", "")
        except Exception:
            pass

        for r in results:
            pid = r.get("metadata", {}).get("parent_id", "")
            if pid and pid in parent_map:
                r["child_text"] = r["text"]
                r["text"] = parent_map[pid]
                r["is_parent_context"] = True

        return results

    # ── 质量检查 ──────────────────────────────────────

    def _check_quality(self, pages_text: list[tuple[int, str]]) -> list[str]:
        flags = []
        total_chars = sum(len(t) for _, t in pages_text)
        empty_pages = sum(1 for _, t in pages_text if not t.strip())

        if total_chars < 100:
            flags.append("empty_pdf")
        elif total_chars < 500:
            flags.append("low_text_coverage")

        if empty_pages > len(pages_text) * 0.5:
            flags.append("scanned_pdf_suspected")

        all_lines = []
        for _, t in pages_text:
            all_lines.extend(t.split("\n"))
        short_lines = sum(1 for l in all_lines if 0 < len(l.strip()) < 20)
        if len(all_lines) > 10 and short_lines > len(all_lines) * 0.6:
            flags.append("too_many_short_lines")

        return flags

    # ── 章节检测 ──────────────────────────────────────

    _SECTION_PATTERNS = [
        "abstract", "摘要",
        "introduction", "引言", "导言",
        "related work", "相关工作", "文献综述",
        "background", "背景", "preliminary", "preliminaries",
        "method", "方法", "methodology", "方法论",
        "approach", "approaches",
        "experiment", "实验", "experiments",
        "model", "模型", "estimation", "估计",
        "simulation", "仿真", "simulations",
        "data analysis", "数据分析",
        "proposed method", "proposed model",
        "model selection", "模型选择", "model estimation",
        "simulation results", "simulation settings",
        "result", "结果", "results",
        "discussion", "讨论",
        "conclusion", "结论", "conclusions",
        "limitation", "局限", "limitations",
        "future work", "未来工作", "future direction",
        "acknowledgment", "致谢",
        "reference", "参考文献", "references",
        "appendix", "附录",
    ]

    def _detect_section(self, line: str) -> str | None:
        """检测段落是否是章节标题，返回归一化的 section_type"""
        stripped = line.strip()
        if not stripped or len(stripped) > 100:
            return None

        lower = stripped.lower()

        has_number_prefix = bool(re.match(r"^\d+[\.\)]?\s+", stripped))
        if has_number_prefix:
            cleaned = re.sub(r"^\d+[\.\)]?\s+", "", lower).strip()
            if not cleaned or len(cleaned) > 60:
                return None
            for pattern in self._SECTION_PATTERNS:
                if cleaned == pattern or cleaned.startswith(pattern + " "):
                    return _SECTION_TYPE_MAP.get(pattern, pattern)

        if len(lower) < 30 and (stripped[0].isupper() or "一" <= stripped[0] <= "鿿"):
            for pattern in self._SECTION_PATTERNS:
                if lower == pattern:
                    return _SECTION_TYPE_MAP.get(pattern, pattern)

        return None

    def _estimate_tokens(self, text: str) -> int:
        """粗略估算 token 数"""
        cn_chars = sum(1 for c in text if "一" <= c <= "鿿")
        en_chars = len(text) - cn_chars
        return cn_chars // 2 + en_chars // 4

    # ── 分块 ──────────────────────────────────────────

    @staticmethod
    def _enrich_context(chunks: list[dict[str, Any]], paper: Paper) -> list[dict[str, Any]]:
        """Anthropic Contextual Retrieval：给每个 chunk 前缀论文标题、作者、章节上下文"""
        title = (paper.title or "").strip()
        if not title:
            return chunks

        author_names = [a.name for a in paper.authors if a.name][:3]
        authors_str = ", ".join(author_names) if author_names else "Unknown"

        for chunk in chunks:
            section = chunk.get("section_title", "") or chunk.get("section_type", "")
            original_text = chunk.get("text", "")
            if not original_text:
                continue

            prefix = f'This chunk is from "{title}" by {authors_str}.'
            if section:
                prefix += f" Section: {section}."
            prefix += "\n\n"

            chunk.setdefault("metadata", {})["original_text"] = original_text
            chunk["text"] = prefix + original_text
            chunk["token_count"] = len(chunk["text"].split())

        return chunks

    def _chunk_by_sections(
        self, pages_text: list[tuple[int, str]], paper_id: str
    ) -> list[dict[str, Any]]:
        """按章节分块，每块 500-900 tokens，带 50-100 token overlap"""
        chunks: list[dict[str, Any]] = []
        current_section_type = ""
        current_text = ""
        current_page_start = 1
        current_page_end = 1
        chunk_idx = 0
        char_offset = 0
        sections_seen: set[str] = set()
        prev_tail = ""

        for page_num, text in pages_text:
            lines = text.split("\n")
            for line in lines:
                section_type = self._detect_section(line)
                if section_type:
                    if current_text.strip():
                        new_chunks = self._flush_buffer(
                            current_text.strip(), current_section_type,
                            paper_id, chunk_idx, char_offset,
                            current_page_start, current_page_end, prev_tail,
                        )
                        if new_chunks:
                            prev_tail = self._get_tail(current_text.strip())
                            chunks.extend(new_chunks)
                            chunk_idx += len(new_chunks)
                            char_offset += len(current_text)
                        current_text = ""
                    current_section_type = section_type
                    sections_seen.add(section_type)
                    current_page_start = page_num
                else:
                    current_text += line + "\n"
                    tokens = self._estimate_tokens(current_text)
                    if tokens >= 800:
                        new_chunks = self._flush_buffer(
                            current_text.strip(), current_section_type,
                            paper_id, chunk_idx, char_offset,
                            current_page_start, current_page_end, prev_tail,
                        )
                        if new_chunks:
                            prev_tail = self._get_tail(current_text.strip())
                            chunks.extend(new_chunks)
                            chunk_idx += len(new_chunks)
                            char_offset += len(current_text)
                        current_text = ""
                        current_page_start = page_num
            current_page_end = page_num

        if current_text.strip():
            new_chunks = self._flush_buffer(
                current_text.strip(), current_section_type,
                paper_id, chunk_idx, char_offset,
                current_page_start, current_page_end, prev_tail,
            )
            if new_chunks:
                chunks.extend(new_chunks)

        return chunks

    def _get_tail(self, text: str, tokens: int = 80) -> str:
        """获取文本尾部用于 overlap"""
        words = text.split()
        if len(words) <= tokens:
            return text
        return " ".join(words[-tokens:])

    def _flush_buffer(
        self, text: str, section_type: str, paper_id: str,
        start_idx: int, char_offset: int,
        page_start: int, page_end: int, prev_tail: str = "",
    ) -> list[dict[str, Any]]:
        """将文本缓冲拆分为 500-900 token 的块"""
        if len(text.strip()) < 30 and section_type not in ("title", "abstract"):
            return []

        chunk_type = _SECTION_TO_CHUNK_TYPE.get(section_type, ChunkType.BODY.value)

        tokens = self._estimate_tokens(text)
        if tokens <= 900:
            chunk_text = text
            if prev_tail and chunk_type == ChunkType.BODY.value:
                overlap_text = prev_tail + " " + text
                if self._estimate_tokens(overlap_text) <= 1000:
                    chunk_text = overlap_text

            return [self._make_chunk(
                paper_id, start_idx, section_type, chunk_type,
                chunk_text, char_offset, page_start, page_end,
            )]

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) <= 1 and tokens > 900:
            sentences = re.split(r"(?<=[.!?。！？])\s+", text)
            paragraphs = [s.strip() for s in sentences if s.strip()]

        result: list[dict[str, Any]] = []
        buf = ""
        idx = start_idx
        for para in paragraphs:
            candidate = (buf + " " + para).strip() if buf else para
            if self._estimate_tokens(candidate) > 900 and buf:
                result.append(self._make_chunk(
                    paper_id, idx, section_type, chunk_type,
                    buf, char_offset, page_start, page_end,
                ))
                idx += 1
                char_offset += len(buf) + 1
                buf = para
            else:
                buf = candidate
        if buf:
            result.append(self._make_chunk(
                paper_id, idx, section_type, chunk_type,
                buf, char_offset, page_start, page_end,
            ))
        return result

    def _make_chunk(
        self, paper_id: str, chunk_index: int,
        section_type: str, chunk_type: str,
        text: str, char_offset: int,
        page_start: int, page_end: int,
    ) -> dict[str, Any]:
        """构建标准 chunk 字典"""
        return {
            "chunk_id": f"chunk_{paper_id}_{chunk_index:04d}",
            "paper_id": paper_id,
            "chunk_index": chunk_index,
            "section_title": section_type.replace("_", " ").title() if section_type else "",
            "section_type": section_type,
            "chunk_type": chunk_type,
            "text": text,
            "start_char": char_offset,
            "end_char": char_offset + len(text),
            "page_start": page_start,
            "page_end": page_end,
            "token_count": self._estimate_tokens(text),
            "parser_name": "pdfplumber",
            "quality_flags": [],
            "metadata": {},
        }

    # ── Parent-Child 分块 ──────────────────────────────

    def _create_parent_chunks(
        self, child_chunks: list[dict[str, Any]], paper_id: str, target_tokens: int = 2000
    ) -> list[dict[str, Any]]:
        """将子块聚合为父块（~target_tokens tokens），返回包含父子的完整列表"""
        body_chunks = []
        other_chunks = []
        for c in child_chunks:
            if c.get("chunk_type") == ChunkType.REFERENCE.value:
                other_chunks.append(c)
            else:
                body_chunks.append(c)

        if not body_chunks:
            return child_chunks

        parents: list[dict[str, Any]] = []
        parent_idx = 0

        groups: list[list[dict]] = []
        current_group: list[dict] = []
        current_section = body_chunks[0].get("section_type", "")

        for chunk in body_chunks:
            sec = chunk.get("section_type", "")
            group_tokens = sum(self._estimate_tokens(c.get("text", "")) for c in current_group)
            if sec != current_section and current_group:
                groups.append(current_group)
                current_group = []
                current_section = sec
            current_group.append(chunk)
            if sum(self._estimate_tokens(c.get("text", "")) for c in current_group) >= target_tokens:
                groups.append(current_group)
                current_group = []
        if current_group:
            groups.append(current_group)

        for group in groups:
            if not group:
                continue
            texts = []
            for c in group:
                orig = c.get("metadata", {}).get("original_text")
                texts.append(orig if orig else c.get("text", ""))
            merged_text = "\n\n".join(texts)
            page_start = min(c.get("page_start", 0) for c in group)
            page_end = max(c.get("page_end", 0) for c in group)
            section_type = group[0].get("section_type", "")
            section_title = group[0].get("section_title", "")

            parent_id = f"parent_{paper_id}_{parent_idx:04d}"
            parent_chunk = {
                "chunk_id": parent_id,
                "paper_id": paper_id,
                "chunk_index": -1,
                "section_title": section_title,
                "section_type": section_type,
                "chunk_type": "parent",
                "text": merged_text,
                "start_char": group[0].get("start_char", 0),
                "end_char": group[-1].get("end_char", 0),
                "page_start": page_start,
                "page_end": page_end,
                "token_count": self._estimate_tokens(merged_text),
                "parser_name": group[0].get("parser_name", "pdfplumber"),
                "quality_flags": [],
                "metadata": {},
            }
            parents.append(parent_chunk)

            for child in group:
                child["parent_id"] = parent_id

            parent_idx += 1

        return parents + body_chunks + other_chunks

    # ── 存储 ──────────────────────────────────────────

    def _save_chunks(self, paper_id: str, chunks: list[dict[str, Any]]) -> None:
        """保存到 paper_chunks 集合"""
        existing = self.storage.load_collection("paper_chunks")
        filtered = [c for c in existing if c.get("paper_id") != paper_id]
        filtered.extend(chunks)
        self.storage.save_collection("paper_chunks", filtered)

    def _assemble_sections(self, paper_id: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """将 chunks 按 section_type 聚合为 PaperSection 列表"""
        section_map: OrderedDict[str, dict] = OrderedDict()

        for c in chunks:
            st = c.get("section_type", "unknown") or "unknown"
            if st not in section_map:
                section_map[st] = {
                    "section_type": st,
                    "section_title": c.get("section_title", st),
                    "texts": [],
                    "chunk_ids": [],
                    "page_start": c.get("page_start", 0),
                    "page_end": c.get("page_end", 0),
                    "token_count": 0,
                }
            sec = section_map[st]
            sec["texts"].append(c.get("text", ""))
            sec["chunk_ids"].append(c.get("chunk_id", ""))
            sec["page_end"] = max(sec["page_end"], c.get("page_end", 0))
            sec["token_count"] += c.get("token_count", 0)

        chunk_to_section: dict[str, str] = {}
        for idx, (st, sec) in enumerate(section_map.items()):
            sid = f"sec_{paper_id}_{idx:03d}"
            for cid in sec["chunk_ids"]:
                chunk_to_section[cid] = sid

        for c in chunks:
            c["section_id"] = chunk_to_section.get(c.get("chunk_id", ""), "")

        sections = []
        for idx, (st, sec) in enumerate(section_map.items()):
            full_text = "\n\n".join(sec["texts"])
            sections.append({
                "section_id": f"sec_{paper_id}_{idx:03d}",
                "paper_id": paper_id,
                "section_type": st,
                "section_title": sec["section_title"],
                "section_index": idx,
                "page_start": sec["page_start"],
                "page_end": sec["page_end"],
                "text": full_text,
                "token_count": sec["token_count"],
                "claims": [],
                "entities": [],
                "figures": [],
                "tables": [],
                "background_points": [],
                "motivation_points": [],
                "gap_points": [],
                "contribution_points": [],
                "prior_work_refs": [],
                "methods_used": [],
                "datasets_used": [],
                "model_details": [],
                "key_results": [],
                "limitations": [],
                "future_work": [],
                "implications": [],
                "chunk_ids": sec["chunk_ids"],
                "extraction_status": "pending",
            })

        return sections

    def _save_sections(self, paper_id: str, sections: list[dict[str, Any]]) -> None:
        """保存到 paper_sections 集合"""
        existing = self.storage.load_collection("paper_sections")
        filtered = [s for s in existing if s.get("paper_id") != paper_id]
        filtered.extend(sections)
        self.storage.save_collection("paper_sections", filtered)
        logger.info(f"Saved {len(sections)} sections for paper {paper_id}")

    def _save_references(self, paper_id: str, references: list[Reference]) -> None:
        """保存结构化参考文献到 references 集合"""
        existing = self.storage.load_collection("paper_references")
        filtered = [r for r in existing if r.get("citing_paper_id") != paper_id]
        filtered.extend([r.model_dump() for r in references])
        self.storage.save_collection("paper_references", filtered)

    def _migrate_old_chunks(self, old_chunks: list[dict], paper_id: str) -> list[dict]:
        """迁移旧格式 chunks 到新格式"""
        migrated = []
        for i, c in enumerate(old_chunks):
            new_c = {
                "chunk_id": c.get("chunk_id", f"chunk_{paper_id}_{i:04d}"),
                "paper_id": paper_id,
                "chunk_index": c.get("chunk_index", i),
                "section_title": c.get("section_title", ""),
                "section_type": "",
                "chunk_type": "body",
                "text": c.get("text", ""),
                "start_char": c.get("start_char", 0),
                "end_char": c.get("end_char", 0),
                "page_start": c.get("page_number", c.get("page_start", 0)),
                "page_end": c.get("page_number", c.get("page_end", 0)),
                "token_count": c.get("token_count", 0),
                "parser_name": "pdfplumber",
                "quality_flags": [],
                "metadata": {},
            }
            migrated.append(new_c)
        return migrated

    def _extract_and_update_metadata(
        self, paper_id: str, pages_text: list[tuple[int, str]], sections: list[dict]
    ) -> None:
        """从解析文本中提取 title/abstract/authors 并更新 papers_pool 记录"""
        pool_item = self.storage.get_item("papers_pool", paper_id)
        if not pool_item:
            return

        needs_update = False

        # 1. 提取 title：从第一页前几行非空文本中找标题
        if not pool_item.get("title") or pool_item["title"] == "?":
            if pages_text:
                first_page = pages_text[0][1] if pages_text[0] else ""
                title = self._guess_title_from_text(first_page)
                if title:
                    pool_item["title"] = title
                    needs_update = True

        # 2. 提取 abstract：从 abstract section 中获取
        if not pool_item.get("abstract"):
            abstract_sec = [s for s in sections if s.get("section_type") == "abstract"]
            if abstract_sec:
                raw = abstract_sec[0].get("text", "")
                # 取前 500 字符作为摘要
                abstract = raw[:500].strip()
                if abstract:
                    pool_item["abstract"] = abstract
                    needs_update = True

        # 3. 提取 authors：从第一页文本中猜测
        if not pool_item.get("authors") or pool_item["authors"] == []:
            if pages_text:
                first_page = pages_text[0][1] if pages_text[0] else ""
                authors = self._guess_authors_from_text(first_page)
                if authors:
                    pool_item["authors"] = authors
                    needs_update = True

        if needs_update:
            pool_item["is_parsed"] = True
            self.storage.save_to_folder("papers_pool", paper_id, pool_item)
            logger.info(f"Updated papers_pool metadata for {paper_id}: title={pool_item.get('title','?')[:50]}")

    _TITLE_SKIP = re.compile(
        r'^(?:the|a|an|proceedings|conference|journal|workshop|symposium|advances|neurips|icml|iclr|aaai|acl|emnlp|naacl|cvpr|iccv|eccv|sigir|www|kdd|ijcai|nips)\b',
        re.IGNORECASE,
    )
    _AFFIL_KEYWORDS = re.compile(
        r'(?:university|institute|laboratory|department|school|college|academy|center|centre|china|usa|uk|germany|france|japan|korea)',
        re.IGNORECASE,
    )

    def _guess_title_from_text(self, text: str) -> str:
        """从第一页文本中猜测论文标题（取第一个合理候选行）"""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines[:10]:
            if len(line) < 10 or len(line) > 200:
                continue
            if self._TITLE_SKIP.match(line):
                continue
            # 跳过数字开头的行（通常是 affiliation: "1Dept of ..."）
            if line[0].isdigit():
                continue
            if "@" in line:
                continue
            if self._AFFIL_KEYWORDS.search(line):
                continue
            # 跳过包含常见非标题模式的行
            lower = line.lower()
            if any(p in lower for p in ["abstract", "introduction", "copyright", "proceedings"]):
                continue
            # 清理并返回第一个有效候选
            title = re.sub(r'\s+', ' ', line).strip()
            return title
        return ""

    def _guess_authors_from_text(self, text: str) -> list[dict]:
        """从第一页文本中猜测作者列表"""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for i, line in enumerate(lines[:10]):
            if len(line) > 150 or len(line) < 5:
                continue
            # 跳过 affiliation 行
            if self._AFFIL_KEYWORDS.search(line):
                continue
            if line[0].isdigit():
                continue
            # 检测作者模式：逗号分隔的名字，可能有上标数字
            # 典型格式："Jiawei Chen1,3, Hongyu Lin1,*, Xianpei Han1,2,*, Le Sun1,2"
            # 先去掉上标标记 (*, 数字)
            cleaned = re.sub(r'[*†‡§¶]', '', line)
            cleaned = re.sub(r'\d+', '', cleaned)
            parts = [p.strip() for p in cleaned.split(',') if p.strip()]
            # 过滤：每个部分应该是 2-4 个词的人名
            names = []
            for p in parts:
                words = p.split()
                if 1 <= len(words) <= 5 and all(2 <= len(w) <= 20 for w in words):
                    # 排除非人名
                    if not self._TITLE_SKIP.match(p) and not self._AFFIL_KEYWORDS.search(p):
                        names.append(p)
            if 2 <= len(names) <= 20:
                return [{"name": n} for n in names]
        return []

    def _update_status(self, paper_id: str, status: PaperStatus, error: str = "") -> None:
        item = self.storage.get_item("papers", paper_id)
        if item:
            item["status"] = status.value
            if error:
                item["error_message"] = error
            self.storage.upsert_item("papers", paper_id, item)

    def _get_pool_id(self, paper: Paper) -> str:
        """获取论文在 papers_pool 中的 ID"""
        if paper.source_payload:
            pid = paper.source_payload.get("pool_paper_id", "")
            if pid:
                return pid
        if paper.identifiers:
            if paper.identifiers.doi:
                return f"doi_{paper.identifiers.doi.replace('/', '_').replace('.', '_')}"
            if paper.identifiers.arxiv_id:
                return f"arxiv_{paper.identifiers.arxiv_id}"
            if paper.identifiers.openalex_id:
                return f"oa_{paper.identifiers.openalex_id}"
            if paper.identifiers.semantic_scholar_id:
                return f"s2_{paper.identifiers.semantic_scholar_id}"
        return ""

    def _update_pool_field(self, paper: Paper, field: str, value: Any) -> None:
        """更新 papers_pool 中的单个字段"""
        pool_id = self._get_pool_id(paper)
        if not pool_id:
            return
        pool_item = self.storage.load_from_folder("papers_pool", pool_id)
        if pool_item:
            pool_item[field] = value
            self.storage.save_to_folder("papers_pool", pool_id, pool_item)

    def _mark_pool_pdf_downloaded(self, paper: Paper) -> None:
        """标记 papers_pool 中对应记录的 is_pdf_downloaded = True"""
        self._update_pool_field(paper, "is_pdf_downloaded", True)

    def _mark_pool_parsed(self, paper: Paper) -> None:
        """标记 papers_pool 中对应记录的 is_parsed = True"""
        self._update_pool_field(paper, "is_parsed", True)

    # ── 多解析器 fallback ────────────────────────────────

    def _extract_with_fallback(
        self, pdf_path: str
    ) -> tuple[list[tuple[int, str]], str, list[str]]:
        """多解析器 fallback 链路"""
        quality_flags: list[str] = []

        scan_result = self._detect_scanned_pdf(pdf_path)
        if scan_result["is_scanned"]:
            quality_flags.append("scanned_pdf_suspected")
            quality_flags.append(f"scan_confidence={scan_result['confidence']:.2f}")
            pages_text, parser_name, ocr_flags = self._try_ocr_fallback(pdf_path)
            quality_flags.extend(ocr_flags)
            return pages_text, parser_name, quality_flags

        for adapter in self._adapters:
            if not adapter.can_parse(pdf_path):
                quality_flags.append(f"{adapter.name}_unavailable")
                continue

            pages_text, flags = adapter.extract_pages(pdf_path)
            quality_flags.extend(flags)

            if not pages_text or not any(t.strip() for _, t in pages_text):
                quality_flags.append(f"{adapter.name}_empty")
                continue

            full_text = "\n".join(t for _, t in pages_text)
            if self._detect_garbled_text(full_text):
                quality_flags.append("garbled_text_detected")
                quality_flags.append(f"{adapter.name}_garbled")
                logger.warning(f"Garbled text detected with {adapter.name}: {pdf_path}")
                continue

            if self._detect_poor_spacing(full_text):
                quality_flags.append("poor_word_spacing")
                quality_flags.append(f"{adapter.name}_spacing")
                logger.warning(f"Poor word spacing with {adapter.name}: {pdf_path}")
                continue

            return pages_text, adapter.name, quality_flags

        pages_text, parser_name, ocr_flags = self._try_ocr_fallback(pdf_path)
        quality_flags.extend(ocr_flags)
        if pages_text:
            quality_flags.append("ocr_fallback_used")
            return pages_text, parser_name, quality_flags

        logger.warning(f"No text extracted from {pdf_path}, all adapters failed")
        quality_flags.append("all_adapters_failed")
        return [], "none", quality_flags

    def _try_ocr_fallback(
        self, pdf_path: str
    ) -> tuple[list[tuple[int, str]], str, list[str]]:
        """尝试 OCR fallback：用 pytesseract 提取扫描 PDF 文本"""
        flags: list[str] = []
        try:
            import pytesseract
        except ImportError:
            flags.append("ocr_not_implemented")
            logger.warning("pytesseract not installed, OCR unavailable. Install with: pip install pytesseract")
            return [], "none", flags

        try:
            import pymupdf
        except ImportError:
            flags.append("ocr_no_pymupdf")
            return [], "none", flags

        try:
            doc = pymupdf.open(pdf_path)
            pages: list[tuple[int, str]] = []
            for i in range(len(doc)):
                page = doc[i]
                # 渲染页面为图片（300 DPI）
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("png")

                # OCR
                from io import BytesIO
                from PIL import Image
                img = Image.open(BytesIO(img_data))
                text = pytesseract.image_to_string(img, lang="chi_sim+eng")
                text = text.strip()
                if text:
                    pages.append((i + 1, text))

            doc.close()
            flags.append("ocr_tesseract_used")
            flags.append(f"ocr_pages_extracted:{len(pages)}")
            logger.info(f"OCR extracted {len(pages)} pages from {pdf_path}")
            return pages, "ocr_tesseract", flags

        except Exception as e:
            flags.append(f"ocr_error:{type(e).__name__}")
            logger.warning(f"OCR fallback failed: {e}")
            return [], "none", flags

    def _detect_scanned_pdf(self, pdf_path: str) -> dict[str, Any]:
        """检测 PDF 是否为扫描件（基于图片数量和文本量）"""
        try:
            import pymupdf
            doc = pymupdf.open(pdf_path)
            total_pages = len(doc)
            if total_pages == 0:
                doc.close()
                return {"is_scanned": False, "confidence": 0, "image_pages": 0, "text_pages": 0}

            image_pages = 0
            text_pages = 0
            for i in range(total_pages):
                page = doc[i]
                text = page.get_text("text").strip()
                images = page.get_images()
                if len(text) < 50 and len(images) > 0:
                    image_pages += 1
                elif len(text) >= 50:
                    text_pages += 1
            doc.close()

            if total_pages > 0:
                image_ratio = image_pages / total_pages
                if image_ratio > 0.7 and text_pages < total_pages * 0.3:
                    return {
                        "is_scanned": True,
                        "confidence": image_ratio,
                        "image_pages": image_pages,
                        "text_pages": text_pages,
                    }

            return {"is_scanned": False, "confidence": 0, "image_pages": image_pages, "text_pages": text_pages}
        except Exception:
            return {"is_scanned": False, "confidence": 0, "image_pages": 0, "text_pages": 0}

    # ── 中文 PDF 处理 ────────────────────────────────────

    def _detect_garbled_text(self, text: str) -> bool:
        """检测文本是否包含乱码"""
        if not text or len(text) < 50:
            return False

        control_chars = sum(1 for c in text if ord(c) < 0x20 and c not in '\n\r\t')
        if control_chars > len(text) * 0.05:
            return True

        replacement_chars = sum(1 for c in text if c in '□■◆◇○●◈◊■□')
        if replacement_chars > len(text) * 0.02:
            return True

        garbled_pattern = re.compile(r'[\U00020000-\U0002A6DF]{3,}')
        if garbled_pattern.search(text):
            return True

        total = len(text)
        abnormal = 0
        for c in text:
            cp = ord(c)
            if cp < 0x80:
                continue
            if 0x4E00 <= cp <= 0x9FFF:
                continue
            if 0x3400 <= cp <= 0x4DBF:
                continue
            if 0xFF00 <= cp <= 0xFFEF:
                continue
            if 0x3000 <= cp <= 0x303F:
                continue
            if c in '\n\r\t ':
                continue
            abnormal += 1
        if total > 100 and abnormal / total > 0.3:
            return True

        return False

    def _detect_poor_spacing(self, text: str) -> bool:
        """检测文本是否有严重的单词间距丢失问题"""
        if not text or len(text) < 200:
            return False

        lines = text.split("\n")
        checked = 0
        for line in lines:
            words = line.split()
            if len(words) < 3:
                continue
            long_words = sum(1 for w in words if len(w) > 20 and not re.search(r"[\d\-_]", w))
            if long_words > 0 and long_words / len(words) > 0.3:
                return True
            checked += 1
            if checked > 200:
                break

        return False

    def _detect_watermark(self, pages_text: list[tuple[int, str]]) -> bool:
        """检测 PDF 是否包含水印"""
        if not pages_text or len(pages_text) < 2:
            return False

        all_lines: list[str] = []
        for _, text in pages_text:
            for line in text.split("\n"):
                stripped = line.strip()
                if stripped and len(stripped) < 30:
                    all_lines.append(stripped)

        if not all_lines:
            return False

        watermark_keywords = [
            "知网", "CNKI", "万方", "维普", "Wanfang",
            "仅供", "个人使用", "未经授权", "禁止转载",
        ]
        for line in all_lines:
            for kw in watermark_keywords:
                if kw in line:
                    return True

        from collections import Counter
        line_counts = Counter(all_lines)
        total_pages = len(pages_text)
        for line, count in line_counts.items():
            if count >= total_pages * 0.5 and len(line) < 20:
                return True

        return False

    # ── 参考文献结构化提取 ────────────────────────────────

    _REF_SPLIT_PATTERNS = [
        re.compile(r'^\[(\d+)\]\s*', re.MULTILINE),
        re.compile(r'^(\d+)\.\s+', re.MULTILINE),
        re.compile(r'^\[(\d+[-–]\d+)\]\s*', re.MULTILINE),
    ]

    _DOI_PATTERN = re.compile(r'(10\.\d{4,}/[^\s,;]+)')
    _YEAR_PATTERN = re.compile(r'\b((?:19|20)\d{2})\b')

    def _extract_references(self, ref_text: str, paper_id: str) -> list[Reference]:
        """从参考文献文本中提取结构化引用"""
        if not ref_text or len(ref_text.strip()) < 20:
            return []

        refs: list[Reference] = []
        entries = self._split_references(ref_text)

        for i, raw_text in enumerate(entries):
            raw_text = raw_text.strip()
            if not raw_text or len(raw_text) < 10:
                continue

            ref = Reference(
                ref_id=f"ref_{paper_id}_{i:04d}",
                citing_paper_id=paper_id,
                index=i,
                raw_text=raw_text,
            )

            doi_match = self._DOI_PATTERN.search(raw_text)
            if doi_match:
                ref.doi = doi_match.group(1).rstrip('.')

            year_match = self._YEAR_PATTERN.search(raw_text)
            if year_match:
                ref.year = int(year_match.group(1))

            ref.title = self._guess_title(raw_text)
            ref.authors = self._guess_authors(raw_text)

            refs.append(ref)

        return refs

    _REF_ENTRY_START = re.compile(
        r'(?:^|\n)\s*'
        r'(?:[A-ZÀ-ÖØ-Þa-z][a-z]*\s+)?'
        r'[A-ZÀ-ÖØ-Þ][A-Za-z\-]+'
        r'[,.\s()]?.*?'
        r'(?:\(\s*\d{4}\s*\)|\d{4})'
    )

    def _split_references(self, text: str) -> list[str]:
        """按编号模式分割参考文献条目"""
        parts = re.split(r'(?:^|\n)\s*\[\d+\]\s*', text)
        if len(parts) > 2:
            return [p.strip() for p in parts if p.strip()]

        parts = re.split(r'(?:^|\n)\s*\d+\.\s+', text)
        if len(parts) > 2:
            return [p.strip() for p in parts if p.strip()]

        entries = self._split_unnumbered_refs(text)
        if len(entries) > 2:
            return entries

        parts = re.split(r'\n\s*\n', text)
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()]

        return [text.strip()] if text.strip() else []

    def _split_unnumbered_refs(self, text: str) -> list[str]:
        """按 Author (Year) 模式分割无编号参考文献"""
        starts = []
        for m in self._REF_ENTRY_START.finditer(text):
            line_start = m.start()
            while line_start < len(text) and text[line_start] in '\n\r\t ':
                line_start += 1
            starts.append(line_start)

        if len(starts) < 2:
            return []

        entries = []
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(text)
            entry = text[start:end].strip()
            if entry and len(entry) > 10:
                entries.append(entry)

        return entries

    def _guess_title(self, raw_text: str) -> str:
        """启发式提取参考文献标题"""
        cleaned = re.sub(r'^\[\d+\]\s*', '', raw_text.strip())
        cleaned = re.sub(r'^\d+\.\s+', '', cleaned)

        year_match = re.search(r'\(\s*\d{4}[a-z]?\s*\)\.\s*', cleaned)
        if year_match:
            after_year = cleaned[year_match.end():]
            title_match = re.match(r'(.+?)\.\s+[A-Z]', after_year)
            if title_match:
                title = title_match.group(1).strip()
            else:
                title = after_year.split('.')[0].strip()
            title = title.strip('"\'""‘’')
            if len(title) > 5:
                return title[:200]

        parts = cleaned.split('.', 2)
        if len(parts) >= 2:
            title = parts[1].strip()
            title = title.strip('"\'""‘’')
            if len(title) > 5:
                return title[:200]

        return ""

    def _guess_authors(self, raw_text: str) -> list[str]:
        """启发式提取参考文献作者"""
        cleaned = re.sub(r'^\[\d+\]\s*', '', raw_text.strip())
        cleaned = re.sub(r'^\d+\.\s+', '', cleaned)

        first_sentence = cleaned.split('.', 1)[0].strip()
        first_sentence = re.sub(r'\s*\(\s*\d{4}\s*\)\s*$', '', first_sentence)
        first_sentence = re.sub(r'\s+\d{4}\s*$', '', first_sentence)

        if not first_sentence or len(first_sentence) > 200:
            return []

        authors = re.split(r',\s*(?:and\s+)?|\s+and\s+', first_sentence)
        result = []
        non_author_words = {'et al', 'eds', 'eds.', 'vol', 'no', 'pp', 'p'}
        for a in authors:
            a = a.strip()
            if a and len(a) < 60 and a.lower() not in non_author_words:
                result.append(a)

        return result

    # ── 质量报告增强 ────────────────────────────────────

    def _check_quality_enhanced(
        self, pages_text: list[tuple[int, str]], section_count: int, chunk_count: int
    ) -> tuple[list[str], dict[str, Any]]:
        """增强版质量检查，返回 (quality_flags, diagnostics)"""
        flags = self._check_quality(pages_text)
        diagnostics: dict[str, Any] = {}

        full_text = "\n".join(t for _, t in pages_text)

        if self._detect_garbled_text(full_text):
            if "garbled_text_detected" not in flags:
                flags.append("garbled_text_detected")
            diagnostics["garbled_text"] = True

        if self._detect_watermark(pages_text):
            flags.append("watermark_suspected")
            diagnostics["watermark"] = True

        if self._detect_dual_column(pages_text):
            flags.append("dual_column_detected")
            diagnostics["dual_column"] = True

        if pages_text and chunk_count > 0:
            total_lines = sum(len(t.split("\n")) for _, t in pages_text)
            section_ratio = section_count / max(chunk_count, 1)
            if section_ratio < 0.1 and total_lines > 50:
                flags.append("low_section_coverage")
                diagnostics["low_section_coverage"] = True

        diagnostics["total_chars"] = len(full_text)
        diagnostics["total_pages"] = len(pages_text)

        return flags, diagnostics

    def _detect_dual_column(self, pages_text: list[tuple[int, str]]) -> bool:
        """检测是否为双栏布局（基于行长度分布）"""
        if not pages_text:
            return False

        sample_pages = pages_text[:3]
        short_line_pairs = 0
        total_line_pairs = 0

        for _, text in sample_pages:
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for i in range(len(lines) - 1):
                total_line_pairs += 1
                if len(lines[i]) < 40 and len(lines[i + 1]) < 40:
                    if abs(len(lines[i]) - len(lines[i + 1])) < 10:
                        short_line_pairs += 1

        if total_line_pairs > 10 and short_line_pairs / total_line_pairs > 0.3:
            return True
        return False
