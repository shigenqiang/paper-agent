"""
Polish Node - LangGraph 工作流节点

对应 MasterSupervisor 的 polish 阶段：
- 多轮迭代优化论文质量
- 评审-修改-精炼循环
- 质量评估与改进
- 针对性问题修复
"""
from src.agents_v2.logging_config import get_logging_logger

import time
import os
from typing import Any, Dict, Optional

logger = get_logging_logger(__name__)

# Polish 阶段质量阈值（最终润色需要更高）
POLISH_QUALITY_THRESHOLD = 0.8


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


class PolishNode:
    """润色节点 - 调用 LanguagePolisherAgent、SmartReviserAgent 等"""

    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider

    async def _run_language_polisher(
        self,
        text: str,
        language: str = "zh",
        polish_level: str = "medium"
    ) -> Dict[str, Any]:
        """运行语言润色"""
        try:
            from src.agents_v2.problem_oriented.language_polisher import LanguagePolisherAgent

            llm_config = _get_llm_config()
            agent = LanguagePolisherAgent(llm_config=llm_config)
            result = await agent.diagnose({
                "text": text,
                "language": language,
                "polish_level": polish_level
            }, {})

            return {
                "success": result.success,
                "polished_text": result.result.get("polished_text", text) if isinstance(result.result, dict) else (result.result if isinstance(result.result, str) else text),
                "quality_score": result.quality_score / 10.0 if result.quality_score else 0,
                "diagnosed_issues": result.diagnosed_issues,
                "recommendations": result.recommendations,
                "error": result.error
            }
        except Exception as e:
            logger.warning(f"Language polisher failed: {e}")
            return {
                "success": False,
                "polished_text": text,  # 回退到原文
                "quality_score": 0.0,
                "diagnosed_issues": [],
                "recommendations": [],
                "error": str(e)
            }

    async def _run_smart_reviser(
        self,
        text: str,
        diagnostic_result: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """运行智能修订"""
        try:
            from src.agents_v2.writing.smart_reviser import SmartReviserAgent

            llm_config = _get_llm_config()
            agent = SmartReviserAgent(llm_config=llm_config)
            result = await agent.execute({
                "task": "revision",
                "text": text,
                "diagnostic": diagnostic_result
            }, {})

            return {
                "success": result.success,
                "revised_text": result.result.get("revised_text", text) if isinstance(result.result, dict) else (result.result if isinstance(result.result, str) else text),
                "quality_score": result.quality_score / 10.0 if result.quality_score else 0,
                "error": result.error
            }
        except Exception as e:
            logger.warning(f"Smart reviser failed: {e}")
            return {
                "success": False,
                "revised_text": text,
                "quality_score": 0.0,
                "error": str(e)
            }

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph 节点入口（同步包装）

        Args:
            state: 当前状态，需包含 draft

        Returns:
            更新后的状态
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.__call__(state))

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行语言润色（异步接口，兼容 LangGraph）

        Args:
            state: 当前状态，需包含 draft

        Returns:
            更新后的状态
        """
        draft = state.get("draft", "")
        if not draft:
            logger.warning("[Polish] No draft to polish")
            state["polish_success"] = False
            state["polished_text"] = ""
            return state

        logger.info(f"[Polish] 开始论文润色，draft length={len(draft)}...")
        start = time.time()

        # 获取诊断结果
        diagnostic_result = state.get("diagnostic_result", {})

        # 1. 语言润色
        polish_result = await self._run_language_polisher(
            text=draft,
            language=state.get("language", "zh"),
            polish_level="medium"
        )

        polished_text = polish_result.get("polished_text", draft)
        language_score = polish_result.get("quality_score", 0)
        language_issues = polish_result.get("diagnosed_issues", [])

        # 2. 智能修订（如果有问题）
        revised_text = polished_text
        revision_score = 0.0
        if language_issues:
            revision_result = await self._run_smart_reviser(polished_text, diagnostic_result)
            revised_text = revision_result.get("revised_text", polished_text)
            revision_score = revision_result.get("quality_score", 0)

        # 存储结果
        state["polished_text"] = revised_text
        state["polish_quality_score"] = (language_score + revision_score) / 2
        state["polish_success"] = polish_result.get("success", False)
        state["polish_issues"] = language_issues

        elapsed = time.time() - start
        logger.info(
            f"[Polish] 润色完成: polished_text type={type(polished_text)}, length={len(polished_text) if isinstance(polished_text, str) else 'N/A'}, "
            f"language_score={language_score:.3f}, revision_score={revision_score:.3f}, total={state['polish_quality_score']:.3f}, "
            f"耗时 {elapsed:.2f}s"
        )

        state["current_phase"] = "polish"
        return state

    def get_quality_threshold(self) -> float:
        """获取润色阶段质量阈值"""
        return POLISH_QUALITY_THRESHOLD
