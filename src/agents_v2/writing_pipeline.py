"""
Complete Writing Pipeline - 完整论文写作流程

从选题到最终润色的完整流程实现
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import asyncio

from .state import PaperState, PaperPhase, StateStatus, create_initial_state
from .intent import IntentType, IntentClassifier
from .validation import InputValidator, ValidationType, TextCleaner, QueryNormalizer

logger = logging.getLogger(__name__)


class WritingPhase(str, Enum):
    """写作阶段"""
    OUTLINE = "outline"           # 大纲生成
    DRAFT = "draft"               # 初稿撰写
    REVIEW = "review"             # 审核
    REVISION = "revision"          # 修订
    POLISH = "polish"             # 润色
    COMPLETED = "completed"       # 完成


@dataclass
class WritingTask:
    """写作任务"""
    task_id: str
    topic: str
    current_phase: WritingPhase = WritingPhase.OUTLINE
    outline: Optional[Dict[str, Any]] = None
    draft: Optional[str] = None
    feedback: List[str] = field(default_factory=list)
    revisions_applied: int = 0
    quality_scores: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PhaseResult:
    """阶段结果"""
    phase: WritingPhase
    success: bool
    output: Any = None
    quality_score: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class WritingPipeline:
    """
    完整论文写作流程

    工作流程:
    1. 选题 -> 大纲
    2. 大纲 -> 初稿
    3. 初稿 -> 审核
    4. 审核 -> 修订（如有反馈）
    5. 修订 -> 润色
    6. 润色 -> 完成

    使用示例:
        pipeline = WritingPipeline()

        # 运行完整流程
        result = await pipeline.run_full_pipeline(
            topic="基于深度学习的图像超分辨率算法研究",
            outline_template="academic",
            revision_rounds=2
        )
    """

    def __init__(
        self,
        llm_config: Optional[Any] = None,
        enable_validation: bool = True,
        enable_monitoring: bool = True
    ):
        self.llm_config = llm_config

        # 子模块
        self.input_validator = InputValidator() if enable_validation else None
        self.text_cleaner = TextCleaner()
        self.query_normalizer = QueryNormalizer()
        self.intent_classifier = IntentClassifier()

        # Agent实例
        self._agents = self._initialize_agents()

        # 监控
        self.enable_monitoring = enable_monitoring
        self._monitoring_data: Dict[str, Any] = {}

        # 配置
        self.max_revision_rounds = 3
        self.quality_threshold = 0.75

        logger.info("WritingPipeline initialized")

    def _initialize_agents(self) -> Dict[str, Any]:
        """初始化写作Agent"""
        from ..writing import (
            OutlineGeneratorAgent,
            DraftGeneratorAgent,
            SmartReviserAgent,
            LanguagePolisherAgent,
        )

        return {
            "outline": OutlineGeneratorAgent(llm_config=self.llm_config),
            "draft": DraftGeneratorAgent(llm_config=self.llm_config),
            "revision": SmartReviserAgent(llm_config=self.llm_config),
            "polish": LanguagePolisherAgent(llm_config=self.llm_config),
        }

    async def run_full_pipeline(
        self,
        topic: str,
        outline_template: str = "academic",
        revision_rounds: int = 2,
        existing_draft: Optional[str] = None,
        feedback: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        运行完整写作流程

        Args:
            topic: 研究主题
            outline_template: 大纲模板 (academic/proposal/thesis)
            revision_rounds: 修订轮次
            existing_draft: 已有草稿（用于继续写作）
            feedback: 修订反馈

        Returns:
            Dict containing final draft, quality scores, and metadata
        """
        import time
        start_time = time.time()

        # 创建写作任务
        task = WritingTask(
            task_id=f"writing_{int(time.time())}",
            topic=topic,
            feedback=feedback or []
        )

        # Phase 1: 大纲生成
        if existing_draft is None:
            outline_result = await self._generate_outline(topic, outline_template)
            if not outline_result.success:
                return self._create_error_response("大纲生成失败", outline_result.errors)
            task.outline = outline_result.output
            task.quality_scores["outline"] = outline_result.quality_score

        # Phase 2: 初稿撰写
        draft_result = await self._write_draft(topic, task.outline, existing_draft)
        if not draft_result.success:
            return self._create_error_response("初稿撰写失败", draft_result.errors)
        task.draft = draft_result.output
        task.quality_scores["draft"] = draft_result.quality_score

        # Phase 3-5: 修订循环
        for round_num in range(min(revision_rounds, self.max_revision_rounds)):
            # 检查是否需要修订
            current_feedback = task.feedback if round_num == 0 else None

            # 审核
            review_result = await self._review_draft(task.draft, current_feedback)
            if review_result.success:
                task.quality_scores[f"review_{round_num}"] = review_result.quality_score

            # 检查质量阈值
            avg_quality = sum(task.quality_scores.values()) / len(task.quality_scores)
            if avg_quality >= self.quality_threshold:
                logger.info(f"Quality threshold met: {avg_quality:.2f}")
                break

            # 修订
            revision_result = await self._revise_draft(task.draft, current_feedback)
            if revision_result.success:
                task.draft = revision_result.output
                task.revisions_applied += 1
                task.quality_scores[f"revision_{round_num}"] = revision_result.quality_score

        # Phase 6: 润色
        polish_result = await self._polish_draft(task.draft)
        if polish_result.success:
            task.draft = polish_result.output
            task.quality_scores["polish"] = polish_result.quality_score

        # 计算总耗时
        total_duration = time.time() - start_time

        return {
            "success": True,
            "topic": topic,
            "outline": task.outline,
            "final_draft": task.draft,
            "revisions_applied": task.revisions_applied,
            "quality_scores": task.quality_scores,
            "overall_quality": sum(task.quality_scores.values()) / max(1, len(task.quality_scores)),
            "duration_seconds": total_duration,
            "phases_completed": [
                WritingPhase.OUTLINE.value,
                WritingPhase.DRAFT.value,
                WritingPhase.REVISION.value,
                WritingPhase.POLISH.value
            ]
        }

    async def _generate_outline(
        self,
        topic: str,
        template: str
    ) -> PhaseResult:
        """生成大纲"""
        import time
        start_time = time.time()

        try:
            agent = self._agents.get("outline")
            if not agent:
                return PhaseResult(
                    phase=WritingPhase.OUTLINE,
                    success=False,
                    errors=["Outline agent not available"]
                )

            # 执行
            if hasattr(agent, 'execute'):
                result = await agent.execute({
                    "topic": topic,
                    "template": template
                })

                success = getattr(result, 'success', False)
                output = getattr(result, 'result', None) if success else None
                quality = getattr(result, 'quality_score', 0.5)

                return PhaseResult(
                    phase=WritingPhase.OUTLINE,
                    success=success,
                    output=output,
                    quality_score=quality,
                    duration_seconds=time.time() - start_time
                )

            return PhaseResult(
                phase=WritingPhase.OUTLINE,
                success=False,
                errors=["Agent execute method not found"]
            )

        except Exception as e:
            logger.error(f"Outline generation failed: {e}")
            return PhaseResult(
                phase=WritingPhase.OUTLINE,
                success=False,
                errors=[str(e)],
                duration_seconds=time.time() - start_time
            )

    async def _write_draft(
        self,
        topic: str,
        outline: Optional[Dict[str, Any]],
        existing_draft: Optional[str]
    ) -> PhaseResult:
        """撰写初稿"""
        import time
        start_time = time.time()

        try:
            agent = self._agents.get("draft")
            if not agent:
                return PhaseResult(
                    phase=WritingPhase.DRAFT,
                    success=False,
                    errors=["Draft agent not available"]
                )

            if existing_draft:
                # 继续写作
                return PhaseResult(
                    phase=WritingPhase.DRAFT,
                    success=True,
                    output=existing_draft,
                    quality_score=0.7,
                    duration_seconds=time.time() - start_time
                )

            if hasattr(agent, 'execute'):
                result = await agent.execute({
                    "topic": topic,
                    "outline": outline or {"chapters": []}
                })

                success = getattr(result, 'success', False)
                output = getattr(result, 'result', {}).get('full_draft', '') if success else None
                quality = getattr(result, 'quality_score', 0.5)

                return PhaseResult(
                    phase=WritingPhase.DRAFT,
                    success=success,
                    output=output,
                    quality_score=quality,
                    duration_seconds=time.time() - start_time
                )

            return PhaseResult(
                phase=WritingPhase.DRAFT,
                success=False,
                errors=["Agent execute method not found"]
            )

        except Exception as e:
            logger.error(f"Draft writing failed: {e}")
            return PhaseResult(
                phase=WritingPhase.DRAFT,
                success=False,
                errors=[str(e)],
                duration_seconds=time.time() - start_time
            )

    async def _review_draft(
        self,
        draft: str,
        feedback: Optional[List[str]]
    ) -> PhaseResult:
        """审核草稿"""
        import time
        start_time = time.time()

        # 简单的质量检查（实际应用中会使用LLM）
        if not draft or len(draft) < 100:
            return PhaseResult(
                phase=WritingPhase.REVIEW,
                success=False,
                errors=["Draft too short to review"],
                duration_seconds=time.time() - start_time
            )

        # 模拟质量评分
        quality_score = min(0.9, len(draft) / 1000 + 0.5)

        return PhaseResult(
            phase=WritingPhase.REVIEW,
            success=True,
            output={"review_notes": "Draft looks good", "needs_revision": quality_score < 0.7},
            quality_score=quality_score,
            duration_seconds=time.time() - start_time
        )

    async def _revise_draft(
        self,
        draft: str,
        feedback: Optional[List[str]]
    ) -> PhaseResult:
        """修订草稿"""
        import time
        start_time = time.time()

        try:
            agent = self._agents.get("revision")
            if not agent:
                return PhaseResult(
                    phase=WritingPhase.REVISION,
                    success=False,
                    errors=["Revision agent not available"]
                )

            if hasattr(agent, 'execute'):
                result = await agent.execute({
                    "original_text": draft,
                    "feedback": feedback or ["请改进内容和结构"]
                })

                success = getattr(result, 'success', False)
                output = getattr(result, 'result', {}).get('revised_text', draft) if success else draft
                quality = getattr(result, 'quality_score', 0.6)

                return PhaseResult(
                    phase=WritingPhase.REVISION,
                    success=success,
                    output=output,
                    quality_score=quality,
                    duration_seconds=time.time() - start_time
                )

            return PhaseResult(
                phase=WritingPhase.REVISION,
                success=True,
                output=draft,  # 没有修订Agent时保持原样
                quality_score=0.6,
                duration_seconds=time.time() - start_time
            )

        except Exception as e:
            logger.error(f"Revision failed: {e}")
            return PhaseResult(
                phase=WritingPhase.REVISION,
                success=False,
                errors=[str(e)],
                duration_seconds=time.time() - start_time
            )

    async def _polish_draft(self, draft: str) -> PhaseResult:
        """润色草稿"""
        import time
        start_time = time.time()

        try:
            agent = self._agents.get("polish")
            if not agent:
                return PhaseResult(
                    phase=WritingPhase.POLISH,
                    success=False,
                    errors=["Polish agent not available"]
                )

            if hasattr(agent, 'execute'):
                result = await agent.execute({
                    "text": draft,
                    "language": "zh",
                    "polish_level": "medium"
                })

                success = getattr(result, 'success', False)
                output = getattr(result, 'result', {}).get('polished_text', draft) if success else draft
                quality = getattr(result, 'quality_score', 0.7)

                return PhaseResult(
                    phase=WritingPhase.POLISH,
                    success=success,
                    output=output,
                    quality_score=quality,
                    duration_seconds=time.time() - start_time
                )

            return PhaseResult(
                phase=WritingPhase.POLISH,
                success=True,
                output=draft,  # 没有润色Agent时保持原样
                quality_score=0.7,
                duration_seconds=time.time() - start_time
            )

        except Exception as e:
            logger.error(f"Polishing failed: {e}")
            return PhaseResult(
                phase=WritingPhase.POLISH,
                success=False,
                errors=[str(e)],
                duration_seconds=time.time() - start_time
            )

    def _create_error_response(
        self,
        message: str,
        errors: List[str]
    ) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "success": False,
            "error": message,
            "details": errors
        }

    def get_pipeline_status(self) -> Dict[str, Any]:
        """获取流程状态"""
        return {
            "agents_available": list(self._agents.keys()),
            "monitoring_enabled": self.enable_monitoring,
            "max_revision_rounds": self.max_revision_rounds,
            "quality_threshold": self.quality_threshold
        }


async def run_writing_pipeline(
    topic: str,
    outline_template: str = "academic",
    revision_rounds: int = 2,
    llm_config: Optional[Any] = None
) -> Dict[str, Any]:
    """
    便捷函数：运行写作流程

    Args:
        topic: 研究主题
        outline_template: 大纲模板
        revision_rounds: 修订轮次
        llm_config: LLM配置

    Returns:
        流程执行结果
    """
    pipeline = WritingPipeline(llm_config=llm_config)
    return await pipeline.run_full_pipeline(
        topic=topic,
        outline_template=outline_template,
        revision_rounds=revision_rounds
    )