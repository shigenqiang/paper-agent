"""论文及其子模型"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.agents_v3.research_workspace.models.enums import ChunkType, PaperStatus


class Author(BaseModel):
    """论文作者"""
    name: str = ""
    given_name: str = ""
    family_name: str = ""
    orcid: str = ""
    affiliations: list[str] = Field(default_factory=list)


class PaperIdentifiers(BaseModel):
    """论文标识符集合"""
    doi: str = ""
    arxiv_id: str = ""
    pubmed_id: str = ""
    openalex_id: str = ""
    semantic_scholar_id: str = ""


class PaperDates(BaseModel):
    """论文日期信息"""
    year: int | None = None
    published_date: str = ""


class PaperSource(BaseModel):
    """论文来源 (期刊/会议/预印本)"""
    venue: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""


class OpenAccessInfo(BaseModel):
    """开放获取信息"""
    is_oa: bool = False
    oa_status: str = ""
    pdf_url: str = ""
    license: str = ""


class PaperClassification(BaseModel):
    """论文分类信息"""
    categories: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    topics_score: list[float] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    fields_of_study: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)


class CitationInfo(BaseModel):
    """引用信息"""
    citation_count: int | None = None
    influential_citation_count: int | None = None
    reference_count: int | None = None
    references: list[str] = Field(default_factory=list)


class Paper(BaseModel):
    paper_id: str
    project_id: str
    title: str = ""
    abstract: str = ""
    language: str = ""
    publication_type: str = ""

    identifiers: PaperIdentifiers = Field(default_factory=PaperIdentifiers)
    authors: list[Author] = Field(default_factory=list)
    dates: PaperDates = Field(default_factory=PaperDates)
    source: PaperSource = Field(default_factory=PaperSource)
    open_access: OpenAccessInfo = Field(default_factory=OpenAccessInfo)
    classification: PaperClassification = Field(default_factory=PaperClassification)
    citation: CitationInfo = Field(default_factory=CitationInfo)

    url: str = ""
    source_platform: str = ""  # arxiv/openalex/upload/bibtex/doi
    source_payload: dict[str, Any] = Field(default_factory=dict)

    status: PaperStatus = PaperStatus.IMPORTED
    pdf_path: str = ""
    error_message: str = ""
    included: bool = True
    exclude_reason: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperChunk(BaseModel):
    chunk_id: str
    paper_id: str
    section_id: str = ""
    chunk_index: int = 0
    section_title: str = ""
    section_type: str = ""
    chunk_type: str = "body"
    text: str = ""
    start_char: int = 0
    end_char: int = 0
    page_start: int = 0
    page_end: int = 0
    token_count: int = 0
    parser_name: str = "pdfplumber"
    quality_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParseResult(BaseModel):
    parse_id: str = Field(default_factory=lambda: f"parse_{uuid.uuid4().hex[:8]}")
    paper_id: str
    parser_name: str = "pdfplumber"
    status: str = "pending"
    page_count: int = 0
    section_count: int = 0
    chunk_count: int = 0
    body_chunk_count: int = 0
    reference_count: int = 0
    table_count: int = 0
    figure_count: int = 0
    quality_flags: list[str] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    error_message: str = ""
    started_at: str = ""
    finished_at: str = ""
