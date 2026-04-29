"""
知识图谱API模块

提供知识图谱相关的REST API端点:
- GET /knowledge-graph/literature - 获取文献知识图谱
- POST /knowledge-graph/generate - 生成知识图谱
- GET /knowledge-graph/entity/{entityId} - 获取实体关联
"""
import logging
import time
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from aiohttp import web

logger = logging.getLogger(__name__)

# 内存中的图谱存储（生产环境应使用Neo4j）
_graph_storage: Dict[str, Any] = {
    "nodes": [],
    "edges": []
}


def _extract_entities_from_text(text: str) -> List[Dict[str, str]]:
    """从文本中提取实体（方法、作者等）"""
    entities = []

    # 提取常见AI/ML方法
    methods = [
        "Transformer", "BERT", "GPT", "GPT-2", "GPT-3", "GPT-4",
        "LSTM", "CNN", "RNN", "ResNet", "ViT", "GAN", "VAE",
        "Attention", "Neural Network", "Deep Learning", "Machine Learning",
        "BERT", "ELMo", "XLNet", "RoBERTa", "ALBERT", "T5", "BART"
    ]

    for method in methods:
        if method.lower() in text.lower():
            entities.append({
                "name": method,
                "type": "method"
            })

    return entities


def _build_graph_from_papers(papers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """从论文列表构建图谱数据

    Args:
        papers: 论文列表，每篇包含 id, title, abstract, authors

    Returns:
        G6兼容的图谱数据
    """
    nodes = []
    edges = []
    method_nodes = set()
    paper_ids = set()

    for paper in papers:
        paper_id = paper.get("id", f"paper_{len(nodes)}")
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        authors = paper.get("authors", [])

        paper_ids.add(paper_id)

        # 添加论文节点
        nodes.append({
            "id": paper_id,
            "label": title[:50] + ("..." if len(title) > 50 else ""),
            "type": "paper",
            "title": title
        })

        # 从标题和摘要中提取方法实体
        text = f"{title} {abstract}"
        extracted_methods = _extract_entities_from_text(text)

        for method in extracted_methods:
            method_name = method["name"]
            if method_name not in method_nodes:
                method_nodes.add(method_name)
                nodes.append({
                    "id": f"method_{method_name}",
                    "label": method_name,
                    "type": "method"
                })

            # 添加论文-方法关系
            edges.append({
                "source": paper_id,
                "target": f"method_{method_name}",
                "relation": "uses"
            })

        # 添加作者节点
        for author in authors[:3]:  # 最多3个作者
            author_id = f"author_{author}".replace(" ", "_")
            if author and len(author) > 1:
                nodes.append({
                    "id": author_id,
                    "label": author,
                    "type": "author"
                })
                edges.append({
                    "source": author_id,
                    "target": paper_id,
                    "relation": "authored"
                })

    # 发现论文之间的引用关系（基于共同方法）
    paper_method_map = {}
    for paper in papers:
        paper_id = paper.get("id", f"paper_{len(nodes)}")
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
        methods = _extract_entities_from_text(text)
        paper_method_map[paper_id] = {m["name"] for m in methods}

    # 基于共同方法创建论文间的隐式关系
    paper_list = list(paper_ids)
    for i, p1 in enumerate(paper_list):
        for p2 in paper_list[i+1:]:
            common_methods = paper_method_map.get(p1, set()) & paper_method_map.get(p2, set())
            if common_methods:
                for method in list(common_methods)[:2]:  # 最多2条边
                    edges.append({
                        "source": p1,
                        "target": p2,
                        "relation": f"shares_{method}"
                    })

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "totalEntities": len(nodes),
            "totalRelations": len(edges),
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "paper_count": len(papers),
            "method_count": len(method_nodes)
        }
    }


