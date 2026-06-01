"""API 请求/响应 DTO"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── 基础结构 ──────────────────────────────────────

class ApiMeta(BaseModel):
    request_id: str = ""
    timestamp: str = ""
    duration_ms: int = 0


class ApiResponse(BaseModel):
    data: Any = None
    meta: ApiMeta = Field(default_factory=ApiMeta)


class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str = ""


class ApiErrorResponse(BaseModel):
    error: ApiErrorBody


class PageInfo(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0
    has_next: bool = False


class ApiListResponse(BaseModel):
    data: list[Any] = Field(default_factory=list)
    pagination: PageInfo = Field(default_factory=PageInfo)
    meta: ApiMeta = Field(default_factory=ApiMeta)


# ── 项目 ──────────────────────────────────────────

class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""
    discipline: str = ""
    education_level: str = ""
    research_goal: str = ""


class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


# ── 论文 ──────────────────────────────────────────

class PaperUploadRequest(BaseModel):
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None


class PaperUpdateRequest(BaseModel):
    title: str | None = None
    included: bool | None = None
    exclude_reason: str | None = None


class PaperImportDoiRequest(BaseModel):
    dois: list[str]


class PaperImportBibtexRequest(BaseModel):
    bibtex: str


# ── 搜索 ──────────────────────────────────────────

class SearchPapersRequest(BaseModel):
    query: str
    sources: list[str] = Field(default_factory=lambda: ["openalex", "arxiv", "semantic_scholar"])
    limit: int = 20
    offset: int = 0
    year_from: int | None = None
    year_to: int | None = None
    field: str = "all"
    use_cache: bool = True
    force_refresh: bool = False


class SearchCommitRequest(BaseModel):
    query_text: str
    selected_result_ids: list[str] = Field(default_factory=list)
    min_score: float = 0.3  # 最低重要性分数阈值，低于此值的论文不入库
    source: str = "candidate"  # candidate / review


# ── Scope ─────────────────────────────────────────

class ScopeResolveRequest(BaseModel):
    type: str = "all_project"
    selected_paper_ids: list[str] = Field(default_factory=list)
    selected_topic_ids: list[str] = Field(default_factory=list)
    selected_method_ids: list[str] = Field(default_factory=list)
    selected_graph_node_ids: list[str] = Field(default_factory=list)
    graph_hops: int = 1
    time_range: list[str] = Field(default_factory=list)


# ── QA ────────────────────────────────────────────

class QARequest(BaseModel):
    question: str
    scope: ScopeResolveRequest = Field(default_factory=ScopeResolveRequest)


# ── 报告 ──────────────────────────────────────────

class ReportGenerateRequest(BaseModel):
    scope: ScopeResolveRequest = Field(default_factory=ScopeResolveRequest)
    options: dict[str, Any] = Field(default_factory=dict)


# ── 任务 ──────────────────────────────────────────

class TaskResponse(BaseModel):
    task_id: str
    status: str = "queued"
    progress: float = 0.0
    result: Any = None
    error: str = ""
    created_at: str = ""
    updated_at: str = ""
