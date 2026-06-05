"""端到端 Pipeline 测试报告 — 真实 PDF 数据验证

测试日期: 2026-06-05
测试项目: proj_a01b65e0 (15 篇论文, 9 个真实 PDF)
测试环境: PostgreSQL + Qdrant Cloud + MiMo v2.5-pro

================================================================
Pipeline 各阶段产出
================================================================

阶段              产出                                  LLM 调用
────────────────────────────────────────────────────────────────
PDF 解析          7 篇论文, 21 sections, 25+ chunks/篇   无
元数据提取        title/abstract/authors 从 PDF 提取      无
实体提取          184 实体, 132 关系                      13 次
论文卡片          7 张 (topics/findings/limitations)      7 次
证据表            22-30 条证据记录                        无
知识图谱          249 节点, 346 边                        无
社区检测          3-12 个社区                             无

================================================================
Token 消耗
================================================================

实体提取 (13 sections × ~13.5K tokens/section):  ~176K input
论文卡片 (7 cards × ~2K input + ~500 output):    ~28K input, ~3.5K output
总计:  ~216K tokens

================================================================
时间消耗
================================================================

PDF 解析 (7 篇):        ~2-5 min
实体提取 (13 sections):  ~6-10 min
论文卡片 (7 张):         ~3-5 min
证据表 + 图谱构建:       ~5 sec
总计:  ~12-18 min

================================================================
图谱质量指标 (修复后)
================================================================

节点: 249, 边: 346
节点类型: Paper(15), Finding(73), Method(49), Topic(39),
          Dataset(30), Task(17), Limitation(14), Metric(9), Gap(3)
边类型: REPORTS_FINDING(81), USES_METHOD(57), EVALUATED_ON(46),
        USES_DATASET(35), BELONGS_TO_TOPIC(25), STUDIES_TASK(25),
        HAS_LIMITATION(23), USED_FOR(7), COMPARE(7), EXTENDS(4)

Paper 节点有 title:  15/15 (修复前 0/15)
边引用缺失节点:      0 (修复前 276)
结构性验证错误:      0 (修复前 276)
可追溯性:            98.72%
孤立非 Paper 节点:   1.28%
重复实体率:          0.44%
平均度数:            2.78

================================================================
修复的问题
================================================================

1. Parser 不提取元数据
   → 添加 _extract_and_update_metadata() 从 PDF 提取 title/authors/abstract
   → 读写 papers_pool 表而非 papers 表

2. paper_cards 表 schema 不匹配
   → paper_cards 表只有 extraction JSONB 列
   → 将完整卡片数据存入 extraction 字段
   → 修复 _get_active_card / to_paper_cards / evidence_table 读取逻辑

3. active vs is_active 列名不一致
   → paper_cards 表用 is_active, 代码查询用 active
   → 统一为 is_active

4. Paper 节点无 title
   → build_project_graph 从 papers 表读取, 但 papers 表无 title 列
   → 改为从 papers_pool 读取完整元数据

5. 边引用不存在的节点 (276 条)
   → Finding/Limitation 节点 ID 用 {type}:{pid}:{hash}
   → entity_name_to_id 用 {type}:{hash}, 不一致
   → 统一为 {type}:{hash}
   → _add_relation_edge 增加节点存在性检查

6. API token 过期
   → 更新 .env 中的 OPENAI_API_KEY
"""

from __future__ import annotations

import os
import time
from collections import Counter
from typing import Any

import pytest

# ── 跳过条件 ──────────────────────────────────────────────
# 运行方式: RUN_E2E_TESTS=1 pytest tests/07-知识图谱/test_pipeline_e2e.py -v
pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_E2E_TESTS"),
    reason="E2E tests require RUN_E2E_TESTS=1 and real DB/API",
)


def _get_storage():
    from src.agents_v3.research_workspace.storage import get_storage
    return get_storage()


def _get_project_id() -> str:
    return "proj_a01b65e0"


# ── 1. PDF 解析 ──────────────────────────────────────────


class TestPDFParsing:
    """PDF 解析阶段验证"""

    def test_papers_parsed(self):
        """验证论文已解析"""
        s = _get_storage()
        papers = s.query("papers", {"project_id": _get_project_id()})
        parsed = [p for p in papers if p.get("status") in ("parsed", "card_ready", "evidence_ready")]
        assert len(parsed) >= 5, f"Expected >=5 parsed papers, got {len(parsed)}"

    def test_paper_metadata_extracted(self):
        """验证元数据已从 PDF 提取"""
        s = _get_storage()
        papers = s.query("papers", {"project_id": _get_project_id()})
        parsed = [p for p in papers if p.get("status") in ("parsed", "card_ready", "evidence_ready")]
        papers_with_title = 0
        for p in parsed:
            pool = s.get_item("papers_pool", p["paper_id"])
            if pool and pool.get("title") and pool["title"] != "?":
                papers_with_title += 1
        assert papers_with_title >= 4, f"Expected >=4 papers with title, got {papers_with_title}"

    def test_sections_created(self):
        """验证 sections 已创建"""
        s = _get_storage()
        sections = s.list_all("paper_sections")
        assert len(sections) >= 10, f"Expected >=10 sections, got {len(sections)}"

    def test_sections_have_text(self):
        """验证 sections 有真实文本内容"""
        s = _get_storage()
        sections = s.list_all("paper_sections")
        sections_with_text = [sec for sec in sections if len(sec.get("text", "") or "") > 100]
        assert len(sections_with_text) >= 5

    def test_chunks_created(self):
        """验证 chunks 已创建"""
        s = _get_storage()
        chunks = s.list_all("paper_chunks")
        assert len(chunks) >= 20


