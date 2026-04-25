"""补充搜索节点 - Critique后的额外搜索"""
from typing import Dict, Any
import logging

from src.core.state_model import State

logger = logging.getLogger(__name__)


async def additional_search_node(state: State) -> State:
    """
    补充搜索节点 - 根据Critique结果补充搜索

    从 critique_result.suggested_queries 中获取补充查询，
    执行额外搜索以填补研究空白。
    """
    try:
        current_state = state["value"]
        critique_result = current_state.metadata.get("critique_result", {}) if current_state.metadata else {}

        suggested_queries = critique_result.get("suggested_queries", [])
        missing_topics = critique_result.get("missing_topics", [])

        if not suggested_queries:
            logger.info("No additional queries suggested, skipping additional search")
            return state

        logger.info(f"Additional search for: {suggested_queries[:3]}...")

        # 记录补充搜索的查询
        if "additional_queries" not in current_state.metadata:
            current_state.metadata["additional_queries"] = []

        current_state.metadata["additional_queries"].extend(suggested_queries[:5])  # 限制最多5个

        # TODO: 实现实际的补充搜索逻辑
        # 这里可以调用现有的搜索流程，传入补充查询
        # 搜索结果应该合并到现有论文列表中

        logger.info(f"Additional queries recorded: {len(suggested_queries[:5])}")

        return state

    except Exception as e:
        logger.error(f"Additional search node failed: {e}")
        return state