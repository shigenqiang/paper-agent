"""结构化日志工具"""

from __future__ import annotations

import contextlib
import time
from contextvars import ContextVar
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.utils import hash_text, redact_text

# ── 请求上下文 ──────────────────────────────────────

_request_id: ContextVar[str] = ContextVar("request_id", default="")
_task_id: ContextVar[str] = ContextVar("task_id", default="")
_project_id: ContextVar[str] = ContextVar("project_id", default="")
_operation: ContextVar[str] = ContextVar("operation", default="")


def bind_context(
    request_id: str = "",
    task_id: str = "",
    project_id: str = "",
    operation: str = "",
) -> None:
    """绑定当前请求上下文"""
    if request_id:
        _request_id.set(request_id)
    if task_id:
        _task_id.set(task_id)
    if project_id:
        _project_id.set(project_id)
    if operation:
        _operation.set(operation)


def get_context() -> dict[str, str]:
    """获取当前上下文"""
    return {
        "request_id": _request_id.get(),
        "task_id": _task_id.get(),
        "project_id": _project_id.get(),
        "operation": _operation.get(),
    }


def clear_context() -> None:
    """清除上下文"""
    _request_id.set("")
    _task_id.set("")
    _project_id.set("")
    _operation.set("")


# ── 日志事件 ──────────────────────────────────────

def log_event(event: str, level: str = "INFO", **kwargs: Any) -> None:
    """记录结构化事件日志"""
    ctx = get_context()
    fields = {k: v for k, v in ctx.items() if v}
    fields.update(kwargs)
    field_str = " ".join(f"{k}={v}" for k, v in fields.items())
    logger.log(level, f"{event} | {field_str}")


@contextlib.contextmanager
def log_operation(operation: str, **extra: Any):
    """记录操作的上下文管理器"""
    bind_context(operation=operation)
    start = time.time()
    log_event(f"{operation}.started", **extra)
    try:
        yield
        elapsed_ms = int((time.time() - start) * 1000)
        log_event(f"{operation}.completed", elapsed_ms=elapsed_ms, **extra)
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        log_event(f"{operation}.failed", elapsed_ms=elapsed_ms, error=str(e)[:200], **extra)
        raise


def truncate_text(text: str | None, max_len: int = 200) -> str | None:
    """截断长文本"""
    if not text:
        return text
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"...[{len(text)}chars]"


def sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """递归清理日志 payload 中的敏感字段"""
    forbidden_keys = {
        "system_prompt", "user_prompt", "full_prompt", "messages",
        "raw_response", "pdf_text", "source_quote_full",
        "api_key", "authorization", "password", "secret",
    }
    result = {}
    for k, v in payload.items():
        if k.lower() in forbidden_keys:
            continue
        if isinstance(v, str) and len(v) > 500:
            result[k] = hash_text(v)
        elif isinstance(v, dict):
            result[k] = sanitize_payload(v)
        else:
            result[k] = v
    return result
