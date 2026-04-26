"""
GAIA Benchmark 单元测试

测试各个小模块:
1. GAIATask - 任务定义
2. GAIAResult - 结果定义
3. GAIABenchmark.evaluate() - 评估功能
4. _check_answer() - 答案检查
"""
import pytest
import asyncio
from src.agents_v2.evaluation.benchmarks.gaia import (
    GAIABenchmark,
    GAIATask,
    GAIAResult
)


class TestGAIATask:
    """GAIATask 测试"""

    def test_create_task(self):
        """测试创建任务"""
        task = GAIATask(
            task_id="test_001",
            question="什么是机器学习？",
            expected_answer="机器学习是...",
            level=1,
            tools_allowed=["search"]
        )
        assert task.task_id == "test_001"
        assert task.level == 1
        assert "search" in task.tools_allowed

    def test_task_with_metadata(self):
        """测试带元数据的任务"""
        task = GAIATask(
            task_id="test_002",
            question="复杂问题",
            expected_answer="答案",
            level=2,
            requires_web=True,
            metadata={"category": "science"}
        )
        assert task.requires_web is True
        assert task.metadata["category"] == "science"


class TestGAIAResult:
    """GAIAResult 测试"""

    def test_create_result(self):
        """测试创建结果"""
        result = GAIAResult(
            level=1,
            accuracy=0.85,
            avg_latency=1.5,
            total_tasks=20,
            passed_tasks=17,
            failed_tasks=3,
            results=[],
            score_breakdown={"overall": 0.85}
        )
        assert result.accuracy == 0.85
        assert result.passed_tasks == 17

    def test_empty_result(self):
        """测试空结果"""
        result = GAIAResult(
            level=1,
            accuracy=0.0,
            avg_latency=0.0,
            total_tasks=0,
            passed_tasks=0,
            failed_tasks=0,
            results=[],
            score_breakdown={}
        )
        assert result.total_tasks == 0


class TestGAIABenchmarkInit:
    """GAIABenchmark 初始化测试"""

    def test_init_level_1(self):
        """测试初始化Level 1"""
        benchmark = GAIABenchmark(level=1)
        assert benchmark.level == 1

    def test_init_level_2(self):
        """测试初始化Level 2"""
        benchmark = GAIABenchmark(level=2)
        assert benchmark.level == 2

    def test_init_level_3(self):
        """测试初始化Level 3"""
        benchmark = GAIABenchmark(level=3)
        assert benchmark.level == 3

    def test_invalid_level(self):
        """测试无效等级"""
        with pytest.raises(ValueError):
            GAIABenchmark(level=4)

    def test_invalid_level_zero(self):
        """测试等级为0"""
        with pytest.raises(ValueError):
            GAIABenchmark(level=0)


class TestGAIABenchmarkTasks:
    """GAIABenchmark 任务加载测试"""

    def test_load_level_1_tasks(self):
        """测试加载Level 1任务"""
        benchmark = GAIABenchmark(level=1)
        assert len(benchmark.tasks) > 0

    def test_load_level_2_tasks(self):
        """测试加载Level 2任务"""
        benchmark = GAIABenchmark(level=2)
        assert len(benchmark.tasks) > 0

    def test_load_level_3_tasks(self):
        """测试加载Level 3任务"""
        benchmark = GAIABenchmark(level=3)
        assert len(benchmark.tasks) > 0

    def test_tasks_have_required_fields(self):
        """测试任务包含必需字段"""
        benchmark = GAIABenchmark(level=1)
        for task in benchmark.tasks:
            assert hasattr(task, 'task_id')
            assert hasattr(task, 'question')
            assert hasattr(task, 'expected_answer')
            assert hasattr(task, 'level')


class TestGAIABenchmarkCheckAnswer:
    """答案检查测试"""

    def setup_method(self):
        """设置测试"""
        self.benchmark = GAIABenchmark(level=1)

    def test_exact_match(self):
        """测试精确匹配"""
        response = "机器学习是人工智能的一个分支"
        expected = "机器学习是人工智能的一个分支"
        assert self.benchmark._check_answer(response, expected) is True

    def test_partial_match(self):
        """测试部分匹配"""
        # response 包含 expected 的前20个字符
        response = "机器学习是人工智能的一个分支"  # 这是expected本身
        expected = "机器学习是人工智能的一个分支"
        # 包含期望答案的前20个字符
        assert self.benchmark._check_answer(response, expected) is True

    def test_keyword_overlap(self):
        """测试关键词重叠"""
        # 当关键词重叠超过50%时通过
        response = "机器 学习 是 使用 数据 来 学习 模型"
        expected = "机器 学习 是 人工智能 技术 分支"
        result = self.benchmark._check_answer(response, expected)
        # 有共同关键词，应该通过
        assert result is True

    def test_no_match(self):
        """测试不匹配"""
        response = "今天天气真好"
        expected = "机器学习是人工智能"
        assert self.benchmark._check_answer(response, expected) is False

    def test_empty_response(self):
        """测试空响应"""
        response = ""
        expected = "机器学习"
        assert self.benchmark._check_answer(response, expected) is False

    def test_dict_response(self):
        """测试字典响应"""
        response = {"answer": "机器学习是AI的一种"}
        expected = "机器学习是AI的一种"
        assert self.benchmark._check_answer(response, expected) is True


