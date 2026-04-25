"""
LanguagePolisherAgent - 语言润色Agent

针对问题：语言表达问题

职责：
- 语法检查
- 学术语言规范
- 术语一致性
"""
from typing import Any, Dict, List, Optional
import json
import logging

from .base_problem_agent import ProblemAgentBase, AgentOutput, LLMConfig

logger = logging.getLogger(__name__)


class LanguagePolisherAgent(ProblemAgentBase):
    """
    LanguagePolisherAgent - 语言润色

    针对问题：
    - 语句不通顺
    - 语法错误
    - 学术规范欠缺
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个学术语言润色专家。
你的职责是：
1. 检查语法错误
2. 规范学术语言
3. 确保术语一致
4. 提升语言质量

请确保语言准确、简洁、符合学术规范。"""
        super().__init__(
            name="language_polisher",
            target_problem="语言表达问题/语法错误",
            llm_config=llm_config,
            description="学术语言润色",
            system_prompt=system_prompt
        )

    async def diagnose(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        润色语言

        输入：
        - text: 需要润色的文本
        - language: 语言（zh/en）
        - domain: 研究领域（可选）
        """
        text = input_data.get("text", "")
        language = input_data.get("language", "zh")
        domain = input_data.get("domain", "")

        if not text:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["文本为空"],
                recommendations=["请提供需要润色的文本"],
                quality_score=0.0,
                error="Empty text"
            )

        try:
            # 1. 语法检查
            grammar_issues = await self._check_grammar(text, language)

            # 2. 学术语言规范
            academic_issues = await self._check_academic_style(text, language)

            # 3. 术语一致性检查
            terminology = await self._check_terminology(text, language)

            # 4. 润色后的文本
            polished = await self._polish_text(text, grammar_issues, academic_issues, terminology, language)

            # 5. 质量评分
            quality_score = 1.0 - (len(grammar_issues) + len(academic_issues)) / 100

            return AgentOutput(
                success=True,
                result={
                    "original_text": text,
                    "polished_text": polished,
                    "grammar_issues": grammar_issues,
                    "academic_issues": academic_issues,
                    "terminology_check": terminology
                },
                agent_name=self.name,
                diagnosed_issues=grammar_issues + academic_issues,
                recommendations=self._generate_recommendations(grammar_issues, academic_issues),
                quality_score=round(max(0, quality_score), 2)
            )

        except Exception as e:
            self.logger.error(f"Language polishing failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["语言润色失败"],
                recommendations=["请检查文本格式"],
                quality_score=0.0,
                error=str(e)
            )

    async def _check_grammar(self, text: str, language: str) -> List[str]:
        """检查语法错误"""
        prompt = f"""
检查以下{language}文案的语法错误：

文本：
{self._truncate(text, 1000)}

请识别：
1. 语法错误
2. 拼写错误（如果是英文）
3. 标点问题
4. 句式问题

输出JSON格式：
{{
    "issues": [
        {{
            "original": "错误内容",
            "location": "位置描述",
            "issue_type": "错误类型",
            "correction": "修正建议"
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            issues = []
            for item in data.get("issues", []):
                issues.append(f"[{item.get('issue_type', '语法')}] {item.get('original', '')} -> {item.get('correction', '')}")
            return issues
        except Exception as e:
            logger.error(f"Grammar check failed: {e}")
            return []

    async def _check_academic_style(self, text: str, language: str) -> List[str]:
        """检查学术语言规范"""
        prompt = f"""
检查以下文本的学术语言规范性：

文本：
{self._truncate(text, 1000)}

请检查：
1. 是否使用口语化表达？
2. 是否过于主观？
3. 是否简洁准确？
4. 是否符合学术写作规范？

输出JSON格式：
{{
    "issues": [
        {{
            "issue": "问题描述",
            "location": "位置",
            "suggestion": "修改建议"
        }}
    ],
    "overall_assessment": "整体评估"
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return [f"[学术规范] {i.get('issue', '')}" for i in data.get("issues", [])]
        except Exception as e:
            logger.error(f"Academic style check failed: {e}")
            return []

    async def _check_terminology(self, text: str, language: str) -> Dict[str, Any]:
        """检查术语一致性"""
        prompt = f"""
检查以下文本的术语使用：

文本：
{self._truncate(text, 1000)}

请检查：
1. 术语是否一致？
2. 是否有同一概念使用不同术语？
3. 术语使用是否准确？

输出JSON格式：
{{
    "consistent": true/false,
    "inconsistencies": [
        {{
            "term1": "术语1",
            "term2": "术语2",
            "context": "语境"
        }}
    ],
    "terminology_suggestions": ["建议1", "建议2"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"Terminology check failed: {e}")
            return {"consistent": True, "inconsistencies": []}

    async def _polish_text(
        self,
        text: str,
        grammar_issues: List,
        academic_issues: List,
        terminology: Dict,
        language: str
    ) -> str:
        """润色文本"""
        prompt = f"""
润色以下{language}学术文本：

原文：
{text}

发现的问题：
- 语法问题：{json.dumps(grammar_issues, ensure_ascii=False)}
- 学术规范问题：{json.dumps(academic_issues, ensure_ascii=False)}
- 术语问题：{json.dumps(terminology, ensure_ascii=False)}

请生成润色后的文本，保持原意，但：
1. 修正语法错误
2. 使用规范的学术语言
3. 统一术语使用

直接输出润色后的文本，不要其他解释。
"""
        try:
            response = await self._llm_call(prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"Text polishing failed: {e}")
            return text

    def _generate_recommendations(self, grammar_issues: List, academic_issues: List) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if grammar_issues:
            recommendations.append(f"修正{len(grammar_issues)}处语法错误")
        if academic_issues:
            recommendations.append(f"改进{len(academic_issues)}处学术语言")
        if not grammar_issues and not academic_issues:
            recommendations.append("语言质量良好，继续保持")

        return recommendations[:5]

    def _truncate(self, text: str, max_length: int) -> str:
        if not text:
            return ""
        return text[:max_length] + "..." if len(text) > max_length else text