# ── 2. 实体提取 ──────────────────────────────────────────


class TestEntityExtraction:
    """LLM 实体提取阶段验证"""

    def test_sections_extracted(self):
        """验证 sections 已完成 LLM 提取"""
        s = _get_storage()
        sections = s.list_all("paper_sections")
        extracted = [sec for sec in sections if sec.get("extraction_status") == "done"]
        assert len(extracted) >= 5

    def test_entities_extracted(self):
        """验证实体已提取"""
        s = _get_storage()
        sections = s.list_all("paper_sections")
        extracted = [sec for sec in sections if sec.get("extraction_status") == "done"]
        total_entities = sum(len(sec.get("entities", []) or []) for sec in extracted)
        assert total_entities >= 50

    def test_relations_extracted(self):
        """验证关系已提取"""
        s = _get_storage()
        sections = s.list_all("paper_sections")
        extracted = [sec for sec in sections if sec.get("extraction_status") == "done"]
        total_relations = sum(len(sec.get("relations", []) or []) for sec in extracted)
        assert total_relations >= 30

    def test_entity_types_diverse(self):
        """验证实体类型多样性"""
        s = _get_storage()
        sections = s.list_all("paper_sections")
        extracted = [sec for sec in sections if sec.get("extraction_status") == "done"]
        entity_types = set()
        for sec in extracted:
            for entity in sec.get("entities", []) or []:
                etype = entity.get("type", "")
                if etype:
                    entity_types.add(etype)
        assert len(entity_types) >= 3


# ── 3. 论文卡片 ──────────────────────────────────────────


class TestPaperCards:
    """论文卡片生成阶段验证"""

    def test_cards_generated(self):
        """验证论文卡片已生成"""
        s = _get_storage()
        cards = s.query("paper_cards", {})
        assert len(cards) >= 5

    def test_cards_have_topics(self):
        """验证卡片有 topics"""
        s = _get_storage()
        cards = s.query("paper_cards", {})
        cards_with_topics = 0
        for card in cards:
            extraction = card.get("extraction", {})
            if isinstance(extraction, dict) and extraction.get("topics"):
                cards_with_topics += 1
        assert cards_with_topics >= 3

    def test_card_extraction_field_populated(self):
        """验证 extraction JSONB 字段有数据"""
        s = _get_storage()
        cards = s.query("paper_cards", {})
        populated = sum(1 for c in cards if isinstance(c.get("extraction"), dict) and c["extraction"].get("card_id"))
        assert populated >= 5


# ── 4. 证据表 ────────────────────────────────────────────


class TestEvidenceTable:
    """证据表构建阶段验证"""

    def test_evidence_records_created(self):
        """验证证据记录已创建"""
        s = _get_storage()
        evidence = s.list_all("evidence_records")
        assert len(evidence) >= 10

    def test_evidence_has_paper_id(self):
        """验证证据记录有 paper_id"""
        s = _get_storage()
        evidence = s.list_all("evidence_records")
        for ev in evidence[:5]:
            assert ev.get("paper_id")


# ── 5. 知识图谱 ──────────────────────────────────────────


