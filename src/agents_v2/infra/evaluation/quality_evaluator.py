"""
统一质量评估器 - Unified QualityEvaluator

7维度评分体系（来自前沿报告Harness设计）:
- 结构完整性 (structure)   0.20
- 逻辑连贯性 (logic)       0.20
- 原创性     (originality) 0.15
- 语言质量   (language)    0.15
- 引用规范   (citation)    0.15
- 内容完整   (completeness)0.10
- 格式规范   (format)      0.05

设计原则:
- LLM-as-Judge + 规则引擎混合评估
- 与现有 OutputValidator / RAGEvaluator 集成
- 可配置维度权重和阈值
"""

from src.agents_v2.logging_config import get_logging_logger

import re
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = get_logging_logger(__name__)


class EvalDimension(str, Enum):
    """评估维度"""
    STRUCTURE = "structure"
    LOGIC = "logic"
    ORIGINALITY = "originality"
    LANGUAGE = "language"
    CITATION = "citation"
    COMPLETENESS = "completeness"
    FORMAT = "format"


# 默认维度权重
DEFAULT_WEIGHTS: Dict[EvalDimension, float] = {
    EvalDimension.STRUCTURE:    0.20,
    EvalDimension.LOGIC:        0.20,
    EvalDimension.ORIGINALITY:  0.15,
    EvalDimension.LANGUAGE:     0.15,
    EvalDimension.CITATION:     0.15,
    EvalDimension.COMPLETENESS: 0.10,
    EvalDimension.FORMAT:       0.05,
}


@dataclass
class DimensionScore:
    """单维度评分"""
    dimension: EvalDimension
    score: float           # 0.0 - 1.0
    weight: float          # 权重
    details: str = ""      # 评分说明
    issues: List[str] = field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class QualityReport:
    """质量评估报告"""
    overall_score: float                     # 加权总分 0.0 - 1.0
    dimensions: Dict[str, DimensionScore]    # 各维度评分
    passed: bool                             # 是否通过质量门槛
    threshold: float                         # 质量门槛
    summary: str = ""                        # 总结
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 4),
            "passed": self.passed,
            "threshold": self.threshold,
            "dimensions": {
                k: {
                    "score": round(v.score, 4),
                    "weight": v.weight,
                    "weighted": round(v.weighted_score, 4),
                    "details": v.details,
                    "issues": v.issues,
                }
                for k, v in self.dimensions.items()
            },
            "summary": self.summary,
            "suggestions": self.suggestions,
        }


