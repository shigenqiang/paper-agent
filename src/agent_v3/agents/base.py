"""
Base agent for Agent v3.

Provides common LLM interaction patterns for all agents.
"""

from __future__ import annotations

import logging
from typing import Any

from src.agent_v3.core.config import AppConfig
from src.agent_v3.llm.client import LLMClient

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all v3 agents."""

    def __init__(self, config: AppConfig, name: str = "base"):
        self.config = config
        self.name = name
        self.llm = LLMClient(config.llm)
        self.logger = logging.getLogger(f"agent_v3.{name}")

    async def call_llm(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
    ) -> Any:
        """Call LLM with optional JSON mode."""
        if json_mode:
            return await self.llm.ainvoke_json(prompt, system_prompt)
        return await self.llm.ainvoke(prompt, system_prompt)
