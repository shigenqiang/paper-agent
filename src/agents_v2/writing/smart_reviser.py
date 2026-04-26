"""
SmartReviserAgent - 智能改稿Agent

职责：
- 解析导师/审稿人意见
- 针对性修改文本
- 保持修改前后一致性
"""
from typing import Any, Dict, List, Optional
import json
import logging
import re

from .base_writing_agent import WritingAgentBase, WritingOutput, LLMConfig

logger = logging.getLogger(__name__)


class SmartReviserAgent(WritingAgentBase):
    """
    SmartReviserAgent - 智能改稿

    职责：
    - 解析导师/审稿人意见
    - 针对性修改文本
    - 保持修改一致性
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个专业的学术论文改稿专家。
你的职责是：
1. 解析导师/审稿人意见
2. 针对性修改论文
3. 保持修改一致性
4. 标记修改内容

请确保：
- 修改准确对应意见
- 不引入新问题
- 保持论文整体质量"""
        super().__init__(
            name="smart_reviser",
            llm_config=llm_config,
            description="智能改稿",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> WritingOutput:
        """
        执行智能改稿

        Args:
            input_data: 包含以下字段的字典：
                - original_text: 原文
                - feedback: 导师/审稿人意见
                - highlight_changes: 是否高亮显示修改 (默认True)
            context: 执行上下文
        """
        original_text = input_data.get("original_text", "")
        feedback = input_data.get("feedback", "")
        highlight_changes = input_data.get("highlight_changes", True)

        if not original_text or not feedback:
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Missing original text or feedback"
            )

        try:
            # 1. 解析意见
            parsed_feedback = await self._parse_feedback(feedback)

            # 2. 分类意见
            categorized = await self._categorize_feedback(parsed_feedback)

            # 3. 执行修改
            revised_text = await self._apply_revisions(
                original_text, categorized, highlight_changes
            )

            # 4. 生成修改报告
            revision_report = self._generate_revision_report(
                original_text, revised_text, categorized
            )

            return WritingOutput(
                success=True,
                result={
                    "original_text": original_text,
                    "revised_text": revised_text,
                    "revision_report": revision_report,
                    "feedback_categories": list(categorized.keys()),
                    "total_revisions": sum(len(v) for v in categorized.values())
                },
                agent_name=self.name,
                reasoning=f"Applied {sum(len(v) for v in categorized.values())} revisions across {len(categorized)} categories",
                quality_score=0.85
            )

        except Exception as e:
            self.logger.error(f"SmartReviserAgent execution failed: {e}")
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _parse_feedback(self, feedback: str) -> List[Dict[str, Any]]:
        """解析导师意见"""
        prompt = f"""
解析以下导师/审稿人意见，提取每个具体意见：

意见内容：
{feedback}

请将意见分解为独立的具体修改项：

输出JSON格式：
{{
    "items": [
        {{
            "id": 1,
            "original_text": "涉及的原文本",
            "issue": "问题描述",
            "suggestion": "修改建议",
            "priority": "high/medium/low"
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("items", [])
        except Exception as e:
            logger.error(f"Feedback parsing failed: {e}")
            return [{"id": 1, "issue": feedback, "suggestion": "请修改", "priority": "medium"}]

    async def _categorize_feedback(
        self,
        feedback_items: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """将意见分类"""
        categories = {
            "content": [],      # 内容问题
            "structure": [],    # 结构问题
            "language": [],     # 语言问题
            "citation": [],     # 引用问题
            "logic": [],        # 逻辑问题
            "format": []        # 格式问题
        }

        prompt = f"""
将以下修改意见按类型分类：

意见列表：{json.dumps(feedback_items, ensure_ascii=False)}

分类标准：
- content: 内容补充、删除、修改
- structure: 章节调整、重排
- language: 语法、用词、表达
- citation: 引用添加、修改
- logic: 论证逻辑问题
- format: 格式规范问题

