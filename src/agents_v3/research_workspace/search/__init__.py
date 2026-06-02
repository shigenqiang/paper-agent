"""论文搜索模块"""

from src.agents_v3.research_workspace.search.arxiv_client import ArxivClient
from src.agents_v3.research_workspace.search.europepmc_client import EuropePMCClient
from src.agents_v3.research_workspace.search.base import (
    BaseSearchAdapter,
    QueryRecord,
    SearchErrorInfo,
    SearchField,
    SearchQuery,
    SearchResponse,
    SearchResult,
)
from src.agents_v3.research_workspace.search.dedup import (
    DedupDecision,
    DedupService,
    build_existing_keys,
    first_author_key,
    is_duplicate,
    make_dedup_key,
    normalize_arxiv_id,
    normalize_author,
    normalize_doi,
    normalize_title,
)
from src.agents_v3.research_workspace.search.errors import SearchError, SearchErrorCategory
from src.agents_v3.research_workspace.search.factory import create_default_adapters, get_adapter
from src.agents_v3.research_workspace.search.merger import SearchResultMerger
from src.agents_v3.research_workspace.search.openalex_client import OpenAlexClient
from src.agents_v3.research_workspace.search.orchestrator import SearchOrchestrator
from src.agents_v3.research_workspace.search.rate_limit import RateManager, SourceConfig
from src.agents_v3.research_workspace.search.sparse_encoder import SparseEncoder
from src.agents_v3.research_workspace.search.hybrid_ranker import HybridRanker
from src.agents_v3.research_workspace.search.quality_filter import (
    compute_quality,
    compute_quality_batch,
    filter_by_quality,
    filter_by_relevance,
    two_stage_filter,
)
from src.agents_v3.research_workspace.search.semantic_scholar_client import SemanticScholarClient
from src.agents_v3.research_workspace.search.strategies import SearchStrategy, get_strategy

__all__ = [
    "ArxivClient",
    "BaseSearchAdapter",
    "DedupDecision",
    "DedupService",
    "EuropePMCClient",
    "HybridRanker",
    "OpenAlexClient",
    "RateManager",
    "QueryRecord",
    "SearchError",
    "SearchErrorCategory",
    "SearchErrorInfo",
    "SearchField",
    "SearchOrchestrator",
    "SearchQuery",
    "SearchResponse",
    "SearchResult",
    "SearchResultMerger",
    "SearchStrategy",
    "SparseEncoder",
    "SemanticScholarClient",
    "SourceConfig",
    "build_existing_keys",
    "compute_quality",
    "compute_quality_batch",
    "create_default_adapters",
    "filter_by_quality",
    "filter_by_relevance",
    "first_author_key",
    "get_adapter",
    "get_strategy",
    "is_duplicate",
    "make_dedup_key",
    "normalize_arxiv_id",
    "normalize_author",
    "normalize_doi",
    "normalize_title",
    "two_stage_filter",
]
