"""LLM 调用日志与脱敏"""

from __future__ import annotations

import hashlib
from typing import Any

from loguru import logger

_SENSITIVE_KEYWORDS = ["api_key", "apikey", "authorization", "bearer", "sk-", "token"]


def redact_text(text: str, max_length: int = 200) -> str:
    if not text:
        return ""
    redacted = text[:max_length] if len(text) > max_length else text
    for kw in _SENSITIVE_KEYWORDS:
        if kw in redacted.lower():
            redacted = f"[REDACTED - contains {kw}]"
            break
    return redacted


def hash_text(text: str) -> str:
    if not text:
        return ""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


def log_llm_call(
    prompt_name: str, prompt_version: str, model: str,
    success: bool, latency_ms: int = 0,
    prompt_tokens: int = 0, completion_tokens: int = 0,
    error_type: str = "", error_message: str = "",
    prompt_hash: str = "", response_hash: str = "",
) -> None:
    level = "INFO" if success else "WARNING"
    logger.log(
        level,
        f"llm.call | prompt={prompt_name}@{prompt_version} model={model} "
        f"success={success} latency={latency_ms}ms "
        f"tokens={prompt_tokens}+{completion_tokens} "
        f"error={error_type}:{redact_text(error_message, 100)} "
        f"hashes={prompt_hash}:{response_hash}",
    )
