"""
RAGAs 评估器 - RAGAs Evaluator

RAGAs (Retrieval Augmented Generation Assessment) 评估框架集成。
评估指标：
- Faithfulness: 答案对上下文的忠实度
- Answer Relevance: 答案与问题的相关性
- Context Precision: 上下文的精确度
- Context Recall: 上下文的召回率（需要参考答案）
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.agents_v2.logging_config import get_logging_logger

import asyncio

logger = get_logging_logger(__name__)


@dataclass
class RAGAsMetrics:
    """RAGAs 评估指标"""
    faithfulness: float  # 忠实度 (0-1)
    answer_relevance: float  # 答案相关性 (0-1)
    context_precision: float  # 上下文精确度 (0-1)
    context_recall: Optional[float]  # 上下文召回率 (0-1，需要参考答案)
    avg_score: float  # 平均分
    metadata: Dict[str, Any] = field(default_factory=dict)


class RAGAsEvaluator:
    """RAGAs 评估器

    集成了 RAGAs 评估框架的核心指标。
    """

    def __init__(
        self,
        llm: Optional[Any] = None,
        reference_answer: Optional[str] = None,
    ):
        """初始化 RAGAs 评估器

        Args:
            llm: LLM 实例
            reference_answer: 参考答案（用于计算 Context Recall）
        """
        self.llm = llm
        self.reference_answer = reference_answer

    async def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
    ) -> RAGAsMetrics:
        """评估 RAG 系统质量

        Args:
            question: 用户问题
            answer: 生成的答案
            contexts: 上下文列表

        Returns:
            RAGAsMetrics: 评估指标
        """
        # 并行计算各指标
        faithfulness_task = self._evaluate_faithfulness(question, answer, contexts)
        relevance_task = self._evaluate_answer_relevance(question, answer)
        precision_task = self._evaluate_context_precision(question, contexts)

        faithfulness, relevance, precision = await asyncio.gather(
            faithfulness_task, relevance_task, precision_task
        )

        # Context Recall（需要参考答案）
        context_recall = None
        if self.reference_answer:
            context_recall = await self._evaluate_context_recall(
                contexts, self.reference_answer
            )

        # 计算平均分
        scores = [faithfulness, relevance, precision]
        if context_recall is not None:
            scores.append(context_recall)
        avg_score = sum(scores) / len(scores)

        return RAGAsMetrics(
            faithfulness=faithfulness,
            answer_relevance=relevance,
            context_precision=precision,
            context_recall=context_recall,
            avg_score=avg_score,
            metadata={
                "num_contexts": len(contexts),
                "has_reference": self.reference_answer is not None,
            }
        )

    async def _evaluate_faithfulness(
        self,
        question: str,
        answer: str,
        contexts: List[str],
    ) -> float:
        """评估忠实度

        答案中的事实声明是否可以被上下文推断。
        """
        if not self.llm:
            return self._simple_faithfulness(answer, contexts)

        # 提取答案中的声明
        statements = await self._extract_statements(answer)

        if not statements:
            return 1.0  # 无声明默认完全忠实

        # 检查每个声明是否可以从上下文推断
        verified_count = 0
        for stmt in statements:
            can_infer = await self._can_infer_from_context(stmt, contexts)
            if can_infer:
                verified_count += 1

        return verified_count / len(statements)

    async def _can_infer_from_context(
        self,
        statement: str,
        contexts: List[str],
    ) -> bool:
        """判断声明是否可以从上下文推断

        Args:
            statement: 声明
            contexts: 上下文列表

        Returns:
            bool: 是否可以推断
        """
        context_text = "\n".join(ctx[:500] for ctx in contexts[:3])

        prompt = f"""判断以下声明是否可以从提供的上下文推断出来。

声明: {statement}

上下文:
{context_text}

请判断：能推断出来 / 不能推断出来"""

        try:
            response = await self._call_llm(prompt)
            return "能推断出来" in response
        except Exception as e:
            logger.error(f"Faithfulness check failed: {e}")
            return False

    async def _extract_statements(self, text: str) -> List[str]:
        """从文本中提取声明

        Args:
            text: 文本

        Returns:
            List[str]: 声明列表
        """
        if not self.llm:
            return self._simple_extract_statements(text)

        prompt = f"""从以下文本中提取所有可验证的事实声明。
每个声明应该是一个完整的陈述句。

文本: {text}

