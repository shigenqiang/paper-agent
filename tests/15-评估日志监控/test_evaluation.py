"""模块15 评估日志监控 — 真实 PostgreSQL

前置条件:
    - Docker 容器 paper-agent-postgres 运行中
    - 已有 QA/综述/创新点报告数据
"""

import pytest

from src.agents_v3.research_workspace.evaluation.evaluator import Evaluator


class TestEvaluationE2E:
    """Evaluator 真实链路测试"""

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.evaluator = Evaluator(storage=pg_storage)

    def test_evaluate_report(self, pg_storage):
        """评估报告质量"""
        reports = pg_storage.list_all("reports")
        if not reports:
            pytest.skip("数据库中无报告")

        report_id = reports[0]["report_id"]
        result = self.evaluator.evaluate_report(report_id)
        assert result is not None
        print(f"\n[eval] 报告评估: {result}")

    def test_quality_gate(self, pg_storage):
        """质量门禁检查"""
        reports = pg_storage.list_all("reports")
        if not reports:
            pytest.skip("数据库中无报告")

        report_id = reports[0]["report_id"]
        gate_result = self.evaluator.check_quality_gate(report_id)
        assert gate_result is not None
        assert "passed" in gate_result
        print(f"\n[eval] 质量门禁: {gate_result}")
