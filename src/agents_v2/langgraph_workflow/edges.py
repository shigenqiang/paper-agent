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
    from src.agents_v2.logging_config import get_logging_logger
    logger = get_logging_logger(__name__)

    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 3)
    feedback = state.get("feedback", [])
    score = state.get("evaluation_score", 0.0)
    last_score = state.get("last_evaluation_score", 0.0)

    # 达到最大迭代次数
    if iteration >= max_iterations:
        return "done"

    # 质量达标（评估分数 >= 6.0）
    if score >= 6.0:
        return "done"

    # 早期停止：如果分数没有提升（improvement < 0.1），停止迭代
    # 注意：last_score在首次评估时为0.0，此时improvement=score > 0.1，应该继续
    # 只有当分数维持在低位（如5.8）且无提升时才停止
    if last_score > 0:  # 确保不是首次评估
        improvement = score - last_score
        if improvement < 0.1:
            logger.info(f"[Edges] 早期停止：分数无提升 ({last_score:.2f} -> {score:.2f}, 提升 {improvement:.2f})")
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
    - 诊断完成后直接进入 topic（跳过迭代）
    - 有选题问题且严重度 >= TOPIC_SEVERITY_THRESHOLD: 触发 HITL 中断

    Args:
        state: 包含 diagnostic_result 的状态

    Returns:
        "topic" - 进入选题阶段
        "hitl_intervene" - 需要人工介入
    """
    # 检查是否有选题问题
    problems = state.get("diagnostic_result", {}).get("problems", [])
    severity = state.get("diagnostic_result", {}).get("severity", {})

    topic_problems = [p for p in problems if p in (
        "topic_vague", "topic_too_broad", "topic_lack_novelty"
    )]

    # 选题问题严重度检查
    for p in topic_problems:
        sev = severity.get(p, 0)
        if sev >= TOPIC_SEVERITY_THRESHOLD:
            return "hitl_intervene"

    # 直接进入选题阶段（不迭代诊断）
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
