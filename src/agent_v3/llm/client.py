"""
Unified LLM client for Agent v3.

Supports: MiniMax, OpenAI, Anthropic, Qwen, DeepSeek, GLM
Uses langchain_openai.ChatOpenAI for OpenAI-compatible providers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from src.agent_v3.core.config import LLMConfig
from src.agent_v3.core.exceptions import LLMError

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client with retry and structured output support."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._llm = None
        self._init_llm()

    def _init_llm(self):
        """Initialize the langchain chat model."""
        try:
            from langchain_openai import ChatOpenAI

            kwargs: dict[str, Any] = {
                "model": self.config.model,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "timeout": self.config.timeout,
            }
            if self.config.api_key:
                kwargs["api_key"] = self.config.api_key
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url

            self._llm = ChatOpenAI(**kwargs)
            logger.info(f"LLM initialized: {self.config.model}")
        except Exception as e:
            logger.error(f"LLM init failed: {e}")
            self._llm = None

    def _clean_thinking_blocks(self, text: str) -> str:
        """Remove <think>...</think> blocks from model output."""
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        return cleaned.strip()

    async def ainvoke(
        self,
        prompt: str,
        system_prompt: str = "",
        max_retries: int = 3,
        response_format: dict | None = None,
    ) -> str:
        """
        Async LLM call with retry.

        Args:
            prompt: User message
            system_prompt: System message
            max_retries: Max retry attempts
            response_format: Optional JSON schema for structured output

        Returns:
            Model response text
        """
        if not self._llm:
            self._init_llm()
            if not self._llm:
                raise LLMError("LLM not initialized")

        from langchain_core.messages import HumanMessage, SystemMessage

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        last_error = None
        for attempt in range(max_retries):
            try:
                response = await self._llm.ainvoke(messages)
                content = (
                    response.content if hasattr(response, "content") else str(response)
                )
                content = self._clean_thinking_blocks(content)
                return content
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = 2**attempt
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}, retry in {wait}s"
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"LLM call failed after {max_retries} attempts: {e}")

        raise LLMError(f"LLM call failed: {last_error}")

    async def ainvoke_json(
        self,
        prompt: str,
        system_prompt: str = "",
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """
        Async LLM call that returns parsed JSON.

        Falls back to extracting JSON from markdown code blocks if direct parse fails.
        """
        raw = await self.ainvoke(prompt, system_prompt, max_retries)

        # Try direct JSON parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try extracting from code block
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding first { ... } or [ ... ]
        for pattern in [r"\{.*\}", r"\[.*\]"]:
            match = re.search(pattern, raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

        raise LLMError(f"Failed to parse JSON from LLM response: {raw[:200]}")

    def invoke(
        self,
        prompt: str,
        system_prompt: str = "",
        max_retries: int = 3,
    ) -> str:
        """Sync wrapper for ainvoke."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.ainvoke(prompt, system_prompt, max_retries)
            )
        finally:
            loop.close()

    def invoke_json(
        self,
        prompt: str,
        system_prompt: str = "",
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Sync wrapper for ainvoke_json."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.ainvoke_json(prompt, system_prompt, max_retries)
            )
        finally:
            loop.close()
