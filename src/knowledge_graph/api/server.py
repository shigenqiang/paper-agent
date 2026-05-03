"""
知识图谱API服务
FastAPI server for Knowledge Graph
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports when running directly
current_file = Path(__file__).resolve()
parent_dir = current_file.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import router from routes module
from src.knowledge_graph.api.routes import router as kg_router


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="Academic Knowledge Graph API",
        description="学术论文知识图谱构建与查询API",
        version="1.0.0"
    )

    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(kg_router)

    return app


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False
):
    """运行API服务器"""
    import uvicorn

    app = create_app()

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="运行知识图谱API服务")
    parser.add_argument("--host", default="0.0.0.0", help="服务地址")
    parser.add_argument("--port", type=int, default=8000, help="服务端口")
    parser.add_argument("--reload", action="store_true", help="热重载")

    args = parser.parse_args()

    run_server(args.host, args.port, args.reload)