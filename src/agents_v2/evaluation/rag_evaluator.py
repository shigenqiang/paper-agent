"""
RAG评估器 - RAG Evaluator

功能:
1. RAG系统端到端评估
2. 检索质量评估
3. 生成质量评估
4. 综合评分

设计原则:
- 多维度评估
- 可配置的评估指标
- 详细的评估报告
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class EvaluationMetric(str, Enum):
    """评估指标"""
    RETRIEVAL_PRECISION = "retrieval_precision"
    RETRIEVAL_RECALL = "retrieval_recall"
    RETRIEVAL_F1 = "retrieval_f1"
    ANSWER_RELEVANCE = "answer_relevance"
    ANSWER_FAITHFULNESS = "answer_faithfulness"
    ANSWER_ACCURACY = "answer_accuracy"
    GROUNDEDNESS = "groundedness"
    CONTEXT_RELEVANCE = "context_relevance"


@dataclass
class RetrievalEvalResult:
    """检索评估结果"""
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    mrr: float = 0.0  # Mean Reciprocal Rank
    ndcg: float = 0.0  # Normalized Discounted Cumulative Gain
    context_utilization: float = 0.0


@dataclass
class GenerationEvalResult:
    """生成评估结果"""
    relevance: float = 0.0
    faithfulness: float = 0.0
    accuracy: float = 0.0
    groundedness: float = 0.0
    context_relevance: float = 0.0


@dataclass
class RAGEvalResult:
    """RAG评估结果"""
    retrieval: RetrievalEvalResult
    generation: GenerationEvalResult
    overall_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "retrieval": {
                "precision": self.retrieval.precision,
                "recall": self.retrieval.recall,
                "f1": self.retrieval.f1,
                "mrr": self.retrieval.mrr,
                "ndcg": self.retrieval.ndcg,
                "context_utilization": self.retrieval.context_utilization
            },
            "generation": {
                "relevance": self.generation.relevance,
                "faithfulness": self.generation.faithfulness,
                "accuracy": self.generation.accuracy,
                "groundedness": self.generation.groundedness,
                "context_relevance": self.generation.context_relevance
            },
            "overall_score": self.overall_score,
            "metadata": self.metadata
        }


class RAGEvaluator:
    """RAG评估器"""

    def __init__(self):
        self._init_metrics()

    def _init_metrics(self):
        """初始化评估指标"""
        # 检索指标权重
        self.retrieval_weights = {
            "precision": 0.3,
            "recall": 0.3,
            "f1": 0.2,
            "mrr": 0.1,
            "ndcg": 0.1
        }

        # 生成指标权重
        self.generation_weights = {
            "relevance": 0.3,
            "faithfulness": 0.25,
            "accuracy": 0.25,
            "groundedness": 0.1,
            "context_relevance": 0.1
        }

    def evaluate_retrieval(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        relevant_docs: Optional[List[str]] = None
    ) -> RetrievalEvalResult:
        """评估检索质量

        Args:
            query: 查询字符串
            retrieved_docs: 检索到的文档列表
            relevant_docs: 实际相关的文档ID列表（用于计算精确率/召回率）

        Returns:
            RetrievalEvalResult: 检索评估结果
        """
        result = RetrievalEvalResult()

        if not retrieved_docs:
            return result

        retrieved_ids = [doc.get("id", doc.get("doc_id", str(i))) for i, doc in enumerate(retrieved_docs)]

        # 计算精确率和召回率
        if relevant_docs:
            retrieved_set = set(retrieved_ids)
            relevant_set = set(relevant_docs)

            true_positives = len(retrieved_set & relevant_set)
            false_positives = len(retrieved_set - relevant_set)
            false_negatives = len(relevant_set - retrieved_set)

            # 精确率
            if len(retrieved_set) > 0:
                result.precision = true_positives / len(retrieved_set)

            # 召回率
            if len(relevant_set) > 0:
                result.recall = true_positives / len(relevant_set)

            # F1
            if result.precision + result.recall > 0:
                result.f1 = 2 * (result.precision * result.recall) / (result.precision + result.recall)

        # MRR (Mean Reciprocal Rank)
        for i, doc_id in enumerate(retrieved_ids):
            if relevant_docs and doc_id in relevant_docs:
                result.mrr = 1.0 / (i + 1)
                break

        # NDCG (简化版本)
        dcg = 0.0
        for i, doc_id in enumerate(retrieved_ids):
            if relevant_docs and doc_id in relevant_docs:
                dcg += 1.0 / (i + 1)

        idcg = sum(1.0 / (i + 1) for i in range(min(len(relevant_docs or []), len(retrieved_docs))))
        result.ndcg = dcg / idcg if idcg > 0 else 0.0

        # 上下文利用率
        result.context_utilization = self._calculate_context_utilization(query, retrieved_docs)

        return result

    def _calculate_context_utilization(self, query: str, docs: List[Dict[str, Any]]) -> float:
        """计算上下文利用率

        Args:
            query: 查询
            docs: 文档列表

        Returns:
            float: 0.0-1.0 的利用率分数
        """
        if not docs:
            return 0.0

        query_terms = set(query.lower().split())
        utilized = 0

        for doc in docs:
            text = doc.get("text", doc.get("content", "")).lower()
            if any(term in text for term in query_terms):
                utilized += 1

        return utilized / len(docs)

    def evaluate_generation(
        self,
        query: str,
        answer: str,
        retrieved_docs: List[Dict[str, Any]],
        reference_answer: Optional[str] = None
    ) -> GenerationEvalResult:
        """评估生成质量

        Args:
            query: 查询
            answer: 生成的答案
            retrieved_docs: 检索到的文档
            reference_answer: 参考答案（用于计算准确率）

        Returns:
            GenerationEvalResult: 生成评估结果
        """
        result = GenerationEvalResult()

        # 答案相关性
        result.relevance = self._evaluate_relevance(query, answer)

        # 答案忠实度（答案是否基于检索到的上下文）
        result.faithfulness = self._evaluate_faithfulness(answer, retrieved_docs)

        # 答案准确率（如果提供了参考答案）
        if reference_answer:
            result.accuracy = self._evaluate_accuracy(answer, reference_answer)

        # 基于性（答案是否有依据）
        result.groundedness = self._evaluate_groundedness(answer, retrieved_docs)

        # 上下文相关性
        result.context_relevance = self._evaluate_context_relevance(query, retrieved_docs)

        return result

    def _evaluate_relevance(self, query: str, answer: str) -> float:
        """评估答案与查询的相关性"""
        query_terms = set(query.lower().split())
        answer_lower = answer.lower()

        if not query_terms:
            return 0.5

        matched = sum(1 for term in query_terms if term in answer_lower)
        return min(1.0, matched / len(query_terms))

    def _evaluate_faithfulness(self, answer: str, docs: List[Dict[str, Any]]) -> float:
        """评估答案是否忠实于检索到的文档"""
        if not docs:
            return 0.5

        # 检查答案中的关键信息是否能在文档中找到
        answer_lower = answer.lower()
        supported_count = 0

        for doc in docs:
            doc_text = doc.get("text", doc.get("content", "")).lower()
            # 简单的验证：检查答案中的句子是否能在文档中找到相似的
            sentences = answer.split('.')
            for sent in sentences[:3]:  # 只检查前3句
                sent = sent.strip()
                if len(sent) > 10:
                    # 简化判断：如果句子中有超过一半的词出现在文档中，认为是支持的
                    words = sent.lower().split()
                    matched = sum(1 for w in words if w in doc_text)
                    if matched > len(words) / 2:
                        supported_count += 1
                        break

        return supported_count / min(3, len(docs))

    def _evaluate_accuracy(self, answer: str, reference: str) -> float:
        """评估答案与参考答案的匹配度"""
        if not reference:
            return 0.5

        # 简化版本：基于词汇重叠
        answer_words = set(answer.lower().split())
        reference_words = set(reference.lower().split())

        if not answer_words or not reference_words:
            return 0.5

        overlap = len(answer_words & reference_words)
        union = len(answer_words | reference_words)

        return overlap / union if union > 0 else 0.5

    def _evaluate_groundedness(self, answer: str, docs: List[Dict[str, Any]]) -> float:
        """评估答案是否有据可查"""
        if not docs:
            return 0.3  # 无文档时给较低分

        # 检查答案中的事实性陈述是否与文档一致
        grounded_count = 0
        total_claims = 0

        # 简化处理：检查答案中的数字和术语是否在文档中
        answer_lower = answer.lower()
        for doc in docs:
            doc_text = doc.get("text", doc.get("content", "")).lower()
            # 统计答案中有多少内容能在文档中找到
            words = answer_lower.split()
            matched = sum(1 for w in words if len(w) > 4 and w in doc_text)
            if len(words) > 0:
                grounded_count += matched / len(words)
            total_claims += 1

        return grounded_count / total_claims if total_claims > 0 else 0.3

    def _evaluate_context_relevance(self, query: str, docs: List[Dict[str, Any]]) -> float:
        """评估检索到的上下文与查询的相关性"""
        if not docs:
            return 0.0

        query_terms = set(query.lower().split())
        total_relevance = 0.0

        for doc in docs:
            doc_text = doc.get("text", doc.get("content", "")).lower()
            matched = sum(1 for term in query_terms if term in doc_text)
            relevance = matched / len(query_terms) if query_terms else 0
            total_relevance += relevance

        return total_relevance / len(docs)

    def evaluate(
        self,
        query: str,
        answer: str,
        retrieved_docs: List[Dict[str, Any]],
        relevant_docs: Optional[List[str]] = None,
        reference_answer: Optional[str] = None
    ) -> RAGEvalResult:
        """完整的RAG系统评估

        Args:
            query: 用户查询
            answer: RAG系统生成的答案
            retrieved_docs: 检索到的文档
            relevant_docs: 实际相关的文档（用于检索评估）
            reference_answer: 参考答案（用于生成评估）

        Returns:
            RAGEvalResult: 综合评估结果
        """
        # 评估检索
        retrieval_result = self.evaluate_retrieval(query, retrieved_docs, relevant_docs)

        # 评估生成
        generation_result = self.evaluate_generation(query, answer, retrieved_docs, reference_answer)

        # 计算综合分数
        retrieval_score = self._compute_retrieval_score(retrieval_result)
        generation_score = self._compute_generation_score(generation_result)

        overall = 0.4 * retrieval_score + 0.6 * generation_score

        return RAGEvalResult(
            retrieval=retrieval_result,
            generation=generation_result,
            overall_score=overall,
            metadata={
                "query_length": len(query),
                "answer_length": len(answer),
                "num_retrieved_docs": len(retrieved_docs)
            }
        )

    def _compute_retrieval_score(self, result: RetrievalEvalResult) -> float:
        """计算检索综合分数"""
        return (
            result.precision * self.retrieval_weights["precision"] +
            result.recall * self.retrieval_weights["recall"] +
            result.f1 * self.retrieval_weights["f1"] +
            result.mrr * self.retrieval_weights["mrr"] +
            result.ndcg * self.retrieval_weights["ndcg"]
        )

    def _compute_generation_score(self, result: GenerationEvalResult) -> float:
        """计算生成综合分数"""
        return (
            result.relevance * self.generation_weights["relevance"] +
            result.faithfulness * self.generation_weights["faithfulness"] +
            result.accuracy * self.generation_weights["accuracy"] +
            result.groundedness * self.generation_weights["groundedness"] +
            result.context_relevance * self.generation_weights["context_relevance"]
        )


class RetrievalMetrics:
    """检索指标计算器"""

    @staticmethod
    def precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
        """计算P@K

        Args:
            retrieved: 检索到的文档ID列表
            relevant: 实际相关的文档ID集合
            k: 考虑前k个结果

        Returns:
            float: P@K分数
        """
        if k <= 0:
            return 0.0

        retrieved_k = retrieved[:k]
        if not retrieved_k:
            return 0.0

        relevant_set = set(relevant)
        hits = sum(1 for doc_id in retrieved_k if doc_id in relevant_set)
        return hits / k

    @staticmethod
    def recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
        """计算R@K

        Args:
            retrieved: 检索到的文档ID列表
            relevant: 实际相关的文档ID集合
            k: 考虑前k个结果

        Returns:
            float: R@K分数
        """
        if k <= 0 or not relevant:
            return 0.0

        retrieved_k = retrieved[:k]
        relevant_set = set(relevant)
        hits = sum(1 for doc_id in retrieved_k if doc_id in relevant_set)
        return hits / len(relevant_set)

    @staticmethod
    def average_precision(retrieved: List[str], relevant: List[str]) -> float:
        """计算平均精确率 (AP)

        Args:
            retrieved: 检索到的文档ID列表
            relevant: 实际相关的文档ID集合

        Returns:
            float: AP分数
        """
        if not relevant:
            return 0.0

        relevant_set = set(relevant)
        num_relevant = len(relevant_set)

        if num_relevant == 0:
            return 0.0

        hits = 0
        sum_precisions = 0.0

        for i, doc_id in enumerate(retrieved):
            if doc_id in relevant_set:
                hits += 1
                sum_precisions += hits / (i + 1)

        return sum_precisions / num_relevant

    @staticmethod
    def mean_average_precision(retrieved_list: List[List[str]], relevant_list: List[List[str]]) -> float:
        """计算平均精确率的平均值 (MAP)

        Args:
            retrieved_list: 多个查询的检索结果列表
            relevant_list: 多个查询的相关文档列表

        Returns:
            float: MAP分数
        """
        if not retrieved_list or not relevant_list:
            return 0.0

        aps = [
            RetrievalMetrics.average_precision(retrieved, relevant)
            for retrieved, relevant in zip(retrieved_list, relevant_list)
        ]

        return sum(aps) / len(aps)


# 便捷函数
def evaluate_rag(
    query: str,
    answer: str,
    retrieved_docs: List[Dict[str, Any]],
    **kwargs
) -> RAGEvalResult:
    """评估RAG系统的便捷函数

    Args:
        query: 查询
        answer: 答案
        retrieved_docs: 检索到的文档
        **kwargs: 其他参数

    Returns:
        RAGEvalResult: 评估结果
    """
    evaluator = RAGEvaluator()
    return evaluator.evaluate(query, answer, retrieved_docs, **kwargs)


def evaluate_retrieval(
    query: str,
    retrieved_docs: List[Dict[str, Any]],
    relevant_docs: Optional[List[str]] = None
) -> RetrievalEvalResult:
    """评估检索质量的便捷函数

    Args:
        query: 查询
        retrieved_docs: 检索到的文档
        relevant_docs: 实际相关的文档

    Returns:
        RetrievalEvalResult: 检索评估结果
    """
    evaluator = RAGEvaluator()
    return evaluator.evaluate_retrieval(query, retrieved_docs, relevant_docs)