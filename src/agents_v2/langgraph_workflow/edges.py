"""
LangGraph 工作流边和条件路由

定义节点之间的连接和条件跳转逻辑。
注意：LangGraph 传入的 state 是普通 dict，不是 PaperAgentState。
"""


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