输出JSON格式：
{{
    "categorized": {{
        "content": [意见ID列表],
        "structure": [意见ID列表],
        ...
    }}
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            cat_map = data.get("categorized", {})

            # 根据分类重新组织
            result = {k: [] for k in categories}
            for cat, ids in cat_map.items():
                if cat in result:
                    for item in feedback_items:
                        if item.get("id") in ids:
                            result[cat].append(item)

            return result
        except Exception as e:
            logger.error(f"Feedback categorization failed: {e}")
            return {"content": feedback_items}

    async def _apply_revisions(
        self,
        original_text: str,
        categorized: Dict[str, List[Dict[str, Any]]],
        highlight_changes: bool
    ) -> str:
        """应用修改"""
        revised_text = original_text

        # 按优先级处理
        for category in ["structure", "content", "logic", "citation", "language", "format"]:
            items = categorized.get(category, [])
            if not items:
                continue

            for item in items:
                try:
                    revised_text = await self._apply_single_revision(
                        revised_text, item, category
                    )
                except Exception as e:
                    logger.error(f"Revision {item.get('id')} failed: {e}")

        return revised_text

    async def _apply_single_revision(
        self,
        text: str,
        item: Dict[str, Any],
        category: str
    ) -> str:
        """应用单个修改"""
        issue = item.get("issue", "")
        suggestion = item.get("suggestion", "")
        original_mention = item.get("original_text", "")

        prompt = f"""
根据以下修改意见修改论文：

意见类型：{category}
问题描述：{issue}
修改建议：{suggestion}
涉及文本：{original_mention}

原始论文：
{text}

请执行修改：
1. 准确理解修改意见
2. 应用修改到论文
3. 确保修改后上下文连贯

请输出修改后的完整论文。
"""
        try:
            response = await self._llm_call(prompt)
            return response
        except Exception as e:
            logger.error(f"Single revision failed: {e}")
            return text

    def _generate_revision_report(
        self,
        original: str,
        revised: str,
        categorized: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """生成修改报告"""
        lines = [
            "# 论文修改报告\n",
            "## 修改统计"
        ]

        for cat, items in categorized.items():
            if items:
                lines.append(f"- **{cat}**: {len(items)}处修改")

        lines.append("\n## 修改详情\n")

        for cat, items in categorized.items():
            if not items:
                continue

            lines.append(f"### {cat.upper()}")
            for item in items:
                lines.append(f"- 位置: {item.get('original_text', 'N/A')[:50]}...")
                lines.append(f"  问题: {item.get('issue', '')}")
                lines.append(f"  建议: {item.get('suggestion', '')}")
            lines.append("")

        return "\n".join(lines)


class LanguagePolisherAgent(WritingAgentBase):
    """
    LanguagePolisherAgent - 语言润色Agent

    职责：
    - 语法检查
    - 术语规范
    - 句式优化
    - 中英翻译润色
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个专业的语言润色专家。
你的职责是：
1. 语法检查与纠正
2. 术语规范化
3. 句式优化
4. 提升表达质量

请确保：
- 语法正确
- 术语统一
- 表达流畅"""
        super().__init__(
            name="language_polisher",
            llm_config=llm_config,
            description="语言润色",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> WritingOutput:
        """
        执行语言润色

        Args:
            input_data: 包含以下字段的字典：
                - text: 要润色的文本
                - language: 语言 ("zh" 或 "en")
                - polish_level: 润色级别 ("light", "medium", "heavy")
        """
        text = input_data.get("text", "")
        language = input_data.get("language", "zh")
        polish_level = input_data.get("polish_level", "medium")

        if not text:
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Empty text"
            )

        try:
            # 1. 语法检查
            grammar_issues = await self._check_grammar(text, language)

            # 2. 术语规范化
            terminology = await self._normalize_terminology(text, language)

            # 3. 润色
            polished = await self._polish_text(text, language, polish_level)

            # 4. 生成报告
            report = await self._generate_polish_report(
                text, polished, grammar_issues, terminology
            )

            return WritingOutput(
                success=True,
                result={
                    "original_text": text,
                    "polished_text": polished,
                    "report": report,
                    "grammar_issues": len(grammar_issues),
                    "terminology_fixed": len(terminology)
                },
                agent_name=self.name,
                reasoning=f"Polished text, fixed {len(grammar_issues)} grammar issues",
                quality_score=0.9
            )

        except Exception as e:
            self.logger.error(f"LanguagePolisherAgent execution failed: {e}")
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _check_grammar(
        self,
        text: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """检查语法"""
        prompt = f"""
检查以下{language}语文本的语法问题：

文本：
{text}

请识别：
1. 语法错误
2. 用词不当
3. 表达不通顺的地方

输出JSON格式：
{{
    "issues": [
        {{"location": "位置", "original": "原文", "issue": "问题", "suggestion": "建议"}}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("issues", [])
        except Exception as e:
            logger.error(f"Grammar check failed: {e}")
            return []

    async def _normalize_terminology(
        self,
        text: str,
        language: str
    ) -> List[Dict[str, str]]:
        """术语规范化"""
        prompt = f"""
检查并规范化以下文本中的术语：

文本：
{text}

请：
1. 识别非标准或不一致的术语使用
2. 提供标准术语
3. 建议统一方案

输出JSON格式：
{{
    "terms": [
        {{"original": "原文", "standard": "标准术语", "count": 出现次数}}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("terms", [])
        except Exception as e:
            logger.error(f"Terminology normalization failed: {e}")
            return []

    async def _polish_text(
        self,
        text: str,
        language: str,
        level: str
    ) -> str:
        """润色文本"""
        level_desc = {
            "light": "轻度润色，只做必要的语法修正",
            "medium": "中度润色，优化表达，提升可读性",
            "heavy": "深度润色，全面优化句式和表达"
        }

        prompt = f"""
对以下{language}语文本进行{level_desc.get(level, '中等')}润色：

文本：
{text}

要求：
1. 修正语法错误
2. 优化句式结构
3. 提升表达的准确性和流畅性
4. 保持原意不变

请输出润色后的文本。
"""
        try:
            response = await self._llm_call(prompt)
            return response
        except Exception as e:
            logger.error(f"Text polishing failed: {e}")
            return text

    async def _generate_polish_report(
        self,
        original: str,
        polished: str,
        grammar_issues: List[Dict],
        terminology: List[Dict]
    ) -> str:
        """生成润色报告"""
        lines = [
            "# 语言润色报告\n",
            f"## 统计"
        ]

        if grammar_issues:
            lines.append(f"- 发现语法问题: {len(grammar_issues)}处")
            lines.append("\n### 语法问题")
            for issue in grammar_issues[:5]:
                lines.append(f"- {issue.get('issue', '')}")
        else:
            lines.append("- 无语法问题")

        if terminology:
            lines.append(f"\n- 术语规范化: {len(terminology)}处")

        return "\n".join(lines)
