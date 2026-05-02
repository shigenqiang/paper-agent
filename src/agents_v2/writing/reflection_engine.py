"""
反思引擎 - Reflection Engine

功能:
1. 自我反思机制
2. 质量评估
3. 改进建议生成
4. 迭代优化
5. SciSage 式多层反思（Outline → Section → Document）

设计原则:
- LLM驱动的反思
- 多维度评估
- 可配置的反思策略
- 分层反思，从宏观结构到微观表达
"""
from src.agents_v2.logging_config import get_logging_logger

import json

from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = get_logging_logger(__name__)


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


# ===================================================================
# SciSage 式多层 Reflector
# ===================================================================


class ReflectionLayer(str, Enum):
    """反思层次"""
    OUTLINE = "outline"       # 大纲级：宏观结构、章节逻辑
    SECTION = "section"       # 章节级：段落质量、论证、引用
    DOCUMENT = "document"     # 文档级：全局一致性、风格、完整性


@dataclass
class LayerReflectionResult:
    """单层反思结果"""
    layer: ReflectionLayer
    score: float                              # 0.0 ~ 1.0
    passed: bool                              # 是否通过质量门控
    issues: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "layer": self.layer.value,
            "score": round(self.score, 3),
            "passed": self.passed,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "dimension_scores": {k: round(v, 3) for k, v in self.dimension_scores.items()},
            "reasoning": self.reasoning,
        }


@dataclass
class MultiLayerReflectionResult:
    """多层反思总结果"""
    outline_result: Optional[LayerReflectionResult] = None
    section_results: List[LayerReflectionResult] = field(default_factory=list)
    document_result: Optional[LayerReflectionResult] = None
    overall_score: float = 0.0
    overall_passed: bool = False
    total_issues: int = 0

    def to_dict(self) -> dict:
        return {
            "outline": self.outline_result.to_dict() if self.outline_result else None,
            "sections": [s.to_dict() for s in self.section_results],
            "document": self.document_result.to_dict() if self.document_result else None,
            "overall_score": round(self.overall_score, 3),
            "overall_passed": self.overall_passed,
            "total_issues": self.total_issues,
        }


