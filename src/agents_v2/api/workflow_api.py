"""
工作流 API - Workflow API

提供统一工作流的 REST API 端点，支持：
1. 智能路由：根据用户查询自动分发到不同工作流
2. 搜索工作流：文献搜索和筛选
3. 写作工作流：大纲生成、初稿撰写、审查迭代
4. 报告工作流：定时报告生成
5. 问答工作流：智能问答
6. 修改工作流：论文修改和润色
"""
import logging
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime
from aiohttp import web
import json

logger = logging.getLogger(__name__)

# 工作流实例缓存
_workflow_instance = None


def get_workflow():
    """获取或创建统一工作流实例"""
    global _workflow_instance

    if _workflow_instance is None:
        from src.agents_v2.langgraph_workflow.unified_workflow import UnifiedWorkflow

        # 创建工作流实例
        _workflow_instance = UnifiedWorkflow(
            llm=None,  # 将使用默认 LLM 配置
            enable_memory=True,
            enable_multimodal=True,
            enable_kg=True,
            enable_evaluation=True,
        )

        # 编译工作流图
        _workflow_instance.compile()
        logger.info("Unified workflow initialized and compiled")

    return _workflow_instance


async def execute_workflow(request: web.Request) -> web.Response:
    """POST /api/workflow/execute - 执行统一工作流"""
    try:
        data = await request.json()
        query = data.get("query", "")

        if not query:
            return web.json_response({
                "success": False,
                "error": "Query is required"
            }, status=400)

        # 获取工作流实例
        workflow = get_workflow()

        # 执行工作流
        logger.info(f"Executing workflow for query: {query}")
        result = await workflow.run(
            query=query,
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
        )

        return web.json_response({
            "success": True,
            "data": {
                "intent": result.get("intent"),
                "route_path": result.get("route_path"),
                "papers": result.get("papers", []),
                "selected_papers": result.get("selected_papers", []),
                "outline": result.get("outline", ""),
                "draft": result.get("draft", ""),
                "feedback": result.get("feedback", []),
                "errors": result.get("errors", []),
            }
        })

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def search_papers(request: web.Request) -> web.Response:
    """POST /api/workflow/search - 搜索工作流（仅搜索和筛选）"""
    try:
        data = await request.json()
        query = data.get("query", "")
        max_results = data.get("max_results", 20)

        if not query:
            return web.json_response({
                "success": False,
                "error": "Query is required"
            }, status=400)

        # 获取工作流实例
        workflow = get_workflow()

        # 执行搜索工作流（通过 run 方法传入 query，路由会自动分发到 search 路径）
        logger.info(f"Executing search workflow for query: {query}")
        result = await workflow.run(query=query)

        return web.json_response({
            "success": True,
            "data": {
                "query": query,
                "papers": result.get("papers", []),
                "selected_papers": result.get("selected_papers", []),
                "total_found": len(result.get("papers", [])),
                "total_selected": len(result.get("selected_papers", [])),
            }
        })

    except Exception as e:
        logger.error(f"Search workflow failed: {e}", exc_info=True)
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def generate_report(request: web.Request) -> web.Response:
    """POST /api/workflow/report - 报告工作流（搜索 → 分析 → 生成）"""
    try:
        data = await request.json()
        report_type = data.get("report_type", "daily")
        keywords = data.get("keywords", [])
        query = data.get("query", "")

        if not keywords and not query:
            return web.json_response({
                "success": False,
                "error": "keywords or query is required"
            }, status=400)

        # 获取工作流实例
        workflow = get_workflow()

        # 执行报告工作流
        logger.info(f"Executing report workflow: type={report_type}")
        result = await workflow.run(
            query=query or " ".join(keywords),
            report_type=report_type,
            keywords=keywords,
        )

        return web.json_response({
            "success": True,
            "data": {
                "report_type": report_type,
                "report_content": result.get("report_content", ""),
                "report_stats": result.get("report_stats", {}),
                "papers": result.get("papers", []),
                "total_papers": len(result.get("papers", [])),
            }
        })

    except Exception as e:
        logger.error(f"Report workflow failed: {e}", exc_info=True)
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def get_workflow_status(request: web.Request) -> web.Response:
    """GET /api/workflow/status - 获取工作流状态"""
    try:
        workflow = get_workflow()
        
        return web.json_response({
            "success": True,
            "data": {
                "initialized": workflow is not None,
                "compiled": workflow.app is not None if workflow else False,
                "enabled_features": {
                    "memory": workflow.enable_memory if workflow else False,
                    "multimodal": workflow.enable_multimodal if workflow else False,
                    "kg": workflow.enable_kg if workflow else False,
                    "evaluation": workflow.enable_evaluation if workflow else False,
                }
            }
        })

    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}", exc_info=True)
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


def register_routes(app: web.Application):
    """注册工作流 API 路由"""
    app.router.add_post("/api/workflow/execute", execute_workflow)
    app.router.add_post("/api/workflow/search", search_papers)
    app.router.add_post("/api/workflow/report", generate_report)
    app.router.add_get("/api/workflow/status", get_workflow_status)
    logger.info("Workflow API routes registered")
