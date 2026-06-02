"""PDF 解析与分块子包"""

from src.agents_v3.research_workspace.parser.adapters import (
    DoclingAdapter,
    ParserAdapter,
    PdfMinerAdapter,
    PdfPlumberAdapter,
    PyMuPDF4LLMAdapter,
    PyMuPDFAdapter,
)
from src.agents_v3.research_workspace.parser.postprocess import (
    ChunkCleaner,
    ChunkDeduplicator,
    ChunkQualityScorer,
    ChunkRedundancyFilter,
    TextPostProcessor,
)
from src.agents_v3.research_workspace.parser.section_extractor import SectionExtractor
from src.agents_v3.research_workspace.parser.service import ParserService

__all__ = [
    "ChunkCleaner",
    "ChunkDeduplicator",
    "ChunkQualityScorer",
    "ChunkRedundancyFilter",
    "DoclingAdapter",
    "ParserAdapter",
    "ParserService",
    "PdfMinerAdapter",
    "PdfPlumberAdapter",
    "PyMuPDF4LLMAdapter",
    "PyMuPDFAdapter",
    "SectionExtractor",
    "TextPostProcessor",
]
