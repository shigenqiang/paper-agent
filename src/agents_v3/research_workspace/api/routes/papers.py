"""论文库路由"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, File, UploadFile

from src.agents_v3.research_workspace.api.deps import get_paper_library, get_parser_service, get_project_service
from src.agents_v3.research_workspace.api import deps as _deps
from src.agents_v3.research_workspace.api.errors import NotFoundError, ValidationError
from src.agents_v3.research_workspace.api.models import (
    ApiListResponse,
    ApiResponse,
    PageInfo,
    PaperImportBibtexRequest,
    PaperImportDoiRequest,
    PaperUpdateRequest,
    SearchPapersRequest,
)
from src.agents_v3.research_workspace.search.base import SearchQuery

router = APIRouter(prefix="/api/rw/projects/{project_ref}/papers", tags=["papers"])


def _resolve_project(project_ref: str):
    svc = get_project_service()
    project = svc.get_project(project_ref)
    if not project:
        raise NotFoundError("project", project_ref)
    return project


@router.get("")
def list_papers(
    project_ref: str,
    status: str | None = None,
    included: bool | None = None,
    page: int = 1,
    page_size: int = 20,
):
    project = _resolve_project(project_ref)
    svc = get_paper_library(project_ref)
    filters = {}
    if status:
        filters["status"] = status
    if included is not None:
        filters["included"] = included
    papers = svc.list_papers(project.project_id, filters or None)
    items = [p.model_dump() for p in papers]
    total = len(items)
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    start = (page - 1) * page_size
    paged = items[start : start + page_size]
    resp = ApiListResponse(
        data=paged,
        pagination=PageInfo(page=page, page_size=page_size, total=total, has_next=start + page_size < total),
    )
    return resp


@router.post("/import/doi")
def import_doi(project_ref: str, req: PaperImportDoiRequest):
    project = _resolve_project(project_ref)
    svc = get_paper_library(project_ref)
    papers = svc.import_doi_list(project.project_id, req.dois)
    return ApiResponse(data=[p.model_dump() for p in papers])


@router.post("/import/bibtex")
def import_bibtex(project_ref: str, req: PaperImportBibtexRequest):
    project = _resolve_project(project_ref)
    svc = get_paper_library(project_ref)
    papers = svc.import_bibtex(project.project_id, req.bibtex)
    return ApiResponse(data=[p.model_dump() for p in papers])


@router.get("/{paper_id}")
def get_paper(project_ref: str, paper_id: str):
    svc = get_paper_library(project_ref)
    paper = svc.get_paper(paper_id)
    if not paper:
        raise NotFoundError("paper", paper_id)
    return ApiResponse(data=paper.model_dump())


@router.patch("/{paper_id}")
def update_paper(project_ref: str, paper_id: str, req: PaperUpdateRequest):
    svc = get_paper_library(project_ref)
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    paper = svc.update_paper(paper_id, **updates)
    if not paper:
        raise NotFoundError("paper", paper_id)
    return ApiResponse(data=paper.model_dump())


@router.post("/{paper_id}/include")
def include_paper(project_ref: str, paper_id: str):
    svc = get_paper_library(project_ref)
    paper = svc.mark_included(paper_id)
    if not paper:
        raise NotFoundError("paper", paper_id)
    return ApiResponse(data=paper.model_dump())


@router.post("/{paper_id}/exclude")
def exclude_paper(project_ref: str, paper_id: str, reason: str = ""):
    svc = get_paper_library(project_ref)
    paper = svc.mark_excluded(paper_id, reason)
    if not paper:
        raise NotFoundError("paper", paper_id)
    return ApiResponse(data=paper.model_dump())


@router.post("/search")
def search_papers(project_ref: str, req: SearchPapersRequest):
    project = _resolve_project(project_ref)
    svc = get_paper_library(project_ref)
    query = SearchQuery(
        query=req.query, sources=req.sources, limit=req.limit,
        offset=req.offset,
        year_from=req.year_from, year_to=req.year_to,
        field=req.field,
        use_cache=req.use_cache, force_refresh=req.force_refresh,
    )
    response = svc.search_candidates(project.project_id, query)
    return ApiResponse(data={
        "query": response.query.query if hasattr(response.query, 'query') else str(response.query),
        "results": [r.model_dump(exclude_defaults=True) for r in response.results],
        "result_count": response.total_count,
    })


@router.post("/upload")
async def upload_pdf(
    project_ref: str,
    file: UploadFile = File(...),
    auto_parse: bool = False,
):
    """上传本地 PDF 文件到项目"""
    project = _resolve_project(project_ref)

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise ValidationError("Only PDF files are accepted")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise ValidationError("File too large (max 50MB)")

    paper_id = f"paper_{uuid.uuid4().hex[:12]}"
    storage = _deps.get_storage()

    # 保存到项目文件目录
    from pathlib import Path
    data_dir = Path(getattr(storage, "data_dir", Path("data")))
    dest_dir = data_dir / "files" / project.project_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{paper_id}.pdf"
    dest_path.write_bytes(content)

    paper_data = {
        "paper_id": paper_id,
        "project_id": project.project_id,
        "title": (file.filename or "uploaded").replace(".pdf", ""),
        "status": "imported",
        "pdf_path": str(dest_path),
        "source": "upload",
    }
    storage.upsert_item("papers", paper_id, paper_data)

    result: dict = {"paper": paper_data}
    if auto_parse:
        try:
            svc = get_parser_service(project_ref)
            parse_result = svc.parse_paper(paper_id)
            result["parse_result"] = parse_result
        except Exception as e:
            result["parse_error"] = str(e)[:200]

    return ApiResponse(data=result)


@router.post("/upload/batch")
async def upload_papers_batch(
    project_ref: str,
    files: list[UploadFile] = File(...),
    auto_parse: bool = False,
):
    """批量上传 PDF 文件"""
    project = _resolve_project(project_ref)
    storage = _deps.get_storage()
    from pathlib import Path
    data_dir = Path(getattr(storage, "data_dir", Path("data")))
    dest_dir = data_dir / "files" / project.project_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    imported = 0
    failed = 0
    results = []
    errors = []

    for file in files:
        filename = file.filename or "unknown.pdf"
        try:
            if not filename.lower().endswith(".pdf"):
                raise ValidationError(f"Not a PDF: {filename}")

            content = await file.read()
            if len(content) > 50 * 1024 * 1024:
                raise ValidationError(f"File too large (max 50MB): {filename}")

            paper_id = f"paper_{uuid.uuid4().hex[:12]}"
            dest_path = dest_dir / f"{paper_id}.pdf"
            dest_path.write_bytes(content)

            paper_data = {
                "paper_id": paper_id,
                "project_id": project.project_id,
                "title": filename.replace(".pdf", ""),
                "status": "imported",
                "pdf_path": str(dest_path),
                "source": "upload",
            }
            storage.upsert_item("papers", paper_id, paper_data)

            result_item: dict = {"paper_id": paper_id, "filename": filename}
            if auto_parse:
                try:
                    svc = get_parser_service(project_ref)
                    parse_result = svc.parse_paper(paper_id)
                    result_item["parse_result"] = parse_result
                except Exception as e:
                    result_item["parse_error"] = str(e)[:200]

            results.append(result_item)
            imported += 1
        except Exception as e:
            errors.append({"filename": filename, "error": str(e)[:200]})
            failed += 1

    return ApiResponse(data={
        "imported": imported,
        "failed": failed,
        "results": results,
        "errors": errors,
    })
