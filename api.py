"""论文Agent API服务"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import uuid
from src.workflows.paper_workflow import PaperWorkflow
from src.core.state_model import State, paperagentstate, SearchAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Paper Agent API", version="1.0.0")

# 初始化工作流
paper_workflow = PaperWorkflow()


class QueryRequest(BaseModel):
    """查询请求"""
    query: str
    max_results: Optional[int] = 20
    year_range: Optional[tuple] = (2020, 2025)


class QueryResponse(BaseModel):
    """查询响应"""
    status: str
    message: str
    report_markdown: Optional[str] = None
    papers_count: Optional[int] = None


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Paper Agent API",
        "version": "1.0.0",
        "endpoints": {
            "/query": "POST - 执行论文调研查询",
            "/health": "GET - 健康检查"
        }
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


@app.post("/query", response_model=QueryResponse)
async def query_papers(request: QueryRequest):
    """执行论文调研查询"""
    try:
        logger.info(f"Received query: {request.query}")

        # 创建初始状态
        initial_state = State(
            value=paperagentstate(
                current_step="initializing",
                search_state=SearchAgent(query=request.query)
            )
        )

        # 运行工作流
        config_dict = {
            "configurable": {
                "thread_id": str(uuid.uuid4())
            }
        }

        result = await paper_workflow.run(initial_state, config_dict)

        # 返回结果
        if result["value"].error.error:
            return QueryResponse(
                status="error",
                message=result["value"].error.error
            )

        papers_count = len(result["value"].search_state.papers) if result["value"].search_state else 0

        return QueryResponse(
            status="success",
            message="Query completed successfully",
            report_markdown=result["value"].report_markdown,
            papers_count=papers_count
        )

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
