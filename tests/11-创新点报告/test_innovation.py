"""模块11 创新点报告 — 真实 LLM + PostgreSQL

前置条件:
    - Docker 容器 paper-agent-postgres 运行中
    - ANTHROPIC_AUTH_TOKEN 或 OPENAI_API_KEY 已配置
    - 项目中有论文、证据和知识图谱
"""

import os
import pytest

from src.agents_v3.research_workspace.services.innovation_generator import InnovationReportGenerator


HAS_LLM_KEY = bool(os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("OPENAI_API_KEY"))


@pytest.mark.skipif(not HAS_LLM_KEY, reason="未配置 LLM API Key")
class TestInnovationGeneratorE2E:
    """InnovationReportGenerator 真实链路测试"""

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = InnovationReportGenerator(storage=pg_storage)

    def _find_project_with_graph(self, pg_storage):
        nodes = pg_storage.list_all("graph_nodes")
        if not nodes:
            return None
        return nodes[0].get("project_id")

    def test_generate_innovation_report(self, pg_storage):
        """生成创新点报告"""
        pid = self._find_project_with_graph(pg_storage)
        if not pid:
            pytest.skip("数据库中无知识图谱")

        report = self.service.generate(pid)
        assert report is not None
        assert report.content
        print(f"\n[innovation] 生成报告: {len(report.content)} 字符")

    def test_report_has_innovation_points(self, pg_storage):
        """报告应包含创新点"""
        pid = self._find_project_with_graph(pg_storage)
        if not pid:
            pytest.skip("数据库中无知识图谱")

        report = self.service.generate(pid)
        assert len(report.content) > 100
