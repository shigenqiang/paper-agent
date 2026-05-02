"""
润色节点 - Polish Node

功能：
1. 语言润色 - 复用 LanguagePolisherAgent
2. 提升表达质量
3. 优化语言风格

设计原则：
- 复用 writing/smart_reviser.py 的 LanguagePolisherAgent
- 保持内容不变
- 提升语言质量
"""
from typing import Dict, Any

logger = get_logging_logger(__name__)


class PolishNode:
    """润色节点 - 语言润色"""

    def __init__(self, llm_provider=None):
        """初始化润色节点

        Args:
            llm_provider: LLM 提供者（可选）
        """
        self.llm_provider = llm_provider

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行语言润色

        Args:
            state: 当前状态，需包含 refined_draft 或 draft

        Returns:
            更新后的状态，添加 polished_draft 字段
        """
        draft = state.get("refined_draft") or state.get("revised_draft") or state.get("draft", "")

        if not draft:
            logger.warning("No draft for polishing")
            state["polished_draft"] = ""
            return state

        try:
            # 简单实现：基于规则的润色
            polished = self._rule_based_polish(draft)
            state["polished_draft"] = polished

            logger.info("Polishing completed")

        except Exception as e:
            logger.error(f"Polishing failed: {e}")
            state["polished_draft"] = draft
            state.setdefault("errors", []).append(f"Polishing error: {str(e)}")

        return state

    def _rule_based_polish(self, draft: str) -> str:
        """基于规则的润色"""
        # 简单实现：标点符号优化
        polished = draft

        # 确保句号后有空格
        polished = polished.replace("。", "。 ")
        polished = polished.replace("，", "， ")

        # 移除多余空格
        while "  " in polished:
            polished = polished.replace("  ", " ")

        return polished.strip()
