"""
Methodology Node - LangGraph 工作流节点

对应 MasterSupervisor 的 methodology 阶段：
- 推荐适合的研究方法
- 检查方法论严谨性
- 辅助统计/数据分析
- 识别方法漏洞
"""
from src.agents_v2.logging_config import get_logging_logger

import time
import os
from typing import Any, Dict, Optional

from ..state import PaperAgentState

logger = get_logging_logger(__name__)

# Methodology 阶段质量阈值
METHODOLOGY_QUALITY_THRESHOLD = 0.7


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


class MethodologyNode:
    """方法论节点 - 调用 MethodologyAdvisorAgent"""

    def __init__(self, llm=None):
        self.llm = llm

    async def _run_methodology_agent(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """运行 MethodologyAdvisorAgent 进行方法论指导"""
        try:
            from src.agents_v2.problem_oriented.methodology_advisor import MethodologyAdvisorAgent

            llm_config = _get_llm_config()
            agent = MethodologyAdvisorAgent(llm_config=llm_config)

            # 从 context 获取已诊断的问题作为 proposed_method
            diagnostic_result = context.get("diagnostic_result", {})
            diagnosed_problems = diagnostic_result.get("diagnosed_issues", [])
            proposed_method = "; ".join(diagnosed_problems) if diagnosed_problems else query

            logger.info(f"[Methodology] diagnostic_problems={diagnosed_problems}, proposed_method={proposed_method[:100]}...")

            result = await agent.diagnose({
                "topic": query,
                "proposed_method": proposed_method,
                "literature": context.get("selected_papers", [])
            }, context)

            logger.info(f"[Methodology] Agent result: success={result.success}, quality_score={result.quality_score}, "
                           f"recommended_methods_count={len(result.result.get('recommended_methods', [])) if result.result else 0}")

            return {
                "methodology_success": result.success,
                "methodology_result": result.result,
                "quality_score": result.quality_score / 10.0 if result.quality_score else 0,
                "recommendations": result.recommendations or [],
                "diagnosed_issues": result.diagnosed_issues or [],
                "error": result.error
            }
        except RuntimeError as e:
            logger.warning(f"Methodology agent RuntimeError: {e}")
            return {
                "methodology_success": False,
                "methodology_result": None,
                "quality_score": 0.0,
                "recommendations": [],
                "diagnosed_issues": [],
                "error": str(e)
            }
        except Exception as e:
            logger.warning(f"Methodology agent failed: {e}")
            return {
                "methodology_success": False,
                "methodology_result": None,
                "quality_score": 0.0,
                "recommendations": [],
                "diagnosed_issues": [],
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
        logger.info(f"[Methodology] 开始方法论分析，query={query[:50]}...")
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
            "papers": state.get("papers", []),
            "selected_papers": state.get("selected_papers", []),
            "diagnostic_result": state.get("diagnostic_result", {}),
        }

        # 运行方法论 Agent
        result = loop.run_until_complete(self._run_methodology_agent(query, context))

        # 存储结果
        state["methodology_success"] = result.get("methodology_success", False)
        state["methodology_result"] = result.get("methodology_result")
        state["methodology_quality_score"] = result.get("quality_score", 0)
        state["methodology_recommendations"] = result.get("recommendations", [])
        state["methodology_issues"] = result.get("diagnosed_issues", [])

        elapsed = time.time() - start
        logger.info(
            f"[Methodology] 方法论分析完成: quality_score={result.get('quality_score', 0):.3f}, "
            f"issues={len(result.get('diagnosed_issues', []))}, 耗时 {elapsed:.2f}s"
        )

        state["current_phase"] = "methodology"
        return state

    def get_quality_threshold(self) -> float:
        """获取方法论阶段质量阈值"""
        return METHODOLOGY_QUALITY_THRESHOLD

    def is_quality_passed(self, state: PaperAgentState) -> bool:
        """检查方法论质量是否通过"""
        quality_score = state.get("methodology_quality_score", 0)
        return quality_score >= self.get_quality_threshold()


# 全局实例
_methodology_node: Optional[MethodologyNode] = None


def get_methodology_node(llm=None) -> MethodologyNode:
    """获取 MethodologyNode 全局实例"""
    global _methodology_node
    if _methodology_node is None:
        _methodology_node = MethodologyNode(llm=llm)
    return _methodology_node