async def handle_get_literature_graph(request: web.Request) -> web.Response:
    """获取文献知识图谱

    Query params (optional):
    - papers: JSON字符串化的论文列表

    Returns G6-compatible graph data.
    """
    start_time = time.time()
    try:
        # 尝试从query参数获取论文数据
        papers_param = request.query.get("papers", "[]")

        try:
            papers = eval(papers_param)  # 安全注意：生产环境应用json.loads并验证
        except:
            papers = []

        if papers:
            graph_data = _build_graph_from_papers(papers)
        else:
            # 返回内存中的图谱或空数据
            graph_data = _graph_storage.copy() if _graph_storage["nodes"] else {
                "nodes": [],
                "edges": [],
                "stats": {
                    "totalEntities": 0,
                    "totalRelations": 0,
                    "total_nodes": 0,
                    "total_edges": 0,
                    "paper_count": 0,
                    "method_count": 0
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

    Request body:
    {
        "papers": [
            {"id": "paper_1", "title": "...", "abstract": "...", "authors": ["author1", "author2"]},
            ...
        ]
    }
    或
    {
        "literatureIds": ["paper_1", "paper_2", ...]
    }
    """
    start_time = time.time()
    try:
        data = await request.json()
        papers = data.get("papers", [])
        literature_ids = data.get("literatureIds", [])

        if not papers and not literature_ids:
            return web.json_response({
                "success": False,
                "error": "papers or literatureIds is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        if papers:
            # 直接使用提供的论文数据构建图谱
            graph_data = _build_graph_from_papers(papers)
        else:
            # 使用ID列表构建图谱（需要从存储获取论文数据）
            # 目前返回空图谱，后续可连接实际存储
            graph_data = {
                "nodes": [{"id": lid, "label": f"Paper {lid}", "type": "paper"} for lid in literature_ids],
                "edges": [],
                "stats": {
                    "totalEntities": len(literature_ids),
                    "totalRelations": 0,
                    "total_nodes": len(literature_ids),
                    "total_edges": 0,
                    "literature_count": len(literature_ids),
                    "method_count": 0
                }
            }

        # 更新内存存储
        global _graph_storage
        _graph_storage = graph_data

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

    Path params:
    - entityId: 实体ID

    Returns relations for the specified entity.
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

        # 从内存图谱中查找实体关系
        incoming = []
        outgoing = []

        for edge in _graph_storage.get("edges", []):
            if edge.get("target") == entity_id:
                incoming.append({
                    "source": edge.get("source"),
                    "relation": edge.get("relation", "related")
                })
            if edge.get("source") == entity_id:
                outgoing.append({
                    "target": edge.get("target"),
                    "relation": edge.get("relation", "related")
                })

        # 查找实体类型
        entity_type = "unknown"
        for node in _graph_storage.get("nodes", []):
            if node.get("id") == entity_id:
                entity_type = node.get("type", "unknown")
                break

        relations = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "incoming": incoming,
            "outgoing": outgoing,
            "stats": {
                "total_relations": len(incoming) + len(outgoing),
                "incoming_count": len(incoming),
                "outgoing_count": len(outgoing)
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
        "question": "Transformer和BERT有什么关系？",
        "papers": [...] // 可选的论文上下文
    }
    """
    start_time = time.time()
    try:
        data = await request.json()
        question = data.get("question", "")
        papers = data.get("papers", [])

        if not question:
            return web.json_response({
                "success": False,
                "error": "question is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        # 如果提供了论文，先更新图谱
        if papers:
            graph_data = _build_graph_from_papers(papers)
            global _graph_storage
            _graph_storage = graph_data

        # 使用GraphRAG进行问答
        from src.agents_v2.knowledge_graph import create_graphrag_qa, GraphRAGQA

        qa: GraphRAGQA = create_graphrag_qa()

        # 将图谱数据构建到GraphRAG中
        for node in _graph_storage.get("nodes", []):
            qa.build_index(
                entities=[(node["id"], node.get("type", "unknown"), node.get("label", ""))],
                relations=[]
            )

        # 添加边作为关系
        for edge in _graph_storage.get("edges", []):
            qa.build_index(
                entities=[],
                relations=[(edge["source"], edge["target"], edge.get("relation", "related"))]
            )

        result = qa.query(question)

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "data": {
                "question": question,
                "answer": result.to_prompt_context(),
                "query_type": result.query.query_type.value if hasattr(result.query.query_type, 'value') else str(result.query.query_type),
                "retrieved_entities": [
                    {"id": item.entity_id, "type": item.entity_type, "score": item.score}
                    for item in result.retrieved_items
                ]
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
