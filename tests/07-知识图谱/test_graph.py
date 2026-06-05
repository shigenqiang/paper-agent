"""模块07 知识图谱 — 真实 PostgreSQL

前置条件:
    - Docker 容器 paper-agent-postgres 运行中
    - 至少有证据记录和已解析论文
"""

import pytest

from src.agents_v3.research_workspace.models.enums import NodeType
from src.agents_v3.research_workspace.services.graph_service import (
    GraphService,
    _levenshtein,
    _cosine_similarity,
    classify_limitation_type,
    compute_gap_confidence,
    resolve_alias,
)


# ── 工具函数测试 ──────────────────────────────────

class TestUtilityFunctions:

    def test_levenshtein_identical(self):
        assert _levenshtein("abc", "abc") == 0

    def test_levenshtein_single_edit(self):
        assert _levenshtein("abc", "ab") == 1
        assert _levenshtein("abc", "abcd") == 1
        assert _levenshtein("abc", "adc") == 1

    def test_levenshtein_symmetric(self):
        assert _levenshtein("kitten", "sitting") == _levenshtein("sitting", "kitten")

    def test_cosine_similarity_identical(self):
        v = [1.0, 2.0, 3.0]
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_cosine_similarity_zero_vector(self):
        assert _cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_classify_limitation_type_sample_size(self):
        assert classify_limitation_type("small sample size") == "sample_size"

    def test_classify_limitation_type_unknown(self):
        assert classify_limitation_type("random text") == "unknown"

    def test_compute_gap_confidence_high(self):
        conf = compute_gap_confidence(
            ["future_work", "possible_gap"], "high", 3, True,
        )
        assert conf >= 0.7

    def test_compute_gap_confidence_low(self):
        conf = compute_gap_confidence([], "low", 0, False)
        assert conf <= 0.4

    def test_resolve_alias_known(self):
        assert resolve_alias("llms") == "llm"
        assert resolve_alias("cnns") == "cnn"

    def test_resolve_alias_unknown(self):
        assert resolve_alias("unknown_term_xyz") == "unknown_term_xyz"


# ── GraphService E2E ──────────────────────────────

class TestGraphServiceE2E:
    """GraphService 真实链路测试"""

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = GraphService(storage=pg_storage)

    def _get_test_project_id(self, pg_storage):
        """获取一个有数据的 project_id"""
        evidence = pg_storage.list_all("evidence_records")
        if evidence:
            return evidence[0].get("project_id", "")
        papers = pg_storage.list_all("papers")
        if papers:
            return papers[0].get("project_id", "")
        pytest.skip("数据库中无数据")

    # ── 构建 ──

    def test_build_project_graph(self, pg_storage):
        """构建项目知识图谱"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid)
        assert graph is not None
        assert graph.project_id == pid
        print(f"\n[graph] 项目 {pid}: {len(graph.nodes)} 节点, {len(graph.edges)} 边")

    def test_build_graph_nodes_have_ids(self, pg_storage):
        """图谱节点应有稳定 ID"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid)
        for node in graph.nodes:
            assert node.node_id
            assert node.label

    def test_build_graph_edges_have_types(self, pg_storage):
        """图谱边应有类型"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid)
        for edge in graph.edges:
            assert edge.edge_type

    # ── 查询 ──

    def test_get_graph(self, pg_storage):
        """读取已构建的图谱"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid)
        graph = self.service.get_graph(pid)
        assert graph.project_id == pid

    def test_get_stats(self, pg_storage):
        """获取图谱统计"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid)
        stats = self.service.get_stats(pid)
        assert "total_nodes" in stats
        assert "total_edges" in stats
        assert "node_type_counts" in stats

    def test_get_node(self, pg_storage):
        """获取节点详情"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid)
        if graph.nodes:
            node = self.service.get_node(pid, graph.nodes[0].node_id)
            assert node is not None

    def test_get_neighbors(self, pg_storage):
        """获取邻居节点"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid)
        if graph.nodes:
            result = self.service.get_neighbors(pid, graph.nodes[0].node_id, hops=1)
            assert "nodes" in result
            assert "edges" in result

    def test_search_nodes(self, pg_storage):
        """搜索节点"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid)
        results = self.service.search_nodes(pid, "test")
        assert isinstance(results, list)

    def test_find_gaps(self, pg_storage):
        """查找 Gap"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid)
        gaps = self.service.find_gaps(pid, min_confidence=0.0)
        assert isinstance(gaps, list)

    def test_validate_graph(self, pg_storage):
        """校验图谱可追溯性"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid)
        result = self.service.validate_graph_traceability(pid)
        assert "valid" in result
        assert "metrics" in result

    def test_build_graph_summary(self, pg_storage):
        """构建图谱摘要"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid)
        summary = self.service.build_graph_summary(pid)
        assert "top_topics" in summary or "total_papers" in summary

    # ── 新增功能 ──

    def test_quality_metrics(self, pg_storage):
        """G13 质量评估指标"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid)
        metrics = self.service.compute_quality_metrics(pid)
        assert "coverage" in metrics
        assert "entity_quality" in metrics
        assert "structure" in metrics

    def test_author_nodes(self, pg_storage):
        """Author 节点和 AUTHORED_BY 边"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid)
        author_nodes = [n for n in graph.nodes if n.node_type.value == "Author"]
        authored_edges = [e for e in graph.edges if e.edge_type.value == "AUTHORED_BY"]
        print(f"\n[authors] {len(author_nodes)} authors, {len(authored_edges)} AUTHORED_BY edges")
        # 如果论文有作者数据，应该有 Author 节点
        if any(p.get("authors") for p in self.service.storage.query("papers", {"project_id": pid})):
            assert len(author_nodes) > 0

    def test_cites_edges(self, pg_storage):
        """CITES 边和 GhostPaper 节点"""
        pid = self._get_test_project_id(pg_storage)
        graph = self.service.build_project_graph(pid)
        cites_edges = [e for e in graph.edges if e.edge_type.value == "CITES"]
        ghost_nodes = [n for n in graph.nodes if n.node_type == NodeType.GHOST_PAPER]
        print(f"\n[citations] {len(cites_edges)} CITES edges, {len(ghost_nodes)} GhostPaper nodes")

    def test_community_detection(self, pg_storage):
        """G11 社区检测"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid)
        result = self.service.detect_communities(pid)
        assert "communities" in result
        assert "total_assigned" in result
        print(f"\n[communities] {result['communities']} communities, {result['total_assigned']} nodes assigned")

    def test_enhanced_gap_detection(self, pg_storage):
        """G6 增强 Gap 检测"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid)
        result = self.service.find_research_gaps_enhanced(pid)
        assert "gaps" in result
        assert "method_dataset_matrix" in result
        assert "sparse_regions" in result

    def test_incremental_update(self, pg_storage):
        """G12 增量更新"""
        pid = self._get_test_project_id(pg_storage)
        # 先全量构建
        self.service.build_project_graph(pid)
        # 增量更新（空列表应返回原图）
        graph = self.service.incremental_update(pid, [])
        assert graph.project_id == pid

    def test_entity_merge(self, pg_storage):
        """G9 实体消歧"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid)
        result = self.service.merge_similar_entities(pid)
        assert "merged_pairs" in result

    def test_consensus_meter(self, pg_storage):
        """Consensus Meter"""
        pid = self._get_test_project_id(pg_storage)
        self.service.build_project_graph(pid)
        result = self.service.build_consensus_meter(pid)
        assert isinstance(result, list)