class TestKnowledgeGraph:
    """知识图谱构建阶段验证"""

    def test_graph_built(self):
        """验证图谱已构建"""
        s = _get_storage()
        graph_data = s.get_item("graphs", _get_project_id())
        assert graph_data
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        assert len(nodes) >= 100
        assert len(edges) >= 100

    def test_paper_nodes_have_title(self):
        """验证 Paper 节点有 title (修复后)"""
        s = _get_storage()
        graph_data = s.get_item("graphs", _get_project_id())
        nodes = graph_data.get("nodes", [])
        paper_nodes = [n for n in nodes if n.get("node_type") == "Paper"]
        papers_with_title = [
            n for n in paper_nodes
            if n.get("properties", {}).get("title") and n["properties"]["title"] != "?"
        ]
        assert len(papers_with_title) == len(paper_nodes), (
            f"{len(papers_with_title)}/{len(paper_nodes)} Paper nodes have title"
        )

    def test_no_broken_edge_references(self):
        """验证边没有引用不存在的节点 (修复后)"""
        s = _get_storage()
        graph_data = s.get_item("graphs", _get_project_id())
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        node_ids = {n["node_id"] for n in nodes}
        broken = [e for e in edges if e["source_id"] not in node_ids or e["target_id"] not in node_ids]
        assert len(broken) == 0, f"{len(broken)} edges reference missing nodes"

    def test_node_type_diversity(self):
        """验证节点类型多样性"""
        s = _get_storage()
        graph_data = s.get_item("graphs", _get_project_id())
        nodes = graph_data.get("nodes", [])
        node_types = set(n.get("node_type", "") for n in nodes)
        assert len(node_types) >= 5

    def test_edge_type_diversity(self):
        """验证边类型多样性"""
        s = _get_storage()
        graph_data = s.get_item("graphs", _get_project_id())
        edges = graph_data.get("edges", [])
        edge_types = set(e.get("edge_type", "") for e in edges)
        assert len(edge_types) >= 5

    def test_finding_nodes_exist(self):
        """验证 Finding 节点存在"""
        s = _get_storage()
        graph_data = s.get_item("graphs", _get_project_id())
        nodes = graph_data.get("nodes", [])
        finding_nodes = [n for n in nodes if n.get("node_type") == "Finding"]
        assert len(finding_nodes) >= 10

    def test_method_nodes_exist(self):
        """验证 Method 节点存在"""
        s = _get_storage()
        graph_data = s.get_item("graphs", _get_project_id())
        nodes = graph_data.get("nodes", [])
        method_nodes = [n for n in nodes if n.get("node_type") == "Method"]
        assert len(method_nodes) >= 10

    def test_traceability(self):
        """验证节点可追溯性"""
        s = _get_storage()
        graph_data = s.get_item("graphs", _get_project_id())
        nodes = graph_data.get("nodes", [])
        non_paper = [n for n in nodes if n.get("node_type") != "Paper"]
        traceable = [
            n for n in non_paper
            if n.get("properties", {}).get("paper_ids")
            or n.get("properties", {}).get("evidence_ids")
        ]
        rate = len(traceable) / len(non_paper) if non_paper else 1.0
        assert rate >= 0.5


# ── 6. 社区检测 ──────────────────────────────────────────


class TestCommunityDetection:
    """社区检测验证"""

    def test_communities_detected(self):
        from src.agents_v3.research_workspace.services.graph_service import GraphService
        s = _get_storage()
        svc = GraphService(storage=s)
        communities = svc.detect_communities(_get_project_id())
        assert len(communities) >= 1


# ── 7. 质量指标 ──────────────────────────────────────────


class TestQualityMetrics:
    """图谱质量指标验证"""

    def test_quality_metrics_computable(self):
        from src.agents_v3.research_workspace.services.graph_service import GraphService
        s = _get_storage()
        svc = GraphService(storage=s)
        qm = svc.compute_quality_metrics(_get_project_id())
        assert "coverage" in qm
        assert "entity_quality" in qm
        assert "structure" in qm

    def test_avg_degree(self):
        from src.agents_v3.research_workspace.services.graph_service import GraphService
        s = _get_storage()
        svc = GraphService(storage=s)
        qm = svc.compute_quality_metrics(_get_project_id())
        assert qm["structure"]["avg_degree"] >= 1.0


# ── 8. 端到端 Pipeline 耗时 ──────────────────────────────


class TestPipelinePerformance:
    """Pipeline 性能指标验证"""

    def test_token_usage_report(self):
        """输出 Token 使用报告"""
        s = _get_storage()
        sections = s.list_all("paper_sections")
        extracted = [sec for sec in sections if sec.get("extraction_status") == "done"]
        total_chars = sum(len(sec.get("text", "") or "") for sec in extracted)
        est_input_tokens = total_chars // 4
        total_entities = sum(len(sec.get("entities", []) or []) for sec in extracted)
        total_relations = sum(len(sec.get("relations", []) or []) for sec in extracted)
        cards = s.query("paper_cards", {})
        est_card_input = len(cards) * 2000
        est_card_output = len(cards) * 500
        total_input = est_input_tokens + est_card_input
        total_output = est_card_output + total_entities * 20 + total_relations * 10

        report = f"""
=== Pipeline Token Usage Report ===
Sections extracted: {len(extracted)}
Total text: {total_chars:,} chars
Est. entity extraction input: ~{est_input_tokens:,} tokens
Est. card generation input:   ~{est_card_input:,} tokens
Est. card generation output:  ~{est_card_output:,} tokens
Total input tokens:  ~{total_input:,}
Total output tokens: ~{total_output:,}
Total tokens:        ~{total_input + total_output:,}
Entities: {total_entities}, Relations: {total_relations}
"""
        print(report)
        assert total_input > 0

    def test_graph_size_report(self):
        """输出图谱规模报告"""
        s = _get_storage()
        graph_data = s.get_item("graphs", _get_project_id())
        assert graph_data
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        node_types = Counter(n.get("node_type", "?") for n in nodes)
        edge_types = Counter(e.get("edge_type", "?") for e in edges)
        report = f"""
=== Knowledge Graph Report ===
Nodes: {len(nodes)}
Edges: {len(edges)}
Node types: {dict(node_types)}
Edge types: {dict(edge_types)}
"""
        print(report)
        assert len(nodes) > 0
