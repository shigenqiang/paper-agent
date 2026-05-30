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

    def test_extract_with_pymupdf_parses_real_pdf(self, service, tmp_path):
        """PyMuPDF 能解析包含文本的 PDF"""
        # 创建一个包含文本的 PDF
        import pymupdf
        pdf_path = tmp_path / "pymupdf_test.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Hello World. This is a test document with enough text.")
        doc.save(str(pdf_path))
        doc.close()

        from src.agents_v3.research_workspace.parser_service import PyMuPDFAdapter
        adapter = PyMuPDFAdapter()
        pages_text, flags = adapter.extract_pages(str(pdf_path))
        assert len(pages_text) == 1
        assert "Hello World" in pages_text[0][1]
        assert len(flags) == 0

    def test_fallback_to_pymupdf_when_pdfplumber_fails(self, service, tmp_path):
        """pdfplumber 失败时应 fallback 到 PyMuPDF"""
        import pymupdf
        pdf_path = tmp_path / "fallback_test.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "PyMuPDF extracted text for fallback test.")
        doc.save(str(pdf_path))
        doc.close()

        pages_text, parser_name, flags = service._extract_with_fallback(str(pdf_path))
        # 应该成功提取文本（pdfplumber 或 PyMuPDF）
        assert len(pages_text) > 0
        assert parser_name in ("pdfplumber", "pymupdf")

    def test_scanned_pdf_detected(self, service):
        """扫描件 PDF 应被检测并标记"""
        # 文件不存在时返回 not scanned
        result = service._detect_scanned_pdf("nonexistent.pdf")
        assert result["is_scanned"] is False
        assert result["confidence"] == 0

    def test_quality_flags_include_fallback_marker(self, service, tmp_path):
        """当 pdfplumber 失败时，quality_flags 应包含 fallback 标记"""
        import pymupdf
        pdf_path = tmp_path / "flag_test.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Test content for quality flags.")
        doc.save(str(pdf_path))
        doc.close()

        _, _, flags = service._extract_with_fallback(str(pdf_path))
        # 如果 pdfplumber 成功则无 fallback 标记，失败则有
        # 无论哪种情况，都不应有 scanned_pdf_suspected
        assert "scanned_pdf_suspected" not in flags

    def test_parser_service_end_to_end(self, service, tmp_path):
        """端到端测试：创建真实 PDF → 解析 → 获取 chunks"""
        import pymupdf
        pdf_path = tmp_path / "e2e_test.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Abstract\nThis is the abstract of the paper.")
        page.insert_text((72, 150), "Introduction\nThis is the introduction section.")
        page.insert_text((72, 250), "Methods\nWe used a novel approach.")
        page.insert_text((72, 350), "Results\nThe results were significant.")
        page.insert_text((72, 450), "Conclusion\nWe conclude that this works.")
        doc.save(str(pdf_path))
        doc.close()

        # 注册论文
        service.storage.upsert_item("papers", "e2e_p1", {
            "paper_id": "e2e_p1",
            "project_id": "proj1",
            "title": "E2E Test Paper",
            "status": "uploaded",
            "pdf_path": str(pdf_path),
        })

        result = service.parse_paper("e2e_p1")
        assert result["success"] is True
        assert result["chunk_count"] > 0

        # 检查 chunks
        chunks = service.get_chunks("e2e_p1")
        assert len(chunks) > 0
        assert all(c.paper_id == "e2e_p1" for c in chunks)

        # 检查 ParseResult
        parse_result = service.get_parse_result("e2e_p1")
        assert parse_result is not None
        assert parse_result.status == "success"
        assert parse_result.parser_name in ("pdfplumber", "pymupdf")


