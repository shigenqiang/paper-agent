"""三层渐进式检索服务：L0 paper_profiles → L1 paper_sections → L2 paper_chunks"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field
from loguru import logger


class RetrievalResult(BaseModel):
    """单条检索结果，含完整层级上下文"""

    chunk_id: str
    paper_id: str
    section_id: str = ""
    chunk_text: str = ""
    section_title: str = ""
    section_type: str = ""
    paper_title: str = ""
    dense_score: float = 0.0
    layer_scores: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalDiagnostics(BaseModel):
    """检索诊断信息"""

    l0_candidates: int = 0
    l0_selected: int = 0
    l1_candidates: int = 0
    l1_selected: int = 0
    l2_candidates: int = 0
    l2_selected: int = 0
    fallback_used: bool = False
    fallback_reason: str = ""
    duration_ms: int = 0


class HierarchicalRetriever:
    """渐进式 L0 → L1 → L2 检索服务"""

    def __init__(self, storage=None):
        from src.agents_v3.research_workspace.storage import get_storage
        self.storage = storage or get_storage()

    # ── 延迟加载存储服务 ──

    def _get_vector_storage(self):
        from src.agents_v3.research_workspace.storage.vector import get_vector_storage
        return get_vector_storage()

    def _get_embedding_service(self):
        from src.agents_v3.research_workspace.storage.embedding_provider import get_embedding_provider
        return get_embedding_provider()

    # ── 主入口 ──

    def retrieve(
        self,
        query_text: str,
        project_id: str,
        top_k_papers: int = 10,
        top_k_sections: int = 20,
        top_k_chunks: int = 30,
        paper_ids: list[str] | None = None,
        fusion: str = "rrf",
    ) -> tuple[list[RetrievalResult], RetrievalDiagnostics]:
        """渐进式检索：L0 → L1 → L2

        Args:
            query_text: 查询文本
            project_id: 项目 ID
            top_k_papers: L0 层返回的论文数
            top_k_sections: L1 层返回的章节数
            top_k_chunks: L2 层返回的 chunk 数
            paper_ids: 可选的论文 ID 预过滤（来自 Scope）
            fusion: 融合方式，"rrf" 或 "dbsf"

        Returns:
            (检索结果列表, 诊断信息)
        """
        start = time.time()
        diag = RetrievalDiagnostics()

        vector_storage = self._get_vector_storage()
        use_inference = vector_storage.use_inference

        # 生成查询向量
        dense_emb, sparse_emb = self._embed_query(query_text, use_inference)

        # ── L0: 搜 paper_profiles ──
        l0_results = self._search_l0(
            query_text, dense_emb, sparse_emb,
            project_id, paper_ids, top_k_papers, fusion, use_inference,
        )
        diag.l0_candidates = len(l0_results)

        if not l0_results:
            # L0 为空，回退到 L2 直搜
            logger.info("L0 returned 0 results, falling back to flat L2 search")
            results, diag = self.retrieve_flat_fallback(
                query_text, project_id, top_k_chunks, paper_ids, use_inference,
            )
            diag.fallback_used = True
            diag.fallback_reason = "L0 paper_profiles returned 0 results"
            diag.duration_ms = int((time.time() - start) * 1000)
            return results, diag

        l0_paper_ids = [r["id"] for r in l0_results]
        diag.l0_selected = len(l0_paper_ids)

        # ── L1: 搜 paper_sections（用 L0 的 paper_ids 过滤） ──
        l1_results = self._search_l1(
            query_text, dense_emb, sparse_emb,
            l0_paper_ids, top_k_sections, fusion, use_inference,
        )
        diag.l1_candidates = len(l1_results)

        if not l1_results:
            # L1 为空，用 L0 的 paper_ids 直接搜 L2
            logger.info("L1 returned 0 results, falling back to L2 with paper_ids filter")
            l2_results = self._search_l2(
                query_text, dense_emb, sparse_emb,
                section_ids=None, paper_ids=l0_paper_ids,
                top_k=top_k_chunks, fusion=fusion, use_inference=use_inference,
            )
            diag.l2_candidates = len(l2_results)
            diag.l2_selected = len(l2_results)
            diag.fallback_used = True
            diag.fallback_reason = "L1 paper_sections returned 0 results"

            results = self._enrich_with_context(l2_results, [], l0_results)
            diag.duration_ms = int((time.time() - start) * 1000)
            return results, diag

        l1_section_ids = [r["id"] for r in l1_results]
        diag.l1_selected = len(l1_section_ids)

        # ── L2: 搜 paper_chunks（用 L1 的 section_ids 过滤） ──
        l2_results = self._search_l2(
            query_text, dense_emb, sparse_emb,
            section_ids=l1_section_ids, paper_ids=l0_paper_ids,
            top_k=top_k_chunks, fusion=fusion, use_inference=use_inference,
        )
        diag.l2_candidates = len(l2_results)
        diag.l2_selected = len(l2_results)

        # 如果 L2 section_id 过滤后结果太少，用 paper_ids 回退
        if len(l2_results) < top_k_chunks // 3:
            logger.info(f"L2 section_id filter returned only {len(l2_results)} results, retrying with paper_ids only")
            l2_fallback = self._search_l2(
                query_text, dense_emb, sparse_emb,
                section_ids=None, paper_ids=l0_paper_ids,
                top_k=top_k_chunks, fusion=fusion, use_inference=use_inference,
            )
            if len(l2_fallback) > len(l2_results):
                l2_results = l2_fallback
                diag.l2_selected = len(l2_results)

        results = self._enrich_with_context(l2_results, l1_results, l0_results)
        diag.duration_ms = int((time.time() - start) * 1000)
        return results, diag

    # ── L0/L1/L2 搜索 ──

    def _embed_query(
        self, query_text: str, use_inference: bool,
    ) -> tuple[list[float], dict[int, float]]:
        """生成查询的 dense + sparse 嵌入"""
        if use_inference:
            # 云端推理模式：search_hybrid_by_text 会自动处理，这里返回空占位
            return [], {}

        embedding_service = self._get_embedding_service()
        dense_emb = embedding_service.embed_query(query_text)
        # 简单的词频作为 sparse 向量（与 add_chunks 中的逻辑一致）
        sparse_emb: dict[int, float] = {}
        try:
            sparse_emb = embedding_service.embed_sparse(query_text)
        except (AttributeError, Exception):
            pass
        return dense_emb, sparse_emb

    def _search_l0(
        self,
        query_text: str,
        dense_emb: list[float],
        sparse_emb: dict[int, float],
        project_id: str,
        paper_ids: list[str] | None,
        top_k: int,
        fusion: str,
        use_inference: bool,
    ) -> list[dict[str, Any]]:
        """L0: 搜索 paper_profiles，用 project_id 过滤"""
        vector_storage = self._get_vector_storage()
        where = {"project_id": project_id}
        if paper_ids:
            where["paper_id"] = paper_ids

        if use_inference:
            return vector_storage.search_hybrid_by_text(
                query_text, top_k=top_k, collection="paper_profiles",
                fusion=fusion, where=where,
            )
        else:
            if not dense_emb:
                return []
            return vector_storage.search_hybrid(
                dense_emb, sparse_emb, top_k=top_k,
                collection="paper_profiles", fusion=fusion, where=where,
            )

    def _search_l1(
        self,
        query_text: str,
        dense_emb: list[float],
        sparse_emb: dict[int, float],
        paper_ids: list[str],
        top_k: int,
        fusion: str,
        use_inference: bool,
    ) -> list[dict[str, Any]]:
        """L1: 搜索 paper_sections，用 L0 的 paper_ids 过滤"""
        vector_storage = self._get_vector_storage()

        if use_inference:
            return vector_storage.search_hybrid_by_text(
                query_text, top_k=top_k, paper_ids=paper_ids,
                collection="paper_sections", fusion=fusion,
            )
        else:
            if not dense_emb:
                return []
            return vector_storage.search_hybrid(
                dense_emb, sparse_emb, top_k=top_k, paper_ids=paper_ids,
                collection="paper_sections", fusion=fusion,
            )

    def _search_l2(
        self,
        query_text: str,
        dense_emb: list[float],
        sparse_emb: dict[int, float],
        section_ids: list[str] | None,
        paper_ids: list[str] | None,
        top_k: int,
        fusion: str,
        use_inference: bool,
    ) -> list[dict[str, Any]]:
        """L2: 搜索 paper_chunks，用 section_ids 或 paper_ids 过滤"""
        vector_storage = self._get_vector_storage()
        where: dict[str, Any] = {}
        if section_ids:
            where["section_id"] = section_ids

        if use_inference:
            return vector_storage.search_hybrid_by_text(
                query_text, top_k=top_k, paper_ids=paper_ids,
                collection="paper_chunks", fusion=fusion, where=where or None,
            )
        else:
            if not dense_emb:
                return []
            return vector_storage.search_hybrid(
                dense_emb, sparse_emb, top_k=top_k, paper_ids=paper_ids,
                collection="paper_chunks", fusion=fusion, where=where or None,
            )

    # ── 上下文合并 ──

    def _enrich_with_context(
        self,
        l2_results: list[dict[str, Any]],
        l1_results: list[dict[str, Any]],
        l0_results: list[dict[str, Any]],
    ) -> list[RetrievalResult]:
        """将 L2 chunk 结果与 L1/L0 上下文合并"""
        paper_map: dict[str, dict] = {}
        for r in l0_results:
            paper_map[r["id"]] = r

        section_map: dict[str, dict] = {}
        for r in l1_results:
            section_map[r["id"]] = r

        results = []
        for chunk in l2_results:
            meta = chunk.get("metadata", {})
            paper_id = meta.get("paper_id", "")
            section_id = meta.get("section_id", "")

            paper_info = paper_map.get(paper_id, {})
            section_info = section_map.get(section_id, {})

            paper_meta = paper_info.get("metadata", {})
            section_meta = section_info.get("metadata", {})

            results.append(RetrievalResult(
                chunk_id=chunk.get("chunk_id", ""),
                paper_id=paper_id,
                section_id=section_id,
                chunk_text=chunk.get("text", ""),
                section_title=section_meta.get("section_title", meta.get("section_title", "")),
                section_type=section_meta.get("section_type", meta.get("section_type", "")),
                paper_title=paper_meta.get("title", ""),
                dense_score=chunk.get("score", 0.0),
                layer_scores={
                    "l0": paper_info.get("score", 0.0),
                    "l1": section_info.get("score", 0.0),
                    "l2": chunk.get("score", 0.0),
                },
                metadata=meta,
            ))
        return results

    # ── 回退检索 ──

    def retrieve_flat_fallback(
        self,
        query_text: str,
        project_id: str,
        top_k: int = 30,
        paper_ids: list[str] | None = None,
        use_inference: bool = False,
    ) -> tuple[list[RetrievalResult], RetrievalDiagnostics]:
        """L0/L1 为空时的 L2 直搜回退"""
        diag = RetrievalDiagnostics(fallback_used=True)
        vector_storage = self._get_vector_storage()
        where: dict[str, Any] = {"project_id": project_id}

        if use_inference:
            l2_results = vector_storage.search_hybrid_by_text(
                query_text, top_k=top_k, paper_ids=paper_ids,
                collection="paper_chunks", where=where,
            )
        else:
            embedding_service = self._get_embedding_service()
            dense_emb = embedding_service.embed_query(query_text)
            sparse_emb: dict[int, float] = {}
            try:
                sparse_emb = embedding_service.embed_sparse(query_text)
            except (AttributeError, Exception):
                pass
            l2_results = vector_storage.search_hybrid(
                dense_emb, sparse_emb, top_k=top_k, paper_ids=paper_ids,
                collection="paper_chunks", where=where,
            )

        diag.l2_candidates = len(l2_results)
        diag.l2_selected = len(l2_results)

        # 尝试从 JSONStorage 补充 paper/section 上下文
        paper_map: dict[str, dict] = {}
        section_map: dict[str, dict] = {}
        try:
            papers = self.storage.query("papers", {"project_id": project_id})
            paper_map = {p["paper_id"]: p for p in papers}
        except Exception:
            pass
        try:
            sections = self.storage.query("paper_sections", {"project_id": project_id})
            for s in sections:
                section_map[s["section_id"]] = s
        except Exception:
            pass

        results = []
        for chunk in l2_results:
            meta = chunk.get("metadata", {})
            paper_id = meta.get("paper_id", "")
            section_id = meta.get("section_id", "")
            paper_info = paper_map.get(paper_id, {})
            section_info = section_map.get(section_id, {})

            results.append(RetrievalResult(
                chunk_id=chunk.get("chunk_id", ""),
                paper_id=paper_id,
                section_id=section_id,
                chunk_text=chunk.get("text", ""),
                section_title=section_info.get("section_title", meta.get("section_title", "")),
                section_type=section_info.get("section_type", meta.get("section_type", "")),
                paper_title=paper_info.get("title", ""),
                dense_score=chunk.get("score", 0.0),
                layer_scores={"l2": chunk.get("score", 0.0)},
                metadata=meta,
            ))

        return results, diag
