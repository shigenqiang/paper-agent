"""搜索适配器注册工厂"""

from __future__ import annotations

from typing import Any

from src.agents_v3.research_workspace.search.arxiv_client import ArxivClient
from src.agents_v3.research_workspace.search.base import BaseSearchAdapter
from src.agents_v3.research_workspace.search.crossref_client import CrossRefClient
from src.agents_v3.research_workspace.search.openalex_client import OpenAlexClient


def create_default_adapters(config: dict[str, Any] | None = None) -> dict[str, BaseSearchAdapter]:
    """创建默认适配器集合"""
    cfg = config or {}
    adapters: dict[str, BaseSearchAdapter] = {}

    adapters["openalex"] = OpenAlexClient(
        email=cfg.get("openalex", {}).get("mailto", ""),
        min_interval=cfg.get("openalex", {}).get("min_interval_seconds", 0.5),
    )
    adapters["arxiv"] = ArxivClient(
        min_interval=cfg.get("arxiv", {}).get("min_interval_seconds", 3.0),
    )
    adapters["crossref"] = CrossRefClient(
        mailto=cfg.get("crossref", {}).get("mailto", ""),
    )

    return adapters


def get_adapter(name: str, config: dict[str, Any] | None = None) -> BaseSearchAdapter | None:
    """按名称获取单个适配器"""
    cfg = config or {}
    adapters = create_default_adapters(cfg)
    return adapters.get(name)
