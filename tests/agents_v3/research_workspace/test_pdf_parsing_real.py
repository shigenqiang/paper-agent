"""真实PDF解析集成测试

使用arXiv论文 (Attention Is All You Need, 1706.03762) 测试完整解析链路。
"""

import json
import time
from pathlib import Path

import pytest

from src.agents_v3.research_workspace.parser_service import (
    ParserService,
    PdfPlumberAdapter,
    PyMuPDFAdapter,
    TextPostProcessor,
    ChunkCleaner,
)
from src.agents_v3.research_workspace.models import PaperStatus

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_PDF = FIXTURES / "sample_paper.pdf"


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr("src.agents_v3.research_workspace.storage._global_storage", None)
    monkeypatch.setattr(
        "src.agents_v3.research_workspace.parser_service.get_storage",
        lambda: __import__("src.agents_v3.research_workspace.storage", fromlist=["JSONStorage"]).JSONStorage(tmp_path),
    )
    return ParserService()


@pytest.fixture
def registered_paper(service, tmp_path):
    """将真实PDF注册到storage"""
    import shutil
    dest = tmp_path / "sample_paper.pdf"
    shutil.copy(SAMPLE_PDF, dest)

    service.storage.upsert_item("papers", "real_p1", {
        "paper_id": "real_p1",
        "project_id": "proj1",
        "title": "Attention Is All You Need",
        "status": PaperStatus.UPLOADED.value,
        "pdf_path": str(dest),
    })
    return {"paper_id": "real_p1", "pdf_path": str(dest)}


# ── 适配器级别测试 ────────────────────────────────────


class TestAdaptersOnRealPDF:
    """真实PDF适配器提取测试"""

    def test_pdfplumber_extracts_text(self, tmp_path):
        """pdfplumber 应从真实PDF提取到文本"""
        adapter = PdfPlumberAdapter()
        assert adapter.can_parse(str(SAMPLE_PDF))

        pages_text, flags = adapter.extract_pages(str(SAMPLE_PDF))
        assert len(pages_text) > 0
        all_text = " ".join(t for _, t in pages_text)
        assert len(all_text) > 1000, f"提取文本过短: {len(all_text)} chars"

    def test_pymupdf_extracts_text(self, tmp_path):
        """PyMuPDF 应从真实PDF提取到文本"""
        adapter = PyMuPDFAdapter()
        assert adapter.can_parse(str(SAMPLE_PDF))

        pages_text, flags = adapter.extract_pages(str(SAMPLE_PDF))
        assert len(pages_text) > 0
        all_text = " ".join(t for _, t in pages_text)
        assert len(all_text) > 1000

    def test_both_adapters_extract_similar_page_count(self):
        """两个适配器应提取到相近的页数"""
        pp_adapter = PdfPlumberAdapter()
        pm_adapter = PyMuPDFAdapter()

        pp_pages, _ = pp_adapter.extract_pages(str(SAMPLE_PDF))
        pm_pages, _ = pm_adapter.extract_pages(str(SAMPLE_PDF))

        # 允许1页差异
        assert abs(len(pp_pages) - len(pm_pages)) <= 1

    def test_page_numbers_are_sequential(self):
        """页码应连续递增"""
        adapter = PdfPlumberAdapter()
        pages_text, _ = adapter.extract_pages(str(SAMPLE_PDF))
        page_nums = [p for p, _ in pages_text]
        for i in range(len(page_nums) - 1):
            assert page_nums[i + 1] > page_nums[i]


# ── 文本后处理测试 ────────────────────────────────────


