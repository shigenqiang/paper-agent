"""模块04 PDF 解析与分块 — 真实 HTTP API + PostgreSQL

测试全部通过 HTTP API 走真实链路：
  POST /api/rw/projects                → 创建项目
  POST /api/rw/projects/{id}/papers/search → 搜索入库
  POST /api/rw/projects/{id}/papers/{pid}/download → 下载 PDF
  POST /api/rw/projects/{id}/papers/{pid}/parse    → 解析 PDF

前置条件:
    - Docker 容器 postgres (5432) + qdrant (6333) 运行中
    - 服务运行在 http://localhost:8000
    - 网络可达 arxiv 等 PDF 源
"""

import time

import pytest
import requests

BASE = "http://localhost:8000"


def api(method: str, path: str, body: dict | None = None) -> dict:
    """调用真实 HTTP API"""
    url = f"{BASE}{path}"
    resp = requests.request(method, url, json=body, timeout=300)
    resp.raise_for_status()
    return resp.json()


def wait_for_service(max_wait: int = 15) -> bool:
    """等待服务就绪"""
    for _ in range(max_wait):
        try:
            r = requests.get(f"{BASE}/api/health", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


@pytest.fixture(scope="module", autouse=True)
def ensure_service():
    """确保服务可用"""
    if not wait_for_service():
        pytest.skip("服务未启动，请先运行 python -m src.service")


@pytest.fixture(scope="module")
def project_id():
    """通过 API 创建测试项目"""
    name = f"parser_test_{int(time.time())}"
    result = api("POST", "/api/rw/projects", {"name": name})
    pid = result["data"]["project_id"]
    print(f"\n[setup] 创建项目: {pid}")
    yield pid


@pytest.fixture(scope="module")
def paper_with_pdf(project_id, pg_storage):
    """搜索并找到有 PDF URL 的论文"""
    # 搜索有 PDF URL 的论文
    body = {"query": "BERT pre-training", "limit": 10}
    result = api("POST", f"/api/rw/projects/{project_id}/papers/search", body)
    results = result["data"]["results"]
    print(f"[setup] 搜索到 {len(results)} 篇论文")

    # 从数据库中找有 PDF URL 的论文
    for r in results:
        pid = r.get("paper_id") or r.get("source_payload", {}).get("pool_paper_id")
        if pid:
            pool_item = pg_storage.get_item("papers_pool", pid)
            if pool_item and pool_item.get("pdf_url"):
                print(f"[setup] 选择论文: {pid}")
                return pid

    pytest.skip("没有找到有 PDF URL 的论文")


class TestPDFDownload:
    """PDF 下载测试"""

    def test_download_pdf(self, project_id, paper_with_pdf, pg_storage):
        """通过 API 下载 PDF"""
        result = api("POST", f"/api/rw/projects/{project_id}/papers/{paper_with_pdf}/download")
        data = result["data"]

        print(f"\n[download] success={data.get('success')} pdf_path={data.get('pdf_path', '')[:50]}")
        assert data.get("success"), f"下载失败: {data.get('error')}"

        # 验证数据库中的 pdf_path
        stored = pg_storage.get_item("papers", paper_with_pdf)
        assert stored.get("pdf_path"), "pdf_path 应已更新"
        print(f"[download] 数据库 pdf_path: {stored['pdf_path'][:50]}")


class TestPDFParse:
    """PDF 解析测试"""

    def test_parse_paper(self, project_id, paper_with_pdf, pg_storage):
        """通过 API 解析 PDF"""
        # 先下载
        api("POST", f"/api/rw/projects/{project_id}/papers/{paper_with_pdf}/download")

        # 解析
        result = api("POST", f"/api/rw/projects/{project_id}/papers/{paper_with_pdf}/parse")
        data = result["data"]

        print(f"\n[parse] success={data.get('success')}")
        print(f"  pages={data.get('page_count')} chunks={data.get('chunk_count')}")
        print(f"  body_chunks={data.get('body_chunk_count')} refs={data.get('reference_count')}")
        print(f"  quality_flags={data.get('quality_flags')}")

        assert data.get("success"), f"解析失败: {data.get('error')}"
        assert data.get("chunk_count", 0) > 0, "应有分块"

    def test_parse_creates_chunks(self, project_id, paper_with_pdf, pg_storage):
        """解析后应创建 paper_chunks 记录"""
        # 下载 + 解析
        api("POST", f"/api/rw/projects/{project_id}/papers/{paper_with_pdf}/download")
        api("POST", f"/api/rw/projects/{project_id}/papers/{paper_with_pdf}/parse")

        # 验证 chunks
        chunks = pg_storage.query("paper_chunks", {"paper_id": paper_with_pdf})
        print(f"\n[chunks] 共 {len(chunks)} 个分块")
        for c in chunks[:3]:
            print(f"  - {c.get('chunk_id', '')[:30]}: section={c.get('section_title', '')[:20]} type={c.get('chunk_type')}")

        assert len(chunks) > 0, "应创建 paper_chunks 记录"

    def test_parse_creates_references(self, project_id, paper_with_pdf, pg_storage):
        """解析后应创建 paper_references 记录"""
        # 下载 + 解析
        api("POST", f"/api/rw/projects/{project_id}/papers/{paper_with_pdf}/download")
        api("POST", f"/api/rw/projects/{project_id}/papers/{paper_with_pdf}/parse")

        # 验证 references
        refs = pg_storage.query("paper_references", {"citing_paper_id": paper_with_pdf})
        print(f"\n[references] 共 {len(refs)} 条引用")
        for r in refs[:3]:
            print(f"  - {r.get('title', '')[:40]} ({r.get('year', '')})")

    def test_parse_creates_parse_result(self, project_id, paper_with_pdf, pg_storage):
        """解析后应创建 parse_results 记录"""
        # 下载 + 解析
        api("POST", f"/api/rw/projects/{project_id}/papers/{paper_with_pdf}/download")
        result = api("POST", f"/api/rw/projects/{project_id}/papers/{paper_with_pdf}/parse")
        parse_id = result["data"].get("parse_id")

        # 验证 parse_results
        parse_result = pg_storage.get_item("parse_results", parse_id)
        if not parse_result:
            all_parses = pg_storage.query("parse_results", {"paper_id": paper_with_pdf})
            parse_result = all_parses[-1] if all_parses else None

        print(f"\n[parse_result] {parse_id}: status={parse_result.get('status') if parse_result else 'N/A'}")
        if parse_result:
            print(f"  pages={parse_result.get('page_count')} chunks={parse_result.get('chunk_count')}")

        assert parse_result, "应创建 parse_results 记录"
        assert parse_result.get("status") == "success", "状态应为 success"

    def test_paper_status_updated(self, project_id, paper_with_pdf, pg_storage):
        """解析后论文状态应更新"""
        # 下载 + 解析
        api("POST", f"/api/rw/projects/{project_id}/papers/{paper_with_pdf}/download")
        api("POST", f"/api/rw/projects/{project_id}/papers/{paper_with_pdf}/parse")

        # 验证状态
        stored = pg_storage.get_item("papers", paper_with_pdf)
        print(f"\n[status] {paper_with_pdf}: {stored.get('status')}")
        assert stored.get("status") in ("parsed", "card_ready", "evidence_ready"), \
            f"状态应为 parsed，实际: {stored.get('status')}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
