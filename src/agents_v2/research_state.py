"""
学术写作助手 - 核心状态模型

基于新的Agent架构设计，定义完整的研究状态模型。
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, TypedDict, List, Dict, Literal
from datetime import datetime
from enum import Enum
import uuid


class Phase(str, Enum):
    """工作流阶段"""
    PLANNING = "planning"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    REVIEW = "review"
    WRITING = "writing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(str, Enum):
    """Agent类型"""
    SUPERVISOR = "supervisor"
    PLANNER = "planner"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    WRITER = "writer"
    REVIEWER = "reviewer"


class ValidationStatus(str, Enum):
    """验证状态"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============ 论文相关模型 ============

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
    categories: List[str] = Field(default_factory=list)
    doi: Optional[str] = None
    relevance_score: float = 0.0


class ExtractedPaperData(BaseModel):
    """论文提取数据"""
    title: str
    abstract: str = ""
    core_problem: str = ""
    key_methodology_name: str = ""
    key_methodology_principle: str = ""
    key_methodology_novelty: str = ""
    datasets_used: List[str] = Field(default_factory=list)
    evaluation_metrics: List[str] = Field(default_factory=list)
    main_results: str = ""
    limitations: str = ""
    contributions: List[str] = Field(default_factory=list)


# ============ 分析相关模型 ============

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


# ============ 写作相关模型 ============

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


# ============ 验证门模型 ============

class ValidationGateResult(BaseModel):
    """验证门结果"""
    gate_name: str
    status: ValidationStatus
    criteria: Dict[str, Any] = Field(default_factory=dict)
    actual: Dict[str, Any] = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)
    severity: Literal["info", "warning", "error"] = "info"
    suggestions: List[str] = Field(default_factory=list)


class QualityMetrics(BaseModel):
    """质量指标"""
    # 研究质量
    research_coverage: float = 0.0
    paper_relevance: float = 0.0
    source_diversity: float = 0.0

    # 分析质量
    theme_coherence: float = 0.0
    gap_identification: float = 0.0
    contradiction_detection: float = 0.0

    # 写作质量
    content_alignment: float = 0.0
    structural_quality: float = 0.0
    language_quality: float = 0.0
    citation_completeness: float = 0.0

    # 整体质量
    overall_score: float = 0.0


# ============ 错误处理模型 ============

class CircuitBreakerState(BaseModel):
    """熔断器状态"""
    failure_count: int = 0
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    circuit_state: Literal["CLOSED", "OPEN", "HALF_OPEN"] = "CLOSED"
    last_failure_time: Optional[datetime] = None


class ErrorRecord(BaseModel):
    """错误记录"""
    node: str
    error_type: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    recovered: bool = False


# ============ 记忆模型 ============

class ShortTermMemory(BaseModel):
    """短期记忆"""
    current_query: str = ""
    recent_searches: List[str] = Field(default_factory=list)
    recent_findings: List[str] = Field(default_factory=list)
    active_context: Dict[str, Any] = Field(default_factory=dict)


class EpisodicMemory(BaseModel):
    """情景记忆"""
    session_id: str
    events: List[Dict[str, Any]] = Field(default_factory=list)
    key_decisions: List[str] = Field(default_factory=list)
    failures: List[Dict[str, Any]] = Field(default_factory=list)


# ============ Critique模型 ============

class CritiqueResult(BaseModel):
    """Critique结果"""
    passed: bool = False
    overall_score: float = 0.0
    perspective_scores: Dict[str, float] = Field(default_factory=dict)
    missing_topics: List[str] = Field(default_factory=list)
    suggested_queries: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    confidence: float = 0.8


# ============ LangGraph TypedDict 状态 ============

