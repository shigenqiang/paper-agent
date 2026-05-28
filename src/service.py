"""
Paper Knowledge-Base Analysis Agent - 统一服务入口

启动 FastAPI 应用（基于 agents_v3/research_workspace）

使用方法:
    python -m src.service                    # 默认端口 8000
    python -m src.service --port 9000        # 指定端口
    python -m src.service --host 127.0.0.1   # 指定地址
"""

import argparse

from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Paper Knowledge-Base Analysis Agent")
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址 (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="端口 (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="开发模式自动重载")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Paper Knowledge-Base Analysis Agent (v3)")
    logger.info("=" * 60)
    logger.info(f"  Address:  http://{args.host}:{args.port}")
    logger.info(f"  Health:   http://{args.host}:{args.port}/api/health")
    logger.info(f"  Docs:     http://{args.host}:{args.port}/docs")
    logger.info("-" * 60)
    logger.info("API Endpoints:")
    logger.info("  POST /api/rw/projects                      — 创建项目")
    logger.info("  GET  /api/rw/projects                      — 项目列表")
    logger.info("  POST /api/rw/projects/{id}/papers/search   — 搜索论文")
    logger.info("  POST /api/rw/projects/{id}/papers/parse    — 解析论文")
    logger.info("  POST /api/rw/projects/{id}/cards           — 生成论文卡片")
    logger.info("  POST /api/rw/projects/{id}/evidence/build  — 构建证据表")
    logger.info("  POST /api/rw/projects/{id}/kg/build        — 构建知识图谱")
    logger.info("  POST /api/rw/projects/{id}/qa              — Scope QA")
    logger.info("  POST /api/rw/projects/{id}/reports/literature-review — 文献综述")
    logger.info("  POST /api/rw/projects/{id}/reports/innovation       — 创新点报告")
    logger.info("=" * 60)

    import uvicorn
    uvicorn.run(
        "src.agents_v3.research_workspace.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
