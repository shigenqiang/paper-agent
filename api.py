"""论文Agent API服务"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import uuid
import json
import time
from datetime import datetime
from src.workflows.paper_workflow import PaperWorkflow
from src.core.state_model import State, paperagentstate, SearchAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Paper Agent API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

paper_workflow = PaperWorkflow()

# ─── In-memory task store (replace with Redis/DB in production) ───────────────
_tasks: Dict[str, Dict[str, Any]] = {}
_task_queues: Dict[str, asyncio.Queue] = {}


# ─── Models ───────────────────────────────────────────────────────────────────

class StartRequest(BaseModel):
    query: str

class ChatRequest(BaseModel):
    message: str
    task_id: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

def _emit(task_id: str, event_type: str, agent: str, message: str, data: Any = None):
    q = _task_queues.get(task_id)
    if q:
        payload = {
            "type": event_type,
            "agent": agent,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        q.put_nowait(payload)
        # mirror into task store
        _tasks[task_id]["events"].append(payload)
        if event_type == "paper_found" and data:
            _tasks[task_id]["papers"].append(data)
        if event_type == "writing_update" and isinstance(data, dict) and "report" in data:
            _tasks[task_id]["report"] = data["report"]
        if event_type == "done":
            _tasks[task_id]["status"] = "done"
        if event_type == "error":
            _tasks[task_id]["status"] = "error"
            _tasks[task_id]["error"] = message


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Paper Agent API v2", "version": "2.0.0"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}


@app.post("/api/research/start")
async def start_research(req: StartRequest):
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {
        "task_id": task_id,
        "query": req.query,
        "status": "planning",
        "created_at": datetime.utcnow().isoformat(),
        "papers": [],
        "report": None,
        "error": None,
        "events": [],
    }
    _task_queues[task_id] = asyncio.Queue()

    # run workflow in background
    asyncio.create_task(_run_workflow(task_id, req.query))
    return {"task_id": task_id}


@app.get("/api/research/stream/{task_id}")
async def stream_research(task_id: str):
    if task_id not in _tasks:
        raise HTTPException(404, "Task not found")

    async def generator():
        q = _task_queues.get(task_id)
        if not q:
            return
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30)
                yield _sse("agent_event", event)
                if event["type"] in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/research/{task_id}")
async def get_task(task_id: str):
    if task_id not in _tasks:
        raise HTTPException(404, "Task not found")
    return _tasks[task_id]


@app.get("/api/research")
async def list_tasks():
    return list(_tasks.values())


@app.get("/api/papers")
async def list_papers(query: Optional[str] = None, page: int = 1):
    all_papers = []
    seen = set()
    for t in _tasks.values():
        for p in t.get("papers", []):
            pid = p.get("id")
            if pid and pid not in seen:
                seen.add(pid)
                all_papers.append(p)
    if query:
        q = query.lower()
        all_papers = [p for p in all_papers if q in p.get("title", "").lower()]
    return {"papers": all_papers, "total": len(all_papers)}


@app.get("/api/papers/{paper_id}")
async def get_paper(paper_id: str):
    for t in _tasks.values():
        for p in t.get("papers", []):
            if p.get("id") == paper_id:
                return p
    raise HTTPException(404, "Paper not found")


@app.get("/api/reports")
async def list_reports():
    reports = []
    for t in _tasks.values():
        if t.get("report"):
            reports.append({
                "id": t["task_id"],
                "task_id": t["task_id"],
                "query": t["query"],
                "content": t["report"],
                "created_at": t["created_at"],
                "paper_count": len(t.get("papers", [])),
            })
    return reports


@app.get("/api/reports/{report_id}")
async def get_report(report_id: str):
    t = _tasks.get(report_id)
    if not t or not t.get("report"):
        raise HTTPException(404, "Report not found")
    return {
        "id": t["task_id"],
        "task_id": t["task_id"],
        "query": t["query"],
        "content": t["report"],
        "created_at": t["created_at"],
        "paper_count": len(t.get("papers", [])),
    }


@app.get("/api/knowledge-graph")
async def get_knowledge_graph(task_id: Optional[str] = None):
    # placeholder — wire to ConceptGraph in production
    return {"nodes": [], "edges": []}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    # placeholder — wire to RAG retriever in production
    return {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": f"（RAG 对话功能开发中，你的问题：{req.message}）",
        "timestamp": datetime.utcnow().isoformat(),
        "sources": [],
    }


# ─── Workflow runner ───────────────────────────────────────────────────────────

async def _run_workflow(task_id: str, query: str):
    try:
        _emit(task_id, "status", "coordinator", "开始规划研究方案", {"status": "planning"})

        initial_state = State(
            value=paperagentstate(
                current_step="initializing",
                search_state=SearchAgent(query=query)
            )
        )
        config = {"configurable": {"thread_id": task_id}}

        result = await paper_workflow.run(initial_state, config)

        val = result["value"]
        if val.error and val.error.error:
            _emit(task_id, "error", "coordinator", val.error.error)
            return

        if val.report_markdown:
            _emit(task_id, "writing_update", "writer", "报告生成完毕", {"report": val.report_markdown})

        _emit(task_id, "done", "coordinator", "研究完成")

    except Exception as e:
        logger.exception("Workflow failed")
        _emit(task_id, "error", "coordinator", str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