class RuleEngine:
    """规则引擎 - 基于规则的快速评估"""

    def evaluate_structure(self, text: str) -> DimensionScore:
        """评估结构完整性"""
        score = 1.0
        issues = []

        # 检查是否有标题结构
        headings = re.findall(r'^#{1,6}\s+.+', text, re.MULTILINE)
        if len(headings) < 2:
            score -= 0.3
            issues.append("缺少足够的标题结构")

        # 检查段落分布
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) < 3:
            score -= 0.2
            issues.append("段落数量不足")

        # 检查是否有引言/结论
        text_lower = text.lower()
        has_intro = any(kw in text_lower for kw in ['引言', 'introduction', '概述', '摘要'])
        has_conclusion = any(kw in text_lower for kw in ['结论', 'conclusion', '总结', '展望'])
        if not has_intro:
            score -= 0.15
            issues.append("缺少引言部分")
        if not has_conclusion:
            score -= 0.15
            issues.append("缺少结论部分")

        # 检查章节编号一致性
        section_numbers = re.findall(r'^#+\s*(\d+(?:\.\d+)*)', text, re.MULTILINE)
        if section_numbers and len(section_numbers) < 3:
            score -= 0.1
            issues.append("章节编号结构不完整")

        return DimensionScore(
            dimension=EvalDimension.STRUCTURE,
            score=max(0.0, min(1.0, score)),
            weight=DEFAULT_WEIGHTS[EvalDimension.STRUCTURE],
            details=f"标题{len(headings)}个, 段落{len(paragraphs)}个",
            issues=issues,
        )

    def evaluate_logic(self, text: str) -> DimensionScore:
        """评估逻辑连贯性"""
        score = 1.0
        issues = []

        # 检查逻辑连接词
        connectors = [
            '因此', '然而', '此外', '同时', '首先', '其次', '最后',
            'however', 'therefore', 'moreover', 'furthermore',
            'in addition', 'consequently', 'as a result',
        ]
        text_lower = text.lower()
        connector_count = sum(1 for c in connectors if c in text_lower)
        if connector_count < 3:
            score -= 0.2
            issues.append("逻辑连接词使用不足，段落间过渡生硬")

        # 检查段落长度均匀性
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and not p.strip().startswith('#')]
        if paragraphs:
            lengths = [len(p) for p in paragraphs]
            avg_len = sum(lengths) / len(lengths)
            if avg_len > 0:
                variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
                cv = (variance ** 0.5) / avg_len
                if cv > 1.5:
                    score -= 0.15
                    issues.append("段落长度差异过大，结构不均匀")

        # 检查是否有论点-论据模式
        evidence_patterns = ['研究表明', '数据显示', '根据', '实验表明', '文献', 'according to', 'research shows']
        evidence_count = sum(1 for p in evidence_patterns if p in text_lower)
        if evidence_count < 2:
            score -= 0.15
            issues.append("论据支撑不足，缺少引用研究或数据")

        return DimensionScore(
            dimension=EvalDimension.LOGIC,
            score=max(0.0, min(1.0, score)),
            weight=DEFAULT_WEIGHTS[EvalDimension.LOGIC],
            details=f"连接词{connector_count}个, 论据引用{evidence_count}处",
            issues=issues,
        )

    def evaluate_originality(self, text: str) -> DimensionScore:
        """评估原创性（规则层面）"""
        score = 0.8  # 默认中等偏上，需要LLM进一步评估
        issues = []

        # 检查是否有自己的分析和观点
        opinion_markers = ['本文认为', '我们认为', '笔者', '分析表明', '本文提出', 'we argue', 'we propose']
        text_lower = text.lower()
        opinion_count = sum(1 for m in opinion_markers if m in text_lower)
        if opinion_count < 1:
            score -= 0.2
            issues.append("缺少作者自己的分析观点")

        # 检查是否有创新性表述
        novel_markers = ['创新', '首次', '提出了一种', '新的方法', 'novel', 'propose', 'first time']
        novel_count = sum(1 for m in novel_markers if m in text_lower)
        if novel_count >= 1:
            score += 0.1

        return DimensionScore(
            dimension=EvalDimension.ORIGINALITY,
            score=max(0.0, min(1.0, score)),
            weight=DEFAULT_WEIGHTS[EvalDimension.ORIGINALITY],
            details=f"观点表达{opinion_count}处, 创新表述{novel_count}处",
            issues=issues,
        )

    def evaluate_language(self, text: str) -> DimensionScore:
        """评估语言质量"""
        score = 1.0
        issues = []

        # 检查重复用词
        words = re.findall(r'[一-鿿]+|[a-zA-Z]+', text.lower())
        if words:
            word_freq: Dict[str, int] = {}
            for w in words:
                if len(w) > 1:
                    word_freq[w] = word_freq.get(w, 0) + 1
            total = len(words)
            repeats = [(w, c) for w, c in word_freq.items() if c > max(5, total * 0.03)]
            if len(repeats) > 5:
                score -= 0.2
                issues.append(f"高频重复词{len(repeats)}个，词汇多样性不足")

        # 检查句子长度
        sentences = re.split(r'[。！？.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_sentence_len = sum(len(s) for s in sentences) / len(sentences)
            if avg_sentence_len > 100:
                score -= 0.15
                issues.append("平均句子过长，影响可读性")

        # 检查中英文混排规范
        bad_spacing = re.findall(r'[一-鿿][a-zA-Z]|[a-zA-Z][一-鿿]', text)
        if len(bad_spacing) > 10:
            score -= 0.1
            issues.append("中英文混排缺少空格")

        return DimensionScore(
            dimension=EvalDimension.LANGUAGE,
            score=max(0.0, min(1.0, score)),
            weight=DEFAULT_WEIGHTS[EvalDimension.LANGUAGE],
            details=f"{len(sentences)}句, 平均{avg_sentence_len:.0f}字/句" if sentences else "",
            issues=issues,
        )

    def evaluate_citation(self, text: str) -> DimensionScore:
        """评估引用规范"""
        score = 1.0
        issues = []

        # 检查引用标记
        citations = re.findall(r'\[[\d,\s\-]+\]|\([^)]*\d{4}[^)]*\)', text)
        if len(citations) < 2:
            score -= 0.3
            issues.append("引用数量不足")

        # 检查参考文献章节
        has_references = bool(re.search(r'(?i)#+\s*(参考文献|references|bibliography)', text))
        if not has_references:
            score -= 0.3
            issues.append("缺少参考文献章节")

        # 检查引用格式一致性
        bracket_citations = re.findall(r'\[\d+\]', text)
        paren_citations = re.findall(r'\(\w+,?\s*\d{4}\)', text)
        if bracket_citations and paren_citations:
            score -= 0.1
            issues.append("引用格式不统一（混用方括号和圆括号格式）")

        return DimensionScore(
            dimension=EvalDimension.CITATION,
            score=max(0.0, min(1.0, score)),
            weight=DEFAULT_WEIGHTS[EvalDimension.CITATION],
            details=f"引用{len(citations)}处, 参考文献章节{'有' if has_references else '无'}",
            issues=issues,
        )

    def evaluate_completeness(self, text: str, expected_sections: Optional[List[str]] = None) -> DimensionScore:
        """评估内容完整性"""
        score = 1.0
        issues = []

        # 检查总字数
        char_count = len(text)
        if char_count < 1000:
            score -= 0.4
            issues.append(f"内容过短（{char_count}字），缺少深度分析")
        elif char_count < 3000:
            score -= 0.15
            issues.append(f"内容较短（{char_count}字），可进一步展开")

        # 检查必要章节
        if expected_sections:
            text_lower = text.lower()
            missing = [s for s in expected_sections if s.lower() not in text_lower]
            if missing:
                penalty = min(0.4, len(missing) * 0.1)
                score -= penalty
                issues.append(f"缺少章节: {', '.join(missing)}")

        return DimensionScore(
            dimension=EvalDimension.COMPLETENESS,
            score=max(0.0, min(1.0, score)),
            weight=DEFAULT_WEIGHTS[EvalDimension.COMPLETENESS],
            details=f"总字数{char_count}",
            issues=issues,
        )

    def evaluate_format(self, text: str) -> DimensionScore:
        """评估格式规范"""
        score = 1.0
        issues = []

        # 检查Markdown语法
        lines = text.split('\n')
        empty_line_ratio = sum(1 for l in lines if not l.strip()) / max(len(lines), 1)
        if empty_line_ratio > 0.5:
            score -= 0.2
            issues.append("空行比例过高")

        # 检查列表格式
        lists = re.findall(r'^[\s]*[-*+]\s|^[\s]*\d+\.\s', text, re.MULTILINE)
        has_lists = len(lists) > 0

        # 检查代码块格式
        code_blocks = re.findall(r'```[\s\S]*?```', text)
        unclosed_backticks = text.count('```') % 2
        if unclosed_backticks:
            score -= 0.15
            issues.append("代码块未正确闭合")

        # 检查图片/表格标记
        images = re.findall(r'!\[.*?\]\(.*?\)', text)
        tables = re.findall(r'\|.*\|', text)

        return DimensionScore(
            dimension=EvalDimension.FORMAT,
            score=max(0.0, min(1.0, score)),
            weight=DEFAULT_WEIGHTS[EvalDimension.FORMAT],
            details=f"列表{len(lists)}个, 代码块{len(code_blocks)}个, 图片{len(images)}个",
            issues=issues,
        )


class LLMJudge:
    """LLM-as-Judge - 使用LLM进行深度评估"""

    def __init__(self, llm_caller: Optional[Callable] = None):
        """
        Args:
            llm_caller: LLM调用函数，签名 async (prompt: str) -> str
        """
        self._llm_caller = llm_caller

    async def evaluate_dimension(
        self,
        dimension: EvalDimension,
        text: str,
        rubric: Optional[str] = None,
    ) -> Optional[DimensionScore]:
        """使用LLM评估单个维度"""
        if not self._llm_caller:
            return None

        prompts = {
            EvalDimension.LOGIC: (
                "评估以下学术文本的逻辑连贯性。关注：论点是否有清晰的支撑、"
                "段落间是否有逻辑过渡、是否存在逻辑跳跃或矛盾。"
                "给出0-100的分数和简要说明。"
            ),
            EvalDimension.ORIGINALITY: (
                "评估以下学术文本的原创性。关注：是否有独立的分析观点、"
                "是否仅是复述他人工作还是有自己的见解、研究方法或结论是否有新意。"
                "给出0-100的分数和简要说明。"
            ),
            EvalDimension.LANGUAGE: (
                "评估以下学术文本的语言质量。关注：表述是否准确清晰、"
                "学术用语是否规范、是否存在语病或歧义。"
                "给出0-100的分数和简要说明。"
            ),
            EvalDimension.COMPLETENESS: (
                "评估以下学术文本的内容完整性。关注：是否覆盖了主题的关键方面、"
                "分析是否深入、是否存在重要遗漏。"
                "给出0-100的分数和简要说明。"
            ),
        }

        prompt_base = prompts.get(dimension)
        if not prompt_base:
            return None

        if rubric:
            prompt_base += f"\n\n评估标准：{rubric}"

        prompt = f"{prompt_base}\n\n文本：\n{text[:3000]}"

        try:
            response = await self._llm_caller(prompt)
            score, details = self._parse_llm_score(response)
            return DimensionScore(
                dimension=dimension,
                score=score,
                weight=DEFAULT_WEIGHTS[dimension],
                details=details,
            )
        except Exception as e:
            logger.warning(f"LLM judge failed for {dimension.value}: {e}")
            return None

    def _parse_llm_score(self, response: str) -> tuple:
        """解析LLM返回的分数"""
        # 尝试提取数字
        numbers = re.findall(r'(\d+(?:\.\d+)?)\s*[/／]\s*100', response)
        if numbers:
            score = float(numbers[0]) / 100.0
            return max(0.0, min(1.0, score)), response[:200]

        # 尝试提取百分比
        percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', response)
        if percentages:
            score = float(percentages[0]) / 100.0
            return max(0.0, min(1.0, score)), response[:200]

        # 默认中等分数
        return 0.6, response[:200]


class QualityEvaluator:
    """
    统一质量评估器

    结合规则引擎和LLM-as-Judge进行7维度评估。

    使用示例:
        evaluator = QualityEvaluator()

        # 同步评估（仅规则引擎）
        report = evaluator.evaluate_sync(text)

        # 异步评估（规则 + LLM）
        report = await evaluator.evaluate(text, rubric="学术论文标准")

        # 自定义权重
        evaluator = QualityEvaluator(weights={EvalDimension.STRUCTURE: 0.30})
    """

    def __init__(
        self,
        weights: Optional[Dict[EvalDimension, float]] = None,
        threshold: float = 0.6,
        llm_caller: Optional[Callable] = None,
    ):
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.threshold = threshold
        self.rule_engine = RuleEngine()
        self.llm_judge = LLMJudge(llm_caller)

    def evaluate_sync(
        self,
        text: str,
        expected_sections: Optional[List[str]] = None,
        rubric: Optional[str] = None,
    ) -> QualityReport:
        """同步评估（仅规则引擎）"""
        dimensions: Dict[str, DimensionScore] = {}

        dimensions[EvalDimension.STRUCTURE.value] = self.rule_engine.evaluate_structure(text)
        dimensions[EvalDimension.LOGIC.value] = self.rule_engine.evaluate_logic(text)
        dimensions[EvalDimension.ORIGINALITY.value] = self.rule_engine.evaluate_originality(text)
        dimensions[EvalDimension.LANGUAGE.value] = self.rule_engine.evaluate_language(text)
        dimensions[EvalDimension.CITATION.value] = self.rule_engine.evaluate_citation(text)
        dimensions[EvalDimension.COMPLETENESS.value] = self.rule_engine.evaluate_completeness(text, expected_sections)
        dimensions[EvalDimension.FORMAT.value] = self.rule_engine.evaluate_format(text)

        return self._build_report(dimensions)

    async def evaluate(
        self,
        text: str,
        expected_sections: Optional[List[str]] = None,
        rubric: Optional[str] = None,
    ) -> QualityReport:
        """异步评估（规则 + LLM）"""
        # 规则引擎评估
        dimensions: Dict[str, DimensionScore] = {}

        dimensions[EvalDimension.STRUCTURE.value] = self.rule_engine.evaluate_structure(text)
        dimensions[EvalDimension.CITATION.value] = self.rule_engine.evaluate_citation(text)
        dimensions[EvalDimension.FORMAT.value] = self.rule_engine.evaluate_format(text)
        dimensions[EvalDimension.COMPLETENESS.value] = self.rule_engine.evaluate_completeness(text, expected_sections)

        # LLM评估（逻辑、原创性、语言、完整性）
        llm_dimensions = [
            EvalDimension.LOGIC,
            EvalDimension.ORIGINALITY,
            EvalDimension.LANGUAGE,
            EvalDimension.COMPLETENESS,
        ]

        for dim in llm_dimensions:
            llm_result = await self.llm_judge.evaluate_dimension(dim, text, rubric)
            if llm_result:
                # LLM结果优先，规则结果作为fallback
                rule_result = getattr(self.rule_engine, f"evaluate_{dim.value}")(text)
                # 取LLM和规则的平均
                merged_score = (llm_result.score + rule_result.score) / 2
                dimensions[dim.value] = DimensionScore(
                    dimension=dim,
                    score=merged_score,
                    weight=self.weights.get(dim, DEFAULT_WEIGHTS[dim]),
                    details=f"LLM: {llm_result.details[:80]} | 规则: {rule_result.details}",
                    issues=rule_result.issues,
                )
            else:
                # 无LLM结果，使用规则
                dimensions[dim.value] = getattr(self.rule_engine, f"evaluate_{dim.value}")(text)

        return self._build_report(dimensions)

    def _build_report(self, dimensions: Dict[str, DimensionScore]) -> QualityReport:
        """构建评估报告"""
        overall = sum(d.weighted_score for d in dimensions.values())
        passed = overall >= self.threshold

        # 收集所有issues
        all_issues = []
        for d in dimensions.values():
            all_issues.extend(d.issues)

        # 生成建议
        suggestions = []
        for name, dim in sorted(dimensions.items(), key=lambda x: x[1].score):
            if dim.score < 0.6:
                suggestions.append(f"提升{dim.dimension.value}: {dim.details}")
                if dim.issues:
                    suggestions.extend(f"  - {i}" for i in dim.issues[:2])

        summary_parts = [f"总分{overall:.2f}({'通过' if passed else '未通过'}，门槛{self.threshold})"]
        weak = [name for name, d in dimensions.items() if d.score < 0.6]
        if weak:
            summary_parts.append(f"薄弱维度: {', '.join(weak)}")

        return QualityReport(
            overall_score=overall,
            dimensions=dimensions,
            passed=passed,
            threshold=self.threshold,
            summary="; ".join(summary_parts),
            suggestions=suggestions[:10],
        )


def create_evaluator(
    threshold: float = 0.6,
    llm_caller: Optional[Callable] = None,
) -> QualityEvaluator:
    """创建质量评估器"""
    return QualityEvaluator(threshold=threshold, llm_caller=llm_caller)
