"""端到端 smoke test：项目 -> 论文 -> 卡片 -> 证据 -> 图谱 -> QA -> 报告"""

import pytest

from src.agents_v3.research_workspace.storage import JSONStorage
from src.agents_v3.research_workspace.project_service import ProjectService
from src.agents_v3.research_workspace.paper_library import PaperLibraryService
from src.agents_v3.research_workspace.paper_card import PaperCardGenerator
from src.agents_v3.research_workspace.evidence_table import EvidenceTableService
from src.agents_v3.research_workspace.graph_service import GraphService
from src.agents_v3.research_workspace.scope import RetrievalScopeService
from src.agents_v3.research_workspace.scope_qa import ScopeQAService
from src.agents_v3.research_workspace.review_generator import LiteratureReviewGenerator
from src.agents_v3.research_workspace.innovation_generator import InnovationReportGenerator
from src.agents_v3.research_workspace.report_service import ReportService
from src.agents_v3.research_workspace.models import PaperCard, SourceSpan


@pytest.fixture
def storage(tmp_path):
    return JSONStorage(data_dir=tmp_path)


class TestE2ESmoke:
    """端到端 smoke test"""

    def test_full_pipeline(self, storage):
        """完整流程：项目 -> 论文 -> 卡片 -> 证据 -> 图谱 -> QA -> 报告"""

        # 1. 创建项目
        ps = ProjectService(storage=storage)
        project = ps.create_project("大语言模型与自主学习")
        assert project.project_id.startswith("proj_")

        # 2. 添加论文
        pls = PaperLibraryService(storage=storage)
        papers = pls.add_search_results(project.project_id, [
            {"title": "LLM Feedback for Learning", "authors": ["Alice"], "year": 2024, "method": "experiment"},
            {"title": "AI Tutoring Systems", "authors": ["Bob"], "year": 2023, "method": "survey"},
            {"title": "Self-Regulated Learning with AI", "authors": ["Charlie"], "year": 2024, "method": "interview"},
        ])
        assert len(papers) == 3

        # 3. 为每篇论文创建 chunks 和卡片（跳过真实解析）
        for paper in papers:
            storage.save_collection(f"chunks_{paper.paper_id}", [
                {
                    "chunk_id": f"c_{paper.paper_id}_0",
                    "paper_id": paper.paper_id,
                    "section_title": "abstract",
                    "text": f"This paper studies {paper.title}. Found improvement.",
                    "start_char": 0,
                    "end_char": 100,
                    "token_count": 15,
                },
            ])

            card = PaperCard(
                card_id=f"card_{paper.paper_id}",
                paper_id=paper.paper_id,
                project_id=project.project_id,
                research_question="How does AI affect learning?",
                method=paper.metadata.get("method", "experiment") if hasattr(paper, 'metadata') else "experiment",
                data_or_sample="100 students",
                key_findings=[f"Improved outcomes in {paper.title}"],
                limitations=["Small sample size"],
                future_work=["Extend to other contexts"],
                topics=["AI feedback", "self-regulated learning"],
                source_spans=[
                    SourceSpan(field="key_findings", chunk_id=f"c_{paper.paper_id}_0", quote="Found improvement"),
                ],
                confidence=0.7,
            )
            storage.upsert_item("paper_cards", card.card_id, card.model_dump())

        # 4. 构建证据表
        ev_svc = EvidenceTableService(storage=storage)
        evidence = ev_svc.build_for_project(project.project_id)
        assert len(evidence) > 0

        # 5. 构建知识图谱
        graph_svc = GraphService(storage=storage)
        graph = graph_svc.build_project_graph(project.project_id)
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

        # 6. Scope QA
        qa_svc = ScopeQAService(storage=storage)
        qa_svc.llm = None  # 使用 fallback
        response = qa_svc.answer(project.project_id, "这些研究有什么不足？", {"type": "all_project"})
        assert response.answer
        assert response.scope_summary
        assert len(response.supporting_papers) > 0

        # 7. 生成文献综述
        review_gen = LiteratureReviewGenerator(storage=storage)
        review_gen.llm = None  # 使用 fallback
        review = review_gen.generate(project.project_id, {"type": "all_project"})
        assert review.content
        assert len(review.paper_ids) > 0

        # 8. 生成创新点报告
        innovation_gen = InnovationReportGenerator(storage=storage)
        innovation_gen.llm = None  # 使用 fallback
        innovation = innovation_gen.generate(project.project_id, {"type": "all_project"})
        assert innovation.content

        # 9. 导出 Markdown
        report_svc = ReportService(storage=storage)
        md = report_svc.export_markdown(review.report_id)
        assert "文献综述" in md
        assert "论文数" in md

        # 10. 验证项目统计
        stats = ps.get_project_stats(project.project_id)
        assert stats["paper_count"] == 3
        assert stats["card_count"] == 3
        assert stats["evidence_count"] > 0

    def test_scope_isolation(self, storage):
        """验证 Scope 隔离：选中论文不会引用其他论文"""

        ps = ProjectService(storage=storage)
        project = ps.create_project("测试项目")

        pls = PaperLibraryService(storage=storage)
        p1 = pls.add_paper_metadata(project.project_id, {"title": "Paper 1"}, "search")
        p2 = pls.add_paper_metadata(project.project_id, {"title": "Paper 2"}, "search")

        # 为每篇论文创建证据
        ev_svc = EvidenceTableService(storage=storage)
        storage.upsert_item("paper_cards", "card1", {
            "card_id": "card1",
            "paper_id": p1.paper_id,
            "project_id": project.project_id,
            "key_findings": ["Finding from paper 1"],
            "limitations": ["Limitation from paper 1"],
            "topics": ["topic A"],
        })
        storage.upsert_item("paper_cards", "card2", {
            "card_id": "card2",
            "paper_id": p2.paper_id,
            "project_id": project.project_id,
            "key_findings": ["Finding from paper 2"],
            "limitations": ["Limitation from paper 2"],
            "topics": ["topic B"],
        })
        ev_svc.build_for_project(project.project_id)

        # 只选中 p1
        scope_svc = RetrievalScopeService(storage=storage)
        scope = scope_svc.resolve(project.project_id, {
            "type": "selected_papers",
            "selected_paper_ids": [p1.paper_id],
        })

        # 验证 scope 只包含 p1
        assert scope.paper_ids == [p1.paper_id]
        evidence = scope_svc.to_evidence_records(scope)
        for e in evidence:
            assert e.paper_id == p1.paper_id

    def test_empty_scope_handling(self, storage):
        """空 scope 应返回明确说明"""

        ps = ProjectService(storage=storage)
        project = ps.create_project("空项目")

        scope_svc = RetrievalScopeService(storage=storage)
        scope = scope_svc.resolve(project.project_id, {"type": "all_project"})

        assert scope.paper_ids == []
        assert "全项目" in scope.summary or len(scope.paper_ids) == 0
