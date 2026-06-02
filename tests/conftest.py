"""E2E 共享 fixtures — 真实 PostgreSQL + 真实 API

所有 e2e 测试共用此文件的 fixture，避免重复连接配置。
"""

import os
import pytest

from src.agents_v3.research_workspace.storage.postgres import PostgresStorage
from src.agents_v3.research_workspace.services.paper_library import PaperLibraryService
from src.agents_v3.research_workspace.search.factory import create_default_adapters

PG_DSN = os.environ.get(
    "PG_DSN",
    "postgresql://postgres:postgres@localhost:5432/paper_agent",
)


@pytest.fixture(scope="module")
def pg_storage():
    """连接真实 PostgreSQL"""
    try:
        storage = PostgresStorage(dsn=PG_DSN)
        yield storage
    except Exception as e:
        pytest.skip(f"PostgreSQL 不可用: {e}")


@pytest.fixture(scope="module")
def adapters():
    """创建真实搜索适配器"""
    return create_default_adapters()


@pytest.fixture(scope="module")
def service(pg_storage, adapters):
    """PaperLibraryService — 真实存储 + 真实适配器"""
    return PaperLibraryService(
        storage=pg_storage,
        search_adapters=list(adapters.values()),
        global_storage=pg_storage,
    )
