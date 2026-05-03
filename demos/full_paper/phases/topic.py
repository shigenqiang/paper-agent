"""
选题阶段 - Pipeline型Agent

职责：
- 分析研究领域
- 生成候选主题
- 评估可行性
- 凝练具体研究问题
"""
import time
from typing import Any, Dict, Optional

from src.agents_v2.logging_config import get_logging_logger

from ..utils.config import PhaseConfig
from ..utils.output import PhaseOutput

logger = get_logging_logger(__name__)


class TopicPhase:
    """
    选题阶段 - 使用TopicAgent

    职责：
    - 分析研究领域
    - 生成候选主题
    - 评估可行性
    - 凝练具体研究问题
    """

    def __init__(self, config: Optional[PhaseConfig] = None):
        self.config = config or PhaseConfig(phase_name="topic")
        self.agent = None
        self._init_agent()

    def _init_agent(self):
        """初始化TopicAgent"""
        try:
            from src.agents_v2.paper_agents import TopicAgent
            self.agent = TopicAgent(self.config.llm_config)
            logger.debug("TopicAgent initialized")
        except ImportError as e:
            logger.warning(f"Could not import TopicAgent: {e}")

    async def run(self, user_request: str, context: Optional[Dict[str, Any]] = None) -> PhaseOutput:
        """
        运行选题阶段

        Args:
            user_request: 用户请求/主题
            context: 上下文

        Returns:
            PhaseOutput: 选题结果输出
        """
        start_time = time.time()
        phase_name = "topic"

        logger.info(f"[{phase_name}] Starting topic selection for: {user_request[:50]}...")

        if not self.agent:
            return PhaseOutput(
                phase_name=phase_name,
                success=False,
                status="failed",
                error="TopicAgent not available"
            )

        try:
            input_data = {"user_request": user_request}
            result = await self.agent.execute(input_data, context)

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
                    error=error or "TopicAgent execution failed",
                    execution_time=time.time() - start_time
                )

            # 提取选中的主题
            selected_topic = {}
            if isinstance(result_dict, dict):
                selected_topic = result_dict.get("selected_topic", {})
                if not selected_topic:
                    selected_topic = result_dict

            # 生成输出文本
            topic_text = self._format_topic_output(selected_topic, result_dict)

            execution_time = time.time() - start_time

            return PhaseOutput(
                phase_name=phase_name,
                success=True,
                status="completed",
                text=topic_text,
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

    def _format_topic_output(self, topic: Dict[str, Any], result: Optional[Dict[str, Any]] = None) -> str:
        """格式化主题输出 - 与全链路一致"""
        lines = [
            "# 选题报告",
            "",
        ]

        title = topic.get("title", "未命名主题")
        description = topic.get("description", "")
        scope = topic.get("scope", "")
        innovation = topic.get("innovation", topic.get("innovation_point", ""))
        feasibility = topic.get("feasibility", topic.get("overall_score", topic.get("scores", {}).get("overall_score", "N/A")))
        literature_support = topic.get("literature_support", topic.get("literature_support", ""))
        potential_methods = topic.get("potential_methods", [])
        expected_contribution = topic.get("expected_contribution", "")
        scores = topic.get("scores", {})

        lines.append(f"## 选定主题: {title}")
        lines.append("")
        lines.append(f"**主题描述**: {description}")
        lines.append("")
        lines.append(f"**研究范围**: {scope}")
        lines.append("")
        lines.append(f"**创新点**: {innovation}")
        lines.append("")
        lines.append(f"**可行性评分**: {feasibility}")
        lines.append("")
        lines.append(f"**文献支持**: {literature_support}")
        lines.append("")

        if potential_methods:
            lines.append("**可能使用的方法**:")
            for method in potential_methods:
                lines.append(f"- {method}")
            lines.append("")

        if expected_contribution:
            lines.append(f"**预期贡献**: {expected_contribution}")
            lines.append("")

        # 显示评分详情
        if scores:
            lines.append("**评分详情**:")
            lines.append(f"- 文献充足性: {scores.get('literature_adequacy', 'N/A')}")
            lines.append(f"- 方法可行性: {scores.get('method_feasibility', 'N/A')}")
            lines.append(f"- 创新性: {scores.get('novelty', 'N/A')}")
            lines.append(f"- 时间合理性: {scores.get('time_reasonableness', 'N/A')}")
            lines.append(f"- 资源可获取性: {scores.get('resource_accessibility', 'N/A')}")
            lines.append("")

        # 显示备选主题
        if result and result.get("alternative_topics"):
            lines.append("**备选主题**:")
            for i, alt in enumerate(result.get("alternative_topics", []), 1):
                alt_title = alt.get("original", {}).get("title", "未命名")
                alt_score = alt.get("overall_score", 0)
                lines.append(f"{i}. {alt_title} (评分: {alt_score})")
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
