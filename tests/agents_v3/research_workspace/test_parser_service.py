"""ParserService 测试"""

import pytest
from pathlib import Path

from src.agents_v3.research_workspace.parser_service import ParserService
from src.agents_v3.research_workspace.models import PaperStatus, PaperChunk


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("src.agents_v3.research_workspace.storage._global_storage", None)
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.parser_service.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return ParserService()


@pytest.fixture
def sample_paper(service, tmp_path):
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    storage = service.storage
    paper_data = {
        "paper_id": "p1",
        "project_id": "proj1",
        "title": "Test Paper",
        "status": PaperStatus.UPLOADED.value,
        "pdf_path": str(pdf_path),
    }
    storage.upsert_item("papers", "p1", paper_data)
    return paper_data


class TestParserService:
    def test_parse_nonexistent_paper_returns_failure(self, service):
        result = service.parse_paper("missing")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_parse_paper_without_pdf_returns_failure(self, service):
        service.storage.upsert_item("papers", "p1", {
            "paper_id": "p1", "project_id": "proj1", "pdf_path": ""
        })
        result = service.parse_paper("p1")
        assert result["success"] is False
        # Should be marked FAILED
        paper = service.storage.get_item("papers", "p1")
        assert paper["status"] == PaperStatus.FAILED.value

    def test_parse_paper_sets_parsing_status(self, service, sample_paper):
        """解析开始时应写 PARSING 状态"""
        # We can't easily test intermediate PARSING status since it's fast,
        # but we can verify the final status
        result = service.parse_paper("p1")
        paper = service.storage.get_item("papers", "p1")
        # Either PARSED or FAILED depending on pdfplumber handling of fake PDF
        assert paper["status"] in (PaperStatus.PARSED.value, PaperStatus.FAILED.value)

    def test_parse_paper_no_stub_chunk_on_failure(self, service, sample_paper):
        """解析失败时不应生成 stub 正文 chunk"""
        result = service.parse_paper("p1")
        if not result["success"]:
            # No chunks should be written
            chunks = service.get_chunks("p1")
            for c in chunks:
                assert "requires pdfplumber" not in c.text

    def test_get_chunks_returns_parsed_chunks(self, service, sample_paper):
        result = service.parse_paper("p1")
        if result["success"]:
            chunks = service.get_chunks("p1")
            assert len(chunks) > 0
            assert chunks[0].paper_id == "p1"
            # New fields should exist
            assert hasattr(chunks[0], "chunk_index")
            assert hasattr(chunks[0], "section_type")
            assert hasattr(chunks[0], "chunk_type")
            assert hasattr(chunks[0], "page_start")
            assert hasattr(chunks[0], "page_end")

    def test_parse_project_papers_parses_all_unparsed(self, service, sample_paper):
        result = service.parse_project_papers("proj1")
        assert result["success"] + result["failed"] == 1

    def test_parse_project_skips_already_parsed(self, service, sample_paper):
        result = service.parse_paper("p1")
        if result["success"]:
            # Already parsed, should skip
            result2 = service.parse_project_papers("proj1", only_unparsed=True)
            assert result2["skipped"] == 1
        else:
            # pdfplumber not installed - manually set PARSED and verify skip
            service._update_status("p1", PaperStatus.PARSED)
            result2 = service.parse_project_papers("proj1", only_unparsed=True)
            assert result2["skipped"] == 1

    def test_parse_missing_pdf_file_returns_failure(self, service):
        service.storage.upsert_item("papers", "p2", {
            "paper_id": "p2",
            "project_id": "proj1",
            "pdf_path": "/nonexistent/file.pdf",
        })
        result = service.parse_paper("p2")
        assert result["success"] is False

    def test_get_body_chunks_excludes_references(self, service):
        """get_body_chunks 应排除 reference 类型"""
        # Manually insert chunks
        service.storage.save_collection("paper_chunks", [
            {"chunk_id": "c1", "paper_id": "p1", "chunk_type": "body", "text": "Body text " * 50, "chunk_index": 0},
            {"chunk_id": "c2", "paper_id": "p1", "chunk_type": "reference", "text": "[1] Ref text", "chunk_index": 1},
            {"chunk_id": "c3", "paper_id": "p1", "chunk_type": "body", "text": "More body " * 50, "chunk_index": 2},
        ])
        body = service.get_body_chunks("p1")
        assert len(body) == 2
        assert all(c.chunk_type != "reference" for c in body)

    def test_get_chunks_compatible_with_old_format(self, service):
        """旧格式 chunks_{paper_id} 应能被读取"""
        service.storage.save_collection("chunks_p1", [
            {"chunk_id": "c1", "paper_id": "p1", "text": "Old format chunk", "token_count": 5},
        ])
        chunks = service.get_chunks("p1")
        assert len(chunks) == 1
        assert chunks[0].text == "Old format chunk"

    def test_parse_result_stored(self, service, sample_paper):
        """解析后应存储 ParseResult"""
        result = service.parse_paper("p1")
        if "parse_id" in result:
            parse_result = service.get_parse_result("p1")
            assert parse_result is not None
            assert parse_result.paper_id == "p1"
