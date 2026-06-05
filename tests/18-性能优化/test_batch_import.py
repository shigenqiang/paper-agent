"""模块18 批量导入测试

验证批量 PDF 上传和 BibTeX 解析改进。
"""

import io

import pytest
from unittest.mock import MagicMock


class TestBatchUpload:
    """批量 PDF 上传测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from src.agents_v3.research_workspace.api.app import create_app
        _store: dict = {}
        mock_storage = MagicMock()
        mock_storage.upsert.side_effect = lambda t, tid, d: _store.update({tid: dict(d)})
        mock_storage.upsert_item.side_effect = lambda t, tid, d: _store.update({tid: dict(d)})
        mock_storage.get_item.side_effect = lambda t, tid: _store.get(tid)
        mock_storage.get.side_effect = lambda t, ref: _store.get(ref)
        mock_storage.list_all.side_effect = lambda t: [dict(v) for v in _store.values()]
        mock_storage.query.side_effect = lambda t, f: [
            dict(v) for v in _store.values()
            if all(v.get(k) == val for k, val in f.items())
        ]
        mock_storage.load_collection.side_effect = lambda t: [dict(v) for v in _store.values()]
        self.app = create_app(storage=mock_storage)
        self.client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(self.app)
        self._store = _store

        # 创建一个项目
        resp = self.client.post("/api/rw/projects", json={"name": "batch_test"})
        self.project_id = resp.json().get("data", resp.json()).get("project_id")

    def test_batch_upload_success(self):
        """批量上传多个 PDF"""
        pdf_bytes = b"%PDF-1.4 fake pdf content"
        files = [
            ("files", ("paper1.pdf", io.BytesIO(pdf_bytes), "application/pdf")),
            ("files", ("paper2.pdf", io.BytesIO(pdf_bytes), "application/pdf")),
        ]
        resp = self.client.post(
            f"/api/rw/projects/{self.project_id}/papers/upload/batch",
            files=files,
        )
        assert resp.status_code == 200
        data = resp.json().get("data", resp.json())
        assert data["imported"] == 2
        assert data["failed"] == 0
        assert len(data["results"]) == 2

    def test_batch_upload_rejects_non_pdf(self):
        """非 PDF 文件应被拒绝"""
        files = [
            ("files", ("paper.txt", io.BytesIO(b"not a pdf"), "text/plain")),
        ]
        resp = self.client.post(
            f"/api/rw/projects/{self.project_id}/papers/upload/batch",
            files=files,
        )
        assert resp.status_code == 200
        data = resp.json().get("data", resp.json())
        assert data["imported"] == 0
        assert data["failed"] == 1
        assert len(data["errors"]) == 1

    def test_batch_upload_mixed(self):
        """混合有效和无效文件"""
        pdf_bytes = b"%PDF-1.4 fake pdf content"
        files = [
            ("files", ("good.pdf", io.BytesIO(pdf_bytes), "application/pdf")),
            ("files", ("bad.txt", io.BytesIO(b"text"), "text/plain")),
        ]
        resp = self.client.post(
            f"/api/rw/projects/{self.project_id}/papers/upload/batch",
            files=files,
        )
        data = resp.json().get("data", resp.json())
        assert data["imported"] == 1
        assert data["failed"] == 1


class TestBibtexParsing:
    """BibTeX 解析改进测试"""

    def test_parse_bibtex_library(self):
        """bibtexparser 库解析标准 BibTeX"""
        from src.agents_v3.research_workspace.services.paper_library import PaperLibraryService

        bibtex = """@article{smith2024,
            title = {A Great Paper},
            author = {Smith, John and Doe, Jane},
            year = {2024},
            journal = {Nature},
            doi = {10.1234/test}
        }"""
        entries = PaperLibraryService._parse_bibtex_library(bibtex)
        assert len(entries) == 1
        e = entries[0]
        assert e["title"] == "A Great Paper"
        assert e["year"] == 2024
        assert "Smith, John" in e["authors"]
        assert e["doi"] == "10.1234/test"

    def test_parse_bibtex_regex_nested_braces(self):
        """regex 解析器处理嵌套花括号"""
        from src.agents_v3.research_workspace.services.paper_library import PaperLibraryService

        bibtex = """@article{key1,
            title = {A Title with {Nested} Braces},
            year = {2023}
        }"""
        entries = PaperLibraryService._parse_bibtex_regex(bibtex)
        assert len(entries) == 1
        assert "Nested" in entries[0]["title"]

    def test_parse_bibtex_regex_quoted_values(self):
        """regex 解析器处理引号值"""
        from src.agents_v3.research_workspace.services.paper_library import PaperLibraryService

        bibtex = """@inproceedings{key2,
            title = "Quoted Title",
            year = "2022"
        }"""
        entries = PaperLibraryService._parse_bibtex_regex(bibtex)
        assert len(entries) == 1
        assert entries[0]["title"] == "Quoted Title"

    def test_parse_bibtex_skips_comment_preamble(self):
        """应跳过 @comment 和 @preamble"""
        from src.agents_v3.research_workspace.services.paper_library import PaperLibraryService

        bibtex = """@comment{some comment}
@preamble{some preamble}
@article{real_entry,
            title = {Real},
            year = {2024}
        }"""
        entries = PaperLibraryService._parse_bibtex_regex(bibtex)
        assert len(entries) == 1
        assert entries[0]["key"] == "real_entry"

    def test_parse_bibtex_multiple_entries(self):
        """解析多个条目"""
        from src.agents_v3.research_workspace.services.paper_library import PaperLibraryService

        bibtex = """@article{a1, title = {First}, year = {2020}}
@article{a2, title = {Second}, year = {2021}}
@article{a3, title = {Third}, year = {2022}}"""
        entries = PaperLibraryService._parse_bibtex_regex(bibtex)
        assert len(entries) == 3
