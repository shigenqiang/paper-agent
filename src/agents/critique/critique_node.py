"""Critique 节点 - LangGraph集成"""
from typing import Dict, Any
import logging

from src.agents.critique.critique_agent import CritiqueAgent, CritiqueResult
from src.core.state_model import State

logger = logging.getLogger(__name__)


# 全局 Critique Agent 实例
_critique_agent = CritiqueAgent()


async def critique_node(state: State) -> State:
    """
    Critique 节点 - 多视角评审研究结果

    流程：
    1. 从当前状态提取研究信息
    2. 调用 Critique Agent 进行多视角评审
    3. 将评审结果存入状态
    4. 根据评分决定是否需要补充搜索
    """
    try:
        current_state = state["value"]
        current_state.current_step = "critique"

        # 提取信息
        query = current_state.search_state.query if current_state.search_state else ""
        papers = current_state.papers_content.extracted_data if current_state.papers_content else []
        themes = []
        research_gaps = []
        contradictions = []

        if current_state.analysis_result:
            # 尝试从分析结果中提取更多信息
            if hasattr(current_state.analysis_result, 'topic_clusters'):
                themes = [
                    {"name": name, "papers": papers}
                    for name, papers in (current_state.analysis_result.topic_clusters or {}).items()
                ]
            if hasattr(current_state.analysis_result, 'research_gaps'):
                research_gaps = current_state.analysis_result.research_gaps or []
            if hasattr(current_state.analysis_result, 'contradictions'):
                contradictions = current_state.analysis_result.contradictions or []

        # 准备论文数据
        papers_data = []
        for paper in papers:
            if hasattr(paper, 'model_dump'):
                papers_data.append(paper.model_dump())
            else:
                papers_data.append(paper)

        logger.info(f"Starting critique for query: {query}, papers: {len(papers_data)}")

        # 执行 Critique
        critique_result = await _critique_agent.critique(
            query=query,
            papers=papers_data,
            themes=themes,
            research_gaps=research_gaps,
            contradictions=contradictions
        )

        logger.info(f"Critique completed: score={critique_result.score}, passed={critique_result.passed}")

        # 将结果存入状态
        current_state.metadata = current_state.metadata or {}
        current_state.metadata["critique_result"] = {
            "passed": critique_result.passed,
            "score": critique_result.score,
            "missing_topics": critique_result.missing_topics,
            "suggested_queries": critique_result.suggested_queries,
            "issues": critique_result.issues,
            "perspective_scores": critique_result.perspective_scores
        }

        # 记录迭代次数
        iteration = current_state.metadata.get("critique_iteration", 0) + 1
        current_state.metadata["critique_iteration"] = iteration

        return {"value": current_state}

    except Exception as e:
        logger.error(f"Critique node failed: {e}")
        state["value"].error.error = f"Critique failed: {str(e)}"
        return state


def should_iterate(state: State) -> str:
    """
    判断是否需要补充搜索

    Returns:
        "additional_search" - 需要补充搜索
        "writing" - 通过Critique，进入写作阶段
    """
    try:
        current_state = state["value"]
        critique_result = current_state.metadata.get("critique_result", {}) if current_state.metadata else {}

        passed = critique_result.get("passed", False)
        iteration = current_state.metadata.get("critique_iteration", 0) if current_state.metadata else 0
        max_iterations = current_state.metadata.get("max_critique_iterations", 3) if current_state.metadata else 3

        if not passed and iteration < max_iterations:
            logger.info(f"Critique not passed, iteration {iteration}/{max_iterations}, requesting additional search")
            return "additional_search"

        logger.info(f"Critique passed or max iterations reached, proceeding to writing")
        return "writing"

    except Exception as e:
        logger.error(f"Error in should_iterate: {e}")
        return "writing"


def has_critique_gaps(state: State) -> bool:
    """检查是否有评审发现需要补充"""
    try:
        current_state = state["value"]
        critique_result = current_state.metadata.get("critique_result", {}) if current_state.metadata else {}

        return (
            not critique_result.get("passed", True) and
            len(critique_result.get("suggested_queries", [])) > 0
        )
    except:
        return False