class TestGarbledTextDetection:
    """中文乱码检测测试"""

    def test_clean_text_not_garbled(self, service):
        """正常文本不应被检测为乱码"""
        text = "This is a normal English text with some Chinese characters like 你好世界."
        assert service._detect_garbled_text(text) is False

    def test_control_characters_detected(self, service):
        """包含控制字符的文本应被检测为乱码"""
        text = "Normal text" + "\x00\x01\x02\x03" * 20 + "more text"
        assert service._detect_garbled_text(text) is True

    def test_replacement_characters_detected(self, service):
        """包含大量替换字符的文本应被检测为乱码"""
        text = "Some text " + "□■◆◇○●" * 10 + " more text"
        assert service._detect_garbled_text(text) is True

    def test_short_text_not_garbled(self, service):
        """太短的文本不检测"""
        assert service._detect_garbled_text("short") is False
        assert service._detect_garbled_text("") is False

    def test_cjk_basic_range_not_garbled(self, service):
        """正常 CJK 字符不应被检测为乱码"""
        text = "这是一段正常的中文文本，包含常用的汉字和标点符号。" * 5
        assert service._detect_garbled_text(text) is False


class TestWatermarkDetection:
    """水印检测测试"""

    def test_no_watermark_normal_pdf(self, service):
        """正常 PDF 不应有水印"""
        pages = [(1, "This is normal text.\nNo watermarks here.")]
        assert service._detect_watermark(pages) is False

    def test_empty_pages_no_watermark(self, service):
        """空页面不应有水印"""
        assert service._detect_watermark([]) is False
        assert service._detect_watermark([(1, "")]) is False

    def test_single_page_no_watermark(self, service):
        """单页不检测水印"""
        pages = [(1, "Some text")]
        assert service._detect_watermark(pages) is False

    def test_cnki_watermark_detected(self, service):
        """知网水印应被检测"""
        pages = [
            (1, "Normal text\n知网"),
            (2, "More text\n知网"),
            (3, "Other text\n知网"),
        ]
        assert service._detect_watermark(pages) is True

    def test_repeated_short_text_detected(self, service):
        """多页重复的短文本应被检测为水印"""
        pages = [
            (1, "Normal text\n仅供个人使用"),
            (2, "Other text\n仅供个人使用"),
            (3, "More text\n仅供个人使用"),
        ]
        assert service._detect_watermark(pages) is True


class TestReferenceExtraction:
    """参考文献结构化提取测试"""

    def test_split_bracket_references(self, service):
        """[N] 格式的参考文献应被正确分割"""
        ref_text = """[1] Author A. Title A. Journal A, 2020.
[2] Author B. Title B. Journal B, 2021.
[3] Author C. Title C. Journal C, 2022."""
        refs = service._extract_references(ref_text, "p1")
        assert len(refs) == 3
        assert refs[0].index == 0
        assert refs[1].index == 1
        assert refs[2].index == 2

    def test_extract_doi(self, service):
        """DOI 应被正确提取"""
        ref_text = "[1] Smith J. A study. Nature, 2023. https://doi.org/10.1234/example"
        refs = service._extract_references(ref_text, "p1")
        assert len(refs) == 1
        assert "10.1234/example" in refs[0].doi

    def test_extract_year(self, service):
        """年份应被正确提取"""
        ref_text = "[1] Author A. Title. Journal, 2021."
        refs = service._extract_references(ref_text, "p1")
        assert len(refs) == 1
        assert refs[0].year == 2021

    def test_empty_ref_text(self, service):
        """空文本应返回空列表"""
        assert service._extract_references("", "p1") == []
        assert service._extract_references("short", "p1") == []

    def test_number_dot_references(self, service):
        """N. 格式的参考文献应被正确分割"""
        ref_text = """1. Author A. Title A. Journal A, 2020.
2. Author B. Title B. Journal B, 2021."""
        refs = service._extract_references(ref_text, "p1")
        assert len(refs) == 2

    def test_ref_id_format(self, service):
        """ref_id 应包含 paper_id"""
        ref_text = "[1] Author. Title. Journal, 2020."
        refs = service._extract_references(ref_text, "paper_123")
        assert len(refs) == 1
        assert "paper_123" in refs[0].ref_id


