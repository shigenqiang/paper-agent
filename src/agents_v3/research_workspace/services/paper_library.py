"""论文库管理服务"""

from __future__ import annotations

import hashlib
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import (
    Author,
    CitationInfo,
    OpenAccessInfo,
    Paper,
    PaperClassification,
    PaperDates,
    PaperIdentifiers,
    PaperSource,
    PaperStatus,
)
from src.agents_v3.research_workspace.search.base import BaseSearchAdapter, QueryRecord, SearchQuery, SearchResult, SearchResponse
from src.agents_v3.research_workspace.search.dedup import build_existing_keys, make_dedup_key
from src.agents_v3.research_workspace.storage import get_storage


def search_result_to_meta(r: SearchResult) -> dict[str, Any]:
    """将 SearchResult 转换为 Paper 构造用的元数据 dict"""
    return {
        "title": r.title,
        "authors": [{"name": a} for a in r.authors],
        "dates": {"year": r.year},
        "source": {"venue": r.venue},
        "identifiers": {
            "doi": r.doi,
            "arxiv_id": r.arxiv_id,
            "pubmed_id": r.pubmed_id,
            "openalex_id": r.openalex_id,
            "semantic_scholar_id": r.semantic_scholar_id,
        },
        "abstract": r.abstract,
        "language": r.language,
        "publication_type": r.publication_type,
        "url": r.url,
        "open_access": {"pdf_url": r.pdf_url},
        "classification": {
            "topics": r.topics,
            "keywords": r.keywords,
        },
        "citation": {"citation_count": r.citations},
    }


def _apply_quality_filter(
    results: list[SearchResult], quality_threshold: float = 0.3, min_results: int = 3
) -> list[SearchResult]:
    """质量分过滤（保底保留 top-N）"""
    if not results:
        return []
    from src.agents_v3.research_workspace.search.quality_filter import compute_quality
    for r in results:
        if not r.quality_score:
            r.quality_score = compute_quality(r)
    filtered = [r for r in results if (r.quality_score or 0) >= quality_threshold]
    if len(filtered) < min_results and len(results) > min_results:
        results.sort(key=lambda r: r.quality_score or 0, reverse=True)
        filtered = results[:min_results]
    return filtered


