"""统一测试 fixture"""

import pytest
from pathlib import Path

from src.agents_v3.research_workspace.storage import JSONStorage


@pytest.fixture
def storage(tmp_path):
    """提供临时 storage，不污染真实数据目录"""
    return JSONStorage(data_dir=tmp_path)


@pytest.fixture
def sample_project(storage):
    """创建示例项目"""
    from src.agents_v3.research_workspace.project_service import ProjectService
    ps = ProjectService(storage=storage)
    return ps.create_project("测试项目", description="用于测试")


@pytest.fixture
def sample_papers(storage, sample_project):
    """创建示例论文"""
    from src.agents_v3.research_workspace.paper_library import PaperLibraryService
    pls = PaperLibraryService(storage=storage)
    papers = pls.add_search_results(sample_project.project_id, [
        {"title": "LLM Feedback Study", "authors": ["Alice"], "year": 2024, "method": "experiment"},
        {"title": "AI Tutoring System", "authors": ["Bob"], "year": 2023, "method": "survey"},
        {"title": "Self-Regulated Learning", "authors": ["Charlie"], "year": 2024, "method": "interview"},
    ])
    return papers


@pytest.fixture
def sample_chunks(storage, sample_papers):
    """为论文创建 chunks"""
    for paper in sample_papers:
        storage.save_collection(f"chunks_{paper.paper_id}", [
            {
                "chunk_id": f"c_{paper.paper_id}_0",
                "paper_id": paper.paper_id,
                "section_title": "abstract",
                "text": f"This paper studies {paper.title}. Found improvement in learning outcomes.",
                "start_char": 0,
                "end_char": 100,
                "token_count": 15,
            },
            {
                "chunk_id": f"c_{paper.paper_id}_1",
                "paper_id": paper.paper_id,
                "section_title": "discussion",
                "text": f"A limitation of this study is the small sample size. Future work should extend.",
                "start_char": 100,
                "end_char": 200,
                "token_count": 18,
            },
        ])
    return sample_papers


@pytest.fixture
def sample_cards(storage, sample_chunks):
    """生成论文卡片"""
    from src.agents_v3.research_workspace.paper_card import PaperCardGenerator
    gen = PaperCardGenerator.__new__(PaperCardGenerator)
    gen.storage = storage
    gen.llm = None  # 不使用 LLM

    cards = []
    for paper in sample_chunks:
        # 手动创建卡片（跳过 LLM）
        from src.agents_v3.research_workspace.models import PaperCard, SourceSpan
        card = PaperCard(
            card_id=f"card_{paper.paper_id}",
            paper_id=paper.paper_id,
            project_id=paper.project_id,
            research_question="How does AI affect learning?",
            method="experiment",
            data_or_sample="100 students",
            key_findings=["Improved test scores", "Higher engagement"],
            limitations=["Small sample size"],
            future_work=["Extend to other subjects"],
            topics=["AI feedback", "self-regulated learning"],
            possible_gaps=["Long-term effects"],
            source_spans=[
                SourceSpan(field="key_findings", chunk_id=f"c_{paper.paper_id}_0", quote="Found improvement"),
            ],
            confidence=0.7,
        )
        storage.upsert_item("paper_cards", card.card_id, card.model_dump())
        cards.append(card)
    return cards


@pytest.fixture
def sample_evidence(storage, sample_cards):
    """生成证据记录"""
    from src.agents_v3.research_workspace.evidence_table import EvidenceTableService
    svc = EvidenceTableService(storage=storage)
    return svc.build_for_project(sample_cards[0].project_id)


@pytest.fixture
def sample_graph(storage, sample_evidence):
    """构建知识图谱"""
    from src.agents_v3.research_workspace.graph_service import GraphService
    svc = GraphService(storage=storage)
    return svc.build_project_graph(sample_evidence[0].project_id)
