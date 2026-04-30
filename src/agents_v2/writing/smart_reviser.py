"""
SmartReviserAgent - 智能改稿Agent

职责：
- 解析导师/审稿人意见
- 针对性修改文本
- 保持修改前后一致性
"""
import os
from typing import Any, Dict, List, Optional
import json
import logging
import re

from .base_writing_agent import WritingAgentBase, WritingOutput, LLMConfig
from ..problem_oriented.base_problem_agent import AgentOutput

logger = logging.getLogger(__name__)


class TrinkaGrammarChecker:
    """
    Trinka AI 语法检查器

    集成 Trinka API 进行专业学术语法检查。
    API 文档: https://api.trinka.ai/docs/
    """

    API_KEY = os.getenv("TRINKA_API_KEY", "")
    BASE_URL = "https://api.trinka.ai/api/v1/document/check"

    def __init__(self):
        self.enabled = bool(self.API_KEY)

    async def check(self, text: str, language: str = "en") -> Dict[str, Any]:
        """
        使用 Trinka API 检查语法

        Args:
            text: 待检查文本
            language: 语言 (en/zh)

        Returns:
            包含错误列表的字典
        """
        if not self.enabled:
            logger.warning("Trinka API key not configured, skipping API check")
            return {"success": False, "error": "API not configured", "issues": []}

        try:
            import aiohttp

            headers = {
                "Authorization": f"Bearer {self.API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "content": text,
                "language": language
            }

            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.BASE_URL, json=data, headers=headers) as resp:
                    if resp.status == 401:
                        logger.error("Trinka API authentication failed")
                        return {"success": False, "error": "Authentication failed", "issues": []}
                    if resp.status == 429:
                        logger.warning("Trinka API rate limit exceeded")
                        return {"success": False, "error": "Rate limit exceeded", "issues": []}
                    if resp.status != 200:
                        text_response = await resp.text()
                        logger.error(f"Trinka API error: {resp.status} - {text_response}")
                        return {"success": False, "error": f"API error: {resp.status}", "issues": []}

                    result = await resp.json()
                    return self._parse_trinka_result(result)

        except Exception as e:
            logger.error(f"Trinka grammar check failed: {e}")
            return {"success": False, "error": str(e), "issues": []}

    def _parse_trinka_result(self, result: dict) -> Dict[str, Any]:
        """解析 Trinka API 返回结果"""
        issues = []

        try:
            matches = result.get("matches", [])
            for match in matches:
                issue = {
                    "location": match.get("location", {}),
                    "original": match.get("original", ""),
                    "replacement": match.get("replacement", ""),
                    "message": match.get("message", ""),
                    "rule": match.get("rule", {}),
                    "type": match.get("type", ""),
                    "category": match.get("category", "")
                }
                issues.append(issue)
        except Exception as e:
            logger.error(f"Failed to parse Trinka result: {e}")

        return {
            "success": True,
            "error": "",
            "issues": issues,
            "total_issues": len(issues)
        }

    def format_issues(self, issues: List[Dict]) -> str:
        """格式化错误列表为可读文本"""
        if not issues:
            return "No grammar issues found."

        lines = []
        for i, issue in enumerate(issues, 1):
            original = issue.get("original", "")
            replacement = issue.get("replacement", "")
            message = issue.get("message", "")

            if replacement:
                lines.append(f"{i}. '{original}' → '{replacement}'")
            else:
                lines.append(f"{i}. '{original}': {message}")

        return "\n".join(lines)


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
            if not response:
                logger.warning("Feedback parsing LLM returned empty response")
                return [{"id": 1, "issue": feedback, "suggestion": "请修改", "priority": "medium"}]
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
            if not response:
                logger.warning("Feedback categorization LLM returned empty response")
                return {"content": feedback_items}
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
    - 格式修正（LaTeX公式、标题层级、段落间距）
    """

    # 基于Agent提示词工程指南的诊断型Agent标准结构
    SYSTEM_PROMPT_TEMPLATE = """## 角色
你是一位专业的学术语言诊断与润色专家，专注于提升学术论文的语言质量。

## 诊断维度
1. **语法正确性**：检查句子结构、时态、主谓一致、标点符号等基础语法问题
2. **学术规范性**：评估文本是否符合学术写作标准，包括表达客观性、逻辑严密性
3. **术语一致性**：确保同一概念使用统一术语，避免一词多义或一义多词
4. **语言简洁性**：判断表达是否冗余，是否存在冗长的句式结构
5. **学科适配性**：检查术语使用是否契合目标学科的表达习惯

