"""
Diagnostic Node - LangGraph 工作流节点

在论文写作前进行问题诊断，调用问题导向 Agent 识别选题、文献、方法等方面的问题。
diagnostic 作为守门员，必须通过质量阈值才能进入 outline/writing 阶段。
"""
from src.agents_v2.logging_config import get_logging_logger

import time
import os
from typing import Any, Dict, List, Optional, Tuple

from ..state import PaperAgentState

logger = get_logging_logger(__name__)


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


# 诊断相关的问题类型
TOPIC_PROBLEMS = ["topic_vague", "topic_too_broad", "topic_lack_novelty"]
LITERATURE_PROBLEMS = ["literature_insufficient", "literature_one_sided", "gap_not_identified"]
METHOD_PROBLEMS = ["method_inappropriate", "method_not_rigorous"]
ARGUMENT_PROBLEMS = ["argument_weak", "logic_incoherent"]
CONTENT_PROBLEMS = ["abstract_repeats_conclusion", "discussion_shallow"]
FORMAT_PROBLEMS = ["chart_poor", "language_poor", "plagiarism_risk"]

# 质量阈值
DIAGNOSTIC_QUALITY_THRESHOLD = 0.6


class DiagnosticNode:
    """诊断节点 - 调用问题导向Agent"""

    def __init__(self, llm=None):
        self.llm = llm

    async def _run_diagnostic_agents(self, user_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行诊断 Agent（问题导向）

        Returns:
            dict with keys: problems, severity, recommendations, quality_score
        """
        from src.agents_v2.problem_oriented.base_problem_agent import AgentOutput

        agents_results = []
        quality_scores = []

        # 选题诊断
        topic_result = await self._diagnose_topic(user_query, context)
        if topic_result:
            agents_results.append(("topic", topic_result))
            quality_scores.append(topic_result.quality_score)

        # 文献诊断
        literature_result = await self._diagnose_literature(user_query, context)
        if literature_result:
            agents_results.append(("literature", literature_result))
            quality_scores.append(literature_result.quality_score)

        # 方法诊断
        method_result = await self._diagnose_methodology(user_query, context)
        if method_result:
            agents_results.append(("methodology", method_result))
            quality_scores.append(method_result.quality_score)

        # 汇总诊断结果
        all_problems = []
        all_severity = {}
        all_recommendations = []

        for agent_name, result in agents_results:
            if result.diagnosed_issues:
                all_problems.extend(result.diagnosed_issues)
                for issue in result.diagnosed_issues:
                    all_severity[issue] = result.quality_score / 10.0  # 转换为 0-1
            if result.recommendations:
                all_recommendations.extend(result.recommendations)

        # 计算综合质量分
        avg_quality = sum(quality_scores) / len(quality_scores) / 10.0 if quality_scores else 0.0

        return {
            "problems": all_problems,
            "severity": all_severity,
            "recommendations": list(set(all_recommendations)),
            "quality_score": avg_quality,
            "agent_results": {name: {"success": r.success, "quality": r.quality_score}
                             for name, r in agents_results}
        }

    async def _diagnose_topic(self, user_query: str, context: Dict[str, Any]) -> Optional[Any]:
        """诊断选题问题"""
        try:
            from src.agents_v2.problem_oriented.topic_refiner import TopicRefinerAgent

            llm_config = _get_llm_config()
            agent = TopicRefinerAgent(llm_config=llm_config)
            result = await agent.diagnose({"topic": user_query}, context)
            return result
        except Exception as e:
            logger.warning(f"Topic diagnostic failed: {e}")
            return None

    async def _diagnose_literature(self, user_query: str, context: Dict[str, Any]) -> Optional[Any]:
        """诊断文献问题"""
        try:
            from src.agents_v2.problem_oriented.literature_mapper import LiteratureMapperAgent

            llm_config = _get_llm_config()
            agent = LiteratureMapperAgent(llm_config=llm_config)
            result = await agent.diagnose({
                "topic": user_query,
                "papers": context.get("papers", [])
            }, context)
            return result
        except Exception as e:
            logger.warning(f"Literature diagnostic failed: {e}")
            return None

    async def _diagnose_methodology(self, user_query: str, context: Dict[str, Any]) -> Optional[Any]:
        """诊断方法问题"""
        try:
            from src.agents_v2.problem_oriented.methodology_advisor import MethodologyAdvisorAgent

            llm_config = _get_llm_config()
            agent = MethodologyAdvisorAgent(llm_config=llm_config)
            result = await agent.diagnose({
                "topic": user_query,
                "literature": context.get("selected_papers", [])
            }, context)
            return result
        except Exception as e:
            logger.warning(f"Methodology diagnostic failed: {e}")
            return None

    def _check_topic_problems(self, problems: List[str]) -> Tuple[bool, List[str]]:
        """
        检查是否有选题相关问题

        Returns:
            (has_topic_problem, topic_problem_list)
        """
        topic_found = []
        for p in problems:
            if p in TOPIC_PROBLEMS:
                topic_found.append(p)
        return len(topic_found) > 0, topic_found

    def _should_interrupt_for_topic(self, problems: List[str], severity: Dict[str, float]) -> bool:
        """
        判断是否因选题问题触发 HITL 中断

        规则：选题问题严重度 >= 0.7 时触发
        """
        for p in problems:
            if p in TOPIC_PROBLEMS:
                sev = severity.get(p, 0)
                if sev >= 0.7:
                    return True
        return False

    def execute(self, state: PaperAgentState) -> PaperAgentState:
        """
        LangGraph 节点入口（同步包装）

        Args:
            state: PaperAgentState (dict subclass)

        Returns:
            更新后的 state
        """
        query = state.user_query
        logger.info(f"[Diagnostic] 开始诊断，query={query[:50]}...")
        start = time.time()

        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 构建上下文
        context = {
            "papers": state.get("papers", []),
            "selected_papers": state.get("selected_papers", []),
            "outline": state.get("outline", {}),
            "draft": state.get("draft", ""),
        }

        # 运行诊断
        diag_result = loop.run_until_complete(self._run_diagnostic_agents(query, context))

        # 存储诊断结果
        state["diagnostic_result"] = {
            "problems": diag_result["problems"],
            "severity": diag_result["severity"],
            "recommendations": diag_result["recommendations"],
            "quality_score": diag_result["quality_score"],
            "agent_results": diag_result["agent_results"]
        }

        # 检查是否有选题问题
        has_topic_prob, topic_problems = self._check_topic_problems(diag_result["problems"])

        if has_topic_prob:
            state["topic_problems"] = topic_problems
            state["topic_problems_severity"] = {
                p: diag_result["severity"].get(p, 0)
                for p in topic_problems
            }
            logger.info(f"[Diagnostic] 发现选题问题: {topic_problems}")

            # 检查是否需要 HITL 中断
            should_interrupt = self._should_interrupt_for_topic(
                diag_result["problems"],
                diag_result["severity"]
            )
            if should_interrupt:
                state["hitl_triggered"] = True
                state["hitl_stage"] = "diagnostic_topic"
                state["hitl_reason"] = f"选题问题严重: {topic_problems}"
                logger.info(f"[Diagnostic] 选题问题严重度 >= 0.7，触发 HITL")

        elapsed = time.time() - start
        logger.info(
            f"[Diagnostic] 诊断完成: {len(diag_result['problems'])} 个问题, "
            f"质量分={diag_result['quality_score']:.3f}, 耗时 {elapsed:.2f}s"
        )

        state["current_phase"] = "diagnostic"
        return state

    def get_quality_threshold(self) -> float:
        """获取诊断质量阈值"""
        return DIAGNOSTIC_QUALITY_THRESHOLD

    def is_quality_passed(self, state: PaperAgentState) -> bool:
        """检查诊断质量是否通过"""
        diag_result = state.get("diagnostic_result", {})
        quality_score = diag_result.get("quality_score", 0)
        return quality_score >= self.get_quality_threshold()


# 全局实例
_diagnostic_node: Optional[DiagnosticNode] = None


def get_diagnostic_node(llm=None) -> DiagnosticNode:
    """获取 DiagnosticNode 全局实例"""
    global _diagnostic_node
    if _diagnostic_node is None:
        _diagnostic_node = DiagnosticNode(llm=llm)
    return _diagnostic_node