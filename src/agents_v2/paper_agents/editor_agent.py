"""
EditorAgent - 修订编辑Agent

职责：
- 内容修订
- 语言润色
- 格式调整
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

import json

from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig

logger = get_logging_logger(__name__)


class EditorAgent(PaperAgentBase):
    """
    EditorAgent - 修订编辑

    职责：
    - 内容修订
    - 语言润色
    - 格式调整
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个专业的学术论文编辑。
你的职责是：
1. 修订论文内容
2. 润色语言表达
3. 调整格式规范
4. 确保学术规范

请确保：
- 语言学术、规范、简洁
- 逻辑连贯
- 格式统一"""
        super().__init__(
            name="editor_agent",
            llm_config=llm_config,
            description="论文修订编辑",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        执行修订编辑

        Args:
            input_data: 包含task_type的字典
            context: 执行上下文（包含full_draft、outline）
        """
        draft = ""
        outline = {}

        if context:
            draft = context.get("full_draft", "")
            outline = context.get("outline", {})

        if not draft:
            draft = input_data.get("draft", "")

        if not draft:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Empty draft"
            )

        try:
            # 1. 内容修订
            revised = await self._revise_content(draft, outline)

            # 2. 语言润色
            polished = await self._polish_language(revised)

            # 3. 格式调整
            formatted = await self._adjust_format(polished)

            # 4. 生成最终稿
            final_draft = formatted

            return AgentOutput(
                success=True,
                result={
                    "final_draft": final_draft,
                    "revisions_made": await self._summarize_revisions(draft, final_draft)
                },
                agent_name=self.name,
                reasoning="Draft revised and polished",
                quality_score=0.85
            )

        except Exception as e:
            self.logger.error(f"EditorAgent execution failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _revise_content(self, draft: str, outline: Dict[str, Any]) -> str:
        """修订内容"""
        prompt = f"""
修订以下论文的内容，确保：
1. 逻辑连贯性
2. 论述完整性
3. 论点清晰
4. 论据充分

论文内容：
{draft[:3000]}...

请输出修订后的内容：
"""
        try:
            revised = await self._llm_call(prompt)
            # 如果原始内容更长，附加未修订部分
            if len(draft) > 3000:
                revised += "\n\n" + draft[3000:]
            return revised
        except Exception as e:
            self.logger.error(f"Content revision failed: {e}")
            return draft

    async def _polish_language(self, draft: str) -> str:
        """语言润色"""
        prompt = f"""
润色以下论文的语言表达，确保：
1. 学术规范
2. 语言简洁
3. 表达准确
4. 术语一致

论文内容：
{draft[:4000]}...

请输出润色后的内容：
"""
        try:
            polished = await self._llm_call(prompt)
            if len(draft) > 4000 and len(polished) < len(draft) * 0.9:
                # 内容可能被截断，附加原始内容
                polished += "\n\n" + draft[4000:]
            return polished
        except Exception as e:
            self.logger.error(f"Language polishing failed: {e}")
            return draft

    async def _adjust_format(self, draft: str) -> str:
        """调整格式"""
        prompt = f"""
检查并调整以下论文的格式，确保：
1. 标题层级正确
2. 段落缩进一致
3. 引用格式规范
4. 参考文献格式统一

论文内容：
{draft[:4000]}...

请输出格式调整后的内容：
"""
        try:
            formatted = await self._llm_call(prompt)
            if len(draft) > 4000 and len(formatted) < len(draft) * 0.9:
                formatted += "\n\n" + draft[4000:]
            return formatted
        except Exception as e:
            self.logger.error(f"Format adjustment failed: {e}")
            return draft

    async def _summarize_revisions(self, original: str, revised: str) -> List[str]:
        """总结修订内容"""
        if original == revised:
            return ["No changes made"]

        prompt = f"""
比较以下原文和修订后内容的区别，总结主要修订：

原文：{original[:2000]}
修订后：{revised[:2000]}

请列出3-5个主要修订点：
"""
        try:
            response = await self._llm_call(prompt)
            return [line.strip() for line in response.split('\n') if line.strip()]
        except Exception as e:
            self.logger.error(f"Revision summary failed: {e}")
            return ["Minor revisions made"]
