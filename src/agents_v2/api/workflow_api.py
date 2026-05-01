"""
工作流 API - Workflow API

提供统一工作流的 REST API 端点，支持：
1. 智能路由：根据用户查询自动分发到不同工作流
2. 搜索工作流：文献搜索和筛选
3. 写作工作流：大纲生成、初稿撰写、审查迭代
4. 报告工作流：定时报告生成
5. 问答工作流：智能问答
6. 修改工作流：论文修改和润色
7. HITL：人机协作中断/恢复
"""
import logging
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime
from aiohttp import web
import json

logger = logging.getLogger(__name__)

# 工作流实例缓存（按 HITL 模式分开缓存）
_workflow_instances: Dict[str, Any] = {}


def get_workflow(enable_hitl: bool = False):
    """获取或创建统一工作流实例

    Args:
        enable_hitl: 是否启用 HITL 模式（会使用不同的编译配置）

    Returns:
        UnifiedWorkflow 实例
    """
    cache_key = "hitl" if enable_hitl else "default"

    if cache_key not in _workflow_instances:
        from src.agents_v2.langgraph_workflow.unified_workflow import UnifiedWorkflow

        instance = UnifiedWorkflow(
            llm=None,
            enable_memory=True,
            enable_multimodal=True,
            enable_kg=True,
            enable_evaluation=True,
            enable_hitl=enable_hitl,
        )
        instance.compile()
        _workflow_instances[cache_key] = instance
        logger.info(f"Unified workflow initialized (hitl={enable_hitl})")

    return _workflow_instances[cache_key]


async def execute_workflow(request: web.Request) -> web.Response:
    """POST /api/workflow/execute - 执行统一工作流

    Request body:
        query: 用户查询（必需）
        user_id: 用户 ID
        session_id: 会话 ID
        enable_hitl: 是否启用 HITL 人机协作（默认 false）

    Response:
        当 enable_hitl=false 时返回完整结果。
        当 enable_hitl=true 时可能返回中断状态，需用 /api/workflow/resume 恢复。
    """
    try:
        data = await request.json()
        query = data.get("query", "")

        if not query:
            return web.json_response({
                "success": False,
                "error": "Query is required"
            }, status=400)

        enable_hitl = data.get("enable_hitl", False)
        workflow = get_workflow(enable_hitl=enable_hitl)

        logger.info(f"Executing workflow for query: {query} (hitl={enable_hitl})")
        result = await workflow.run(
            query=query,
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
        )

        state = result["state"]
        response_data = {
            "intent": state.get("intent"),
            "route_path": state.get("route_path"),
            "papers": state.get("papers", []),
            "selected_papers": state.get("selected_papers", []),
            "outline": state.get("outline", ""),
            "draft": state.get("draft", ""),
            "feedback": state.get("feedback", []),
            "errors": state.get("errors", []),
            "thread_id": result["thread_id"],
            "interrupted": result["interrupted"],
            "interrupt_node": result["interrupt_node"],
        }

        # HITL 中断时返回 202 Accepted
        status_code = 202 if result["interrupted"] else 200

        return web.json_response({
            "success": True,
            "data": response_data,
        }, status=status_code)

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
                    "hitl": workflow.enable_hitl if workflow else False,
                }
            }
        })

    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}", exc_info=True)
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def resume_workflow(request: web.Request) -> web.Response:
    """POST /api/workflow/resume - 从 HITL 中断点恢复工作流

    Request body:
        thread_id: 之前 execute 返回的线程 ID（必需）
        decision: 人工决策 - "approve" / "revise" / "reject"（默认 approve）
        feedback: 人工反馈内容（decision=revise 时提供修改意见）

    Response:
        恢复后的执行结果，可能再次中断（多中断点场景）。
    """
    try:
        data = await request.json()
        thread_id = data.get("thread_id", "")

        if not thread_id:
            return web.json_response({
                "success": False,
                "error": "thread_id is required"
            }, status=400)

        decision = data.get("decision", "approve")
        feedback = data.get("feedback", "")

        workflow = get_workflow(enable_hitl=True)

        logger.info(f"Resuming workflow thread {thread_id}: decision={decision}")
        result = await workflow.resume(
            thread_id=thread_id,
            decision=decision,
            feedback=feedback,
        )

        state = result["state"]
        response_data = {
            "intent": state.get("intent"),
            "route_path": state.get("route_path"),
            "papers": state.get("papers", []),
            "selected_papers": state.get("selected_papers", []),
            "outline": state.get("outline", ""),
            "draft": state.get("draft", ""),
            "feedback": state.get("feedback", []),
            "errors": state.get("errors", []),
            "thread_id": result["thread_id"],
            "interrupted": result["interrupted"],
            "interrupt_node": result["interrupt_node"],
            "diff": result.get("diff", {}),
        }

        status_code = 202 if result["interrupted"] else 200

        return web.json_response({
            "success": True,
            "data": response_data,
        }, status=status_code)

    except Exception as e:
        logger.error(f"Workflow resume failed: {e}", exc_info=True)
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def get_hitl_status(request: web.Request) -> web.Response:
    """GET /api/workflow/hitl/{thread_id} - 获取指定线程的 HITL 中断状态

    Response:
        interrupted: 是否处于中断状态
        interrupt_node: 中断节点名
        state: 当前工作流状态快照
    """
    try:
        thread_id = request.match_info.get("thread_id", "")

        if not thread_id:
            return web.json_response({
                "success": False,
                "error": "thread_id is required"
            }, status=400)

        workflow = get_workflow(enable_hitl=True)
        info = workflow.get_interrupt_info(thread_id)

        return web.json_response({
            "success": True,
            "data": info,
        })

    except Exception as e:
        logger.error(f"Failed to get HITL status: {e}", exc_info=True)
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
    # HITL 路由
    app.router.add_post("/api/workflow/resume", resume_workflow)
    app.router.add_get("/api/workflow/hitl/{thread_id}", get_hitl_status)
    logger.info("Workflow API routes registered (including HITL)")
