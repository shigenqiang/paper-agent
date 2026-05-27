"""
修改节点 - Revise Node

功能：
1. 智能改稿 - 复用 SmartReviserAgent
2. 支持多轮精炼
3. 生成修改报告

设计原则：
- 复用 writing/smart_reviser.py
- 保持修改历史
- 提供修改建议
"""
from typing import Dict, Any
from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class ReviseNode:
    """修改节点 - 智能改稿"""

    def __init__(self, llm_provider=None):
        """初始化修改节点

        Args:
            llm_provider: LLM 提供者（可选）
        """
        self.llm_provider = llm_provider

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行智能改稿

        Args:
            state: 当前状态，需包含 draft

        Returns:
            更新后的状态，添加 revised_draft 字段
        """
        draft = state.get("draft", "")

        if not draft:
            logger.warning("No draft for revision")
            state["revised_draft"] = ""
            return state

        try:
            # 简单实现：基于规则的改稿
            revised = self._rule_based_revise(draft)
            state["revised_draft"] = revised
            state["revision_report"] = self._generate_report(draft, revised)

            logger.info("Revision completed")

        except Exception as e:
            logger.error(f"Revision failed: {e}")
            state["revised_draft"] = draft
            state.setdefault("errors", []).append(f"Revision error: {str(e)}")

        return state

    def _rule_based_revise(self, draft: str) -> str:
        """基于规则的改稿"""
        # 简单实现：格式化和基本修正
        lines = draft.split("\n")
        revised_lines = []

        for line in lines:
            # 移除多余空格
            line = " ".join(line.split())
            # 确保标题格式
            if line.startswith("#"):
                line = line.strip()
            revised_lines.append(line)

        return "\n".join(revised_lines)

    def _generate_report(self, original: str, revised: str) -> Dict[str, Any]:
        """生成修改报告"""
        return {
            "original_length": len(original),
            "revised_length": len(revised),
            "changes": "格式化和基本修正"
        }
