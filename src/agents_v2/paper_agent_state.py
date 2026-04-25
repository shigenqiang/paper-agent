"""
学术写作助手 - 单一PaperAgent状态模型

核心设计：
- 单一Agent内部通过current_phase切换不同处理模式
- 各阶段结果存储在phase_history中
- Self-Reflection状态贯穿全程
"""
from pydantic import BaseModel, Field
from typing import TypedDict, List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum
import uuid


class Phase(str, Enum):
    """工作阶段"""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    WRITING = "writing"
    REVIEW = "review"
    COMPLETED = "completed"


class AgentMode(str, Enum):
    """Agent执行模式"""
    IDLE = "idle"
    RESEARCH_MODE = "research_mode"
    ANALYSIS_MODE = "analysis_mode"
    WRITING_MODE = "writing_mode"
    REVIEW_MODE = "review_mode"


class ValidationStatus(str, Enum):
    """验证状态"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============ 反思模型 ============

class ReflectionResult(BaseModel):
    """反思结果"""
    needs_improvement: bool = False
    quality_score: float = 0.0
    issues: List[str] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)
    iteration: int = 0


class PhaseExecution(BaseModel):
    """阶段执行记录"""
    phase: str
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    result: Dict[str, Any] = Field(default_factory=dict)
    reflection: Optional[Dict[str, Any]] = None
    quality_score: float = 0.0
    validation_passed: bool = False
    error: Optional[str] = None


# ============ 研究阶段模型 ============

class SearchQuery(BaseModel):
    """搜索查询"""
    query: str
    strategy: str = "default"  # default, expansion, verification
    aspect: str = "general"  # method, application, trend, general


class PaperMetadata(BaseModel):
    """论文元数据"""
    paper_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: str = ""
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    published_date: Optional[str] = None
    source: str = "unknown"
    relevance_score: float = 0.0


class PaperAnalysis(BaseModel):
    """论文分析结果"""
    paper_id: str
    title: str
    core_problem: str = ""
    key_methodology: str = ""
    key_findings: str = ""
    limitations: str = ""
    datasets: List[str] = Field(default_factory=list)
    evaluation_metrics: List[str] = Field(default_factory=list)


# ============ 分析阶段模型 ============

class Theme(BaseModel):
    """主题"""
    name: str
    description: str
    paper_ids: List[str] = Field(default_factory=list)
    key_papers: List[str] = Field(default_factory=list)


class ResearchGap(BaseModel):
    """研究空白"""
    description: str
    evidence: str = ""
    potential_directions: List[str] = Field(default_factory=list)


class MethodComparison(BaseModel):
    """方法对比"""
    method_name: str
    description: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    datasets: List[str] = Field(default_factory=list)


# ============ 写作阶段模型 ============

class SectionOutline(BaseModel):
    """章节大纲"""
    index: int
    title: str
    outline: str
    key_points: List[str] = Field(default_factory=list)


class WrittenSection(BaseModel):
    """已写章节"""
    index: int
    title: str
    content: str
    citations: List[str] = Field(default_factory=list)
    quality_score: float = 0.0
    completed: bool = False


# ============ 审核阶段模型 ============

class CritiqueResult(BaseModel):
    """Critique结果"""
    passed: bool = False
    overall_score: float = 0.0
    perspective_scores: Dict[str, float] = Field(default_factory=dict)
    missing_topics: List[str] = Field(default_factory=list)
    suggested_queries: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    confidence: float = 0.8


# ============ Validation Gate模型 ============

class ValidationGateResult(BaseModel):
    """验证门结果"""
    gate_name: str
    status: ValidationStatus
    criteria: Dict[str, Any] = Field(default_factory=dict)
    actual: Dict[str, Any] = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)
    severity: Literal["info", "warning", "error"] = "info"


class QualityMetrics(BaseModel):
    """质量指标"""
    # 研究质量
    research_coverage: float = 0.0
    paper_relevance: float = 0.0
    source_diversity: float = 0.0

    # 分析质量
    theme_coherence: float = 0.0
    gap_identification: float = 0.0

    # 写作质量
    content_alignment: float = 0.0
    structural_quality: float = 0.0
    language_quality: float = 0.0
    citation_completeness: float = 0.0

    # 整体质量
    overall_score: float = 0.0


# ============ LangGraph TypedDict 状态 ============

class PaperAgentState(TypedDict):
    """
    单一PaperAgent核心状态

    设计原则：
    1. 单一Agent通过current_phase切换模式
    2. 各阶段结果存储在phase_history
    3. reflection_result存储当前反思结果
    4. validation_gates存储各阶段验证状态
    """

    # ===== 输入层 =====
    session_id: str
    user_request: str
    constraints: Dict[str, Any]
    created_at: str

    # ===== 执行上下文 =====
    current_phase: str  # research | analysis | writing | review | completed
    current_mode: str  # research_mode | analysis_mode | writing_mode | review_mode
    phase_history: List[Dict[str, Any]]  # 各阶段执行记录
    execution_context: Dict[str, Any]  # 当前执行上下文

    # ===== 研究阶段 =====
    search_queries: List[Dict[str, str]]
    papers: List[Dict[str, Any]]
    ranked_papers: List[Dict[str, Any]]
    pending_papers: List[Dict[str, Any]]
    paper_analyses: List[Dict[str, Any]]

    # ===== 分析阶段 =====
    themes: List[Dict[str, Any]]
    research_gaps: List[str]
    method_comparisons: List[Dict[str, Any]]
    trend_analysis: Dict[int, int]

    # ===== 写作阶段 =====
    outline: List[Dict[str, str]]
    written_sections: List[Dict[str, Any]]
    current_section_index: int
    report: str

    # ===== 审核阶段 =====
    critique_result: Dict[str, Any]
    critique_passed: bool
    missing_topics: List[str]
    suggested_queries: List[str]

    # ===== 反思循环 =====
    reflection_result: Dict[str, Any]  # 当前反思结果
    reflection_history: List[Dict[str, Any]]  # 反思历史
    improvement_suggestions: List[str]  # 改进建议
    iteration: int  # 当前迭代次数

    # ===== 质量门控 =====
    quality_scores: Dict[str, float]
    validation_gates: Dict[str, str]  # phase_name -> ValidationStatus

    # ===== 记忆层 =====
    short_term_memory: Dict[str, Any]
    long_term_memory: Dict[str, Any]
    episodic_memory: List[Dict[str, Any]]

    # ===== 迭代控制 =====
    max_iterations: int
    self_reflection_notes: List[str]

    # ===== 错误处理 =====
    errors: List[Dict[str, Any]]
    checkpoints: Dict[str, Dict[str, Any]]
    circuit_breaker_triggered: bool
    fallback_mode: bool

    # ===== 系统状态 =====
    status: Literal["init", "running", "paused", "completed", "failed"]
    start_time: Optional[str]
    end_time: Optional[str]


# ============ 默认状态工厂函数 ============

def create_initial_paper_state(
    user_request: str,
    session_id: Optional[str] = None,
    constraints: Optional[Dict[str, Any]] = None
) -> PaperAgentState:
    """创建初始状态"""
    return PaperAgentState(
        # 输入层
        session_id=session_id or str(uuid.uuid4()),
        user_request=user_request,
        constraints=constraints or {},
        created_at=datetime.now().isoformat(),

        # 执行上下文
        current_phase=Phase.RESEARCH.value,
        current_mode=AgentMode.IDLE.value,
        phase_history=[],
        execution_context={},

        # 研究阶段
        search_queries=[],
        papers=[],
        ranked_papers=[],
        pending_papers=[],
        paper_analyses=[],

        # 分析阶段
        themes=[],
        research_gaps=[],
        method_comparisons=[],
        trend_analysis={},

        # 写作阶段
        outline=[],
        written_sections=[],
        current_section_index=0,
        report="",

        # 审核阶段
        critique_result={},
        critique_passed=False,
        missing_topics=[],
        suggested_queries=[],

        # 反思循环
        reflection_result={},
        reflection_history=[],
        improvement_suggestions=[],
        iteration=0,

        # 质量门控
        quality_scores={},
        validation_gates={},

        # 记忆层
        short_term_memory={},
        long_term_memory={},
        episodic_memory=[],

        # 迭代控制
        max_iterations=3,
        self_reflection_notes=[],

        # 错误处理
        errors=[],
        checkpoints={},
        circuit_breaker_triggered=False,
        fallback_mode=False,

        # 系统状态
        status="init",
        start_time=None,
        end_time=None
    )
