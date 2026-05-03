"""
诊断阶段 - 问题导向Agent并行诊断

职责：
- 识别论文问题
- 评估问题严重程度
- 提供修复建议
"""
import time
from typing import Any, Dict, List, Optional

from src.agents_v2.logging_config import get_logging_logger

from ..utils.config import PhaseConfig
from ..utils.output import PhaseOutput

logger = get_logging_logger(__name__)


class DiagnosticPhase:
    """
    诊断阶段 - 并行运行多个诊断Agent

    使用问题导向Agent:
    - TopicRefinerAgent: 诊断选题问题
    - LiteratureMapperAgent: 诊断文献问题
    - MethodologyAdvisorAgent: 诊断方法问题
    """

    def __init__(self, config: Optional[PhaseConfig] = None):
        self.config = config or PhaseConfig(phase_name="diagnostic")
        self.agents = {}
        self._init_agents()

    def _init_agents(self):
        """初始化诊断Agent"""
        try:
            from src.agents_v2.problem_oriented import (
                TopicRefinerAgent,
                LiteratureMapperAgent,
                MethodologyAdvisorAgent,
            )
            self.agents["topic_refiner"] = TopicRefinerAgent(self.config.llm_config)
            self.agents["literature_mapper"] = LiteratureMapperAgent(self.config.llm_config)
            self.agents["methodology_advisor"] = MethodologyAdvisorAgent(self.config.llm_config)
            logger.debug("Diagnostic agents initialized")
        except ImportError as e:
            logger.warning(f"Could not import diagnostic agents: {e}")

    async def run(self, user_request: str, context: Optional[Dict[str, Any]] = None) -> PhaseOutput:
        """
        运行诊断阶段

        Args:
            user_request: 用户请求/主题
            context: 上下文

        Returns:
            PhaseOutput: 诊断结果输出
        """
        start_time = time.time()
        phase_name = "diagnostic"

        logger.info(f"[{phase_name}] Starting diagnostic phase for: {user_request[:50]}...")

        if not self.agents:
            return PhaseOutput(
                phase_name=phase_name,
                success=False,
                status="failed",
                error="No diagnostic agents available"
            )

        try:
            # 并行运行诊断Agent
            import asyncio
            tasks = []
            agent_names = []

            for name, agent in self.agents.items():
                task = self._run_agent(agent, user_request, context)
                tasks.append(task)
                agent_names.append(name)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 聚合结果
            all_issues: List[str] = []
            all_recommendations: List[str] = []
            total_quality = 0.0
            success_count = 0

            for i, result in enumerate(results):
                agent_name = agent_names[i]
                if isinstance(result, Exception):
                    logger.error(f"Agent {agent_name} failed: {result}")
                    continue

                if isinstance(result, dict) and result.get("success"):
                    success_count += 1
                    total_quality += result.get("quality_score", 0.0)
                    all_issues.extend(result.get("issues", []))
                    all_recommendations.extend(result.get("recommendations", []))

            avg_quality = total_quality / success_count if success_count > 0 else 0.0

            # 生成诊断报告
            diagnostic_report = self._generate_report(
                issues=all_issues,
                recommendations=all_recommendations,
                quality=avg_quality
            )

            execution_time = time.time() - start_time

            return PhaseOutput(
                phase_name=phase_name,
                success=success_count > 0,
                status="completed" if success_count > 0 else "failed",
                text=diagnostic_report,
                result={
                    "issues": all_issues,
                    "recommendations": all_recommendations,
                    "agents_run": agent_names,
                    "success_count": success_count
                },
                quality_score=avg_quality,
                quality_level=self._get_quality_level(avg_quality),
                issues=all_issues,
                recommendations=all_recommendations,
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

    async def _run_agent(
        self,
        agent,
        user_request: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """运行单个Agent"""
        try:
            input_data = {"user_request": user_request}
            if hasattr(agent, 'execute'):
                result = await agent.execute(input_data, context)
            else:
                result = await agent(input_data, context)

            if hasattr(result, 'result'):
                return {
                    "success": result.success,
                    "quality_score": result.quality_score or 0.0,
                    "issues": result.diagnosed_issues if hasattr(result, 'diagnosed_issues') else [],
                    "recommendations": result.recommendations if hasattr(result, 'recommendations') else [],
                    "output": result.result if hasattr(result, 'result') else None
                }
            return {"success": False, "error": "Unknown result format"}
        except Exception as e:
            logger.error(f"Agent run failed: {e}")
            return {"success": False, "error": str(e)}

    def _generate_report(self, issues: List[str], recommendations: List[str], quality: float) -> str:
        """生成诊断报告"""
        report_lines = [
            "# 诊断报告",
            "",
            f"## 质量评估: {quality:.2f}",
            "",
            "## 发现的问题",
        ]

        if issues:
            for i, issue in enumerate(issues, 1):
                report_lines.append(f"{i}. {issue}")
        else:
            report_lines.append("未发现明显问题")

        report_lines.append("")
        report_lines.append("## 改进建议")

        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                report_lines.append(f"{i}. {rec}")
        else:
            report_lines.append("当前状态良好，无需强制改进")

        return "\n".join(report_lines)

    def _get_quality_level(self, score: float) -> str:
        """获取质量等级"""
        if score >= 9.0:
            return "excellent"
        elif score >= 7.0:
            return "good"
        elif score >= 5.0:
            return "acceptable"
        return "poor"
