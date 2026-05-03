"""
置信度校准器 - Confidence Calibrator

多维度置信度评估：
1. 检索相关性
2. 答案完整性
3. 内部一致性
4. 事实支撑度
5. 不确定性表达
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.agents_v2.logging_config import get_logging_logger

import asyncio

logger = get_logging_logger(__name__)


@dataclass
class ConfidenceScore:
    """置信度分数"""
    overall: float  # 综合置信度 (0-1)
    retrieval_relevance: float = 0.0
    answer_completeness: float = 0.0
    internal_consistency: float = 0.0
    groundedness: float = 0.0
    uncertainty_expression: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class ConfidenceCalibrator:
    """置信度校准器

    多维度评估答案的置信度，并进行校准使其更加准确。
    """

    # 各维度权重
    DEFAULT_WEIGHTS = {
        "retrieval_relevance": 0.25,
        "answer_completeness": 0.15,
        "internal_consistency": 0.15,
        "groundedness": 0.30,
        "uncertainty_expression": 0.15,
    }

    def __init__(
        self,
        llm: Optional[Any] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        """初始化置信度校准器

        Args:
            llm: LLM 实例
            weights: 各维度权重
        """
        self.llm = llm
        self.weights = weights or self.DEFAULT_WEIGHTS

    async def calibrate(
        self,
        question: str,
        answer: str,
        context_docs: List[Dict[str, Any]],
        hallucination_score: Optional[float] = None,
    ) -> ConfidenceScore:
        """校准置信度

        Args:
            question: 用户问题
            answer: 生成的答案
            context_docs: 上下文文档
            hallucination_score: 幻觉分数（如果有）

        Returns:
            ConfidenceScore: 多维度置信度分数
        """
        # 1. 检索相关性
        retrieval_relevance = await self._evaluate_retrieval_relevance(
            question, context_docs
        )

        # 2. 答案完整性
        answer_completeness = await self._evaluate_answer_completeness(
            question, answer
        )

        # 3. 内部一致性
        internal_consistency = await self._evaluate_internal_consistency(
            answer
        )

        # 4. 事实支撑度
        groundedness = await self._evaluate_groundedness(
            answer, context_docs
        )

        # 5. 不确定性表达
        uncertainty_expression = await self._evaluate_uncertainty(
            answer
        )

        # 如果有幻觉分数，加入考虑
        if hallucination_score is not None:
            # 幻觉分数高会降低事实支撑度
            groundedness = min(groundedness, 1.0 - hallucination_score)

        # 计算综合分数
        overall = (
            retrieval_relevance * self.weights["retrieval_relevance"] +
            answer_completeness * self.weights["answer_completeness"] +
            internal_consistency * self.weights["internal_consistency"] +
            groundedness * self.weights["groundedness"] +
            uncertainty_expression * self.weights["uncertainty_expression"]
        )

        return ConfidenceScore(
            overall=overall,
            retrieval_relevance=retrieval_relevance,
            answer_completeness=answer_completeness,
            internal_consistency=internal_consistency,
            groundedness=groundedness,
            uncertainty_expression=uncertainty_expression,
            details={
                "weights": self.weights,
                "num_docs": len(context_docs),
            }
        )

    async def _evaluate_retrieval_relevance(
        self,
        question: str,
        context_docs: List[Dict[str, Any]],
    ) -> float:
        """评估检索相关性

        评估检索到的文档与问题的相关程度。
        """
        if not context_docs:
            return 0.0

        if not self.llm:
            return self._simple_relevance(question, context_docs)

        # 使用 LLM 评估
        docs_summary = "\n".join([
            f"- {(doc.get('content', doc.get('page_content', '')) if isinstance(doc, dict) else str(doc))[:100]}..."
            for doc in context_docs[:3]
        ])

        prompt = f"""评估以下检索结果与问题的相关程度。

问题: {question}

检索结果:
{docs_summary}

