"""P3-C PDF 上传端点测试

覆盖：
- 成功上传 PDF
- 拒绝非 PDF 文件
- 拒绝超大文件
- 自动解析选项
- 创建论文记录
"""

import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestPDFUpload:
    """PDF 上传测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from src.agents_v3.research_workspace.api.app import create_app
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_upload_pdf_success(self):
        """成功上传 PDF 文件"""
        with patch("src.agents_v3.research_workspace.api.routes.papers._resolve_project") as mock_proj, \
             patch("src.agents_v3.research_workspace.api.deps.get_storage") as mock_storage:
            mock_proj.return_value = MagicMock(project_id="proj1")
            mock_store = MagicMock()
            mock_store.data_dir = MagicMock()
            mock_store.data_dir.__truediv__ = lambda self, x: MagicMock(
                __truediv__=lambda s, y: MagicMock(
                    mkdir=MagicMock(),
                    write_bytes=MagicMock(),
                    __str__=lambda s: f"/tmp/files/proj1/paper_test.pdf",
                )
            )
            mock_storage.return_value = mock_store

            # Create a small PDF-like file
            pdf_content = b"%PDF-1.4 minimal pdf content"
            resp = self.client.post(
                "/api/rw/projects/proj1/papers/upload",
                files={"file": ("test_paper.pdf", io.BytesIO(pdf_content), "application/pdf")},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "paper" in data.get("data", {})
            assert data["data"]["paper"]["source"] == "upload"

    def test_upload_rejects_non_pdf(self):
        """拒绝非 PDF 文件"""
        with patch("src.agents_v3.research_workspace.api.routes.papers._resolve_project") as mock_proj:
            mock_proj.return_value = MagicMock(project_id="proj1")

            resp = self.client.post(
                "/api/rw/projects/proj1/papers/upload",
                files={"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")},
            )
            assert resp.status_code == 422
            assert "PDF" in resp.json().get("error", {}).get("message", "")

    def test_upload_rejects_oversized(self):
        """拒绝超大文件（>50MB）"""
        with patch("src.agents_v3.research_workspace.api.routes.papers._resolve_project") as mock_proj:
            mock_proj.return_value = MagicMock(project_id="proj1")

            # Create a 51MB file
            big_content = b"%PDF" + b"x" * (51 * 1024 * 1024)
            resp = self.client.post(
                "/api/rw/projects/proj1/papers/upload",
                files={"file": ("big.pdf", io.BytesIO(big_content), "application/pdf")},
            )
            assert resp.status_code == 422
            assert "too large" in resp.json().get("error", {}).get("message", "").lower()

    def test_upload_auto_parse(self):
        """auto_parse=true 时触发解析"""
        with patch("src.agents_v3.research_workspace.api.routes.papers._resolve_project") as mock_proj, \
             patch("src.agents_v3.research_workspace.api.deps.get_storage") as mock_storage, \
             patch("src.agents_v3.research_workspace.api.routes.papers.get_parser_service") as mock_parser:
            mock_proj.return_value = MagicMock(project_id="proj1")
            mock_store = MagicMock()
            mock_store.data_dir = MagicMock()
            mock_store.data_dir.__truediv__ = lambda self, x: MagicMock(
                __truediv__=lambda s, y: MagicMock(
                    mkdir=MagicMock(),
                    write_bytes=MagicMock(),
                    __str__=lambda s: "/tmp/test.pdf",
                )
            )
            mock_storage.return_value = mock_store

            mock_svc = MagicMock()
            mock_svc.parse_paper.return_value = {"sections": 5, "quality": "good"}
            mock_parser.return_value = mock_svc

            pdf_content = b"%PDF-1.4 test"
            resp = self.client.post(
                "/api/rw/projects/proj1/papers/upload?auto_parse=true",
                files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
            )
            assert resp.status_code == 200
            data = resp.json().get("data", {})
            assert "parse_result" in data

    def test_upload_creates_paper_record(self):
        """上传后创建论文记录"""
        with patch("src.agents_v3.research_workspace.api.routes.papers._resolve_project") as mock_proj, \
             patch("src.agents_v3.research_workspace.api.deps.get_storage") as mock_storage:
            mock_proj.return_value = MagicMock(project_id="proj1")
            mock_store = MagicMock()
            mock_store.data_dir = MagicMock()
            mock_store.data_dir.__truediv__ = lambda self, x: MagicMock(
                __truediv__=lambda s, y: MagicMock(
                    mkdir=MagicMock(),
                    write_bytes=MagicMock(),
                    __str__=lambda s: "/tmp/test.pdf",
                )
            )
            mock_storage.return_value = mock_store

            pdf_content = b"%PDF-1.4 test"
            resp = self.client.post(
                "/api/rw/projects/proj1/papers/upload",
                files={"file": ("my_paper.pdf", io.BytesIO(pdf_content), "application/pdf")},
            )
            assert resp.status_code == 200

            # Verify upsert was called with paper data
            mock_store.upsert_item.assert_called_once()
            call_args = mock_store.upsert_item.call_args
            assert call_args[0][0] == "papers"
            paper_data = call_args[0][2]
            assert paper_data["project_id"] == "proj1"
            assert paper_data["title"] == "my_paper"
            assert paper_data["source"] == "upload"
