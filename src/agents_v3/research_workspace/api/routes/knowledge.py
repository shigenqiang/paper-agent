"""知识提取与图谱路由"""

from __future__ import annotations

import threading

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.agents_v3.research_workspace.api.deps import (
    get_card_generator,
    get_evidence_service,
    get_graph_extractor,
    get_graph_service,
    get_project_service,
    get_task_service,
)
from src.agents_v3.research_workspace.api.errors import NotFoundError
from src.agents_v3.research_workspace.api.models import ApiResponse

router = APIRouter(prefix="/api/rw/projects/{project_ref}", tags=["knowledge"])


def _resolve_project(project_ref: str):
    svc = get_project_service()
    project = svc.get_project(project_ref)
    if not project:
        raise NotFoundError("project", project_ref)
    return project


# ── 论文卡片 ──

@router.post("/cards")
def generate_cards(project_ref: str, only_missing: bool = True):
    project = _resolve_project(project_ref)
    svc = get_card_generator(project_ref)
    cards = svc.batch_generate(project.project_id, only_missing=only_missing)
    return ApiResponse(data=[c.model_dump() for c in cards])


# ── 证据表 ──

@router.post("/evidence/build")
def build_evidence(project_ref: str):
    project = _resolve_project(project_ref)
    task_svc = get_task_service()
    task = task_svc.create_task("evidence_build", project.project_id)

    def _bg():
        try:
            task_svc.update_task(task["task_id"], status="running", progress=0.3)
            svc = get_evidence_service(project_ref)
            records = svc.build_for_project(project.project_id)
            task_svc.update_task(
                task["task_id"], status="completed", progress=1.0,
                result={"count": len(records)},
            )
        except Exception as e:
            task_svc.update_task(task["task_id"], status="failed", error=str(e)[:500])

    threading.Thread(target=_bg, daemon=True).start()
    return JSONResponse(status_code=202, content={
        "data": {"task_id": task["task_id"], "status": "queued"},
    })


# ── 知识图谱 ──

@router.post("/kg/build")
def build_graph(project_ref: str, force: bool = False):
    project = _resolve_project(project_ref)
    task_svc = get_task_service()
    task = task_svc.create_task("graph_build", project.project_id, {"force": force})

    def _bg():
        try:
            task_svc.update_task(task["task_id"], status="running", progress=0.1)
            task_svc.add_event(task["task_id"], "stage", {"name": "building_graph"})
            svc = get_graph_service(project_ref)
            graph = svc.build_project_graph(project.project_id, force=force)
            task_svc.update_task(
                task["task_id"], status="completed", progress=1.0,
                result={"node_count": len(graph.nodes), "edge_count": len(graph.edges)},
            )
        except Exception as e:
            task_svc.update_task(task["task_id"], status="failed", error=str(e)[:500])

    threading.Thread(target=_bg, daemon=True).start()
    return JSONResponse(status_code=202, content={
        "data": {"task_id": task["task_id"], "status": "queued"},
    })


@router.post("/kg/rebuild")
def rebuild_graph(project_ref: str):
    """强制全量重建图谱"""
    project = _resolve_project(project_ref)
    task_svc = get_task_service()
    task = task_svc.create_task("graph_rebuild", project.project_id)

    def _bg():
        try:
            task_svc.update_task(task["task_id"], status="running", progress=0.1)
            task_svc.add_event(task["task_id"], "stage", {"name": "rebuilding_graph"})
            svc = get_graph_service(project_ref)
            graph = svc.build_project_graph(project.project_id, force=True)
            task_svc.update_task(
                task["task_id"], status="completed", progress=1.0,
                result={"node_count": len(graph.nodes), "edge_count": len(graph.edges)},
            )
        except Exception as e:
            task_svc.update_task(task["task_id"], status="failed", error=str(e)[:500])

    threading.Thread(target=_bg, daemon=True).start()
    return JSONResponse(status_code=202, content={
        "data": {"task_id": task["task_id"], "status": "queued"},
    })


@router.post("/kg/incremental-update")
def incremental_update(project_ref: str, paper_ids: list[str]):
    """增量更新：只处理新增论文"""
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    graph = svc.incremental_update(project.project_id, paper_ids)
    return ApiResponse(data={"node_count": len(graph.nodes), "edge_count": len(graph.edges)})


@router.post("/kg/extract")
def extract_entities(project_ref: str, only_missing: bool = True):
    """从所有已解析论文的 sections 中用 LLM 提取实体/关系"""
    project = _resolve_project(project_ref)
    task_svc = get_task_service()
    task = task_svc.create_task("entity_extraction", project.project_id, {
        "only_missing": only_missing,
    })

    def _bg():
        try:
            task_svc.update_task(task["task_id"], status="running", progress=0.1)
            extractor = get_graph_extractor(project_ref)
            results = extractor.extract_from_project(project.project_id, only_missing=only_missing)
            task_svc.update_task(
                task["task_id"], status="completed", progress=1.0,
                result=results,
            )
        except Exception as e:
            task_svc.update_task(task["task_id"], status="failed", error=str(e)[:500])

    threading.Thread(target=_bg, daemon=True).start()
    return JSONResponse(status_code=202, content={
        "data": {"task_id": task["task_id"], "status": "queued"},
    })


