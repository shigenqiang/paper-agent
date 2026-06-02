"""模块12 报告版本与导出 — 真实 PostgreSQL

前置条件:
    - Docker 容器 paper-agent-postgres 运行中
    - 已有生成的报告
"""

import pytest

from src.agents_v3.research_workspace.report_service import ReportService


class TestReportServiceE2E:
    """ReportService 真实链路测试"""

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = ReportService(storage=pg_storage)

    def test_list_reports(self, pg_storage):
        """列出报告"""
        reports = self.service.list_reports()
        print(f"\n[report] 共 {len(reports)} 份报告")
        # 不要求必须有报告，只验证不报错

    def test_get_report(self, pg_storage):
        """获取报告详情"""
        reports = pg_storage.list_all("reports")
        if not reports:
            pytest.skip("数据库中无报告")

        report_id = reports[0]["report_id"]
        report = self.service.get_report(report_id)
        assert report is not None
        assert report.content

    def test_export_markdown(self, pg_storage):
        """导出 Markdown"""
        reports = pg_storage.list_all("reports")
        if not reports:
            pytest.skip("数据库中无报告")

        report_id = reports[0]["report_id"]
        md = self.service.export_markdown(report_id)
        assert md
        assert isinstance(md, str)
        print(f"\n[export] Markdown: {len(md)} 字符")
