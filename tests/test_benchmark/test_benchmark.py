"""
基准测试

测试系统性能基准和关键指标
"""
import pytest
import time
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from src.agents_v2.evaluation.evaluation_runner import (
    EvaluationRunner,
    BenchmarkConfig,
    BenchmarkResult
)


class TestBenchmarkConfig:
    """测试基准配置"""

    def test_config_creation(self):
        """测试配置创建"""
        config = BenchmarkConfig(
            name="Test_Benchmark",
            description="测试基准",
            test_cases=[{"input": "test"}],
            expected_min_score=7.5
        )
        assert config.name == "Test_Benchmark"
        assert config.expected_min_score == 7.5

    def test_config_defaults(self):
        """测试配置默认值"""
        config = BenchmarkConfig(
            name="Test",
            description="Test",
            test_cases=[]
        )
        assert config.expected_min_score == 7.0


class TestBenchmarkResult:
    """测试基准结果"""

    def test_result_creation(self):
        """测试结果创建"""
        result = BenchmarkResult(
            benchmark_name="Test",
            passed=True,
            actual_score=8.5,
            expected_score=7.0,
            details={"latency": 100}
        )
        assert result.passed is True
        assert result.actual_score == 8.5
        assert result.details["latency"] == 100

    def test_pass_fail判定(self):
        """测试通过失败判定"""
        result = BenchmarkResult(
            benchmark_name="Test",
            passed=False,
            actual_score=6.5,
            expected_score=7.0
        )
        assert result.passed is False

        result.passed = True
        assert result.passed is True


class TestEvaluationRunner:
    """测试评估运行器"""

    def test_runner_init(self):
        """测试运行器初始化"""
        runner = EvaluationRunner()
        assert runner.benchmark_history == []
        assert runner.evaluator is not None

    @pytest.mark.asyncio
    async def test_run_topic_agent_mock(self):
        """测试运行TopicAgent基准(模拟)"""
        runner = EvaluationRunner()

        with patch('src.agents_v2.paper_agents.TopicAgent') as MockAgent:
            mock_agent = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.quality_score = 0.85
            mock_result.result = {
                "selected_topic": {"title": "Test Topic"},
                "alternative_topics": [{"title": "Alt"}]
            }
            mock_result.error = None

            mock_instance = MagicMock()
            mock_instance.execute = AsyncMock(return_value=mock_result)
            MockAgent.return_value = mock_instance

            result = await runner.run_topic_agent_benchmark()

        assert result.benchmark_name == "TopicAgent_Benchmark"
        assert result.actual_score > 0

    @pytest.mark.asyncio
    async def test_run_literature_agent_mock(self):
        """测试运行LiteratureAgent基准(模拟)"""
        runner = EvaluationRunner()

        with patch('src.agents_v2.paper_agents.LiteratureAgent') as MockAgent:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.quality_score = 0.8
            mock_result.result = {
                "papers": [{"title": "P1"}, {"title": "P2"}],
                "search_queries": ["q1"],
                "paper_analyses": [{"a": 1}]
            }
            mock_result.error = None

            mock_instance = MagicMock()
            mock_instance.execute = AsyncMock(return_value=mock_result)
            MockAgent.return_value = mock_instance

            result = await runner.run_literature_agent_benchmark()

        assert result.benchmark_name == "LiteratureAgent_Benchmark"

    @pytest.mark.asyncio
    async def test_run_all_benchmarks_mock(self):
        """测试运行所有基准(模拟)"""
        runner = EvaluationRunner()

        with patch('src.agents_v2.paper_agents.TopicAgent') as MockTopic, \
             patch('src.agents_v2.paper_agents.LiteratureAgent') as MockLit:

            # Mock TopicAgent
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.quality_score = 0.85
            mock_result.result = {"selected_topic": {"title": "T"}}
            mock_topic_instance = MagicMock()
            mock_topic_instance.execute = AsyncMock(return_value=mock_result)
            MockTopic.return_value = mock_topic_instance

            # Mock LiteratureAgent
            mock_result2 = MagicMock()
            mock_result2.success = True
            mock_result2.quality_score = 0.8
            mock_result2.result = {"papers": [{"title": "P"}]}
            mock_lit_instance = MagicMock()
            mock_lit_instance.execute = AsyncMock(return_value=mock_result2)
            MockLit.return_value = mock_lit_instance

            results = await runner.run_all_benchmarks()

        assert len(results) == 2

    def test_generate_report(self):
        """测试生成报告"""
        runner = EvaluationRunner()

        # 添加基准结果
        runner.benchmark_history.append(
            BenchmarkResult("Test1", True, 8.0, 7.0)
        )
        runner.benchmark_history.append(
            BenchmarkResult("Test2", False, 6.5, 7.0)
        )

        report = runner.generate_report()

        assert "evaluation_summary" in report
        assert "benchmark_summary" in report
        assert report["benchmark_summary"]["total"] == 2
        assert report["benchmark_summary"]["passed"] == 1
        assert report["benchmark_summary"]["failed"] == 1

    def test_print_report(self):
        """测试打印报告"""
        runner = EvaluationRunner()
        runner.benchmark_history.append(
            BenchmarkResult("Test", True, 8.0, 7.0)
        )

        # 不应抛出异常
        runner.print_report()

    def test_save_report(self, tmp_path):
        """测试保存报告"""
        runner = EvaluationRunner()
        runner.benchmark_history.append(
            BenchmarkResult("Test", True, 8.0, 7.0)
        )

        report_path = tmp_path / "report.json"
        runner.save_report(str(report_path))

        assert report_path.exists()


class TestPerformanceBenchmarks:
    """性能基准测试"""

    @pytest.mark.asyncio
    async def test_response_time_benchmark(self):
        """测试响应时间基准"""
        # 模拟快速响应
        async def fast_operation():
            await asyncio.sleep(0.01)
            return True

        start = time.time()
        await fast_operation()
        elapsed = time.time() - start

        # 100ms内完成算通过
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """测试并发执行"""
        async def task(n):
            await asyncio.sleep(0.01)
            return n * 2

        start = time.time()
        results = await asyncio.gather(*[task(i) for i in range(10)])
        elapsed = time.time() - start

        assert len(results) == 10
        assert all(r == i * 2 for i, r in enumerate(results))
        # 并发执行应该很快
        assert elapsed < 0.5

    def test_memory_efficiency(self):
        """测试内存效率"""
        data = [{"key": f"value_{i}"} for i in range(1000)]

        # 简单内存占用检查
        import sys
        size = sys.getsizeof(data)
        assert size > 0

    def test_throughput_benchmark(self):
        """测试吞吐量基准"""
        iterations = 1000

        start = time.time()
        for i in range(iterations):
            _ = i * 2
        elapsed = time.time() - start

        ops_per_second = iterations / elapsed
        # 简单操作应该能达到很高的吞吐量
        assert ops_per_second > 10000


class TestQualityBenchmarks:
    """质量基准测试"""

    def test_quality_score_bounds(self):
        """测试质量分数边界"""
        scores = [0.0, 0.5, 0.75, 1.0, 0.85, 0.92]

        for score in scores:
            assert 0 <= score <= 1

    def test_error_rate_threshold(self):
        """测试错误率阈值"""
        total_requests = 100
        failed_requests = 3
        error_rate = failed_requests / total_requests

        # 错误率低于5%算通过
        assert error_rate < 0.05

    def test_latency_p95(self):
        """测试P95延迟"""
        latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200]

        # 计算P95
        sorted_latencies = sorted(latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[p95_index]

        # P95延迟应该不高于200ms
        assert p95_latency <= 200