class PaperLibraryService:
    """项目论文库管理"""

    def __init__(
        self,
        storage=None,
        search_adapters: list[BaseSearchAdapter] | None = None,
        global_storage=None,
        pg_storage: Any | None = None,
    ):
        self.storage = storage or get_storage()
        self.search_adapters = search_adapters or []
        self.global_storage = global_storage or get_storage()
        self.pg = pg_storage  # PostgresStorage instance (optional)


    # ── 论文池操作 ──────────────────────────────────────

    def add_to_pool(self, result: SearchResult) -> str:
        """将搜索结果存入全局论文池（无搜索分数），返回 paper_id"""
        # 用 DOI/arXiv ID/OpenAlex ID 生成稳定的 paper_id
        paper_id = self._make_pool_paper_id(result)
        existing = self.global_storage.load_from_folder("papers_pool", paper_id)
        if existing:
            logger.debug(f"Paper already in pool: {paper_id}")
            return paper_id

        pool_data = {
            "paper_id": paper_id,
            "title": result.title,
            "abstract": result.abstract,
            "authors": [{"name": a} for a in result.authors],
            "year": result.year,
            "venue": result.venue,
            "doi": result.doi,
            "arxiv_id": result.arxiv_id,
            "pubmed_id": result.pubmed_id,
            "openalex_id": result.openalex_id,
            "semantic_scholar_id": result.semantic_scholar_id,
            "url": result.url,
            "pdf_url": result.pdf_url,
            "citations": result.citations,
            "topics": result.topics,
            "keywords": result.keywords,
            "language": result.language,
            "publication_type": result.publication_type,
            "source": result.source,
            "source_payload": result.source_payload,
            "is_pdf_downloaded": False,
            "is_parsed": False,
            "added_at": __import__("datetime").datetime.now().isoformat(),
        }
        self.global_storage.save_to_folder("papers_pool", paper_id, pool_data)
        logger.info(f"Added to pool: {paper_id} - {result.title[:50]}")
        return paper_id

    def get_from_pool(self, paper_id: str) -> dict[str, Any] | None:
        """从全局论文池读取论文元数据"""
        return self.global_storage.load_from_folder("papers_pool", paper_id)

    def list_pool(self) -> list[dict[str, Any]]:
        """列出论文池中的所有论文"""
        return self.global_storage.list_folder("papers_pool")

    def _make_pool_paper_id(self, result: SearchResult) -> str:
        """生成稳定的 paper_id（基于标识符）"""
        if result.doi:
            return f"doi_{result.doi.replace('/', '_').replace('.', '_')}"
        if result.arxiv_id:
            return f"arxiv_{result.arxiv_id}"
        if result.openalex_id:
            return f"oa_{result.openalex_id}"
        if result.semantic_scholar_id:
            return f"s2_{result.semantic_scholar_id}"
        # fallback: 用标题生成
        import hashlib
        title_hash = hashlib.md5(result.title.lower().strip().encode()).hexdigest()[:12]
        return f"title_{title_hash}"

    def add_uploaded_paper(
        self,
        project_id: str,
        file_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> Paper:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        paper_id = f"paper_{uuid.uuid4().hex[:8]}"
        dest_dir = self.storage.data_dir / "files" / project_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{paper_id}.pdf"

        import shutil
        shutil.copy2(file_path, dest_path)

        meta = metadata or {}
        authors_raw = meta.get("authors", [])
        authors = [
            Author(name=a) if isinstance(a, str) else Author(**a)
            for a in authors_raw
        ]

        paper = Paper(
            paper_id=paper_id,
            project_id=project_id,
            title=meta.get("title", path.stem),
            abstract=meta.get("abstract", ""),
            authors=authors,
            dates=PaperDates(year=meta.get("year")),
            source=PaperSource(venue=meta.get("venue", "")),
            identifiers=PaperIdentifiers(
                doi=meta.get("doi", ""),
                arxiv_id=meta.get("arxiv_id", ""),
            ),
            source_platform="upload",
            status=PaperStatus.UPLOADED,
            pdf_path=str(dest_path),
        )
        self.storage.upsert_item("papers", paper_id, paper.model_dump())
        logger.info(f"Added paper {paper_id} to project {project_id}")
        return paper

    def add_paper_metadata(
        self,
        project_id: str,
        metadata: dict[str, Any],
        source: str = "import",
        scores: dict[str, float] | None = None,
        topic: str = "",
        pool_paper_id: str = "",
        query_id: str = "",
    ) -> Paper | None:
        # 去重检查
        existing = self.storage.query("papers", {"project_id": project_id})
        existing_keys = build_existing_keys(existing)
        if make_dedup_key(metadata) in existing_keys:
            # 即使论文已存在，仍保存主题相关分数
            if scores and topic:
                dedup_key = make_dedup_key(metadata)
                for p in existing:
                    if make_dedup_key(p) == dedup_key:
                        self.save_topic_score(p["paper_id"], topic, scores, query_id)
                        break
            logger.info(f"Duplicate skipped: {metadata.get('title', '')[:50]}")
            return None

        # 优先使用 pool_paper_id（来自论文池），否则生成新 ID
        paper_id = pool_paper_id if pool_paper_id else f"paper_{uuid.uuid4().hex[:8]}"

        # 兼容处理：authors 可能是 list[str] 或 list[Author] 或 list[dict]
        authors_raw = metadata.get("authors", [])
        authors = []
        for a in authors_raw:
            if isinstance(a, str):
                authors.append(Author(name=a))
            elif isinstance(a, dict):
                authors.append(Author(**a))
            elif isinstance(a, Author):
                authors.append(a)
            else:
                authors.append(Author(name=str(a)))

        # 兼容处理：identifiers 可能是 dict 或 PaperIdentifiers
        ids_raw = metadata.get("identifiers")
        if isinstance(ids_raw, PaperIdentifiers):
            identifiers = ids_raw
        elif isinstance(ids_raw, dict):
            identifiers = PaperIdentifiers(**ids_raw)
        else:
            identifiers = PaperIdentifiers(
                doi=metadata.get("doi", ""),
                arxiv_id=metadata.get("arxiv_id", ""),
                pubmed_id=metadata.get("pubmed_id", ""),
                openalex_id=metadata.get("openalex_id", ""),
                semantic_scholar_id=metadata.get("semantic_scholar_id", ""),
            )

        # 兼容处理：dates
        dates_raw = metadata.get("dates")
        if isinstance(dates_raw, PaperDates):
            dates = dates_raw
        elif isinstance(dates_raw, dict):
            dates = PaperDates(**dates_raw)
        else:
            dates = PaperDates(year=metadata.get("year"))

        # 兼容处理：source
        source_raw = metadata.get("source_info") or metadata.get("source")
        if isinstance(source_raw, PaperSource):
            paper_source = source_raw
        elif isinstance(source_raw, dict):
            paper_source = PaperSource(**source_raw)
        else:
            paper_source = PaperSource(venue=metadata.get("venue", ""))

        # 兼容处理：open_access
        oa_raw = metadata.get("open_access")
        if isinstance(oa_raw, OpenAccessInfo):
            oa = oa_raw
        elif isinstance(oa_raw, dict):
            oa = OpenAccessInfo(**oa_raw)
        else:
            oa = OpenAccessInfo(pdf_url=metadata.get("pdf_url", ""))

        # 兼容处理：classification
        cls_raw = metadata.get("classification")
        if isinstance(cls_raw, PaperClassification):
            classification = cls_raw
        elif isinstance(cls_raw, dict):
            classification = PaperClassification(**cls_raw)
        else:
            classification = PaperClassification(
                topics=metadata.get("topics", []),
                keywords=metadata.get("keywords", []),
            )

        # 兼容处理：citation
        cit_raw = metadata.get("citation")
        if isinstance(cit_raw, CitationInfo):
            citation = cit_raw
        elif isinstance(cit_raw, dict):
            citation = CitationInfo(**cit_raw)
        else:
            citation = CitationInfo(citation_count=metadata.get("citations"))

        # 提取余弦相似度得分
        dense_score = 0.0
        if scores:
            dense_score = scores.get("dense_score", 0.0)

        paper = Paper(
            paper_id=paper_id,
            project_id=project_id,
            title=metadata.get("title", ""),
            abstract=metadata.get("abstract", ""),
            language=metadata.get("language", ""),
            publication_type=metadata.get("publication_type", ""),
            authors=authors,
            identifiers=identifiers,
            dates=dates,
            source=paper_source,
            open_access=oa,
            classification=classification,
            citation=citation,
            url=metadata.get("url", ""),
            source_platform=source if isinstance(source, str) else "",
            status=PaperStatus.IMPORTED,
            dense_score=dense_score,
        )
        self.storage.upsert_item("papers", paper_id, paper.model_dump())

        # 持久化主题相关分数到 topic_scores 集合
        if scores and topic:
            self.save_topic_score(paper_id, topic, scores, query_id)

        logger.info(f"Imported paper {paper_id}: {paper.title}")
        return paper

    def add_search_results(
        self,
        project_id: str,
        results: list[dict[str, Any]],
    ) -> list[Paper]:
        papers = []
        for r in results:
            paper = self.add_paper_metadata(project_id, r, source="search")
            if paper:
                papers.append(paper)
        return papers

    def search_papers(
        self,
        query: SearchQuery,
    ) -> list[SearchResult]:
        """调用已注册的搜索适配器，返回结果（去重 + HyDE 排序 + 质量过滤）"""
        from src.agents_v3.research_workspace.search.merger import SearchResultMerger
        from src.agents_v3.research_workspace.search.query_optimizer import refine_query
        from src.agents_v3.research_workspace.config import get_search_config
        merger = SearchResultMerger()

        # 优化搜索词：提取核心主题，去除泛化词
        original_query = query.query
        optimized = refine_query(original_query)
        if optimized != original_query:
            logger.info(f"Query optimized: \"{original_query}\" → \"{optimized}\"")
            query = query.model_copy(update={"query": optimized})

        all_results: list[SearchResult] = []

        def _search_one(adapter):
            try:
                return adapter.search(query), None
            except Exception as e:
                logger.error(f"Search adapter {adapter.source_name} failed: {e}")
                return [], e

        with ThreadPoolExecutor(max_workers=min(4, len(self.search_adapters))) as executor:
            futures = {executor.submit(_search_one, a): a for a in self.search_adapters}
            for future in as_completed(futures):
                results, error = future.result()
                all_results.extend(results)

        # 去重合并
        merged = merger.merge(all_results)

        # 混合排序 + 质量过滤
        search_cfg = get_search_config().get("hyde", {})
        hybrid_cfg = get_search_config().get("hybrid", {})
        qual_threshold = search_cfg.get("quality_threshold", 0.3)
        top_n = hybrid_cfg.get("top_n", 30)

        if merged:
            try:
                from src.agents_v3.research_workspace.search.hybrid_ranker import HybridRanker
                hybrid_ranker = HybridRanker(
                    rrf_k=get_search_config().get("rrf_k", 60),
                    top_k=hybrid_cfg.get("top_k", 60),
                    top_n=top_n,
                    quality_threshold=qual_threshold,
                )
                merged = hybrid_ranker.rank(merged, original_query)
            except Exception as e:
                logger.warning(f"Hybrid ranking failed, applying quality filter only: {e}")
                merged = _apply_quality_filter(merged[:top_n], qual_threshold)

        # 存入论文池
        for r in merged:
            paper_id = self.add_to_pool(r)
            r.source_payload["pool_paper_id"] = paper_id

        return merged


    def _index_paper_profiles(self, papers: list[Paper]) -> None:
        """将论文摘要向量化存入 Qdrant paper_profiles 集合"""
        try:
            from src.agents_v3.research_workspace.storage.vector import get_vector_storage
            from src.agents_v3.research_workspace.storage.embedding import get_embedding_service

            vs = get_vector_storage()
            es = get_embedding_service()

            paper_ids = []
            texts = []
            metadatas = []
            for p in papers:
                abstract = p.abstract or ""
                if not abstract:
                    continue
                text = f"{p.title or ''} {abstract}"
                paper_ids.append(p.paper_id)
                texts.append(text)
                metadatas.append({
                    "title": p.title or "",
                    "abstract": abstract[:500],
                    "source_platform": p.source_platform or "",
                })

            if not paper_ids:
                return

            embeddings = es.embed_texts(texts)
            vs.add_paper_profiles(
                paper_ids=paper_ids,
                texts=texts,
                metadatas=metadatas,
                embeddings=embeddings,
            )
            logger.info(f"Indexed {len(paper_ids)} paper profiles to Qdrant")
        except Exception as e:
            logger.warning(f"Paper profile indexing failed (non-fatal): {e}")

    # ── 文献综述专用搜索 ──────────────────────────────

    def search_for_review(
        self,
        project_id: str,
        query: str,
        max_local: int | None = None,
        max_remote: int | None = None,
        max_total: int | None = None,
    ) -> dict[str, Any]:
        """为文献综述搜索论文：本地项目库 + 联网学术平台

        流程：
        1. 本地搜索：从项目已入库论文中按相关性筛选
        2. 查询相似度检查：与历史查询对比，复用相关论文
        3. 联网搜索：用同一搜索词在学术平台搜索补充
        4. 返回结果（不持久化，用户 commit 时再写入）

        Args:
            project_id: 项目 ID
            query: 搜索词
            max_local: 本地搜索最大论文数
            max_remote: 联网搜索最大论文数
            max_total: 总论文数上限

        Returns:
            {
                "local_papers": [{"paper_id": ..., "score": ...}],
                "remote_papers": [{"paper_id": ..., "score": ...}],
                "total_count": int,
                "query": str,
            }
        """
        import os
        _max_local = max_local or int(os.getenv("REVIEW_LOCAL_MAX", "20"))
        _max_remote = max_remote or int(os.getenv("REVIEW_REMOTE_MAX", "20"))
        _max_total = max_total or int(os.getenv("REVIEW_MAX_PAPERS", "40"))

        # ── Step 1: 本地搜索（项目论文库）──────────────
        local_results = self._search_local_papers(project_id, query, _max_local)
        local_count = len(local_results)
        logger.info(f"Local search: {local_count} papers found (max={_max_local})")

        # ── Step 2: 查询相似度检查 ──────────────────
        # 检查是否有相似的历史查询，复用其关联的论文
        similar_paper_ids = self._find_similar_queries(query, project_id)
        if similar_paper_ids:
            logger.info(f"Found {len(similar_paper_ids)} papers from similar queries")

        # ── Step 3: 联网搜索（学术平台）────────────────
        remaining_slots = max(0, _max_total - local_count)
        remote_limit = min(remaining_slots, _max_remote)

        remote_results: list[dict[str, Any]] = []
        if remote_limit > 0:
            new_remote = self._search_remote_papers(
                project_id, query, remote_limit,
                exclude_ids={r["paper_id"] for r in local_results},
            )
            remote_results.extend(new_remote)

        logger.info(f"Remote search: {len(remote_results)} papers (limit={remote_limit})")

        # ── Step 4: 返回结果 ──────────────────────────
        total = local_count + len(remote_results)
        logger.info(f"Review search complete: {local_count} local + {len(remote_results)} remote = {total} total")

        return {
            "local_papers": local_results,
            "remote_papers": remote_results,
            "total_count": total,
            "query": query,
        }

    def _search_local_papers(
        self,
        project_id: str,
        query: str,
        max_count: int,
    ) -> list[dict[str, Any]]:
        """从项目论文库中搜索：历史查询匹配 → Qdrant hybrid 检索

        Step 1: 从 paper_queries 获取历史查询关联的论文作为候选。
        Step 2: Qdrant dense + sparse 双路交集检索，按 paper_id 聚合分数。
        """
        papers = self.list_papers(project_id)
        if not papers:
            return []

        # ── Step 1: 历史查询关联论文 ──
        candidate_ids = self._find_similar_queries(query, project_id)
        logger.info(f"Historical query match: {len(candidate_ids)} candidate papers")

        # 候选不够时用全项目论文补充
        all_paper_ids = {p.paper_id for p in papers}
        if len(candidate_ids) < max_count:
            candidate_ids.update(all_paper_ids)

        # 只保留项目内论文
        candidate_ids &= all_paper_ids
        if not candidate_ids:
            return []

        # ── Step 2: Qdrant hybrid 检索 ────────────────
        paper_scores = self._qdrant_hybrid_search(
            query, project_id, list(candidate_ids),
        )

        if not paper_scores:
            logger.warning("Qdrant hybrid search failed, returning empty")

        # 直接取 top-N（RRF 融合后无需 relevance 过滤）
        selected = []
        for pid, score in paper_scores[:max_count]:
            selected.append({
                "paper_id": pid,
                "score": round(score, 3),
                "source": "local",
            })

        return selected

    def _qdrant_hybrid_search(
        self,
        query: str,
        project_id: str,
        paper_ids: list[str],
    ) -> list[tuple[str, float]]:
        """Qdrant dense + sparse + RRF 混合检索，按 paper_id 聚合分数

        云端推理模式下直接传文本，Qdrant 自动向量化。
        优先搜索 paper_profiles，无结果时回退到 paper_chunks。

        Returns:
            [(paper_id, score), ...] 按分数降序排列
        """
        try:
            from src.agents_v3.research_workspace.storage.vector import get_vector_storage
            vector_storage = get_vector_storage()

            # ── 优先搜 paper_profiles（论文级）──
            paper_scores = self._qdrant_search_collection(
                vector_storage, query, paper_ids, "paper_profiles",
            )
            if paper_scores:
                return paper_scores

            # ── 回退搜 paper_chunks（chunk 级，按 paper_id 聚合）──
            return self._qdrant_search_collection(
                vector_storage, query, paper_ids, "paper_chunks",
            )

        except Exception as e:
            logger.error(f"Qdrant hybrid search failed: {e}")
            return []

    def _qdrant_search_collection(
        self,
        vector_storage,
        query: str,
        paper_ids: list[str],
        collection: str,
        top_k: int = 100,
    ) -> list[tuple[str, float]]:
        """对指定 Qdrant 集合执行双路交集检索（dense + sparse 各取 top-K，取交集）

        交集内的论文按两路排名之和排序（排名越小越好）。
        交集为空时回退到 dense-only 结果。

        Returns:
            [(paper_id, score), ...] score 为归一化排名分（越高越好）
        """
        # ── Dense 路 ──
        dense_results = vector_storage.search_dense_by_text(
            query_text=query, top_k=top_k, paper_ids=paper_ids, collection=collection,
        )
        # ── Sparse 路 ──
        sparse_results = vector_storage.search_sparse_by_text(
            query_text=query, top_k=top_k, paper_ids=paper_ids, collection=collection,
        )

        if not dense_results and not sparse_results:
            return []

        # 提取 paper_id
        def _get_pid(item: dict) -> str:
            return item.get("metadata", {}).get("paper_id", "") or item.get("id", "")

        # Dense 排名表 {paper_id: rank}
        dense_rank: dict[str, int] = {}
        for rank, item in enumerate(dense_results):
            pid = _get_pid(item)
            if pid and pid not in dense_rank:
                dense_rank[pid] = rank

        # Sparse 排名表 {paper_id: rank}
        sparse_rank: dict[str, int] = {}
        for rank, item in enumerate(sparse_results):
            pid = _get_pid(item)
            if pid and pid not in sparse_rank:
                sparse_rank[pid] = rank

        # 双路交集：同时出现在 dense 和 sparse top-K 中
        intersection = set(dense_rank.keys()) & set(sparse_rank.keys())

        if not intersection:
            # 交集为空，回退到 dense-only
            logger.debug(f"No intersection for {collection}, falling back to dense-only")
            paper_best: dict[str, float] = {}
            for item in dense_results:
                pid = _get_pid(item)
                score = item.get("score", 0.0)
                if pid and (pid not in paper_best or score > paper_best[pid]):
                    paper_best[pid] = score
            ranked = sorted(paper_best.items(), key=lambda x: x[1], reverse=True)
            logger.info(f"Qdrant {collection} (dense fallback): {len(ranked)} papers")
            return ranked

        # 交集内按两路排名之和排序（排名越小 = 分数越高）
        scored: list[tuple[str, float]] = []
        for pid in intersection:
            combined_rank = dense_rank[pid] + sparse_rank[pid]
            # 归一化：排名和越小越好，转换为 [0,1] 分数
            score = 1.0 - combined_rank / (top_k * 2)
            scored.append((pid, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        logger.info(f"Qdrant {collection} (intersection): {len(scored)} papers (dense={len(dense_rank)}, sparse={len(sparse_rank)})")
        return scored

    def _search_remote_papers(
        self,
        project_id: str,
        query: str,
        need_count: int,
        exclude_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """联网搜索学术平台，返回新论文（去重后）"""
        exclude = exclude_ids or set()

        if not self.search_adapters:
            logger.warning("No search adapters configured, skipping remote search")
            return []

        search_query = SearchQuery(
            query=query,
            project_id=project_id,
            limit=need_count * 2,  # 多搜一些，去重后可能不够
        )

        # 复用现有 search_papers 方法
        results = self.search_papers(search_query)

        # 去重：排除已有的论文
        new_results = []
        for r in results:
            pool_id = r.source_payload.get("pool_paper_id", "")
            # 用 dedup key 检查是否已在项目中
            meta = search_result_to_meta(r)
            dedup_key = make_dedup_key(meta)
            if dedup_key and dedup_key in exclude:
                continue
            if pool_id and pool_id in exclude:
                continue

            new_results.append({
                "paper_id": pool_id or r.result_id,
                "score": round(r.final_score, 3),
                "dense_score": round(r.dense_score, 3),
                "quality_score": round(r.quality_score, 3),
                "source": r.source,
                "title": r.title,
                "dedup_key": dedup_key or "",
            })

            if len(new_results) >= need_count:
                break

        return new_results

    def _find_similar_queries(
        self,
        query_text: str,
        project_id: str,
        similarity_threshold: float = 0.5,
        top_k: int = 5,
    ) -> set[str]:
        """查找与当前查询相似的历史查询，返回关联的 paper_id 集合

        流程：
        1. Qdrant dense-only 语义搜索 → 获取相似 query_id
        2. 从 PG queries 表确认 query 存在
        3. 从 PG paper_queries 表获取关联的 paper_id
        4. 回退：Jaccard token 相似度匹配 PG queries 表
        """
        paper_ids: set[str] = set()

        # ── 优先：Qdrant 向量相似度 ──
        try:
            from src.agents_v3.research_workspace.storage.vector import get_vector_storage
            vs = get_vector_storage()
            similar = vs.search_similar_queries(query_text, top_k=top_k)
            for item in similar:
                if item["score"] < similarity_threshold:
                    continue
                query_id = item["query_id"]
                # 从 paper_queries 获取关联论文
                if self.pg:
                    rows = self.pg.query("paper_queries", {"query_id": query_id})
                    for row in rows:
                        paper_ids.add(row["paper_id"])
                    logger.info(
                        f"Similar query found (vector): {query_id} "
                        f"(score={item['score']:.2f}), {len(rows)} papers"
                    )
        except Exception as e:
            logger.debug(f"Qdrant query similarity failed, falling back to Jaccard: {e}")

        # ── 回退：Jaccard token 相似度 ──
        if not paper_ids:
            query_tokens = set(query_text.lower().split())
            if not query_tokens:
                return paper_ids

            best_query_id = None
            best_sim = 0.0

            # 从 PG queries 表读取所有查询
            if self.pg:
                try:
                    records = self.pg.query("queries", {})
                    for rec in records:
                        rec_text = rec.get("query_text", "")
                        if not rec_text:
                            continue
                        rec_tokens = set(rec_text.lower().split())
                        if not rec_tokens:
                            continue
                        intersection = query_tokens & rec_tokens
                        union = query_tokens | rec_tokens
                        sim = len(intersection) / len(union) if union else 0.0
                        if sim > best_sim and sim >= similarity_threshold:
                            best_sim = sim
                            best_query_id = rec["query_id"]

                    if best_query_id:
                        rows = self.pg.query("paper_queries", {"query_id": best_query_id})
                        for row in rows:
                            paper_ids.add(row["paper_id"])
                        logger.info(
                            f"Similar query found (Jaccard): {best_query_id} "
                            f"(sim={best_sim:.2f}), {len(rows)} papers"
                        )
                except Exception as e:
                    logger.debug(f"Jaccard query similarity failed: {e}")

        return paper_ids

    def list_papers(
        self,
        project_id: str,
        filters: dict[str, Any] | None = None,
    ) -> list[Paper]:
        query = {"project_id": project_id}
        if filters:
            query.update(filters)
        items = self.storage.query("papers", query)
        return [Paper(**i) for i in items]

    def get_paper(self, paper_id: str) -> Paper | None:
        item = self.storage.get_item("papers", paper_id)
        if item:
            return Paper(**item)
        return None

    def update_paper(self, paper_id: str, **updates: Any) -> Paper | None:
        item = self.storage.get_item("papers", paper_id)
        if not item:
            return None
        item.update(updates)
        item["updated_at"] = datetime.now().isoformat()
        self.storage.upsert_item("papers", paper_id, item)
        return Paper(**item)

    def mark_included(self, paper_id: str) -> Paper | None:
        return self.update_paper(paper_id, included=True, exclude_reason="")

    def mark_excluded(self, paper_id: str, reason: str) -> Paper | None:
        return self.update_paper(paper_id, included=False, exclude_reason=reason)

    def import_doi_list(
        self,
        project_id: str,
        doi_list: list[str],
    ) -> list[Paper]:
        """通过 DOI 导入论文，使用 Semantic Scholar 查询元数据（并行查询）"""
        import json
        import urllib.request

        def _lookup_one(doi: str) -> tuple[str, dict[str, Any]]:
            meta = self._lookup_doi_via_s2(doi)
            return doi, meta

        # 并行查询 DOI 元数据
        doi_meta: dict[str, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=min(4, len(doi_list))) as executor:
            futures = {executor.submit(_lookup_one, doi): doi for doi in doi_list}
            for future in as_completed(futures):
                doi, meta = future.result()
                doi_meta[doi] = meta

        # 顺序导入（写入操作需要保持顺序）
        papers = []
        for doi in doi_list:
            meta = doi_meta.get(doi, {})
            meta["identifiers"] = PaperIdentifiers(doi=doi)
            paper = self.add_paper_metadata(project_id, meta, source="doi")
            if paper:
                papers.append(paper)
        return papers

    @staticmethod
    def _lookup_doi_via_s2(doi: str) -> dict[str, Any]:
        """通过 Semantic Scholar API 查询 DOI 元数据"""
        import json
        import time
        import urllib.request

        url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=title,abstract,authors,year,venue,openAccessPdf,externalIds,citationCount"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PaperAgent/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            authors = [a.get("name", "") for a in (data.get("authors") or []) if a.get("name")]
            oa = data.get("openAccessPdf") or {}
            pdf_url = oa.get("url", "") or ""
            ext = data.get("externalIds") or {}
            arxiv_id = ext.get("ArXiv", "") or ""

            # 优先使用 arXiv PDF
            if arxiv_id:
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

            return {
                "title": data.get("title", f"DOI: {doi}"),
                "abstract": data.get("abstract") or "",
                "authors": [{"name": a} for a in authors],
                "year": data.get("year"),
                "venue": data.get("venue") or "",
                "open_access": {"pdf_url": pdf_url} if pdf_url else {},
            }
        except Exception as e:
            logger.warning(f"S2 DOI lookup failed for {doi}: {e}")
            return {"title": f"DOI: {doi}"}

    def import_bibtex(
        self,
        project_id: str,
        bibtex_text: str,
    ) -> list[Paper]:
        papers = []
        entries = self._parse_bibtex(bibtex_text)
        for entry in entries:
            paper = self.add_paper_metadata(project_id, entry, source="bibtex")
            if paper:
                papers.append(paper)
        return papers

    def _parse_bibtex(self, text: str) -> list[dict[str, Any]]:
        entries = []
        parts = text.split("@")
        for part in parts[1:]:
            match = re.match(r'\w+\{([^,]+),', part)
            if not match:
                continue
            key = match.group(1).strip()
            entry: dict[str, Any] = {"key": key}
            for field_match in re.finditer(r'(\w+)\s*=\s*\{([^}]*)\}', part):
                field_name = field_match.group(1).lower()
                field_value = field_match.group(2).strip()
                if field_name == "author":
                    entry["authors"] = [a.strip() for a in field_value.split(" and ")]
                elif field_name == "year":
                    try:
                        entry["year"] = int(field_value)
                    except ValueError:
                        pass
                elif field_name == "title":
                    entry["title"] = field_value
                elif field_name == "journal":
                    entry["venue"] = field_value
                elif field_name == "doi":
                    entry["doi"] = field_value
            entries.append(entry)
        return entries

    # ── 搜索与提交 ──────────────────────────────

    def search_candidates(
        self,
        project_id: str,
        query: SearchQuery,
    ) -> SearchResponse:
        """搜索候选论文并直接入库（papers_pool + papers + queries + paper_queries + Qdrant）"""
        results = self.search_papers(query)

        # 写 queries 表
        query_id = self._ensure_query(query.query)

        # 遍历结果，直接入库
        imported = []
        for r in results:
            meta = search_result_to_meta(r)
            scores = {
                "dense_score": r.dense_score,
                "quality_score": r.quality_score,
            }
            pool_pid = r.source_payload.get("pool_paper_id", "")
            paper = self.add_paper_metadata(
                project_id, meta, source=r.source, scores=scores,
                topic=query.query, pool_paper_id=pool_pid, query_id=query_id,
            )
            if paper:
                imported.append(paper)
                self._link_paper_query(paper.paper_id, query_id, r.final_score, "candidate")

        # 写 Qdrant search_queries 向量
        self._save_query_vector(query_id, query.query)

        # 写 Qdrant paper_profiles 向量
        if imported:
            self._index_paper_profiles(imported)

        logger.info(f"Search & import: {len(imported)} papers imported")
        return SearchResponse(
            query=query,
            results=results,
            total_count=len(results),
        )

    def _ensure_query(self, query_text: str) -> str:
        """确保查询存在于 queries 表，返回 query_id（去重）"""
        if not self.pg:
            # 无 PG 时跳过
            query_id = f"qry_{uuid.uuid4().hex[:8]}"
            return query_id

        # 先查是否已存在
        existing = self.pg.query("queries", {"query_text": query_text})
        if existing:
            return existing[0]["query_id"]

        # 新建
        query_id = f"qry_{uuid.uuid4().hex[:8]}"
        record = QueryRecord(query_id=query_id, query_text=query_text)
        self.pg.upsert_item("queries", query_id, record.model_dump())
        logger.debug(f"Created query: {query_id} for \"{query_text[:50]}\"")
        return query_id

    def _link_paper_query(
        self, paper_id: str, query_id: str, score: float, source: str,
    ) -> None:
        """写入 paper_queries 关联记录"""
        if not self.pg:
            return

        record = {
            "paper_id": paper_id,
            "query_id": query_id,
            "score": score,
            "source": source,
        }
        try:
            self.pg.upsert_item("paper_queries", paper_id, record)
        except Exception as e:
            logger.warning(f"Failed to link paper_query: {e}")

    def _save_query_vector(self, query_id: str, query_text: str) -> None:
        """将查询文本写入 Qdrant search_queries 集合（向量化）"""
        try:
            from src.agents_v3.research_workspace.storage.vector import get_vector_storage
            vs = get_vector_storage()
            vs.add_search_query(query_id, query_text)
        except Exception as e:
            logger.warning(f"Failed to save query vector to Qdrant: {e}")

    # ── 主题相关重要性得分 ──────────────────────────────────

    def save_topic_score(
        self,
        paper_id: str,
        topic: str,
        scores: dict[str, float],
        query_id: str = "",
    ) -> None:
        """保存论文在特定主题下的重要性得分"""
        from datetime import datetime as _dt

        score_record = {
            "paper_id": paper_id,
            "topic": topic,
            "query_id": query_id or None,
            "dense_score": scores.get("dense_score", 0.0),
            "quality_score": scores.get("quality_score", 0.0),
            "scored_at": _dt.now().isoformat(),
        }

        # 读取现有记录，按 paper_id + topic 去重更新
        records = self.storage.load_collection("topic_scores")
        updated = False
        for i, rec in enumerate(records):
            if rec.get("paper_id") == paper_id and rec.get("topic") == topic:
                records[i] = score_record
                updated = True
                break
        if not updated:
            records.append(score_record)

        self.storage.save_collection("topic_scores", records)
        logger.debug(f"Saved topic score: {paper_id} @ {topic[:30]} = {scores.get('dense_score', 0):.3f}")

    def get_topic_scores(
        self,
        project_id: str,
        topic: str,
    ) -> list[dict[str, Any]]:
        """获取某主题下所有论文的相关性得分

        返回按 dense_score 降序排列的得分记录列表。
        """
        paper_ids = {p.paper_id for p in self.list_papers(project_id)}
        records = self.storage.load_collection("topic_scores")
        matched = [
            r for r in records
            if r.get("paper_id") in paper_ids and r.get("topic") == topic
        ]
        matched.sort(key=lambda r: r.get("dense_score", 0), reverse=True)
        return matched

    def get_paper_topic_scores(
        self,
        paper_id: str,
    ) -> list[dict[str, Any]]:
        """获取某篇论文在所有主题下的得分"""
        records = self.storage.load_collection("topic_scores")
        return [r for r in records if r.get("paper_id") == paper_id]

    def recompute_topic_scores(
        self,
        project_id: str,
        topic: str,
    ) -> list[dict[str, Any]]:
        """重新计算某主题下所有论文的质量得分

        基于引用数、引用速度、发表时间计算 quality_score。
        返回更新后的得分记录列表。
        """
        from src.agents_v3.research_workspace.search.base import SearchResult
        from src.agents_v3.research_workspace.search.quality_filter import compute_quality_batch

        papers = self.list_papers(project_id)
        if not papers:
            return []

        # 将 Paper 转换为 SearchResult 用于评分
        results = []
        for p in papers:
            r = SearchResult(
                result_id=p.paper_id,
                source=p.source_platform or "unknown",
                title=p.title,
                authors=[a.name for a in p.authors],
                year=p.dates.year,
                venue=p.source.venue,
                abstract=p.abstract,
                doi=p.identifiers.doi,
                arxiv_id=p.identifiers.arxiv_id,
                pubmed_id=p.identifiers.pubmed_id,
                semantic_scholar_id=p.identifiers.semantic_scholar_id,
                openalex_id=p.identifiers.openalex_id,
                citations=p.citation.citation_count,
                topics=p.classification.topics,
                keywords=p.classification.keywords,
            )
            results.append(r)

        # 计算质量分
        quality_scores = compute_quality_batch(results)

        # 持久化分数
        scored_records = []
        for i, r in enumerate(results):
            scores = {
                "dense_score": 0.0,
                "quality_score": quality_scores[i],
            }
            self.save_topic_score(r.result_id, topic, scores)
            scored_records.append({
                "paper_id": r.result_id,
                "topic": topic,
                "dense_score": 0.0,
                "quality_score": quality_scores[i],
            })

        logger.info(f"Recomputed topic scores for {len(scored_records)} papers @ {topic[:30]}")
        return scored_records