## 问题分类
- GRAMMAR_ERROR：语法错误（主谓不一致、时态错误、词性误用）
- SPELLING_ERROR：拼写错误（英文专有名词、大小写、连字符）
- PUNCTUATION_ERROR：标点错误（中英文标点混用、位置不当）
- COLLOQUIALISM：口语化表达（使用"很好"、"非常大"等主观模糊词汇）
- SUBJECTIVITY：主观性过强（缺乏客观数据支撑的绝对化表述）
- VERBOSITY：冗余表达（重复啰嗦的句式）
- INCONSISTENCY：术语不一致（同概念不同表述）
- LOGIC_BREAK：逻辑断裂（跳跃性推理、因果关系不清）
- FORMAT_ERROR：格式错误（LaTeX公式、标题层级、段落间距、列表格式）

## 严重程度
- HIGH（0.8-1.0）：严重影响阅读理解或导致歧义，必须立即修正
- MEDIUM（0.4-0.7）：影响语言质量但不导致误解，建议修正
- LOW（0.1-0.3）：轻微问题，可选择性优化

## 输出格式
```json
{
    "diagnosis": {
        "grammar_issues": [{"original": "", "location": "", "type": "", "severity": 0.0-1.0, "correction": ""}],
        "style_issues": [{"original": "", "location": "", "type": "", "severity": 0.0-1.0, "correction": ""}],
        "terminology_issues": [{"term1": "", "term2": "", "context": "", "severity": 0.0-1.0, "suggestion": ""}]
    },
    "overall_quality": 0.0-1.0,
    "polished_text": "润色后的完整文本",
    "summary": "问题总结与改进要点"
}
```"""

    FEW_SHOT_EXAMPLES = """
## 少样本示例

【示例1：中文论文润色】
输入文本："我们的方法比基线高了5个百分点，效果非常好"
诊断结果：
{
    "diagnosis": {
        "grammar_issues": [],
        "style_issues": [
            {"original": "高了5个百分点", "location": "第1句", "type": "COLLOQUIALISM", "severity": 0.6, "correction": "准确率提升5个百分点"},
            {"original": "效果非常好", "location": "第1句", "type": "SUBJECTIVITY", "severity": 0.7, "correction": "取得了显著的性能提升"}
        ],
        "terminology_issues": []
    },
    "overall_quality": 0.65,
    "polished_text": "相比基线方法，本文方法准确率提升5个百分点，取得了显著的性能提升。",
    "summary": "修正1处口语化表达，替换1处主观评价为客观描述"
}

