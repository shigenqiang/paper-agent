"""
精炼节点 - Refine Node

功能：
1. 多轮精炼 - 复用 ReportRefinerAgent
2. 提升内容质量
3. 优化表达

设计原则：
- 复用 writing/report_refiner.py
- 支持迭代精炼
- 保持内容准确性
"""
from typing import Dict, Any
from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class RefineNode:
    """精炼节点 - 多轮精炼"""

    def __init__(self, llm_provider=None):
        """初始化精炼节点

        Args:
            llm_provider: LLM 提供者（可选）
        """
        self.llm_provider = llm_provider

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行内容精炼

        Args:
            state: 当前状态，需包含 revised_draft 或 draft

        Returns:
            更新后的状态，添加 refined_draft 字段
        """
        draft = state.get("revised_draft") or state.get("draft", "")

        if not draft:
            logger.warning("No draft for refinement")
            state["refined_draft"] = ""
            return state

        try:
            # 简单实现：基于规则的精炼
            refined = self._rule_based_refine(draft)
            state["refined_draft"] = refined

            logger.info("Refinement completed")

        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            state["refined_draft"] = draft
            state.setdefault("errors", []).append(f"Refinement error: {str(e)}")

        return state

    def _rule_based_refine(self, draft: str) -> str:
        """基于规则的精炼"""
        # 简单实现：优化段落结构
        paragraphs = draft.split("\n\n")
        refined_paragraphs = []

        for para in paragraphs:
            # 确保段落不为空
            if para.strip():
                refined_paragraphs.append(para.strip())

        return "\n\n".join(refined_paragraphs)