class OutlineReflector:
    """大纲级反思器 — 评估宏观结构质量

    评估维度：
    - 结构完整性：章节是否覆盖了论文核心要素
    - 逻辑连贯性：章节排列是否有清晰的逻辑主线
    - 层次合理性：标题层级是否恰当
    - 研究覆盖度：是否涵盖了足够的研究维度
    """

    DIMENSIONS = {
        "structural_completeness": 0.30,
        "logical_coherence": 0.30,
        "hierarchy合理性": 0.20,
        "research_coverage": 0.20,
    }

    SYSTEM_PROMPT = """你是一位学术论文结构专家。请评估以下论文大纲的质量。

评估维度（请逐一打分 0.0-1.0）：
1. structural_completeness（结构完整性）：大纲是否包含引言、文献综述、方法、结果、讨论、结论等核心章节
2. logical_coherence（逻辑连贯性）：章节排列是否有清晰的逻辑递进关系
3. hierarchy合理性（层次合理性）：标题层级（章/节/小节）是否恰当，粒度是否均匀
4. research_coverage（研究覆盖度）：是否涵盖了足够的研究维度，有无重大遗漏

请以 JSON 格式返回：
{{
    "dimension_scores": {{"structural_completeness": 0.0, "logical_coherence": 0.0, "hierarchy合理性": 0.0, "research_coverage": 0.0}},
    "issues": [{{"dimension": "...", "description": "...", "severity": "high/medium/low"}}],
    "suggestions": ["建议1", "建议2"],
    "reasoning": "总体评价"
}}"""

    def __init__(self, llm_provider: Optional[Callable] = None):
        self.llm_provider = llm_provider

    async def reflect(self, outline: Dict[str, Any]) -> LayerReflectionResult:
        """反思大纲

        Args:
            outline: 大纲数据，格式如 {"title": "...", "sections": [{"title": "...", "subsections": [...]}]}

        Returns:
            LayerReflectionResult
        """
        if not self.llm_provider:
            return self._rule_based_reflect(outline)

        outline_text = json.dumps(outline, ensure_ascii=False, indent=2)
        prompt = f"{self.SYSTEM_PROMPT}\n\n论文大纲：\n{outline_text}"

        try:
            response = await self.llm_provider(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.warning(f"OutlineReflector LLM failed: {e}")
            return self._rule_based_reflect(outline)

    def _rule_based_reflect(self, outline: Dict[str, Any]) -> LayerReflectionResult:
        """基于规则的大纲反思"""
        sections = outline.get("sections", [])
        issues = []
        scores = {}

        # 结构完整性
        section_titles = [s.get("title", "").lower() for s in sections]
        required_elements = ["引言", "introduction", "方法", "method", "结果", "result", "讨论", "discussion", "结论", "conclusion"]
        found = sum(1 for e in required_elements if any(e in t for t in section_titles))
        scores["structural_completeness"] = min(1.0, found / 4)
        if scores["structural_completeness"] < 0.7:
            issues.append({"dimension": "structural_completeness", "description": "缺少核心章节（引言/方法/结果/讨论/结论）", "severity": "high"})

        # 逻辑连贯性
        scores["logical_coherence"] = 0.7 if len(sections) >= 3 else 0.4
        if len(sections) < 3:
            issues.append({"dimension": "logical_coherence", "description": "章节数量过少，逻辑层次不足", "severity": "medium"})

        # 层次合理性
        has_subsections = any(s.get("subsections") for s in sections)
        scores["hierarchy合理性"] = 0.8 if has_subsections else 0.5

        # 研究覆盖度
        scores["research_coverage"] = min(1.0, len(sections) / 5)

        avg_score = sum(scores.values()) / len(scores)

        return LayerReflectionResult(
            layer=ReflectionLayer.OUTLINE,
            score=avg_score,
            passed=avg_score >= 0.6,
            issues=issues,
            suggestions=["建议增加核心章节" if scores["structural_completeness"] < 0.7 else ""],
            dimension_scores=scores,
            reasoning="基于规则的大纲评估",
        )

    def _parse_response(self, response: str) -> LayerReflectionResult:
        """解析 LLM 响应"""
        try:
            data = json.loads(response)
            dim_scores = data.get("dimension_scores", {})
            avg = sum(dim_scores.values()) / len(dim_scores) if dim_scores else 0.5
            return LayerReflectionResult(
                layer=ReflectionLayer.OUTLINE,
                score=avg,
                passed=avg >= 0.6,
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                dimension_scores=dim_scores,
                reasoning=data.get("reasoning", ""),
            )
        except Exception:
            return LayerReflectionResult(
                layer=ReflectionLayer.OUTLINE,
                score=0.5,
                passed=True,
                reasoning="解析失败，使用默认评估",
            )


class SectionReflector:
    """章节级反思器 — 评估单个章节的写作质量

    评估维度：
    - argumentation（论证质量）：论点是否有充分的论据支撑
    - citation_adequacy（引用充分性）：引用是否充足且相关
    - paragraph_coherence（段落连贯性）：段落间是否有清晰的过渡
    - academic_language（学术语言）：语言是否符合学术规范
    """

    DIMENSIONS = {
        "argumentation": 0.30,
        "citation_adequacy": 0.25,
        "paragraph_coherence": 0.25,
        "academic_language": 0.20,
    }

    SYSTEM_PROMPT = """你是一位学术写作专家。请评估以下论文章节的质量。

评估维度（请逐一打分 0.0-1.0）：
1. argumentation（论证质量）：论点是否有充分的论据支撑，推理是否严密
2. citation_adequacy（引用充分性）：引用数量是否充足，引用是否与论点相关
3. paragraph_coherence（段落连贯性）：段落间是否有清晰的逻辑过渡
4. academic_language（学术语言）：用词是否准确、正式，是否符合学术写作规范

请以 JSON 格式返回：
{{
    "dimension_scores": {{"argumentation": 0.0, "citation_adequacy": 0.0, "paragraph_coherence": 0.0, "academic_language": 0.0}},
    "issues": [{{"dimension": "...", "description": "...", "severity": "high/medium/low", "location": "段落位置（如有）"}}],
    "suggestions": ["建议1", "建议2"],
    "reasoning": "总体评价"
}}"""

    def __init__(self, llm_provider: Optional[Callable] = None):
        self.llm_provider = llm_provider

    async def reflect(self, section_title: str, section_content: str) -> LayerReflectionResult:
        """反思单个章节

        Args:
            section_title: 章节标题
            section_content: 章节内容

        Returns:
            LayerReflectionResult
        """
        if not self.llm_provider:
            return self._rule_based_reflect(section_title, section_content)

        prompt = f"{self.SYSTEM_PROMPT}\n\n章节标题：{section_title}\n\n章节内容：\n{section_content}"

        try:
            response = await self.llm_provider(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.warning(f"SectionReflector LLM failed: {e}")
            return self._rule_based_reflect(section_title, section_content)

    def _rule_based_reflect(self, title: str, content: str) -> LayerReflectionResult:
        """基于规则的章节反思"""
        issues = []
        scores = {}

        # 论证质量
        sentences = [s.strip() for s in content.split("。") if s.strip()]
        scores["argumentation"] = min(1.0, len(sentences) / 10)
        if len(sentences) < 5:
            issues.append({"dimension": "argumentation", "description": "论证内容过短，论据不充分", "severity": "high"})

        # 引用充分性
        import re
        citations = re.findall(r'\[\d+\]|\([A-Za-z]+,?\s*\d{4}\)', content)
        scores["citation_adequacy"] = min(1.0, len(citations) / 3)
        if len(citations) < 2:
            issues.append({"dimension": "citation_adequacy", "description": "引用数量不足", "severity": "medium"})

        # 段落连贯性
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        scores["paragraph_coherence"] = min(1.0, len(paragraphs) / 3)

        # 学术语言
        informal_words = ["我觉得", "我认为", "其实", " basically", " actually"]
        has_informal = any(w in content.lower() for w in informal_words)
        scores["academic_language"] = 0.5 if has_informal else 0.8
        if has_informal:
            issues.append({"dimension": "academic_language", "description": "包含非正式用语", "severity": "low"})

        avg = sum(scores.values()) / len(scores)
        return LayerReflectionResult(
            layer=ReflectionLayer.SECTION,
            score=avg,
            passed=avg >= 0.5,
            issues=issues,
            dimension_scores=scores,
            reasoning="基于规则的章节评估",
        )

    def _parse_response(self, response: str) -> LayerReflectionResult:
        try:
            data = json.loads(response)
            dim_scores = data.get("dimension_scores", {})
            avg = sum(dim_scores.values()) / len(dim_scores) if dim_scores else 0.5
            return LayerReflectionResult(
                layer=ReflectionLayer.SECTION,
                score=avg,
                passed=avg >= 0.5,
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                dimension_scores=dim_scores,
                reasoning=data.get("reasoning", ""),
            )
        except Exception:
            return LayerReflectionResult(
                layer=ReflectionLayer.SECTION,
                score=0.5,
                passed=True,
                reasoning="解析失败，使用默认评估",
            )


class DocumentReflector:
    """文档级反思器 — 评估全文的整体质量

    评估维度：
    - cross_section_consistency（跨章节一致性）：术语、风格是否统一
    - overall_coherence（整体连贯性）：全文是否有清晰的主线
    - completeness（内容完整性）：是否覆盖了大纲中的所有要点
    - style_uniformity（风格统一性）：语言风格、人称是否一致
    """

    DIMENSIONS = {
        "cross_section_consistency": 0.30,
        "overall_coherence": 0.30,
        "completeness": 0.20,
        "style_uniformity": 0.20,
    }

    SYSTEM_PROMPT = """你是一位资深学术论文审稿人。请对以下完整论文进行全局评估。

评估维度（请逐一打分 0.0-1.0）：
1. cross_section_consistency（跨章节一致性）：各章节使用的术语、定义是否一致，有无矛盾
2. overall_coherence（整体连贯性）：全文是否有一条清晰的逻辑主线贯穿
3. completeness（内容完整性）：大纲中提出的问题是否都在正文中得到了回答
4. style_uniformity（风格统一性）：语言风格、人称、时态是否全文统一

请以 JSON 格式返回：
{{
    "dimension_scores": {{"cross_section_consistency": 0.0, "overall_coherence": 0.0, "completeness": 0.0, "style_uniformity": 0.0}},
    "issues": [{{"dimension": "...", "description": "...", "severity": "high/medium/low", "sections_involved": ["章节1", "章节2"]}}],
    "suggestions": ["建议1", "建议2"],
    "reasoning": "总体评价"
}}"""

    def __init__(self, llm_provider: Optional[Callable] = None):
        self.llm_provider = llm_provider

    async def reflect(
        self,
        full_text: str,
        outline: Optional[Dict[str, Any]] = None,
    ) -> LayerReflectionResult:
        """反思整篇文档

        Args:
            full_text: 完整论文文本
            outline: 论文大纲（用于检查完整性）

        Returns:
            LayerReflectionResult
        """
        if not self.llm_provider:
            return self._rule_based_reflect(full_text, outline)

        outline_text = ""
        if outline:
            outline_text = f"\n\n论文大纲（用于检查完整性）：\n{json.dumps(outline, ensure_ascii=False, indent=2)}"

        prompt = f"{self.SYSTEM_PROMPT}\n\n论文全文（前 8000 字）：\n{full_text[:8000]}{outline_text}"

        try:
            response = await self.llm_provider(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.warning(f"DocumentReflector LLM failed: {e}")
            return self._rule_based_reflect(full_text, outline)

    def _rule_based_reflect(self, full_text: str, outline: Optional[Dict] = None) -> LayerReflectionResult:
        """基于规则的文档反思"""
        issues = []
        scores = {}

        # 跨章节一致性：检查术语使用
        import re
        sections = re.split(r'\n#{1,3}\s+', full_text)
        if len(sections) < 2:
            scores["cross_section_consistency"] = 0.5
        else:
            scores["cross_section_consistency"] = 0.7  # 默认

        # 整体连贯性
        total_chars = len(full_text)
        scores["overall_coherence"] = min(1.0, total_chars / 3000)
        if total_chars < 1000:
            issues.append({"dimension": "overall_coherence", "description": "全文过短，可能不完整", "severity": "high"})

        # 完整性
        if outline:
            outline_sections = outline.get("sections", [])
            outline_titles = [s.get("title", "") for s in outline_sections]
            found = sum(1 for t in outline_titles if t in full_text)
            scores["completeness"] = found / len(outline_titles) if outline_titles else 0.5
        else:
            scores["completeness"] = 0.5

        # 风格统一性
        scores["style_uniformity"] = 0.7  # 默认

        avg = sum(scores.values()) / len(scores)
        return LayerReflectionResult(
            layer=ReflectionLayer.DOCUMENT,
            score=avg,
            passed=avg >= 0.5,
            issues=issues,
            dimension_scores=scores,
            reasoning="基于规则的文档评估",
        )

    def _parse_response(self, response: str) -> LayerReflectionResult:
        try:
            data = json.loads(response)
            dim_scores = data.get("dimension_scores", {})
            avg = sum(dim_scores.values()) / len(dim_scores) if dim_scores else 0.5
            return LayerReflectionResult(
                layer=ReflectionLayer.DOCUMENT,
                score=avg,
                passed=avg >= 0.5,
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                dimension_scores=dim_scores,
                reasoning=data.get("reasoning", ""),
            )
        except Exception:
            return LayerReflectionResult(
                layer=ReflectionLayer.DOCUMENT,
                score=0.5,
                passed=True,
                reasoning="解析失败，使用默认评估",
            )


class MultiLayerReflector:
    """SciSage 式多层反思器

    按三个层次依次反思：
    1. Outline-Level：评估大纲结构
    2. Section-Level：逐章节评估写作质量
    3. Document-Level：评估全文整体一致性

    使用示例:
        reflector = MultiLayerReflector(llm_provider=my_llm)

        result = await reflector.reflect_all(
            outline={"title": "...", "sections": [...]},
            sections=[("引言", "..."), ("方法", "...")],
            full_text="完整论文文本",
        )

        print(result.overall_score)
        print(result.to_dict())
    """

    # 各层权重
    LAYER_WEIGHTS = {
        ReflectionLayer.OUTLINE: 0.25,
        ReflectionLayer.SECTION: 0.40,  # 所有章节的平均
        ReflectionLayer.DOCUMENT: 0.35,
    }

    def __init__(
        self,
        llm_provider: Optional[Callable] = None,
        quality_threshold: float = 0.6,
    ):
        """
        Args:
            llm_provider: LLM 调用函数（async callable）
            quality_threshold: 质量门控阈值
        """
        self.llm_provider = llm_provider
        self.quality_threshold = quality_threshold
        self.outline_reflector = OutlineReflector(llm_provider)
        self.section_reflector = SectionReflector(llm_provider)
        self.document_reflector = DocumentReflector(llm_provider)

    async def reflect_outline(self, outline: Dict[str, Any]) -> LayerReflectionResult:
        """大纲级反思"""
        return await self.outline_reflector.reflect(outline)

    async def reflect_section(self, title: str, content: str) -> LayerReflectionResult:
        """章节级反思"""
        return await self.section_reflector.reflect(title, content)

    async def reflect_document(
        self,
        full_text: str,
        outline: Optional[Dict[str, Any]] = None,
    ) -> LayerReflectionResult:
        """文档级反思"""
        return await self.document_reflector.reflect(full_text, outline)

    async def reflect_all(
        self,
        outline: Optional[Dict[str, Any]] = None,
        sections: Optional[List[Tuple[str, str]]] = None,
        full_text: Optional[str] = None,
    ) -> MultiLayerReflectionResult:
        """执行完整的多层反思

        Args:
            outline: 大纲数据（如提供则执行大纲级反思）
            sections: 章节列表 [(title, content), ...]（如提供则执行章节级反思）
            full_text: 完整文本（如提供则执行文档级反思）

        Returns:
            MultiLayerReflectionResult
        """
        result = MultiLayerReflectionResult()

        # Layer 1: Outline
        if outline:
            logger.info("MultiLayerReflector: starting outline reflection")
            result.outline_result = await self.reflect_outline(outline)

        # Layer 2: Sections
        if sections:
            logger.info(f"MultiLayerReflector: reflecting {len(sections)} sections")
            for title, content in sections:
                section_result = await self.reflect_section(title, content)
                result.section_results.append(section_result)

        # Layer 3: Document
        if full_text:
            logger.info("MultiLayerReflector: starting document reflection")
            result.document_result = await self.reflect_document(full_text, outline)

        # 计算总分
        scores = []
        weights = []

        if result.outline_result:
            scores.append(result.outline_result.score)
            weights.append(self.LAYER_WEIGHTS[ReflectionLayer.OUTLINE])

        if result.section_results:
            section_avg = sum(s.score for s in result.section_results) / len(result.section_results)
            scores.append(section_avg)
            weights.append(self.LAYER_WEIGHTS[ReflectionLayer.SECTION])

        if result.document_result:
            scores.append(result.document_result.score)
            weights.append(self.LAYER_WEIGHTS[ReflectionLayer.DOCUMENT])

        if scores:
            result.overall_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        result.overall_passed = result.overall_score >= self.quality_threshold

        # 统计总 issue 数
        all_issues = []
        if result.outline_result:
            all_issues.extend(result.outline_result.issues)
        for s in result.section_results:
            all_issues.extend(s.issues)
        if result.document_result:
            all_issues.extend(result.document_result.issues)
        result.total_issues = len(all_issues)

        logger.info(
            f"MultiLayerReflector: done. score={result.overall_score:.3f}, "
            f"passed={result.overall_passed}, issues={result.total_issues}"
        )
        return result