评分标准 (0-1):
- 1.0: 完全相关，检索到了能够直接回答问题的内容
- 0.7: 高度相关，检索到了大部分相关内容
- 0.5: 中度相关，检索到了部分相关内容
- 0.3: 低度相关，检索结果相关性较低
- 0.0: 完全不相关，检索结果与问题无关

请只输出一个数字（0.0-1.0）："""

        try:
            response = await self._call_llm(prompt)
            score = float(response.strip())
            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.error(f"Retrieval relevance evaluation failed: {e}")
            return 0.5

    def _simple_relevance(
        self,
        question: str,
        context_docs: List[Dict[str, Any]],
    ) -> float:
        """简单的相关性评估"""
        if not context_docs:
            return 0.0

        query_terms = set(question.lower().split())
        total_overlap = 0

        for doc in context_docs:
            content = (doc.get("content", doc.get("page_content", str(doc))) if isinstance(doc, dict) else str(doc)).lower()
            doc_terms = set(content.split())
            overlap = len(query_terms & doc_terms)
            if query_terms:
                total_overlap += overlap / len(query_terms)

        avg_overlap = total_overlap / len(context_docs) if context_docs else 0
        return min(1.0, avg_overlap * 2)

    async def _evaluate_answer_completeness(
        self,
        question: str,
        answer: str,
    ) -> float:
        """评估答案完整性

        评估答案是否完整回答了问题。
        """
        if not answer:
            return 0.0

        if not self.llm:
            return self._simple_completeness(question, answer)

        # 检查问题类型
        question_type = self._classify_question_type(question)

        # 评估完整性
        prompt = f"""评估以下答案对问题的完整程度。

问题类型: {question_type}

问题: {question}

答案: {answer}

评分标准 (0-1):
- 1.0: 完全完整，答案完整回答了问题的所有方面
- 0.7: 大部分完整，答案回答了主要问题，但有遗漏
- 0.5: 部分完整，答案只回答了问题的部分内容
- 0.3: 不完整，答案遗漏了大量重要内容
- 0.0: 完全不完整，答案与问题不相关

请只输出一个数字（0.0-1.0）："""

        try:
            response = await self._call_llm(prompt)
            score = float(response.strip())
            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.error(f"Completeness evaluation failed: {e}")
            return 0.5

    def _simple_completeness(self, question: str, answer: str) -> float:
        """简单的完整性评估"""
        # 检查问题中的疑问词
        question_type = self._classify_question_type(question)

        # 基本检查
        if not answer or len(answer) < 20:
            return 0.2

        answer_len = len(answer)

        # 根据问题类型评估
        if "多少" in question or "how many" in question.lower():
            # 数值问题：检查是否包含数字
            has_number = any(c.isdigit() for c in answer)
            return 0.9 if has_number else 0.4

        elif "为什么" in question or "why" in question.lower():
            # 因果问题：检查是否包含原因说明
            has_reason = any(word in answer for word in ["因为", "由于", "所以", "原因", "because", "therefore"])
            return 0.8 if has_reason else 0.4

        elif "如何" in question or "how" in question.lower():
            # 方法问题：检查是否包含步骤
            has_steps = any(word in answer for word in ["首先", "然后", "最后", "步骤", "first", "then", "finally"])
            return 0.8 if has_steps else 0.5

        else:
            # 一般问题：根据长度估计
            if answer_len > 200:
                return 0.7
            elif answer_len > 100:
                return 0.6
            elif answer_len > 50:
                return 0.5
            else:
                return 0.4

    def _classify_question_type(self, question: str) -> str:
        """分类问题类型"""
        question_lower = question.lower()

        if any(kw in question for kw in ["多少", "how many", "how much", "number", "数量"]):
            return "factoid_count"
        elif any(kw in question for kw in ["谁", "who", "when", "时间", "哪里", "where"]):
            return "factoid_wh"
        elif any(kw in question for kw in ["为什么", "why", "原因", "因为"]):
            return "causal"
        elif any(kw in question for kw in ["如何", "how", "方法", "怎么做"]):
            return "procedural"
        elif any(kw in question for kw in ["比较", "compare", "区别", "difference"]):
            return "comparative"
        else:
            return "general"

    async def _evaluate_internal_consistency(self, answer: str) -> float:
        """评估内部一致性

        评估答案内容的前后一致性。
        """
        if not answer or len(answer) < 20:
            return 0.5

        if not self.llm:
            return self._simple_consistency(answer)

        prompt = f"""评估以下答案的内部一致性。

