"""
API Server - HTTP接口服务

提供HTTP API访问Agent能力

使用方法:
    python -m src.agents_v2.api_server

认证:
    设置环境变量 API_KEY，然后请求头添加 X-API-Key
"""
import asyncio
import logging
import time
from typing import Any, Dict, Optional
from datetime import datetime
from aiohttp import web
import os
import json

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Key配置
API_KEY = os.getenv('API_KEY', 'dev-api-key')

# 公开端点（不需要认证）
PUBLIC_ENDPOINTS = {'/health', '/docs', '/openapi.json'}


def is_public_endpoint(path: str) -> bool:
    """检查是否是公开端点"""
    return path in PUBLIC_ENDPOINTS or path.startswith('/static')


@web.middleware
async def api_key_auth_middleware(request: web.Request, handler):
    """
    API密钥认证中间件

    公开端点不需要认证，其他端点需要有效的API密钥
    """
    # 公开端点跳过认证
    if is_public_endpoint(request.path):
        return await handler(request)

    # 检查API密钥
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        logger.warning(f"Missing API key for {request.path}")
        return web.json_response({
            "success": False,
            "error": "Missing API key. Set X-API-Key header."
        }, status=401)

    if api_key != API_KEY:
        logger.warning(f"Invalid API key for {request.path}")
        return web.json_response({
            "success": False,
            "error": "Invalid API key"
        }, status=401)

    return await handler(request)


async def health_check(request: web.Request) -> web.Response:
    """健康检查"""
    from datetime import datetime
    import time

    return web.json_response({
        "status": "healthy",
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "api": "available",
            "llm": "available" if os.getenv('OPENAI_API_KEY') else "unavailable",
            "cache": "available"
        }
    })