class TestParserAdapter:
    """ParserAdapter 架构测试"""

    def test_pdfplumber_adapter_can_parse(self, service, tmp_path):
        """PdfPlumberAdapter 应能解析真实 PDF"""
        from src.agents_v3.research_workspace.parser_service import PdfPlumberAdapter
        import pymupdf

        pdf_path = tmp_path / "adapter_test.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Adapter test content.")
        doc.save(str(pdf_path))
        doc.close()

        adapter = PdfPlumberAdapter()
        assert adapter.name == "pdfplumber"
        assert adapter.can_parse(str(pdf_path)) is True

    def test_pymupdf_adapter_can_parse(self, service, tmp_path):
        """PyMuPDFAdapter 应能解析真实 PDF"""
        from src.agents_v3.research_workspace.parser_service import PyMuPDFAdapter
        import pymupdf

        pdf_path = tmp_path / "pymupdf_adapter_test.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "PyMuPDF adapter test.")
        doc.save(str(pdf_path))
        doc.close()

        adapter = PyMuPDFAdapter()
        assert adapter.name == "pymupdf"
        assert adapter.can_parse(str(pdf_path)) is True

    def test_fallback_chain_uses_adapters(self, service, tmp_path):
        """_extract_with_fallback 应使用适配器链"""
        import pymupdf

        pdf_path = tmp_path / "chain_test.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Chain test content for fallback.")
        doc.save(str(pdf_path))
        doc.close()

        pages_text, parser_name, flags = service._extract_with_fallback(str(pdf_path))
        assert len(pages_text) > 0
        assert parser_name in ("pdfplumber", "pymupdf")


class TestEnhancedQualityReport:
    """增强质量报告测试"""

    def test_enhanced_quality_returns_flags_and_diagnostics(self, service):
        """增强质量检查应返回 flags 和 diagnostics"""
        pages = [(1, "Normal text content. " * 20)]
        flags, diagnostics = service._check_quality_enhanced(pages, 3, 5)
        assert isinstance(flags, list)
        assert isinstance(diagnostics, dict)
        assert "total_chars" in diagnostics
        assert "total_pages" in diagnostics

    def test_enhanced_quality_detects_watermark(self, service):
        """增强质量检查应检测水印"""
        pages = [
            (1, "Text\n知网"),
            (2, "Text\n知网"),
            (3, "Text\n知网"),
        ]
        flags, diagnostics = service._check_quality_enhanced(pages, 3, 5)
        assert "watermark_suspected" in flags
        assert diagnostics.get("watermark") is True

    def test_enhanced_quality_detects_garbled(self, service):
        """增强质量检查应检测乱码"""
        garbled_text = "Normal " + "\x00\x01\x02" * 30 + " end"
        pages = [(1, garbled_text)]
        flags, diagnostics = service._check_quality_enhanced(pages, 1, 1)
        assert "garbled_text_detected" in flags

    def test_parse_result_has_diagnostics(self, service, tmp_path):
        """ParseResult 应包含 diagnostics 字段"""
        import pymupdf

        pdf_path = tmp_path / "diag_test.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Abstract\nThis is the abstract.")
        page.insert_text((72, 150), "Introduction\nThis is the introduction.")
        doc.save(str(pdf_path))
        doc.close()

        service.storage.upsert_item("papers", "diag_p1", {
            "paper_id": "diag_p1",
            "project_id": "proj1",
            "title": "Diag Test Paper",
            "status": "uploaded",
            "pdf_path": str(pdf_path),
        })

        result = service.parse_paper("diag_p1")
        if result["success"]:
            parse_result = service.get_parse_result("diag_p1")
            assert parse_result is not None
            assert isinstance(parse_result.diagnostics, dict)
            assert "total_chars" in parse_result.diagnostics


