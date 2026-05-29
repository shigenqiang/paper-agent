"""搜索适配器基类和数据模型"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    query: str
    project_id: str | None = None
    sources: list[str] = Field(default_factory=lambda: ["openalex", "arxiv", "semantic_scholar"])
    limit: int = 20
    year_from: int | None = None
    year_to: int | None = None
    field: str = "all"  # all/title/author/abstract
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
    source_stats: dict[str, dict[str, Any]] = Field(default_factory=dict)
    errors: list[SearchErrorInfo] = Field(default_factory=list)
    cache_hit: bool = False
    elapsed_ms: int = 0


class SearchSession(BaseModel):
    session_id: str = Field(default_factory=lambda: f"ss_{uuid.uuid4().hex[:8]}")
    project_id: str
    query: dict[str, Any] = Field(default_factory=dict)
    results: list[SearchResult] = Field(default_factory=list)
    duplicate_groups: list[dict[str, Any]] = Field(default_factory=list)
    selected_result_ids: list[str] = Field(default_factory=list)
    status: str = "pending"  # pending/committed/expired
    created_at: str = Field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())


class BaseSearchAdapter(ABC):
    """搜索源适配器基类"""

    @property
    @abstractmethod
    def source_name(self) -> str:
        ...

    @abstractmethod
    def search(self, query: SearchQuery) -> list[SearchResult]:
        ...

    def health_check(self) -> dict[str, Any]:
        return {"source": self.source_name, "status": "ok"}
