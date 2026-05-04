"""
学术QA系统 - Academic QA System

面向学术领域的严谨问答系统，支持引用溯源和多跳推理。

核心模块:
- DocumentParser: 文档解析器
- AcademicChunker: 学术文档分块器
- HybridRetriever: 混合检索器 (BM25 + 向量 + RRF)
- CitationTracker: 引用溯源器
- AnswerGenerator: 答案生成器
- CRAGEvaluator: CRAG 纠错型检索评估
- SelfRAGController: Self-RAG 反思机制
- HallucinationDetector: 幻觉检测器
- ConfidenceCalibrator: 置信度校准器
- QueryDecomposer: 查询分解器（多跳推理）
- MultiHopReasoner: 多跳推理器
- RAGAsEvaluator: RAGAs 评估框架
- AnswerAggregator: 答案聚合器

推荐使用统一模块:
- src.agents_v2.citation: 统一引用管理
- src.agents_v2.reports: 统一报告生成
"""

from .doc_parser import DocumentParser, ParsedDocument
from .chunker import AcademicChunker, Chunk
from .hybrid_retriever import HybridRetriever, RetrievalResult

# 引用溯源 - 使用统一模块（推荐）
# 旧的 CitationTracker 保留用于向后兼容
from .citation_tracker import CitationTracker, Citation, TracedContent

from .answer_generator import AnswerGenerator, GeneratedAnswer, AcademicAnswerGenerator
from .crag import CRAGEvaluator, CRAGResult, RetrievalQuality
from .self_rag import SelfRAGController, SelfRAGResult, ReflectionToken
from .hallucination_detector import HallucinationDetector, HallucinationReport, StatementCheck
from .confidence_calibrator import ConfidenceCalibrator, ConfidenceScore
from .query_decomposer import QueryDecomposer, SubQuestion
from .multi_hop_reasoner import MultiHopReasoner, MultiHopResult, SubAnswer
from .ragas_evaluator import RAGAsEvaluator, RAGAsMetrics
from .answer_aggregator import AnswerAggregator, AggregatedResult, ReasoningStep
from .system import AcademicQASystem, AcademicQAResult, AcademicQAConfig, create_academic_qa_system
from .kg_integration import (
    KGEnhancedContext,
    KGRetrieverWrapper,
    KGAnswerEnricher,
    KGMultiHopReasoner,
    AcademicQAKGIntegration,
    create_kg_enhanced_qa_system,
)

# 尝试导入统一引用模块
try:
    from ..citation import (
        CitationFormatter,
        CitationStyle,
        SUPPORTED_STYLES as CITATION_STYLES,
        format_citation,
        DOIVerifier,
        verify_doi,
        CitationExtractor,
        extract_citations,
        track_citations,
    )
    _citation_module_available = True
except ImportError:
    _citation_module_available = False

__all__ = [
    # 文档解析
    "DocumentParser",
    "ParsedDocument",

    # 分块
    "AcademicChunker",
    "Chunk",

    # 检索
    "HybridRetriever",
    "RetrievalResult",

    # 引用溯源 (legacy - use src.agents_v2.citation instead)
    "CitationTracker",
    "Citation",
    "TracedContent",

    # 答案生成
    "AnswerGenerator",
    "GeneratedAnswer",
    "AcademicAnswerGenerator",

    # CRAG
    "CRAGEvaluator",
    "CRAGResult",
    "RetrievalQuality",

    # Self-RAG
    "SelfRAGController",
    "SelfRAGResult",
    "ReflectionToken",

    # 幻觉检测
    "HallucinationDetector",
    "HallucinationReport",
    "StatementCheck",

    # 置信度校准
    "ConfidenceCalibrator",
    "ConfidenceScore",

    # 查询分解
    "QueryDecomposer",
    "SubQuestion",

    # 多跳推理
    "MultiHopReasoner",
    "MultiHopResult",
    "SubAnswer",

    # RAGAs 评估
    "RAGAsEvaluator",
    "RAGAsMetrics",

    # 答案聚合
    "AnswerAggregator",
    "AggregatedResult",
    "ReasoningStep",

    # 统一系统
    "AcademicQASystem",
    "AcademicQAResult",
    "AcademicQAConfig",
    "create_academic_qa_system",

    # 知识图谱集成
    "KGEnhancedContext",
    "KGRetrieverWrapper",
    "KGAnswerEnricher",
    "KGMultiHopReasoner",
    "AcademicQAKGIntegration",
    "create_kg_enhanced_qa_system",
]

# Unified citation exports (if available)
if _citation_module_available:
    __all__.extend([
        "CitationFormatter",
        "CitationStyle",
        "CITATION_STYLES",
        "format_citation",
        "DOIVerifier",
        "verify_doi",
        "CitationExtractor",
        "extract_citations",
        "track_citations",
    ])