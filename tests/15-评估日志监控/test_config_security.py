"""P3-E 配置安全 + 输入校验测试

覆盖：
- config.yaml 无硬编码密钥
- 环境变量覆盖 DB 配置
- API Key 认证中间件拦截/放行
- 认证默认关闭
- 健康检查跳过认证
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
import yaml
from pathlib import Path


class TestConfigNoHardcodedSecrets:
    """config.yaml 不应包含硬编码密钥"""

    @pytest.fixture()
    def config(self):
        config_path = Path("config.yaml")
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def test_postgres_password_empty(self, config):
        """PostgreSQL 密码应为空字符串"""
        pg = config.get("database", {}).get("postgres", {})
        assert pg.get("password", "SENTINEL") == "", \
            "config.yaml: postgres.password should be empty (use env var)"

    def test_qdrant_cloud_disabled(self, config):
        """Qdrant Cloud 默认禁用"""
        cloud = config.get("database", {}).get("qdrant", {}).get("cloud", {})
        assert cloud.get("enabled") is False

    def test_qdrant_cloud_url_empty(self, config):
        """Qdrant Cloud URL 应为空"""
        cloud = config.get("database", {}).get("qdrant", {}).get("cloud", {})
        assert cloud.get("url", "SENTINEL") == ""

    def test_qdrant_cloud_api_key_empty(self, config):
        """Qdrant Cloud API Key 应为空"""
        cloud = config.get("database", {}).get("qdrant", {}).get("cloud", {})
        assert cloud.get("api_key", "SENTINEL") == ""


class TestEnvVarOverride:
    """环境变量覆盖 DB 配置"""

    def test_dsn_env_override(self, monkeypatch):
        """PAPER_AGENT_DB_DSN 覆盖 config.yaml 的 dsn"""
        monkeypatch.setenv("PAPER_AGENT_DB_DSN", "postgresql://test:test@remote:5432/testdb")
        from src.agents_v3.research_workspace.storage import _load_pg_config
        cfg = _load_pg_config()
        assert cfg["dsn"] == "postgresql://test:test@remote:5432/testdb"

    def test_password_env_override(self, monkeypatch):
        """PAPER_AGENT_DB_PASSWORD 覆盖 config.yaml 的 password"""
        monkeypatch.setenv("PAPER_AGENT_DB_PASSWORD", "secret123")
        from src.agents_v3.research_workspace.storage import _load_pg_config
        cfg = _load_pg_config()
        assert cfg["password"] == "secret123"


class TestAPIKeyMiddleware:
    """API Key 认证中间件测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from src.agents_v3.research_workspace.api.app import create_app
        from fastapi.testclient import TestClient
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_auth_disabled_by_default(self):
        """无 PAPER_AGENT_API_KEY 环境变量时，认证关闭"""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PAPER_AGENT_API_KEY", None)
            resp = self.client.get("/api/health")
            assert resp.status_code == 200

    def test_auth_blocks_without_key(self, monkeypatch):
        """设置了 API Key 后，无 key 的请求被拦截"""
        monkeypatch.setenv("PAPER_AGENT_API_KEY", "test-secret-key")
        # 用一个存在的端点测试（/api/health 会被跳过，用其他路径）
        resp = self.client.get("/api/projects/")
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "unauthorized"

    def test_auth_blocks_wrong_key(self, monkeypatch):
        """设置了 API Key 后，错误 key 被拦截"""
        monkeypatch.setenv("PAPER_AGENT_API_KEY", "test-secret-key")
        resp = self.client.get("/api/projects/", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401

    def test_auth_allows_valid_key(self, monkeypatch):
        """正确 API Key 放行"""
        monkeypatch.setenv("PAPER_AGENT_API_KEY", "test-secret-key")
        resp = self.client.get("/api/projects/", headers={"X-API-Key": "test-secret-key"})
        # 不是 401 即可（可能是 200 或其他业务状态码）
        assert resp.status_code != 401

    def test_health_skips_auth(self, monkeypatch):
        """/api/health 跳过认证"""
        monkeypatch.setenv("PAPER_AGENT_API_KEY", "test-secret-key")
        resp = self.client.get("/api/health")
        assert resp.status_code == 200

    def test_docs_skips_auth(self, monkeypatch):
        """/docs 跳过认证"""
        monkeypatch.setenv("PAPER_AGENT_API_KEY", "test-secret-key")
        resp = self.client.get("/docs")
        assert resp.status_code == 200