@router.get("/kg")
def get_graph(project_ref: str):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    graph = svc.get_graph(project.project_id)
    return ApiResponse(data={
        "nodes": [n.model_dump() for n in graph.nodes],
        "edges": [e.model_dump() for e in graph.edges],
    })


@router.get("/kg/stats")
def get_graph_stats(project_ref: str):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.get_stats(project.project_id))


@router.post("/kg/subgraph")
def get_subgraph(project_ref: str, node_ids: list[str], hops: int = 1):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.get_subgraph(project.project_id, node_ids, hops=hops))


@router.get("/kg/gaps")
def find_gaps(project_ref: str, min_confidence: float = 0.5):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.find_gaps(project.project_id, min_confidence=min_confidence))


@router.get("/kg/nodes/{node_id}")
def get_node_detail(project_ref: str, node_id: str):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    node = svc.get_node(project.project_id, node_id)
    if not node:
        raise NotFoundError("node", node_id)
    return ApiResponse(data=node.model_dump())


@router.get("/kg/nodes/{node_id}/neighbors")
def get_node_neighbors(project_ref: str, node_id: str, hops: int = 1):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.get_neighbors(project.project_id, node_id, hops))


@router.post("/kg/paths")
def find_paths(project_ref: str, source_id: str, target_id: str, max_hops: int = 3):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.find_paths(project.project_id, source_id, target_id, max_hops))


@router.post("/kg/search-nodes")
def search_nodes(project_ref: str, query: str, node_types: list[str] | None = None, top_k: int = 10):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.search_nodes(project.project_id, query, node_types, top_k))


@router.post("/kg/scope")
def resolve_scope(project_ref: str, graph_node_ids: list[str], hops: int = 1):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.resolve_graph_scope(project.project_id, graph_node_ids, hops=hops))


@router.post("/kg/context")
def build_context(project_ref: str, graph_node_ids: list[str], hops: int = 1, token_budget: int = 4000):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.build_graph_context(project.project_id, graph_node_ids, hops, token_budget))


@router.get("/kg/summary")
def get_graph_summary(project_ref: str):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.build_graph_summary(project.project_id))


@router.get("/kg/validate")
def validate_graph(project_ref: str):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.validate_graph_traceability(project.project_id))


@router.get("/kg/quality")
def get_quality_metrics(project_ref: str):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.compute_quality_metrics(project.project_id))


@router.get("/kg/downstream-value")
def get_downstream_value(project_ref: str):
    """下游模块对图谱的使用率指标"""
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.compute_downstream_value(project.project_id))


@router.get("/kg/export/json")
def export_graph_json(project_ref: str):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    graph = svc.get_graph(project.project_id)
    if not graph:
        return ApiResponse(data={})
    from datetime import datetime
    return ApiResponse(data={
        "project_id": project.project_id,
        "exported_at": datetime.now().isoformat(),
        "nodes": [n.model_dump() for n in graph.nodes],
        "edges": [e.model_dump() for e in graph.edges],
        "stats": svc.get_stats(project.project_id),
    })


@router.post("/kg/consensus")
def consensus_meter(project_ref: str, claim_node_ids: list[str] | None = None, min_confidence: float = 0.3):
    """多论文结论聚合（Consensus Meter）"""
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.build_consensus_meter(project.project_id, claim_node_ids, min_confidence))


@router.post("/kg/global-search")
def global_search(project_ref: str, question: str, max_communities: int = 10):
    """GraphRAG Global Search：Map-Reduce over community summaries"""
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.global_search(project.project_id, question, max_communities))


@router.post("/kg/merge-entities")
def merge_entities(project_ref: str, similarity_threshold: float = 0.85, edit_distance_threshold: int = 2):
    """实体消歧：合并相似实体"""
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.merge_similar_entities(project.project_id, similarity_threshold, edit_distance_threshold))


# ── 社区检测 ──

@router.post("/kg/communities")
def detect_communities(project_ref: str, resolution: float = 1.0):
    """社区检测（Leiden / Label Propagation）"""
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.detect_communities(project.project_id, resolution=resolution))


@router.post("/kg/communities/summaries")
def build_community_summaries(project_ref: str, token_budget: int = 500):
    """为社区生成 LLM 摘要"""
    project = _resolve_project(project_ref)
    task_svc = get_task_service()
    task = task_svc.create_task("community_summaries", project.project_id, {
        "token_budget": token_budget,
    })

    def _bg():
        try:
            task_svc.update_task(task["task_id"], status="running", progress=0.1)
            svc = get_graph_service(project_ref)
            result = svc.build_community_summaries(project.project_id, token_budget=token_budget)
            task_svc.update_task(task["task_id"], status="completed", progress=1.0, result=result)
        except Exception as e:
            task_svc.update_task(task["task_id"], status="failed", error=str(e)[:500])

    threading.Thread(target=_bg, daemon=True).start()
    return JSONResponse(status_code=202, content={
        "data": {"task_id": task["task_id"], "status": "queued"},
    })


# ── 增强 Gap 检测 ──

@router.get("/kg/gaps/enhanced")
def find_research_gaps_enhanced(project_ref: str):
    """增强的 Gap 检测：future_work/possible_gaps/Method-Dataset矩阵/稀疏区域"""
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    return ApiResponse(data=svc.find_research_gaps_enhanced(project.project_id))
