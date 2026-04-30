"""
API模块 - API网关

包含:
- APIGateway: API网关
- APIRouter: 路由器
- paper_api: 论文相关API
- reports_api: 报告相关API
- knowledge_graph_api: 知识图谱API
"""
from .gateway import (
    APIGateway,
    APIRouter,
    APIEndpoint,
    APIRequest,
    APIResponse,
    create_gateway
)
from .paper_api import setup_paper_routes
from .reports_api import setup_reports_routes
from .knowledge_graph_api import setup_knowledge_graph_routes
from .workflow_api import register_routes as register_workflow_routes

__all__ = [
    "APIGateway",
    "APIRouter",
    "APIEndpoint",
    "APIRequest",
    "APIResponse",
    "create_gateway",
    "setup_paper_routes",
    "setup_reports_routes",
    "setup_knowledge_graph_routes",
    "register_workflow_routes",
]