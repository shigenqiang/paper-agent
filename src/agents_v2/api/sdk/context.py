"""
Auto context compression for long-running agent conversations.

When the conversation exceeds a token threshold:
1. Summarize older messages into a condensed form
2. Preserve system message and most recent messages intact
3. Use a lightweight LLM call to generate the summary

This mirrors Claude Agent SDK's automatic context compression behavior.
"""

from src.agents_v2.logging_config import get_logging_logger

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = get_logging_logger(__name__)


# Approximate token counting — ~4 chars per token for CJK/English mix
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Rough token count estimate. ~4 chars per token for mixed CJK/English."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_message_tokens(msg: Dict[str, Any]) -> int:
    """Estimate tokens in a single message."""
    content = msg.get("content", "")
    if isinstance(content, list):
        # Multimodal content blocks
        text = "".join(b.get("text", "") for b in content if isinstance(b, dict))
        return estimate_tokens(text)
    return estimate_tokens(str(content))


@dataclass
class CompressionResult:
    """Result of a context compression pass."""
    original_count: int
    compressed_count: int
    messages_before: int
    messages_after: int
    estimated_tokens_saved: int
    summary: str = ""


class ContextCompressor:
    """Auto-compresses conversation context when it exceeds a token threshold.

    Strategy:
    - Always preserve the system message (index 0)
    - Keep the last N messages intact (sliding window)
    - Summarize everything in between into a single condensed message

    Usage:
        compressor = ContextCompressor(threshold_tokens=80000, keep_last=6)
        compressed = await compressor.compress(messages)
    """

    def __init__(
        self,
        threshold_tokens: int = 80000,
        keep_last: int = 6,
        summary_model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.threshold_tokens = threshold_tokens
        self.keep_last = keep_last
        self.summary_model = summary_model
        self.api_key = api_key
        self.base_url = base_url
        self._compression_count = 0
        self._total_tokens_saved = 0

    async def compress(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compress messages if they exceed the token threshold.

        Returns compressed list if threshold exceeded, otherwise returns the
        original list unchanged.
        """
        total_tokens = sum(estimate_message_tokens(m) for m in messages)

        if total_tokens <= self.threshold_tokens:
            return messages

        logger.info(
            f"Context compression triggered: {total_tokens} tokens > "
            f"{self.threshold_tokens} threshold"
        )

        # Identify segments
        sys_msg = messages[0] if messages and messages[0].get("role") == "system" else None
        start_idx = 1 if sys_msg else 0

        # Messages to keep intact (last N)
        keep_count = min(self.keep_last, len(messages) - start_idx)
        to_keep = messages[-keep_count:] if keep_count > 0 else []
        to_summarize = messages[start_idx:-keep_count] if keep_count > 0 else messages[start_idx:]

        if not to_summarize:
            return messages

        # Generate summary
        summary = await self._summarize(to_summarize)

        # Build compressed message list
        compressed = []
        if sys_msg:
            compressed.append(sys_msg)

        compressed.append({
            "role": "system",
            "content": f"[CONVERSATION SUMMARY] {summary}",
        })

        compressed.extend(to_keep)

        self._compression_count += 1
        saved = total_tokens - sum(estimate_message_tokens(m) for m in compressed)
        self._total_tokens_saved += saved

        logger.info(f"Compressed {len(to_summarize)} messages → 1 summary "
                    f"(saved ~{saved} tokens, total saved ~{self._total_tokens_saved})")

        return compressed

    async def _summarize(self, messages: List[Dict[str, Any]]) -> str:
        """Generate a concise summary of the messages to be compressed."""
        # Build a compact representation
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, str):
                # Truncate long content
                if len(content) > 1000:
                    content = content[:1000] + "..."
                lines.append(f"[{role}]: {content}")
            else:
                lines.append(f"[{role}]: <non-text content>")

        full_text = "\n".join(lines)

        # If a summary model is configured, use it
        if self.summary_model:
            try:
                return await self._llm_summarize(full_text)
            except Exception as e:
                logger.warning(f"LLM summarization failed, falling back to extractive: {e}")

        # Fallback: extractive summary (first + last + key tool results)
        return self._extractive_summarize(messages)

    async def _llm_summarize(self, text: str) -> str:
        """Use a lightweight LLM to summarize."""
        import os
        from openai import OpenAI

        api_key = self.api_key or os.getenv("OPENAI_API_KEY", "")
        base_url = self.base_url or os.getenv("OPENAI_BASE_URL", "https://api.minimax.chat/v1")
        model = self.summary_model or os.getenv("LLM_MODEL", "MiniMax-M2.7")

        client = OpenAI(api_key=api_key, base_url=base_url)

        prompt = (
            "Summarize the following conversation into a concise paragraph (max 200 words). "
            "Focus on key decisions, tool calls made, results obtained, and current state. "
            "Preserve specific numbers, names, and technical details.\n\n"
            f"{text[:8000]}"  # Truncate to avoid context issues
        )

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3,
        )

        content = response.choices[0].message.content or ""
        return content.strip()

    def _extractive_summarize(self, messages: List[Dict[str, Any]]) -> str:
        """Simple extractive summary: key user/assistant exchanges + tool results."""
        key_points = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user" and content:
                # First user message in sequence
                if len(key_points) < 3:
                    key_points.append(f"User asked: {str(content)[:200]}")

            if role == "tool" and content:
                # Tool result — keep brief
                short = str(content)[:150]
                if "Error" in short or "error" in short.lower():
                    key_points.append(f"Tool error: {short}")
                elif len(key_points) < 6:
                    key_points.append(f"Tool result: {short}")

        if not key_points:
            return "Previous conversation context (details omitted)."

        return " | ".join(key_points)

    @property
    def compression_count(self) -> int:
        return self._compression_count

    @property
    def total_tokens_saved(self) -> int:
        return self._total_tokens_saved