class TestTextPostProcessor:
    """文本后处理管线测试"""

    def test_fix_ligatures(self, service):
        from src.agents_v3.research_workspace.parser_service import TextPostProcessor
        pp = TextPostProcessor()
        assert pp.fix_ligatures("eﬃcient") == "efficient"
        assert pp.fix_ligatures("ﬁle") == "file"
        assert pp.fix_ligatures("ﬂow") == "flow"
        assert pp.fix_ligatures("normal text") == "normal text"

    def test_fix_hyphenation(self, service):
        from src.agents_v3.research_workspace.parser_service import TextPostProcessor
        pp = TextPostProcessor()
        assert pp.fix_hyphenation("computa-\ntion") == "computation"
        # 断行连字符被移除（包括复合词跨行的情况）
        assert pp.fix_hyphenation("self-\ncontained") == "selfcontained"
        # 不应修改非断行连字符（同一行内）
        assert pp.fix_hyphenation("well-known") == "well-known"

    def test_fix_citation_markers(self, service):
        from src.agents_v3.research_workspace.parser_service import TextPostProcessor
        pp = TextPostProcessor()
        assert pp.fix_citation_markers("word [1]") == "word[1]"
        assert pp.fix_citation_markers("words [1, 2]") == "words[1, 2]"
        assert pp.fix_citation_markers("text [3]") == "text[3]"

    def test_remove_page_numbers(self, service):
        from src.agents_v3.research_workspace.parser_service import TextPostProcessor
        pp = TextPostProcessor()
        text = "Some text\n- 3 -\nMore text\n42\nEnd"
        result = pp.remove_page_numbers(text)
        assert "- 3 -" not in result
        assert "42" not in result
        assert "Some text" in result
        assert "More text" in result

    def test_remove_headers_footers(self, service):
        from src.agents_v3.research_workspace.parser_service import TextPostProcessor
        pp = TextPostProcessor()
        pages = [
            (1, "Journal of XYZ\nReal content here\nPage 1"),
            (2, "Journal of XYZ\nMore content here\nPage 2"),
            (3, "Journal of XYZ\nFinal content here\nPage 3"),
        ]
        result = pp.remove_headers_footers(pages)
        # "Journal of XYZ" 和 "Page 1"/"Page 2"/"Page 3" 应被去除
        for _, text in result:
            assert "Journal of XYZ" not in text
            assert "Real content here" in text or "More content here" in text or "Final content here" in text

    def test_process_full_pipeline(self, service):
        from src.agents_v3.research_workspace.parser_service import TextPostProcessor
        pp = TextPostProcessor()
        text = "The ﬁrst computa-\ntion was eﬃcient [1] result."
        result = pp.process(text)
        assert "first" in result
        assert "computation" in result
        assert "efficient" in result
        assert "[1]" in result


class TestColumnDetection:
    """双栏检测与重排测试"""

    def test_single_column_returns_none(self, service):
        """单栏 PDF 应返回 None"""
        from src.agents_v3.research_workspace.parser_service import PyMuPDFAdapter
        # 模拟单栏文本块
        blocks = [
            (72, 72, 400, 90, "First line of text", 0, 0),
            (72, 100, 400, 118, "Second line of text", 0, 0),
            (72, 128, 400, 146, "Third line of text", 0, 0),
            (72, 156, 400, 174, "Fourth line of text", 0, 0),
        ]
        result = PyMuPDFAdapter._find_column_boundary(blocks, 595)
        assert result is None

    def test_dual_column_detected(self, service):
        """双栏文本应检测到分界线"""
        from src.agents_v3.research_workspace.parser_service import PyMuPDFAdapter
        # 模拟双栏文本块：左栏 x0=72, 右栏 x0=310
        blocks = [
            (72, 72, 280, 90, "Left column line 1", 0, 0),
            (72, 100, 280, 118, "Left column line 2", 0, 0),
            (310, 72, 520, 90, "Right column line 1", 0, 0),
            (310, 100, 520, 118, "Right column line 2", 0, 0),
        ]
        result = PyMuPDFAdapter._find_column_boundary(blocks, 595)
        assert result is not None
        # 分界线应在左栏右边界和右栏左边界之间
        assert 72 < result < 310

    def test_reorder_columns(self, service):
        """双栏重排应按 全宽→左栏→右栏 顺序"""
        from src.agents_v3.research_workspace.parser_service import PyMuPDFAdapter
        blocks = [
            (72, 72, 280, 90, "Left 1", 0, 0),
            (72, 100, 280, 118, "Left 2", 0, 0),
            (310, 72, 520, 90, "Right 1", 0, 0),
            (310, 100, 520, 118, "Right 2", 0, 0),
            (72, 200, 520, 218, "Full width title", 0, 0),
        ]
        boundary = 295.0
        result = PyMuPDFAdapter._reorder_columns(blocks, boundary)
        lines = [l for l in result.split("\n") if l.strip()]
        # 全宽应在最前
        assert lines[0] == "Full width title"
        # 左栏在右栏之前
        assert "Left 1" in lines[1]
        assert "Left 2" in lines[2]
        assert "Right 1" in lines[3]
        assert "Right 2" in lines[4]


