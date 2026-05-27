"""
多跳推理器 - Multi-Hop Reasoner

协调子问题检索和答案聚合。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from src.agents_v2.logging_config import get_logging_logger
from src.agents_v2.academic_qa.query_decomposer import SubQuestion

import asyncio

logger = get_logging_logger(__name__)


@dataclass
class SubAnswer:
    """子问题答案"""
    sub_question: str
    answer: str
    citations: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    success: bool = True
    error: Optional[str] = None


@dataclass
class MultiHopResult:
    """多跳推理结果"""
    final_answer: str
    reasoning_chain: List[Dict[str, Any]]
    all_citations: List[Dict[str, Any]] = field(default_factory=list)
    overall_confidence: float = 0.0
    sub_answers: List[SubAnswer] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiHopReasoner:
    """多跳推理器

    协调多跳问题的分解、检索和答案聚合。
    """

    def __init__(
        self,
        llm: Optional[Any] = None,
        retriever: Optional[Callable] = None,
        decomposer: Optional[Any] = None,
        aggregator: Optional[Any] = None,
    ):
        """初始化多跳推理器

        Args:
            llm: LLM 实例
            retriever: 检索器
            decomposer: 查询分解器
            aggregator: 答案聚合器
        """
        self.llm = llm
        self.retriever = retriever
        self.decomposer = decomposer
        self.aggregator = aggregator

    async def reason(
        self,
        query: str,
        top_k: int = 5,
    ) -> MultiHopResult:
        """执行多跳推理

        Args:
            query: 用户问题
            top_k: 检索返回数量

        Returns:
            MultiHopResult: 推理结果
        """
        # 1. 分解问题
        if self.decomposer:
            sub_questions = await self.decomposer.decompose(query)
        else:
            # 使用内置分解
            from .query_decomposer import QueryDecomposer, SubQuestion
            decomposer = QueryDecomposer(self.llm)
            sub_questions = await decomposer.decompose(query)

        logger.info(f"Decomposed into {len(sub_questions)} sub-questions")

        # 2. 依次回答子问题
        sub_answers = []
        context_cache = {}  # 缓存中间答案

        for sq in sub_questions:
            try:
                # 检查依赖是否都满足
                if sq.depends_on:
                    deps_met = all(
                        context_cache.get(dep_id) is not None
                        for dep_id in sq.depends_on
                    )
                    if not deps_met:
                        logger.warning(f"Dependencies not met for sub-question {sq.id}")

                # 构建带有上下文的查询
                context_query = self._build_contextual_query(sq, context_cache)

                # 检索
                retrieved_docs = []
                if self.retriever:
                    retrieved_docs = await self._retrieve(context_query, top_k)

                # 生成答案
                sub_answer = await self._answer_sub_question(
                    sq.text, retrieved_docs, context_cache
                )

                # 缓存答案
                context_cache[sq.id] = sub_answer

                sub_answers.append(sub_answer)
                logger.info(f"Sub-question {sq.id} answered: {sub_answer.answer[:50]}...")

            except Exception as e:
                logger.error(f"Failed to answer sub-question {sq.id}: {e}")
                sub_answers.append(SubAnswer(
                    sub_question=sq.text,
                    answer="无法回答此子问题",
                    confidence=0.0,
                    success=False,
                    error=str(e),
                ))

        # 3. 聚合答案
        if self.aggregator:
            result = await self.aggregator.aggregate(query, sub_questions, sub_answers)
        else:
            # 使用内置聚合
            result = await self._simple_aggregate(query, sub_questions, sub_answers)

        return result

    def _build_contextual_query(
        self,
        sub_question: SubQuestion,
        context_cache: Dict[int, SubAnswer],
    ) -> str:
        """构建带上下文的查询

        将已回答的子问题的答案作为上下文加入查询。
        """
        query = sub_question.text

        if sub_question.depends_on:
            context_parts = []
            for dep_id in sub_question.depends_on:
                if dep_id in context_cache:
                    dep_answer = context_cache[dep_id]
                    context_parts.append(f"已确定的信息: {dep_answer.answer[:100]}")

            if context_parts:
                query = f"{query}\n\n上下文:\n" + "\n".join(context_parts)

        return query

    async def _retrieve(
        self,
        query: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """执行检索

        Args:
            query: 查询
            top_k: 返回数量

        Returns:
            List[Dict[str, Any]]: 检索结果
        """
        if not self.retriever:
            return []

        try:
            if asyncio.iscoroutinefunction(self.retriever):
                return await self.retriever(query, top_k=top_k)
            else:
                return self.retriever(query, top_k=top_k)
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []

    async def _answer_sub_question(
        self,
        question: str,
        retrieved_docs: List[Dict[str, Any]],
        context_cache: Dict[int, SubAnswer],
    ) -> SubAnswer:
        """回答子问题

        Args:
            question: 子问题
            retrieved_docs: 检索结果
            context_cache: 上下文缓存

        Returns:
            SubAnswer: 子问题答案
        """
        if not self.llm:
            # 无 LLM 时的简单处理
            if retrieved_docs:
                content = retrieved_docs[0].get("content", retrieved_docs[0].get("page_content", ""))
                return SubAnswer(
                    sub_question=question,
                    answer=content[:200],
                    citations=[],
                    confidence=0.5,
                )
            else:
                return SubAnswer(
                    sub_question=question,
                    answer="无法回答",
                    confidence=0.0,
                    success=False,
                )

        # 构建 prompt
        context_parts = []
        for doc in retrieved_docs[:3]:
            content = doc.get("content", doc.get("page_content", str(doc)))
            context_parts.append(f"[文档]\n{content[:300]}")

        context = "\n\n".join(context_parts)

        # 如果有前置答案，加入上下文
        for dep_id, dep_answer in context_cache.items():
            if dep_answer.success and dep_answer.answer:
                context += f"\n\n[已确定信息 {dep_id}]\n{dep_answer.answer[:150]}"

        prompt = f"""基于以下信息回答问题。

