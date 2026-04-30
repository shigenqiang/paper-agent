"""
成本优化器 - Cost Optimizer

实现LLM调用成本优化:
- 模型降级
- 缓存复用
- 批处理
- 摘要压缩
"""
import time
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class CostConfig:
    """成本配置"""
    primary_model: str = "gpt-4"
    fallback_model: str = "gpt-3.5-turbo"
    cache_enabled: bool = True
    batch_size: int = 10
    cache_ttl: float = 3600.0  # 秒


@dataclass
class CostMetrics:
    """成本指标"""
    total_calls: int = 0
    cached_calls: int = 0
    fallback_calls: int = 0
    total_cost: float = 0.0
    latency_total: float = 0.0

    @property
    def cache_hit_rate(self) -> float:
        return self.cached_calls / self.total_calls if self.total_calls > 0 else 0.0


class CostOptimizer:
    """成本优化器

    优化策略:
    1. 模型降级: 在合适场景使用便宜模型
    2. 缓存复用: 相同查询返回缓存结果
    3. 批处理: 合并多个请求减少开销
    4. 摘要压缩: 压缩上下文减少token
    """

    def __init__(self, config: CostConfig = None):
        """初始化

        Args:
            config: 成本配置
        """
        self.config = config or CostConfig()
        self._cache: Dict[str, Any] = {}
        self._cache_times: Dict[str, float] = {}
        self._batch_queue: List[Tuple[str, Callable]] = []
        self._batch_results: Dict[str, Any] = {}
        self.metrics = CostMetrics()

        # 模型价格 (每1K token)
        self.model_prices = {
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.002,
            "claude-3": 0.015,
            "claude-3-haiku": 0.00025
        }

    def _get_cache_key(self, prompt: str) -> str:
        """生成缓存键"""
        return hashlib.md5(prompt.encode()).hexdigest()

    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self._cache:
            return False

        if self.config.cache_ttl > 0:
            age = time.time() - self._cache_times.get(key, 0)
            return age < self.config.cache_ttl

        return True

    async def execute_with_fallback(self,
                                     prompt: str,
                                     primary_func: Callable,
                                     fallback_func: Callable,
                                     use_cache: bool = True) -> Any:
        """带降级策略的执行

        Args:
            prompt: 提示词
            primary_func: 主模型执行函数
            fallback_func: 降级模型执行函数
            use_cache: 是否使用缓存

        Returns:
            Any: 执行结果
        """
        start_time = time.time()

        # 缓存检查
        if use_cache and self.config.cache_enabled:
            cache_key = self._get_cache_key(prompt)
            if self._is_cache_valid(cache_key):
                self.metrics.cached_calls += 1
                logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
                return self._cache[cache_key]

        # 估算成本 (简单用长度估算)
        estimated_tokens = len(prompt) // 4

        # 简单查询使用降级模型
        use_fallback = self._should_use_fallback(prompt, estimated_tokens)

        try:
            if use_fallback:
                self.metrics.fallback_calls += 1
                result = await fallback_func(prompt)
            else:
                result = await primary_func(prompt)

            # 缓存结果
            if self.config.cache_enabled:
                cache_key = self._get_cache_key(prompt)
                self._cache[cache_key] = result
                self._cache_times[cache_key] = time.time()

            # 更新指标
            self.metrics.total_calls += 1
            model = self.config.fallback_model if use_fallback else self.config.primary_model
            cost = self._estimate_cost(estimated_tokens, model)
            self.metrics.total_cost += cost
            self.metrics.latency_total += time.time() - start_time

            return result

        except Exception as e:
            logger.error(f"执行失败，尝试降级: {e}")

            # 降级重试
            if not use_fallback:
                self.metrics.fallback_calls += 1
                try:
                    result = await fallback_func(prompt)
                    return result
                except Exception as fallback_error:
                    logger.error(f"降级执行也失败: {fallback_error}")
                    raise

            raise

    def _should_use_fallback(self, prompt: str, estimated_tokens: int) -> bool:
        """判断是否使用降级模型"""
        # 简单任务 (< 500 tokens) 或重复查询使用降级
        if estimated_tokens < 500:
            return True

        # 检查是否重复
        cache_key = self._get_cache_key(prompt)
        if cache_key in self._cache:
            return True

        return False

    def _estimate_cost(self, tokens: int, model: str) -> float:
        """估算成本"""
        price = self.model_prices.get(model, 0.002)
        return (tokens / 1000) * price

    async def execute_batch(self,
                            items: List[str],
                            exec_func: Callable,
                            use_cache: bool = True) -> List[Any]:
        """批量执行

        Args:
            items: 项目列表
            exec_func: 执行函数
            use_cache: 是否使用缓存

        Returns:
            List[Any]: 结果列表
        """
        results = []

        # 按批次处理
        for i in range(0, len(items), self.config.batch_size):
            batch = items[i:i + self.config.batch_size]
            batch_results = []

            for item in batch:
                # 检查缓存
                if use_cache and self.config.cache_enabled:
                    cache_key = self._get_cache_key(item)
                    if self._is_cache_valid(cache_key):
                        self.metrics.cached_calls += 1
                        batch_results.append(self._cache[cache_key])
                        continue

                # 执行
                result = await exec_func(item)
                batch_results.append(result)

                # 缓存
                if self.config.cache_enabled:
                    cache_key = self._get_cache_key(item)
                    self._cache[cache_key] = result
                    self._cache_times[cache_key] = time.time()

            results.extend(batch_results)

        self.metrics.total_calls += len(items)
        return results

    def compress_context(self, context: str, max_length: int = 4000) -> str:
        """压缩上下文

        Args:
            context: 上下文文本
            max_length: 最大长度

        Returns:
            str: 压缩后的上下文
        """
        if len(context) <= max_length:
            return context

        # 简单压缩：截断并保留关键信息
        compressed = context[:max_length]

        # 尝试在句子边界截断
        last_period = compressed.rfind("。")
        last_newline = compressed.rfind("\n")

        cutoff = max(last_period, last_newline)
        if cutoff > max_length * 0.7:
            compressed = context[:cutoff + 1]

        logger.debug(f"Context compressed: {len(context)} -> {len(compressed)}")
        return compressed

    def get_stats(self) -> Dict[str, Any]:
        """获取成本统计

        Returns:
            Dict: 统计信息
        """
        return {
            "total_calls": self.metrics.total_calls,
            "cached_calls": self.metrics.cached_calls,
            "cache_hit_rate": self.metrics.cache_hit_rate,
            "fallback_calls": self.metrics.fallback_calls,
            "total_cost": self.metrics.total_cost,
            "avg_latency": self.metrics.latency_total / self.metrics.total_calls if self.metrics.total_calls > 0 else 0
        }

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self._cache_times.clear()
        logger.info("Cost optimizer cache cleared")


# 便捷函数
def create_cost_optimizer(
    primary_model: str = "gpt-4",
    fallback_model: str = "gpt-3.5-turbo",
    cache_enabled: bool = True
) -> CostOptimizer:
    """创建成本优化器"""
    config = CostConfig(
        primary_model=primary_model,
        fallback_model=fallback_model,
        cache_enabled=cache_enabled
    )
    return CostOptimizer(config=config)