声明列表（每行一个）："""

        try:
            response = await self._call_llm(prompt)
            lines = response.strip().split("\n")
            statements = []
            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line[0] in "-●◆"):
                    content = line.split(".", 1)[-1].split("-", 1)[-1].strip()
                    if content and len(content) > 5:
                        statements.append(content)
            return statements if statements else [text[:200]]
        except Exception:
            return self._simple_extract_statements(text)

    def _simple_extract_statements(self, text: str) -> List[str]:
        """简单的声明提取"""
        import re
        sentence_endings = r'[。！？.!?]+'
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if len(s.strip()) > 10][:10]

    def _simple_faithfulness(
        self,
        answer: str,
        contexts: List[str],
    ) -> float:
        """简单的忠实度评估"""
        if not contexts:
            return 0.5

        context_text = " ".join(ctx.lower() for ctx in contexts)
        answer_terms = set(answer.lower().split())
        context_terms = set(context_text.split())

        if not answer_terms:
            return 1.0

        overlap = len(answer_terms & context_terms)
        return min(1.0, overlap / len(answer_terms) * 1.5)

    async def _evaluate_answer_relevance(
        self,
        question: str,
        answer: str,
    ) -> float:
        """评估答案相关性

        答案是否直接回答了问题。
        """
        if not self.llm:
            return self._simple_relevance(question, answer)

        prompt = f"""评估以下答案对问题的相关程度。

问题: {question}

答案: {answer}

评分标准 (0-1):
- 1.0: 完全相关，答案直接、完整地回答了问题
- 0.7: 高度相关，答案回答了问题的主要方面
- 0.5: 中度相关，答案部分相关但有偏离
- 0.3: 低度相关，答案与问题关联较少
- 0.0: 完全不相关，答案没有回答问题

请只输出一个数字（0.0-1.0）："""

        try:
            response = await self._call_llm(prompt)
            response_clean = response.strip()
            try:
                score = float(response_clean)
            except ValueError:
                import re
                # 匹配各种可能的数字格式：0.5, 0.75, 1.0, 0, 1, 0.85等
                # 也处理如 "评分: 0.8" 或 "得分是0.5" 等格式
                numbers = re.findall(r'(?:0?\.\d+|1\.0|0(?!\.\d)|1(?!\.\d))', response_clean)
                if numbers:
                    score = float(numbers[0])
                else:
                    # 如果找不到数字，返回默认值并记录
                    logger.warning(f"No numeric score found in response: {response_clean[:80]}...")
                    return 0.5
            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.error(f"Answer relevance evaluation failed: {e}")
            return 0.5

    def _simple_relevance(self, question: str, answer: str) -> float:
        """简单的相关性评估"""
        if not answer:
            return 0.0

        # 检查问题关键词是否在答案中出现
        question_terms = set(question.lower().split())
        answer_terms = set(answer.lower().split())

        if not question_terms:
            return 0.5

        overlap = len(question_terms & answer_terms)
        return min(1.0, overlap / len(question_terms) * 1.5)

    async def _evaluate_context_precision(
        self,
        question: str,
        contexts: List[str],
    ) -> float:
        """评估上下文精确度

        上下文中有多少相关内容（不考虑排序）。
        """
        if not contexts:
            return 0.0

        if not self.llm:
            return self._simple_precision(question, contexts)

        # 评估每个上下文与问题的相关性
        relevance_scores = []
        for ctx in contexts:
            score = await self._evaluate_single_precision(question, ctx)
            relevance_scores.append(score)

        # 只考虑相关性 > 0.5 的上下文
        relevant_count = sum(1 for s in relevance_scores if s > 0.5)
        total_count = len(contexts)

        return relevant_count / total_count if total_count > 0 else 0.0

    async def _evaluate_single_precision(
        self,
        question: str,
        context: str,
    ) -> float:
        """评估单个上下文的精确度

        Args:
            question: 问题
            context: 上下文

        Returns:
            float: 相关性分数 (0-1)
        """
        prompt = f"""评估以下上下文对于回答问题的相关性。

问题: {question}

上下文: {context[:300]}

评分标准 (0-1):
- 1.0: 完全相关，直接支持回答问题
- 0.5: 部分相关，提供一定的支持
- 0.0: 不相关，对回答问题没有帮助