# ── SPECTER2 Provider 测试 ──────────────────────────

def _specter2_available() -> bool:
    """快速检查 SPECTER2 模型是否可加载（本地缓存或网络可用）"""
    import os
    # 检查本地缓存是否存在
    cache_home = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
    if os.path.isdir(cache_home):
        for name in os.listdir(cache_home):
            if "specter2" in name.lower():
                return True
    # 快速网络检测（2 秒超时）
    try:
        import urllib.request
        urllib.request.urlopen("https://huggingface.co", timeout=2)
        return True
    except Exception:
        return False


class TestSPECTER2Provider:
    """SPECTER2 学术文本 Embedding Provider 测试"""

    def test_import_specter2_provider(self):
        """SPECTER2Provider 可以正常 import"""
        from src.agents_v3.research_workspace.storage.embedding_provider import (
            SPECTER2Provider,
            get_specter2_provider,
            reset_specter2_provider,
        )
        assert SPECTER2Provider is not None
        assert callable(get_specter2_provider)
        assert callable(reset_specter2_provider)

    def test_specter2_dimension(self):
        """SPECTER2 输出维度应为 768"""
        if not _specter2_available():
            pytest.skip("SPECTER2 模型不可用（网络或缓存）")
        from src.agents_v3.research_workspace.storage.embedding_provider import (
            SPECTER2Provider,
            reset_specter2_provider,
        )
        reset_specter2_provider()
        try:
            provider = SPECTER2Provider()
            assert provider.dimension == 768
        finally:
            reset_specter2_provider()

    def test_specter2_embed_texts(self):
        """SPECTER2 embed_texts 返回正确维度"""
        if not _specter2_available():
            pytest.skip("SPECTER2 模型不可用（网络或缓存）")
        from src.agents_v3.research_workspace.storage.embedding_provider import (
            SPECTER2Provider,
            reset_specter2_provider,
        )
        reset_specter2_provider()
        try:
            provider = SPECTER2Provider()
            texts = ["transformer attention mechanism", "BERT pre-training"]
            embeddings = provider.embed_texts(texts)
            assert len(embeddings) == 2
            assert len(embeddings[0]) == 768
            assert len(embeddings[1]) == 768
        finally:
            reset_specter2_provider()

    def test_specter2_embed_query(self):
        """SPECTER2 embed_query 返回 768 维向量"""
        if not _specter2_available():
            pytest.skip("SPECTER2 模型不可用（网络或缓存）")
        from src.agents_v3.research_workspace.storage.embedding_provider import (
            SPECTER2Provider,
            reset_specter2_provider,
        )
        reset_specter2_provider()
        try:
            provider = SPECTER2Provider()
            vec = provider.embed_query("knowledge graph completion")
            assert len(vec) == 768
        finally:
            reset_specter2_provider()
