"""
Topic Node - LangGraph 工作流节点

对应 MasterSupervisor 的 topic 阶段：
- 分析研究领域
- 生成候选主题
- 评估可行性
- 凝练具体研究问题
"""
from src.agents_v2.logging_config import get_logging_logger

import time
import os
from typing import Any, Dict, Optional

from ..state import PaperAgentState

logger = get_logging_logger(__name__)

# Topic 阶段质量阈值
TOPIC_QUALITY_THRESHOLD = 0.7


def _get_llm_config():
    """获取 LLM 配置"""
    from src.agents_v2.core.config import LLMConfig

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.minimax.chat/v1")
    model_name = os.getenv("LLM_MODEL", "MiniMax-M2.7")

    return LLMConfig(
        provider="openai",
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.7,
        max_tokens=4096
    )


class TopicNode:
    """选题节点 - 调用 TopicAgent"""

    def __init__(self, llm=None):
        self.llm = llm

    async def _run_topic_agent(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """运行 TopicAgent 进行选题分析"""
        try:
            from src.agents_v2.agents.paper.topic_agent import TopicAgent

            llm_config = _get_llm_config()
            agent = TopicAgent(llm_config=llm_config)
            result = await agent.execute({"user_request": query}, context)

            return {
                "success": result.success,
                "topic_result": result.result,
                "quality_score": result.quality_score / 10.0 if result.quality_score else 0,  # 转换为 0-1
                "error": result.error
            }
        except Exception as e:
            logger.warning(f"Topic agent failed: {e}")
            return {
                "success": False,
                "topic_result": None,
                "quality_score": 0.0,
                "recommendations": [],
                "error": str(e)
            }

    def execute(self, state: PaperAgentState) -> PaperAgentState:
        """
        LangGraph 节点入口（同步包装）

        Args:
            state: PaperAgentState (dict subclass)

        Returns:
            更新后的 state
        """
        query = state.user_query
        logger.info(f"[Topic] 开始选题分析，query={query[:50]}...")
        start = time.time()

        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 构建上下文（包含 HITL 反馈等）
        context = {
            "hitl_feedback": state.get("hitl_feedback", ""),
            "topic_feedback": state.get("topic_feedback", ""),
            "papers": state.get("papers", []),
            "selected_papers": state.get("selected_papers", []),
            "diagnostic_result": state.get("diagnostic_result", {}),
        }

        # 运行选题 Agent
        result = loop.run_until_complete(self._run_topic_agent(query, context))

        # 存储结果
        state["topic_result"] = result.get("topic_result")
        state["topic_quality_score"] = result.get("quality_score", 0)
        state["topic_recommendations"] = result.get("recommendations", [])

        # 如果有 HITL 反馈，说明之前的选题被驳回，需要更新选题
        if context.get("topic_feedback") or context.get("hitl_feedback"):
            state["topic_needs_revision"] = True
            logger.info(f"[Topic] 根据人工反馈修订选题")

        elapsed = time.time() - start
        logger.info(
            f"[Topic] 选题完成: quality_score={result.get('quality_score', 0):.3f}, "
            f"success={result.get('success')}, 耗时 {elapsed:.2f}s"
        )

        state["current_phase"] = "topic"
        return state

    def get_quality_threshold(self) -> float:
        """获取选题质量阈值"""
        return TOPIC_QUALITY_THRESHOLD

    def is_quality_passed(self, state: PaperAgentState) -> bool:
        """检查选题质量是否通过"""
        quality_score = state.get("topic_quality_score", 0)
        return quality_score >= self.get_quality_threshold()


# 全局实例
_topic_node: Optional[TopicNode] = None


def get_topic_node(llm=None) -> TopicNode:
    """获取 TopicNode 全局实例"""
    global _topic_node
    if _topic_node is None:
        _topic_node = TopicNode(llm=llm)
    return _topic_node