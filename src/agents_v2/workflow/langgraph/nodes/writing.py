"""
Writing Node - LangGraph 工作流节点

对应 MasterSupervisor 的 writing 阶段：
- 生成论文大纲
- 按大纲撰写各章节
- 整合初稿
"""
from src.agents_v2.logging_config import get_logging_logger

import time
import os
from typing import Any, Dict, Optional

from ..state import PaperAgentState

logger = get_logging_logger(__name__)

# Writing 阶段质量阈值
WRITING_QUALITY_THRESHOLD = 0.7


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


class WritingNode:
    """写作节点 - 调用 OutlineAgent 和 DraftWriterAgent"""

    def __init__(self, llm=None):
        self.llm = llm

    async def _run_outline_agent(self, topic: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """运行 OutlineAgent 生成大纲"""
        try:
            from src.agents_v2.agents.paper.outline_agent import OutlineAgent

            llm_config = _get_llm_config()
            agent = OutlineAgent(llm_config=llm_config)
            result = await agent.execute({
                "task": "outline_generation",
                "topic": topic
            }, context)

            return {
                "success": result.success,
                "outline": result.result if result.result else {},
                "thesis_statement": result.result.get("thesis", "") if result.result else "",
                "quality_score": result.quality_score / 10.0 if result.quality_score else 0,
                "error": result.error
            }
        except Exception as e:
            logger.warning(f"Outline agent failed: {e}")
            return {
                "success": False,
                "outline": {},
                "thesis_statement": "",
                "quality_score": 0.0,
                "error": str(e)
            }

    async def _run_draft_agent(self, topic: str, outline: Dict, context: Dict[str, Any]) -> Dict[str, Any]:
        """运行 DraftWriterAgent 撰写初稿"""
        try:
            from src.agents_v2.agents.paper.draft_writer import DraftWriterAgent

            llm_config = _get_llm_config()
            agent = DraftWriterAgent(llm_config=llm_config)
            result = await agent.execute({
                "task": "draft_writing",
                "outline": outline
            }, context)

            # Debug: log the result
            logger.info(f"[Writing] draft_result success={result.success}, result={result.result}")

            return {
                "success": result.success,
                "draft": result.result.get("full_draft", "") if result.result else "",
                "quality_score": result.quality_score / 10.0 if result.quality_score else 0,
                "error": result.error
            }
        except Exception as e:
            logger.warning(f"Draft writer agent failed: {e}")
            return {
                "success": False,
                "draft": "",
                "quality_score": 0.0,
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
        topic = state.user_query
        logger.info(f"[Writing] 开始论文写作，topic={topic[:50]}...")
        start = time.time()

        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 构建上下文
        context = {
            "topic_result": state.get("topic_result", {}),
            "literature_result": state.get("literature_result", {}),
            "methodology_result": state.get("methodology_result", {}),
            "papers": state.get("papers", []),
            "selected_papers": state.get("selected_papers", []),
            "hitl_feedback": state.get("hitl_feedback", ""),
        }

        # 1. 生成大纲
        outline_result = loop.run_until_complete(self._run_outline_agent(topic, context))
        state["outline"] = outline_result.get("outline", {})
        state["thesis_statement"] = outline_result.get("thesis_statement", "")
        state["outline_score"] = outline_result.get("quality_score", 0)

        # 2. 撰写初稿
        if outline_result.get("success") and outline_result.get("outline"):
            # 将新生成的 outline 和 thesis 注入 context
            context["outline"] = outline_result["outline"]
            context["thesis_statement"] = outline_result.get("thesis_statement", "")

            draft_result = loop.run_until_complete(
                self._run_draft_agent(topic, outline_result["outline"], context)
            )
            state["draft"] = draft_result.get("draft", "")
            state["draft_score"] = draft_result.get("quality_score", 0)
            state["writing_success"] = draft_result.get("success", False)
        else:
            state["draft"] = ""
            state["draft_score"] = 0
            state["writing_success"] = False

        elapsed = time.time() - start
        total_score = (state.get("outline_score", 0) + state.get("draft_score", 0)) / 2

        logger.info(
            f"[Writing] 写作完成: outline_score={outline_result.get('quality_score', 0):.3f}, "
            f"draft_score={state.get('draft_score', 0):.3f}, "
            f"total={total_score:.3f}, 耗时 {elapsed:.2f}s"
        )

        state["current_phase"] = "writing"
        return state

    def get_quality_threshold(self) -> float:
        """获取写作阶段质量阈值"""
        return WRITING_QUALITY_THRESHOLD

    def is_quality_passed(self, state: PaperAgentState) -> bool:
        """检查写作质量是否通过"""
        total_score = (state.get("outline_score", 0) + state.get("draft_score", 0)) / 2
        return total_score >= self.get_quality_threshold()


# 全局实例
_writing_node: Optional[WritingNode] = None


def get_writing_node(llm=None) -> WritingNode:
    """获取 WritingNode 全局实例"""
    global _writing_node
    if _writing_node is None:
        _writing_node = WritingNode(llm=llm)
    return _writing_node