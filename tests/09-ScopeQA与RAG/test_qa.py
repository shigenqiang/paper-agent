"""模块09 ScopeQA与RAG — 真实 LLM + PostgreSQL

前置条件:
    - Docker 容器 paper-agent-postgres 运行中
    - ANTHROPIC_AUTH_TOKEN 或 OPENAI_API_KEY 已配置
    - 项目中有论文和证据
"""

import os
import pytest

from src.agents_v3.research_workspace.services.scope_qa import ScopeQAService


HAS_LLM_KEY = bool(os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("OPENAI_API_KEY"))


@pytest.mark.skipif(not HAS_LLM_KEY, reason="未配置 LLM API Key")
class TestScopeQAE2E:
    """ScopeQAService 真实链路测试"""

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = ScopeQAService(storage=pg_storage)

    def _find_project_with_evidence(self, pg_storage):
        evidence = pg_storage.list_all("evidence_records")
        if not evidence:
            return None
        return evidence[0].get("project_id")

    def test_answer_returns_response(self, pg_storage):
        """scope QA 应返回回答"""
        pid = self._find_project_with_evidence(pg_storage)
        if not pid:
            pytest.skip("数据库中无证据记录")

        response = self.service.answer(pid, "这个项目的主要研究方法是什么？")
        assert response is not None
        assert response.answer
        print(f"\n[qa] 回答: {response.answer[:100]}...")

    def test_answer_has_supporting_papers(self, pg_storage):
        """回答应引用支撑论文"""
        pid = self._find_project_with_evidence(pg_storage)
        if not pid:
            pytest.skip("数据库中无证据记录")

        response = self.service.answer(pid, "主要发现有哪些？")
        if response.supporting_papers:
            print(f"\n[qa] 引用 {len(response.supporting_papers)} 篇论文")
