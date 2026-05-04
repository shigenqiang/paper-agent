"""
统一引用管理模块 - Unified Citation Module

功能：
1. 格式化参考文献（APA/MLA/Chicago/IEEE/GB7714等）
2. DOI验证和元数据解析
3. 从文本提取引用标记
4. 答案溯源追踪

使用方式：
    from src.agents_v2.citation import CitationFormatter, DOIVerifier, CitationExtractor

    # 格式化引用
    formatter = CitationFormatter()
    formatted = formatter.format(paper, style='apa')

    # 验证DOI
    verifier = DOIVerifier()
    result = await verifier.verify("10.1038/nature12373")

    # 提取引用
    extractor = CitationExtractor()
    citations = extractor.extract_from_text(text)
"""

from .formatter import CitationFormatter, format_citation
from .verifier import DOIVerifier, verify_doi
from .extractor import CitationExtractor, extract_citations
from .tracker import CitationTracker, track_citations
from .styles import CitationStyle, SUPPORTED_STYLES

__all__ = [
    "CitationFormatter",
    "CitationStyle",
    "SUPPORTED_STYLES",
    "format_citation",
    "DOIVerifier",
    "verify_doi",
    "CitationExtractor",
    "extract_citations",
    "CitationTracker",
    "track_citations",
]