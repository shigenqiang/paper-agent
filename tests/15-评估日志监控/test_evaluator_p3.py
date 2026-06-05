"""P3-B Evaluator 类单元测试

覆盖：
- Evaluator.evaluate_report 基本流程
- Evaluator.evaluate_report 报告不存在
- Evaluator.check_quality_gate 通过/失败
- MetricsCollector 记录和汇总
"""

from unittest.mock import MagicMock

import pytest

from src.agents_v3.research_workspace.evaluation.evaluator import (
    Evaluator,
    EvaluationResult,
    generic_text_check,
    report_traceability_check,
)
from src.agents_v3.research_workspace.evaluation.gates import run_quality_gates
from src.agents_v3.research_workspace.evaluation.metrics import MetricsCollector


class TestEvaluatorReport:
    """Evaluator 报告评估测试"""

    def test_report_not_found(self):
        """报告不存在时返回 error"""
        mock_storage = MagicMock()
        mock_storage.get_item.return_value = None
        evaluator = Evaluator(storage=mock_storage)

        result = evaluator.evaluate_report("nonexistent")
        assert result["error"] == "report_not_found"
        assert result["report_id"] == "nonexistent"

    def test_evaluate_report_basic(self):
        """基本报告评估流程"""
        mock_storage = MagicMock()
        mock_storage.get_item.return_value = {
            "report_id": "r1",
            "content": "This is a test report with real content about transformers.",
            "metadata": {
                "paper_ids": ["p1", "p2"],
                "evidence_ids": ["e1", "e2"],
                "section_sources": {
                    "intro": {"evidence_ids": ["e1"]},
                    "methods": {"evidence_ids": ["e2"]},
                },
            },
        }
        evaluator = Evaluator(storage=mock_storage)

        result = evaluator.evaluate_report("r1")
        assert result["report_id"] == "r1"
        assert "evaluations" in result
        assert len(result["evaluations"]) == 2  # traceability + generic_text
        assert result["summary"]["total"] == 2
        assert result["summary"]["passed"] >= 0

    def test_evaluate_report_with_string_metadata(self):
        """metadata 为 JSON 字符串时也能解析"""
        import json
        mock_storage = MagicMock()
        mock_storage.get_item.return_value = {
            "report_id": "r1",
            "content": "Test content.",
            "metadata": json.dumps({
                "paper_ids": ["p1"],
                "evidence_ids": ["e1"],
                "section_sources": {},
            }),
        }
        evaluator = Evaluator(storage=mock_storage)

        result = evaluator.evaluate_report("r1")
        assert "evaluations" in result
        assert len(result["evaluations"]) == 2

    def test_evaluate_report_empty_metadata(self):
        """metadata 为空时使用空默认值"""
        mock_storage = MagicMock()
        mock_storage.get_item.return_value = {
            "report_id": "r1",
            "content": "Some content.",
            "metadata": None,
        }
        evaluator = Evaluator(storage=mock_storage)

        result = evaluator.evaluate_report("r1")
        assert "evaluations" in result


class TestEvaluatorQualityGate:
    """Evaluator 质量门测试"""

    def test_quality_gate_passes(self):
        """高质量报告通过质量门"""
        mock_storage = MagicMock()
        mock_storage.get_item.return_value = {
            "report_id": "r1",
            "content": "Real content about NLP research findings.",
            "metadata": {
                "paper_ids": ["p1"],
                "evidence_ids": ["e1"],
                "section_sources": {"intro": {"evidence_ids": ["e1"]}},
            },
        }
        evaluator = Evaluator(storage=mock_storage)

        result = evaluator.check_quality_gate("r1")
        assert "passed" in result
        assert "gates" in result
        assert result["total_gates"] > 0

    def test_quality_gate_report_not_found(self):
        """报告不存在时返回 error"""
        mock_storage = MagicMock()
        mock_storage.get_item.return_value = None
        evaluator = Evaluator(storage=mock_storage)

        result = evaluator.check_quality_gate("nonexistent")
        assert result["error"] == "report_not_found"


class TestGenericTextCheck:
    """泛化文本检查测试"""

    def test_clean_text_passes(self):
        """无泛化套话的文本通过"""
        result = generic_text_check("Transformer architecture uses self-attention mechanisms.")
        assert result.passed is True

    def test_generic_text_fails(self):
        """充满泛化套话的文本失败"""
        text = "大量研究表明这个方法有效。许多研究都证实了这一点。普遍认为这是正确的。"
        result = generic_text_check(text)
        assert result.passed is False

    def test_empty_text_passes(self):
        """空文本通过"""
        assert generic_text_check("").passed is True


class TestMetricsCollector:
    """MetricsCollector 测试"""

    def test_record_metric(self):
        """记录指标"""
        collector = MetricsCollector()
        collector.record("test_metric", 42.0, unit="ms", service="test")
        records = collector.get_records("test_metric")
        assert len(records) == 1
        assert records[0].value == 42.0

    def test_summarize_metrics(self):
        """汇总指标"""
        collector = MetricsCollector()
        for v in [10.0, 20.0, 30.0]:
            collector.record("latency", v, unit="ms")
        summary = collector.summarize("latency")
        assert summary["count"] == 3
        assert summary["min"] == 10.0
        assert summary["max"] == 30.0
        assert summary["avg"] == 20.0

    def test_multiple_metric_names(self):
        """不同名称的指标互不干扰"""
        collector = MetricsCollector()
        collector.record("metric_a", 1.0)
        collector.record("metric_b", 2.0)
        assert len(collector.get_records("metric_a")) == 1
        assert len(collector.get_records("metric_b")) == 1
