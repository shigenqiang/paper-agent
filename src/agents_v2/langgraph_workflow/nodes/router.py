"""
路由节点 - Route Node

功能：
1. 包装 LLMIntentClassifier 进行意图分类
2. 将用户查询路由到不同的工作流路径
3. 支持 11 种意图类型的识别

设计原则：
- 复用现有的 routing/llm_intent_classifier.py
- 将意图映射到工作流路径
- 保持状态不变，只添加路由信息
"""
from typing import Dict, Any

from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class RouteNode:
    """路由节点 - 意图分类与路由分发"""

    def __init__(self, llm_provider=None):
        """初始化路由节点

        Args:
            llm_provider: LLM 提供者（可选），用于智能意图分类
        """
        from ...routing.llm_intent_classifier import LLMIntentClassifier

        self.classifier = LLMIntentClassifier(
            llm_provider=llm_provider,
            fallback_keyword_matching=True
        )

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """同步执行入口（兼容 LangGraph 节点调用）

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.__call__(state))

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行路由分类

        Args:
            state: 当前状态

        Returns:
            更新后的状态，添加 intent 和 route_path 字段
        """
        user_query = state.get("user_query", "")

        # 如果外部已经设置了明确的 route_path，优先使用
        if state.get("_route_path_set") and state.get("route_path"):
            intent_str = state.get("intent", "unknown")
            route_path = state["route_path"]
            state["intent_confidence"] = 1.0
            state["suggested_agents"] = []
            logger.info(f"Using explicit route_path: {route_path} (intent: {intent_str})")
            return state

        if not user_query:
            logger.warning("Empty user query, defaulting to UNKNOWN intent")
            state["intent"] = "unknown"
            state["route_path"] = "search"
            return state

        try:
            # 使用分类器识别意图
            result = await self.classifier.classify(user_query)

            intent_str = result.primary_intent.value
            state["intent"] = intent_str
            state["intent_confidence"] = result.confidence
            state["suggested_agents"] = result.suggested_agents

            # 映射意图到工作流路径
            route_path = self._map_intent_to_route(intent_str)
            state["route_path"] = route_path

            logger.info(
                f"Routed query to '{route_path}' "
                f"(intent: {intent_str}, confidence: {result.confidence:.2f})"
            )

        except Exception as e:
            logger.error(f"Route classification failed: {e}")
            state["intent"] = "unknown"
            state["route_path"] = "search"
            state.setdefault("errors", []).append(f"Route error: {str(e)}")

        return state

    def _map_intent_to_route(self, intent: str) -> str:
        """将意图映射到工作流路径

        Args:
            intent: 意图类型字符串

        Returns:
            工作流路径名称
        """
        # 意图到路径的映射
        intent_route_map = {
            "literature_search": "search",
            "literature_review": "writing",
            "topic_select": "writing",
            "thesis_formulate": "writing",
            "outline_generate": "writing",
            "draft_write": "writing",
            "full_paper": "writing",
            "diagnostic": "qa",
            "question": "qa",
            "comparison": "qa",
            "unknown": "search"
        }

        return intent_route_map.get(intent, "search")
