"""
写作阶段 - Pipeline型Agent

职责：
- 按大纲撰写各章节
- 保持内容连贯性
- 添加引用和参考文献
"""
import time
from typing import Any, Dict, Optional

from src.agents_v2.logging_config import get_logging_logger

from ..utils.config import PhaseConfig
from ..utils.output import PhaseOutput

logger = get_logging_logger(__name__)


class WritingPhase:
    """
    写作阶段 - 使用多个Agent协同

    流程：
    1. OutlineAgent - 设计论文结构
    2. DraftWriterAgent - 按大纲撰写章节

    职责：
    - 设计论文大纲
    - 分节撰写论文
    - 整合初稿
    """

    def __init__(self, config: Optional[PhaseConfig] = None):
        self.config = config or PhaseConfig(phase_name="writing")
        self.agents = {}
        self._init_agents()

    def _init_agents(self):
        """初始化写作阶段Agent"""
        try:
            from src.agents_v2.paper_agents import (
                OutlineAgent,
                DraftWriterAgent,
            )
            self.agents["outline"] = OutlineAgent(self.config.llm_config)
            self.agents["draft"] = DraftWriterAgent(self.config.llm_config)
            logger.debug("Writing agents initialized")
        except ImportError as e:
            logger.warning(f"Could not import writing agents: {e}")

    async def run(
        self,
        topic: Any,
        literature_result: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PhaseOutput:
        """
        运行写作阶段

        Args:
            topic: 研究主题
            literature_result: 文献阶段结果
            context: 上下文

        Returns:
            PhaseOutput: 写作结果输出
        """
        start_time = time.time()
        phase_name = "writing"

        logger.info(f"[{phase_name}] Starting paper writing...")

        if not self.agents:
            return PhaseOutput(
                phase_name=phase_name,
                success=False,
                status="failed",
                error="No writing agents available"
            )

        try:
            # 1. 先生成大纲
            outline_result = await self._generate_outline(topic, literature_result, context)
            if not outline_result["success"]:
                return PhaseOutput(
                    phase_name=phase_name,
                    success=False,
                    status="failed",
                    error=outline_result.get("error", "Outline generation failed"),
                    execution_time=time.time() - start_time
                )

            outline = outline_result.get("outline", {})
            thesis_statement = outline_result.get("thesis_statement", "")

            # 2. 撰写初稿
            draft_result = await self._write_draft(
                topic, outline, thesis_statement, literature_result, context
            )

            # 3. 整合结果
            execution_time = time.time() - start_time
            full_draft = draft_result.get("full_draft", draft_result.get("report", ""))

            quality_score = min(outline_result.get("quality_score", 0.7) * 0.4 +
                               draft_result.get("quality_score", 0.7) * 0.6, 1.0)

            return PhaseOutput(
                phase_name=phase_name,
                success=True,
                status="completed",
                text=full_draft,
                result={
                    "outline": outline,
                    "draft": draft_result,
                    "thesis_statement": thesis_statement
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

    async def _generate_outline(
        self,
        topic: Any,
        literature_result: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成论文大纲"""
        outline_agent = self.agents.get("outline")
        if not outline_agent:
            return {"success": False, "error": "OutlineAgent not available"}

        try:
            input_data = {"task_description": topic}
            exec_context = context or {}
            exec_context["thesis_statement"] = str(topic)  # 确保有thesis_statement供翻译使用
            if literature_result:
                exec_context["literature_result"] = literature_result

            result = await outline_agent.execute(input_data, exec_context)

            if hasattr(result, 'success') and result.success:
                result_dict = result.result or {}
                return {
                    "success": True,
                    "outline": result_dict.get("outline", {}),
                    "thesis_statement": result_dict.get("thesis_statement", str(topic)),
                    "quality_score": result.quality_score or 0.7
                }
            return {"success": False, "error": result.error if hasattr(result, 'error') else "Unknown"}
        except Exception as e:
            logger.error(f"Outline generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def _write_draft(
        self,
        topic: Any,
        outline: Dict[str, Any],
        thesis_statement: str,
        literature_result: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """撰写论文初稿"""
        draft_agent = self.agents.get("draft")
        if not draft_agent:
            return {"success": False, "error": "DraftWriterAgent not available"}

        try:
            input_data = {"outline": outline}
            exec_context = context or {}
            exec_context["thesis_statement"] = thesis_statement
            if literature_result:
                exec_context["literature_result"] = literature_result

            result = await draft_agent.execute(input_data, exec_context)

            if hasattr(result, 'success') and result.success:
                return {
                    "success": True,
                    "full_draft": result.result.get("full_draft", ""),
                    "chapters": result.result.get("chapters", []),
                    "quality_score": result.quality_score or 0.7
                }
            return {"success": False, "error": result.error if hasattr(result, 'error') else "Unknown"}
        except Exception as e:
            logger.error(f"Draft writing failed: {e}")
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
