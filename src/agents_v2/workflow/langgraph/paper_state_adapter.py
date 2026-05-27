"""
PaperState 适配层 - 连接 LangGraph State 与 Unified PaperState

提供 dict 状态与 PaperState dataclass 的双向转换，
使 UnifiedWorkflow 能够使用 PaperState 的丰富接口。
"""
from typing import Any, Dict, List, Optional
from dataclasses import asdict

from src.agents_v2.workflow.unified.state_model import (
    PaperState as UnifiedPaperState,
    PhaseResult,
    DiagnosticResult,
    QualityScore,
    ProblemType,
    PhaseStatus,
    QualityLevel,
)


def to_unified_paper_state(state: Dict[str, Any]) -> UnifiedPaperState:
    """
    将 LangGraph dict 状态转换为 UnifiedPaperState

    Args:
        state: LangGraph PaperAgentState dict

    Returns:
        UnifiedPaperState 实例
    """
    user_request = state.get("user_query", "")

    unified = UnifiedPaperState(user_request=user_request)

    # 基本属性映射
    if "current_phase" in state:
        unified.current_phase = state["current_phase"]

    if "iteration" in state:
        unified.iteration = state["iteration"]

    if "errors" in state:
        unified.errors = state["errors"]

    # context 映射到 unified.context
    unified.context.update({
        "papers": state.get("papers", []),
        "selected_papers": state.get("selected_papers", []),
        "outline": state.get("outline", {}),
        "draft": state.get("draft", ""),
        "feedback": state.get("feedback", []),
    })

    # HITL 状态
    unified.context["hitl_enabled"] = state.get("hitl_enabled", False)
    unified.context["hitl_decision"] = state.get("hitl_decision", "")
    unified.context["hitl_feedback"] = state.get("hitl_feedback", "")
    unified.context["hitl_stage"] = state.get("hitl_stage", "")

    # 诊断结果（如果有）
    diagnostic = state.get("diagnostic_result")
    if diagnostic:
        unified_problems = _parse_problems(diagnostic.get("problems", []))
        unified_diagnostic = DiagnosticResult(
            problems_found=unified_problems,
            severity=diagnostic.get("severity", {}),
            recommendations=diagnostic.get("recommendations", []),
            affected_phases=["diagnostic"]
        )
        unified.diagnostics["diagnostic"] = unified_diagnostic

        # 同步到 problems 列表
        unified.problems.extend(unified_problems)

    # 质量分数
    quality = state.get("quality_score")
    if quality:
        unified.context["quality_score"] = quality

    return unified


def _parse_problems(problem_values: List[str]) -> List[ProblemType]:
    """将字符串列表转换为 ProblemType 枚举列表"""
    result = []
    for p in problem_values:
        if isinstance(p, ProblemType):
            result.append(p)
        elif isinstance(p, str):
            try:
                result.append(ProblemType(p))
            except ValueError:
                pass  # 忽略无法解析的问题类型
    return result


def from_unified_paper_state(unified: UnifiedPaperState) -> Dict[str, Any]:
    """
    将 UnifiedPaperState 转换回 LangGraph dict 状态

    Args:
        unified: UnifiedPaperState 实例

    Returns:
        可用于 LangGraph 的 dict 状态
    """
    state = {}

    # 基本属性
    state["user_query"] = unified.user_request
    state["current_phase"] = unified.current_phase or "diagnostic"
    state["iteration"] = unified.iteration
    state["errors"] = unified.errors

    # context 展开
    state["papers"] = unified.context.get("papers", [])
    state["selected_papers"] = unified.context.get("selected_papers", [])
    state["outline"] = unified.context.get("outline", {})
    state["draft"] = unified.context.get("draft", "")
    state["feedback"] = unified.context.get("feedback", [])

    # HITL 状态
    state["hitl_enabled"] = unified.context.get("hitl_enabled", False)
    state["hitl_decision"] = unified.context.get("hitl_decision", "")
    state["hitl_feedback"] = unified.context.get("hitl_feedback", "")
    state["hitl_stage"] = unified.context.get("hitl_stage", "")

    # 质量分数
    if unified.quality_history:
        latest = unified.quality_history[-1]
        state["quality_score"] = latest.score

    return state


def create_langgraph_state(
    user_query: str,
    enable_hitl: bool = False,
    max_iterations: int = 3,
) -> Dict[str, Any]:
    """
    创建初始 LangGraph 状态（与 PaperAgentState 兼容）

    这是 create_initial_state 的别名，保持接口一致性
    """
    from src.agents_v2.langgraph_workflow.state import create_initial_state

    return create_initial_state(
        user_query=user_query,
        max_iterations=max_iterations,
        hitl_enabled=enable_hitl,
    )


def extract_diagnostic_from_state(state: Dict[str, Any]) -> Optional[DiagnosticResult]:
    """
    从 LangGraph state 中提取诊断结果

    Args:
        state: LangGraph 状态 dict

    Returns:
        DiagnosticResult 或 None
    """
    problems = state.get("diagnostic_problems", [])
    if not problems:
        return None

    severity = state.get("diagnostic_severity", {})
    recommendations = state.get("diagnostic_recommendations", [])

    unified_problems = _parse_problems(problems if isinstance(problems, list) else [])

    return DiagnosticResult(
        problems_found=unified_problems,
        severity=severity,
        recommendations=recommendations if isinstance(recommendations, list) else [],
        affected_phases=["diagnostic"]
    )


def check_quality_threshold(
    quality_score: float,
    threshold: float = 0.6,
) -> bool:
    """
    检查质量分数是否达到阈值

    Args:
        quality_score: 质量分数 (0-1 scale)
        threshold: 阈值，默认 0.6

    Returns:
        True if quality_score >= threshold
    """
    return quality_score >= threshold


def build_quality_result(
    score: float,
    details: str = "",
) -> QualityScore:
    """
    构建 QualityScore 对象

    Args:
        score: 质量分数 (0-1 scale)
        details: 评分详情

    Returns:
        QualityScore 实例
    """
    if score >= 0.9:
        level = QualityLevel.EXCELLENT
    elif score >= 0.7:
        level = QualityLevel.GOOD
    elif score >= 0.5:
        level = QualityLevel.ACCEPTABLE
    else:
        level = QualityLevel.POOR

    return QualityScore(score=score, level=level, details=details)