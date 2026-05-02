"""
生成优化器 - Generation Optimizer

功能:
1. Prompt优化
2. 生成参数调优
3. 缓存优化
4. 批处理优化

设计原则:
- 自动Prompt优化
- 自适应参数
- 高效缓存
"""
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib


class OptimizationStrategy(str, Enum):
    """优化策略"""
    MINIMIZE_TOKENS = "minimize_tokens"  # 最小化token
    MAXIMIZE_QUALITY = "maximize_quality"  # 最大化质量
    BALANCED = "balanced"  # 平衡
    FAST = "fast"  # 快速生成


@dataclass
class GenerationConfig:
    """生成配置"""
    model: str = "minimax-m2.7"
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    strategy: OptimizationStrategy = OptimizationStrategy.BALANCED


@dataclass
class OptimizationResult:
    """优化结果"""
    original_config: GenerationConfig
    optimized_config: GenerationConfig
    improvements: List[str] = field(default_factory=list)
    estimated_token_savings: float = 0.0
    estimated_quality_change: float = 0.0


class GenerationOptimizer:
    """生成优化器"""

    def __init__(self):
        self._config_history: List[Tuple[GenerationConfig, float]] = []  # (config, quality_score)

    def optimize_config(
        self,
        task_type: str,
        context_length: Optional[str] = None
    ) -> GenerationConfig:
        """优化生成配置

        Args:
            task_type: 任务类型
            context_length: 上下文长度

        Returns:
            GenerationConfig: 优化后的配置
        """
        # 根据任务类型选择策略
        if task_type in ["summary", "extraction", "classification"]:
            strategy = OptimizationStrategy.MINIMIZE_TOKENS
        elif task_type in ["writing", "analysis", "reasoning"]:
            strategy = OptimizationStrategy.MAXIMIZE_QUALITY
        elif task_type == "chat":
            strategy = OptimizationStrategy.BALANCED
        else:
            strategy = OptimizationStrategy.FAST

        # 分析历史配置
        similar_configs = [
            (config, score)
            for config, score in self._config_history
            if config.strategy == strategy
        ]

        if similar_configs:
            # 使用表现最好的配置作为基础
            best_config = max(similar_configs, key=lambda x: x[1])[0]
            base_config = best_config
        else:
            base_config = GenerationConfig(strategy=strategy)

        # 根据上下文长度调整
        if context_length:
            if "short" in context_length.lower():
                base_config.max_tokens = min(base_config.max_tokens, 1000)
            elif "long" in context_length.lower():
                base_config.max_tokens = max(base_config.max_tokens, 4000)

        # 根据策略微调
        if strategy == OptimizationStrategy.MINIMIZE_TOKENS:
            base_config.temperature = 0.5
            base_config.max_tokens = min(base_config.max_tokens, 1500)
        elif strategy == OptimizationStrategy.MAXIMIZE_QUALITY:
            base_config.temperature = 0.8
            base_config.max_tokens = max(base_config.max_tokens, 3000)
        elif strategy == OptimizationStrategy.FAST:
            base_config.temperature = 0.3
            base_config.max_tokens = min(base_config.max_tokens, 1000)

        return base_config

    def optimize_prompt(
        self,
        prompt: str,
        task_type: str
    ) -> str:
        """优化Prompt

        Args:
            prompt: 原始prompt
            task_type: 任务类型

        Returns:
            str: 优化后的prompt
        """
        # 移除冗余空格
        optimized = " ".join(prompt.split())

        # 根据任务类型添加优化指令
        if task_type == "summary":
            if "简" not in optimized and "summary" not in optimized.lower():
                optimized = optimized + "\n\n请用简洁的语言总结。"
        elif task_type == "analysis":
            if "分析" not in optimized:
                optimized = optimized + "\n\n请进行深入分析。"
        elif task_type == "qa":
            if "回答" not in optimized:
                optimized = optimized + "\n\n请准确回答问题。"

        return optimized

    def record_result(
        self,
        config: GenerationConfig,
        quality_score: float
    ):
        """记录配置和结果用于学习

        Args:
            config: 使用的配置
            quality_score: 质量分数
        """
        self._config_history.append((config, quality_score))

        # 保持历史记录在合理范围内
        if len(self._config_history) > 100:
            self._config_history = self._config_history[-50:]

    def get_best_config(self, strategy: OptimizationStrategy) -> Optional[GenerationConfig]:
        """获取最佳配置"""
        similar = [
            (config, score)
            for config, score in self._config_history
            if config.strategy == strategy
        ]

        if not similar:
            return None

        return max(similar, key=lambda x: x[1])[0]


class PromptCache:
    """Prompt缓存"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, str] = {}
        self._access_times: Dict[str, float] = {}

    def get_cache_key(
        self,
        prompt: str,
        task_type: str,
        **kwargs
    ) -> str:
        """生成缓存键"""
        key_parts = [prompt[:100], task_type]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(
        self,
        prompt: str,
        task_type: str,
        **kwargs
    ) -> Optional[str]:
        """获取缓存的优化prompt"""
        cache_key = self.get_cache_key(prompt, task_type, **kwargs)
        result = self._cache.get(cache_key)

        if result:
            self._access_times[cache_key] = time.time()

        return result

    def set(
        self,
        prompt: str,
        task_type: str,
        optimized_prompt: str,
        **kwargs
    ):
        """设置缓存"""
        cache_key = self.get_cache_key(prompt, task_type, **kwargs)

        # LRU淘汰
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
            del self._cache[oldest_key]
            del self._access_times[oldest_key]

        self._cache[cache_key] = optimized_prompt
        self._access_times[cache_key] = time.time()

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._access_times.clear()


class BatchGenerationOptimizer:
    """批处理生成优化器"""

    def __init__(self, max_batch_size: int = 10):
        self.max_batch_size = max_batch_size

    def batch_prompts(
        self,
        prompts: List[str],
        strategy: str = "similar_length"
    ) -> List[List[str]]:
        """将prompts分批

        Args:
            prompts: prompt列表
            strategy: 分批策略

        Returns:
            List[List[str]]: 批次列表
        """
        if strategy == "similar_length":
            # 按相似长度分批，减少padding
            sorted_prompts = sorted(enumerate(prompts), key=lambda x: len(x[1]))
            batches = []
            current_batch = []
            current_avg = 0

            for idx, prompt in sorted_prompts:
                if not current_batch:
                    current_batch.append(prompt)
                    current_avg = len(prompt)
                elif len(prompt) / current_avg < 2:  # 长度差异小于2倍
                    current_batch.append(prompt)
                    current_avg = (current_avg * (len(current_batch) - 1) + len(prompt)) / len(current_batch)
                else:
                    batches.append(current_batch)
                    current_batch = [prompt]
                    current_avg = len(prompt)

            if current_batch:
                batches.append(current_batch)

            return batches

        elif strategy == "fixed_size":
            # 固定大小分批
            return [
                prompts[i:i + self.max_batch_size]
                for i in range(0, len(prompts), self.max_batch_size)
            ]

        else:
            return [prompts]


# 便捷函数
def optimize_generation(
    task_type: str,
    context_length: Optional[str] = None
) -> GenerationConfig:
    """便捷生成优化函数"""
    optimizer = GenerationOptimizer()
    return optimizer.optimize_config(task_type, context_length)
