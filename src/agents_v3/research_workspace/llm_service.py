"""LLM 服务封装 - 基于 LangChain"""

from __future__ import annotations

import json
import os
from typing import Any

from loguru import logger
from pydantic import BaseModel


class LLMConfig(BaseModel):
    """LLM 配置"""
    provider: str = "openai"
    model_name: str = "MiniMax-M2.7"
    temperature: float = 0.7
    max_tokens: int = 4096
    api_key: str | None = None
    base_url: str | None = None


class LLMService:
    """统一 LLM 调用服务"""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm

    def _create_llm(self):
        config = self.config
        api_key = config.api_key or os.environ.get("OPENAI_API_KEY", "")
        base_url = config.base_url or os.environ.get("OPENAI_BASE_URL", "")

        if config.provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                api_key=api_key,
                base_url=base_url if base_url else None,
            )
        elif config.provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                api_key=api_key,
            )
        else:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                api_key=api_key,
                base_url=base_url if base_url else None,
            )

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        """调用 LLM"""
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def invoke_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """调用 LLM 并解析 JSON 响应"""
        response = self.invoke(system_prompt, user_prompt)
        # 尝试提取 JSON
        try:
            # 处理 markdown 代码块
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from LLM response: {response[:200]}")
            return {"raw_response": response}


# 全局单例
_llm_service: LLMService | None = None


def get_llm_service(config: LLMConfig | None = None) -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(config)
    return _llm_service
