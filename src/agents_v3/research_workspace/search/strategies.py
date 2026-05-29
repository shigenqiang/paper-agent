"""搜索策略"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SearchStrategy:
    name: str
    sources: list[str] = field(default_factory=list)
    limit: int = 20


# 预定义策略
STRATEGIES: dict[str, SearchStrategy] = {
    "quick_explore": SearchStrategy(
        name="quick_explore",
        sources=["openalex", "arxiv"],
        limit=20,
    ),
    "literature_review": SearchStrategy(
        name="literature_review",
        sources=["openalex", "arxiv", "semantic_scholar"],
        limit=50,
    ),
    "doi_import": SearchStrategy(
        name="doi_import",
        sources=["openalex"],
        limit=10,
    ),
    "precise": SearchStrategy(
        name="precise",
        sources=["openalex", "arxiv", "semantic_scholar"],
        limit=20,
    ),
}


def get_strategy(name: str) -> SearchStrategy:
    """获取搜索策略"""
    return STRATEGIES.get(name, STRATEGIES["quick_explore"])
