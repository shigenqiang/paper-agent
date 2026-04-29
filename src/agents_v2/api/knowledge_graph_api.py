"""
知识图谱API模块

提供知识图谱相关的REST API端点:
- GET /knowledge-graph/literature - 获取文献知识图谱
- POST /knowledge-graph/generate - 生成知识图谱
- GET /knowledge-graph/entity/{entityId} - 获取实体关联
"""
import logging
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

from aiohttp import web

logger = logging.getLogger(__name__)


async def handle_get_literature_graph(request: web.Request) -> web.Response:
    """获取文献知识图谱

    Returns the knowledge graph for all literature in the system.
    """
    start_time = time.time()
    try:
        # 获取已有论文
        from src.agents_v2.paper_agents import TopicAgent
        from src.agents_v2.qa import PaperSearchAgent

        # 构建图谱数据
        nodes = []
        edges = []

        # 模拟数据（实际应从存储获取）
        # 后续应连接 Neo4j 或内存图谱存储
        graph_data = {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "communities": 0
            }
        }

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "data": graph_data,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Get literature graph error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_generate_graph(request: web.Request) -> web.Response:
    """生成知识图谱

    根据指定文献ID列表生成知识图谱

    Request body:
    {
        "literatureIds": ["paper_1", "paper_2", ...]
    }
    """
    start_time = time.time()
    try:
        data = await request.json()
        literature_ids = data.get("literatureIds", [])

        if not literature_ids:
            return web.json_response({
                "success": False,
                "error": "literatureIds is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        # 使用知识图谱服务生成
        from src.agents_v2.knowledge_graph import KnowledgeGraphService, ServiceConfig

        config = ServiceConfig(
            vector_store_type="memory",
            enable_graphrag=True
        )
        service = KnowledgeGraphService(config)
        await service.initialize()

        # 获取论文数据并提取实体
        nodes = []
        edges = []

        for paper_id in literature_ids:
            # 模拟论文数据（实际应从数据库获取）
            paper_data = {
                "id": paper_id,
                "title": f"Paper {paper_id}",
                "abstract": "",
                "authors": []
            }

            # 添加论文节点
            nodes.append({
                "id": paper_id,
                "type": "paper",
                "label": paper_data["title"][:50]
            })

        # 生成图谱结果
        graph_data = {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "literature_count": len(literature_ids)
            }
        }

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "data": graph_data,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Generate graph error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_get_entity_relations(request: web.Request) -> web.Response:
    """获取实体关联

    根据实体ID获取其关联的实体和关系

    Path params:
    - entityId: 实体ID
    """
    start_time = time.time()
    try:
        entity_id = request.match_info.get("entityId", "")

        if not entity_id:
            return web.json_response({
                "success": False,
                "error": "entityId is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        # 模拟数据（实际应从图谱查询）
        relations = {
            "entity_id": entity_id,
            "entity_type": "paper",
            "incoming": [],
            "outgoing": [],
            "stats": {
                "total_relations": 0
            }
        }

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "data": relations,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Get entity relations error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_query_graph(request: web.Request) -> web.Response:
    """GraphRAG问答接口

    基于知识图谱的问答检索

    Request body:
    {
        "question": "Transformer和BERT有什么关系？"
    }
    """
    start_time = time.time()
    try:
        data = await request.json()
        question = data.get("question", "")

        if not question:
            return web.json_response({
                "success": False,
                "error": "question is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        # 使用GraphRAG进行问答
        from src.agents_v2.knowledge_graph import create_graphrag_qa

        qa = create_graphrag_qa()
        result = qa.query(question)

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "data": {
                "question": question,
                "answer": result.to_prompt_context(),
                "query_type": result.query.query_type.value if hasattr(result.query.query_type, 'value') else str(result.query.query_type)
            },
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Query graph error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


def setup_knowledge_graph_routes(app: web.Application) -> None:
    """注册知识图谱API路由

    Args:
        app: aiohttp web应用实例
    """
    app.router.add_get('/knowledge-graph/literature', handle_get_literature_graph)
    app.router.add_post('/knowledge-graph/generate', handle_generate_graph)
    app.router.add_get('/knowledge-graph/entity/{entityId}', handle_get_entity_relations)
    app.router.add_post('/knowledge-graph/query', handle_query_graph)

    logger.info("Knowledge graph routes registered")
