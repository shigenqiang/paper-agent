"""
答案聚合器 - Answer Aggregator

多跳答案聚合，构建推理链，综合最终答案和引用。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.agents_v2.logging_config import get_logging_logger

import asyncio

logger = get_logging_logger(__name__)


@dataclass
class ReasoningStep:
    """推理步骤"""
    step: int
    question: str
    answer: str
    citations: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedResult:
    """聚合结果"""
    final_answer: str
    reasoning_chain: List[ReasoningStep]
    all_citations: List[Dict[str, Any]] = field(default_factory=list)
    overall_confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class AnswerAggregator:
    """答案聚合器

    将多个子问题的答案聚合为最终答案。
    """

    def __init__(
        self,
        llm: Optional[Any] = None,
    ):
        """初始化答案聚合器

        Args:
            llm: LLM 实例
        """
        self.llm = llm

    async def aggregate(
        self,
        original_query: str,
        sub_questions: List[Any],
        sub_answers: List[Any],
    ) -> Any:
        """聚合多跳答案

        Args:
            original_query: 原始问题
            sub_questions: 子问题列表
            sub_answers: 子答案列表

        Returns:
            AggregatedResult: 聚合结果
        """
        # 1. 构建推理链
        reasoning_chain = self._build_reasoning_chain(sub_questions, sub_answers)

        # 2. 聚合引用
        all_citations = self._aggregate_citations(sub_answers)

        # 3. 计算总体置信度
        overall_confidence = self._calculate_overall_confidence(sub_answers)

        # 4. 生成最终答案
        final_answer = await self._generate_final_answer(
            original_query, reasoning_chain
        )

        return AggregatedResult(
            final_answer=final_answer,
            reasoning_chain=reasoning_chain,
            all_citations=all_citations,
            overall_confidence=overall_confidence,
            metadata={
                "num_steps": len(reasoning_chain),
                "num_citations": len(all_citations),
            }
        )

    def _build_reasoning_chain(
        self,
        sub_questions: List[Any],
        sub_answers: List[Any],
    ) -> List[ReasoningStep]:
        """构建推理链

        Args:
            sub_questions: 子问题列表
            sub_answers: 子答案列表

        Returns:
            List[ReasoningStep]: 推理链
        """
        chain = []

        for i, (sq, sa) in enumerate(zip(sub_questions, sub_answers)):
            step = ReasoningStep(
                step=i + 1,
                question=sq.text if hasattr(sq, 'text') else str(sq),
                answer=sa.answer if hasattr(sa, 'answer') else str(sa),
                citations=sa.citations if hasattr(sa, 'citations') else [],
                confidence=sa.confidence if hasattr(sa, 'confidence') else 0.5,
            )
            chain.append(step)

        return chain

    def _aggregate_citations(self, sub_answers: List[Any]) -> List[Dict[str, Any]]:
        """聚合所有引用

        Args:
            sub_answers: 子答案列表

        Returns:
            List[Dict[str, Any]]: 聚合后的引用列表
        """
        seen_ids = set()
        citations = []

        for sa in sub_answers:
            if not hasattr(sa, 'citations'):
                continue

            for cit in sa.citations:
                source_id = cit.get('source_id', cit.get('id', ''))
                if source_id and source_id not in seen_ids:
                    seen_ids.add(source_id)
                    citations.append(cit)

        return citations[:10]  # 限制数量

    def _calculate_overall_confidence(
        self,
        sub_answers: List[Any],
    ) -> float:
        """计算总体置信度

        Args:
            sub_answers: 子答案列表

        Returns:
            float: 总体置信度
        """
        if not sub_answers:
            return 0.0

        confidences = []
        for sa in sub_answers:
            if hasattr(sa, 'confidence'):
                confidences.append(sa.confidence)
            elif hasattr(sa, 'success'):
                confidences.append(1.0 if sa.success else 0.0)

        if not confidences:
            return 0.5

        # 使用加权平均，越后面的步骤权重越高
        weighted_sum = sum(c * (i + 1) for i, c in enumerate(confidences))
        weight_sum = sum(i + 1 for i in range(len(confidences)))

        return weighted_sum / weight_sum if weight_sum > 0 else 0.0

    async def _generate_final_answer(
        self,
        original_query: str,
        reasoning_chain: List[ReasoningStep],
    ) -> str:
        """生成最终答案

        Args:
            original_query: 原始问题
            reasoning_chain: 推理链

        Returns:
            str: 最终答案
        """
        if not self.llm:
            return self._concatenate_chain(reasoning_chain)

        # 构建推理过程文本
        chain_text = "\n".join([
            f"步骤 {step.step}: {step.question}\n  答案: {step.answer}"
            for step in reasoning_chain
        ])

        prompt = f"""基于以下推理链，给出问题的最终答案。

原始问题: {original_query}

推理过程:
{chain_text}

要求:
1. 综合各步骤的答案，给出完整、连贯的最终答案
2. 清晰地呈现推理过程和结论
3. 如有矛盾，说明并尝试解决
4. 不要简单罗列各步骤的答案，要综合成连贯的段落

最终答案:"""

        try:
            answer = await self._call_llm(prompt)
            return answer
        except Exception as e:
            logger.error(f"Failed to generate final answer: {e}")
            return self._concatenate_chain(reasoning_chain)

    def _concatenate_chain(self, reasoning_chain: List[ReasoningStep]) -> str:
        """连接推理链为最终答案

        简单的聚合方法。
        """
        if not reasoning_chain:
            return "无法生成答案"

        # 找出标记为 final 的步骤
        final_steps = [s for s in reasoning_chain if s.step == len(reasoning_chain)]
        if final_steps:
            return final_steps[0].answer

        # 如果没有 final 步骤，连接所有答案
        parts = [f"（步骤 {step.step}）{step.answer}" for step in reasoning_chain]
        return "\n\n".join(parts)

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

    def format_result(self, result: AggregatedResult) -> str:
        """格式化聚合结果

        Args:
            result: 聚合结果

        Returns:
            str: 格式化的文本
        """
        lines = [
            "=== 多跳推理答案聚合 ===",
            f"总体置信度: {result.overall_confidence:.2f}",
            f"引用数量: {len(result.all_citations)}",
            "",
            "--- 推理链 ---",
        ]

        for step in result.reasoning_chain:
            lines.append(f"\n步骤 {step.step}: {step.question}")
            lines.append(f"答案: {step.answer}")

        lines.extend([
            "",
            "--- 最终答案 ---",
            result.final_answer,
        ])

        return "\n".join(lines)


# 便捷函数
async def aggregate_answers(
    original_query: str,
    sub_questions: List[Any],
    sub_answers: List[Any],
    llm: Optional[Any] = None,
) -> AggregatedResult:
    """答案聚合的便捷函数"""
    aggregator = AnswerAggregator(llm=llm)
    return await aggregator.aggregate(original_query, sub_questions, sub_answers)


def format_aggregated_result(result: AggregatedResult) -> str:
    """格式化聚合结果的便捷函数"""
    aggregator = AnswerAggregator()
    return aggregator.format_result(result)