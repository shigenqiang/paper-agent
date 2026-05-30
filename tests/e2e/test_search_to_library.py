"""端到端测试：创建项目 → 搜索论文 → 确认入库 → 删除项目

运行方式（需先启动服务）:
    python -m tests.e2e.test_search_to_library
    # 或
    python tests/e2e/test_search_to_library.py

可选参数:
    --query "your search query"   自定义搜索词（默认: sparse functional data）
    --limit 10                    搜索数量（默认: 10）
    --sources openalex,arxiv      搜索源（默认: openalex,arxiv,semantic_scholar）
    --no-cleanup                  测试后不删除项目
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8000"


# ── 工具函数 ──────────────────────────────────────────

def api(method: str, path: str, body: dict | None = None) -> dict:
    """调用 API，返回 JSON 响应"""
    url = f"{BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP {e.code}: {err_body[:200]}")
        raise


def wait_for_service(max_wait: int = 15) -> bool:
    """等待服务就绪"""
    for _ in range(max_wait):
        try:
            req = urllib.request.Request(f"{BASE}/api/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


# ── 测试步骤 ──────────────────────────────────────────

def step_create_project(name: str) -> str:
    """步骤 1: 创建项目，返回 project_id"""
    print(f"\n[1/4] 创建项目: {name}")
    result = api("POST", "/api/rw/projects", {"name": name})
    project_id = result["data"]["project_id"]
    print(f"  -> project_id: {project_id}")
    return project_id


def step_search_papers(
    project_id: str,
    query: str,
    sources: list[str],
    limit: int,
) -> tuple[str, list[str]]:
    """步骤 2: 搜索论文，返回 (session_id, result_ids)"""
    print(f"\n[2/4] 搜索论文: \"{query}\"")
    print(f"  sources={sources}, limit={limit}")

    body = {
        "query": query,
        "sources": sources,
        "limit": limit,
    }
    result = api("POST", f"/api/rw/projects/{project_id}/papers/search", body)
    data = result["data"]

    session_id = data["session_id"]
    results = data["results"]
    result_ids = [r["result_id"] for r in results]

    print(f"  -> session_id: {session_id}")
    print(f"  -> 找到 {len(results)} 篇论文:")
    for i, r in enumerate(results[:10]):
        title = r.get("title", "")[:55]
        year = r.get("year", "?")
        score = r.get("final_score", 0)
        pdf = "PDF" if r.get("pdf_url") else "no-pdf"
        print(f"     {i+1:2d}. [{score:.3f}] {title} ({year}) [{pdf}]")
    if len(results) > 10:
        print(f"     ... 共 {len(results)} 篇")

    return session_id, result_ids


def step_commit(project_id: str, session_id: str, result_ids: list[str]) -> list[dict]:
    """步骤 3: 确认入库，返回已入库论文列表"""
    print(f"\n[3/4] 确认入库 ({len(result_ids)} 篇)...")

    body = {
        "session_id": session_id,
        "selected_result_ids": result_ids,
    }
    result = api("POST", f"/api/rw/projects/{project_id}/papers/search/commit", body)
    papers = result["data"]

    print(f"  -> 成功入库 {len(papers)} 篇:")
    for p in papers:
        pid = p.get("paper_id", "?")
        title = p.get("title", "")[:50]
        print(f"     {pid}: {title}")

    return papers


def step_delete_project(project_id: str) -> bool:
    """步骤 4: 删除项目，清理所有数据"""
    print(f"\n[4/4] 删除项目: {project_id}")

    try:
        result = api("DELETE", f"/api/rw/projects/{project_id}")
        data = result.get("data", {})
        papers_cleaned = data.get("papers_cleaned", 0)
        print(f"  -> 删除成功，清理了 {papers_cleaned} 篇论文的向量数据")
        return True
    except Exception as e:
        print(f"  -> 删除失败: {e}")
        return False


def verify_project_papers(project_id: str, expected_min: int) -> bool:
    """验证项目中已有论文"""
    result = api("GET", f"/api/rw/projects/{project_id}/papers")
    papers = result["data"]
    has_pdf = sum(1 for p in papers if p.get("open_access", {}).get("pdf_url"))
    has_abs = sum(1 for p in papers if p.get("abstract"))

    print(f"\n项目论文统计:")
    print(f"  总数:     {len(papers)}")
    print(f"  有 PDF:   {has_pdf}")
    print(f"  有摘要:   {has_abs}")

    ok = len(papers) >= expected_min
    print(f"  验证:     {'PASS' if ok else 'FAIL'} (期望 >= {expected_min})")
    return ok


def verify_project_deleted(project_id: str) -> bool:
    """验证项目已被删除"""
    try:
        api("GET", f"/api/rw/projects/{project_id}")
        print(f"  验证:     FAIL (项目仍存在)")
        return False
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  验证:     PASS (项目已删除)")
            return True
        raise


# ── 主流程 ──────────────────────────────────────────

def run(
    query: str = "sparse functional data",
    limit: int = 10,
    sources: list[str] | None = None,
    project_name: str = "",
    cleanup: bool = True,
) -> bool:
    """运行完整流程：创建项目 → 搜索 → 入库 → 验证 → 删除"""
    if sources is None:
        sources = ["openalex", "arxiv", "semantic_scholar"]
    if not project_name:
        project_name = f"e2e_test_{int(time.time())}"

    print("=" * 60)
    print("端到端测试: 创建项目 → 搜索论文 → 确认入库 → 删除项目")
    print("=" * 60)

    # 等待服务
    if not wait_for_service():
        print("ERROR: 服务未启动，请先运行 python -m src.service")
        return False
    print(f"服务就绪: {BASE}")

    try:
        # 步骤 1: 创建项目
        project_id = step_create_project(project_name)

        # 步骤 2: 搜索论文
        session_id, result_ids = step_search_papers(project_id, query, sources, limit)

        if not result_ids:
            print("\nERROR: 搜索结果为空")
            return False

        # 步骤 3: 确认入库
        papers = step_commit(project_id, session_id, result_ids)

        if not papers:
            print("\nERROR: 入库失败（可能全部重复）")
            return False

        # 验证入库
        ok = verify_project_papers(project_id, expected_min=1)

        # 步骤 4: 删除项目
        if cleanup:
            deleted = step_delete_project(project_id)
            if deleted:
                verify_project_deleted(project_id)
            ok = ok and deleted
        else:
            print(f"\n[4/4] 跳过删除（--no-cleanup）")
            print(f"  项目 ID: {project_id}")

        print("\n" + "=" * 60)
        print(f"测试{'通过' if ok else '失败'}!")
        print("=" * 60)
        return ok

    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


# ── 入口 ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="端到端测试: 创建项目 → 搜索论文 → 入库 → 删除")
    parser.add_argument("--query", default="sparse functional data", help="搜索关键词")
    parser.add_argument("--limit", type=int, default=10, help="搜索数量")
    parser.add_argument("--sources", default="openalex,arxiv,semantic_scholar", help="搜索源，逗号分隔")
    parser.add_argument("--name", default="", help="项目名称（默认自动生成）")
    parser.add_argument("--no-cleanup", action="store_true", help="测试后不删除项目")
    args = parser.parse_args()

    sources = [s.strip() for s in args.sources.split(",")]
    ok = run(
        query=args.query,
        limit=args.limit,
        sources=sources,
        project_name=args.name,
        cleanup=not args.no_cleanup,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
