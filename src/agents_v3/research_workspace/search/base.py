"""搜索适配器基类和数据模型"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SearchField(str, Enum):
    """搜索字段模式"""
    ALL = "all"
    TITLE = "title"
    AUTHOR = "author"
    ABSTRACT = "abstract"


class SearchQuery(BaseModel):
    query: str
    project_id: str | None = None
    sources: list[str] = Field(default_factory=lambda: ["openalex", "arxiv", "europepmc"])
    limit: int = 20
    offset: int = 0
    year_from: int | None = None
    year_to: int | None = None
    field: SearchField = SearchField.ALL
    require_pdf: bool = False
    use_cache: bool = True
    force_refresh: bool = False


class SearchResult(BaseModel):
    result_id: str = Field(default_factory=lambda: f"sr_{uuid.uuid4().hex[:8]}")
    source: str = ""
    source_rank: int = 0
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    abstract: str = ""
    doi: str = ""
    arxiv_id: str = ""
    pubmed_id: str = ""
    semantic_scholar_id: str = ""
    openalex_id: str = ""
    url: str = ""
    pdf_url: str = ""
    citations: int | None = None
    concepts: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    language: str = ""
    publication_type: str = ""
    source_payload: dict[str, Any] = Field(default_factory=dict)
    dedup_key: str = ""
    relevance_score: float = 0.0
    quality_score: float = 0.0
    final_score: float = 0.0


class SearchErrorInfo(BaseModel):
    source: str
    category: str = "UNKNOWN"  # RATE_LIMIT, TIMEOUT, NETWORK_ERROR, API_ERROR, PARSE_ERROR, UNKNOWN
    message: str = ""
    retryable: bool = True


class SearchResponse(BaseModel):
    query: SearchQuery
    results: list[SearchResult] = Field(default_factory=list)
    total_count: int = 0
    source_stats: dict[str, dict[str, Any]] = Field(default_factory=dict)
    errors: list[SearchErrorInfo] = Field(default_factory=list)
    cache_hit: bool = False
    elapsed_ms: int = 0


class QueryRecord(BaseModel):
    """查询记录（去重）"""
    query_id: str = Field(default_factory=lambda: f"qry_{uuid.uuid4().hex[:8]}")
    query_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())


class SessionPaper(BaseModel):
    """搜索会话与论文的关联"""
    session_id: str
    paper_id: str
    created_at: str = Field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())


class SearchSession(BaseModel):
    """论文工作会话 — 当前使用哪些论文"""
    session_id: str = Field(default_factory=lambda: f"ss_{uuid.uuid4().hex[:8]}")
    project_id: str
    name: str = ""
    status: str = "active"  # active / archived
    paper_count: int = 0
    created_at: str = Field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())


class BaseSearchAdapter(ABC):
    """搜索源适配器基类"""

    @property
    @abstractmethod
    def source_name(self) -> str:
        ...

    @property
    def supported_fields(self) -> set[SearchField]:
        """该 adapter 支持的搜索字段模式，默认只支持 ALL"""
        return {SearchField.ALL}

    def _resolve_field(self, field: SearchField) -> SearchField:
        """如果 adapter 不支持请求的 field，降级为 ALL"""
        if field in self.supported_fields:
            return field
        return SearchField.ALL

    @abstractmethod
    def search(self, query: SearchQuery) -> list[SearchResult]:
        ...

    def health_check(self) -> dict[str, Any]:
        return {"source": self.source_name, "status": "ok"}
