"""
Enhanced Base Searcher - 增强型搜索器基类

包含重试逻辑、速率控制、错误处理等功能。
"""

from src.agents_v2.logging_config import get_logging_logger

import asyncio

import os
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from .base_searcher import BaseSearcher, SearchResult, SearchResponse
from .rate_manager import RateManager, get_rate_manager, PlatformConfig

logger = get_logging_logger(__name__)


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True


class EnhancedBaseSearcher(BaseSearcher):
    """增强型搜索器基类 - 集成速率控制和重试逻辑"""

    def __init__(
        self,
        name: str,
        platform_config: Optional[PlatformConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        rate_manager: Optional[RateManager] = None
    ):
        super().__init__(name)
        self.rate_manager = rate_manager or get_rate_manager()
        self.platform_config = platform_config or self.rate_manager.get_config(name)
        self.retry_config = retry_config or RetryConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        self._api_key: Optional[str] = None

    @property
    def api_key(self) -> Optional[str]:
        """获取API Key"""
        if self._api_key is None and self.platform_config.use_api_key:
            env_var = self.platform_config.api_key_env_var
            if env_var:
                self._api_key = os.getenv(env_var, "")
        return self._api_key

    async def _get_session(self) -> 'aiohttp.ClientSession':
        """获取或创建HTTP会话"""
        import aiohttp

        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """关闭HTTP会话"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _make_request(
        self,
        url: str,
        params: Dict = None,
        headers: Dict = None,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """发送HTTP请求，带速率控制和重试

        Args:
            url: 请求URL
            params: 查询参数
            headers: 请求头
            method: HTTP方法

        Returns:
            响应数据或错误信息
        """
        import aiohttp

        last_error = None

        for attempt in range(self.retry_config.max_retries):
            try:
                # 1. 获取请求许可（速率控制）
                await self.rate_manager.acquire(self.name, self.platform_config)

                # 2. 发送请求
                session = await self._get_session()

                if method.upper() == "GET":
                    async with session.get(url, params=params, headers=headers) as resp:
                        return await self._handle_response(resp)
                elif method.upper() == "POST":
                    async with session.post(url, json=params, headers=headers) as resp:
                        return await self._handle_response(resp)

            except aiohttp.ClientError as e:
                last_error = e
                logger.warning(f"{self.name} request failed (attempt {attempt + 1}/{self.retry_config.max_retries}): {e}")
                if attempt < self.retry_config.max_retries - 1:
                    delay = self._calculate_delay(attempt)
                    logger.debug(f"{self.name} retrying in {delay:.2f}s")
                    await asyncio.sleep(delay)
                    continue

            except asyncio.TimeoutError:
                last_error = Exception("Request timeout")
                logger.warning(f"{self.name} request timeout (attempt {attempt + 1}/{self.retry_config.max_retries})")
                if attempt < self.retry_config.max_retries - 1:
                    delay = self._calculate_delay(attempt)
                    await asyncio.sleep(delay)
                    continue

            except Exception as e:
                last_error = e
                logger.error(f"{self.name} unexpected error: {e}")
                break

        # 所有重试都失败
        self.rate_manager.record_error(self.name, self.platform_config)
        return {"error": str(last_error or "Unknown error")}

    async def _handle_response(self, resp: 'aiohttp.ClientResponse') -> Dict[str, Any]:
        """处理HTTP响应"""
        import aiohttp

        if resp.status == 429:
            # 限流错误
            self.rate_manager.record_rate_limit(self.name, self.platform_config)
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    wait_time = min(int(retry_after), 60)
                    await asyncio.sleep(wait_time)
                except ValueError:
                    pass
            return {"error": "Rate limit exceeded", "retry_after": retry_after}

        if resp.status == 404:
            return {"data": [], "not_found": True}

        if resp.status == 401 or resp.status == 403:
            return {"error": f"Authentication failed: {resp.status}"}

        if resp.status != 200:
            text = await resp.text()
            logger.error(f"{self.name} API error: {resp.status} - {text[:500]}")
            return {"error": f"HTTP {resp.status}: {text[:200]}"}

        # 尝试解析JSON
        try:
            return await resp.json()
        except Exception:
            text = await resp.text()
            return {"data": [], "error": f"Failed to parse response: {text[:200]}"}

    def _calculate_delay(self, attempt: int) -> float:
        """计算重试延迟（指数退避 + 抖动）"""
        delay = self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt)
        delay = min(delay, self.retry_config.max_delay)

        if self.retry_config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # 0.5 ~ 1.0 倍

        return delay

    def _build_headers(self, extra: Dict = None) -> Dict:
        """构建请求头"""
        headers = {
            "Accept": "application/json",
            "User-Agent": "PaperAgent/1.0 (https://github.com/paper-agent)"
        }

        # 添加API Key（如果需要）
        if self.api_key:
            if self.name == "semantic_scholar":
                headers["x-api-key"] = self.api_key
            elif self.name == "pubmed":
                headers["api-key"] = self.api_key

        if extra:
            headers.update(extra)

        return headers

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """执行搜索 - 子类必须实现"""
        pass

    async def health_check(self) -> bool:
        """健康检查 - 测试API是否可用"""
        try:
            result = await self.search("test", max_results=1)
            return result.error == "" or "not_found" in result.error or len(result.results) >= 0
        except Exception as e:
            logger.error(f"{self.name} health check failed: {e}")
            return False

    def get_rate_stats(self) -> Dict:
        """获取速率统计信息"""
        return self.rate_manager.get_stats(self.name)


import aiohttp  # 引入类型注解