"""
Paper Agent 状态定义 - LangGraph State

定义统一的 PaperAgentState，包含论文调研与写作全流程的状态字段。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Paper:
    """论文数据结构"""
    id: str
    title: str
    authors: List[str]
    abstract: str
    url: str
    year: int = 0
    citations: int = 0
    venue: str = ""
    relevance_score: float = 0.0
    quality_score: float = 0.0
    full_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class PaperAgentState(dict):
    """LangGraph 状态类

    注意：继承 dict 以兼容 LangGraph 的 TypedDict 模式，
    同时提供属性访问的便利方法。
    """

    # ===== 输入 =====
    @property
    def user_query(self) -> str:
        return self.get("user_query", "")

    @user_query.setter
    def user_query(self, value: str):
        self["user_query"] = value

    # ===== 论文列表 =====
    @property
    def papers(self) -> List[Paper]:
        return self.get("papers", [])

    @papers.setter
    def papers(self, value: List[Paper]):
        self["papers"] = value

    @property
    def selected_papers(self) -> List[Paper]:
        return self.get("selected_papers", [])

    @selected_papers.setter
    def selected_papers(self, value: List[Paper]):
        self["selected_papers"] = value

    # ===== 大纲与写作 =====
    @property
    def outline(self) -> Dict[str, Any]:
        return self.get("outline", {})

    @outline.setter
    def outline(self, value: Dict[str, Any]):
        self["outline"] = value

    @property
    def draft(self) -> str:
        return self.get("draft", "")

    @draft.setter
    def draft(self, value: str):
        self["draft"] = value

    @property
    def feedback(self) -> List[str]:
        return self.get("feedback", [])

    @feedback.setter
    def feedback(self, value: List[str]):
        self["feedback"] = value

    # ===== 控制流 =====
    @property
    def iteration(self) -> int:
        return self.get("iteration", 0)

    @iteration.setter
    def iteration(self, value: int):
        self["iteration"] = value

    @property
    def max_iterations(self) -> int:
        return self.get("max_iterations", 3)

    @max_iterations.setter
    def max_iterations(self, value: int):
        self["max_iterations"] = value

    @property
    def current_phase(self) -> str:
        return self.get("current_phase", "crawl")

    @current_phase.setter
    def current_phase(self, value: str):
        self["current_phase"] = value

    # ===== 元数据 =====
    @property
    def session_id(self) -> str:
        return self.get("session_id", "")

    @session_id.setter
    def session_id(self, value: str):
        self["session_id"] = value

    @property
    def user_id(self) -> str:
        return self.get("user_id", "")

    @user_id.setter
    def user_id(self, value: str):
        self["user_id"] = value

    @property
    def timestamp(self) -> float:
        return self.get("timestamp", 0.0)

    @timestamp.setter
    def timestamp(self, value: float):
        self["timestamp"] = value

    # ===== 错误与日志 =====
    @property
    def errors(self) -> List[str]:
        return self.get("errors", [])

    @errors.setter
    def errors(self, value: List[str]):
        self["errors"] = value

    def add_error(self, error: str):
        self.setdefault("errors", []).append(error)


def create_initial_state(
    user_query: str,
    user_id: str = "",
    session_id: str = "",
    max_iterations: int = 3,
) -> PaperAgentState:
    """创建初始状态"""
    import time
    state = PaperAgentState()
    state.user_query = user_query
    state.user_id = user_id
    state.session_id = session_id
    state.max_iterations = max_iterations
    state.iteration = 0
    state.current_phase = "crawl"
    state.timestamp = time.time()
    state.papers = []
    state.selected_papers = []
    state.outline = {}
    state.draft = ""
    state.feedback = []
    state.errors = []
    return state
