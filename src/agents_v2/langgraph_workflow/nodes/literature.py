"""
Literature Node - LangGraph 工作流节点

对应 MasterSupervisor 的 literature 阶段：
- 多源文献搜索
- 质量筛选
- PDF阅读与信息提取
- 识别研究空白
"""
from src.agents_v2.logging_config import get_logging_logger

import time
import os
from typing import Any, Dict, Optional

from ..state import PaperAgentState

logger = get_logging_logger(__name__)

# Literature 阶段质量阈值
LITERATURE_QUALITY_THRESHOLD = 0.7


def _get_llm_config():
    """获取 LLM 配置"""
    from src.agents_v2.config import LLMConfig

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


class LiteratureNode:
    """文献节点 - 调用 LiteratureAgent"""

    def __init__(self, llm=None):
        self.llm = llm

    async def _run_literature_agent(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """运行 LiteratureAgent 进行文献搜索和筛选"""
        try:
            from src.agents_v2.paper_agents.literature_agent import LiteratureAgent

            llm_config = _get_llm_config()
            agent = LiteratureAgent(llm_config=llm_config)
            result = await agent.execute({
                "topic": query,
                "topic_result": context.get("topic_result", {})
            }, context)

            return {
                "success": result.success,
                "literature_result": result.result,
                "papers": result.result.get("papers", []) if result.result else [],
                "quality_score": result.quality_score / 10.0 if result.quality_score else 0,
                "error": result.error
            }
        except Exception as e:
            logger.warning(f"Literature agent failed: {e}")
            return {
                "success": False,
                "literature_result": None,
                "papers": [],
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
        logger.info(f"[Literature] 开始文献搜索，query={query[:50]}...")
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
            "papers": state.get("papers", []),
            "diagnostic_result": state.get("diagnostic_result", {}),
            "hitl_feedback": state.get("hitl_feedback", ""),
        }

        # 运行文献 Agent
        result = loop.run_until_complete(self._run_literature_agent(query, context))

        # 更新论文列表
        if result.get("papers"):
            existing_ids = {p.id for p in state.get("papers", [])}
            new_papers = [p for p in result["papers"] if p.id not in existing_ids]
            state["papers"] = state.get("papers", []) + new_papers

        # 存储结果
        state["literature_result"] = result.get("literature_result")
        state["literature_quality_score"] = result.get("quality_score", 0)
        state["literature_recommendations"] = result.get("recommendations", [])

        elapsed = time.time() - start
        papers_list = result.get("papers") or []
        logger.info(
            f"[Literature] 文献搜索完成: {len(papers_list)} 篇论文, "
            f"quality_score={result.get('quality_score', 0):.3f}, 耗时 {elapsed:.2f}s"
        )

        state["current_phase"] = "literature"
        return state

    def get_quality_threshold(self) -> float:
        """获取文献阶段质量阈值"""
        return LITERATURE_QUALITY_THRESHOLD

    def is_quality_passed(self, state: PaperAgentState) -> bool:
        """检查文献质量是否通过"""
        quality_score = state.get("literature_quality_score", 0)
        return quality_score >= self.get_quality_threshold()


# 全局实例
_literature_node: Optional[LiteratureNode] = None


def get_literature_node(llm=None) -> LiteratureNode:
    """获取 LiteratureNode 全局实例"""
    global _literature_node
    if _literature_node is None:
        _literature_node = LiteratureNode(llm=llm)
    return _literature_node