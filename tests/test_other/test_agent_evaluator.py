"""
Agent评估测试 v2.0

测试增强后的Agent评估框架
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents_v2.evaluation.agent_evaluator import (
    AgentEvaluator,
    AgentEvaluationReport,
    EvaluationResult,
    ImprovementSuggestion,
    EvaluationLevel,
    get_evaluator,
    reset_evaluator
)


class TestEvaluationResult:
    """测试评估结果"""

    def test_evaluation_result_creation(self):
        """测试评估结果创建"""
        result = EvaluationResult(
            dimension="task_completion",
            score=8.5,
            details={"completed": True, "steps": 5},
            suggestions=["增加验证步骤"]
        )
        assert result.dimension == "task_completion"
        assert result.score == 8.5
        assert result.details["completed"] is True

    def test_score_bounds(self):
        """测试分数边界"""
        result = EvaluationResult(dimension="test", score=10.0)
        assert result.score == 10.0

        result = EvaluationResult(dimension="test", score=0.0)
        assert result.score == 0.0


class TestImprovementSuggestion:
    """测试改进建议"""

    def test_improvement_creation(self):
        """测试改进建议创建"""
        suggestion = ImprovementSuggestion(
            dimension="quality",
            current_score=7.5,
            target_score=9.0,
            gap=1.5,
            priority=1,
            actions=["优化提示词", "增加验证"],
            expected_impact="提升质量维度1.5分"
        )
        assert suggestion.dimension == "quality"
        assert suggestion.current_score == 7.5
        assert suggestion.gap == 1.5
        assert suggestion.priority == 1


class TestAgentEvaluationReport:
    """测试Agent评估报告"""

    def test_report_creation(self):
        """测试报告创建"""
        report = AgentEvaluationReport(
            agent_name="TopicAgent",
            evaluation_time=None,
            task_type="topic_selection",
            task_description="测试选题"
        )
        assert report.agent_name == "TopicAgent"
        assert report.overall_score == 0.0

    def test_compute_overall(self):
        """测试综合评分计算"""
        report = AgentEvaluationReport(
            agent_name="TestAgent",
            evaluation_time=None,
            task_type="test",
            task_description="测试"
        )
        report.task_completion = 8.0
        report.quality = 9.0
        report.tool_usage = 7.0
        report.planning = 8.0
        report.efficiency = 7.0
        report.collaboration = 8.0
        report.safety = 9.0
        report.self_correction = 8.0
        report.robustness = 7.5
        report.consistency = 8.0
        report.cost_efficiency = 7.5
        report.multi_turn = 7.0

        report.compute_overall()

        assert report.overall_score > 0
        assert report.overall_score <= 10

    def test_grade_property(self):
        """测试评分等级"""
        report = AgentEvaluationReport(
            agent_name="TestAgent",
            evaluation_time=None,
            task_type="test",
            task_description="测试"
        )

        report.overall_score = 9.6
        assert "A+" in report.grade

        report.overall_score = 9.5
        assert "A+" in report.grade

        report.overall_score = 9.0
        assert "A" in report.grade

        report.overall_score = 8.5
        assert "B" in report.grade

        report.overall_score = 7.5
        assert "C" in report.grade

        report.overall_score = 6.5
        assert "D" in report.grade

        report.overall_score = 5.0
        assert "F" in report.grade

    def test_all_dimensions_scored(self):
        """测试所有维度都评分"""
        report = AgentEvaluationReport(
            agent_name="TestAgent",
            evaluation_time=None,
            task_type="test",
            task_description="测试"
        )
        report.task_completion = 8.0
        report.quality = 8.0
        report.tool_usage = 8.0
        report.planning = 8.0
        report.efficiency = 8.0
        report.collaboration = 8.0
        report.safety = 8.0
        report.self_correction = 8.0
        report.robustness = 8.0
        report.consistency = 8.0
        report.cost_efficiency = 8.0
        report.multi_turn = 8.0

        report.compute_overall()

        assert report.overall_score > 0

    def test_strength_dimensions(self):
        """测试优势维度"""
        report = AgentEvaluationReport(
            agent_name="TestAgent",
            evaluation_time=None,
            task_type="test",
            task_description="测试"
        )
        report.task_completion = 8.0
        report.quality = 9.0
        report.tool_usage = 7.0
        report.planning = 6.0
        report.efficiency = 5.0
        report.collaboration = 7.0
        report.safety = 8.0
        report.self_correction = 7.0
        report.robustness = 6.0
        report.consistency = 5.0
        report.cost_efficiency = 7.0
        report.multi_turn = 6.0

        strengths = report.strength_dimensions
        assert len(strengths) == 3
        assert strengths[0][0] == "quality"  # 最高分

    def test_weakness_dimensions(self):
        """测试弱势维度"""
        report = AgentEvaluationReport(
            agent_name="TestAgent",
            evaluation_time=None,
            task_type="test",
            task_description="测试"
        )
        report.task_completion = 8.0
        report.quality = 9.0
        report.tool_usage = 7.0
        report.planning = 6.0
        report.efficiency = 5.0
        report.collaboration = 7.0
        report.safety = 8.0
        report.self_correction = 7.0
        report.robustness = 6.0
        report.consistency = 5.5
        report.cost_efficiency = 7.0
        report.multi_turn = 6.0

        weaknesses = report.weakness_dimensions
        assert len(weaknesses) == 3
        assert weaknesses[0][0] == "efficiency"  # 最低分

    def test_generate_improvements(self):
        """测试改进建议生成"""
        report = AgentEvaluationReport(
            agent_name="TestAgent",
            evaluation_time=None,
            task_type="test",
            task_description="测试"
        )
        report.task_completion = 7.0
        report.quality = 6.0
        report.tool_usage = 8.0
        report.planning = 7.0
        report.efficiency = 6.0
        report.collaboration = 8.0
        report.safety = 7.0
        report.self_correction = 8.0
        report.robustness = 7.0
        report.consistency = 6.0
        report.cost_efficiency = 8.0
        report.multi_turn = 7.0

        improvements = report.generate_improvements(target_score=9.0)

        assert len(improvements) > 0
        # quality是最低分之一，应该在建议中
        dim_names = [imp.dimension for imp in improvements]
        assert "quality" in dim_names

    def test_benchmark_comparison(self):
        """测试基准对比"""
        report = AgentEvaluationReport(
            agent_name="TestAgent",
            evaluation_time=None,
            task_type="test",
            task_description="测试"
        )
        report.overall_score = 9.0
        report.benchmark_score = 8.5

        assert report.overall_score - report.benchmark_score == 0.5


class TestAgentEvaluator:
    """测试Agent评估器"""

    def test_evaluator_init(self):
        """测试评估器初始化"""
        evaluator = AgentEvaluator()
        assert evaluator.evaluation_history == []
        assert evaluator.peer_groups == {}

    @pytest.mark.asyncio
    async def test_evaluate_topic_agent_mock(self):
        """测试TopicAgent评估(模拟)"""
        evaluator = AgentEvaluator()

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.quality_score = 0.85
        mock_result.result = {
            "selected_topic": {"title": "Test Topic"},
            "alternative_topics": [{"title": "Alt 1"}, {"title": "Alt 2"}]
        }
        mock_result.error = None
        mock_agent.execute = AsyncMock(return_value=mock_result)

        test_cases = [
            {"input": "深度学习在医学中的应用"},
            {"input": "自然语言处理研究"}
        ]

        with patch('time.time', return_value=1000):
            with patch('time.time', return_value=1005):
                report = await evaluator.evaluate_topic_agent(mock_agent, test_cases)

        assert report.agent_name == "TopicAgent"
        assert report.task_type == "topic_selection"
        assert report.task_completion > 0
        assert report.quality > 0
        assert report.benchmark_score > 0
        assert len(report.improvements) > 0
        assert len(evaluator.evaluation_history) == 1

    @pytest.mark.asyncio
    async def test_evaluate_literature_agent_mock(self):
        """测试LiteratureAgent评估(模拟)"""
        evaluator = AgentEvaluator()

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.quality_score = 0.8
        mock_result.result = {
            "papers": [
                {"title": "Paper 1", "source": "arxiv"},
                {"title": "Paper 2", "source": "arxiv"},
                {"title": "Paper 3", "source": "pubmed"}
            ],
            "search_queries": ["query1", "query2"],
            "paper_analyses": [{"analysis": "1"}]
        }
        mock_result.error = None
        mock_agent.execute = AsyncMock(return_value=mock_result)

        test_cases = [
            {"topic": "机器学习"},
            {"topic": "深度学习"}
        ]

        with patch('time.time', return_value=1000):
            with patch('time.time', return_value=1008):
                report = await evaluator.evaluate_literature_agent(mock_agent, test_cases)

        assert report.agent_name == "LiteratureAgent"
        assert report.task_completion > 0
        assert report.tool_usage > 0
        assert len(report.improvements) > 0

    @pytest.mark.asyncio
    async def test_evaluate_agent_generic_mock(self):
        """测试通用Agent评估(模拟)"""
        evaluator = AgentEvaluator()

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.quality_score = 0.75
        mock_result.error = None
        mock_agent.execute = AsyncMock(return_value=mock_result)

        test_cases = [
            {"input": {"task": "test1"}},
            {"input": {"task": "test2"}}
        ]

        with patch('time.time', return_value=1000):
            with patch('time.time', return_value=1005):
                report = await evaluator.evaluate_agent(mock_agent, "TestAgent", test_cases)

        assert report.agent_name == "TestAgent"
        assert report.overall_score > 0

    @pytest.mark.asyncio
    async def test_evaluate_with_failure(self):
        """测试评估失败情况"""
        evaluator = AgentEvaluator()

        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=Exception("Agent failed"))

        test_cases = [{"input": "test"}]

        with patch('time.time', return_value=1000):
            with patch('time.time', return_value=1003):
                report = await evaluator.evaluate_topic_agent(mock_agent, test_cases)

        # 失败情况下分数应该较低但不为零
        assert report.task_completion >= 0
        assert report.quality >= 0

    @pytest.mark.asyncio
    async def test_multi_case_evaluation(self):
        """测试多案例评估"""
        evaluator = AgentEvaluator()

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.quality_score = 0.85
        mock_result.result = {"selected_topic": {"title": "Test"}}
        mock_result.error = None
        mock_agent.execute = AsyncMock(return_value=mock_result)

        test_cases = [
            {"input": "测试1"},
            {"input": "测试2"},
            {"input": "测试3"}
        ]

        with patch('time.time', return_value=1000):
            with patch('time.time', return_value=1003):
                report = await evaluator.evaluate_topic_agent(mock_agent, test_cases)

        # 多次评估应累加到历史
        assert len(evaluator.evaluation_history) == 1

    @pytest.mark.asyncio
    async def test_consistency_scoring(self):
        """测试一致性评分"""
        evaluator = AgentEvaluator()

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.quality_score = 0.8
        mock_result.result = {"selected_topic": {"title": "Test"}}
        mock_result.error = None
        mock_agent.execute = AsyncMock(return_value=mock_result)

        with patch('time.time', return_value=1000):
            with patch('time.time', return_value=1003):
                report = await evaluator.evaluate_topic_agent(mock_agent, [{"input": "test"}])

        # 一致性分数应该在0-10之间
        assert 0 <= report.consistency <= 10

    def test_evaluation_summary(self):
        """测试评估总结"""
        evaluator = AgentEvaluator()

        # 添加评估报告
        report = AgentEvaluationReport(
            agent_name="Agent1",
            evaluation_time=None,
            task_type="test",
            task_description="测试1"
        )
        report.task_completion = 8.0
        report.quality = 8.0
        report.tool_usage = 8.0
        report.planning = 8.0
        report.efficiency = 8.0
        report.collaboration = 8.0
        report.safety = 8.0
        report.self_correction = 8.0
        report.robustness = 8.0
        report.consistency = 8.0
        report.cost_efficiency = 8.0
        report.multi_turn = 8.0
        report.compute_overall()

        evaluator.evaluation_history.append(report)

        summary = evaluator.get_evaluation_summary()

        assert "agent" in summary
        assert "overall_score" in summary
        assert "dimensions" in summary
        assert "strengths" in summary
        assert "weaknesses" in summary
        assert "improvements" in summary
        assert summary["total_evaluations"] == 1

    def test_evaluation_summary_empty(self):
        """测试空评估总结"""
        evaluator = AgentEvaluator()
        summary = evaluator.get_evaluation_summary()
        assert "message" in summary
        assert summary["message"] == "No evaluations yet"

    def test_peer_comparison(self):
        """测试同级对比"""
        evaluator = AgentEvaluator()

        # 添加多个评估
        for i in range(3):
            report = AgentEvaluationReport(
                agent_name="TestAgent",
                evaluation_time=None,
                task_type="test",
                task_description="测试"
            )
            report.task_completion = 8.0 + i * 0.5
            report.quality = 8.0 + i * 0.3
            report.tool_usage = 8.0
            report.planning = 8.0
            report.efficiency = 8.0
            report.collaboration = 8.0
            report.safety = 8.0
            report.self_correction = 8.0
            report.robustness = 8.0
            report.consistency = 8.0
            report.cost_efficiency = 8.0
            report.multi_turn = 8.0
            report.compute_overall()
            evaluator.evaluation_history.append(report)
            if "TestAgent" not in evaluator.peer_groups:
                evaluator.peer_groups["TestAgent"] = []
            evaluator.peer_groups["TestAgent"].append(report)

        comparison = evaluator.get_peer_comparison("TestAgent")

        if "message" not in comparison:
            assert "scores" in comparison
            assert "best_in_class" in comparison

    def test_improvement_roadmap(self):
        """测试改进路线图"""
        evaluator = AgentEvaluator()

        report = AgentEvaluationReport(
            agent_name="TestAgent",
            evaluation_time=None,
            task_type="test",
            task_description="测试"
        )
        report.task_completion = 7.0
        report.quality = 6.0
        report.tool_usage = 8.0
        report.planning = 7.0
        report.efficiency = 6.0
        report.collaboration = 8.0
        report.safety = 7.0
        report.self_correction = 8.0
        report.robustness = 7.0
        report.consistency = 6.0
        report.cost_efficiency = 8.0
        report.multi_turn = 7.0
        report.compute_overall()

        evaluator.evaluation_history.append(report)

        roadmap = evaluator.compute_improvement_roadmap(target_score=9.0)

        assert len(roadmap) > 0
        assert "step" in roadmap[0]
        assert "dimension" in roadmap[0]
        assert "actions" in roadmap[0]


class TestEvaluatorSingleton:
    """测试评估器单例"""

    def test_get_evaluator(self):
        """测试获取评估器"""
        reset_evaluator()
        evaluator1 = get_evaluator()
        evaluator2 = get_evaluator()
        assert evaluator1 is evaluator2

    def test_get_evaluator_reset(self):
        """测试评估器重置"""
        reset_evaluator()

        evaluator = get_evaluator()
        assert isinstance(evaluator, AgentEvaluator)
        assert evaluator.evaluation_history == []


class TestEvaluationDimensions:
    """测试评估维度"""

    @pytest.mark.asyncio
    async def test_all_dimensions_present(self):
        """测试所有评估维度都存在"""
        evaluator = AgentEvaluator()

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.quality_score = 0.8
        mock_result.result = {"selected_topic": {"title": "Test"}}
        mock_result.error = None
        mock_agent.execute = AsyncMock(return_value=mock_result)

        report = await evaluator.evaluate_topic_agent(mock_agent, [{"input": "test"}])

        dimensions = [
            "task_completion",
            "quality",
            "tool_usage",
            "planning",
            "efficiency",
            "collaboration",
            "safety",
            "self_correction",
            "robustness",
            "consistency",
            "cost_efficiency",
            "multi_turn"
        ]

        for dim in dimensions:
            assert hasattr(report, dim)
            value = getattr(report, dim)
            assert 0 <= value <= 10, f"Dimension {dim} out of bounds: {value}"

    @pytest.mark.asyncio
    async def test_dimension_weighting(self):
        """测试维度权重"""
        evaluator = AgentEvaluator()

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.quality_score = 0.9
        mock_result.result = {
            "selected_topic": {"title": "Test"},
            "alternative_topics": [{"title": "Alt"}]
        }
        mock_result.error = None
        mock_agent.execute = AsyncMock(return_value=mock_result)

        report = await evaluator.evaluate_topic_agent(mock_agent, [{"input": "test"}])

        # 验证综合评分计算
        weights = {
            'task_completion': 0.22,
            'quality': 0.18,
            'tool_usage': 0.12,
            'planning': 0.08,
            'efficiency': 0.08,
            'collaboration': 0.08,
            'safety': 0.07,
            'self_correction': 0.05,
            'robustness': 0.05,
            'consistency': 0.04,
            'cost_efficiency': 0.02,
            'multi_turn': 0.01
        }

        expected = sum(getattr(report, dim) * weight for dim, weight in weights.items())
        assert abs(report.overall_score - expected) < 0.01

    @pytest.mark.asyncio
    async def test_benchmark_scores(self):
        """测试基准分数"""
        evaluator = AgentEvaluator()

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.quality_score = 0.85
        mock_result.result = {"selected_topic": {"title": "Test"}}
        mock_result.error = None
        mock_agent.execute = AsyncMock(return_value=mock_result)

        report = await evaluator.evaluate_topic_agent(mock_agent, [{"input": "test"}])

        # TopicAgent应该有基准分数
        assert report.benchmark_score > 0
        assert report.benchmark_score == AgentEvaluator.BENCHMARK_SCORES.get('TopicAgent')


class TestEvaluationLevel:
    """测试评估级别"""

    def test_evaluation_levels(self):
        """测试评估级别枚举"""
        assert EvaluationLevel.UNIT.value == "unit"
        assert EvaluationLevel.INTEGRATION.value == "integration"
        assert EvaluationLevel.BENCHMARK.value == "benchmark"
        assert EvaluationLevel.COMPETITIVE.value == "competitive"

    @pytest.mark.asyncio
    async def test_different_levels(self):
        """测试不同评估级别"""
        evaluator = AgentEvaluator()

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.quality_score = 0.8
        mock_result.result = {"selected_topic": {"title": "Test"}}
        mock_result.error = None
        mock_agent.execute = AsyncMock(return_value=mock_result)

        # 单元级别
        report1 = await evaluator.evaluate_topic_agent(
            mock_agent, [{"input": "test"}],
            level=EvaluationLevel.UNIT
        )
        assert report1.evaluation_level == EvaluationLevel.UNIT

        # 基准测试级别
        report2 = await evaluator.evaluate_topic_agent(
            mock_agent, [{"input": "test"}],
            level=EvaluationLevel.BENCHMARK
        )
        assert report2.evaluation_level == EvaluationLevel.BENCHMARK
