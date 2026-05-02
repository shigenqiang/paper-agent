"""
LLM Call with Fallback - 多层降级LLM调用

层级降级:
1. 主模型 (gpt-4)
2. 次级模型 (gpt-3.5-turbo)
3. 本地模型 (llama3:70b)
4. 缓存结果
5. 默认回复
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from src.agents_v2.logging_config import get_logging_logger

import time

import hashlib

logger = get_logging_logger(__name__)


class ModelLevel(str, Enum):
    """模型层级"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    LOCAL = "local"
    CACHE = "cache"
    NONE = "none"


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    quality: float
    model: str
    latency: float = 0.0
    from_cache: bool = False
    error: Optional[str] = None


@dataclass
class ModelConfig:
    """模型配置"""
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: float = 30.0


class LRUCache:
    """简单LRU缓存"""

    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Any] = {}
        self._max_size = max_size
        self._access_order: List[str] = []

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self._cache:
            # 更新访问顺序
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """设置缓存"""
        if key in self._cache:
            self._access_order.remove(key)
        elif len(self._cache) >= self._max_size:
            # 删除最旧的
            oldest = self._access_order.pop(0)
            del self._cache[oldest]

        self._cache[key] = value
        self._access_order.append(key)

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._access_order.clear()


class LLMCallWithFallback:
    """
    带降级策略的LLM调用

    层级降级:
    1. 主模型 (primary)
    2. 次级模型 (secondary)
    3. 本地模型 (local)
    4. 缓存结果 (cache)
    5. 默认回复 (none)

    使用示例:
        caller = LLMCallWithFallback(agent=my_agent)

        response = await caller.call_with_fallback(
            prompt="写一首诗",
            required_quality=0.7,
            context={"style": "古典"}
        )

        print(f"Response: {response.content}")
        print(f"Model used: {response.model}")
        print(f"Quality: {response.quality}")
    """

    def __init__(
        self,
        agent: Any,
        primary_config: Optional[ModelConfig] = None,
        secondary_config: Optional[ModelConfig] = None,
        local_config: Optional[ModelConfig] = None,
        cache_ttl_seconds: float = 3600
    ):
        """
        初始化LLM调用器

        Args:
            agent: Agent实例
            primary_config: 主模型配置
            secondary_config: 次级模型配置
            local_config: 本地模型配置
            cache_ttl_seconds: 缓存TTL
        """
        self.agent = agent
        self._cache = LRUCache(max_size=1000)
        self._cache_ttl = cache_ttl_seconds
        self._cache_timestamps: Dict[str, float] = {}

        # 模型配置
        self._model_configs = {
            "primary": primary_config or ModelConfig(model="gpt-4", temperature=0.7, max_tokens=2048, timeout=30),
            "secondary": secondary_config or ModelConfig(model="gpt-3.5-turbo", temperature=0.5, max_tokens=1024, timeout=15),
            "local": local_config or ModelConfig(model="llama3:70b", temperature=0.6, max_tokens=1024, timeout=60)
        }

        # 降级配置
        self._fallback_configs = {
            "primary": {"quality_threshold": 0.7, "next_level": "secondary"},
            "secondary": {"quality_threshold": 0.63, "next_level": "local"},  # 0.7 * 0.9
            "local": {"quality_threshold": 0.56, "next_level": "cache"},  # 0.7 * 0.8
            "cache": {"quality_threshold": 0.0, "next_level": "none"},
        }

        # 统计
        self._call_stats = {
            "total_calls": 0,
            "cache_hits": 0,
            "model_failures": {k: 0 for k in self._model_configs.keys()}
        }

    async def call_with_fallback(
        self,
        prompt: str,
        required_quality: float = 0.7,
        context: Optional[Dict[str, Any]] = None,
        fallback_content: Optional[str] = None
    ) -> LLMResponse:
        """
        带降级的LLM调用

        Args:
            prompt: 提示词
            required_quality: 最低质量要求
            context: 上下文（用于缓存键生成）
            fallback_content: 默认回复内容

        Returns:
            LLMResponse: 包含结果和质量信息
        """
        self._call_stats["total_calls"] += 1

        # 1. 检查缓存
        cache_key = self._generate_cache_key(prompt, context)
        cached = self._get_from_cache(cache_key)
        if cached:
            cached.from_cache = True
            self._call_stats["cache_hits"] += 1
            logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
            return cached

        # 2. 尝试主模型
        try:
            response = await self._call_model("primary", prompt)
            if response.quality >= required_quality:
                self._save_to_cache(cache_key, response)
                return response
        except Exception as e:
            logger.warning(f"Primary model failed: {e}")
            self._call_stats["model_failures"]["primary"] += 1

        # 3. 尝试次级模型
        try:
            response = await self._call_model("secondary", prompt)
            threshold = self._fallback_configs["secondary"]["quality_threshold"]
            if response.quality >= threshold:
                self._save_to_cache(cache_key, response)
                return response
        except Exception as e:
            logger.warning(f"Secondary model failed: {e}")
            self._call_stats["model_failures"]["secondary"] += 1

        # 4. 尝试本地模型
        try:
            response = await self._call_model("local", prompt)
            threshold = self._fallback_configs["local"]["quality_threshold"]
            if response.quality >= threshold:
                return response
        except Exception as e:
            logger.warning(f"Local model failed: {e}")
            self._call_stats["model_failures"]["local"] += 1

        # 5. 返回默认回复
        return LLMResponse(
            content=fallback_content or self._get_default_content(context),
            quality=0.3,
            model="none",
            from_cache=False,
            error="All models failed, using fallback"
        )

    async def _call_model(
        self,
        model_level: str,
        prompt: str
    ) -> LLMResponse:
        """调用指定层级的模型"""
        config = self._model_configs.get(model_level)
        if not config:
            raise ValueError(f"Unknown model level: {model_level}")

        start_time = time.time()

        try:
            # 获取LLM
            llm = getattr(self.agent, 'llm', None)
            if not llm:
                raise ValueError("Agent has no LLM")

            # 调用LLM
            if hasattr(llm, 'ainvoke'):
                response = await llm.ainvoke(prompt)
            elif hasattr(llm, 'agenerate'):
                # 流式生成
                response = await llm.agenerate([prompt])
            else:
                response = await llm(prompt)

            latency = time.time() - start_time

            # 提取内容
            content = ""
            if hasattr(response, 'content'):
                content = response.content
            elif hasattr(response, 'text'):
                content = response.text
            elif isinstance(response, str):
                content = response

            # 估计质量
            quality = self._estimate_quality(content, prompt)

            return LLMResponse(
                content=content,
                quality=quality,
                model=config.model,
                latency=latency,
                from_cache=False
            )

        except Exception as e:
            raise LLMCallError(f"{model_level} model failed: {e}")

    def _estimate_quality(
        self,
        content: str,
        prompt: str
    ) -> float:
        """
        估计内容质量

        基于多个维度:
        1. 内容长度
        2. 与prompt的相关性
        3. 结构完整性
        """
        if not content or len(content) < 10:
            return 0.0

        # 1. 长度分数
        length_score = min(1.0, len(content) / 500)

        # 2. 相关性分数
        prompt_keywords = set(prompt.lower().split()[:20])
        content_keywords = set(content.lower().split()[:100])
        overlap = len(prompt_keywords & content_keywords) / len(prompt_keywords) if prompt_keywords else 0
        relevance_score = min(1.0, overlap * 2)

        # 3. 结构完整性
        has_structure = any(marker in content for marker in ["##", "###", "1.", "2.", "- ", "* "])
        structure_score = 0.3 if has_structure else 0.0

        # 4. 格式正确性（如果是JSON）
        format_score = 0.0
        if content.strip().startswith("{") or content.strip().startswith("["):
            try:
                import json
                json.loads(content)
                format_score = 0.2
            except:
                pass

        # 综合分数
        return min(1.0, length_score * 0.2 + relevance_score * 0.4 + structure_score + format_score)

    def _generate_cache_key(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """生成缓存键"""
        # 结合prompt和上下文生成键
        key_parts = [prompt]

        if context:
            # 添加上下文的关键信息
            context_str = str(sorted(context.items()))
            key_parts.append(context_str)

        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_from_cache(self, key: str) -> Optional[LLMResponse]:
        """从缓存获取"""
        # 检查TTL
        if key in self._cache_timestamps:
            age = time.time() - self._cache_timestamps[key]
            if age > self._cache_ttl:
                # 过期
                if key in self._cache:
                    del self._cache[key]
                del self._cache_timestamps[key]
                return None

        cached = self._cache.get(key)
        if cached:
            return cached
        return None

    def _save_to_cache(self, key: str, response: LLMResponse) -> None:
        """保存到缓存"""
        self._cache.set(key, response)
        self._cache_timestamps[key] = time.time()

    def _get_default_content(self, context: Optional[Dict[str, Any]]) -> str:
        """获取默认回复内容"""
        if context:
            task = context.get("task", "")
            if task:
                return f"抱歉，我无法完成「{task}」任务。请稍后再试。"

        return "抱歉，我目前无法处理这个请求。请稍后再试。"

    def get_stats(self) -> Dict[str, Any]:
        """获取调用统计"""
        cache_hit_rate = 0.0
        if self._call_stats["total_calls"] > 0:
            cache_hit_rate = self._call_stats["cache_hits"] / self._call_stats["total_calls"]

        return {
            "total_calls": self._call_stats["total_calls"],
            "cache_hits": self._call_stats["cache_hits"],
            "cache_hit_rate": cache_hit_rate,
            "model_failures": self._call_stats["model_failures"],
            "cache_size": len(self._cache._cache)
        }

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._cache_timestamps.clear()


class LLMCallError(Exception):
    """LLM调用错误"""
    pass


def create_llm_caller(
    agent: Any,
    primary_model: str = "gpt-4",
    secondary_model: str = "gpt-3.5-turbo"
) -> LLMCallWithFallback:
    """创建LLM调用器"""
    return LLMCallWithFallback(
        agent=agent,
        primary_config=ModelConfig(model=primary_model),
        secondary_config=ModelConfig(model=secondary_model)
    )
