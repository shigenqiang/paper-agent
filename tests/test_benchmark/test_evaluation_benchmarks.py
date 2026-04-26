"""
评估基准测试

测试GAIA基准、AgentBench适配器、论文写作基准和A/B测试框架
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# 测试 GAIA 基准
from src.agents_v2.evaluation.benchmarks.gaia import (
    GAIABenchmark,
    GAIATask,
    GAIAResult,
    run_gaia_evaluation
)

# 测试 AgentBench 适配器
from src.agents_v2.evaluation.benchmarks.agent_bench import (
    AgentBenchAdapter,
    Domain,
    DomainTask,
    BenchmarkReport
)

# 测试论文写作基准
from src.agents_v2.evaluation.benchmarks.paper_writing import (
    PaperWritingBenchmark,
    PaperWritingResult,
    evaluate_paper
)

# 测试A/B测试框架
from src.agents_v2.evaluation.benchmarks.ab_testing import (
    ABTestFramework,
    ABTestResult,
    AgentConfig,
    TestTask as TestTaskData,
    TestTypeEnum,
    run_ab_test
)


class TestGAIABenchmark:
    """测试GAIA基准"""

    def test_benchmark_init_level_1(self):
        """测试Level 1初始化"""
        benchmark = GAIABenchmark(level=1)
        assert benchmark.level == 1
        assert len(benchmark.tasks) > 0

    def test_benchmark_init_level_2(self):
        """测试Level 2初始化"""
        benchmark = GAIABenchmark(level=2)
        assert benchmark.level == 2

    def test_benchmark_init_level_3(self):
        """测试Level 3初始化"""
        benchmark = GAIABenchmark(level=3)
        assert benchmark.level == 3

    def test_benchmark_invalid_level(self):
        """测试无效等级"""
        with pytest.raises(ValueError):
            GAIABenchmark(level=4)

    @pytest.mark.asyncio
    async def test_evaluate_mock_agent(self):
        """测试评估模拟Agent"""
        benchmark = GAIABenchmark(level=1)

        # 创建模拟Agent
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value="机器学习是人工智能的一个分支...")

        result = await benchmark.evaluate(mock_agent)

        assert isinstance(result, GAIAResult)
        assert result.level == 1
        assert result.total_tasks > 0

    def test_check_answer(self):
        """测试答案检查"""
        benchmark = GAIABenchmark(level=1)

        # 正确答案
        assert benchmark._check_answer("机器学习是...", "机器学习")
        assert benchmark._check_answer("深度学习是机器学习的一个分支", "机器学习")

        # 错误答案
        assert not benchmark._check_answer("物理学", "机器学习")

    def test_calculate_breakdown(self):
        """测试分项评分计算"""
        benchmark = GAIABenchmark(level=1)

        results = [
            {"success": True, "latency": 1.0},
            {"success": True, "latency": 2.0},
            {"success": False, "latency": 3.0}
        ]

        breakdown = benchmark._calculate_breakdown(results)

        assert "overall" in breakdown
        assert breakdown["overall"] == 2/3

    def test_generate_report(self):
        """测试报告生成"""
        benchmark = GAIABenchmark(level=1)

        result = GAIAResult(
            level=1,
            accuracy=0.8,
            avg_latency=2.5,
            total_tasks=5,
            passed_tasks=4,
            failed_tasks=1,
            results=[],
            score_breakdown={"overall": 0.8}
        )

        report = benchmark.generate_report(result)
        assert "GAIA" in report
        assert "Level 1" in report
        assert "80" in report


class TestAgentBenchAdapter:
    """测试AgentBench适配器"""

    def test_adapter_init(self):
        """测试适配器初始化"""
        adapter = AgentBenchAdapter()

        assert Domain.KNOWLEDGE_GRAPH in adapter.tasks
        assert Domain.DATABASE in adapter.tasks
        assert Domain.CODE in adapter.tasks

    def test_add_task(self):
        """测试添加任务"""
        adapter = AgentBenchAdapter()

        task = DomainTask(
            task_id="custom_001",
            domain=Domain.WEB,
            description="测试任务",
            expected_output="test"
        )

        adapter.add_task(task)

        assert len(adapter.tasks[Domain.WEB]) > 0

    @pytest.mark.asyncio
    async def test_evaluate_domain(self):
        """测试领域评估"""
        adapter = AgentBenchAdapter()

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value="测试结果")

        # 只评估一个任务
        result = await adapter.evaluate_domain(mock_agent, Domain.CODE)

        assert isinstance(result.domain, str)
        assert 0 <= result.accuracy <= 1

    @pytest.mark.asyncio
    async def test_evaluate_all(self):
        """测试全领域评估"""
        adapter = AgentBenchAdapter()

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value="测试结果")

        report = await adapter.evaluate_all(mock_agent)

        assert isinstance(report, BenchmarkReport)
        assert report.overall_score >= 0
        assert len(report.domain_scores) == 4

    def test_eval_list_overlap(self):
        """测试列表重叠评估"""
        adapter = AgentBenchAdapter()

        expected = ["BERT", "GPT", "Transformer"]
        response1 = ["BERT", "GPT", "T5"]
        response2 = ["XXL"]  # 完全不匹配

        assert adapter._eval_list_overlap(response1, expected)
        assert not adapter._eval_list_overlap(response2, expected)

    def test_eval_result_exists(self):
        """测试结果存在评估"""
        adapter = AgentBenchAdapter()

        assert adapter._eval_result_exists(["item"], None)
        assert not adapter._eval_result_exists([], None)
        assert not adapter._eval_result_exists(None, None)

    def test_generate_recommendations(self):
        """测试生成建议"""
        adapter = AgentBenchAdapter()

        domain_scores = {
            "knowledge_graph": MagicMock(accuracy=0.6),
            "database": MagicMock(accuracy=0.8)
        }
        gap_analysis = {
            "knowledge_graph": -0.15,
            "database": 0.1
        }

        recommendations = adapter._generate_recommendations(domain_scores, gap_analysis)

        assert len(recommendations) > 0


class TestPaperWritingBenchmark:
    """测试论文写作基准"""

    def test_benchmark_init(self):
        """测试基准初始化"""
        benchmark = PaperWritingBenchmark()

        assert "topic_quality" in benchmark.weights
        assert "language_quality" in benchmark.weights

    def test_custom_weights(self):
        """测试自定义权重"""
        weights = {
            "topic_quality": 0.3,
            "literature_coverage": 0.1,
            "thesis_clarity": 0.1,
            "outline_quality": 0.2,
            "draft_quality": 0.2,
            "language_quality": 0.1
        }

        benchmark = PaperWritingBenchmark(weights=weights)

        assert benchmark.weights["topic_quality"] == 0.3

    @pytest.mark.asyncio
    async def test_evaluate_minimal_paper(self):
        """测试评估最小论文"""
        benchmark = PaperWritingBenchmark()

        paper = {
            "topic": "深度学习在图像识别中的应用研究",
            "literature": [{"title": "Paper1", "source": "arXiv", "year": 2023}],
            "thesis": "本研旨在提高图像识别的准确率",
            "outline": "1.引言 2.方法 3.实验 4.结论",
            "draft": "这是论文的完整内容..." * 50,
            "title": "深度学习图像识别",
            "abstract": "本文研究..."
        }

        result = await benchmark.evaluate(paper)

        assert isinstance(result, PaperWritingResult)
        assert 0 <= result.overall_score <= 10

    @pytest.mark.asyncio
    async def test_evaluate_empty_paper(self):
        """测试评估空论文"""
        benchmark = PaperWritingBenchmark()

        paper = {
            "topic": "",
            "literature": [],
            "thesis": "",
            "outline": "",
            "draft": ""
        }

        result = await benchmark.evaluate(paper)

        assert result.overall_score < 5

    @pytest.mark.asyncio
    async def test_evaluate_topic_quality(self):
        """测试评估选题质量"""
        benchmark = PaperWritingBenchmark()

        # 好的选题
        good_topic = await benchmark._evaluate_topic(
            "基于Transformer架构的大规模语言模型在学术论文写作辅助中的应用研究"
        )
        assert good_topic.score > 5

        # 差的选题
        bad_topic = await benchmark._evaluate_topic("AI")
        assert bad_topic.score < 5

    @pytest.mark.asyncio
    async def test_evaluate_literature_coverage(self):
        """测试评估文献覆盖"""
        benchmark = PaperWritingBenchmark()

        # 丰富的文献
        rich_lit = await benchmark._evaluate_literature([
            {"title": "P1", "source": "arXiv", "year": 2023, "citations": 500},
            {"title": "P2", "source": "PubMed", "year": 2024, "citations": 200},
            {"title": "P3", "source": "IEEE", "year": 2022, "citations": 100}
        ] * 5)
        assert rich_lit.score > 5

        # 贫乏的文献
        poor_lit = await benchmark._evaluate_literature([])
        assert poor_lit.score < 5

    def test_calculate_grade(self):
        """测试等级计算"""
        benchmark = PaperWritingBenchmark()

        assert benchmark._calculate_grade(9.5) == "A"
        assert benchmark._calculate_grade(8.5) == "B"
        assert benchmark._calculate_grade(7.5) == "C"
        assert benchmark._calculate_grade(6.5) == "D"
        assert benchmark._calculate_grade(5.0) == "F"


class TestABTestFramework:
    """测试A/B测试框架"""

    def test_framework_init(self):
        """测试框架初始化"""
        framework = ABTestFramework(significance_level=0.05)

        assert framework.significance_level == 0.05
        assert len(framework.experiments) == 0

    def test_create_config(self):
        """测试创建配置"""
        framework = ABTestFramework()

        config = framework.create_config(
            name="Test Config",
            llm_model="gpt-4"
        )

        assert config.name == "Test Config"
        assert config.llm_model == "gpt-4"
        assert config.config_id is not None

    def test_create_task(self):
        """测试创建任务"""
        framework = ABTestFramework()

        task = framework.create_task(
            description="测试任务",
            difficulty="hard"
        )

        assert task.description == "测试任务"
        assert task.difficulty == "hard"
        assert task.task_id is not None

    @pytest.mark.asyncio
    async def test_run_single_task(self):
        """测试运行单个任务"""
        framework = ABTestFramework()

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value="测试结果")

        task = TestTaskData(
            task_id="test_001",
            description="测试任务",
            expected_output="测试"
        )

        result = await framework._run_single_task(mock_agent, task, "config_1")

        assert result.task_id == "test_001"
        assert result.config_id == "config_1"

    def test_extract_score(self):
        """测试提取分数"""
        framework = ABTestFramework()

        # 成功结果
        success_result = MagicMock()
        success_result.success = True
        success_result.latency = 1.0
        success_result.metrics = {"quality_score": 0.9}

        score = framework._extract_score(success_result)
        assert score == 0.9

        # 失败结果
        failed_result = MagicMock()
        failed_result.success = False

        score = framework._extract_score(failed_result)
        assert score == 0.0

    def test_t_test(self):
        """测试t检验"""
        framework = ABTestFramework()

        control = [0.8, 0.85, 0.9, 0.75, 0.88]
        treatment = [0.85, 0.9, 0.95, 0.82, 0.92]

        p_value = framework._t_test(control, treatment)

        assert 0 <= p_value <= 1

    def test_t_test_identical(self):
        """测试相同数据t检验"""
        framework = ABTestFramework()

        data = [0.8, 0.85, 0.9]
        p_value = framework._t_test(data, data)

        assert p_value == 1.0  # 完全相同的分布，p值应为1

    def test_generate_report(self):
        """测试生成报告"""
        framework = ABTestFramework()

        result = ABTestResult(
            experiment_id="exp_001",
            control_config=AgentConfig(config_id="c1", name="Control"),
            treatment_config=AgentConfig(config_id="t1", name="Treatment"),
            control_results=[],
            treatment_results=[],
            control_mean=0.75,
            treatment_mean=0.85,
            improvement=13.33,
            absolute_difference=0.1,
            p_value=0.03,
            is_significant=True,
            confidence_level=0.97,
            test_type=TestTypeEnum.SIMULATION
        )

        report = framework.generate_report(result)

        assert "A/B" in report
        assert "Control" in report
        assert "Treatment" in report
        assert "显著" in report


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_gaia_evaluation(self):
        """完整GAIA评估流程"""
        benchmark = GAIABenchmark(level=1)

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value="测试响应")

        result = await benchmark.evaluate(mock_agent)

        assert result.total_tasks > 0
        assert 0 <= result.accuracy <= 1

    @pytest.mark.asyncio
    async def test_full_paper_evaluation(self):
        """完整论文评估流程"""
        benchmark = PaperWritingBenchmark()

        paper = {
            "topic": "深度学习在大规模图像分类中的应用与优化研究",
            "literature": [
                {"title": "ImageNet", "source": "arXiv", "year": 2023, "citations": 1000},
                {"title": "ResNet", "source": "IEEE", "year": 2022, "citations": 800},
            ] * 5,
            "thesis": "本研提出一种新的图像分类优化方法，显著提升准确率",
            "outline": "1.引言 2.相关工作 3.方法 4.实验 5.结论 6.参考文献",
            "draft": "这是详细的论文内容..." * 100,
        }

        result = await benchmark.evaluate(paper)

        assert result.overall_score > 0
        assert result.feedback is not None

    def test_all_evaluation_modules_importable(self):
        """测试所有评估模块可导入"""
        from src.agents_v2.evaluation.benchmarks import (
            GAIABenchmark,
            AgentBenchAdapter,
            PaperWritingBenchmark,
            ABTestFramework
        )

        assert GAIABenchmark is not None
        assert AgentBenchAdapter is not None
        assert PaperWritingBenchmark is not None
        assert ABTestFramework is not None
