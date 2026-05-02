"""
Reviewer Agent - LangGraph 工作流节点

职责：
- 审查草稿质量
- 提供修改建议
- 控制迭代终止条件

集成现有的 ReviewerAgent (paper_agents/reviewer_agent.py)。
"""

from src.agents_v2.logging_config import get_logging_logger

import time
from typing import List

from ..state import PaperAgentState

logger = get_logging_logger(__name__)


class ReviewerAgent:
    """审查 Agent - LangGraph 节点"""

    def __init__(self, llm=None, min_quality_score: float = 0.6):
        """
        Args:
            llm: LangChain LLM 实例。如果为 None，使用规则审查。
            min_quality_score: 最低质量阈值，达到则停止迭代
        """
        self.llm = llm
        self.min_quality_score = min_quality_score

    def _rule_based_review(self, draft: str) -> List[str]:
        """基于规则的审查（无 LLM 时的回退方案）"""
        feedback = []

        if not draft:
            feedback.append("草稿为空，需要重新生成")
            return feedback

        # 检查长度
        word_count = len(draft.split())
        if word_count < 500:
            feedback.append(f"草稿过短（{word_count} 词），建议扩展到至少 1500 词")

        # 检查章节完整性
        section_count = draft.count("## ")
        if section_count < 3:
            feedback.append("章节数量不足，建议至少包含 5 个章节")

        # 检查引用格式
        if "[" not in draft or "]" not in draft:
            feedback.append("缺少文献引用，请添加 [Title, Year] 格式的引用")

        # 检查是否有分析性内容
        analysis_keywords = ["however", "although", "compared to", "in contrast", "limitation", "challenge"]
        has_analysis = any(kw in draft.lower() for kw in analysis_keywords)
        if not has_analysis:
            feedback.append("缺少批判性分析，请添加方法间的对比和局限性讨论")

        if not feedback:
            feedback.append("草稿质量良好，无需修改")

        return feedback

    async def _llm_review(self, draft: str) -> List[str]:
        """使用 LLM 进行深度审查"""
        if self.llm is None:
            return self._rule_based_review(draft)

        prompt = f"""You are an expert academic reviewer. Review the following survey draft and provide specific, constructive feedback.

Draft:
{draft[:5000]}

Please provide feedback on:
1. Content completeness and depth
2. Citation quality and integration
3. Critical analysis and comparison
4. Writing clarity and organization
5. Specific areas for improvement

Return a list of feedback points, each on a new line starting with "- ".
If the draft is good, return "The draft is good and requires no changes"."""

        try:
            from langchain_core.messages import HumanMessage

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            feedback = [
                line.lstrip("- ").strip()
                for line in content.split("\n")
                if line.strip().startswith("-") or (line.strip() and content == line)
            ]
            if not feedback and content:
                feedback = [content]
            return feedback
        except Exception as e:
            logger.warning(f"LLM 审查失败，使用规则审查: {e}")
            return self._rule_based_review(draft)

    def execute(self, state: PaperAgentState) -> PaperAgentState:
        """LangGraph 节点入口"""
        draft = state.draft
        logger.info(f"[Reviewer] 开始审查草稿，当前迭代: {state.iteration}/{state.max_iterations}")
        start = time.time()

        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        feedback = loop.run_until_complete(self._llm_review(draft))

        # 过滤正面反馈
        actionable_feedback = [
            f for f in feedback
            if "good" not in f.lower() or "no changes" not in f.lower()
        ]

        state.feedback = actionable_feedback
        state.iteration += 1

        elapsed = time.time() - start
        logger.info(
            f"[Reviewer] 审查完成，发现 {len(actionable_feedback)} 条建议，耗时 {elapsed:.2f}s"
        )
        return state
