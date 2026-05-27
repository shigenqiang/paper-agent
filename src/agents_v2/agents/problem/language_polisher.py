"""
LanguagePolisherAgent - 语言润色Agent

针对问题：语言表达问题

职责：
- 语法检查
- 学术语言规范
- 术语一致性
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

import json

from .base_problem_agent import ProblemAgentBase, AgentOutput, LLMConfig

logger = get_logging_logger(__name__)


class LanguagePolisherAgent(ProblemAgentBase):
    """
    LanguagePolisherAgent - 语言润色

    针对问题：
    - 语句不通顺
    - 语法错误
    - 学术规范欠缺
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

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = self.SYSTEM_PROMPT_TEMPLATE + "\n\n" + self.FEW_SHOT_EXAMPLES
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
        诊断并润色学术文本

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

        # 构建诊断提示词
        domain_context = f"研究领域：{domain}" if domain else "通用学术文本"
        prompt = f"""请对以下{language}学术文本进行全面的语言诊断与润色。

{domain_context}

待处理文本：
{text}

请按照系统提示词中定义的诊断维度进行全面检查，并输出JSON格式的诊断结果。"""

        try:
            response = await self._llm_call(prompt)
            # 尝试解析LLM返回的JSON
            diagnosis_data = self._parse_diagnosis_response(response)

            if diagnosis_data:
                return AgentOutput(
                    success=True,
                    result=diagnosis_data,
                    agent_name=self.name,
                    diagnosed_issues=self._extract_issues(diagnosis_data),
                    recommendations=self._generate_recommendations_from_diagnosis(diagnosis_data),
                    quality_score=diagnosis_data.get("overall_quality", 0.5)
                )
            else:
                # JSON解析失败，降级到简单润色
                return await self._fallback_polish(text, language)

        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:177] Language diagnosis failed: {e}")
            return await self._fallback_polish(text, language)

    def _parse_diagnosis_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析LLM返回的诊断结果"""
        import re
        # 尝试提取JSON块
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed in _parse_diagnosis_response (json_match): {e}, raw_input={json_match.group(1)[:500] if json_match.group(1) else 'empty'}")
                pass
        # 尝试直接解析
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed in _parse_diagnosis_response: {e}, raw_input={response.strip()[:500] if response.strip() else 'empty'}")
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

    async def _fallback_polish(self, text: str, language: str) -> AgentOutput:
        """降级润色（当诊断失败时）"""
        prompt = f"""请润色以下{language}学术文本，保持原意，修正明显问题。

原文：
{text}

直接输出润色后的文本："""
        try:
            polished = await self._llm_call(prompt)
            import re
            cleaned = re.sub(r'<think>.*?</think>', '', polished, flags=re.DOTALL)
            cleaned = re.sub(r'```json\s*', '', cleaned)
            cleaned = re.sub(r'```\s*', '', cleaned)
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            cleaned = cleaned.strip()
            return AgentOutput(
                success=True,
                result={
                    "diagnosis": {"grammar_issues": [], "style_issues": [], "terminology_issues": []},
                    "overall_quality": 0.7,
                    "polished_text": cleaned,
                    "summary": "简化润色（原始诊断失败）"
                },
                agent_name=self.name,
                diagnosed_issues=["简化诊断模式"],
                recommendations=["建议人工复核润色结果"],
                quality_score=0.7
            )
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:252] Fallback polish failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["语言润色失败"],
                recommendations=["请检查文本格式"],
                quality_score=0.0,
                error=str(e)
            )

    def _truncate(self, text: str, max_length: int) -> str:
        if not text:
            return ""
        return text[:max_length] + "..." if len(text) > max_length else text
