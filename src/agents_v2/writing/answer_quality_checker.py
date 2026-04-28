"""
答案质量检查器 - Answer Quality Checker

功能:
1. 答案完整性检查
2. 事实准确性验证
3. 一致性检查
4. 质量评分

设计原则:
- 多维度质量评估
- 可配置的检查项
- 详细的检查报告
"""
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class QualityDimension(str, Enum):
    """质量维度"""
    COMPLETENESS = "completeness"  # 完整性
    ACCURACY = "accuracy"  # 准确性
    COHERENCE = "coherence"  # 连贯性
    RELEVANCE = "relevance"  # 相关性
    CONCISENESS = "conciseness"  # 简洁性


@dataclass
class QualityIssue:
    """质量问题"""
    dimension: QualityDimension
    severity: str  # "error", "warning", "info"
    description: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class QualityCheckResult:
    """质量检查结果"""
    overall_score: float
    passed: bool
    issues: List[QualityIssue] = field(default_factory=list)
    scores_by_dimension: Dict[QualityDimension, float] = field(default_factory=dict)
    summary: str = ""


@dataclass
class FactCheckResult:
    """事实检查结果"""
    statement: str
    is_claim: bool
    verified: Optional[bool] = None
    confidence: float = 0.0
    source: Optional[str] = None