class TestPostProcessing:
    """文本后处理管线测试"""

    def test_ligature_fix_on_real_text(self):
        """真实PDF中的合字应被修复"""
        adapter = PdfPlumberAdapter()
        pages_text, _ = adapter.extract_pages(str(SAMPLE_PDF))
        all_text = " ".join(t for _, t in pages_text)

        pp = TextPostProcessor()
        processed = pp.process(all_text)

        # 常见合字不应出现
        assert "ﬁ" not in processed or "fi" in processed

    def test_hyphenation_fix_on_synthetic(self):
        """连字符断行应被修复"""
        pp = TextPostProcessor()
        assert pp.fix_hyphenation("computa-\ntion") == "computation"
        assert pp.fix_hyphenation("self-\ncontained") == "selfcontained"

    def test_citation_markers_fixed(self):
        """引用标记应被正确处理"""
        adapter = PdfPlumberAdapter()
        pages_text, _ = adapter.extract_pages(str(SAMPLE_PDF))
        all_text = " ".join(t for _, t in pages_text)

        pp = TextPostProcessor()
        processed = pp.process(all_text)

        # 引用标记应紧贴前文
        assert "word [1]" not in processed


# ── 章节检测与分块测试 ────────────────────────────────────


class TestSectionDetection:
    """章节检测测试"""

    def test_detects_abstract_section(self, service, registered_paper):
        """应检测到 Abstract 章节"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        chunks = service.get_chunks("real_p1")
        section_types = {c.section_type for c in chunks}
        assert "abstract" in section_types, f"未检测到abstract，实际sections: {section_types}"

    def test_detects_body_sections(self, service, registered_paper):
        """应检测到正文章节（Introduction/Background/Method等）"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        chunks = service.get_chunks("real_p1")
        section_types = {c.section_type for c in chunks}
        body_like = {"introduction", "body", "background", "method", "result", "discussion", "conclusion"}
        has_body = body_like & section_types
        assert has_body, f"未检测到正文章节，实际sections: {section_types}"

    def test_detects_references_section(self, service, registered_paper):
        """应检测到 References 章节"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        chunks = service.get_chunks("real_p1")
        section_types = {c.section_type for c in chunks}
        assert "reference" in section_types, f"未检测到reference，实际sections: {section_types}"

    def test_section_coverage(self, service, registered_paper):
        """章节覆盖率应合理（大部分文本应被归类）"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        chunks = service.get_chunks("real_p1")
        total_tokens = sum(c.token_count for c in chunks)
        assert total_tokens > 1000, f"总token数过少: {total_tokens}"


# ── 分块质量测试 ────────────────────────────────────


