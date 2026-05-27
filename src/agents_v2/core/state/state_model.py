"""
State Model - 状态模型

定义PaperState及其相关数据结构。
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PaperPhase(str, Enum):
    """论文阶段"""
    DIAGNOSTIC = "diagnostic"
    TOPIC = "topic"
    LITERATURE = "literature"
    METHODOLOGY = "methodology"
    WRITING = "writing"
    POLISH = "polish"
    COMPLETED = "completed"
    FAILED = "failed"


class StateStatus(str, Enum):
    """状态状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StateMetadata:
    """状态元数据"""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateValidationError:
    """状态验证错误"""
    field: str
    message: str
    code: str


@dataclass
class StateValidationResult:
    """状态验证结果"""
    valid: bool
    errors: List[StateValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [
                {"field": e.field, "message": e.message, "code": e.code}
                for e in self.errors
            ],
            "warnings": self.warnings
        }


@dataclass
class PaperState:
    """
    论文状态

    包含论文处理的完整状态信息。

    Attributes:
        phase: 当前阶段
        status: 状态
        title: 论文标题
        topic: 研究主题
        outline: 大纲
        content: 内容
        references: 参考文献
        metadata: 元数据
    """

    # 基本信息
    paper_id: Optional[str] = None
    phase: PaperPhase = PaperPhase.DIAGNOSTIC
    status: StateStatus = StateStatus.PENDING

    # 内容相关
    title: Optional[str] = None
    topic: Optional[str] = None
    abstract: Optional[str] = None
    outline: Optional[str] = None
    content: Optional[str] = None

    # 文献相关
    references: List[Dict[str, Any]] = field(default_factory=list)
    cited_papers: List[str] = field(default_factory=list)

    # 诊断信息
    diagnostic_result: Optional[Dict[str, Any]] = None
    research_gaps: List[str] = field(default_factory=list)

    # 元数据
    metadata: StateMetadata = field(default_factory=StateMetadata)

    # 错误处理
    error_message: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "paper_id": self.paper_id,
            "phase": self.phase.value if isinstance(self.phase, Enum) else self.phase,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "title": self.title,
            "topic": self.topic,
            "abstract": self.abstract,
            "outline": self.outline,
            "content": self.content,
            "references": self.references,
            "cited_papers": self.cited_papers,
            "diagnostic_result": self.diagnostic_result,
            "research_gaps": self.research_gaps,
            "metadata": {
                "created_at": self.metadata.created_at.isoformat() if self.metadata.created_at else None,
                "updated_at": self.metadata.updated_at.isoformat() if self.metadata.updated_at else None,
                "version": self.metadata.version,
                "tags": self.metadata.tags,
                "notes": self.metadata.notes,
            },
            "error_message": self.error_message,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaperState":
        """从字典创建"""
        metadata = data.get("metadata", {})
        state = cls(
            paper_id=data.get("paper_id"),
            phase=PaperPhase(data.get("phase", "diagnostic")) if isinstance(data.get("phase"), str) else data.get("phase", PaperPhase.DIAGNOSTIC),
            status=StateStatus(data.get("status", "pending")) if isinstance(data.get("status"), str) else data.get("status", StateStatus.PENDING),
            title=data.get("title"),
            topic=data.get("topic"),
            abstract=data.get("abstract"),
            outline=data.get("outline"),
            content=data.get("content"),
            references=data.get("references", []),
            cited_papers=data.get("cited_papers", []),
            diagnostic_result=data.get("diagnostic_result"),
            research_gaps=data.get("research_gaps", []),
            error_message=data.get("error_message"),
            retry_count=data.get("retry_count", 0),
        )

        if "metadata" in data:
            state.metadata = StateMetadata(
                created_at=datetime.fromisoformat(metadata["created_at"]) if metadata.get("created_at") else datetime.now(),
                updated_at=datetime.fromisoformat(metadata["updated_at"]) if metadata.get("updated_at") else datetime.now(),
                version=metadata.get("version", 1),
                tags=metadata.get("tags", []),
                notes=metadata.get("notes", ""),
            )

        return state

    def is_terminal(self) -> bool:
        """是否处于终态"""
        return self.status in (StateStatus.COMPLETED, StateStatus.FAILED, StateStatus.CANCELLED)

    def can_transition_to(self, new_phase: PaperPhase) -> bool:
        """是否可以转换到新阶段"""
        phase_order = [
            PaperPhase.DIAGNOSTIC,
            PaperPhase.TOPIC,
            PaperPhase.LITERATURE,
            PaperPhase.METHODOLOGY,
            PaperPhase.WRITING,
            PaperPhase.POLISH,
            PaperPhase.COMPLETED,
        ]

        try:
            current_idx = phase_order.index(self.phase)
            new_idx = phase_order.index(new_phase)
            return new_idx >= current_idx
        except ValueError:
            return False

    def update_metadata(self):
        """更新元数据"""
        self.metadata.updated_at = datetime.now()
        self.metadata.version += 1

    def get_progress(self) -> float:
        """获取进度百分比"""
        phase_map = {
            PaperPhase.DIAGNOSTIC: 0.1,
            PaperPhase.TOPIC: 0.2,
            PaperPhase.LITERATURE: 0.4,
            PaperPhase.METHODOLOGY: 0.5,
            PaperPhase.WRITING: 0.7,
            PaperPhase.POLISH: 0.9,
            PaperPhase.COMPLETED: 1.0,
            PaperPhase.FAILED: 0.0,
        }
        return phase_map.get(self.phase, 0.0)


def create_initial_state(paper_id: str) -> PaperState:
    """创建初始状态"""
    return PaperState(
        paper_id=paper_id,
        phase=PaperPhase.DIAGNOSTIC,
        status=StateStatus.PENDING,
        metadata=StateMetadata()
    )