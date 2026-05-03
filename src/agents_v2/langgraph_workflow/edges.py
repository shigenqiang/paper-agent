"""
LangGraph 工作流边和条件路由

定义节点之间的连接和条件跳转逻辑。
注意：LangGraph 传入的 state 是普通 dict，不是 PaperAgentState。
"""

# 诊断质量阈值
DIAGNOSTIC_QUALITY_THRESHOLD = 0.6

# 选题问题严重度阈值，触发 HITL
TOPIC_SEVERITY_THRESHOLD = 0.7


def should_continue(state: dict) -> str:
    """审查后决定是否继续迭代

    Args:
        state: LangGraph 传入的普通 dict 状态

    Returns:
        "write" - 需要修改，回到写作节点
        "done" - 质量达标或达到最大迭代次数，结束
    """
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 3)
    feedback = state.get("feedback", [])

    # 达到最大迭代次数
    if iteration >= max_iterations:
        return "done"

    # 没有可操作的反馈
    if not feedback or all("good" in f.lower() for f in feedback):
        return "done"

    # 需要修改
    return "write"


def route_by_phase(state: dict) -> str:
    """根据当前阶段路由到下一个节点"""
    phase = state.get("current_phase", "")
    routing = {
        "crawl": "crawler",
        "select": "selector",
        "outline": "outline",
        "write": "writing",
        "review": "review",
    }
    return routing.get(phase, "done")


def route_by_intent(state: dict) -> str:
    """根据意图路由到不同的工作流路径

    Args:
        state: 包含 route_path 字段的状态

    Returns:
        工作流路径名称: "search", "writing", "report", "qa", "revision"
    """
    route_path = state.get("route_path", "search")

    # 路径映射
    valid_paths = ["search", "writing", "report", "qa", "revision"]

    if route_path in valid_paths:
        return route_path

    # 默认返回搜索路径
    return "search"


def diagnostic_quality_gate(state: dict) -> str:
    """
    诊断质量门禁 - 决定诊断后是否进入写作流程

    规则：
    - quality_score >= threshold: 进入 outline
    - 有选题问题且严重度 >= TOPIC_SEVERITY_THRESHOLD: 触发 HITL 中断
    - 其他情况: 根据质量决定继续或迭代

    Args:
        state: 包含 diagnostic_result 的状态

    Returns:
        "outline" - 质量达标，继续
        "hitl_intervene" - 需要人工介入
        "diagnostic_retry" - 质量不达标但可迭代
    """
    diagnostic = state.get("diagnostic_result", {})
    quality_score = diagnostic.get("quality_score", 0)

    # 检查是否有选题问题
    problems = diagnostic.get("problems", [])
    severity = diagnostic.get("severity", {})

    topic_problems = [p for p in problems if p in (
        "topic_vague", "topic_too_broad", "topic_lack_novelty"
    )]

    # 选题问题严重度检查
    for p in topic_problems:
        sev = severity.get(p, 0)
        if sev >= TOPIC_SEVERITY_THRESHOLD:
            return "hitl_intervene"

    # 质量达标 - 进入选题阶段
    if quality_score >= DIAGNOSTIC_QUALITY_THRESHOLD:
        return "topic"

    # 质量不达标但可迭代
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 3)
    if iteration < max_iterations:
        # 递增迭代计数，重新进入诊断
        state["iteration"] = iteration + 1
        state["diagnostic_retry"] = True
        return "diagnostic_retry"

    # 达到最大迭代，仍进入写作（降级处理）
    return "topic"


def is_hitl_interrupted(state: dict) -> bool:
    """
    检查是否触发 HITL 中断

    用于 LangGraph interrupt_after 配置
    """
    return state.get("hitl_triggered", False)


def get_hitl_stage(state: dict) -> str:
    """获取 HITL 中断阶段"""
    return state.get("hitl_stage", "")
