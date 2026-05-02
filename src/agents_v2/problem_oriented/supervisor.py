"""
ProblemSupervisor - 问题导向论文写作协调者

协调各问题导向Agent工作：
1. 诊断阶段 - 并行运行诊断Agent
2. 写作阶段 - 根据诊断结果针对性写作
3. 完善阶段 - 多Agent协作润色
"""
from typing import Any, Dict, List, Optional

from src.agents_v2.logging_config import get_logging_logger

import asyncio

from .base_problem_agent import ProblemAgentBase, AgentOutput, LLMConfig
from .topic_refiner import TopicRefinerAgent
from .literature_mapper import LiteratureMapperAgent
from .methodology_advisor import MethodologyAdvisorAgent
from .argument_builder import ArgumentBuilderAgent
from .section_differentiator import SectionDifferentiatorAgent
from .discussion_deepener import DiscussionDeepenerAgent
from .chart_formatter import ChartFormatterAgent
from .language_polisher import LanguagePolisherAgent
from .plagiarism_checker import PlagiarismCheckerAgent

logger = get_logging_logger(__name__)


class ProblemSupervisor:
    """
    ProblemSupervisor - 问题导向论文写作协调者

    工作流程：
    1. 诊断阶段 - 识别论文写作中的问题
    2. 针对性处理 - 根据问题调用对应Agent
    3. 完善阶段 - 最终润色
    """

    # Agent分组
    DIAGNOSTIC_AGENTS = {
        "topic": TopicRefinerAgent,
        "literature": LiteratureMapperAgent,
        "methodology": MethodologyAdvisorAgent,
    }

    WRITING_AGENTS = {
        "argument": ArgumentBuilderAgent,
        "section_diff": SectionDifferentiatorAgent,
        "discussion": DiscussionDeepenerAgent,
    }

    POLISH_AGENTS = {
        "chart": ChartFormatterAgent,
        "language": LanguagePolisherAgent,
        "plagiarism": PlagiarismCheckerAgent,
    }

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        self.llm_config = llm_config or LLMConfig()
        self._init_agents()
        logger.info("ProblemSupervisor initialized")

    def _init_agents(self):
        """初始化所有Agent"""
        self.agents = {}

        # 诊断Agent
        for name, agent_cls in self.DIAGNOSTIC_AGENTS.items():
            self.agents[name] = agent_cls(self.llm_config)

        # 写作Agent
        for name, agent_cls in self.WRITING_AGENTS.items():
            self.agents[name] = agent_cls(self.llm_config)

        # 完善Agent
        for name, agent_cls in self.POLISH_AGENTS.items():
            self.agents[name] = agent_cls(self.llm_config)

    async def run_diagnostic_phase(self, user_input: Dict[str, Any]) -> Dict[str, AgentOutput]:
        """
        运行诊断阶段

        并行运行所有诊断Agent，识别问题
        """
        logger.info("Running diagnostic phase")

        tasks = []
        agent_names = []

        # 并行运行诊断Agent
        for name, agent in self.agents.items():
            if name in self.DIAGNOSTIC_AGENTS:
                task = agent.execute(user_input)
                tasks.append(task)
                agent_names.append(name)

        # 等待所有诊断完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 整理结果
        diagnostic_results = {}
        all_issues = []
        all_recommendations = []

        for name, result in zip(agent_names, results):
            if isinstance(result, Exception):
                logger.error(f"Agent {name} failed: {result}")
                diagnostic_results[name] = AgentOutput(
                    success=False,
                    result=None,
                    agent_name=name,
                    diagnosed_issues=[str(result)],
                    recommendations=[],
                    quality_score=0.0,
                    error=str(result)
                )
            else:
                diagnostic_results[name] = result
                all_issues.extend(result.diagnosed_issues)
                all_recommendations.extend(result.recommendations)

        return {
            "diagnostics": diagnostic_results,
            "all_issues": all_issues,
            "all_recommendations": list(set(all_recommendations))
        }

    async def run_writing_phase(
        self,
        content: Dict[str, Any],
        diagnostic_results: Dict[str, AgentOutput]
    ) -> Dict[str, AgentOutput]:
        """
        运行写作阶段

        根据诊断结果，调用写作Agent
        """
        logger.info("Running writing phase")

        writing_results = {}

        # 根据诊断结果选择性地运行写作Agent
        issues = set()
        for result in diagnostic_results.values():
            issues.update(result.diagnosed_issues)

        # 如果有论证逻辑问题，运行ArgumentBuilder
        if any("论证" in issue or "逻辑" in issue for issue in issues):
            result = await self.agents["argument"].execute({
                "thesis": content.get("thesis", ""),
                "arguments": content.get("arguments", []),
                "evidence": content.get("evidence", [])
            })
            writing_results["argument"] = result

        # 如果有摘要/结论重复问题，运行SectionDifferentiator
        if any("重复" in issue for issue in issues):
            result = await self.agents["section_diff"].execute({
                "sections": content.get("sections", {})
            })
            writing_results["section_diff"] = result

        # 如果有讨论薄弱问题，运行DiscussionDeepener
        if any("讨论" in issue for issue in issues):
            result = await self.agents["discussion"].execute({
                "results": content.get("results", ""),
                "discussion": content.get("discussion", ""),
                "literature": content.get("literature", [])
            })
            writing_results["discussion"] = result

        return writing_results

    async def run_polish_phase(
        self,
        content: Dict[str, Any],
        issues: List[str]
    ) -> Dict[str, AgentOutput]:
        """
        运行完善阶段

        图表、语言、查重检查
        """
        logger.info("Running polish phase")

        polish_results = {}
        tasks = []
        agent_names = []

        # 如果有图表问题
        if any("图表" in issue for issue in issues):
            task = self.agents["chart"].execute({
                "charts": content.get("charts", [])
            })
            tasks.append(task)
            agent_names.append("chart")

        # 如果有语言问题
        if any("语言" in issue or "语法" in issue for issue in issues):
            task = self.agents["language"].execute({
                "text": content.get("text", ""),
                "language": content.get("language", "zh")
            })
            tasks.append(task)
            agent_names.append("language")

        # 如果有查重问题
        if any("复制" in issue or "抄袭" in issue for issue in issues):
            task = self.agents["plagiarism"].execute({
                "text": content.get("text", ""),
                "cited_sources": content.get("cited_sources", [])
            })
            tasks.append(task)
            agent_names.append("plagiarism")

        # 如果没有特定问题，对全文进行语言润色和查重
        if not tasks:
            # 全面检查
            polish_tasks = [
                ("chart", self.agents["chart"].execute({"charts": content.get("charts", [])})),
                ("language", self.agents["language"].execute({
                    "text": content.get("full_text", content.get("text", "")),
                    "language": content.get("language", "zh")
                })),
                ("plagiarism", self.agents["plagiarism"].execute({
                    "text": content.get("full_text", content.get("text", "")),
                    "cited_sources": content.get("cited_sources", [])
                }))
            ]

            for name, task in polish_tasks:
                try:
                    result = await task
                    polish_results[name] = result
                except Exception as e:
                    logger.error(f"Polish agent {name} failed: {e}")

            return polish_results

        # 运行选择的Agent
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for name, result in zip(agent_names, results):
                if isinstance(result, Exception):
                    logger.error(f"Polish agent {name} failed: {result}")
                else:
                    polish_results[name] = result

        return polish_results

    async def run_full_pipeline(
        self,
        user_input: Dict[str, Any],
        content: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        运行完整流程

        Args:
            user_input: 用户输入（如研究兴趣、初步想法）
            content: 论文内容（如有）
        """
        logger.info("Running full pipeline")

        # Phase 1: 诊断
        diagnostic_results = await self.run_diagnostic_phase(user_input)

        # Phase 2: 写作（如果有内容）
        writing_results = {}
        if content:
            writing_results = await self.run_writing_phase(content, diagnostic_results["diagnostics"])

        # Phase 3: 完善（如果有内容）
        polish_results = {}
        if content:
            all_issues = diagnostic_results["all_issues"]
            polish_results = await self.run_polish_phase(content, all_issues)

        # 汇总结果
        return {
            "success": True,
            "diagnostics": {
                name: {
                    "success": r.success,
                    "issues": r.diagnosed_issues,
                    "recommendations": r.recommendations,
                    "quality_score": r.quality_score
                }
                for name, r in diagnostic_results["diagnostics"].items()
            },
            "writing": {
                name: {
                    "success": r.success,
                    "issues": r.diagnosed_issues,
                    "recommendations": r.recommendations,
                    "quality_score": r.quality_score
                }
                for name, r in writing_results.items()
            },
            "polish": {
                name: {
                    "success": r.success,
                    "issues": r.diagnosed_issues,
                    "recommendations": r.recommendations,
                    "quality_score": r.quality_score
                }
                for name, r in polish_results.items()
            },
            "overall_quality": self._calculate_overall_quality(
                diagnostic_results["diagnostics"],
                writing_results,
                polish_results
            ),
            "next_recommendations": self._get_next_recommendations(
                diagnostic_results["all_recommendations"],
                writing_results,
                polish_results
            )
        }

    def _calculate_overall_quality(
        self,
        diagnostics: Dict,
        writing: Dict,
        polish: Dict
    ) -> float:
        """计算整体质量分数"""
        all_results = list(diagnostics.values()) + list(writing.values()) + list(polish.values())
        if not all_results:
            return 0.0

        scores = [r.quality_score for r in all_results if hasattr(r, 'quality_score')]
        return round(sum(scores) / len(scores), 2) if scores else 0.0

    def _get_next_recommendations(
        self,
        diagnostic_recs: List[str],
        writing: Dict,
        polish: Dict
    ) -> List[str]:
        """获取下一步建议"""
        recommendations = list(set(diagnostic_recs))

        # 从writing和polish结果中添加建议
        for results in [writing, polish]:
            for result in results.values():
                if hasattr(result, 'recommendations'):
                    recommendations.extend(result.recommendations)

        # 去重并返回前5个
        seen = set()
        unique = []
        for r in recommendations:
            if r not in seen:
                seen.add(r)
                unique.append(r)

        return unique[:5]
