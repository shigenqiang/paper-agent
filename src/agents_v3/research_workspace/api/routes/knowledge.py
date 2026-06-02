"""知识提取与图谱路由"""

from __future__ import annotations

from fastapi import APIRouter

from src.agents_v3.research_workspace.api.deps import (
    get_card_generator,
    get_evidence_service,
    get_graph_service,
    get_project_service,
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
    svc = get_evidence_service(project_ref)
    records = svc.build_for_project(project.project_id)
    return ApiResponse(data=[e.model_dump() for e in records])


# ── 知识图谱 ──

@router.post("/kg/build")
def build_graph(project_ref: str):
    project = _resolve_project(project_ref)
    svc = get_graph_service(project_ref)
    graph = svc.build_project_graph(project.project_id)
    return ApiResponse(data={"node_count": len(graph.nodes), "edge_count": len(graph.edges)})


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
