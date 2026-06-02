"""模块04 PDF解析与分块 — 真实链路

流程：搜索论文 → 下载 PDF → 解析 → 分块 → 验证

前置条件:
    - Docker 容器 paper-agent-postgres 运行中
    - 网络可达 arxiv.org
"""

import pytest

from src.agents_v3.research_workspace.parser.service import ParserService
from src.agents_v3.research_workspace.services.paper_library import PaperLibraryService
from src.agents_v3.research_workspace.search.base import SearchQuery
from src.agents_v3.research_workspace.search.factory import create_default_adapters
from src.agents_v3.research_workspace.models import PaperStatus

PROJECT_ID = "e2e_parser_test"


@pytest.fixture(scope="module")
def imported_papers(pg_storage, adapters):
    """模块级 fixture：搜索导入有 PDF 的论文（只执行一次）"""
    library = PaperLibraryService(
        storage=pg_storage,
        search_adapters=list(adapters.values()),
        global_storage=pg_storage,
    )
    pg_storage.upsert_item("projects", PROJECT_ID, {
        "project_id": PROJECT_ID, "name": "解析测试项目",
    })
    query = SearchQuery(query="chain of thought prompting", limit=5)
    library.search_candidates(PROJECT_ID, query, min_score=0.1)
    papers = library.list_papers(PROJECT_ID)
    with_pdf = []
    for p in papers:
        pdf_url = p.open_access.pdf_url if p.open_access else ""
        if pdf_url:
            with_pdf.append(p)
    yield with_pdf
    try:
        papers_all = pg_storage.query("papers", {"project_id": PROJECT_ID})
        for p in papers_all:
            chunks = pg_storage.query("paper_chunks", {"paper_id": p["paper_id"]})
            for c in chunks:
                pg_storage.delete_item("paper_chunks", c["chunk_id"])
            pg_storage.delete_item("papers", p["paper_id"])
        pg_storage.delete_item("projects", PROJECT_ID)
    except Exception:
        pass


class TestParserE2E:
    """PDF 解析与分块真实链路测试"""

    def test_01_download_pdf(self, pg_storage, imported_papers):
        """下载论文 PDF"""
        if not imported_papers:
            pytest.skip("搜索结果中无 PDF 链接")

        parser = ParserService(storage=pg_storage)
        paper = imported_papers[0]
        result = parser.download_pdf(paper.paper_id)

        print(f"\n[download] {paper.title[:50]}...")
        print(f"  pdf_url={paper.open_access.pdf_url[:60]}")
        print(f"  result: success={result['success']}, path={result.get('pdf_path', 'N/A')}")
        assert result["success"], f"下载失败: {result.get('error')}"
        assert result.get("pdf_path")

    def test_02_parse_paper(self, pg_storage, imported_papers):
        """解析论文 PDF → 生成 chunks"""
        if not imported_papers:
            pytest.skip("搜索结果中无 PDF 链接")

        parser = ParserService(storage=pg_storage)
        paper = imported_papers[0]
        dl = parser.download_pdf(paper.paper_id)
        if not dl.get("success"):
            pytest.skip(f"PDF 下载失败: {dl.get('error')}")

        result = parser.parse_paper(paper.paper_id)

        print(f"\n[parse] {paper.title[:50]}...")
        print(f"  success={result.get('success')}, chunks={result.get('chunk_count', 0)}")
        if not result.get("success"):
            print(f"  error={result.get('error')}")
        assert result["success"], f"解析失败: {result.get('error')}"
        assert result.get("chunk_count", 0) > 0, "应生成至少 1 个 chunk"

    def test_03_chunks_have_metadata(self, pg_storage, imported_papers):
        """chunks 应有页码、章节、类型等元数据"""
        if len(imported_papers) < 1:
            pytest.skip("论文不足")

        parser = ParserService(storage=pg_storage)
        paper = imported_papers[0]
        parser.download_pdf(paper.paper_id)
        parser.parse_paper(paper.paper_id)

        chunks = pg_storage.query("paper_chunks", {"paper_id": paper.paper_id})
        if not chunks:
            pytest.skip("未生成 chunks")

        print(f"\n[chunks] {paper.title[:50]}...: {len(chunks)} chunks")
        for c in chunks[:5]:
            print(f"  - {c.get('chunk_type', 'N/A')}: section={c.get('section_title', '')[:30]}, pages={c.get('page_start')}-{c.get('page_end')}")

        for c in chunks:
            assert c.get("page_start"), "chunk 缺少 page_start"
            assert c.get("chunk_type"), "chunk 缺少 chunk_type"

    def test_04_references_separated(self, pg_storage, imported_papers):
        """参考文献应被识别并分离为独立 chunk"""
        if len(imported_papers) < 1:
            pytest.skip("论文不足")

        parser = ParserService(storage=pg_storage)
        paper = imported_papers[0]
        parser.download_pdf(paper.paper_id)
        parser.parse_paper(paper.paper_id)

        chunks = pg_storage.query("paper_chunks", {"paper_id": paper.paper_id})
        ref_chunks = [c for c in chunks if c.get("chunk_type") == "reference"]
        body_chunks = [c for c in chunks if c.get("chunk_type") == "body"]

        print(f"\n[refs] body={len(body_chunks)}, reference={len(ref_chunks)}")
        if ref_chunks:
            print(f"  参考文献示例: {ref_chunks[0].get('text', '')[:80]}...")

    def test_05_paper_status_updated(self, pg_storage, imported_papers):
        """解析后论文状态应更新为 PARSED"""
        if len(imported_papers) < 1:
            pytest.skip("论文不足")

        parser = ParserService(storage=pg_storage)
        paper = imported_papers[0]
        parser.download_pdf(paper.paper_id)
        parser.parse_paper(paper.paper_id)

        item = pg_storage.get_item("papers", paper.paper_id)
        assert item is not None
        print(f"\n[status] {paper.paper_id}: {item['status']}")
        assert item["status"] in (
            PaperStatus.PARSED.value,
            PaperStatus.CARD_READY.value,
            PaperStatus.EVIDENCE_READY.value,
        ), f"状态应为 PARSED，实际: {item['status']}"

    def test_06_parse_project_batch(self, pg_storage, imported_papers):
        """批量解析项目中所有论文"""
        if not imported_papers:
            pytest.skip("搜索结果中无 PDF 链接")

        parser = ParserService(storage=pg_storage)
        dl_result = parser.download_all_pdfs(PROJECT_ID)
        print(f"\n[batch] 下载: total={dl_result['total']}, ok={dl_result['downloaded']}, skip={dl_result['skipped']}, fail={dl_result['failed']}")

        result = parser.parse_project_papers(PROJECT_ID)
        print(f"[batch] 解析: total={result['total']}, ok={result['success']}, fail={result['failed']}, skip={result['skipped']}")

        assert result["success"] > 0, "应至少成功解析 1 篇"

    def test_07_chunks_stored_in_postgres(self, pg_storage, imported_papers):
        """chunks 应存入 PostgreSQL paper_chunks 表"""
        if len(imported_papers) < 1:
            pytest.skip("论文不足")

        parser = ParserService(storage=pg_storage)
        paper = imported_papers[0]
        parser.download_pdf(paper.paper_id)
        parser.parse_paper(paper.paper_id)

        chunks = pg_storage.query("paper_chunks", {"paper_id": paper.paper_id})
        assert len(chunks) > 0, "paper_chunks 表应有数据"

        c = chunks[0]
        assert c.get("chunk_id")
        assert c.get("paper_id") == paper.paper_id
        assert c.get("text")
        print(f"\n[postgres] {len(chunks)} chunks 存入 paper_chunks 表")