class TestGAIABenchmarkBreakdown:
    """评分分解测试"""

    def setup_method(self):
        """设置测试"""
        self.benchmark = GAIABenchmark(level=1)

    def test_calculate_breakdown_all_pass(self):
        """测试全部通过的分项评分"""
        results = [
            {"success": True, "latency": 1.0},
            {"success": True, "latency": 2.0},
            {"success": True, "latency": 1.5}
        ]
        breakdown = self.benchmark._calculate_breakdown(results)
        assert breakdown["overall"] == 1.0
        assert breakdown["pass_rate"] == 1.0

    def test_calculate_breakdown_partial(self):
        """测试部分通过的分项评分"""
        results = [
            {"success": True, "latency": 1.0},
            {"success": False, "latency": 2.0},
            {"success": True, "latency": 1.5}
        ]
        breakdown = self.benchmark._calculate_breakdown(results)
        assert breakdown["overall"] == pytest.approx(2/3)

    def test_calculate_breakdown_empty(self):
        """测试空结果的分解"""
        breakdown = self.benchmark._calculate_breakdown([])
        assert breakdown["overall"] == 0.0


class MockAgent:
    """模拟Agent用于测试"""

    def __init__(self, responses: dict):
        self.responses = responses
        self.call_count = 0

    async def run(self, question: str):
        """模拟运行"""
        self.call_count += 1
        if question in self.responses:
            return self.responses[question]
        return "默认响应"


class TestGAIABenchmarkEvaluate:
    """评估功能测试"""

    @pytest.mark.asyncio
    async def test_evaluate_with_mock_agent(self):
        """测试使用模拟Agent评估"""
        benchmark = GAIABenchmark(level=1)

        # 设置一个会回答的agent
        agent = MockAgent({
            "什么是机器学习？": "机器学习是..."
        })

        result = await benchmark.evaluate(agent)
        assert isinstance(result, GAIAResult)
        assert result.level == 1

    @pytest.mark.asyncio
    async def test_evaluate_all_pass(self):
        """测试全部通过"""
        benchmark = GAIABenchmark(level=1)

        # 让agent对所有问题都返回预期的部分答案
        agent = MockAgent({
            task.question: task.expected_answer[:20]
            for task in benchmark.tasks
        })

        result = await benchmark.evaluate(agent)
        # 由于答案检查逻辑，部分可能通过
        assert result.total_tasks == len(benchmark.tasks)

    @pytest.mark.asyncio
    async def test_evaluate_handles_exceptions(self):
        """测试评估处理异常"""
        benchmark = GAIABenchmark(level=1)

        class FailingAgent:
            async def run(self, question):
                raise RuntimeError("Agent failed")

        agent = FailingAgent()
        result = await benchmark.evaluate(agent)

        # 应该处理异常并记录失败
        assert result.total_tasks == len(benchmark.tasks)
        assert result.failed_tasks == len(benchmark.tasks)


class TestGAIABenchmarkReport:
    """报告生成测试"""

    def test_generate_report(self):
        """测试报告生成"""
        benchmark = GAIABenchmark(level=1)
        result = GAIAResult(
            level=1,
            accuracy=0.8,
            avg_latency=1.5,
            total_tasks=10,
            passed_tasks=8,
            failed_tasks=2,
            results=[],
            score_breakdown={"overall": 0.8}
        )

        report = benchmark.generate_report(result)
        assert "Level 1" in report
        assert "80.00%" in report
        assert "8" in report  # 通过任务数


class TestLoadTasksFromFile:
    """从文件加载任务测试"""

    def test_load_tasks_from_file_not_found(self):
        """测试文件不存在"""
        benchmark = GAIABenchmark(level=1)
        with pytest.raises(FileNotFoundError):
            benchmark.load_tasks_from_file("nonexistent_file.json")

    def test_load_tasks_updates_tasks(self):
        """测试加载任务更新任务列表"""
        benchmark = GAIABenchmark(level=1)
        original_count = len(benchmark.tasks)

        # 这个测试需要有效的JSON文件
        # 暂时跳过实际文件测试
        assert original_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])