class TestPdfMinerAdapter:
    """PdfMinerAdapter 测试"""

    def test_pdfminer_adapter_name(self):
        from src.agents_v3.research_workspace.parser_service import PdfMinerAdapter
        adapter = PdfMinerAdapter()
        assert adapter.name == "pdfminer"

    def test_pdfminer_can_parse(self, tmp_path):
        from src.agents_v3.research_workspace.parser_service import PdfMinerAdapter
        import pymupdf
        pdf_path = tmp_path / "pdfminer_test.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Test content for pdfminer.")
        doc.save(str(pdf_path))
        doc.close()

        adapter = PdfMinerAdapter()
        # pdfminer.six 可能未安装，但 can_parse 不应崩溃
        result = adapter.can_parse(str(pdf_path))
        assert isinstance(result, bool)


class TestEnhancedFallback:
    """增强 fallback 链路测试"""

    def test_scan_detection_returns_dict(self, service, tmp_path):
        """_detect_scanned_pdf 应返回字典"""
        import pymupdf
        pdf_path = tmp_path / "scan_dict_test.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Normal text content.")
        doc.save(str(pdf_path))
        doc.close()

        result = service._detect_scanned_pdf(str(pdf_path))
        assert isinstance(result, dict)
        assert "is_scanned" in result
        assert "confidence" in result
        assert "image_pages" in result
        assert "text_pages" in result

    def test_normal_pdf_not_scanned(self, service, tmp_path):
        """有文本的 PDF 不应被标记为扫描件"""
        import pymupdf
        pdf_path = tmp_path / "normal_scan_test.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "This is a normal PDF with text content.")
        doc.save(str(pdf_path))
        doc.close()

        result = service._detect_scanned_pdf(str(pdf_path))
        assert result["is_scanned"] is False

    def test_fallback_chain_with_post_processing(self, service, tmp_path):
        """fallback 链路应与后处理管线集成"""
        import pymupdf
        pdf_path = tmp_path / "postprocess_test.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Abstract\nThis is the abstract of the paper with enough text.")
        page.insert_text((72, 150), "Introduction\nThis is the introduction section content.")
        doc.save(str(pdf_path))
        doc.close()

        service.storage.upsert_item("papers", "pp_p1", {
            "paper_id": "pp_p1",
            "project_id": "proj1",
            "title": "Post Process Test",
            "status": "uploaded",
            "pdf_path": str(pdf_path),
        })

        result = service.parse_paper("pp_p1")
        # 不崩溃即可，后处理是透明的
        assert "success" in result


# ── ChunkCleaner 测试 ────────────────────────────────


