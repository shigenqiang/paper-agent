"""
API模块
RESTful API for Knowledge Graph
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from ..storage.neo4j_client import Neo4jClient
from ..storage.graph_builder import AcademicGraphBuilder
from ..graphrag.subgraph_retriever import SubgraphRetriever
from ..graphrag.reasoner import KGReasoner, ReasoningMode
from ..graphrag.answer_generator import GraphRAGAnswerGenerator
from ..visualization.graph_visualizer import KnowledgeGraphVisualizer, VisualizationConfig
from ..config import KGConfig


router = APIRouter(prefix="/api/kg", tags=["knowledge_graph"])


# ============ Request/Response Models ============

class EntityCreate(BaseModel):
    """创建实体请求"""
    id: str
    name: str
    type: str
    properties: Optional[Dict[str, Any]] = None


class RelationCreate(BaseModel):
    """创建关系请求"""
    source: str
    target: str
    type: str
    properties: Optional[Dict[str, Any]] = None


class QueryRequest(BaseModel):
    """查询请求"""
    query: str
    top_k: Optional[int] = 5
    depth: Optional[int] = 2


class SubgraphQueryRequest(BaseModel):
    """子图查询请求"""
    center_id: str
    depth: Optional[int] = 2


class BuildRequest(BaseModel):
    """构建请求"""
    file_paths: List[str]
    batch_mode: Optional[bool] = False


@dataclass
class BuildResponse:
    """构建响应"""
    success: bool
    entities_count: int
    relations_count: int
    message: str


# ============ Dependencies ============

def get_neo4j_client() -> Neo4jClient:
    """获取Neo4j客户端"""
    return Neo4jClient()


def get_config() -> KGConfig:
    """获取配置"""
    return KGConfig()


def get_graph_builder(config: KGConfig = Depends(get_config)) -> AcademicGraphBuilder:
    """获取图构建器"""
    return AcademicGraphBuilder(config)


def get_subgraph_retriever(config: KGConfig = Depends(get_config)) -> SubgraphRetriever:
    """获取子图检索器"""
    return SubgraphRetriever(config)


def get_answer_generator() -> GraphRAGAnswerGenerator:
    """获取答案生成器"""
    return GraphRAGAnswerGenerator()


# ============ Health & Statistics ============

@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "knowledge_graph"}


@router.get("/statistics")
async def get_statistics(client: Neo4jClient = Depends(get_neo4j_client)):
    """获取图谱统计信息"""
    stats = client.get_statistics()
    return stats


# ============ Entity Operations ============

@router.post("/entities")
async def create_entity(
    entity: EntityCreate,
    client: Neo4jClient = Depends(get_neo4j_client)
):
    """创建实体"""
    from ..schema.academic_kg_schema import Entity, EntityType

    entity_obj = Entity(
        id=entity.id,
        name=entity.name,
        type=EntityType(entity.type) if entity.type in [e.value for e in EntityType] else EntityType.PAPER,
        properties=entity.properties or {}
    )

    success = client.insert_entity(entity_obj)

    return {
        "id": entity.id,
        "status": "created" if success else "failed"
    }


@router.get("/entities/{entity_id}")
async def get_entity(
    entity_id: str,
    client: Neo4jClient = Depends(get_neo4j_client)
):
    """获取实体"""
    entity = client.get_entity(entity_id)

    if entity:
        return entity
    else:
        raise HTTPException(status_code=404, detail="Entity not found")


@router.get("/entities/by_type/{entity_type}")
async def get_entities_by_type(
    entity_type: str,
    limit: int = Query(default=100, le=1000),
    client: Neo4jClient = Depends(get_neo4j_client)
):
    """按类型获取实体列表"""
    entities = client.get_entities_by_type(entity_type, limit=limit)
    return {"entities": entities, "total": len(entities)}


@router.delete("/entities/{entity_id}")
async def delete_entity(
    entity_id: str,
    client: Neo4jClient = Depends(get_neo4j_client)
):
    """删除实体"""
    success = client.delete_entity(entity_id)
    return {"status": "deleted" if success else "failed"}


# ============ Relation Operations ============

@router.post("/relations")
async def create_relation(
    relation: RelationCreate,
    client: Neo4jClient = Depends(get_neo4j_client)
):
    """创建关系"""
    from ..schema.academic_kg_schema import Relation, RelationType

    relation_obj = Relation(
        source=relation.source,
        target=relation.target,
        type=RelationType(relation.type) if relation.type in [r.value for r in RelationType] else RelationType.CITES,
        properties=relation.properties or {}
    )

    success = client.insert_relation(relation_obj)

    return {
        "source": relation.source,
        "target": relation.target,
        "status": "created" if success else "failed"
    }


@router.get("/relations/{entity_id}")
async def get_relations(
    entity_id: str,
    client: Neo4jClient = Depends(get_neo4j_client)
):
    """获取实体的关系"""
    relations = client.get_relations(entity_id)
    return {"relations": relations}


# ============ Graph Operations ============

@router.post("/subgraph")
async def query_subgraph(
    request: SubgraphQueryRequest,
    client: Neo4jClient = Depends(get_neo4j_client)
):
    """查询子图"""
    subgraph = client.query_subgraph(
        center_id=request.center_id,
        depth=request.depth or 2
    )
    return {
        "nodes": subgraph.nodes,
        "edges": subgraph.edges,
        "center_id": subgraph.center_id
    }


@router.post("/query")
async def query_graph(
    request: QueryRequest,
    retriever: SubgraphRetriever = Depends(get_subgraph_retriever),
    reasoner: KGReasoner = Depends(get_kg_reasoner),
    generator: GraphRAGAnswerGenerator = Depends(get_answer_generator)
):
    """查询图谱（GraphRAG）"""
    from ..graphrag.subgraph_retriever import CommunitySummary

    # 检索相关社区
    communities = retriever.retrieve(request.query, top_k=request.top_k or 5)

    # 推理
    reasoning_result = reasoner.reason(
        query=request.query,
        community_summaries=communities,
        mode=ReasoningMode.CHAIN_OF_THOUGHT
    )

    # 生成答案
    answer = generator.generate(
        query=request.query,
        community_summaries=communities,
        subgraph=None,
        use_llm=False
    )

    return {
        "answer": answer.answer,
        "reasoning_steps": [
            {
                "step_id": s.step_id,
                "description": s.description,
                "conclusion": s.conclusion,
                "confidence": s.confidence
            }
            for s in reasoning_result.reasoning_steps
        ],
        "citations": answer.citations,
        "confidence": answer.confidence
    }


@router.get("/neighbors/{entity_id}")
async def get_neighbors(
    entity_id: str,
    depth: int = Query(default=1, le=3),
    client: Neo4jClient = Depends(get_neo4j_client)
):
    """获取邻居节点"""
    neighbors = client.get_neighbors(entity_id, depth=depth)
    return {"neighbors": neighbors}


@router.get("/path/{source_id}/{target_id}")
async def find_path(
    source_id: str,
    target_id: str,
    max_length: int = Query(default=5, le=10),
    client: Neo4jClient = Depends(get_neo4j_client)
):
    """查找最短路径"""
    path = client.find_path(source_id, target_id, max_length=max_length)
    return {"path": path}


# ============ Visualization ============

@router.get("/visualize/{center_id}")
async def visualize_subgraph(
    center_id: str,
    layout: str = Query(default="force", pattern="^(force|circular|hierarchical)$"),
    max_nodes: int = Query(default=100, le=500),
    client: Neo4jClient = Depends(get_neo4j_client)
):
    """获取子图可视化配置"""
    subgraph = client.query_subgraph(center_id=center_id, depth=2)

    config = VisualizationConfig(
        layout=layout,
        max_nodes=max_nodes
    )

    visualizer = KnowledgeGraphVisualizer(config)
    vis_data = visualizer.visualize(subgraph)

    return vis_data


@router.post("/visualize/export")
async def export_visualization(
    center_id: str,
    output_path: str,
    layout: str = Query(default="force", pattern="^(force|circular|hierarchical)$"),
    client: Neo4jClient = Depends(get_neo4j_client)
):
    """导出可视化HTML"""
    subgraph = client.query_subgraph(center_id=center_id, depth=2)

    config = VisualizationConfig(layout=layout)
    visualizer = KnowledgeGraphVisualizer(config)

    visualizer.export_to_html(subgraph, output_path)

    return {"status": "exported", "path": output_path}


# ============ Build Operations ============

@router.post("/build")
async def build_graph(
    request: BuildRequest,
    builder: AcademicGraphBuilder = Depends(get_graph_builder)
):
    """构建知识图谱"""
    try:
        if request.batch_mode:
            result = builder.build_from_directory(
                dir_path=request.file_paths[0] if request.file_paths else ".",
                file_pattern="*.pdf"
            )
        else:
            result = builder.build_from_documents(request.file_paths)

        return {
            "success": True,
            "entities_count": result.statistics.get("total_entities", 0),
            "relations_count": result.statistics.get("total_relations", 0),
            "message": "Build completed successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "entities_count": 0,
            "relations_count": 0,
            "message": str(e)
        }


@router.post("/build/batch")
async def build_graph_batch(
    dir_path: str,
    file_pattern: str = Query(default="*.pdf"),
    builder: AcademicGraphBuilder = Depends(get_graph_builder)
):
    """批量构建知识图谱"""
    try:
        result = builder.build_from_directory(dir_path, file_pattern)

        return {
            "success": True,
            "processed_files": result.statistics.get("processed_files", 0),
            "entities_count": result.statistics.get("total_entities", 0),
            "relations_count": result.statistics.get("total_relations", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Maintenance ============

@router.delete("/clear")
async def clear_graph(
    client: Neo4jClient = Depends(get_neo4j_client)
):
    """清空图谱"""
    success = client.clear_all()
    return {"status": "cleared" if success else "failed"}


@router.post("/export")
async def export_graph(
    output_path: str,
    builder: AcademicGraphBuilder = Depends(get_graph_builder)
):
    """导出图谱"""
    try:
        builder.save(output_path)
        return {"status": "exported", "path": output_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Helper Dependencies ============

def get_kg_reasoner() -> KGReasoner:
    """获取推理器"""
    return KGReasoner()


__all__ = ["router"]