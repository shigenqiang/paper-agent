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
    """从文本中提取实体（方法、数据集、任务、指标等）"""
    entities = []
    text_lower = text.lower()

    # 提取常见AI/ML方法
    methods = [
        "Transformer", "BERT", "GPT", "GPT-2", "GPT-3", "GPT-4", "GPT-4o",
        "LSTM", "CNN", "RNN", "ResNet", "ViT", "GAN", "VAE", "AE",
        "Attention", "Self-Attention", "Cross-Attention",
        "Neural Network", "Deep Learning", "Machine Learning",
        "ELMo", "XLNet", "RoBERTa", "ALBERT", "T5", "BART",
        "Word2Vec", "GloVe", "FastText",
        "SVM", "Random Forest", "Gradient Boosting", "XGBoost", "LightGBM",
        "K-Means", "DBSCAN", "PCA", "t-SNE", "UMAP",
        "Logistic Regression", "Linear Regression", "Decision Tree",
        "Reinforcement Learning", "Supervised Learning", "Unsupervised Learning",
        "Transfer Learning", "Meta Learning", "Multi-Task Learning",
        "Graph Neural Network", "GCN", "GAT", "GraphSAGE",
        "Adversarial Training", "Contrastive Learning", "Contrastive Loss",
        "Knowledge Distillation", "Quantization", "Pruning"
    ]

    for method in methods:
        if method.lower() in text_lower:
            entities.append({
                "name": method,
                "type": "method"
            })

    # 提取常见数据集
    datasets = [
        "ImageNet", "COCO", "MNIST", "SQuAD", "GLUE", "SuperGLUE",
        "Wikipedia", "BookCorpus", "Common Crawl", "OpenWebText",
        "PubMed", "arXiv", "Reddit", "Twitter", "Facebook",
        "CIFAR-10", "CIFAR-100", "SVHN", "FLICKR", "MSCOCO",
        "WikiText", "Penn Treebank", "CoNLL", "ACE",
        "Visual Genome", "Flickr30k", "SNLI", "MNLI", "QQP", "QNLI"
    ]

    for dataset in datasets:
        if dataset.lower() in text_lower:
            entities.append({
                "name": dataset,
                "type": "dataset"
            })

    # 提取常见任务类型
    tasks = [
        "classification", "detection", "segmentation", "parsing",
        "translation", "generation", "summarization", "extraction",
        "recognition", "prediction", "estimation", "retrieval",
        "question answering", "qa", "machine reading comprehension",
        "named entity recognition", "ner", "part-of-speech tagging",
        "dependency parsing", "semantic parsing", "sentiment analysis",
        "image captioning", "visual question answering", "vqa",
        "object detection", "semantic segmentation", "instance segmentation",
        "pose estimation", "face recognition", "speech recognition"
    ]

    for task in tasks:
        if task in text_lower:
            entities.append({
                "name": task.replace("question answering", "QA").replace("named entity recognition", "NER"),
                "type": "task"
            })

    # 提取常见评估指标
    metrics = [
        "accuracy", "precision", "recall", "f1", "f1-score",
        "auc", "roc", "map", "mrr", "ndcg",
        "bleu", "rouge", "meteor", "cider",
        "perplexity", "loss", "cross-entropy",
        "iou", "dice", "hausdorff distance"
    ]

    for metric in metrics:
        if metric in text_lower:
            entities.append({
                "name": metric.upper() if metric in ["auc", "roc", "f1", "map", "mrr", "ndcg", "iou"] else metric,
                "type": "metric"
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
    # 跟踪已添加的实体（按类型分组）
    entity_tracker = {
        "method": set(),
        "dataset": set(),
        "task": set(),
        "metric": set()
    }
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

        # 从标题和摘要中提取所有实体
        text = f"{title} {abstract}"
        extracted_entities = _extract_entities_from_text(text)

        for entity in extracted_entities:
            entity_name = entity["name"]
            entity_type = entity["type"]
            entity_key = f"{entity_type}_{entity_name}"

            # 检查是否已添加该实体
            if entity_name not in entity_tracker[entity_type]:
                entity_tracker[entity_type].add(entity_name)
                nodes.append({
                    "id": f"{entity_type}_{entity_name}",
                    "label": entity_name,
                    "type": entity_type
                })

            # 添加论文-实体关系
            edges.append({
                "source": paper_id,
                "target": f"{entity_type}_{entity_name}",
                "relation": "uses" if entity_type == "method" else "applies_to"
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

    # 发现论文之间的关联（基于共同实体）
    paper_entity_map = {}
    for paper in papers:
        paper_id = paper.get("id", f"paper_{len(nodes)}")
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
        entities = _extract_entities_from_text(text)
        # 按类型组织实体
        paper_entity_map[paper_id] = {e["type"]: {e["name"] for e in entities if e["type"] == e["type"]}
                                   for e_type in entity_tracker}

    # 基于共同方法/数据集等创建论文间的隐式关系
    paper_list = list(paper_ids)
    for i, p1 in enumerate(paper_list):
        for p2 in paper_list[i+1:]:
            # 检查共同的方法
            common_methods = paper_entity_map.get(p1, {}).get("method", set()) & \
                            paper_entity_map.get(p2, {}).get("method", set())
            if common_methods:
                for method in list(common_methods)[:1]:  # 最多1条边
                    edges.append({
                        "source": p1,
                        "target": p2,
                        "relation": f"shares_method_{method}"
                    })

            # 检查共同的数据集
            common_datasets = paper_entity_map.get(p1, {}).get("dataset", set()) & \
                            paper_entity_map.get(p2, {}).get("dataset", set())
            if common_datasets:
                for dataset in list(common_datasets)[:1]:
                    edges.append({
                        "source": p1,
                        "target": p2,
                        "relation": f"uses_same_dataset"
                    })

    # 计算统计信息
    total_entities = (
        len(entity_tracker["method"]) +
        len(entity_tracker["dataset"]) +
        len(entity_tracker["task"]) +
        len(entity_tracker["metric"])
    )

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "totalEntities": len(nodes),
            "totalRelations": len(edges),
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "paper_count": len(papers),
            "method_count": len(entity_tracker["method"]),
            "dataset_count": len(entity_tracker["dataset"]),
            "task_count": len(entity_tracker["task"]),
            "metric_count": len(entity_tracker["metric"])
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


async def handle_detect_communities(request: web.Request) -> web.Response:
    """社区检测接口

    Query params (optional):
    - algorithm: "leiden" (default), "louvain", "label_propagation"

    Returns community detection results with hierarchical structure.
    """
    start_time = time.time()
    try:
        algorithm = request.query.get("algorithm", "leiden")

        # 将边转换为元组列表
        edges = []
        for edge in _graph_storage.get("edges", []):
            source = edge.get("source", "")
            target = edge.get("target", "")
            if source and target:
                edges.append((source, target))

        if not edges:
            return web.json_response({
                "success": True,
                "data": {
                    "communities": [],
                    "hierarchy": {"levels": {}},
                    "modularity": 0.0,
                    "algorithm": algorithm,
                    "stats": {
                        "total_communities": 0,
                        "largest_community": 0,
                        "smallest_community": 0
                    }
                },
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            })

        # 执行社区检测
        from src.agents_v2.knowledge_graph.kg_community import (
            detect_communities,
            CommunityAlgorithm
        )

        if algorithm == "louvain":
            algo = CommunityAlgorithm.LOUVAIN
        elif algorithm == "label_propagation":
            algo = CommunityAlgorithm.LABEL_PROPAGATION
        else:
            algo = CommunityAlgorithm.LEIDEN

        result = detect_communities(edges, algorithm=algo)

        # 格式化社区数据
        communities_data = []
        for comm in result.get("communities", []):
            # 获取社区成员的类型分布
            member_types = {}
            for member_id in comm.members:
                for node in _graph_storage.get("nodes", []):
                    if node.get("id") == member_id:
                        node_type = node.get("type", "unknown")
                        member_types[node_type] = member_types.get(node_type, 0) + 1
                        break

            communities_data.append({
                "id": comm.community_id,
                "level": comm.level,
                "members": comm.members,
                "size": len(comm.members),
                "member_types": member_types,
                "keywords": comm.keywords,
                "summary": comm.summary,
                "quality_score": comm.quality_score
            })

        # 计算统计信息
        if communities_data:
            sizes = [c["size"] for c in communities_data]
            stats = {
                "total_communities": len(communities_data),
                "largest_community": max(sizes),
                "smallest_community": min(sizes),
                "average_size": sum(sizes) / len(sizes)
            }
        else:
            stats = {
                "total_communities": 0,
                "largest_community": 0,
                "smallest_community": 0,
                "average_size": 0
            }

        # 格式化层次结构
        hierarchy_data = {"levels": {}}
        if result.get("hierarchy"):
            for level, communities in result["hierarchy"].levels.items():
                hierarchy_data["levels"][str(level)] = [
                    {"id": c.community_id, "size": len(c.members)}
                    for c in communities
                ]

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "data": {
                "communities": communities_data,
                "hierarchy": hierarchy_data,
                "modularity": result.get("modularity", 0.0),
                "algorithm": algorithm,
                "stats": stats
            },
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Detect communities error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_get_community_papers(request: web.Request) -> web.Response:
    """获取社区内的论文

    Path params:
    - communityId: 社区ID

    Query params:
    - level: 社区层级 (default: 0)
    """
    start_time = time.time()
    try:
        community_id = request.match_info.get("communityId", "")
        level = int(request.query.get("level", 0))

        if not community_id:
            return web.json_response({
                "success": False,
                "error": "communityId is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        # 获取社区成员
        member_ids = set()
        for edge in _graph_storage.get("edges", []):
            source = edge.get("source", "")
            target = edge.get("target", "")
            if source == community_id or target == community_id:
                if source != community_id:
                    member_ids.add(source)
                if target != community_id:
                    member_ids.add(target)

        # 获取论文节点
        papers = []
        for node in _graph_storage.get("nodes", []):
            if node.get("type") == "paper" and node.get("id") in member_ids:
                papers.append({
                    "id": node.get("id"),
                    "title": node.get("title", node.get("label", "")),
                    "label": node.get("label", "")
                })

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "data": {
                "community_id": community_id,
                "level": level,
                "papers": papers,
                "total_papers": len(papers)
            },
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Get community papers error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_node_centrality(request: web.Request) -> web.Response:
    """节点中心性分析

    计算图中各节点的重要程度：
    - degree: 度中心性（连接数）
    - betweenness: 介数中心性（最短路径经过次数）

    Returns:
        各节点的中心性分数
    """
    start_time = time.time()
    try:
        algorithm = request.query.get("algorithm", "degree")

        # 构建邻接表
        adj: Dict[str, Set[str]] = {}
        degree: Dict[str, int] = {}
        betweenness: Dict[str, float] = {}

        for edge in _graph_storage.get("edges", []):
            source = edge.get("source", "")
            target = edge.get("target", "")
            if source and target:
                if source not in adj:
                    adj[source] = set()
                if target not in adj:
                    adj[target] = set()
                adj[source].add(target)
                adj[target].add(source)

        nodes = list(adj.keys())
        total_nodes = len(nodes)

        # 计算度中心性
        if algorithm == "degree":
            for node in nodes:
                degree[node] = len(adj.get(node, set()))
            max_degree = max(degree.values()) if degree else 1

            centrality = {
                node: {
                    "degree": degree.get(node, 0),
                    "normalized": degree.get(node, 0) / max_degree if max_degree > 0 else 0
                }
                for node in nodes
            }
        else:
            # 介数中心性（简化版）
            for node in nodes:
                betweenness[node] = 0.0

            # 计算每对节点之间的最短路径
            for i, start in enumerate(nodes):
                for end in nodes[i+1:]:
                    # BFS找最短路径
                    path = _bfs_shortest_path(adj, start, end)
                    if path:
                        for mid in path[1:-1]:
                            betweenness[mid] += 1

            max_betweenness = max(betweenness.values()) if betweenness else 1
            centrality = {
                node: {
                    "betweenness": betweenness.get(node, 0),
                    "normalized": betweenness.get(node, 0) / max_betweenness if max_betweenness > 0 else 0
                }
                for node in nodes
            }

        # 排序
        sorted_centrality = sorted(
            centrality.items(),
            key=lambda x: x[1].get("degree", x[1].get("betweenness", 0)),
            reverse=True
        )

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "data": {
                "algorithm": algorithm,
                "total_nodes": total_nodes,
                "centrality": [
                    {"node_id": node_id, **scores}
                    for node_id, scores in sorted_centrality[:50]  # Top 50
                ],
                "top_hub_nodes": [n[0] for n in sorted_centrality[:5]]
            },
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Node centrality error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_find_paths(request: web.Request) -> web.Response:
    """查找两节点之间的路径

    Query params:
    - source: 起始节点ID
    - target: 目标节点ID
    - max_depth: 最大路径长度 (default: 3)

    Returns:
        两节点之间的所有路径
    """
    start_time = time.time()
    try:
        source = request.query.get("source", "")
        target = request.query.get("target", "")
        max_depth = int(request.query.get("max_depth", "3"))

        if not source or not target:
            return web.json_response({
                "success": False,
                "error": "source and target are required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        # 构建邻接表
        adj: Dict[str, Set[str]] = {}
        for edge in _graph_storage.get("edges", []):
            src = edge.get("source", "")
            dst = edge.get("target", "")
            if src and dst:
                if src not in adj:
                    adj[src] = set()
                if dst not in adj:
                    adj[dst] = set()
                adj[src].add(dst)
                adj[dst].add(src)

        # 查找所有路径
        paths = []
        visited = set()

        def dfs(current: str, path: List[str], depth: int):
            if depth > max_depth:
                return
            if current == target and len(path) > 1:
                paths.append(path.copy())
                return
            if current in visited:
                return

            visited.add(current)
            for neighbor in adj.get(current, set()):
                if neighbor not in visited or neighbor == target:
                    path.append(neighbor)
                    dfs(neighbor, path, depth + 1)
                    path.pop()
            visited.discard(current)

        dfs(source, [source], 0)

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "data": {
                "source": source,
                "target": target,
                "max_depth": max_depth,
                "path_count": len(paths),
                "paths": paths[:20]  # 最多返回20条路径
            },
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Find paths error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def handle_neighborhood(request: web.Request) -> web.Response:
    """邻居节点分析

    Path params:
    - entityId: 实体ID

    Query params:
    - depth: 探索深度 (default: 1)

    Returns:
        指定节点的邻居及其关系
    """
    start_time = time.time()
    try:
        entity_id = request.match_info.get("entityId", "")
        depth = int(request.query.get("depth", "1"))

        if not entity_id:
            return web.json_response({
                "success": False,
                "error": "entityId is required",
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }, status=400)

        # 构建邻接表和边映射
        adj: Dict[str, Set[str]] = {}
        edge_map: Dict[str, List[Dict]] = {}

        for edge in _graph_storage.get("edges", []):
            src = edge.get("source", "")
            dst = edge.get("target", "")
            rel = edge.get("relation", "related")
            if src and dst:
                if src not in adj:
                    adj[src] = set()
                    edge_map[src] = []
                if dst not in adj:
                    adj[dst] = set()
                    edge_map[dst] = []
                adj[src].add(dst)
                adj[dst].add(src)
                edge_map.setdefault(src, []).append({"target": dst, "relation": rel})
                edge_map.setdefault(dst, []).append({"target": src, "relation": rel})

        # BFS探索邻居
        visited = {entity_id}
        current_level = {entity_id}

        for _ in range(depth):
            next_level = set()
            for node in current_level:
                for neighbor in adj.get(node, set()):
                    if neighbor not in visited:
                        next_level.add(neighbor)
            visited.update(next_level)
            current_level = next_level

        # 获取邻居节点信息
        neighbors = []
        for node_id in visited:
            if node_id == entity_id:
                continue
            # 找到连接关系
            rel_to_entity = []
            for edge in _graph_storage.get("edges", []):
                if (edge.get("source") == entity_id and edge.get("target") == node_id) or \
                   (edge.get("target") == entity_id and edge.get("source") == node_id):
                    rel_to_entity.append(edge.get("relation", "related"))

            # 获取节点类型
            node_type = "unknown"
            for node in _graph_storage.get("nodes", []):
                if node.get("id") == node_id:
                    node_type = node.get("type", "unknown")
                    break

            neighbors.append({
                "id": node_id,
                "type": node_type,
                "relations": rel_to_entity
            })

        execution_time = time.time() - start_time
        return web.json_response({
            "success": True,
            "data": {
                "entity_id": entity_id,
                "depth": depth,
                "total_neighbors": len(neighbors),
                "neighbors": neighbors
            },
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Neighborhood error: {e}")
        execution_time = time.time() - start_time
        return web.json_response({
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }, status=500)


def _bfs_shortest_path(adj: Dict[str, Set[str]], start: str, end: str) -> Optional[List[str]]:
    """BFS查找最短路径"""
    from collections import deque

    if start == end:
        return [start]

    queue = deque([(start, [start])])
    visited = {start}

    while queue:
        current, path = queue.popleft()
        for neighbor in adj.get(current, set()):
            if neighbor == end:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return None


def setup_knowledge_graph_routes(app: web.Application) -> None:
    """注册知识图谱API路由

    Args:
        app: aiohttp web应用实例
    """
    app.router.add_get('/api/knowledge-graph/literature', handle_get_literature_graph)
    app.router.add_post('/api/knowledge-graph/generate', handle_generate_graph)
    app.router.add_get('/api/knowledge-graph/entity/{entityId}', handle_get_entity_relations)
    app.router.add_post('/api/knowledge-graph/query', handle_query_graph)
    app.router.add_get('/api/knowledge-graph/communities', handle_detect_communities)
    app.router.add_get('/api/knowledge-graph/communities/{communityId}/papers', handle_get_community_papers)
    app.router.add_get('/api/knowledge-graph/centrality', handle_node_centrality)
    app.router.add_get('/api/knowledge-graph/paths', handle_find_paths)
    app.router.add_get('/api/knowledge-graph/entity/{entityId}/neighbors', handle_neighborhood)

    logger.info("Knowledge graph routes registered")
