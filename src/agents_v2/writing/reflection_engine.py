"""
反思引擎 - Reflection Engine

功能:
1. 自我反思机制
2. 质量评估
3. 改进建议生成
4. 迭代优化

设计原则:
- LLM驱动的反思
- 多维度评估
- 可配置的反思策略
"""
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ReflectionLevel(str, Enum):
    """反思级别"""
    NONE = "none"
    BASIC = "basic"
    DETAILED = "detailed"
    CRITICAL = "critical"


@dataclass
class ReflectionResult:
    """反思结果"""
    is_adequate: bool
    score: float
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class SelfCritique:
    """自我批评"""
    original_output: str
    critique: str
    revised_output: Optional[str] = None
    improvement_score: float = 0.0


class ReflectionEngine:
    """反思引擎"""

    def __init__(
        self,
        llm_provider: Optional[Callable] = None,
        reflection_level: ReflectionLevel = ReflectionLevel.DETAILED
    ):
        self.llm_provider = llm_provider
        self.reflection_level = reflection_level

        # 反思提示模板
        self._reflection_prompts = {
            ReflectionLevel.BASIC: """评估以下输出是否足够好:

输出: {output}

只需回答"是"或"否"。
""",
            ReflectionLevel.DETAILED: """详细评估以下输出:

输出: {output}

请分析:
1. 主要优点
2. 主要缺点
3. 改进建议

以JSON格式返回:
{{
    "is_adequate": true/false,
    "score": 0.0-1.0,
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["缺点1", "缺点2"],
    "suggestions": ["建议1", "建议2"],
    "reasoning": "总体评价"
}}
""",
            ReflectionLevel.CRITICAL: """严格评估以下输出，找出所有可能的问题:

输出: {output}
上下文: {context}

请进行严格评估，特别关注:
- 事实准确性
- 逻辑一致性
- 完整性
- 学术规范性

以JSON格式返回:
{{
    "is_adequate": true/false,
    "score": 0.0-1.0,
    "strengths": [...],
    "weaknesses": [...],
    "suggestions": [...],
    "reasoning": "..."
}}
"""
        }

    async def reflect(
        self,
        output: str,
        context: Optional[str] = None
    ) -> ReflectionResult:
        """反思输出

        Args:
            output: 待反思的输出
            context: 上下文信息

        Returns:
            ReflectionResult: 反思结果
        """
        if self.reflection_level == ReflectionLevel.NONE:
            return ReflectionResult(
                is_adequate=True,
                score=1.0,
                reasoning="反思已禁用"
            )

        if not self.llm_provider:
            return self._rule_based_reflection(output)

        prompt = self._reflection_prompts[self.reflection_level].format(
            output=output,
            context=context or ""
        )

        try:
            response = await self.llm_provider(prompt)
            return self._parse_reflection_response(response)
        except Exception:
            return self._rule_based_reflection(output)

    def _rule_based_reflection(self, output: str) -> ReflectionResult:
        """基于规则的反思"""
        score = 0.5
        weaknesses = []
        suggestions = []

        # 检查长度
        if len(output) < 100:
            weaknesses.append("输出过短，可能不完整")
            suggestions.append("增加详细内容")
            score -= 0.1
        elif len(output) > 10000:
            weaknesses.append("输出过长，可能过于冗余")
            suggestions.append("精简内容")
            score -= 0.1

        # 检查结构
        if "\n" not in output:
            weaknesses.append("缺少段落结构")
            suggestions.append("添加适当的段落分隔")
            score -= 0.1

        # 检查关键词
        required_keywords = ["论文", "研究", "分析"]
        has_keyword = any(kw in output for kw in required_keywords)
        if not has_keyword:
            weaknesses.append("可能偏离主题")
            suggestions.append("确保内容与主题相关")
            score -= 0.2

        # 基础分
        score = max(0.0, min(1.0, score + 0.3))

        return ReflectionResult(
            is_adequate=score >= 0.6,
            score=score,
            weaknesses=weaknesses,
            suggestions=suggestions,
            reasoning="基于规则的评估"
        )

    def _parse_reflection_response(self, response: str) -> ReflectionResult:
        """解析反思响应"""
        try:
            import json
            data = json.loads(response)

            return ReflectionResult(
                is_adequate=data.get("is_adequate", True),
                score=float(data.get("score", 0.5)),
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                suggestions=data.get("suggestions", []),
                reasoning=data.get("reasoning", "")
            )
        except Exception:
            return ReflectionResult(
                is_adequate=True,
                score=0.5,
                reasoning="解析失败，使用默认评估"
            )

    async def self_critique(
        self,
        output: str,
        criteria: Optional[List[str]] = None
    ) -> SelfCritique:
        """自我批评

        Args:
            output: 待批评的输出
            criteria: 评估标准

        Returns:
            SelfCritique: 自我批评结果
        """
        criteria = criteria or [
            "准确性",
            "完整性",
            "逻辑性",
            "学术规范性"
        ]

        criteria_text = "\n".join(f"- {c}" for c in criteria)

        prompt = f"""对以下输出进行严格批评:

输出:
{output}

评估标准:
{criteria_text}

请指出具体的问题和改进方法。
"""

        critique = await self.llm_provider(prompt) if self.llm_provider else "无法进行批评"

        return SelfCritique(
            original_output=output,
            critique=critique
        )

    async def improve(
        self,
        output: str,
        suggestions: List[str]
    ) -> str:
        """根据建议改进输出

        Args:
            output: 原始输出
            suggestions: 改进建议

        Returns:
            str: 改进后的输出
        """
        if not self.llm_provider:
            return output

        suggestions_text = "\n".join(f"- {s}" for s in suggestions)

        prompt = f"""根据以下建议改进输出:

原始输出:
{output}

改进建议:
{suggestions_text}

请提供改进后的版本，只返回改进后的内容，不要额外的解释。
"""

        improved = await self.llm_provider(prompt)
        return improved if improved else output


class ImprovementGenerator:
    """改进建议生成器"""

    def __init__(self, llm_provider: Optional[Callable] = None):
        self.llm_provider = llm_provider

    async def generate_suggestions(
        self,
        reflection_result: ReflectionResult,
        output_type: str = "论文"
    ) -> List[str]:
        """生成具体的改进建议

        Args:
            reflection_result: 反思结果
            output_type: 输出类型

        Returns:
            List[str]: 具体的改进建议
        """
        if not self.llm_provider:
            return reflection_result.suggestions

        weaknesses_text = "\n".join(
            f"- {w}" for w in reflection_result.weaknesses
        )

        prompt = f"""针对以下{output_type}的弱点，生成具体的改进建议:

弱点:
{weaknesses_text}

请生成3-5个具体可操作的改进建议。
"""

        response = await self.llm_provider(prompt)

        try:
            suggestions = [
                line.strip() for line in response.split("\n")
                if line.strip() and line.strip().startswith("-")
            ]
            return suggestions if suggestions else reflection_result.suggestions
        except Exception:
            return reflection_result.suggestions


# 便捷函数
async def reflect(
    output: str,
    level: ReflectionLevel = ReflectionLevel.DETAILED,
    context: Optional[str] = None
) -> ReflectionResult:
    """便捷反思函数"""
    engine = ReflectionEngine(reflection_level=level)
    return await engine.reflect(output, context)
