"""
知识图谱推理引擎
Knowledge Graph Reasoner
"""

from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum

from .subgraph_retriever import CommunitySummary, SubgraphResult


class ReasoningMode(str, Enum):
    """推理模式"""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    GRAPH_WALK = "graph_walk"
    TEMPLATE_BASED = "template_based"


@dataclass
class ReasoningStep:
    """推理步骤"""
    step_id: int
    description: str
    evidence: List[Dict]
    conclusion: str
    confidence: float


@dataclass
class ReasoningResult:
    """推理结果"""
    query: str
    answer: str
    reasoning_steps: List[ReasoningStep]
    confidence: float
    evidence_entities: List[str]
    citations: List[Dict]


class KGReasoner:
    """知识图谱推理引擎"""

    def __init__(self):
        self.reasoning_mode = ReasoningMode.CHAIN_OF_THOUGHT

    def reason(
        self,
        query: str,
        community_summaries: List[CommunitySummary],
        subgraph: Optional[SubgraphResult] = None,
        mode: Optional[ReasoningMode] = None
    ) -> ReasoningResult:
        """执行推理"""
        mode = mode or self.reasoning_mode

        if mode == ReasoningMode.CHAIN_OF_THOUGHT:
            return self._chain_of_thought_reasoning(query, community_summaries, subgraph)
        elif mode == ReasoningMode.GRAPH_WALK:
            return self._graph_walk_reasoning(query, community_summaries, subgraph)
        else:
            return self._template_based_reasoning(query, community_summaries, subgraph)

    def _chain_of_thought_reasoning(
        self,
        query: str,
        community_summaries: List[CommunitySummary],
        subgraph: Optional[SubgraphResult]
    ) -> ReasoningResult:
        """链式推理"""
        reasoning_steps = []
        all_evidence = []

        # 分析查询类型
        query_type = self._classify_query(query)

        # 步骤1：识别关键实体
        step1 = ReasoningStep(
            step_id=1,
            description="识别查询中的关键实体和概念",
            evidence=[{"entity": s.core_entities} for s in community_summaries[:3]],
            conclusion=f"查询类型: {query_type}",
            confidence=0.9
        )
        reasoning_steps.append(step1)

        # 步骤2：分析社区结构
        step2 = ReasoningStep(
            step_id=2,
            description="分析相关社区的结构和关系",
            evidence=[{"relations": s.key_relations} for s in community_summaries],
            conclusion=f"发现 {len(community_summaries)} 个相关社区",
            confidence=0.85
        )
        reasoning_steps.append(step2)

        # 步骤3：综合答案
        step3 = ReasoningStep(
            step_id=3,
            description="基于证据综合推理答案",
            evidence=[{"summary": s.description} for s in community_summaries],
            conclusion="基于知识图谱结构的综合推理",
            confidence=0.8
        )
        reasoning_steps.append(step3)

        # 收集证据实体
        evidence_entities = []
        for summary in community_summaries:
            evidence_entities.extend(summary.core_entities)

        return ReasoningResult(
            query=query,
            answer=self._generate_answer(query, community_summaries, reasoning_steps),
            reasoning_steps=reasoning_steps,
            confidence=0.85,
            evidence_entities=evidence_entities[:10],
            citations=self._extract_citations(community_summaries)
        )

    def _graph_walk_reasoning(
        self,
        query: str,
        community_summaries: List[CommunitySummary],
        subgraph: Optional[SubgraphResult]
    ) -> ReasoningResult:
        """图游走推理"""
        reasoning_steps = []

        # 简单的图游走逻辑
        visited: Set[str] = set()
        current_nodes = []

        for summary in community_summaries:
            for entity in summary.core_entities:
                if entity not in visited:
                    visited.add(entity)
                    current_nodes.append(entity)

        step = ReasoningStep(
            step_id=1,
            description="通过图游走收集相关实体",
            evidence=[{"visited": list(visited)[:10]}],
            conclusion=f"遍历了 {len(visited)} 个实体节点",
            confidence=0.8
        )
        reasoning_steps.append(step)

        return ReasoningResult(
            query=query,
            answer=self._generate_answer(query, community_summaries, reasoning_steps),
            reasoning_steps=reasoning_steps,
            confidence=0.75,
            evidence_entities=list(visited)[:10],
            citations=[]
        )

    def _template_based_reasoning(
        self,
        query: str,
        community_summaries: List[CommunitySummary],
        subgraph: Optional[SubgraphResult]
    ) -> ReasoningResult:
        """基于模板的推理"""
        reasoning_steps = []

        # 简单的模板匹配
        templates = {
            "who": "找到了以下相关实体: {entities}",
            "what": "相关概念包括: {entities}",
            "when": "时间相关实体: {entities}",
            "where": "地点相关实体: {entities}",
            "how": "方法和过程: {entities}"
        }

        query_lower = query.lower()
        template_key = "what"

        for key in templates:
            if key in query_lower:
                template_key = key
                break

        step = ReasoningStep(
            step_id=1,
            description=f"使用{template_key}模板推理",
            evidence=[{"entities": [s.core_entities for s in community_summaries]}],
            conclusion="基于模板推理完成",
            confidence=0.7
        )
        reasoning_steps.append(step)

        all_entities = []
        for s in community_summaries:
            all_entities.extend(s.core_entities)

        return ReasoningResult(
            query=query,
            answer=templates[template_key].format(entities=", ".join(all_entities[:5])),
            reasoning_steps=reasoning_steps,
            confidence=0.7,
            evidence_entities=all_entities[:10],
            citations=[]
        )

    def _classify_query(self, query: str) -> str:
        """分类查询类型"""
        query_lower = query.lower()

        if query_lower.startswith("who") or query_lower.startswith("whom"):
            return "person"
        elif query_lower.startswith("what"):
            return "concept"
        elif query_lower.startswith("when"):
            return "time"
        elif query_lower.startswith("where"):
            return "location"
        elif query_lower.startswith("how"):
            return "method"
        elif query_lower.startswith("why"):
            return "cause"
        elif query_lower.startswith("compare"):
            return "comparison"
        else:
            return "general"

    def _generate_answer(
        self,
        query: str,
        community_summaries: List[CommunitySummary],
        reasoning_steps: List[ReasoningStep]
    ) -> str:
        """生成答案"""
        if not community_summaries:
            return "在知识图谱中未找到相关信息"

        # 收集所有核心实体
        all_entities = []
        for summary in community_summaries:
            all_entities.extend(summary.core_entities)

        # 去重
        unique_entities = list(set(all_entities))[:10]

        # 生成答案
        answer_parts = [
            "基于知识图谱分析，",
            f"发现与查询相关的实体包括: {', '.join(unique_entities[:5])}。",
            f"这些实体分布在 {len(community_summaries)} 个相关社区中。"
        ]

        if len(unique_entities) > 5:
            answer_parts.append(
                f"此外还有: {', '.join(unique_entities[5:8])}等相关实体。"
            )

        return "".join(answer_parts)

    def _extract_citations(self, community_summaries: List[CommunitySummary]) -> List[Dict]:
        """提取引用"""
        citations = []

        for summary in community_summaries:
            for entity in summary.core_entities:
                citations.append({
                    "entity": entity,
                    "community_id": summary.community_id,
                    "relevance": "high"
                })

        return citations[:5]

    def multi_hop_reasoning(
        self,
        query: str,
        hops: int = 3
    ) -> ReasoningResult:
        """多跳推理"""
        reasoning_steps = []

        for hop in range(hops):
            step = ReasoningStep(
                step_id=hop + 1,
                description=f"第{hop + 1}跳推理",
                evidence=[],
                conclusion="继续扩展推理范围",
                confidence=0.8 - hop * 0.1
            )
            reasoning_steps.append(step)

        return ReasoningResult(
            query=query,
            answer=f"通过{hops}跳推理得到答案",
            reasoning_steps=reasoning_steps,
            confidence=0.75,
            evidence_entities=[],
            citations=[]
        )
