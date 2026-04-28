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
- AnswerQualityChecker: 答案质量检查
- StreamingGenerator: 流式生成
- GenerationOptimizer: 生成优化
- CitationGenerator: 引用生成
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
    reflect
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
    CitationStyle,
    Citation,
    InTextCitation,
    CitationResult,
    CitationStyleAdapter,
    format_citation,
    generate_references
)

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
    "CitationGenerator",
    "CitationStyle",
    "Citation",
    "InTextCitation",
    "CitationResult",
    "CitationStyleAdapter",
    "format_citation",
    "generate_references",
]
