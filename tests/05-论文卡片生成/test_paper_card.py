"""模块05 论文卡片生成 — 真实 LLM 调用

前置条件:
    - Docker 容器 paper-agent-postgres 运行中
    - ANTHROPIC_AUTH_TOKEN 或 OPENAI_API_KEY 已配置
    - 至少有一篇已解析的论文（有 chunks）
"""

import os
import pytest

from src.agents_v3.research_workspace.services.paper_card import PaperCardGenerator


HAS_LLM_KEY = bool(os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("OPENAI_API_KEY"))


@pytest.mark.skipif(not HAS_LLM_KEY, reason="未配置 LLM API Key")
class TestPaperCardE2E:
    """PaperCardGenerator 真实链路测试"""

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = PaperCardGenerator(storage=pg_storage)

    def test_generate_card_for_paper(self, pg_storage):
        """为已解析论文生成卡片"""
        # 查找一篇有 chunks 的论文
        papers = pg_storage.list_all("papers")
        paper_with_chunks = None
        for p in papers:
            chunks = pg_storage.query("paper_chunks", {"paper_id": p["paper_id"]})
            if chunks:
                paper_with_chunks = p
                break

        if not paper_with_chunks:
            pytest.skip("数据库中无已解析论文")

        card = self.service.generate(paper_with_chunks["paper_id"])
        assert card is not None
        assert card.paper_id == paper_with_chunks["paper_id"]
        assert card.title
        print(f"\n[card] 生成卡片: {card.title[:60]}...")

    def test_card_has_sections(self, pg_storage):
        """卡片应包含结构化章节"""
        papers = pg_storage.list_all("papers")
        paper_with_chunks = None
        for p in papers:
            chunks = pg_storage.query("paper_chunks", {"paper_id": p["paper_id"]})
            if chunks:
                paper_with_chunks = p
                break

        if not paper_with_chunks:
            pytest.skip("数据库中无已解析论文")

        card = self.service.generate(paper_with_chunks["paper_id"])
        assert card.method_summary or card.findings_summary