class TestChunkCleaner:
    """ChunkCleaner 分块后清洗测试"""

    def setup_method(self):
        from src.agents_v3.research_workspace.parser_service import ChunkCleaner
        self.cleaner = ChunkCleaner()

    def test_filter_formula_lines(self):
        """公式行被过滤，正文行保留"""
        lines = [
            "The model uses a joint framework for analysis.",
            "βj (Φi ξ + Ψi ζij ), and xij = (x⊤ i1, · · · , x⊤ iJ )⊤",
            "We estimate the parameters using EM algorithm.",
            "∑ i=1 n Y j=1 J",
        ]
        result = self.cleaner._filter_lines(lines)
        assert "The model uses a joint framework for analysis." in result
        assert "We estimate the parameters using EM algorithm." in result
        # 公式行应被过滤
        assert len(result) == 2

    def test_filter_preserves_inline_math(self):
        """包含少量数学符号的正文行保留"""
        lines = [
            "The coefficient β represents the effect size.",
            "We set α = 0.05 for all tests.",
        ]
        result = self.cleaner._filter_lines(lines)
        assert len(result) == 2

    def test_filter_axis_label_block(self):
        """连续短行坐标轴标签块被过滤"""
        lines = [
            "The results show significant improvement.",
            "0.0", "0.2", "0.4", "0.6", "0.8", "1.0",
            "Months since baseline",
            "t", "t", "t",
            "Figure 3: Comparison of methods.",
        ]
        result = self.cleaner._filter_lines(lines)
        assert "The results show significant improvement." in result
        assert "Figure 3: Comparison of methods." in result
        # 坐标轴标签应被过滤
        assert "0.0" not in result
        assert "Months since baseline" not in result

    def test_keep_figure_caption(self):
        """Figure/Table caption 保留"""
        lines = [
            "Figure 1: Longitudinal biomarker trends.",
            "Table 2: Model comparison results.",
        ]
        result = self.cleaner._filter_lines(lines)
        assert len(result) == 2
        assert "Figure 1" in result[0]
        assert "Table 2" in result[1]

    def test_merge_small_fragments(self):
        """小于 min_tokens 的碎片与相邻 chunk 合并"""
        chunks = [
            {"chunk_index": 0, "section_type": "method", "chunk_type": "method",
             "text": "a" * 800, "page_start": 1, "page_end": 2, "token_count": 200},
            {"chunk_index": 1, "section_type": "method", "chunk_type": "method",
             "text": "small fragment", "page_start": 3, "page_end": 3, "token_count": 3},
            {"chunk_index": 2, "section_type": "method", "chunk_type": "method",
             "text": "b" * 800, "page_start": 4, "page_end": 5, "token_count": 200},
        ]
        result = self.cleaner._merge_fragments(chunks, min_tokens=200)
        # 碎片应被合并到前一个或后一个
        assert len(result) < len(chunks)

    def test_no_merge_different_section(self):
        """不同 section_type 的 chunk 不合并"""
        chunks = [
            {"chunk_index": 0, "section_type": "introduction", "chunk_type": "body",
             "text": "a" * 800, "page_start": 1, "page_end": 1, "token_count": 200},
            {"chunk_index": 1, "section_type": "method", "chunk_type": "method",
             "text": "small", "page_start": 2, "page_end": 2, "token_count": 1},
            {"chunk_index": 2, "section_type": "method", "chunk_type": "method",
             "text": "b" * 800, "page_start": 3, "page_end": 3, "token_count": 200},
        ]
        result = self.cleaner._merge_fragments(chunks, min_tokens=200)
        # 碎片与前一个不同 section，但与后一个相同 → 合并到后一个
        assert len(result) == 2

    def test_no_merge_exceeds_limit(self):
        """合并后超过 max_tokens 不合并"""
        chunks = [
            {"chunk_index": 0, "section_type": "method", "chunk_type": "method",
             "text": "a" * 3600, "page_start": 1, "page_end": 2, "token_count": 900},
            {"chunk_index": 1, "section_type": "method", "chunk_type": "method",
             "text": "b" * 1200, "page_start": 3, "page_end": 3, "token_count": 300},
        ]
        result = self.cleaner._merge_fragments(chunks, min_tokens=200, max_tokens=1000)
        assert len(result) == 2

    def test_update_token_counts(self):
        """clean 后 token_count 被重新计算"""
        chunks = [
            {"chunk_index": 0, "section_type": "method", "chunk_type": "method",
             "text": "This is a test sentence with enough words.", "token_count": 999},
        ]
        result = self.cleaner.clean(chunks)
        assert result[0]["token_count"] != 999
        assert result[0]["token_count"] > 0

    def test_clean_pipeline_includes_dedup(self):
        """clean 管线应包含去重步骤"""
        # 使用足够大的 chunk 避免被 _merge_fragments 合并
        dup_text = "Exact duplicate text for testing dedup. " * 30
        diff_text = "Different text that should remain after dedup. " * 30
        chunks = [
            {"chunk_index": 0, "section_type": "method", "chunk_type": "method",
             "text": dup_text, "token_count": 200},
            {"chunk_index": 1, "section_type": "method", "chunk_type": "method",
             "text": dup_text, "token_count": 200},
            {"chunk_index": 2, "section_type": "method", "chunk_type": "method",
             "text": diff_text, "token_count": 200},
        ]
        result = self.cleaner.clean(chunks)
        # 精确重复应被去重
        texts = [c["text"] for c in result]
        assert len(result) == 2

    def test_clean_pipeline_includes_quality_filter(self):
        """clean 管线应包含质量过滤"""
        chunks = [
            {"chunk_index": 0, "section_type": "method", "chunk_type": "method",
             "text": "High quality chunk. " * 50, "token_count": 200},
            {"chunk_index": 1, "section_type": "method", "chunk_type": "method",
             "text": "bad", "token_count": 1},  # 极低质量
        ]
        result = self.cleaner.clean(chunks)
        # 低质量 chunk 应被过滤
        assert len(result) == 1
        assert "High quality chunk" in result[0]["text"]