答案: {answer}

检查内容:
1. 答案前后是否矛盾
2. 事实陈述是否一致
3. 时间顺序是否合理

评分标准 (0-1):
- 1.0: 完全一致，答案内容逻辑自洽
- 0.7: 高度一致，有轻微不一致但不影响理解
- 0.5: 中度一致，存在一些不一致但主要结论可信
- 0.3: 低度一致，存在明显矛盾
- 0.0: 完全不一致，答案前后矛盾无法理解

请只输出一个数字（0.0-1.0）："""

        try:
            response = await self._call_llm(prompt)
            score = float(response.strip())
            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.error(f"Consistency evaluation failed: {e}")
            return 0.5

    def _simple_consistency(self, answer: str) -> float:
        """简单的内部一致性检查"""
        # 检查是否有明显的矛盾词
        contradictions = [
            ("但是", "然而"),  # 前后转折
            ("一方面", "另一方面"),  # 可能有不同观点
        ]

        # 如果答案太短，无法判断
        if len(answer) < 50:
            return 0.5

        # 检查转折词使用是否合理
        has_contrast = any(c in answer for c in ["但是", "然而", "不过", "然而", "although", "however"])

        if has_contrast:
            return 0.7  # 有对比但可能合理使用

        return 0.8  # 默认良好一致性

    async def _evaluate_groundedness(
        self,
        answer: str,
        context_docs: List[Dict[str, Any]],
    ) -> float:
        """评估事实支撑度

        评估答案是否有充分的文献支撑。
        """
        if not context_docs:
            return 0.3  # 无上下文时默认较低

        if not self.llm:
            return self._simple_groundedness(answer, context_docs)

        context_summary = "\n".join([
            f"[文档{i+1}] {(doc.get('content', doc.get('page_content', '')) if isinstance(doc, dict) else str(doc))[:200]}..."
            for i, doc in enumerate(context_docs[:3])
        ])

        prompt = f"""评估答案中的事实声明是否被提供的文献支撑。

文献:
{context_summary}

答案:
{answer}

评分标准 (0-1):
- 1.0: 完全支撑，所有事实声明都能从文献中推断
- 0.7: 大部分支撑，大部分事实有文献依据
- 0.5: 部分支撑，部分事实有文献依据
- 0.3: 支撑不足，只有很少的事实有文献依据
- 0.0: 几乎无支撑，答案包含大量文献中没有的信息

请只输出一个数字（0.0-1.0）："""

        try:
            response = await self._call_llm(prompt)
            score = float(response.strip())
            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.error(f"Groundedness evaluation failed: {e}")
            return 0.5

    def _simple_groundedness(
        self,
        answer: str,
        context_docs: List[Dict[str, Any]],
    ) -> float:
        """简单的事实支撑度评估"""
        if not context_docs:
            return 0.3

        # 检查答案中的术语是否出现在上下文中
        answer_terms = set(answer.lower().split())
        context_text = " ".join(
            (doc.get("content", doc.get("page_content", str(doc))) if isinstance(doc, dict) else str(doc)).lower()
            for doc in context_docs
        )
        context_terms = set(context_text.split())

        if not answer_terms:
            return 0.5

        overlap = len(answer_terms & context_terms)
        ratio = overlap / len(answer_terms)

        # 根据重叠率调整
        if ratio >= 0.5:
            return min(0.9, ratio * 1.2)
        else:
            return ratio

    async def _evaluate_uncertainty(self, answer: str) -> float:
        """评估不确定性表达

        评估答案是否恰当地表达了不确定性。
        - 适当的 Uncertainty 是好的（说明知道边界）
        - 过高的 Uncertainty 是不好的（缺乏自信）
        - 过低的 Uncertainty 可能意味着过度自信
        """
        if not answer:
            return 0.0

        if not self.llm:
            return self._simple_uncertainty(answer)

        prompt = f"""评估以下答案对不确定性信息的表达。