上下文:
{context if context else '（无相关上下文）'}

问题: {question}

要求:
1. 只使用提供的信息回答
2. 如果信息不足，明确说明
3. 简洁回答

答案:"""

        try:
            answer = await self._call_llm(prompt)

            # 提取引用
            citations = []
            for doc in retrieved_docs[:3]:
                citations.append({
                    "source_id": doc.get("id", doc.get("chunk_id", "unknown")),
                    "relevance": doc.get("score", 0.8),
                })

            return SubAnswer(
                sub_question=question,
                answer=answer,
                citations=citations,
                confidence=0.8 if retrieved_docs else 0.5,
            )

        except Exception as e:
            logger.error(f"Failed to answer sub-question: {e}")
            return SubAnswer(
                sub_question=question,
                answer="生成答案时发生错误",
                confidence=0.0,
                success=False,
                error=str(e),
            )

    async def _simple_aggregate(
        self,
        query: str,
        sub_questions: List[Any],
        sub_answers: List[SubAnswer],
    ) -> MultiHopResult:
        """简单的答案聚合

        无专门的聚合器时的降级方案。
        """
        # 构建推理链
        reasoning_chain = []
        for sq, sa in zip(sub_questions, sub_answers):
            reasoning_chain.append({
                "step": sq.id,
                "question": sq.text,
                "answer": sa.answer,
                "citations": sa.citations,
                "confidence": sa.confidence,
            })

        # 聚合所有引用
        all_citations = []
        for sa in sub_answers:
            all_citations.extend(sa.citations)

        # 计算总体置信度
        if sub_answers:
            confidences = [sa.confidence for sa in sub_answers]
            overall_confidence = sum(confidences) / len(confidences)
        else:
            overall_confidence = 0.0

        # 生成最终答案
        if self.llm:
            try:
                final_answer = await self._generate_final_answer(
                    query, reasoning_chain
                )
            except Exception:
                final_answer = self._concatenate_answers(sub_answers)
        else:
            final_answer = self._concatenate_answers(sub_answers)

        return MultiHopResult(
            final_answer=final_answer,
            reasoning_chain=reasoning_chain,
            all_citations=all_citations,
            overall_confidence=overall_confidence,
            sub_answers=sub_answers,
            metadata={
                "num_sub_questions": len(sub_questions),
                "num_successful": sum(1 for sa in sub_answers if sa.success),
            }
        )

    async def _generate_final_answer(
        self,
        query: str,
        reasoning_chain: List[Dict[str, Any]],
    ) -> str:
        """生成最终答案

        Args:
            query: 原始问题
            reasoning_chain: 推理链

        Returns:
            str: 最终答案
        """
        # 构建推理过程描述
        chain_text = "\n".join([
            f"步骤 {step['step']}: {step['question']}\n  答案: {step['answer']}"
            for step in reasoning_chain
        ])

        prompt = f"""基于以下推理过程，给出问题的最终答案。

原始问题: {query}

推理过程:
{chain_text}

要求:
1. 综合各步骤的答案，给出完整的最终答案
2. 清晰地呈现推理过程
3. 如有矛盾，说明并尝试解决

最终答案:"""

        try:
            return await self._call_llm(prompt)
        except Exception as e:
            logger.error(f"Failed to generate final answer: {e}")
            return self._concatenate_answers([
                SubAnswer(sub_question="", answer=step["answer"])
                for step in reasoning_chain
            ])

    def _concatenate_answers(self, sub_answers: List[SubAnswer]) -> str:
        """连接子答案

        简单的聚合方法。
        """
        parts = []
        for sa in sub_answers:
            if sa.success:
                parts.append(f"回答「{sa.sub_question}」：{sa.answer}")

        return "\n\n".join(parts) if parts else "无法生成答案"

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

    def format_result(self, result: MultiHopResult) -> str:
        """格式化推理结果

        Args:
            result: 推理结果

        Returns:
            str: 格式化的文本
        """
        lines = [
            "=== 多跳推理结果 ===",
            f"置信度: {result.overall_confidence:.2f}",
            "",
            "--- 推理链 ---",
        ]

        for step in result.reasoning_chain:
            lines.append(f"\n步骤 {step['step']}: {step['question']}")
            lines.append(f"答案: {step['answer']}")

        lines.extend([
            "",
            "--- 最终答案 ---",
            result.final_answer,
        ])

        if result.all_citations:
            lines.append("")
            lines.append("--- 引用 ---")
            for i, cit in enumerate(result.all_citations[:5], 1):
                lines.append(f"[{i}] {cit.get('source_id', 'unknown')}")

        return "\n".join(lines)


# 便捷函数
async def multi_hop_reason(
    query: str,
    llm: Optional[Any] = None,
    retriever: Optional[Callable] = None,
    **kwargs
) -> MultiHopResult:
    """多跳推理的便捷函数"""
    reasoner = MultiHopReasoner(llm=llm, retriever=retriever, **kwargs)
    return await reasoner.reason(query)