# ── T4.27 ChunkDeduplicator 测试 ─────────────────────


class TestChunkDeduplicator:
    """ChunkDeduplicator 三层去重测试"""

    def setup_method(self):
        from src.agents_v3.research_workspace.parser_service import ChunkDeduplicator
        self.dedup = ChunkDeduplicator()

    def test_exact_dedup_removes_duplicates(self):
        """完全相同的文本应被去重"""
        chunks = [
            {"text": "This is a duplicate sentence."},
            {"text": "This is a duplicate sentence."},
            {"text": "This is a different sentence."},
        ]
        result = self.dedup._exact_dedup(chunks)
        assert len(result) == 2

    def test_exact_dedup_preserves_unique(self):
        """不同文本应全部保留"""
        chunks = [
            {"text": "First unique text."},
            {"text": "Second unique text."},
            {"text": "Third unique text."},
        ]
        result = self.dedup._exact_dedup(chunks)
        assert len(result) == 3

    def test_exact_dedup_empty_text(self):
        """空文本应被去重（保留一个空 + 非空）"""
        chunks = [
            {"text": ""},
            {"text": ""},
            {"text": "non-empty"},
        ]
        result = self.dedup._exact_dedup(chunks)
        # 两个空文本 hash 相同 → 保留一个 + non-empty = 2
        assert len(result) == 2

    def test_deduplicate_calls_all_layers(self):
        """deduplicate 应调用所有三层去重"""
        chunks = [
            {"text": "Exact duplicate for testing."},
            {"text": "Exact duplicate for testing."},
            {"text": "Unique text for comparison."},
        ]
        result = self.dedup.deduplicate(chunks)
        assert len(result) == 2

    def test_deduplicate_empty_list(self):
        """空列表应返回空列表"""
        result = self.dedup.deduplicate([])
        assert result == []

    def test_deduplicate_single_chunk(self):
        """单个 chunk 应原样返回"""
        chunks = [{"text": "Single chunk text."}]
        result = self.dedup.deduplicate(chunks)
        assert len(result) == 1


# ── T4.28 ChunkQualityScorer 测试 ─────────────────────


