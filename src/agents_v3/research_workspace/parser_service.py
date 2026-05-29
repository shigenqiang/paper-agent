"""论文解析服务 - 增强版"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import (
    ChunkType,
    Paper,
    PaperChunk,
    PaperStatus,
    ParseResult,
)
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage


# ── 章节类型归一 ──────────────────────────────────────

_SECTION_TYPE_MAP: dict[str, str] = {
    "abstract": "abstract", "摘要": "abstract",
    "introduction": "introduction", "引言": "introduction", "导言": "introduction",
    "related work": "related_work", "相关工作": "related_work", "文献综述": "related_work",
    "background": "background", "背景": "background",
    "method": "method", "方法": "method", "methodology": "method", "方法论": "method",
    "approach": "method", "approaches": "method",
    "experiment": "method", "实验": "method", "experiments": "method",
    "result": "result", "结果": "result", "results": "result",
    "discussion": "discussion", "讨论": "discussion",
    "conclusion": "conclusion", "结论": "conclusion", "conclusions": "conclusion",
    "limitation": "limitation", "局限": "limitation", "limitations": "limitation",
    "future work": "future_work", "未来工作": "future_work", "future direction": "future_work",
    "acknowledgment": "acknowledgment", "致谢": "acknowledgment", "acknowledgment": "acknowledgment",
    "reference": "reference", "参考文献": "reference", "references": "reference",
    "appendix": "appendix", "附录": "appendix",
}

# 正文 chunk 类型映射
_SECTION_TO_CHUNK_TYPE: dict[str, str] = {
    "abstract": ChunkType.ABSTRACT.value,
    "introduction": ChunkType.BODY.value,
    "related_work": ChunkType.BODY.value,
    "background": ChunkType.BODY.value,
    "method": ChunkType.METHOD.value,
    "result": ChunkType.RESULT.value,
    "discussion": ChunkType.DISCUSSION.value,
    "limitation": ChunkType.LIMITATION.value,
    "conclusion": ChunkType.CONCLUSION.value,
    "future_work": ChunkType.BODY.value,
    "reference": ChunkType.REFERENCE.value,
    "appendix": ChunkType.APPENDIX.value,
    "acknowledgment": ChunkType.BODY.value,
}


class ParserService:
    """PDF 解析与分块"""

    def __init__(self, storage: JSONStorage | None = None):
        self.storage = storage or get_storage()

    def download_pdf(self, paper_id: str) -> dict[str, Any]:
        """下载论文 PDF 到本地"""
        import urllib.request
        from pathlib import Path

        item = self.storage.get_item("papers", paper_id)
        if not item:
            return {"success": False, "error": "Paper not found"}

        paper = Paper(**item)
        pdf_url = paper.open_access.pdf_url if paper.open_access else ""
        if not pdf_url:
            return {"success": False, "error": "No PDF URL"}

        # 目标路径
        project_id = paper.project_id
        dest_dir = self.storage.data_dir / "files" / project_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{paper_id}.pdf"

        if dest_path.exists():
            # 已下载，更新路径
            self._update_pdf_path(paper_id, str(dest_path))
            return {"success": True, "pdf_path": str(dest_path), "skipped": True}

        try:
            logger.info(f"Downloading PDF: {pdf_url}")
            headers = {"User-Agent": "PaperAgent/1.0 (research-tool)"}
            req = urllib.request.Request(pdf_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(dest_path, "wb") as f:
                    f.write(resp.read())
            self._update_pdf_path(paper_id, str(dest_path))
            logger.info(f"Downloaded PDF: {dest_path}")
            return {"success": True, "pdf_path": str(dest_path)}
        except Exception as e:
            logger.error(f"PDF download failed: {e}")
            return {"success": False, "error": str(e)}

    def download_all_pdfs(self, project_id: str) -> dict[str, Any]:
        """下载项目中所有有 PDF URL 但没有本地文件的论文"""
        items = self.storage.query("papers", {"project_id": project_id})
        results = {"total": 0, "downloaded": 0, "skipped": 0, "failed": 0}

        for item in items:
            paper = Paper(**item)
            pdf_url = paper.open_access.pdf_url if paper.open_access else ""
            if not pdf_url:
                continue
            if paper.pdf_path and Path(paper.pdf_path).exists():
                results["skipped"] += 1
                continue

            results["total"] += 1
            result = self.download_pdf(paper.paper_id)
            if result.get("success"):
                if result.get("skipped"):
                    results["skipped"] += 1
                else:
                    results["downloaded"] += 1
            else:
                results["failed"] += 1

        return results

    def _update_pdf_path(self, paper_id: str, pdf_path: str) -> None:
        """更新论文的 pdf_path"""
        item = self.storage.get_item("papers", paper_id)
        if item:
            item["pdf_path"] = pdf_path
            self.storage.upsert_item("papers", paper_id, item)

    def parse_paper(self, paper_id: str) -> dict[str, Any]:
        item = self.storage.get_item("papers", paper_id)
        if not item:
            return {"success": False, "error": "Paper not found"}

        paper = Paper(**item)

        # 开始解析 → PARSING
        self._update_status(paper_id, PaperStatus.PARSING)

        parse_result = ParseResult(
            paper_id=paper_id,
            project_id=paper.project_id,
            parser_name="pdfplumber",
            status="parsing",
            started_at=datetime.now().isoformat(),
        )

        if not paper.pdf_path:
            return self._fail(paper_id, parse_result, "No PDF path")

        from pathlib import Path
        if not Path(paper.pdf_path).exists():
            return self._fail(paper_id, parse_result, "PDF file missing")

        try:
            import pdfplumber
        except ImportError:
            return self._fail(paper_id, parse_result, "pdfplumber not installed")

        try:
            pages_text: list[tuple[int, str]] = []
            with pdfplumber.open(paper.pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    pages_text.append((i + 1, text))

            parse_result.page_count = len(pages_text)

            # 质量检查
            quality_flags = self._check_quality(pages_text)
            parse_result.quality_flags = quality_flags

            # 分块
            chunks_data = self._chunk_by_sections(pages_text, paper_id)

            if not chunks_data:
                return self._fail(paper_id, parse_result, "No text extracted from PDF")

            # 分离正文和参考文献
            body_chunks = [c for c in chunks_data if c.get("chunk_type") != ChunkType.REFERENCE.value]
            ref_chunks = [c for c in chunks_data if c.get("chunk_type") == ChunkType.REFERENCE.value]

            parse_result.chunk_count = len(chunks_data)
            parse_result.body_chunk_count = len(body_chunks)
            parse_result.reference_count = len(ref_chunks)

            # 统计 section 数
            sections = {c.get("section_type", "") for c in chunks_data if c.get("section_type")}
            parse_result.section_count = len(sections)

            # 保存到 paper_chunks 集合
            self._save_chunks(paper_id, chunks_data)

            # 保存 ParseResult
            parse_result.status = "success"
            parse_result.finished_at = datetime.now().isoformat()
            self.storage.upsert_item("parse_results", parse_result.parse_id, parse_result.model_dump())

            self._update_status(paper_id, PaperStatus.PARSED)
            logger.info(f"Parsed paper {paper_id}: {len(body_chunks)} body chunks, {len(ref_chunks)} refs")

            return {
                "success": True,
                "chunk_count": len(chunks_data),
                "body_chunk_count": len(body_chunks),
                "reference_count": len(ref_chunks),
                "page_count": parse_result.page_count,
                "section_count": parse_result.section_count,
                "quality_flags": quality_flags,
                "parse_id": parse_result.parse_id,
            }

        except Exception as e:
            return self._fail(paper_id, parse_result, str(e))

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
        self, project_id: str, only_unparsed: bool = True
    ) -> dict[str, Any]:
        papers = self.storage.query("papers", {"project_id": project_id})
        results = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

        for p in papers:
            paper = Paper(**p)
            if only_unparsed and paper.status in (
                PaperStatus.PARSED,
                PaperStatus.CARD_READY,
                PaperStatus.EVIDENCE_READY,
            ):
                results["skipped"] += 1
                continue

            results["total"] += 1
            result = self.parse_paper(paper.paper_id)
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1

        return results

    def get_chunks(
        self,
        paper_id: str,
        chunk_types: list[str] | None = None,
        exclude_types: list[str] | None = None,
    ) -> list[PaperChunk]:
        """获取论文 chunks，支持类型过滤"""
        # 优先从 paper_chunks 集合读取
        chunks_data = self.storage.load_collection("paper_chunks")
        paper_chunks = [c for c in chunks_data if c.get("paper_id") == paper_id]

        # 兼容旧格式
        if not paper_chunks:
            old_chunks = self.storage.load_collection(f"chunks_{paper_id}")
            if old_chunks:
                # 迁移到新格式
                migrated = self._migrate_old_chunks(old_chunks, paper_id)
                paper_chunks = migrated

        # 类型过滤
        if chunk_types:
            paper_chunks = [c for c in paper_chunks if c.get("chunk_type", "body") in chunk_types]
        if exclude_types:
            paper_chunks = [c for c in paper_chunks if c.get("chunk_type", "body") not in exclude_types]

        # 按 chunk_index 排序
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

        # 检查是否有过多短行（可能是表格或乱码）
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
        "background", "背景",
        "method", "方法", "methodology", "方法论",
        "approach", "approaches",
        "experiment", "实验", "experiments",
        "result", "结果", "results",
        "discussion", "讨论",
        "conclusion", "结论", "conclusions",
        "limitation", "局限", "limitations",
        "future work", "未来工作", "future direction",
        "acknowledgment", "致谢", "acknowledgment",
        "reference", "参考文献", "references",
        "appendix", "附录",
    ]

    def _detect_section(self, line: str) -> str | None:
        """检测段落是否是章节标题，返回归一化的 section_type"""
        stripped = line.strip().lower()
        cleaned = re.sub(r"^[\dIVXivxa-z]+[\.\)]\s*", "", stripped).strip()
        if not cleaned or len(cleaned) > 60:
            return None
        for pattern in self._SECTION_PATTERNS:
            if cleaned == pattern or cleaned.startswith(pattern):
                return _SECTION_TYPE_MAP.get(pattern, pattern)
        return None

    def _estimate_tokens(self, text: str) -> int:
        """粗略估算 token 数"""
        cn_chars = sum(1 for c in text if "一" <= c <= "鿿")
        en_chars = len(text) - cn_chars
        return cn_chars // 2 + en_chars // 4

    # ── 分块 ──────────────────────────────────────────

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
        prev_tail = ""  # 用于 overlap

        for page_num, text in pages_text:
            lines = text.split("\n")
            for line in lines:
                section_type = self._detect_section(line)
                if section_type:
                    # Flush current buffer
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

        # Flush remaining
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
        # 短文本丢弃（除非是标题/表格/图注）
        if len(text.strip()) < 30 and section_type not in ("title", "abstract"):
            return []

        chunk_type = _SECTION_TO_CHUNK_TYPE.get(section_type, ChunkType.BODY.value)

        tokens = self._estimate_tokens(text)
        if tokens <= 900:
            # 添加 overlap
            chunk_text = text
            if prev_tail and chunk_type == ChunkType.BODY.value:
                overlap_text = prev_tail + " " + text
                if self._estimate_tokens(overlap_text) <= 1000:
                    chunk_text = overlap_text

            return [self._make_chunk(
                paper_id, start_idx, section_type, chunk_type,
                chunk_text, char_offset, page_start, page_end,
            )]

        # Split by paragraphs, then by sentences if needed
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

    # ── 存储 ──────────────────────────────────────────

    def _save_chunks(self, paper_id: str, chunks: list[dict[str, Any]]) -> None:
        """保存到 paper_chunks 集合"""
        # 加载已有数据，移除该 paper 的旧 chunks
        existing = self.storage.load_collection("paper_chunks")
        filtered = [c for c in existing if c.get("paper_id") != paper_id]
        filtered.extend(chunks)
        self.storage.save_collection("paper_chunks", filtered)

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

    def _update_status(self, paper_id: str, status: PaperStatus, error: str = "") -> None:
        item = self.storage.get_item("papers", paper_id)
        if item:
            item["status"] = status.value
            if error:
                item["error_message"] = error
            self.storage.upsert_item("papers", paper_id, item)
