"""
论文写作全流程Agent模块

Agent列表:
- LiteratureReviewAgent: 文献综述
- OutlineGeneratorAgent: 大纲生成
- DraftGeneratorAgent: 全文初稿
- ReportRefinerAgent: 报告精炼(多轮迭代)
- ProposalGeneratorAgent: 开题报告
- ReferenceProcessorAgent: 参考文献处理
- SmartReviserAgent: 智能改稿
- LanguagePolisherAgent: 语言润色

写作工具:
- ReflectionEngine: 反思引擎
- MultiLayerReflector: SciSage式多层反思器
- AnswerQualityChecker: 答案质量检查
- StreamingGenerator: 流式生成
- GenerationOptimizer: 生成优化
- CitationGenerator: 引用生成
- CitationVerifier: 引用验证
- DiffManager: 文本对比与补丁

推荐使用统一模块:
- src.agents_v2.citation: 统一引用管理
"""

from .literature_review import LiteratureReviewAgent
from .outline_generator import OutlineGeneratorAgent
from .draft_generator import DraftGeneratorAgent
from .report_refiner import ReportRefinerAgent, ReviewerAgent
from .proposal_generator import ProposalGeneratorAgent
from .reference_processor import ReferenceProcessorAgent
from .smart_reviser import SmartReviserAgent, LanguagePolisherAgent
from .reflection_engine import (
    ReflectionEngine,
    ReflectionLevel,
    ReflectionResult,
    SelfCritique,
    reflect,
    # Multi-layer reflector
    MultiLayerReflector,
    OutlineReflector,
    SectionReflector,
    DocumentReflector,
    ReflectionLayer,
    LayerReflectionResult,
    MultiLayerReflectionResult,
)
from .answer_quality_checker import (
    AnswerQualityChecker,
    QualityDimension,
    QualityIssue,
    QualityCheckResult,
    check_quality
)
from .streaming_generator import (
    StreamingGenerator,
    StreamChunk,
    StreamStatus,
    GenerationProgress,
    ChunkManager,
    stream_generate
)
from .generation_optimizer import (
    GenerationOptimizer,
    GenerationConfig,
    OptimizationStrategy,
    PromptCache,
    BatchGenerationOptimizer,
    optimize_generation
)
from .citation_generator import (
    CitationGenerator,
    CitationStyle as LegacyCitationStyle,
    Citation as LegacyCitation,
    InTextCitation,
    CitationResult,
    CitationStyleAdapter,
    format_citation as legacy_format_citation,
    generate_references,
    # Citation verification
    CitationVerifier,
    VerificationResult,
    verify_citation,
    verify_references,
)
from .diff_manager import (
    DiffManager,
    DiffView,
    DiffHunk,
    DiffLine,
    DiffLineType,
    ChangeSummary,
    get_diff_manager,
)

# 引用模块 - 使用统一模块（推荐）
# 旧的引用生成器保留用于向后兼容
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
        CitationTracker,
        track_citations,
    )
    _citation_module_available = True
except ImportError:
    _citation_module_available = False

__all__ = [
    # Agents
    "LiteratureReviewAgent",
    "OutlineGeneratorAgent",
    "DraftGeneratorAgent",
    "ReportRefinerAgent",
    "ReviewerAgent",
    "ProposalGeneratorAgent",
    "ReferenceProcessorAgent",
    "SmartReviserAgent",
    "LanguagePolisherAgent",
    # Writing Tools
    "ReflectionEngine",
    "ReflectionLevel",
    "ReflectionResult",
    "SelfCritique",
    "reflect",
    # Multi-layer reflector
    "MultiLayerReflector",
    "OutlineReflector",
    "SectionReflector",
    "DocumentReflector",
    "ReflectionLayer",
    "LayerReflectionResult",
    "MultiLayerReflectionResult",
    "AnswerQualityChecker",
    "QualityDimension",
    "QualityIssue",
    "QualityCheckResult",
    "check_quality",
    "StreamingGenerator",
    "StreamChunk",
    "StreamStatus",
    "GenerationProgress",
    "ChunkManager",
    "stream_generate",
    "GenerationOptimizer",
    "GenerationConfig",
    "OptimizationStrategy",
    "PromptCache",
    "BatchGenerationOptimizer",
    "optimize_generation",
    # Citation (legacy - use src.agents_v2.citation instead)
    "CitationGenerator",
    "LegacyCitationStyle",
    "LegacyCitation",
    "InTextCitation",
    "CitationResult",
    "CitationStyleAdapter",
    "legacy_format_citation",
    "generate_references",
    "CitationVerifier",
    "VerificationResult",
    "verify_citation",
    "verify_references",
    # Diff/Patch
    "DiffManager",
    "DiffView",
    "DiffHunk",
    "DiffLine",
    "DiffLineType",
    "ChangeSummary",
    "get_diff_manager",
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
        "CitationTracker",
        "track_citations",
    ])