class ResearchAgentState(TypedDict):
    """
    学术写作助手核心状态

    分层组织：
    1. 输入层 - 用户请求和会话信息
    2. 规划层 - 研究计划和任务分解
    3. 研究层 - 论文搜索和阅读
    4. 分析层 - 主题分析和趋势发现
    5. 审核层 - Critique和迭代
    6. 写作层 - 报告生成
    7. 验证层 - 质量门控
    8. 记忆层 - 记忆管理
    9. 迭代层 - 迭代控制
    10. 错误层 - 错误处理
    """

    # ===== 输入层 =====
    session_id: str
    user_request: str
    constraints: Dict[str, Any]
    created_at: str

    # ===== 规划层 =====
    phase: str  # Phase枚举
    search_queries: List[Dict[str, str]]  # [{query, strategy}]
    task_queue: List[Dict[str, Any]]
    execution_plan: Dict[str, Any]
    current_tasks: List[str]
    completed_tasks: List[str]

    # ===== 研究层 =====
    papers: List[Dict[str, Any]]
    papers_after_rank: List[Dict[str, Any]]
    pending_papers: List[Dict[str, Any]]
    read_papers: List[Dict[str, Any]]
    extraction_results: List[Dict[str, Any]]
    search_errors: List[Dict[str, Any]]
    search_metadata: Dict[str, Any]

    # ===== 分析层 =====
    themes: List[Dict[str, Any]]
    trend_analysis: Dict[int, int]
    method_comparison: List[Dict[str, Any]]
    research_gaps: List[str]
    contradictions: List[str]
    influential_works: List[str]
    analysis_metadata: Dict[str, Any]

    # ===== 审核层 =====
    critique_result: Dict[str, Any]
    critique_score: float
    critique_passed: bool
    missing_topics: List[str]
    suggested_queries: List[str]
    critique_iteration: int

    # ===== 写作层 =====
    outline: List[Dict[str, str]]
    sections: List[Dict[str, str]]
    written_sections: List[Dict[str, Any]]
    current_section_index: int
    report: str
    writing_metadata: Dict[str, Any]

    # ===== 验证层 =====
    validation_gates: Dict[str, str]  # gate_name -> ValidationStatus
    quality_scores: Dict[str, float]
    validation_errors: List[str]

    # ===== 记忆层 =====
    short_term_memory: Dict[str, Any]
    long_term_memory: Dict[str, Any]
    episodic_memory: List[Dict[str, Any]]
    memory_retrieval_results: List[Dict[str, Any]]

    # ===== 迭代控制 =====
    iteration: int
    max_iterations: int
    self_reflection_notes: List[str]
    improvement_suggestions: List[str]

    # ===== 错误处理 =====
    errors: List[Dict[str, Any]]
    checkpoints: Dict[str, Dict[str, Any]]
    rollback_count: int
    circuit_breaker_triggered: bool
    fallback_mode: bool

    # ===== 系统状态 =====
    status: Literal["init", "running", "paused", "completed", "failed"]
    start_time: Optional[str]
    end_time: Optional[str]
    total_duration: Optional[float]


# ============ 默认状态工厂函数 ============

def create_initial_state(
    user_request: str,
    session_id: Optional[str] = None,
    constraints: Optional[Dict[str, Any]] = None
) -> ResearchAgentState:
    """创建初始状态"""
    return ResearchAgentState(
        # 输入层
        session_id=session_id or str(uuid.uuid4()),
        user_request=user_request,
        constraints=constraints or {},
        created_at=datetime.now().isoformat(),

        # 规划层
        phase=Phase.PLANNING.value,
        search_queries=[],
        task_queue=[],
        execution_plan={},
        current_tasks=[],
        completed_tasks=[],

        # 研究层
        papers=[],
        papers_after_rank=[],
        pending_papers=[],
        read_papers=[],
        extraction_results=[],
        search_errors=[],
        search_metadata={},

        # 分析层
        themes=[],
        trend_analysis={},
        method_comparison=[],
        research_gaps=[],
        contradictions=[],
        influential_works=[],
        analysis_metadata={},

        # 审核层
        critique_result={},
        critique_score=0.0,
        critique_passed=False,
        missing_topics=[],
        suggested_queries=[],
        critique_iteration=0,

        # 写作层
        outline=[],
        sections=[],
        written_sections=[],
        current_section_index=0,
        report="",
        writing_metadata={},

        # 验证层
        validation_gates={},
        quality_scores={},
        validation_errors=[],

        # 记忆层
        short_term_memory={},
        long_term_memory={},
        episodic_memory=[],
        memory_retrieval_results=[],

        # 迭代层
        iteration=0,
        max_iterations=3,
        self_reflection_notes=[],
        improvement_suggestions=[],

        # 错误层
        errors=[],
        checkpoints={},
        rollback_count=0,
        circuit_breaker_triggered=False,
        fallback_mode=False,

        # 系统状态
        status="init",
        start_time=None,
        end_time=None,
        total_duration=None
    )
