"""LLM 调用日志与脱敏"""

from __future__ import annotations

from loguru import logger

from src.agents_v3.research_workspace.utils import hash_text, redact_text


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