【示例2：英文论文润色】
输入文本："This method is very good and we got better results."
诊断结果：
{
    "diagnosis": {
        "grammar_issues": [
            {"original": "we got better results", "location": "句1", "type": "GRAMMAR_ERROR", "severity": 0.5, "correction": "the method achieves improved results"}
        ],
        "style_issues": [
            {"original": "is very good", "location": "句1", "type": "COLLOQUIALISM", "severity": 0.8, "correction": "demonstrates superior performance"}
        ],
        "terminology_issues": []
    },
    "overall_quality": 0.55,
    "polished_text": "This novel method demonstrates superior performance compared to existing approaches.",
    "summary": "修正时态错误，替换口语化表达为学术规范用语"
}
"""

    def __init__(self, llm_config: Optional[LLMConfig] = None, use_trinka: bool = False):
        system_prompt = self.SYSTEM_PROMPT_TEMPLATE + "\n\n" + self.FEW_SHOT_EXAMPLES
        super().__init__(
            name="language_polisher",
            llm_config=llm_config,
            description="语言润色与格式修正",
            system_prompt=system_prompt
        )
        self._trinka = TrinkaGrammarChecker() if use_trinka else None

    def _clean_text_output(self, text: str) -> str:
        """清理文本输出，移除思考块、代码块标记等"""
        if not text:
            return text
        import re
        # 1. 移除思考块
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # 2. 移除 markdown 代码块标记
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = re.sub(r'```$', '', text)
        # 3. 清理多余的空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _parse_diagnosis_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析LLM返回的诊断结果"""
        import re
        # 先清理思考块
        cleaned_response = self._clean_text_output(response)
        json_match = re.search(r'```json\s*(.*?)\s*```', cleaned_response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        try:
            return json.loads(cleaned_response.strip())
        except json.JSONDecodeError:
            return None

    def _extract_issues(self, diagnosis_data: Dict[str, Any]) -> List[str]:
        """从诊断数据中提取问题列表"""
        issues = []
        diag = diagnosis_data.get("diagnosis", {})
        for category in ["grammar_issues", "style_issues", "terminology_issues"]:
            for item in diag.get(category, []):
                original = item.get("original", "")[:30]
                issue_type = item.get("type", "语言问题")
                severity = item.get("severity", 0.5)
                issues.append(f"[{issue_type}|{severity:.1f}] {original}...")
        return issues

    def _generate_recommendations_from_diagnosis(self, diagnosis_data: Dict[str, Any]) -> List[str]:
        """从诊断数据生成改进建议"""
        recommendations = []
        diag = diagnosis_data.get("diagnosis", {})

        grammar_count = len(diag.get("grammar_issues", []))
        style_count = len(diag.get("style_issues", []))
        term_count = len(diag.get("terminology_issues", []))

        if grammar_count > 0:
            recommendations.append(f"修正{grammar_count}处语法错误")
        if style_count > 0:
            recommendations.append(f"改进{style_count}处语言风格问题")
        if term_count > 0:
            recommendations.append(f"统一{term_count}处术语使用")
        if not recommendations:
            recommendations.append("语言质量良好，继续保持")

        return recommendations[:5]

    async def _fallback_polish(self, text: str, language: str) -> WritingOutput:
        """降级润色（当诊断失败时）"""
        prompt = f"""请润色以下{language}学术文本，保持原意，修正明显问题。

原文：
{text}

直接输出润色后的文本："""
        try:
            polished = await self._llm_call(prompt)
            cleaned_polished = self._clean_text_output(polished)
            return WritingOutput(
                success=True,
                result={
                    "original_text": text,
                    "polished_text": cleaned_polished.strip() if cleaned_polished else text,
                    "grammar_issues": 0,
                    "terminology_fixed": 0
                },
                agent_name=self.name,
                reasoning="简化润色（原始诊断失败）",
                quality_score=0.7
            )
        except Exception as e:
            self.logger.error(f"Fallback polish failed: {e}")
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
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

        if not text:
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Empty text"
            )

        # 构建诊断提示词
        prompt = f"""请对以下{language}学术文本进行全面的语言诊断与润色。

待处理文本：
{text}

请按照系统提示词中定义的诊断维度进行全面检查，并输出JSON格式的诊断结果。"""

        try:
            response = await self._llm_call(prompt)
            diagnosis_data = self._parse_diagnosis_response(response)

            if diagnosis_data:
                # 清理润色文本中的思考块、代码块等
                raw_polished = diagnosis_data.get("polished_text", text)
                polished_text = self._clean_text_output(raw_polished) if raw_polished else text
                return WritingOutput(
                    success=True,
                    result={
                        "original_text": text,
                        "polished_text": polished_text,
                        "diagnosis": diagnosis_data.get("diagnosis", {}),
                        "grammar_issues": len(diagnosis_data.get("diagnosis", {}).get("grammar_issues", [])),
                        "style_issues": len(diagnosis_data.get("diagnosis", {}).get("style_issues", [])),
                        "terminology_issues": len(diagnosis_data.get("diagnosis", {}).get("terminology_issues", []))
                    },
                    agent_name=self.name,
                    diagnosed_issues=self._extract_issues(diagnosis_data),
                    recommendations=self._generate_recommendations_from_diagnosis(diagnosis_data),
                    reasoning=diagnosis_data.get("summary", ""),
                    quality_score=diagnosis_data.get("overall_quality", 0.5)
                )
            else:
                return await self._fallback_polish(text, language)

        except Exception as e:
            self.logger.error(f"LanguagePolisherAgent execution failed: {e}")
            return await self._fallback_polish(text, language)

    # 保留diagnose方法作为兼容入口（调用execute）
    async def diagnose(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """诊断并润色学术文本（兼容problem_oriented版本）"""
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

        # 调用execute获取结果
        result = await self.execute({
            "text": text,
            "language": language
        })

        return AgentOutput(
            success=result.success,
            result=result.result,
            agent_name=self.name,
            diagnosed_issues=result.diagnosed_issues or [],
            recommendations=result.recommendations or [],
            quality_score=result.quality_score,
            error=result.error
        )
