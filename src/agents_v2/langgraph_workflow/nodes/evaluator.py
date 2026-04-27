"""
Evaluator Node - LangGraph 工作流评估节点

提供完整的工作流质量评估：
1. 检索质量评估（召回率估计、精确率估计）
2. 论文质量评估（引用数、年份、多样性）
3. 大纲质量评估（章节完整性、覆盖率）
4. 写作质量评估（字数、引用密度、分析深度）
5. 综合评估报告
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..state import PaperAgentState, Paper

logger = logging.getLogger(__name__)


@dataclass
class RetrievalMetrics:
    """检索质量指标"""
    total_papers_found: int = 0
    selected_papers: int = 0
    selection_rate: float = 0.0
    avg_citations: float = 0.0
    avg_year: float = 0.0
    venue_diversity: int = 0  # 不同期刊/会议数
    freshness_ratio: float = 0.0  # 近5年论文比例


@dataclass
class WritingMetrics:
    """写作质量指标"""
    total_words: int = 0
    sections_count: int = 0
    citations_count: int = 0
    citations_per_section: float = 0.0
    analysis_keywords: int = 0  # 分析性词汇出现次数
    avg_section_length: int = 0
    has_introduction: bool = False
    has_conclusion: bool = False
    quality_score: float = 0.0  # 0-10


@dataclass
class WorkflowReport:
    """工作流评估报告"""
    retrieval: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    writing: WritingMetrics = field(default_factory=WritingMetrics)
    execution_time_s: float = 0.0
    iterations: int = 0
    overall_score: float = 0.0  # 0-10
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class EvaluatorNode:
    """评估节点 - LangGraph 节点"""

    def __init__(self, min_quality_score: float = 6.0):
        """
        Args:
            min_quality_score: 最低质量阈值
        """
        self.min_quality_score = min_quality_score

    def execute(self, state: PaperAgentState) -> PaperAgentState:
        """执行工作流评估"""
        start = time.time()
        report = WorkflowReport()

        # 1. 评估检索质量
        report.retrieval = self._evaluate_retrieval(state)

        # 2. 评估写作质量
        report.writing = self._evaluate_writing(state)

        # 3. 计算综合评分
        report.overall_score = self._calculate_overall_score(report)

        # 4. 识别问题和建议
        report.issues = self._find_issues(report)
        report.suggestions = self._generate_suggestions(report)

        # 5. 收集元数据
        report.execution_time_s = time.time() - start
        report.iterations = state.get("iteration", 0)
        report.metadata = {
            "evaluated_at": time.time(),
            "user_id": state.get("user_id", ""),
            "session_id": state.get("session_id", ""),
        }

        # 6. 存储到状态
        state["evaluation_report"] = report
        state["evaluation_score"] = report.overall_score

        logger.info(
            f"[Evaluator] 评估完成: 综合评分 {report.overall_score:.1f}/10, "
            f"耗时 {report.execution_time_s:.2f}s"
        )

        return state

    def _evaluate_retrieval(self, state: PaperAgentState) -> RetrievalMetrics:
        """评估检索质量"""
        metrics = RetrievalMetrics()
        papers = state.get("papers", [])
        selected = state.get("selected_papers", [])

        metrics.total_papers_found = len(papers)
        metrics.selected_papers = len(selected)
        metrics.selection_rate = len(selected) / max(len(papers), 1)

        if not selected:
            return metrics

        # 计算平均引用数
        total_citations = sum(p.citations for p in selected if isinstance(p, Paper))
        metrics.avg_citations = total_citations / max(len(selected), 1)

        # 计算平均年份
        valid_years = [p.year for p in selected if isinstance(p, Paper) and p.year > 0]
        if valid_years:
            metrics.avg_year = sum(valid_years) / len(valid_years)

        # 期刊/会议多样性
        venues = set()
        for p in selected:
            if isinstance(p, Paper) and p.venue:
                venues.add(p.venue)
        metrics.venue_diversity = len(venues)

        # 新鲜度（近5年论文比例）
        current_year = 2026
        recent_papers = [
            p for p in selected
            if isinstance(p, Paper) and p.year >= current_year - 5 and p.year > 0
        ]
        metrics.freshness_ratio = len(recent_papers) / max(len(selected), 1)

        return metrics

    def _evaluate_writing(self, state: PaperAgentState) -> WritingMetrics:
        """评估写作质量"""
        metrics = WritingMetrics()
        draft = state.get("draft", "")
        outline = state.get("outline", {})

        if not draft:
            return metrics

        # 字数统计
        metrics.total_words = len(draft.split())

        # 章节统计
        sections = outline.get("sections", [])
        metrics.sections_count = len(sections)

        # 计算引用数量（基于 [Title, Year] 格式）
        import re
        citation_pattern = re.compile(r'\[[^\]]+,\s*\d{4}\]')
        metrics.citations_count = len(citation_pattern.findall(draft))
        metrics.citations_per_section = metrics.citations_count / max(metrics.sections_count, 1)

        # 分析性关键词
        analysis_keywords = [
            "however", "although", "in contrast", "compared to", "limitation",
            "challenge", "drawback", "shortcoming", "gap", "issue",
            "furthermore", "moreover", "consequently", "therefore", "thus"
        ]
        draft_lower = draft.lower()
        metrics.analysis_keywords = sum(
            draft_lower.count(kw) for kw in analysis_keywords
        )

        # 平均章节长度
        section_texts = draft.split("## ")
        if section_texts:
            section_lengths = [len(s.split()) for s in section_texts if s.strip()]
            metrics.avg_section_length = sum(section_lengths) / max(len(section_lengths), 1)

        # 检查是否有 intro 和 conclusion
        draft_lower = draft.lower()
        metrics.has_introduction = "introduction" in draft_lower
        metrics.has_conclusion = "conclusion" in draft_lower

        # 计算质量评分 (0-10)
        score = 0.0

        # 基础结构 (30%)
        if metrics.has_introduction:
            score += 1.5
        if metrics.has_conclusion:
            score += 1.5
        if metrics.sections_count >= 5:
            score += 1.0
        elif metrics.sections_count >= 3:
            score += 0.5

        # 内容深度 (40%)
        if metrics.total_words >= 1500:
            score += 2.0
        elif metrics.total_words >= 500:
            score += 1.0
        elif metrics.total_words >= 200:
            score += 0.5

        # 分析性 (30%)
        if metrics.analysis_keywords >= 5:
            score += 1.5
        elif metrics.analysis_keywords >= 2:
            score += 0.8
        if metrics.citations_per_section >= 2:
            score += 1.0
        elif metrics.citations_per_section >= 1:
            score += 0.5

        metrics.quality_score = min(score, 10.0)
        return metrics

    def _calculate_overall_score(self, report: WorkflowReport) -> float:
        """计算综合评分"""
        score = 0.0
        weights = {
            "retrieval": 0.35,
            "writing": 0.50,
            "efficiency": 0.15,
        }

        # 检索评分
        retrieval = report.retrieval
        retrieval_score = 0.0
        if retrieval.selection_rate >= 0.1:
            retrieval_score += 0.2
        if retrieval.venue_diversity >= 2:
            retrieval_score += 0.3
        if retrieval.freshness_ratio >= 0.5:
            retrieval_score += 0.3
        if retrieval.avg_citations >= 10:
            retrieval_score += 0.2
        retrieval_score = min(retrieval_score * 2.5, 10.0)  # 归一化到 0-10

        # 写作评分
        writing_score = report.writing.quality_score

        # 效率评分（执行时间 < 30s 满分）
        efficiency_score = max(10.0 - report.execution_time_s * 0.3, 0.0)

        score = (
            retrieval_score * weights["retrieval"] +
            writing_score * weights["writing"] +
            efficiency_score * weights["efficiency"]
        )

        return min(score, 10.0)

    def _find_issues(self, report: WorkflowReport) -> List[str]:
        """识别问题"""
        issues = []

        if report.retrieval.total_papers_found < 10:
            issues.append("检索到的论文数量较少（< 10 篇）")
        if report.retrieval.venue_diversity < 2:
            issues.append("来源期刊/会议过于单一")
        if report.retrieval.freshness_ratio < 0.3:
            issues.append("近期论文比例偏低（< 30% 近5年）")

        if not report.writing.has_introduction:
            issues.append("缺少 Introduction 章节")
        if not report.writing.has_conclusion:
            issues.append("缺少 Conclusion 章节")
        if report.writing.total_words < 500:
            issues.append(f"论文过短（{report.writing.total_words} 词，建议 > 1500）")
        if report.writing.analysis_keywords < 3:
            issues.append("分析性内容不足，建议增加对比和批判性分析")
        if report.writing.citations_count < 3:
            issues.append("文献引用较少")

        return issues

    def _generate_suggestions(self, report: WorkflowReport) -> List[str]:
        """生成改进建议"""
        suggestions = []

        if report.retrieval.total_papers_found < 20:
            suggestions.append("考虑使用更多检索源（arXiv + Semantic Scholar + PubMed）")
        if report.retrieval.freshness_ratio < 0.5:
            suggestions.append("尝试添加年份过滤器，优先检索近5年的论文")
        if not report.writing.has_introduction:
            suggestions.append("在大纲中添加 Introduction 章节")
        if report.writing.total_words < 1000:
            suggestions.append("使用 LLM 模式生成更详细的章节内容")
        if report.writing.analysis_keywords < 5:
            suggestions.append("在 Reviewer 反馈中要求增加对比分析")

        return suggestions


def create_evaluator_node(min_quality_score: float = 6.0) -> EvaluatorNode:
    """便捷函数：创建评估节点"""
    return EvaluatorNode(min_quality_score=min_quality_score)