async def handle_topic(request: web.Request) -> web.Response:
    """处理选题请求"""
    start_time = time.time()
    try:
        data = await request.json()
        user_request = data.get("user_request", "")

        if not user_request:
            return web.json_response({
                "success": False,
                "error": "user_request is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.paper_agents import TopicAgent
        from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

        llm_config = LLMConfig(
            provider="openai",
            model_name="minimax",
            temperature=0.7
        )

        agent = TopicAgent(llm_config)
        result = await agent.execute({"user_request": user_request})

        execution_time = time.time() - start_time
        return web.json_response({
            "success": result.success,
            "result": result.result,
            "quality_score": result.quality_score,
            "error": result.error,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Topic handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_search(request: web.Request) -> web.Response:
    """处理论文搜索请求"""
    start_time = time.time()
    try:
        data = await request.json()
        query = data.get("query", "")
        source = data.get("source", "all")
        max_results = data.get("max_results", 10)

        if not query:
            return web.json_response({
                "success": False,
                "error": "query is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.qa import PaperSearchAgent

        agent = PaperSearchAgent()
        result = await agent.execute(
            query,
            {"source": source, "max_results": max_results}
        )

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "papers": result.get("papers", []),
            "total": len(result.get("papers", [])),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Search handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_route(request: web.Request) -> web.Response:
    """处理意图路由请求"""
    start_time = time.time()
    try:
        data = await request.json()
        user_request = data.get("user_request", "")

        if not user_request:
            return web.json_response({
                "success": False,
                "error": "user_request is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.unified import IntentRouter

        router = IntentRouter()
        result = await router.route(user_request)

        execution_time = time.time() - start_time
        result["execution_time"] = execution_time
        result["timestamp"] = datetime.now().isoformat()

        return web.json_response(result)

    except Exception as e:
        logger.error(f"Route handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_literature(request: web.Request) -> web.Response:
    """处理文献综述请求"""
    start_time = time.time()
    try:
        data = await request.json()
        topic = data.get("topic", "")

        if not topic:
            return web.json_response({
                "success": False,
                "error": "topic is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.writing import LiteratureReviewAgent

        agent = LiteratureReviewAgent()
        result = await agent.execute({"topic": topic})

        execution_time = time.time() - start_time
        return web.json_response({
            "success": result.success,
            "result": result.result,
            "quality_score": result.quality_score,
            "error": result.error,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Literature handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_proposal(request: web.Request) -> web.Response:
    """处理开题报告请求"""
    start_time = time.time()
    try:
        data = await request.json()
        topic = data.get("topic", "")
        research_background = data.get("research_background", "")
        research_significance = data.get("research_significance", "")

        if not topic:
            return web.json_response({
                "success": False,
                "error": "topic is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.writing import ProposalGeneratorAgent

        agent = ProposalGeneratorAgent()
        result = await agent.execute({
            "topic": topic,
            "research_background": research_background,
            "research_significance": research_significance
        })

        execution_time = time.time() - start_time
        return web.json_response({
            "success": result.success,
            "result": result.result,
            "quality_score": result.quality_score,
            "error": result.error,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Proposal handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_full_paper(request: web.Request) -> web.Response:
    """处理完整论文请求"""
    start_time = time.time()
    try:
        data = await request.json()
        topic = data.get("topic", "")

        if not topic:
            return web.json_response({
                "success": False,
                "error": "topic is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.unified import MasterSupervisor

        supervisor = MasterSupervisor()
        supervisor.register_pipeline_agents()
        supervisor.register_writing_agents()

        result = await supervisor.run("full_paper", {"topic": topic})

        execution_time = time.time() - start_time
        return web.json_response({
            "success": result.get("success", False),
            "result": result,
            "quality_score": result.get("final_quality", 0),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Full paper handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_draft(request: web.Request) -> web.Response:
    """处理论文初稿请求"""
    start_time = time.time()
    try:
        data = await request.json()
        topic = data.get("topic", "")
        outline = data.get("outline", None)

        if not topic:
            return web.json_response({
                "success": False,
                "error": "topic is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.writing import DraftGeneratorAgent

        agent = DraftGeneratorAgent()
        input_data = {"topic": topic}
        if outline:
            input_data["outline"] = outline

        result = await agent.execute(input_data)

        execution_time = time.time() - start_time
        return web.json_response({
            "success": result.success,
            "result": result.result,
            "quality_score": result.quality_score,
            "error": result.error,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Draft handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_revise(request: web.Request) -> web.Response:
    """处理论文局部修改请求"""
    start_time = time.time()
    try:
        data = await request.json()
        content = data.get("content", "")
        revision_type = data.get("revision_type", "general")

        if not content:
            return web.json_response({
                "success": False,
                "error": "content is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.writing import SmartReviserAgent

        agent = SmartReviserAgent()
        result = await agent.execute({
            "content": content,
            "revision_type": revision_type
        })

        execution_time = time.time() - start_time
        return web.json_response({
            "success": result.success,
            "result": result.result,
            "quality_score": result.quality_score,
            "error": result.error,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Revise handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_diagnostics(request: web.Request) -> web.Response:
    """处理诊断请求"""
    start_time = time.time()
    try:
        data = await request.json()
        content = data.get("content", {})
        phase = data.get("phase", "general")

        if not content:
            return web.json_response({
                "success": False,
                "error": "content is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        from src.agents_v2.unified import MasterSupervisor

        supervisor = MasterSupervisor()
        supervisor.register_problem_agents()

        result = await supervisor.run("diagnostic_only", {
            "content": content,
            "phase": phase
        })

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "result": result,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Diagnostics handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


def create_app() -> web.Application:
    """创建Web应用"""
    app = web.Application()

    # 添加认证中间件
    app.middlewares.append(api_key_auth_middleware)

    # 路由
    app.router.add_get('/health', health_check)
    app.router.add_post('/api/topic', handle_topic)
    app.router.add_post('/api/search', handle_search)
    app.router.add_post('/api/route', handle_route)
    app.router.add_post('/api/literature', handle_literature)
    app.router.add_post('/api/proposal', handle_proposal)
    app.router.add_post('/api/paper', handle_full_paper)
    app.router.add_post('/api/draft', handle_draft)
    app.router.add_post('/api/revise', handle_revise)
    app.router.add_post('/api/diagnostics', handle_diagnostics)
    app.router.add_post('/api/batch', handle_batch)

    # WebSocket端点
    app.router.add_get('/ws/status', handle_websocket_status)

    # Paper Agent RESTful API (frontend)
    from src.agents_v2.api.paper_api import setup_paper_routes
    setup_paper_routes(app)

    return app


async def handle_batch(request: web.Request) -> web.Response:
    """处理批量请求"""
    start_time = time.time()
    try:
        data = await request.json()
        requests = data.get("requests", [])

        if not requests or not isinstance(requests, list):
            return web.json_response({
                "success": False,
                "error": "requests must be a non-empty array",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        results = []
        for req in requests:
            req_type = req.get("type")
            req_data = req.get("data", {})

            try:
                if req_type == "topic":
                    from src.agents_v2.paper_agents import TopicAgent
                    agent = TopicAgent()
                    result = await agent.execute({"user_request": req_data.get("user_request", "")})
                    results.append({"success": result.success, "result": result.result})
                elif req_type == "search":
                    from src.agents_v2.qa import PaperSearchAgent
                    agent = PaperSearchAgent()
                    result = await agent.execute(req_data.get("query", ""), {"max_results": req_data.get("max_results", 10)})
                    results.append({"success": True, "result": result.get("papers", [])})
                elif req_type == "literature":
                    from src.agents_v2.writing import LiteratureReviewAgent
                    agent = LiteratureReviewAgent()
                    result = await agent.execute({"topic": req_data.get("topic", "")})
                    results.append({"success": result.success, "result": result.result})
                else:
                    results.append({"success": False, "error": f"Unknown request type: {req_type}"})
            except Exception as e:
                results.append({"success": False, "error": str(e)})

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "results": results,
            "total": len(results),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Batch handler error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_websocket_status(request: web.Request) -> web.WebSocketResponse:
    """WebSocket状态推送"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    try:
        from src.agents_v2.monitoring import get_global_metrics

        while True:
            metrics = get_global_metrics()
            await ws.send_json({
                "type": "metrics",
                "data": {
                    "total_requests": metrics.get("total_requests", 0),
                    "success_rate": metrics.get("success_rate", 0),
                    "avg_response_time": metrics.get("avg_response_time", 0),
                    "cache_hit_rate": metrics.get("cache_hit_rate", 0),
                    "timestamp": datetime.now().isoformat()
                }
            })
            await asyncio.sleep(5)  # 每5秒推送一次

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws.close()

    return ws


def main():
    """主函数"""
    app = create_app()
    logger.info("Starting API server on http://0.0.0.0:8000")
    web.run_app(app, host='0.0.0.0', port=8000)


if __name__ == "__main__":
    main()
