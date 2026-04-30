"""
性能基准测试

测试系统的基本性能指标
"""
import pytest
import time
import asyncio


class TestPerformanceBenchmarks:
    """性能基准测试"""

    def test_validator_performance(self):
        """测试验证器性能"""
        from src.agents_v2.core.validators import InputValidator, ValidationType

        validator = InputValidator()
        validator.add_rule("name", ValidationType.STRING, min_length=1, max_length=100)
        validator.add_rule("age", ValidationType.INTEGER, min_value=0, max_value=150)
        validator.add_rule("email", ValidationType.PATTERN, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')

        # 准备测试数据
        test_data = {
            "name": "张三",
            "age": 25,
            "email": "test@example.com"
        }

        # 性能测试：1000次验证
        iterations = 1000
        start = time.time()
        for _ in range(iterations):
            validator.validate(test_data)
        elapsed = time.time() - start

        avg_ms = (elapsed / iterations) * 1000
        print(f"\nValidator: {iterations} iterations in {elapsed:.3f}s, avg {avg_ms:.4f}ms/iteration")

        # 性能断言：平均每次验证应该小于1ms
        assert avg_ms < 1.0, f"Validator too slow: {avg_ms:.4f}ms per iteration"

    def test_cache_performance(self):
        """测试缓存性能"""
        from src.agents_v2.unified.cache import ResultCache

        cache = ResultCache(default_ttl=3600)

        # 性能测试：10000次缓存操作
        iterations = 10000
        test_data = {"key": f"value_{i}" for i in range(10)}

        start = time.time()
        for i in range(iterations):
            cache.set(f"key_{i % 100}", test_data)  # 100个不同key，循环使用
            cache.get(f"key_{i % 100}")
        elapsed = time.time() - start

        avg_us = (elapsed / iterations) * 1000000
        print(f"\nCache: {iterations} operations in {elapsed:.3f}s, avg {avg_us:.2f}μs/operation")

        # 性能断言：平均每次操作应该小于500μs
        assert avg_us < 500, f"Cache too slow: {avg_us:.2f}μs per operation"

    def test_cache_hit_rate(self):
        """测试缓存命中率"""
        from src.agents_v2.unified.cache import ResultCache

        cache = ResultCache()

        # 先填充缓存
        for i in range(100):
            cache.set(f"key_{i}", {"data": f"value_{i}"})

        # 测试命中
        hits = 0
        for i in range(1000):
            result = cache.get(f"key_{i % 100}")
            if result is not None:
                hits += 1

        hit_rate = hits / 1000
        print(f"\nCache hit rate: {hits}/1000 = {hit_rate:.1%}")

        # 缓存应该100%命中（因为我们只用了100个key循环1000次）
        assert hit_rate == 1.0, f"Expected 100% hit rate, got {hit_rate:.1%}"

    def test_llm_optimizer_cache(self):
        """测试LLM优化器缓存"""
        from src.agents_v2.unified.cache import LLMLCallOptimizer

        optimizer = LLMLCallOptimizer(enable_cache=True)

        # 生成请求键
        key1 = optimizer._make_request_key("test prompt", temperature=0.7)
        key2 = optimizer._make_request_key("test prompt", temperature=0.7)
        key3 = optimizer._make_request_key("different prompt", temperature=0.7)

        # 相同请求应该生成相同键
        assert key1 == key2, "Same prompts should generate same key"
        # 不同请求应该生成不同键
        assert key1 != key3, "Different prompts should generate different keys"

    def test_sanitizer_performance(self):
        """测试输入清理性能"""
        from src.agents_v2.core.security import InputSanitizer

        sanitizer = InputSanitizer()
        test_input = "<script>alert('xss');</script>" + "a" * 1000

        iterations = 100
        start = time.time()
        for _ in range(iterations):
            sanitizer.sanitize(test_input)
        elapsed = time.time() - start

        avg_ms = (elapsed / iterations) * 1000
        print(f"\nSanitizer: {iterations} iterations in {elapsed:.3f}s, avg {avg_ms:.4f}ms/iteration")

        # 性能断言：平均每次清理应该小于20ms
        assert avg_ms < 20, f"Sanitizer too slow: {avg_ms:.4f}ms per iteration"

    def test_error_classifier_performance(self):
        """测试错误分类器性能"""
        from src.agents_v2.unified.error_handler import ErrorClassifier

        test_errors = [
            Exception("OpenAI API timeout"),
            Exception("JSON decode error"),
            Exception("arXiv HTTP 500"),
            Exception("validation failed"),
            Exception("some random error")
        ]

        iterations = 1000
        start = time.time()
        for _ in range(iterations):
            for error in test_errors:
                ErrorClassifier.classify(error)
        elapsed = time.time() - start

        total_ops = iterations * len(test_errors)
        avg_us = (elapsed / total_ops) * 1000000
        print(f"\nErrorClassifier: {total_ops} operations in {elapsed:.3f}s, avg {avg_us:.2f}μs/operation")

        # 性能断言：平均每次分类应该小于50μs
        assert avg_us < 50, f"ErrorClassifier too slow: {avg_us:.2f}μs per operation"

    @pytest.mark.asyncio
    async def test_concurrent_executor_performance(self):
        """测试并发执行器性能"""
        from src.agents_v2.unified.monitoring import ConcurrentExecutor

        executor = ConcurrentExecutor(max_concurrent=10)

        async def task(i):
            await asyncio.sleep(0.001)  # 1ms任务
            return i * 2

        iterations = 5
        tasks_per_iteration = 20

        start = time.time()
        for _ in range(iterations):
            tasks = [lambda i=i: task(i) for i in range(tasks_per_iteration)]
            await executor.execute(tasks)
        elapsed = time.time() - start

        total_tasks = iterations * tasks_per_iteration
        avg_ms = (elapsed / total_tasks) * 1000
        print(f"\nConcurrentExecutor: {total_tasks} tasks in {elapsed:.3f}s, avg {avg_ms:.2f}ms/task")

        # 性能断言：平均每个任务应该小于5ms（考虑并发）
        assert avg_ms < 5.0, f"ConcurrentExecutor too slow: {avg_ms:.2f}ms per task"


class TestConcurrentStability:
    """并发稳定性测试"""

    @pytest.mark.asyncio
    async def test_concurrent_agent_calls(self):
        """测试并发Agent调用稳定性"""
        from src.agents_v2.paper_agents import TopicAgent

        agent = TopicAgent()

        async def call_agent(i):
            try:
                result = await agent.execute({"user_request": f"test_{i % 5}"})
                return result.success
            except Exception:
                return False

        # 并发50次调用
        tasks = [call_agent(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if r is True)
        print(f"\nConcurrent calls: {success_count}/50 succeeded")

        # 至少90%应该成功（考虑可能的API限制）
        assert success_count >= 45, f"Too many failures: {50 - success_count}/50 failed"

    @pytest.mark.asyncio
    async def test_rate_limiter_stability(self):
        """测试限流器稳定性"""
        from src.agents_v2.monitoring.alerts import RateLimiter

        limiter = RateLimiter(max_requests=10, window=1)

        # 快速消耗配额
        allowed = 0
        for i in range(20):
            if limiter.is_allowed(f"user_{i % 5}"):
                allowed += 1

        print(f"\nRate limiter: {allowed}/20 requests allowed for 5 users")

        # 每个用户最多10个请求，5个用户 = 50请求配额
        # 但我们只发了20次，所以至少应该允许一些
        assert allowed > 0, "Rate limiter blocked all requests"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
