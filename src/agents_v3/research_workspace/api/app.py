"""FastAPI 应用工厂与生命周期管理"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from loguru import logger

from src.agents_v3.research_workspace.api.errors import (
    APIError,
    api_error_handler,
    generic_error_handler,
)


def _init_storage_backends() -> None:
    """启动时初始化存储后端（表不存在则创建，存在则跳过）"""
    import yaml
    from pathlib import Path

    config_path = Path("config.yaml")
    config = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    db_config = config.get("database", {})

    # PostgreSQL 初始化
    pg_config = db_config.get("postgres", {})
    if pg_config.get("enabled", False):
        try:
            from src.agents_v3.research_workspace.storage.postgres import PostgresStorage
            dsn = pg_config.get("dsn")
            if dsn:
                storage = PostgresStorage(dsn=dsn)
            else:
                storage = PostgresStorage(
                    host=pg_config.get("host", "localhost"),
                    port=pg_config.get("port", 5432),
                    database=pg_config.get("database", "paper_agent"),
                    user=pg_config.get("user", "postgres"),
                    password=pg_config.get("password", ""),
                )
            storage.close()
            logger.info("PostgreSQL storage initialized (tables ensured)")
        except Exception as e:
            logger.error(f"PostgreSQL initialization failed: {e}")
    else:
        logger.info("PostgreSQL disabled, using JSON storage")

    # Qdrant 向量存储初始化
    qdrant_config = db_config.get("qdrant", {})
    if qdrant_config.get("enabled", False):
        try:
            from src.agents_v3.research_workspace.storage.qdrant import get_collection_info, init_qdrant
            init_qdrant(
                host=qdrant_config.get("host", "localhost"),
                port=qdrant_config.get("port", 6333),
            )
            info = get_collection_info(
                host=qdrant_config.get("host", "localhost"),
                port=qdrant_config.get("port", 6333),
            )
            logger.info(f"Qdrant ready: {info}")
        except Exception as e:
            logger.error(f"Qdrant initialization failed: {e}")
    else:
        logger.info("Qdrant disabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务生命周期管理"""
    logger.info("Service starting up")
    _init_storage_backends()
    yield
    from src.agents_v3.research_workspace.storage import _project_storages
    logger.info(f"Service shutting down, {len(_project_storages)} project caches to clear")
    _project_storages.clear()
    logger.info("Cleanup done")


def create_app(storage=None) -> FastAPI:
    if storage is not None:
        from src.agents_v3.research_workspace.api import deps as deps_module
        deps_module.get_storage = lambda: storage

    app = FastAPI(
        lifespan=lifespan,
        title="Paper Agent Research Workspace API",
        version="3.0.0",
        description="论文知识库分析 Agent API",
        swagger_ui_parameters={
            "swagger_js_url": "https://cdn.staticfile.net/swagger-ui-dist/5.11.0/swagger-ui-bundle.js",
            "swagger_css_url": "https://cdn.staticfile.net/swagger-ui-dist/5.11.0/swagger-ui.css",
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        request.state.request_id = request_id
        start = time.time()
        response = await call_next(request)
        duration = int((time.time() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Duration-Ms"] = str(duration)
        return response

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "3.0.0"}

    # 注册路由模块
    from src.agents_v3.research_workspace.api.routes import register_routers
    register_routers(app)

    return app


app = create_app()
