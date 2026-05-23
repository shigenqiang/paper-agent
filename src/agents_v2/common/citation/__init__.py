"""
Citation模块 - 引用处理

为三大系统（论文写作/QA问答/报告生成）提供统一的引用处理能力。

功能：
1. 引用解析 - 从文本中提取引用标记
2. 引用格式化 - 支持多种引用格式（APA/GB7714/Chicago/IEEE）
3. 引用追踪 - 追踪和管理文档中的引用关系
"""

from .citation_parser import CitationParser, Citation, CitationStyle, ParsedCitation, parse_citations
from .citation_formatter import CitationFormatter, FormattedCitation, format_citation
from .citation_tracker import CitationTracker, CitationNode, CitationStatistics

__all__ = [
    "CitationParser",
    "CitationFormatter",
    "Citation",
    "CitationStyle",
    "CitationTracker",
    "CitationNode",
    "CitationStatistics",
    "ParsedCitation",
    "FormattedCitation",
    "format_citation",
    "parse_citations",
]
