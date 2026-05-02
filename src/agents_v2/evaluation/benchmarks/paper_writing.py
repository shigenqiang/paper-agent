"""
论文写作专项基准 - Paper Agent专属评估维度

评估维度:
- 选题质量 (新颖性、可行性)
- 文献覆盖 (相关性、召回率)
- 论证逻辑 (严密性、完整性)
- 语言表达 (学术性、语法正确率)
- 格式规范 (引用格式、参考文献)
- 整体完成度
"""
from src.agents_v2.logging_config import get_logging_logger

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = get_logging_logger(__name__)


@dataclass
class DimensionScore:
    """维度评分"""
    dimension: str
    score: float  # 0-10
    weight: float
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class PaperWritingResult:
    """论文写作评估结果"""
    overall_score: float  # 0-10
    topic_quality: DimensionScore
    literature_coverage: DimensionScore
    thesis_clarity: DimensionScore
    outline_quality: DimensionScore
    draft_quality: DimensionScore
    language_quality: DimensionScore
    dimension_scores: Dict[str, float]
    feedback: List[str]
    grade: str  # A/B/C/D/F


class PaperWritingBenchmark:
    """论文写作专项基准"""

    # 各维度权重
    DIMENSION_WEIGHTS = {
        "topic_quality": 0.20,       # 选题质量
        "literature_coverage": 0.15, # 文献覆盖
        "thesis_clarity": 0.15,      # 论题清晰度
        "outline_quality": 0.15,      # 大纲质量
        "draft_quality": 0.20,       # 草稿质量
        "language_quality": 0.15     # 语言质量
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """初始化论文写作基准

        Args:
            weights: 自定义维度权重
        """
        self.weights = weights or self.DIMENSION_WEIGHTS

    async def evaluate(self, paper_content: Dict[str, Any]) -> PaperWritingResult:
        """评估论文质量

        Args:
            paper_content: 论文内容字典，包含以下键:
                - topic: 选题
                - literature: 文献列表
                - thesis: 论题陈述
                - outline: 大纲
                - draft: 草稿全文
                - title: 标题
                - abstract: 摘要

        Returns:
            PaperWritingResult: 评估结果
        """
        logger.info("开始论文写作质量评估")

        # 评估各维度
        topic_quality = await self._evaluate_topic(paper_content.get("topic", ""))
        literature_coverage = await self._evaluate_literature(paper_content.get("literature", []))
        thesis_clarity = await self._evaluate_thesis(paper_content.get("thesis", ""))
        outline_quality = await self._evaluate_outline(paper_content.get("outline", ""))
        draft_quality = await self._evaluate_draft(paper_content.get("draft", ""))
        language_quality = await self._evaluate_language(paper_content.get("draft", ""))

        # 计算综合分
        dimension_scores = {
            "topic_quality": topic_quality.score,
            "literature_coverage": literature_coverage.score,
            "thesis_clarity": thesis_clarity.score,
            "outline_quality": outline_quality.score,
            "draft_quality": draft_quality.score,
            "language_quality": language_quality.score
        }

        overall_score = sum(
            dimension_scores[d] * self.weights.get(d, 1/6)
            for d in dimension_scores
        )

        # 生成反馈
        feedback = []
        for dim_score in [topic_quality, literature_coverage, thesis_clarity,
                          outline_quality, draft_quality, language_quality]:
            if dim_score.score < 7:
                feedback.extend(dim_score.suggestions)

        # 确定等级
        grade = self._calculate_grade(overall_score)

        return PaperWritingResult(
            overall_score=round(overall_score, 2),
            topic_quality=topic_quality,
            literature_coverage=literature_coverage,
            thesis_clarity=thesis_clarity,
            outline_quality=outline_quality,
            draft_quality=draft_quality,
            language_quality=language_quality,
            dimension_scores=dimension_scores,
            feedback=feedback,
            grade=grade
        )

    async def _evaluate_topic(self, topic: str) -> DimensionScore:
        """评估选题质量"""
        score = 5.0
        suggestions = []
        details = {}

        # 检查选题是否为空
        if not topic or len(topic) < 10:
            score = 3.0
            suggestions.append("选题过于简单或未提供")
            return DimensionScore("topic_quality", score, self.weights["topic_quality"],
                                   details, suggestions)

        # 检查选题长度
        topic_length = len(topic)
        details["topic_length"] = topic_length

        if topic_length > 100:
            score += 1.0
        elif topic_length < 50:
            score -= 1.0

        # 检查是否包含研究关键词
        research_keywords = ["研究", "analysis", "study", "investigation",
                            "exploration", "method", "approach"]
        has_keywords = any(kw.lower() in topic.lower() for kw in research_keywords)
        if has_keywords:
            score += 1.0
            details["has_research_keywords"] = True
        else:
            score -= 0.5
            suggestions.append("建议在选题中包含研究相关关键词")

        # 检查是否有时效性标识
        time_keywords = ["最新", "2024", "2025", "new", "recent", "latest"]
        is_timely = any(kw in topic for kw in time_keywords)
        if is_timely:
            score += 0.5
            details["is_timely"] = True

        # 检查复杂度（是否包含多个概念）
        concepts = re.findall(r'[一-龥]+|[A-Z][a-z]+', topic)
        if len(concepts) >= 3:
            score += 1.0
            details["concept_count"] = len(concepts)
        elif len(concepts) < 2:
            score -= 1.0
            suggestions.append("选题建议包含多个相关概念")

        score = max(1.0, min(10.0, score))
        return DimensionScore("topic_quality", score, self.weights["topic_quality"],
                               details, suggestions)

    async def _evaluate_literature(self, literature: List) -> DimensionScore:
        """评估文献覆盖"""
        score = 5.0
        suggestions = []
        details = {}

        # 检查文献数量
        num_papers = len(literature) if literature else 0
        details["paper_count"] = num_papers

        if num_papers == 0:
            score = 2.0
            suggestions.append("缺少文献综述")
            return DimensionScore("literature_coverage", score, self.weights["literature_coverage"],
                                   details, suggestions)

        if num_papers >= 20:
            score += 2.0
        elif num_papers >= 10:
            score += 1.0
        elif num_papers < 5:
            score -= 2.0
            suggestions.append("文献数量偏少，建议至少10篇")

        # 检查文献多样性（是否涵盖多个来源）
        sources = set()
        for paper in literature:
            if isinstance(paper, dict):
                source = paper.get("source", "").lower()
                if source:
                    sources.add(source)
                # 检查年份分布
                year = paper.get("year", 0)
                if 2020 <= year <= 2025:
                    details["recent_papers"] = details.get("recent_papers", 0) + 1

        details["source_diversity"] = len(sources)
        if len(sources) >= 3:
            score += 1.0
        elif len(sources) < 2:
            suggestions.append("建议引用多个来源的文献（如arXiv、PubMed等）")

        # 检查核心文献（高引用）
        high_citation_count = 0
        for paper in literature:
            if isinstance(paper, dict):
                citations = paper.get("citations", 0)
                if citations and citations > 100:
                    high_citation_count += 1

        details["high_citation_papers"] = high_citation_count
        if high_citation_count >= 3:
            score += 1.0

        score = max(1.0, min(10.0, score))
        return DimensionScore("literature_coverage", score, self.weights["literature_coverage"],
                               details, suggestions)

    async def _evaluate_thesis(self, thesis: str) -> DimensionScore:
        """评估论题清晰度"""
        score = 5.0
        suggestions = []
        details = {}

        if not thesis or len(thesis) < 20:
            score = 2.0
            suggestions.append("论题陈述缺失或过于简单")
            return DimensionScore("thesis_clarity", score, self.weights["thesis_clarity"],
                                   details, suggestions)

        details["thesis_length"] = len(thesis)

        # 检查论题结构（是否包含研究对象、研究目标、研究方法等要素）
        required_elements = {
            "研究对象": ["算法", "模型", "方法", "系统", "研究", "task", "model", "method"],
            "研究目标": ["提高", "优化", "解决", "探索", "improve", "optimize", "solve", "explore"],
            "创新点": ["新", "首次", "novel", "first", "new", "提出", "propose"]
        }

        found_elements = {}
        for element, keywords in required_elements.items():
            if any(kw in thesis.lower() for kw in keywords):
                found_elements[element] = True
            else:
                found_elements[element] = False

        details["elements_found"] = found_elements
        elements_count = sum(found_elements.values())
        details["element_coverage"] = elements_count / len(required_elements)

        if elements_count >= 2:
            score += 2.0
        elif elements_count >= 1:
            score += 1.0
        else:
            suggestions.append("论题建议明确包含研究对象、研究目标和创新点")

        # 检查是否清晰可量化
        quantifiable_keywords = ["准确率", "性能", "效率", "效果", "accuracy", "performance", "efficiency"]
        has_quantifiable = any(kw in thesis.lower() for kw in quantifiable_keywords)
        if has_quantifiable:
            score += 1.0
            details["is_quantifiable"] = True

        score = max(1.0, min(10.0, score))
        return DimensionScore("thesis_clarity", score, self.weights["thesis_clarity"],
                               details, suggestions)

    async def _evaluate_outline(self, outline: str) -> DimensionScore:
        """评估大纲质量"""
        score = 5.0
        suggestions = []
        details = {}

        if not outline or len(outline) < 50:
            score = 2.0
            suggestions.append("大纲缺失或过于简单")
            return DimensionScore("outline_quality", score, self.weights["outline_quality"],
                                   details, suggestions)

        # 检查标准论文结构
        standard_sections = {
            "abstract": r"(?i)abstract|摘要",
            "introduction": r"(?i)introduction|引言",
            "method": r"(?i)method|methodology|方法",
            "results": r"(?i)results?|结果",
            "discussion": r"(?i)discussion|讨论",
            "conclusion": r"(?i)conclusion|结论",
            "references": r"(?i)references?|参考文献"
        }

        found_sections = {}
        for section, pattern in standard_sections.items():
            found_sections[section] = bool(re.search(pattern, outline))

        details["sections_found"] = found_sections

        sections_count = sum(found_sections.values())
        if sections_count >= 6:
            score += 3.0
        elif sections_count >= 4:
            score += 2.0
        elif sections_count >= 2:
            score += 1.0
        else:
            suggestions.append("大纲建议包含标准论文结构（引言、方法、结果、讨论、结论等）")

        # 检查章节之间的逻辑关系
        transition_keywords = ["首先", "其次", "然后", "最后", "furthermore", "moreover", "therefore"]
        has_transitions = sum(1 for kw in transition_keywords if kw in outline.lower())
        details["transition_count"] = has_transitions

        if has_transitions >= 2:
            score += 1.0

        score = max(1.0, min(10.0, score))
        return DimensionScore("outline_quality", score, self.weights["outline_quality"],
                               details, suggestions)

    async def _evaluate_draft(self, draft: str) -> DimensionScore:
        """评估草稿质量"""
        score = 5.0
        suggestions = []
        details = {}

        if not draft or len(draft) < 100:
            score = 2.0
            suggestions.append("草稿内容缺失")
            return DimensionScore("draft_quality", score, self.weights["draft_quality"],
                                   details, suggestions)

        details["draft_length"] = len(draft)

        # 检查字数（学术论文一般要求5000字以上）
        word_count = len(draft)
        if word_count >= 8000:
            score += 2.0
        elif word_count >= 5000:
            score += 1.5
        elif word_count >= 3000:
            score += 1.0
        elif word_count < 2000:
            score -= 2.0
            suggestions.append("草稿字数偏少，建议达到5000字以上")

        # 检查段落完整性
        paragraphs = draft.split("\n\n")
        paragraphs = [p for p in paragraphs if len(p.strip()) > 100]
        details["paragraph_count"] = len(paragraphs)

        if len(paragraphs) >= 10:
            score += 1.0
        elif len(paragraphs) < 5:
            suggestions.append("建议增加段落数量，每个段落应有充分论述")

        # 检查图表数量
        figure_count = len(re.findall(r"figure|图\d", draft.lower()))
        table_count = len(re.findall(r"table|表\d", draft.lower()))
        details["figures"] = figure_count
        details["tables"] = table_count

        if figure_count + table_count >= 3:
            score += 1.0
        elif figure_count + table_count == 0:
            suggestions.append("建议添加图表以增强表达效果")

        # 检查引用数量
        citation_count = len(re.findall(r"\[\d+\]|\([A-Z]\d{4}\)", draft))
        details["citation_count"] = citation_count

        if citation_count >= 20:
            score += 1.0
        elif citation_count < 5:
            suggestions.append("引用数量偏少，建议增加文献引用")

        score = max(1.0, min(10.0, score))
        return DimensionScore("draft_quality", score, self.weights["draft_quality"],
                               details, suggestions)

    async def _evaluate_language(self, draft: str) -> DimensionScore:
        """评估语言质量"""
        score = 5.0
        suggestions = []
        details = {}

        if not draft:
            score = 2.0
            suggestions.append("缺少文本内容")
            return DimensionScore("language_quality", score, self.weights["language_quality"],
                                   details, suggestions)

        # 检测语言类型
        chinese_chars = len(re.findall(r'[一-龥]', draft))
        english_chars = len(re.findall(r'[a-zA-Z]', draft))
        total_chars = chinese_chars + english_chars

        is_chinese = chinese_chars > english_chars
        details["language_type"] = "chinese" if is_chinese else "english"
        details["chinese_ratio"] = chinese_chars / max(total_chars, 1)
        details["character_count"] = total_chars

        # 检查语法问题（简化检测）
        # 连续相同字符（可能是输入错误）
        repeated_chars = re.findall(r'(.)\1{3,}', draft)
        details["repeated_char_issues"] = len(repeated_chars)

        if repeated_chars:
            score -= 0.5
            suggestions.append("发现可能的输入错误（连续重复字符）")

        # 检查句子平均长度
        sentences = re.split(r'[.。!！?？]', draft)
        sentences = [s.strip() for s in sentences if s.strip()]
        avg_sentence_length = sum(len(s) for s in sentences) / max(len(sentences), 1)
        details["avg_sentence_length"] = round(avg_sentence_length, 1)

        if avg_sentence_length > 100:
            suggestions.append("部分句子过长，建议适当拆分")
        elif avg_sentence_length < 10 and len(sentences) > 5:
            score -= 1.0
            suggestions.append("部分句子过短，建议适当扩展")

        # 检查学术词汇使用
        academic_keywords = ["然而", "因此", "此外", "研究表明", "然而", "综上所述",
                           "however", "therefore", "moreover", "furthermore", "thus", "hence"]
        academic_count = sum(1 for kw in academic_keywords if kw.lower() in draft.lower())
        details["academic_keyword_count"] = academic_count

        if academic_count >= 5:
            score += 1.5
        elif academic_count >= 2:
            score += 1.0
        else:
            suggestions.append("建议增加学术连接词的使用")

        # 检查是否有人称代词（学术写作应避免）
        first_person = re.findall(r"\b(I|we|my|our)\b", draft, re.I)
        details["first_person_count"] = len(first_person)

        if len(first_person) > 3:
            score -= 1.0
            suggestions.append("学术论文建议避免使用第一人称")

        score = max(1.0, min(10.0, score))
        return DimensionScore("language_quality", score, self.weights["language_quality"],
                               details, suggestions)

    def _calculate_grade(self, score: float) -> str:
        """根据分数计算等级"""
        if score >= 9.0:
            return "A"
        elif score >= 8.0:
            return "B"
        elif score >= 7.0:
            return "C"
        elif score >= 6.0:
            return "D"
        else:
            return "F"

    def generate_report(self, result: PaperWritingResult) -> str:
        """生成评估报告

        Args:
            result: 评估结果

        Returns:
            str: 格式化报告
        """
        lines = [
            "=" * 60,
            "论文写作质量评估报告",
            "=" * 60,
            f"\n综合评分: {result.overall_score:.1f}/10.0  (等级: {result.grade})",
            "\n分项评分:",
        ]

        dimensions = [
            ("选题质量", result.topic_quality),
            ("文献覆盖", result.literature_coverage),
            ("论题清晰度", result.thesis_clarity),
            ("大纲质量", result.outline_quality),
            ("草稿质量", result.draft_quality),
            ("语言质量", result.language_quality)
        ]

        for name, dim in dimensions:
            status = "✓" if dim.score >= 7 else "✗"
            lines.append(f"  {status} {name}: {dim.score:.1f}/10.0 (权重: {dim.weight:.0%})")

        if result.feedback:
            lines.append("\n改进建议:")
            for fb in result.feedback[:5]:  # 最多显示5条建议
                lines.append(f"  - {fb}")

        lines.append("=" * 60)

        return "\n".join(lines)


# 便捷函数
async def evaluate_paper(paper_content: Dict[str, Any]) -> PaperWritingResult:
    """评估论文质量的便捷函数

    Args:
        paper_content: 论文内容

    Returns:
        PaperWritingResult: 评估结果
    """
    benchmark = PaperWritingBenchmark()
    result = await benchmark.evaluate(paper_content)
    print(benchmark.generate_report(result))
    return result