请只输出一个数字（0.0-1.0）："""

        try:
            response = await self._call_llm(prompt)
            response_clean = response.strip()
            try:
                score = float(response_clean)
            except ValueError:
                import re
                numbers = re.findall(r'0\.\d+|1\.0|[01]', response_clean)
                if numbers:
                    score = float(numbers[0])
                else:
                    logger.warning(f"No numeric score in context precision: {response_clean[:50]}...")
                    return 0.5
            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.error(f"Context precision evaluation failed: {e}")
            return 0.5

    def _simple_precision(
        self,
        question: str,
        contexts: List[str],
    ) -> float:
        """简单的精确度评估"""
        if not contexts:
            return 0.0

        question_terms = set(question.lower().split())
        precision_scores = []

        for ctx in contexts:
            ctx_terms = set(ctx.lower().split())
            if question_terms:
                overlap = len(question_terms & ctx_terms)
                score = overlap / len(question_terms)
            else:
                score = 0.5
            precision_scores.append(score)

        # 计算加权平均
        return sum(precision_scores) / len(precision_scores)

    async def _evaluate_context_recall(
        self,
        contexts: List[str],
        reference_answer: str,
    ) -> float:
        """评估上下文召回率

        上下文是否包含了参考答案中的关键信息。
        """
        if not self.llm:
            return self._simple_recall(contexts, reference_answer)

        # 提取参考答案中的关键信息
        key_points = await self._extract_key_points(reference_answer)

        if not key_points:
            return 1.0

        # 检查每个关键点是否在上下文中
        covered_count = 0
        for point in key_points:
            point_found = self._point_in_contexts(point, contexts)
            if point_found:
                covered_count += 1

        return covered_count / len(key_points)

    async def _extract_key_points(self, text: str) -> List[str]:
        """提取关键点

        Args:
            text: 文本

        Returns:
            List[str]: 关键点列表
        """
        prompt = f"""从以下文本中提取关键信息点。
每个关键点应该是一个可以独立验证的事实或数字。

文本: {text}

关键点列表（每行一个）："""

        try:
            response = await self._call_llm(prompt)
            lines = response.strip().split("\n")
            points = []
            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line[0] in "-●◆"):
                    content = line.split(".", 1)[-1].split("-", 1)[-1].strip()
                    if content and len(content) > 3:
                        points.append(content)
            return points if points else [text[:200]]
        except Exception:
            return [text[:200]]

    def _point_in_contexts(self, point: str, contexts: List[str]) -> bool:
        """检查关键点是否在上下文中

        Args:
            point: 关键点
            contexts: 上下文列表

        Returns:
            bool: 是否找到
        """
        point_lower = point.lower()
        for ctx in contexts:
            if point_lower in ctx.lower():
                return True
        return False

    def _simple_recall(
        self,
        contexts: List[str],
        reference_answer: str,
    ) -> float:
        """简单的召回率评估"""
        if not reference_answer or not contexts:
            return 0.5

        context_text = " ".join(ctx.lower() for ctx in contexts)
        ref_terms = set(reference_answer.lower().split())

        if not ref_terms:
            return 1.0

        overlap = len(ref_terms & set(context_text.split()))
        return min(1.0, overlap / len(ref_terms) * 1.5)

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

    def format_metrics(self, metrics: RAGAsMetrics) -> str:
        """格式化评估指标

        Args:
            metrics: 评估指标

        Returns:
            str: 格式化的文本
        """
        lines = [
            "=== RAGAs 评估结果 ===",
            f"平均分: {metrics.avg_score:.2f}",
            "",
            "各维度分数:",
            f"  - Faithfulness (忠实度): {metrics.faithfulness:.2f}",
            f"  - Answer Relevance (答案相关性): {metrics.answer_relevance:.2f}",
            f"  - Context Precision (上下文精确度): {metrics.context_precision:.2f}",
        ]

        if metrics.context_recall is not None:
            lines.append(f"  - Context Recall (上下文召回率): {metrics.context_recall:.2f}")

        lines.append("")
        lines.append(f"上下文数量: {metrics.metadata.get('num_contexts', 0)}")

        return "\n".join(lines)


# 便捷函数
async def evaluate_ragas(
    question: str,
    answer: str,
    contexts: List[str],
    llm: Optional[Any] = None,
    **kwargs
) -> RAGAsMetrics:
    """RAGAs 评估的便捷函数"""
    evaluator = RAGAsEvaluator(llm=llm, **kwargs)
    return await evaluator.evaluate(question, answer, contexts)


def format_ragas_metrics(metrics: RAGAsMetrics) -> str:
    """格式化 RAGAs 指标的便捷函数"""
    evaluator = RAGAsEvaluator()
    return evaluator.format_metrics(metrics)