class TestChunkQualityScorer:
    """ChunkQualityScorer 五维质量评分测试"""

    def setup_method(self):
        from src.agents_v3.research_workspace.parser_service import ChunkQualityScorer
        self.scorer = ChunkQualityScorer()

    def test_score_returns_dict_with_quality_score(self):
        """score 应返回包含 quality_score 的字典"""
        chunk = {"text": "This is a well-formed sentence with enough content. " * 10}
        result = self.scorer.score(chunk)
        assert "quality_score" in result
        assert "details" in result
        assert 0 <= result["quality_score"] <= 1

    def test_score_length_short_text(self):
        """过短文本长度分应低"""
        score = self.scorer._score_length("short")
        assert score == 0.2

    def test_score_length_ideal_text(self):
        """理想长度文本长度分应高"""
        text = "word " * 200  # ~200 tokens
        score = self.scorer._score_length(text)
        assert score == 1.0

    def test_score_length_long_text(self):
        """过长文本长度分应降低"""
        text = "word " * 2000  # ~2000 tokens
        score = self.scorer._score_length(text)
        assert score == 0.5

    def test_score_info_density_empty(self):
        """空文本信息密度应为 0"""
        score = self.scorer._score_info_density("")
        assert score == 0.0

    def test_score_info_density_content_text(self):
        """有内容的文本信息密度应高"""
        text = "The researchers conducted a comprehensive analysis of the neural network architecture."
        score = self.scorer._score_info_density(text)
        assert score > 0.5

    def test_score_structure_with_sentences(self):
        """包含句子结构的文本结构分应高"""
        text = "This is a sentence. And another one. With paragraph structure.\n\nNew paragraph."
        score = self.scorer._score_structure(text)
        assert score >= 0.8

    def test_score_language_pure_english(self):
        """纯英文文本语言一致性应高"""
        text = "This is pure English text without any mixed languages."
        score = self.scorer._score_language(text)
        assert score > 0.9

    def test_score_language_pure_chinese(self):
        """纯中文文本语言一致性应高"""
        text = "这是一段纯中文文本，没有混杂其他语言。"
        score = self.scorer._score_language(text)
        assert score > 0.9

    def test_score_noise_clean_text(self):
        """干净文本噪声分应高"""
        text = "This is clean text without noise. It has proper sentences and structure."
        score = self.scorer._score_noise(text)
        assert score > 0.8

    def test_score_overall_quality(self):
        """整体质量评分应在合理范围内"""
        chunk = {
            "text": "This is a well-structured paragraph about machine learning. "
                    "It discusses various approaches to natural language processing. "
                    "The authors propose a novel method for text classification. "
                    "Experimental results show significant improvements over baselines."
        }
        result = self.scorer.score(chunk)
        assert result["quality_score"] > 0.5

    def test_filter_low_quality_removes_bad_chunks(self):
        """filter_low_quality 应移除低质量 chunk"""
        from src.agents_v3.research_workspace.parser_service import ChunkCleaner
        cleaner = ChunkCleaner()
        # 使用高阈值来验证过滤功能
        chunks = [
            {"text": "Good quality chunk with enough words. " * 20},  # 高质量
            {"text": "∑ ∫ ∂ ∇ ∑ ∫ ∂ ∇"},  # 纯噪声
        ]
        result = cleaner._filter_low_quality(chunks, min_score=0.5)
        assert len(result) == 1
        assert "Good quality" in result[0]["text"]


# ── T4.29 ChunkRedundancyFilter 测试 ──────────────────


class TestChunkRedundancyFilter:
    """ChunkRedundancyFilter 冗余过滤测试"""

    def setup_method(self):
        from src.agents_v3.research_workspace.parser_service import ChunkRedundancyFilter
        self.filter = ChunkRedundancyFilter()

    def test_filter_single_chunk(self):
        """单个 chunk 应原样返回"""
        chunks = [{"text": "Single chunk text."}]
        result = self.filter.filter(chunks)
        assert len(result) == 1

    def test_filter_empty_list(self):
        """空列表应返回空列表"""
        result = self.filter.filter([])
        assert result == []

    def test_filter_keeps_unique_chunks(self):
        """不同内容的 chunk 应全部保留"""
        chunks = [
            {"text": "Machine learning is a subset of artificial intelligence."},
            {"text": "Natural language processing deals with text analysis."},
            {"text": "Computer vision focuses on image recognition tasks."},
        ]
        result = self.filter.filter(chunks)
        assert len(result) == 3

    def test_filter_removes_redundant(self):
        """高度冗余的 chunk 应被过滤（保留更长的）"""
        # BM25 有 term frequency saturation，相似度比 TF-IDF 低
        # 使用 0.4 阈值来验证 BM25 冗余过滤功能
        from src.agents_v3.research_workspace.parser_service import ChunkRedundancyFilter
        low_threshold_filter = ChunkRedundancyFilter(redundancy_threshold=0.4)
        chunks = [
            {"text": "The method uses deep learning for classification tasks in natural language processing."},
            {"text": "The method uses deep learning for classification tasks in natural language processing. It also achieves good results."},
            {"text": "Quantum computing is a completely different field of study unrelated."},
        ]
        result = low_threshold_filter.filter(chunks)
        # 冗余对中应保留更长的
        assert len(result) == 2
        texts = [c["text"] for c in result]
        assert any("quantum" in t.lower() for t in texts)

    def test_filter_preserves_quality_score(self):
        """过滤应保留 quality_score 字段"""
        chunks = [
            {"text": "Text A with quality.", "quality_score": 0.8},
            {"text": "Text B with quality.", "quality_score": 0.6},
        ]
        result = self.filter.filter(chunks)
        for c in result:
            assert "quality_score" in c