class AnswerQualityChecker:
    """答案质量检查器"""

    def __init__(
        self,
        llm_provider: Optional[Callable] = None,
        check_facts: bool = False
    ):
        self.llm_provider = llm_provider
        self.check_facts = check_facts

        # 各维度权重
        self.dimension_weights = {
            QualityDimension.COMPLETENESS: 0.25,
            QualityDimension.ACCURACY: 0.30,
            QualityDimension.COHERENCE: 0.15,
            QualityDimension.RELEVANCE: 0.20,
            QualityDimension.CONCISENESS: 0.10
        }

        # 通过阈值
        self.passing_threshold = 0.7

    def check(
        self,
        answer: str,
        question: str,
        context: Optional[str] = None
    ) -> QualityCheckResult:
        """检查答案质量

        Args:
            answer: 待检查的答案
            question: 原始问题
            context: 上下文信息

        Returns:
            QualityCheckResult: 质量检查结果
        """
        issues = []

        # 检查各维度
        completeness_score, completeness_issues = self._check_completeness(answer, question)
        issues.extend(completeness_issues)

        accuracy_score, accuracy_issues = self._check_accuracy(answer)
        issues.extend(accuracy_issues)

        coherence_score, coherence_issues = self._check_coherence(answer)
        issues.extend(coherence_issues)

        relevance_score, relevance_issues = self._check_relevance(answer, question)
        issues.extend(relevance_issues)

        conciseness_score, conciseness_issues = self._check_conciseness(answer)
        issues.extend(conciseness_issues)

        # 计算各维度分数
        scores_by_dimension = {
            QualityDimension.COMPLETENESS: completeness_score,
            QualityDimension.ACCURACY: accuracy_score,
            QualityDimension.COHERENCE: coherence_score,
            QualityDimension.RELEVANCE: relevance_score,
            QualityDimension.CONCISENESS: conciseness_score
        }

        # 计算总分
        overall_score = sum(
            score * self.dimension_weights[dim]
            for dim, score in scores_by_dimension.items()
        )

        # 判断是否通过
        passed = overall_score >= self.passing_threshold and not any(
            issue.severity == "error" for issue in issues
        )

        # 生成摘要
        summary = self._generate_summary(overall_score, issues)

        return QualityCheckResult(
            overall_score=overall_score,
            passed=passed,
            issues=issues,
            scores_by_dimension=scores_by_dimension,
            summary=summary
        )

    def _check_completeness(
        self,
        answer: str,
        question: str
    ) -> Tuple[float, List[QualityIssue]]:
        """检查完整性"""
        score = 0.7
        issues = []

        # 检查答案长度
        if len(answer) < 50:
            issues.append(QualityIssue(
                dimension=QualityDimension.COMPLETENESS,
                severity="warning",
                description="答案过短，可能不完整",
                suggestion="添加更多详细信息"
            ))
            score -= 0.2
        elif len(answer) > 5000:
            issues.append(QualityIssue(
                dimension=QualityDimension.COMPLETENESS,
                severity="warning",
                description="答案过长，可能冗余",
                suggestion="精简内容"
            ))
            score -= 0.1

        # 检查是否回答了问题的主要方面
        question_keywords = set(question.lower().split())
        answer_lower = answer.lower()

        # 简单检查：问题中的关键词是否在答案中
        matched_keywords = question_keywords & set(answer_lower.split())
        match_rate = len(matched_keywords) / len(question_keywords) if question_keywords else 0

        if match_rate < 0.3:
            issues.append(QualityIssue(
                dimension=QualityDimension.COMPLETENESS,
                severity="error",
                description="答案可能没有正确回答问题",
                suggestion="确保答案与问题相关"
            ))
            score -= 0.3

        score = max(0.0, min(1.0, score))
        return score, issues

    def _check_accuracy(
        self,
        answer: str
    ) -> Tuple[float, List[QualityIssue]]:
        """检查准确性"""
        score = 0.8
        issues = []

        # 检查是否包含不确定的表达
        uncertain_phrases = ["可能", "也许", "大概", "perhaps", "maybe", "probably"]
        uncertain_count = sum(1 for phrase in uncertain_phrases if phrase in answer.lower())

        if uncertain_count > 5:
            issues.append(QualityIssue(
                dimension=QualityDimension.ACCURACY,
                severity="warning",
                description="答案包含过多不确定表达",
                suggestion="减少不确定性表述"
            ))
            score -= 0.1

        # 检查是否有明显的逻辑错误标记
        error_markers = ["错误", "不对", "假的", "wrong", "incorrect"]
        has_error_marker = any(marker in answer.lower() for marker in error_markers)

        if has_error_marker:
            issues.append(QualityIssue(
                dimension=QualityDimension.ACCURACY,
                severity="info",
                description="答案包含错误纠正标记",
                suggestion="确保纠正是准确的"
            ))

        score = max(0.0, min(1.0, score))
        return score, issues

    def _check_coherence(
        self,
        answer: str
    ) -> Tuple[float, List[QualityIssue]]:
        """检查连贯性"""
        score = 0.8
        issues = []

        # 检查段落结构
        paragraphs = answer.split("\n\n")

        if len(paragraphs) == 1 and len(answer) > 500:
            issues.append(QualityIssue(
                dimension=QualityDimension.COHERENCE,
                severity="warning",
                description="答案缺少段落分隔",
                suggestion="将长答案分成多个段落"
            ))
            score -= 0.1

        # 检查是否有连接词
        connectors = ["但是", "因此", "因为", "所以", "然而", "however", "therefore", "because"]
        has_connector = any(conn in answer.lower() for conn in connectors)

        if not has_connector and len(answer) > 200:
            issues.append(QualityIssue(
                dimension=QualityDimension.COHERENCE,
                severity="info",
                description="答案可能缺少连接词",
                suggestion="添加适当的连接词改善连贯性"
            ))
            score -= 0.05

        score = max(0.0, min(1.0, score))
        return score, issues

    def _check_relevance(
        self,
        answer: str,
        question: str
    ) -> Tuple[float, List[QualityIssue]]:
        """检查相关性"""
        score = 0.8
        issues = []

        # 简单检查：答案长度与问题复杂度是否匹配
        if "什么" in question or "what" in question.lower():
            if len(answer) < 30:
                issues.append(QualityIssue(
                    dimension=QualityDimension.RELEVANCE,
                    severity="warning",
                    description='对于"什么"类问题，答案可能过于简短',
                    suggestion="提供更详细的定义或描述"
                ))
                score -= 0.1

        elif "为什么" in question or "why" in question.lower():
            if "因为" not in answer and "由于" not in answer:
                issues.append(QualityIssue(
                    dimension=QualityDimension.RELEVANCE,
                    severity="warning",
                    description='对于"为什么"类问题，答案应包含原因解释',
                    suggestion="添加原因分析"
                ))
                score -= 0.15

        elif "如何" in question or "how" in question.lower():
            if "步骤" not in answer and "方法" not in answer:
                issues.append(QualityIssue(
                    dimension=QualityDimension.RELEVANCE,
                    severity="warning",
                    description='对于"如何"类问题，答案应包含方法或步骤',
                    suggestion="提供具体的操作步骤"
                ))
                score -= 0.15

        score = max(0.0, min(1.0, score))
        return score, issues

    def _check_conciseness(
        self,
        answer: str
    ) -> Tuple[float, List[QualityIssue]]:
        """检查简洁性"""
        score = 0.8
        issues = []

        # 检查冗余
        redundant_patterns = [
            (r"实际上", 1),
            (r"事实上", 1),
            (r"总的来说", 1),
            (r"总而言之", 1),
        ]

        redundancy_count = 0
        for pattern, _ in redundant_patterns:
            import re
            redundancy_count += len(re.findall(pattern, answer))

        if redundancy_count > 3:
            issues.append(QualityIssue(
                dimension=QualityDimension.CONCISENESS,
                severity="warning",
                description="答案存在冗余表达",
                suggestion="删除重复的词语和句子"
            ))
            score -= 0.1

        # 检查是否有重复句子
        sentences = answer.replace("。", ".").split(".")
        unique_sentences = set(sentences)
        if len(sentences) > 5 and len(unique_sentences) / len(sentences) < 0.5:
            issues.append(QualityIssue(
                dimension=QualityDimension.CONCISENESS,
                severity="warning",
                description="答案存在重复句子",
                suggestion="删除重复内容"
            ))
            score -= 0.15

        score = max(0.0, min(1.0, score))
        return score, issues

    def _generate_summary(
        self,
        score: float,
        issues: List[QualityIssue]
    ) -> str:
        """生成摘要"""
        if score >= 0.9:
            return "答案质量优秀"
        elif score >= 0.7:
            return "答案质量良好，有少量改进空间"
        elif score >= 0.5:
            return "答案质量一般，需要改进"
        else:
            return "答案质量较差，需要大幅改进"


# 便捷函数
def check_quality(
    answer: str,
    question: str,
    context: Optional[str] = None
) -> QualityCheckResult:
    """便捷质量检查函数"""
    checker = AnswerQualityChecker()
    return checker.check(answer, question, context)