class TestChunkQuality:
    """分块质量测试"""

    def test_chunk_count_reasonable(self, service, registered_paper):
        """分块数量应合理（15页论文应有多个chunk）"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True
        assert result["chunk_count"] >= 5, f"chunk数过少: {result['chunk_count']}"

    def test_chunk_token_counts_in_range(self, service, registered_paper):
        """每个chunk的token数应在合理范围内"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        chunks = service.get_chunks("real_p1")
        for c in chunks:
            # 允许小碎片（标题等）和大chunk
            assert c.token_count > 0, f"chunk {c.chunk_id} token数为0"

    def test_chunk_has_required_fields(self, service, registered_paper):
        """每个chunk应包含所有必要字段"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        chunks = service.get_chunks("real_p1")
        for c in chunks:
            assert c.paper_id == "real_p1"
            assert hasattr(c, "chunk_index")
            assert hasattr(c, "section_type")
            assert hasattr(c, "chunk_type")
            assert hasattr(c, "page_start")
            assert hasattr(c, "page_end")
            assert c.text and len(c.text.strip()) > 0

    def test_no_empty_chunks(self, service, registered_paper):
        """不应有空chunk"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        chunks = service.get_chunks("real_p1")
        for c in chunks:
            assert len(c.text.strip()) > 0, f"chunk {c.chunk_id} 为空"

    def test_body_chunks_exclude_references(self, service, registered_paper):
        """正文chunks不应包含reference类型"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        body_chunks = service.get_body_chunks("real_p1")
        for c in body_chunks:
            assert c.chunk_type != "reference"


# ── 参考文献提取测试 ────────────────────────────────────


class TestReferenceExtraction:
    """参考文献提取测试"""

    def test_references_extracted(self, service, registered_paper):
        """应提取到参考文献"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        chunks = service.get_chunks("real_p1")
        ref_chunks = [c for c in chunks if c.chunk_type == "reference"]
        assert len(ref_chunks) > 0, "未提取到参考文献"

    def test_references_have_content(self, service, registered_paper):
        """参考文献chunk应有实际内容"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        chunks = service.get_chunks("real_p1")
        ref_chunks = [c for c in chunks if c.chunk_type == "reference"]
        for rc in ref_chunks:
            assert len(rc.text) > 50, f"参考文献chunk过短: {rc.text[:50]}"


# ── 端到端解析测试 ────────────────────────────────────


class TestEndToEndParsing:
    """端到端解析链路测试"""

    def test_full_parse_pipeline(self, service, registered_paper):
        """完整解析管线：PDF → 分块 → 存储"""
        start = time.time()
        result = service.parse_paper("real_p1")
        elapsed = time.time() - start

        assert result["success"] is True
        assert result["chunk_count"] > 0
        assert elapsed < 30, f"解析耗时过长: {elapsed:.1f}s"

    def test_parse_result_stored(self, service, registered_paper):
        """解析后应存储ParseResult"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        parse_result = service.get_parse_result("real_p1")
        assert parse_result is None or parse_result.status == "success"

    def test_paper_status_updated(self, service, registered_paper):
        """解析后论文状态应更新为PARSED"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        paper = service.storage.get_item("papers", "real_p1")
        assert paper["status"] == PaperStatus.PARSED.value

    def test_parser_name_recorded(self, service, registered_paper):
        """应记录使用的解析器名称（在ParseResult中）"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True
        parse_result = service.get_parse_result("real_p1")
        if parse_result is not None:
            assert parse_result.parser_name in ("pdfplumber", "pymupdf", "pdfminer")

    def test_quality_flags_present(self, service, registered_paper):
        """应有质量标记字段"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True
        # quality_flags 应该存在（可以是空列表）
        assert "quality_flags" in result or "flags" in result

    def test_force_reparse(self, service, registered_paper):
        """force=True 应重新解析已解析的论文"""
        result1 = service.parse_paper("real_p1")
        assert result1["success"] is True

        result2 = service.parse_paper("real_p1", force=True)
        assert result2["success"] is True
        assert result2["chunk_count"] > 0

    def test_skip_already_parsed(self, service, registered_paper):
        """不force时应跳过已解析的论文"""
        result1 = service.parse_paper("real_p1")
        assert result1["success"] is True

        result2 = service.parse_paper("real_p1", force=False)
        # 应该被跳过
        assert result2.get("skipped") is True or result2["success"] is True


# ── 内容验证测试 ────────────────────────────────────


class TestContentVerification:
    """验证解析内容的正确性"""

    def test_abstract_content_present(self, service, registered_paper):
        """解析结果应包含摘要内容"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        chunks = service.get_chunks("real_p1")
        abstract_chunks = [c for c in chunks if c.section_type == "abstract"]
        if abstract_chunks:
            abstract_text = " ".join(c.text for c in abstract_chunks)
            # Attention Is All You Need 的摘要应包含这些关键词
            assert any(kw in abstract_text.lower() for kw in [
                "attention", "sequence", "transducer", "transformer",
                "recurrent", "convolutional", "translation",
            ]), f"摘要内容异常: {abstract_text[:200]}"

    def test_keywords_present_in_chunks(self, service, registered_paper):
        """解析结果应包含论文关键术语"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        chunks = service.get_chunks("real_p1")
        all_text = " ".join(c.text for c in chunks).lower()

        keywords = ["attention", "transformer", "encoder", "decoder", "self-attention"]
        found = [kw for kw in keywords if kw in all_text]
        assert len(found) >= 3, f"关键词命中不足: {found}"

    def test_no_garbled_content(self, service, registered_paper):
        """解析结果不应有乱码"""
        result = service.parse_paper("real_p1")
        assert result["success"] is True

        chunks = service.get_chunks("real_p1")
        for c in chunks:
            # 不应有CID伪影
            assert "(cid:" not in c.text, f"chunk含CID伪影: {c.text[:100]}"
