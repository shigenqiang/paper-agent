"""
文档监控测试
"""
import pytest
from pathlib import Path
from src.agents_v2.docs_monitor import (
    DocsMonitor,
    DocInfo,
    DocStatus,
    DocsHealthReport
)


class TestDocsMonitor:
    """测试文档监控器"""

    def test_create_monitor(self):
        """测试创建监控器"""
        monitor = DocsMonitor("docs")
        assert monitor.docs_path == Path("docs")
        assert not monitor.is_running

    def test_scan_docs(self):
        """测试扫描文档"""
        monitor = DocsMonitor("docs")
        docs = monitor.scan()

        assert isinstance(docs, dict)
        # 应该有文档被扫描到
        assert len(docs) > 0

    def test_get_health_report(self):
        """测试生成健康报告"""
        monitor = DocsMonitor("docs")
        monitor.scan()
        report = monitor.get_health_report()

        assert isinstance(report, DocsHealthReport)
        assert report.total_docs > 0
        assert report.total_size > 0
        assert report.avg_size > 0
        assert len(report.doc_list) > 0

    def test_doc_info_structure(self):
        """测试文档信息结构"""
        monitor = DocsMonitor("docs")
        monitor.scan()

        for path, doc in monitor.docs.items():
            assert isinstance(doc, DocInfo)
            assert doc.name.endswith('.md')
            assert doc.size > 0
            assert doc.lines > 0
            assert len(doc.checksum) == 32  # MD5

    def test_report_contains_required_fields(self):
        """测试报告包含必需字段"""
        monitor = DocsMonitor("docs")
        monitor.scan()
        report = monitor.get_health_report()

        assert hasattr(report, 'timestamp')
        assert hasattr(report, 'total_docs')
        assert hasattr(report, 'healthy_count')
        assert hasattr(report, 'total_size')
        assert hasattr(report, 'doc_list')

    def test_doc_list_sorted_by_size(self):
        """测试文档列表按大小排序"""
        monitor = DocsMonitor("docs")
        monitor.scan()
        report = monitor.get_health_report()

        doc_sizes = [d['size'] for d in report.doc_list]
        assert doc_sizes == sorted(doc_sizes, reverse=True)

    def test_headings_extraction(self):
        """测试标题提取"""
        monitor = DocsMonitor("docs")
        monitor.scan()

        for path, doc in monitor.docs.items():
            if doc.headings:
                assert all(h.startswith('#') for h in doc.headings)


class TestDocStatus:
    """测试文档状态"""

    def test_all_statuses(self):
        """测试所有状态枚举"""
        statuses = list(DocStatus)
        assert DocStatus.HEALTHY in statuses
        assert DocStatus.CHANGED in statuses
        assert DocStatus.NEW in statuses
        assert DocStatus.DELETED in statuses
        assert DocStatus.MISSING in statuses


class TestDocsHealthReport:
    """测试健康报告"""

    def test_report_json_serialization(self):
        """测试报告JSON序列化"""
        monitor = DocsMonitor("docs")
        monitor.scan()
        report = monitor.get_health_report()

        # 转换为字典
        report_dict = {
            "timestamp": report.timestamp,
            "total_docs": report.total_docs,
            "healthy_count": report.healthy_count,
            "changed_count": report.changed_count,
            "new_count": report.new_count,
            "total_size": report.total_size,
            "avg_size": report.avg_size,
            "largest_doc": report.largest_doc,
            "smallest_doc": report.smallest_doc,
            "docs_by_status": report.docs_by_status,
            "doc_list": report.doc_list
        }

        import json
        json_str = json.dumps(report_dict, ensure_ascii=False)
        assert len(json_str) > 0
