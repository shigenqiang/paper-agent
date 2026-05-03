"""
润色阶段 - 问题导向Agent

职责：
- 多轮迭代优化论文质量
- 评审-修改-精炼循环
- 质量评估与改进
- 针对性问题修复
"""
import time
from typing import Any, Dict, Optional

from src.agents_v2.logging_config import get_logging_logger

from ..utils.config import PhaseConfig
from ..utils.output import PhaseOutput

logger = get_logging_logger(__name__)


class PolishPhase:
    """
    润色阶段 - 使用写作型Agent

    职责：
    - 多轮迭代优化论文质量
    - 评审论文问题
    - 针对性修改
    - 精炼语言和逻辑
    """

    def __init__(self, config: Optional[PhaseConfig] = None):
        self.config = config or PhaseConfig(phase_name="polish")
        self.agents = {}
        self._init_agents()

    def _init_agents(self):
        """初始化润色阶段Agent"""
        try:
            from src.agents_v2.writing import (
                LanguagePolisherAgent,
                SmartReviserAgent,
                ReportRefinerAgent,
            )
            self.agents["language_polisher"] = LanguagePolisherAgent(self.config.llm_config)
            self.agents["smart_reviser"] = SmartReviserAgent(self.config.llm_config)
            self.agents["report_refiner"] = ReportRefinerAgent(self.config.llm_config)
            logger.debug("Polish agents initialized")
        except ImportError as e:
            logger.warning(f"Could not import polish agents: {e}")

    async def run(
        self,
        text: str,
        language: str = "zh",
        polish_level: str = "medium",
        context: Optional[Dict[str, Any]] = None
    ) -> PhaseOutput:
        """
        运行润色阶段

        Args:
            text: 待润色的文本
            language: 语言 (zh/en)
            polish_level: 润色级别 (light/medium/heavy)
            context: 上下文

        Returns:
            PhaseOutput: 润色结果输出
        """
        start_time = time.time()
        phase_name = "polish"

        logger.info(f"[{phase_name}] Starting paper polishing...")

        if not text:
            return PhaseOutput(
                phase_name=phase_name,
                success=False,
                status="failed",
                error="Empty text to polish"
            )

        if not self.agents:
            return PhaseOutput(
                phase_name=phase_name,
                success=False,
                status="failed",
                error="No polish agents available"
            )

        try:
            # 1. 先用LanguagePolisher进行基础润色
            polished_text = text
            quality_score = 0.0
            iteration_count = 0

            language_polisher = self.agents.get("language_polisher")
            if language_polisher:
                result = await self._run_language_polisher(
                    language_polisher, polished_text, language, polish_level, context
                )
                if result["success"]:
                    polished_text = result.get("polished_text", polished_text)
                    quality_score = result.get("quality_score", 0.0)
                    iteration_count += 1

            # 2. 用SmartReviser进行针对性修改（需要feedback，无feedback时跳过）
            smart_reviser = self.agents.get("smart_reviser")
            feedback = context.get("feedback") if context else None
            if smart_reviser and polished_text and feedback:
                result = await self._run_smart_reviser(
                    smart_reviser, polished_text, feedback, context
                )
                if result["success"]:
                    polished_text = result.get("polished_text", polished_text)
                    quality_score = max(quality_score, result.get("quality_score", 0.0))
                    iteration_count += 1

            # 3. 用ReportRefiner进行多轮精炼
            report_refiner = self.agents.get("report_refiner")
            if report_refiner and polished_text:
                result = await self._run_report_refiner(
                    report_refiner, polished_text, context
                )
                if result["success"]:
                    polished_text = result.get("polished_text", polished_text)
                    quality_score = max(quality_score, result.get("quality_score", 0.0))
                    iteration_count += result.get("iterations", 1)

            # 生成润色报告（默认只输出润色后文本，不含标题）
            polished_report = self._generate_polish_report(
                text=text,
                polished_text=polished_text,
                quality_score=quality_score,
                include_header=False
            )

            execution_time = time.time() - start_time

            return PhaseOutput(
                phase_name=phase_name,
                success=True,
                status="completed",
                text=polished_report,
                result={
                    "original_length": len(text),
                    "polished_length": len(polished_text),
                    "iterations": iteration_count,
                    "fallback": False
                },
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

    async def _run_language_polisher(
        self,
        agent,
        text: str,
        language: str,
        polish_level: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """运行语言润色Agent"""
        try:
            input_data = {
                "text": text,
                "language": language,
                "polish_level": polish_level
            }
            result = await agent.execute(input_data, context)

            if hasattr(result, 'success') and result.success:
                result_dict = result.result if hasattr(result, 'result') else {}
                return {
                    "success": True,
                    "polished_text": result_dict.get("polished_text", result_dict.get("text", text)),
                    "quality_score": result.quality_score if hasattr(result, 'quality_score') else 0.7
                }
            return {"success": False, "error": result.error if hasattr(result, 'error') else "Unknown"}
        except Exception as e:
            logger.error(f"Language polisher failed: {e}")
            return {"success": False, "error": str(e)}

    async def _run_smart_reviser(
        self,
        agent,
        text: str,
        feedback: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """运行智能改稿Agent（需要feedback）"""
        try:
            input_data = {
                "original_text": text,
                "feedback": feedback
            }
            result = await agent.execute(input_data, context)

            if hasattr(result, 'success') and result.success:
                result_dict = result.result if hasattr(result, 'result') else {}
                return {
                    "success": True,
                    "polished_text": result_dict.get("polished_text", result_dict.get("text", text)),
                    "quality_score": result.quality_score if hasattr(result, 'quality_score') else 0.7
                }
            return {"success": False, "error": result.error if hasattr(result, 'error') else "Unknown"}
        except Exception as e:
            logger.error(f"Smart reviser failed: {e}")
            return {"success": False, "error": str(e)}

    async def _run_report_refiner(
        self,
        agent,
        text: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """运行报告精炼Agent"""
        try:
            input_data = {
                "draft": text,
                "max_iterations": 3,
                "quality_threshold": 0.7
            }
            result = await agent.execute(input_data, context)

            if hasattr(result, 'success') and result.success:
                result_dict = result.result if hasattr(result, 'result') else {}
                return {
                    "success": True,
                    "polished_text": result_dict.get("polished_text", result_dict.get("final_draft", text)),
                    "quality_score": result.quality_score if hasattr(result, 'quality_score') else 0.7,
                    "iterations": result_dict.get("iterations_completed", 1)
                }
            return {"success": False, "error": result.error if hasattr(result, 'error') else "Unknown"}
        except Exception as e:
            logger.error(f"Report refiner failed: {e}")
            return {"success": False, "error": str(e)}

    def _get_quality_level(self, score: float) -> str:
        """获取质量等级"""
        if score >= 9.0:
            return "excellent"
        elif score >= 7.0:
            return "good"
        elif score >= 5.0:
            return "acceptable"
        return "poor"

    def _generate_polish_report(
        self,
        text: str,
        polished_text: str,
        quality_score: float,
        include_header: bool = False
    ) -> str:
        """生成润色报告

        Args:
            text: 原文
            polished_text: 润色后文本
            quality_score: 质量评分
            include_header: 是否包含报告标题（True=完整报告，False=仅润色后文本）
        """
        if not include_header:
            return polished_text

        lines = [
            "# 论文润色结果",
            "",
            "## 原文",
            text,
            "",
            "## 润色后",
            polished_text,
            "",
            f"**质量评分**: {quality_score:.2f}",
        ]
        return "\n".join(lines)
