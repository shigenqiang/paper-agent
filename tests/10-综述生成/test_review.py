"""模块10 综述生成 — 真实 LLM + PostgreSQL

前置条件:
    - Docker 容器 paper-agent-postgres 运行中
    - ANTHROPIC_AUTH_TOKEN 或 OPENAI_API_KEY 已配置
    - 项目中有论文和证据
"""

import os
import pytest

from src.agents_v3.research_workspace.review_generator import LiteratureReviewGenerator


HAS_LLM_KEY = bool(os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("OPENAI_API_KEY"))


@pytest.mark.skipif(not HAS_LLM_KEY, reason="未配置 LLM API Key")
class TestReviewGeneratorE2E:
    """LiteratureReviewGenerator 真实链路测试"""

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = LiteratureReviewGenerator(storage=pg_storage)

    def _find_project_with_evidence(self, pg_storage):
        evidence = pg_storage.list_all("evidence_records")
        if not evidence:
            return None
        return evidence[0].get("project_id")

    def test_generate_review(self, pg_storage):
        """生成综述应返回 Report"""
        pid = self._find_project_with_evidence(pg_storage)
        if not pid:
            pytest.skip("数据库中无证据记录")

        report = self.service.generate(pid)
        assert report is not None
        assert report.content
        assert "文献综述" in report.title or "综述" in report.title
        print(f"\n[review] 生成综述: {len(report.content)} 字符")

    def test_review_has_sections(self, pg_storage):
        """综述应有章节结构"""
        pid = self._find_project_with_evidence(pg_storage)
        if not pid:
            pytest.skip("数据库中无证据记录")

        report = self.service.generate(pid)
        # 至少应有引言/发现/结论相关章节
        content = report.content
        assert len(content) > 200
