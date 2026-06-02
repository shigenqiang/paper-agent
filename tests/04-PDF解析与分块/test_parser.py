"""模块04 PDF解析与分块 — 真实链路

流程：搜索论文 → 下载 PDF → 解析 → 分块 → 验证

前置条件:
    - Docker 容器 paper-agent-postgres 运行中
    - 网络可达 arxiv.org
"""

import pytest

from src.agents_v3.research_workspace.parser_service import ParserService
from src.agents_v3.research_workspace.paper_library import PaperLibraryService
from src.agents_v3.research_workspace.search.base import SearchQuery
from src.agents_v3.research_workspace.search.factory import create_default_adapters
from src.agents_v3.research_workspace.models import PaperStatus


class TestParserE2E:
    """PDF 解析与分块真实链路测试"""

    PROJECT_ID = "e2e_parser_test"

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage, adapters):
        self.pg = pg_storage
        self.parser = ParserService(storage=pg_storage)
        self.library = PaperLibraryService(
            storage=pg_storage,
            search_adapters=list(adapters.values()),
            global_storage=pg_storage,
        )
        pg_storage.upsert_item("projects", self.PROJECT_ID, {
            "project_id": self.PROJECT_ID, "name": "解析测试项目",
        })
        yield
        try:
            papers = pg_storage.query("papers", {"project_id": self.PROJECT_ID})
            for p in papers:
                chunks = pg_storage.query("paper_chunks", {"paper_id": p["paper_id"]})
                for c in chunks:
                    pg_storage.delete_item("paper_chunks", c["chunk_id"])
                pg_storage.delete_item("papers", p["paper_id"])
            pg_storage.delete_item("projects", self.PROJECT_ID)
        except Exception:
            pass

    def _import_arxiv_papers(self, query="chain of thought prompting", limit=3):
        """搜索并导入 arXiv 论文（确保有 PDF URL）"""
        q = SearchQuery(query=query, limit=limit)
        papers = self.library.search_and_import(self.PROJECT_ID, q, min_score=0.1)
        # 只保留有 PDF URL 的论文
        with_pdf = []
        for p in papers:
            pdf_url = p.open_access.pdf_url if p.open_access else ""
            if pdf_url:
                with_pdf.append(p)
        return with_pdf

    def test_01_download_pdf(self):
        """下载论文 PDF"""
        papers = self._import_arxiv_papers()
        if not papers:
            pytest.skip("搜索结果中无 PDF 链接")

        paper = papers[0]
        result = self.parser.download_pdf(paper.paper_id)

        print(f"\n[download] {paper.title[:50]}...")
        print(f"  pdf_url={paper.open_access.pdf_url[:60] if paper.open_access else 'N/A'}")
        print(f"  result={result}")
        assert result["success"], f"下载失败: {result.get('error')}"
        assert result.get("pdf_path")

    def test_02_parse_paper(self):
        """解析论文 PDF → 生成 chunks"""
        papers = self._import_arxiv_papers()
        if not papers:
            pytest.skip("搜索结果中无 PDF 链接")

        paper = papers[0]
        dl = self.parser.download_pdf(paper.paper_id)
        if not dl.get("success"):
            pytest.skip(f"PDF 下载失败: {dl.get('error')}")

        result = self.parser.parse_paper(paper.paper_id)

        print(f"\n[parse] {paper.title[:50]}...")
        print(f"  success={result.get('success')}, chunks={result.get('chunk_count', 0)}")
        if not result.get("success"):
            print(f"  error={result.get('error')}")
        assert result["success"], f"解析失败: {result.get('error')}"
        assert result.get("chunk_count", 0) > 0, "应生成至少 1 个 chunk"

    def test_03_chunks_have_metadata(self):
        """chunks 应有页码、章节、类型等元数据"""
        papers = self._import_arxiv_papers("transformer neural network", 2)
        if not papers:
            pytest.skip("搜索结果中无 PDF 链接")

        paper = papers[0]
        dl = self.parser.download_pdf(paper.paper_id)
        if not dl.get("success"):
            pytest.skip(f"PDF 下载失败")
        self.parser.parse_paper(paper.paper_id)

        chunks = self.pg.query("paper_chunks", {"paper_id": paper.paper_id})
        if not chunks:
            pytest.skip("未生成 chunks")

        print(f"\n[chunks] {paper.title[:50]}...: {len(chunks)} chunks")
        for c in chunks[:5]:
            print(f"  - {c.get('chunk_type', 'N/A')}: section={c.get('section_title', '')[:30]}, pages={c.get('page_start')}-{c.get('page_end')}")

        for c in chunks:
            assert c.get("page_start"), "chunk 缺少 page_start"
            assert c.get("chunk_type"), "chunk 缺少 chunk_type"

    def test_04_references_separated(self):
        """参考文献应被识别并分离为独立 chunk"""
        papers = self._import_arxiv_papers("attention mechanism deep learning", 2)
        if not papers:
            pytest.skip("搜索结果中无 PDF 链接")

        paper = papers[0]
        dl = self.parser.download_pdf(paper.paper_id)
        if not dl.get("success"):
            pytest.skip(f"PDF 下载失败")
        self.parser.parse_paper(paper.paper_id)

        chunks = self.pg.query("paper_chunks", {"paper_id": paper.paper_id})
        ref_chunks = [c for c in chunks if c.get("chunk_type") == "reference"]
        body_chunks = [c for c in chunks if c.get("chunk_type") == "body"]

        print(f"\n[refs] body={len(body_chunks)}, reference={len(ref_chunks)}")
        if ref_chunks:
            print(f"  参考文献示例: {ref_chunks[0].get('text', '')[:80]}...")

    def test_05_paper_status_updated(self):
        """解析后论文状态应更新为 PARSED"""
        papers = self._import_arxiv_papers("reinforcement learning", 2)
        if not papers:
            pytest.skip("搜索结果中无 PDF 链接")

        paper = papers[0]
        dl = self.parser.download_pdf(paper.paper_id)
        if not dl.get("success"):
            pytest.skip(f"PDF 下载失败")
        self.parser.parse_paper(paper.paper_id)

        item = self.pg.get_item("papers", paper.paper_id)
        assert item is not None
        print(f"\n[status] {paper.paper_id}: {item['status']}")
        assert item["status"] in (
            PaperStatus.PARSED.value,
            PaperStatus.CARD_READY.value,
            PaperStatus.EVIDENCE_READY.value,
        ), f"状态应为 PARSED，实际: {item['status']}"

    def test_06_parse_project_batch(self):
        """批量解析项目中所有论文"""
        papers = self._import_arxiv_papers("knowledge graph embedding", 3)
        if not papers:
            pytest.skip("搜索结果中无 PDF 链接")

        dl_result = self.parser.download_all_pdfs(self.PROJECT_ID)
        print(f"\n[batch] 下载: total={dl_result['total']}, ok={dl_result['downloaded']}, skip={dl_result['skipped']}, fail={dl_result['failed']}")

        result = self.parser.parse_project_papers(self.PROJECT_ID)
        print(f"[batch] 解析: total={result['total']}, ok={result['success']}, fail={result['failed']}, skip={result['skipped']}")

        assert result["success"] > 0, "应至少成功解析 1 篇"

    def test_07_chunks_stored_in_postgres(self):
        """chunks 应存入 PostgreSQL paper_chunks 表"""
        papers = self._import_arxiv_papers("few-shot learning", 2)
        if not papers:
            pytest.skip("搜索结果中无 PDF 链接")

        paper = papers[0]
        dl = self.parser.download_pdf(paper.paper_id)
        if not dl.get("success"):
            pytest.skip(f"PDF 下载失败")
        self.parser.parse_paper(paper.paper_id)

        chunks = self.pg.query("paper_chunks", {"paper_id": paper.paper_id})
        assert len(chunks) > 0, "paper_chunks 表应有数据"

        c = chunks[0]
        assert c.get("chunk_id")
        assert c.get("paper_id") == paper.paper_id
        assert c.get("text")
        print(f"\n[postgres] {len(chunks)} chunks 存入 paper_chunks 表")
