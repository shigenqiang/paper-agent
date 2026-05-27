"""
统一Agent框架状态模型

定义论文写作过程中的状态结构
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict


class PhaseStatus(str, Enum):
    """阶段状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class QualityLevel(str, Enum):
    """质量等级"""
    EXCELLENT = "excellent"  # >= 9.0
    GOOD = "good"            # >= 7.0
    ACCEPTABLE = "acceptable"  # >= 5.0
    POOR = "poor"            # < 5.0


class ProblemType(str, Enum):
    """问题类型枚举"""
    # 选题相关
    TOPIC_VAGUE = "topic_vague"           # 选题模糊
    TOPIC_TOO_BROAD = "topic_too_broad"   # 选题太宽
    TOPIC_LACK_NOVELTY = "topic_lack_novelty"  # 缺乏创新

    # 文献相关
    LITERATURE_INSUFFICIENT = "literature_insufficient"  # 文献不足
    LITERATURE_ONE_SIDED = "literature_one_sided"        # 综述片面
    GAP_NOT_IDENTIFIED = "gap_not_identified"            # 空白未识别

    # 方法相关
    METHOD_INAPPROPRIATE = "method_inappropriate"       # 方法不当
    METHOD_NOT_RIGOROUS = "method_not_rigorous"          # 严谨性不足

    # 论证相关
    ARGUMENT_WEAK = "argument_weak"          # 论证薄弱
    LOGIC_INCOHERENT = "logic_incoherent"   # 逻辑不连贯

    # 内容相关
    ABSTRACT_REPEATS_CONCLUSION = "abstract_repeats_conclusion"  # 摘要重复结论
    DISCUSSION_SHALLOW = "discussion_shallow"  # 讨论浅薄

    # 格式相关
    CHART_POOR = "chart_poor"              # 图表粗糙
    LANGUAGE_POOR = "language_poor"        # 语言表达差
    PLAGIARISM_RISK = "plagiarism_risk"    # 查重风险


@dataclass
class QualityScore:
    """质量评分"""
    score: float = 0.0
    level: QualityLevel = QualityLevel.POOR
    details: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AgentResult:
    """Agent执行结果"""
    agent_name: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DiagnosticResult:
    """诊断结果"""
    problems_found: List[ProblemType] = field(default_factory=list)
    severity: Dict[ProblemType, float] = field(default_factory=dict)  # 0.0-1.0
    recommendations: List[str] = field(default_factory=list)
    affected_phases: List[str] = field(default_factory=list)


@dataclass
class PhaseResult:
    """阶段结果"""
    phase_name: str
    status: PhaseStatus
    agent_results: List[AgentResult] = field(default_factory=list)
    diagnostic: Optional[DiagnosticResult] = None
    output: Optional[Dict[str, Any]] = None
    quality_score: Optional[QualityScore] = None
    execution_time: float = 0.0
    error: Optional[str] = None


class PaperState:
    """
    论文写作全局状态

    包含：
    1. 元数据
    2. 各阶段状态
    3. 诊断结果
    4. 问题追踪
    """

    def __init__(self, user_request: str):
        # 元数据
        self.user_request = user_request
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

        # 当前阶段
        self.current_phase: Optional[str] = None
        self.phase_sequence: List[str] = []

        # 各阶段结果
        self.phase_results: Dict[str, PhaseResult] = {}

        # 诊断结果
        self.diagnostics: Dict[str, DiagnosticResult] = {}

        # 发现的问题
        self.problems: List[ProblemType] = []
        self.problem_severity: Dict[ProblemType, float] = {}

        # 迭代控制
        self.iteration: int = 0
        self.max_iterations: int = 3

        # 质量追踪
        self.quality_history: List[QualityScore] = []

        # 上下文传递
        self.context: Dict[str, Any] = {}

        # 错误记录
        self.errors: List[str] = []

    def update_phase(self, phase_name: str, result: PhaseResult):
        """更新阶段结果"""
        self.phase_results[phase_name] = result
        self.current_phase = phase_name
        self.updated_at = datetime.now().isoformat()

        if phase_name not in self.phase_sequence:
            self.phase_sequence.append(phase_name)

        # 更新质量历史
        if result.quality_score:
            self.quality_history.append(result.quality_score)

        # 收集问题
        if result.diagnostic:
            self.problems.extend(result.diagnostic.problems_found)
            for p, s in result.diagnostic.severity.items():
                if p not in self.problem_severity or s > self.problem_severity[p]:
                    self.problem_severity[p] = s

    def add_error(self, error: str, phase: Optional[str] = None):
        """记录错误"""
        self.errors.append(f"[{phase or 'unknown'}] {error}")
        self.updated_at = datetime.now().isoformat()

    def get_quality_level(self) -> QualityLevel:
        """获取当前质量等级"""
        if not self.quality_history:
            return QualityLevel.POOR

        latest = self.quality_history[-1]
        if latest.score >= 9.0:
            return QualityLevel.EXCELLENT
        elif latest.score >= 7.0:
            return QualityLevel.GOOD
        elif latest.score >= 5.0:
            return QualityLevel.ACCEPTABLE
        return QualityLevel.POOR

    def needs_diagnosis(self) -> bool:
        """是否需要诊断"""
        return len(self.problems) > 0

    def get_critical_problems(self) -> List[ProblemType]:
        """获取严重问题"""
        return [p for p, s in self.problem_severity.items() if s >= 0.7]

    def should_retry_phase(self, phase_name: str) -> bool:
        """是否应该重试阶段"""
        result = self.phase_results.get(phase_name)
        if not result:
            return True

        if result.status == PhaseStatus.FAILED:
            return self.iteration < self.max_iterations

        if result.quality_score and result.quality_score.score < 7.0:
            return self.iteration < self.max_iterations

        return False

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "user_request": self.user_request,
            "current_phase": self.current_phase,
            "phase_sequence": self.phase_sequence,
            "phase_results": {
                name: {
                    "phase_name": r.phase_name,
                    "status": r.status,
                    "quality_score": r.quality_score.score if r.quality_score else None,
                    "execution_time": r.execution_time
                }
                for name, r in self.phase_results.items()
            },
            "problems": [p.value for p in self.problems],
            "problem_severity": {p.value: s for p, s in self.problem_severity.items()},
            "iteration": self.iteration,
            "quality_level": self.get_quality_level().value,
            "errors": self.errors[-5:]  # 只保留最近5个错误
        }