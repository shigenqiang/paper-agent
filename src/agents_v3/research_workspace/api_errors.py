"""API 错误处理"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from src.agents_v3.research_workspace.api_models import ApiErrorBody


class APIError(Exception):
    """API 基础异常"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(APIError):
    def __init__(self, resource: str, resource_id: str = ""):
        super().__init__(
            code=f"{resource}_not_found",
            message=f"{resource.title()} not found" + (f": {resource_id}" if resource_id else ""),
            status_code=404,
            details={"resource": resource, "id": resource_id},
        )


class ValidationError(APIError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(code="validation_failed", message=message, status_code=422, details=details)


class ScopeEmptyError(APIError):
    def __init__(self, reason: str = ""):
        super().__init__(
            code="scope_empty",
            message=f"Scope is empty: {reason}" if reason else "Scope is empty",
            status_code=422,
            details={"empty_reason": reason},
        )


class TaskNotFoundError(APIError):
    def __init__(self, task_id: str):
        super().__init__(code="task_not_found", message=f"Task not found: {task_id}", status_code=404)


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": getattr(request.state, "request_id", ""),
            }
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": str(exc)[:200],
                "request_id": getattr(request.state, "request_id", ""),
            }
        },
    )
