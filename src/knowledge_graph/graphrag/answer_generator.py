"""
GraphRAG答案生成器
GraphRAG Answer Generator
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from .subgraph_retriever import CommunitySummary
from .reasoner import ReasoningResult, KGReasoner


@dataclass
class GraphRAGAnswer:
    """GraphRAG答案"""
    answer: str
    reasoning_steps: List[Dict]
    citations: List[Dict]
    confidence: float
    used_communities: List[int]


class GraphRAGAnswerGenerator:
    """GraphRAG答案生成器"""

    def __init__(self, llm=None):
        self.llm = llm
        self.reasoner = KGReasoner()

    def generate(
        self,
        query: str,
        community_summaries: List[CommunitySummary],
        subgraph: Optional[Any] = None,
        use_llm: bool = True
    ) -> GraphRAGAnswer:
        """生成答案"""
        # 1. 推理
        reasoning_result = self.reasoner.reason(
            query=query,
            community_summaries=community_summaries,
            subgraph=subgraph
        )

        # 2. 使用LLM生成（如果可用）
        if use_llm and self.llm:
            answer = self._generate_with_llm(
                query, community_summaries, reasoning_result
            )
        else:
            answer = reasoning_result.answer

        # 3. 提取引用
        citations = self._extract_citations(community_summaries, reasoning_result)

        return GraphRAGAnswer(
            answer=answer,
            reasoning_steps=[
                {
                    "step_id": s.step_id,
                    "description": s.description,
                    "conclusion": s.conclusion,
                    "confidence": s.confidence
                }
                for s in reasoning_result.reasoning_steps
            ],
            citations=citations,
            confidence=reasoning_result.confidence,
            used_communities=[s.community_id for s in community_summaries]
        )

    def _generate_with_llm(
        self,
        query: str,
        community_summaries: List[CommunitySummary],
        reasoning_result: ReasoningResult
    ) -> str:
        """使用LLM生成答案"""
        if not self.llm:
            return reasoning_result.answer

        # 构建上下文
        context = self._build_context(community_summaries)

        # 构建提示
        prompt = self._build_prompt(query, context, reasoning_result)

        # 调用LLM
        try:
            answer = self.llm.generate(prompt)
            return answer
        except Exception as e:
            print(f"LLM generation failed: {e}")
            return reasoning_result.answer

    def _build_context(
        self,
        community_summaries: List[CommunitySummary]
    ) -> str:
        """构建上下文"""
        context_parts = []

        for i, summary in enumerate(community_summaries):
            context_parts.append(
                f"【社区{i + 1}】{summary.description}\n"
                f"核心实体: {', '.join(summary.core_entities)}\n"
                f"关键关系: {', '.join(summary.key_relations)}"
            )

        return "\n\n".join(context_parts)

    def _build_prompt(
        self,
        query: str,
        context: str,
        reasoning_result: ReasoningResult
    ) -> str:
        """构建提示"""
        reasoning_chain = "\n".join([
            f"步骤{s.step_id}: {s.description} -> {s.conclusion}"
            for s in reasoning_result.reasoning_steps
        ])

        return f"""你是一个专业的学术问答助手。基于以下知识图谱信息回答用户问题。

知识图谱信息:
{context}

推理过程:
{reasoning_chain}

用户问题: {query}

回答要求:
1. 基于提供的知识图谱信息给出准确答案
2. 引用信息来源，使用[来源]格式
3. 如知识图谱信息不足以回答，明确说明
4. 保持学术严谨性，避免编造
5. 综合推理过程，给出最终答案

答案:"""

    def _extract_citations(
        self,
        community_summaries: List[CommunitySummary],
        reasoning_result: ReasoningResult
    ) -> List[Dict]:
        """提取引用"""
        citations = []

        for summary in community_summaries:
            for entity in summary.core_entities:
                citations.append({
                    "entity": entity,
                    "community": f"社区{summary.community_id}",
                    "relevance": "high",
                    "description": summary.description
                })

        return citations[:10]

    def generate_citation_string(
        self,
        citations: List[Dict],
        style: str = "inline"
    ) -> str:
        """生成引用字符串"""
        if style == "inline":
            # 格式: [实体1, 实体2, ...]
            entities = [c["entity"] for c in citations[:5]]
            return f"[{', '.join(entities)}]"

        elif style == "numbered":
            # 格式: [1] 实体1, [2] 实体2, ...
            parts = []
            for i, c in enumerate(citations[:5], 1):
                parts.append(f"[{i}] {c['entity']}")
            return ", ".join(parts)

        elif style == "parenthetical":
            # 格式: (实体1, 实体2, ..., 2024)
            entities = [c["entity"] for c in citations[:3]]
            return f"({'、'.join(entities)}, 2024)"

        else:
            return str(citations[:3])

    def format_answer_with_citations(
        self,
        answer: str,
        citations: List[Dict]
    ) -> str:
        """格式化带引用的答案"""
        if not citations:
            return answer

        # 在答案末尾添加引用
        citation_str = self.generate_citation_string(citations)

        return f"""{answer}

参考文献: {citation_str}"""

    def batch_generate(
        self,
        queries: List[str],
        community_summaries_list: List[List[CommunitySummary]]
    ) -> List[GraphRAGAnswer]:
        """批量生成答案"""
        answers = []

        for query, summaries in zip(queries, community_summaries_list):
            answer = self.generate(query, summaries)
            answers.append(answer)

        return answers
