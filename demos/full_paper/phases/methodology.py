"""
方法阶段 - 问题导向Agent指导

职责：
- 根据问题导向Agent的建议设计方法
- 指导研究方法选择
- 评估方法可行性
"""
import time
from typing import Any, Dict, Optional

from src.agents_v2.logging_config import get_logging_logger

from ..utils.config import PhaseConfig
from ..utils.output import PhaseOutput

logger = get_logging_logger(__name__)


class MethodologyPhase:
    """
    方法阶段 - 使用问题导向Agent

    职责：
    - 基于诊断结果设计研究方法
    - 提供方法论指导
    - 论证方法可行性
    """

    def __init__(self, config: Optional[PhaseConfig] = None):
        self.config = config or PhaseConfig(phase_name="methodology")
        self.agents = {}
        self._init_agents()

    def _init_agents(self):
        """初始化方法阶段Agent"""
        try:
            from src.agents_v2.problem_oriented import (
                MethodologyAdvisorAgent,
                ArgumentBuilderAgent,
            )
            self.agents["methodology_advisor"] = MethodologyAdvisorAgent(self.config.llm_config)
            self.agents["argument_builder"] = ArgumentBuilderAgent(self.config.llm_config)
            logger.debug("Methodology agents initialized")
        except ImportError as e:
            logger.warning(f"Could not import methodology agents: {e}")

    async def run(
        self,
        topic: Any,
        literature_result: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PhaseOutput:
        """
        运行方法阶段

        Args:
            topic: 研究主题
            literature_result: 文献阶段结果
            context: 上下文

        Returns:
            PhaseOutput: 方法设计结果输出
        """
        start_time = time.time()
        phase_name = "methodology"

        logger.info(f"[{phase_name}] Starting methodology design...")

        if not self.agents:
            return PhaseOutput(
                phase_name=phase_name,
                success=False,
                status="failed",
                error="No methodology agents available"
            )

        try:
            input_data = {
                "topic": topic,
                "literature_result": literature_result or {}
            }

            # 主要使用MethodologyAdvisorAgent
            advisor = self.agents.get("methodology_advisor")
            if not advisor:
                return PhaseOutput(
                    phase_name=phase_name,
                    success=False,
                    status="failed",
                    error="MethodologyAdvisorAgent not available"
                )

            result = await advisor.execute(input_data, context)

            # 提取结果
            if hasattr(result, 'success'):
                success = result.success
                result_dict = result.result if hasattr(result, 'result') else {}
                quality_score = result.quality_score if hasattr(result, 'quality_score') else 0.0
                error = result.error if hasattr(result, 'error') else None
            else:
                success = False
                result_dict = {}
                quality_score = 0.0
                error = "Unknown result format"

            if not success:
                return PhaseOutput(
                    phase_name=phase_name,
                    success=False,
                    status="failed",
                    error=error or "MethodologyAdvisorAgent execution failed",
                    execution_time=time.time() - start_time
                )

            # 生成输出文本
            methodology_text = self._format_methodology_output(result_dict, topic)

            execution_time = time.time() - start_time

            return PhaseOutput(
                phase_name=phase_name,
                success=True,
                status="completed",
                text=methodology_text,
                result=result_dict,
                quality_score=quality_score,
                quality_level=self._get_quality_level(quality_score),
                execution_time=execution_time
            )

        except Exception as e:
            logger.error(f"[{phase_name}] Phase failed: {type(e).__name__}: {e}")
            return PhaseOutput(
                phase_name=phase_name,
                success=False,
                status="failed",
                error=str(e),
                execution_time=time.time() - start_time
            )

    def _format_methodology_output(self, result: Dict[str, Any], topic: Any) -> str:
        """格式化方法论输出 - 与全链路一致"""
        lines = [
            "# 研究方法报告",
            "",
        ]

        topic_str = topic if isinstance(topic, str) else str(topic)
        lines.append(f"## 研究主题: {topic_str}")
        lines.append("")

        # 从结果中提取方法论信息
        # MethodologyAdvisorAgent.diagnose() 返回的 result 包含:
        # topic, research_type, proposed_method, recommended_methods, method_evaluation, rigor_issues, potential_problems

        research_type = result.get("research_type", "")
        if research_type:
            lines.append(f"**研究类型**: {research_type}")
            lines.append("")

        proposed_method = result.get("proposed_method", "")
        if proposed_method:
            lines.append(f"**提议方法**: {proposed_method}")
            lines.append("")

        # 推荐方法
        recommended_methods = result.get("recommended_methods", [])
        if recommended_methods:
            lines.append("## 推荐研究方法")
            lines.append("")
            for i, method in enumerate(recommended_methods, 1):
                if isinstance(method, dict):
                    name = method.get("name", "未知方法")
                    applicability = method.get("applicability", "")
                    pros = method.get("pros", "")
                    cons = method.get("cons", "")
                    lines.append(f"### {i}. {name}")
                    if applicability:
                        lines.append(f"- **适用场景**: {applicability}")
                    if pros:
                        lines.append(f"- **优点**: {pros}")
                    if cons:
                        lines.append(f"- **缺点**: {cons}")
                    lines.append("")
                elif isinstance(method, str):
                    lines.append(f"{i}. {method}")
            lines.append("")

        # 方法评估
        method_evaluation = result.get("method_evaluation", {})
        if isinstance(method_evaluation, dict) and method_evaluation:
            lines.append("## 方法评估")
            lines.append("")
            suitability = method_evaluation.get("suitability", "")
            feasibility = method_evaluation.get("feasibility", "")
            novelty = method_evaluation.get("novelty", "")
            suitable = method_evaluation.get("suitable", "")

            if suitability:
                lines.append(f"- **适合度**: {suitability}/10")
            if feasibility:
                lines.append(f"- **可行性**: {feasibility}/10")
            if novelty:
                lines.append(f"- **创新性**: {novelty}/10")
            if suitable:
                lines.append(f"- **是否适合**: {'是' if suitable else '否'}")
            lines.append("")

            pros = method_evaluation.get("pros", [])
            cons = method_evaluation.get("cons", [])
            risks = method_evaluation.get("risks", [])

            if pros:
                lines.append("**优点**:")
                for p in pros:
                    lines.append(f"- {p}")
                lines.append("")
            if cons:
                lines.append("**缺点**:")
                for c in cons:
                    lines.append(f"- {c}")
                lines.append("")
            if risks:
                lines.append("**潜在风险**:")
                for r in risks:
                    lines.append(f"- {r}")
                lines.append("")

        # 严谨性问题
        rigor_issues = result.get("rigor_issues", [])
        if rigor_issues:
            lines.append("## 方法严谨性问题")
            lines.append("")
            for issue in rigor_issues:
                lines.append(f"- {issue}")
            lines.append("")

        # 潜在问题
        potential_problems = result.get("potential_problems", [])
        if potential_problems:
            lines.append("## 潜在方法论问题")
            lines.append("")
            for problem in potential_problems:
                lines.append(f"- {problem}")
            lines.append("")

        return "\n".join(lines)

    def _get_quality_level(self, score: float) -> str:
        """获取质量等级"""
        if score >= 9.0:
            return "excellent"
        elif score >= 7.0:
            return "good"
        elif score >= 5.0:
            return "acceptable"
        return "poor"
