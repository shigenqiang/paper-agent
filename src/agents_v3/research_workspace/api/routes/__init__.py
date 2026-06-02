"""路由注册"""

from fastapi import FastAPI

from src.agents_v3.research_workspace.api.routes.knowledge import router as knowledge_router
from src.agents_v3.research_workspace.api.routes.papers import router as papers_router
from src.agents_v3.research_workspace.api.routes.parsing import router as parsing_router
from src.agents_v3.research_workspace.api.routes.projects import router as projects_router
from src.agents_v3.research_workspace.api.routes.reports import router as reports_router
from src.agents_v3.research_workspace.api.routes.scope_qa import router as scope_qa_router
from src.agents_v3.research_workspace.api.routes.tasks import router as tasks_router


def register_routers(app: FastAPI) -> None:
    """注册所有路由到 app"""
    app.include_router(projects_router)
    app.include_router(papers_router)
    app.include_router(parsing_router)
    app.include_router(knowledge_router)
    app.include_router(scope_qa_router)
    app.include_router(reports_router)
    app.include_router(tasks_router)
