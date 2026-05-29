"""论文搜索模块"""

from src.agents_v3.research_workspace.search.arxiv_client import ArxivClient
from src.agents_v3.research_workspace.search.base import (
    BaseSearchAdapter,
    SearchErrorInfo,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SearchSession,
)
from src.agents_v3.research_workspace.search.cache import SearchCache
from src.agents_v3.research_workspace.search.crossref_client import CrossRefClient
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
from src.agents_v3.research_workspace.search.ranking import RankingService
from src.agents_v3.research_workspace.search.semantic_scholar_client import SemanticScholarClient
from src.agents_v3.research_workspace.search.strategies import SearchStrategy, get_strategy

__all__ = [
    "ArxivClient",
    "BaseSearchAdapter",
    "CrossRefClient",
    "DedupDecision",
    "DedupService",
    "OpenAlexClient",
    "RateManager",
    "RankingService",
    "SearchCache",
    "SearchError",
    "SearchErrorCategory",
    "SearchErrorInfo",
    "SearchOrchestrator",
    "SearchQuery",
    "SearchResponse",
    "SearchResult",
    "SearchResultMerger",
    "SearchSession",
    "SearchStrategy",
    "SemanticScholarClient",
    "SourceConfig",
    "build_existing_keys",
    "create_default_adapters",
    "first_author_key",
    "get_adapter",
    "get_strategy",
    "is_duplicate",
    "make_dedup_key",
    "normalize_arxiv_id",
    "normalize_author",
    "normalize_doi",
    "normalize_title",
]
