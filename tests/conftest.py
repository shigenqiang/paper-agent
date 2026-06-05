"""E2E 共享 fixtures — 真实 PostgreSQL

测试通过 HTTP API 调用服务，pg_storage 仅用于数据库验证。
"""

import os
import pytest

from src.agents_v3.research_workspace.storage.postgres import PostgresStorage

PG_DSN = os.environ.get(
    "PG_DSN",
    "postgresql://postgres:postgres@localhost:5432/paper_agent",
)


@pytest.fixture(scope="module")
def pg_storage():
    """连接真实 PostgreSQL（仅用于验证数据）"""
    try:
        storage = PostgresStorage(dsn=PG_DSN)
        yield storage
    except Exception as e:
        pytest.skip(f"PostgreSQL 不可用: {e}")
