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
    - 格式修正（LaTeX公式、标题层级、段落间距）
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None, use_trinka: bool = True):
        system_prompt = """你是一个专业的学术论文语言润色与格式修正专家。

## 角色定义
你是一位资深的学术论文编辑，拥有丰富的论文润色和格式规范经验。你的工作是为学者和研究人员提供高质量的语言润色和格式修正服务。

## 能力边界
1. **语法检查与纠正**
   - 检测并纠正语法错误
   - 修正主谓不一致、时态错误等问题
   - 修正冠词、介词等使用错误

2. **术语规范化**
   - 统一专业术语的使用
   - 确保同一术语在全文中表达一致
   - 修正不规范的术语翻译

3. **句式优化**
   - 简化冗长句式
   - 改善句子流畅度
   - 优化段落逻辑衔接

4. **格式修正**
   - 修正 LaTeX 公式语法，确保公式渲染正确
   - 统一标题层级（# 一级、## 二级、### 三级）
   - 统一段落间距和缩进
   - 修正列表格式（有序/无序列表规范）
   - 确保引用格式一致

5. **中英混合处理**
   - 正确处理中英文混合的学术文本
   - 保留关键英文术语
   - 确保中文表达流畅自然

## 行为准则
1. **保持原意**：润色后必须保持原文的核心含义和学术观点
2. **最小修改**：在保证质量的前提下，尽量少的改动原文
3. **逐项说明**：对每项修改提供简要说明（可选）
4. **学术规范**：确保修正后的内容符合学术论文写作规范

## 约束限制
1. 只返回润色后的内容，不返回解释（除非用户要求）
2. 不添加原文没有的新内容
3. 不删除原文的重要信息
4. 对于不确定的修改，保留原文

## 输出格式
直接返回修正后的 Markdown 格式内容。
"""
        super().__init__(
            name="language_polisher",
            llm_config=llm_config,
            description="语言润色与格式修正",
            system_prompt=system_prompt
        )
        self._trinka = TrinkaGrammarChecker() if use_trinka else None

    async def _check_grammar_with_trinka(
        self,
        text: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """使用 Trinka API 进行专业语法检查"""
        if not self._trinka:
            return []

        result = await self._trinka.check(text, language)
        if result.get("success"):
            return result.get("issues", [])
        else:
            logger.info(f"Trinka check failed: {result.get('error')}, falling back to LLM")
            return []

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
        """检查语法 - 优先使用 Trinka API，回退到 LLM"""
        # 优先使用 Trinka API 进行专业检查
        if self._trinka and language == "en":
            trinka_issues = await self._check_grammar_with_trinka(text, language)
            if trinka_issues:
                return [{
                    "location": issue.get("location", {}),
                    "original": issue.get("original", ""),
                    "issue": issue.get("message", ""),
                    "suggestion": issue.get("replacement", "")
                } for issue in trinka_issues]

        # 回退到 LLM 检查
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
            "light": "轻度润色，只做必要的语法修正和格式调整",
            "medium": "中度润色，优化表达，提升可读性，修正格式",
            "heavy": "深度润色，全面优化句式和表达，修正所有格式问题"
        }

        # 根据语言选择system prompt
        zh_system = "你是一个专业的学术论文润色专家，擅长中文学术写作。"
        en_system = "You are a professional academic writing polish expert, skilled in English academic writing."
        system_msg = zh_system if language == "zh" else en_system

        prompt = f"""## 任务
对以下学术论文内容进行{level_desc.get(level, '中等')}润色。

## 内容
{text}

## 润色要求

### 1. 语法与表达
- 修正语法错误
- 优化句式结构
- 提升表达的准确性和流畅性
- 保持原文的核心含义和学术观点

### 2. 格式修正（关键）
- **LaTeX 公式**：修正公式语法，确保渲染正确
  - 行内公式 `$...$`，独立公式 `$$...$$`
  - 修正公式中的符号、转义、环境标签
- **标题层级**：确保 Markdown 标题层级正确
  - `#` 一级标题（章节）
  - `##` 二级标题（子章节）
  - `###` 三级标题（子子章节）
- **段落间距**：统一段落间距，修正多余的空行
- **列表格式**：规范有序和无序列表的格式
- **引用格式**：确保引用格式一致

### 3. 术语规范
- 同一术语在全文中保持一致
- 使用标准的学术术语

### 4. 输出要求
- 直接输出修正后的 Markdown 内容
- 不要添加解释或说明
- 不要添加原文没有的新内容
- 对于不确定的修改，保留原文

## 语言
{language}（{level}）

请输出润色后的内容：
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