答案: {answer}

评分标准 (0-1):
- 1.0: 表达适当，既能识别不确定性，又不过度犹豫
- 0.7: 基本适当，有一定的不确定性表达
- 0.5: 表达不足，缺乏对不确定性的识别
- 0.3: 过度自信，答案过于确定而忽视了不确定性
- 0.0: 过度犹豫，答案充满不确定表达而缺乏实质内容

请只输出一个数字（0.0-1.0）："""

        try:
            response = await self._call_llm(prompt)
            score = float(response.strip())
            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.error(f"Uncertainty evaluation failed: {e}")
            return 0.5

    def _simple_uncertainty(self, answer: str) -> float:
        """简单的不确定性评估"""
        uncertainty_indicators = [
            "不确定", "可能", "也许", "无法确定", "不清楚",
            "probably", "perhaps", "maybe", "might", "not sure", "uncertain"
        ]

        certainty_indicators = [
            "一定", "肯定", "绝对", "必然", "毫无疑问",
            "certain", "definitely", "certainly", "must", "absolutely"
        ]

        uncertainty_count = sum(
            1 for ind in uncertainty_indicators
            if ind in answer.lower()
        )

        certainty_count = sum(
            1 for ind in certainty_indicators
            if ind in answer.lower()
        )

        # 适度的不确定性表达是好的
        if uncertainty_count == 0 and certainty_count > 2:
            return 0.4  # 过度自信
        elif uncertainty_count > 0 and uncertainty_count <= 2:
            return 0.8  # 适度
        elif uncertainty_count > 3:
            return 0.5  # 过度犹豫
        else:
            return 0.6

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        try:
            if hasattr(self.llm, 'agenerate'):
                result = await self.llm.agenerate([prompt])
                return result.generations[0][0].text.strip()
            elif hasattr(self.llm, 'generate'):
                result = self.llm.generate([prompt])
                return result.generations[0][0].text.strip()
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def format_score(self, score: ConfidenceScore) -> str:
        """格式化置信度分数

        Args:
            score: 置信度分数

        Returns:
            str: 格式化的文本
        """
        lines = [
            "=== 置信度评估 ===",
            f"综合置信度: {score.overall:.2f}",
            "",
            "各维度分数:",
            f"  - 检索相关性: {score.retrieval_relevance:.2f}",
            f"  - 答案完整性: {score.answer_completeness:.2f}",
            f"  - 内部一致性: {score.internal_consistency:.2f}",
            f"  - 事实支撑度: {score.groundedness:.2f}",
            f"  - 不确定性表达: {score.uncertainty_expression:.2f}",
        ]

        if score.details:
            lines.append(f"  - 上下文文档数: {score.details.get('num_docs', 0)}")

        return "\n".join(lines)


# 便捷函数
async def calibrate_confidence(
    question: str,
    answer: str,
    context_docs: List[Dict[str, Any]],
    llm: Optional[Any] = None,
    **kwargs
) -> ConfidenceScore:
    """置信度校准的便捷函数"""
    calibrator = ConfidenceCalibrator(llm=llm, **kwargs)
    return await calibrator.calibrate(question, answer, context_docs)


def format_confidence_score(score: ConfidenceScore) -> str:
    """格式化置信度分数的便捷函数"""
    calibrator = ConfidenceCalibrator()
    return calibrator.format_score(score)