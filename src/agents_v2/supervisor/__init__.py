"""
Supervisor Agent - 任务协调与质量控制

职责：
1. 协调各Agent工作
2. 管理状态流转
3. 执行Validation Gate
4. 控制迭代
"""
from typing import Any, Dict, List, Optional
import json
import logging
import asyncio

from ..paper_agents.base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig
from ..paper_agents import (
    TopicAgent,
    LiteratureAgent,
    ThesisAgent,
    OutlineAgent,
    DraftWriterAgent,
    EditorAgent,
    ReviewerAgent
)

logger = logging.getLogger(__name__)


class SupervisorAgent(PaperAgentBase):
    """
    Supervisor - 任务协调与质量控制

    职责：
    1. 协调各Agent工作
    2. 管理状态流转
    3. 执行Validation Gate
    4. 控制迭代
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个学术写作项目的协调者。
你的职责是：
1. 协调多个Agent的工作
2. 管理研究流程
3. 确保输出质量
4. 控制迭代次数

请确保各Agent按正确的顺序执行，并在必要时进行迭代改进。"""
        super().__init__(
            name="supervisor_agent",
            llm_config=llm_config,
            description="论文写作流程协调者",
            system_prompt=system_prompt
        )

        # 初始化各Agent
        self.agents = {
            "topic": TopicAgent(llm_config),
            "literature": LiteratureAgent(llm_config),
            "thesis": ThesisAgent(llm_config),
            "outline": OutlineAgent(llm_config),
            "draft": DraftWriterAgent(llm_config),
            "editor": EditorAgent(llm_config),
            "reviewer": ReviewerAgent(llm_config)
        }

        # 配置
        self.max_iterations = 3
        self.quality_threshold = 7.0

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        执行完整的论文写作流程

        流程：
        1. TopicAgent - 主题选择
        2. LiteratureAgent - 文献工作
        3. ThesisAgent - 研究凝练 (与2并行)
        4. OutlineAgent - 大纲制定
        5. DraftWriterAgent - 分节撰写
        6. EditorAgent - 修订编辑
        7. ReviewerAgent - 最终审核
        """
        user_request = input_data.get("user_request", "")

        if not user_request:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Empty user request"
            )

        logger.info(f"Starting paper writing workflow for: {user_request}")

        # 初始化状态
        state = {
            "user_request": user_request,
            "iteration": 0,
            "phases_completed": []
        }

        try:
            # Phase 1: TopicAgent
            logger.info("Phase 1: Topic selection")
            topic_result = await self._run_agent("topic", {"user_request": user_request})
            if not topic_result.success:
                return topic_result

            state["topic"] = topic_result.result["selected_topic"]
            state["phases_completed"].append("topic")
            state["context"] = {"topic": state["topic"]}

            # Phase 2 & 3: LiteratureAgent + ThesisAgent (并行)
            logger.info("Phase 2 & 3: Literature collection + Thesis formulation (parallel)")
            lit_input = {"topic": state["topic"]}
            thesis_input = {"topic": state["topic"]}

            lit_result, thesis_result = await asyncio.gather(
                self._run_agent("literature", lit_input, state["context"]),
                self._run_agent("thesis", thesis_input, state["context"])
            )

            if not lit_result.success:
                logger.warning("LiteratureAgent failed, continuing...")
            else:
                state["literature_result"] = lit_result.result
                state["phases_completed"].append("literature")

            if not thesis_result.success:
                logger.warning("ThesisAgent failed, continuing...")
            else:
                state["thesis_statement"] = thesis_result.result["thesis_statement"]
                state["phases_completed"].append("thesis")

            state["context"].update({
                "literature_result": state.get("literature_result", {}),
                "thesis_statement": state.get("thesis_statement", "")
            })

            # Phase 4: OutlineAgent
            logger.info("Phase 4: Outline creation")
            outline_result = await self._run_agent("outline", {}, state["context"])
            if not outline_result.success:
                return outline_result

            state["outline"] = outline_result.result["outline"]
            state["phases_completed"].append("outline")
            state["context"]["outline"] = state["outline"]

            # Phase 5: DraftWriterAgent
            logger.info("Phase 5: Draft writing")
            draft_result = await self._run_agent("draft", {}, state["context"])
            if not draft_result.success:
                return draft_result

            state["full_draft"] = draft_result.result["full_draft"]
            state["phases_completed"].append("draft")
            state["context"]["full_draft"] = state["full_draft"]

            # Phase 6: EditorAgent
            logger.info("Phase 6: Editing")
            editor_result = await self._run_agent("editor", {}, state["context"])
            if not editor_result.success:
                return editor_result

            state["final_draft"] = editor_result.result["final_draft"]
            state["phases_completed"].append("editor")
            state["context"]["final_draft"] = state["final_draft"]

            # Phase 7: ReviewerAgent + 迭代
            logger.info("Phase 7: Review and iteration")
            review_result = await self._review_with_iteration(state)

            # 编译最终结果
            final_paper = state.get("final_draft", state.get("full_draft", ""))
            quality_score = review_result.result.get("quality_score", 0) if review_result.success else 5.0

            return AgentOutput(
                success=True,
                result={
                    "paper": final_paper,
                    "topic": state.get("topic", {}).get("title", ""),
                    "thesis": state.get("thesis_statement", ""),
                    "phases_completed": state["phases_completed"],
                    "quality_score": quality_score,
                    "review_result": review_result.result if review_result.success else {},
                    "iterations": state.get("iteration", 0) + 1
                },
                agent_name=self.name,
                reasoning=f"Paper writing completed with {len(state['phases_completed'])} phases",
                quality_score=quality_score / 10
            )

        except Exception as e:
            logger.error(f"Supervisor execution failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _run_agent(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """运行指定Agent"""
        agent = self.agents.get(agent_name)
        if not agent:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=f"Unknown agent: {agent_name}"
            )

        try:
            result = await agent.execute(input_data, context)
            return result
        except Exception as e:
            logger.error(f"Agent {agent_name} execution failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=agent_name,
                error=str(e)
            )

    async def _review_with_iteration(self, state: Dict[str, Any]) -> AgentOutput:
        """审核并迭代改进"""
        for iteration in range(self.max_iterations):
            state["iteration"] = iteration
            logger.info(f"Review iteration {iteration + 1}/{self.max_iterations}")

            # 运行ReviewerAgent
            review_result = await self._run_agent(
                "reviewer",
                {},
                {
                    "final_draft": state["final_draft"],
                    "thesis_statement": state.get("thesis_statement", ""),
                    "outline": state.get("outline", {})
                }
            )

            if not review_result.success:
                logger.warning("Review failed, continuing...")
                return review_result

            # 检查是否通过
            passed = review_result.result.get("passed", False)
            quality_score = review_result.result.get("quality_score", 0)

            logger.info(f"Review iteration {iteration + 1}: score={quality_score}, passed={passed}")

            if passed:
                return review_result

            # 如果不通过，进行迭代改进
            if iteration < self.max_iterations - 1:
                logger.info("Review not passed, iterating improvement...")

                # 获取反馈
                critiques = review_result.result.get("critiques", {})
                issues = []
                issues.extend(critiques.get("expert_review", {}).get("weaknesses", []))
                issues.extend(critiques.get("reviewer_review", {}).get("issues", []))

                # 重新编辑
                state["context"]["feedback"] = issues
                editor_result = await self._run_agent("editor", {}, state["context"])

                if editor_result.success:
                    state["final_draft"] = editor_result.result["final_draft"]
                    state["context"]["final_draft"] = state["final_draft"]

        # 达到最大迭代
        logger.warning(f"Max iterations ({self.max_iterations}) reached")
        return review_result


class ValidationGate:
    """验证门"""

    GATES = {
        "topic": {"min_score": 0.5},
        "literature": {"min_papers": 5, "min_gaps": 1},
        "thesis": {"required_fields": ["thesis_statement", "research_objectives"]},
        "outline": {"min_chapters": 5},
        "draft": {"min_words": 1000},
        "review": {"min_quality_score": 7.0}
    }

    @classmethod
    def validate(cls, phase: str, result: Dict[str, Any]) -> bool:
        """验证阶段结果"""
        gate = cls.GATES.get(phase, {})
        if not gate:
            return True

        # 检查分数
        if "min_score" in gate:
            score = result.get("quality_score", 0)
            if score < gate["min_score"]:
                return False

        # 检查论文数量
        if "min_papers" in gate:
            papers = result.get("papers", [])
            if len(papers) < gate["min_papers"]:
                return False

        return True
