"""
Knowledge Graph Agent - builds a knowledge graph from paper cards and evidence.

Creates nodes (Paper, Topic, Method, Finding, Limitation, Gap, InnovationPoint)
and edges (BELONGS_TO_TOPIC, USES_METHOD, etc.) per AGENT.md §4.
"""

from __future__ import annotations

import logging

from src.agent_v3.agents.base import BaseAgent
from src.agent_v3.core.config import AppConfig
from src.agent_v3.models import (
    EvidenceRecord,
    KGEdge,
    KGNode,
    KnowledgeGraph,
    NodeType,
    PaperCard,
    RelationType,
)

logger = logging.getLogger(__name__)

KG_SYSTEM_PROMPT = """你是一个学术知识图谱构建专家。你的任务是从论文卡片和证据表中提取知识图谱节点和关系。

请严格按照JSON格式输出。"""

KG_PROMPT = """请从以下论文信息中提取知识图谱的节点和关系。

## 论文卡片
标题: {title}
论文ID: {paper_id}
作者: {authors}
研究问题: {research_question}
方法: {method}
数据集: {dataset}
关键发现: {findings}
局限性: {limitations}
相关主题: {topics}

## 证据记录
{evidence_text}

请输出JSON格式：
{{
  "nodes": [
    {{"type": "Topic", "label": "主题名"}},
    {{"type": "Method", "label": "方法名"}},
    {{"type": "Task", "label": "任务名"}},
    {{"type": "Dataset", "label": "数据集名"}},
    {{"type": "Finding", "label": "发现描述"}},
    {{"type": "Limitation", "label": "局限描述"}},
    {{"type": "Gap", "label": "研究空白描述"}},
    {{"type": "InnovationPoint", "label": "创新点描述"}}
  ],
  "edges": [
    {{"source_label": "论文标题", "target_label": "主题名", "relation": "BELONGS_TO_TOPIC"}},
    {{"source_label": "论文标题", "target_label": "方法名", "relation": "USES_METHOD"}}
  ]
}}

关系类型: BELONGS_TO_TOPIC, STUDIES_TASK, USES_METHOD, USES_DATASET, REPORTS_FINDING, HAS_LIMITATION, SUGGESTS_GAP, SUPPORTS_INNOVATION

注意：
- source_label和target_label必须与nodes中的label完全一致（论文节点用标题）
- 不要编造信息
- 如果局限性指向某个研究空白，添加SUGGESTS_GAP关系
- 如果研究空白支持某个创新点，添加SUPPORTS_INNOVATION关系"""


class KGAgent(BaseAgent):
    """Build knowledge graph from paper cards and evidence."""

    def __init__(self, config: AppConfig):
        super().__init__(config, name="kg_agent")

    async def build_graph(
        self,
        cards: list[PaperCard],
        evidence: list[EvidenceRecord],
    ) -> KnowledgeGraph:
        """
        Build a knowledge graph from paper cards and evidence.

        Args:
            cards: Paper cards
            evidence: Evidence records

        Returns:
            KnowledgeGraph with nodes and edges
        """
        kg = KnowledgeGraph()

        # Add paper nodes
        paper_label_to_id = {}
        for card in cards:
            node = KGNode(
                node_id=card.paper_id,
                node_type=NodeType.PAPER,
                label=card.title,
                properties={
                    "authors": card.authors,
                    "year": card.year,
                    "venue": card.venue,
                },
            )
            kg.add_node(node)
            paper_label_to_id[card.title] = card.paper_id

        # For each paper, extract graph elements via LLM
        for card in cards:
            evidence_for_paper = [e for e in evidence if e.paper_id == card.paper_id]
            evidence_text = (
                "\n".join(
                    f"- [{e.evidence_strength}] {e.finding} (topic: {e.topic})"
                    for e in evidence_for_paper
                )
                or "无证据记录"
            )

            prompt = KG_PROMPT.format(
                title=card.title,
                paper_id=card.paper_id,
                authors=", ".join(card.authors),
                research_question=card.research_question,
                method=card.method,
                dataset=card.dataset_or_sample,
                findings="\n".join(f"- {f}" for f in card.key_findings) or "未提及",
                limitations="\n".join(f"- {l}" for l in card.limitations) or "未提及",
                topics=", ".join(card.related_topics) or "未分类",
                evidence_text=evidence_text,
            )

            try:
                result = await self.call_llm(prompt, KG_SYSTEM_PROMPT, json_mode=True)
            except Exception as e:
                logger.error(f"KG extraction failed for '{card.title}': {e}")
                continue

            # Process nodes
            label_to_id = dict(paper_label_to_id)
            for node_data in result.get("nodes", []):
                node_type_str = node_data.get("type", "Topic")
                try:
                    node_type = NodeType(node_type_str)
                except ValueError:
                    node_type = NodeType.TOPIC

                label = node_data.get("label", "")
                if not label:
                    continue

                # Check if node already exists
                existing = next(
                    (
                        n
                        for n in kg.nodes
                        if n.label == label and n.node_type == node_type
                    ),
                    None,
                )
                if existing:
                    label_to_id[label] = existing.node_id
                else:
                    node = KGNode(node_type=node_type, label=label)
                    kg.add_node(node)
                    label_to_id[label] = node.node_id

            # Process edges
            for edge_data in result.get("edges", []):
                source_label = edge_data.get("source_label", "")
                target_label = edge_data.get("target_label", "")
                relation_str = edge_data.get("relation", "BELONGS_TO_TOPIC")

                source_id = label_to_id.get(source_label)
                target_id = label_to_id.get(target_label)

                if not source_id or not target_id:
                    logger.warning(
                        f"Edge skipped: {source_label} -> {target_label} (node not found)"
                    )
                    continue

                try:
                    relation = RelationType(relation_str)
                except ValueError:
                    relation = RelationType.BELONGS_TO_TOPIC

                edge = KGEdge(
                    source_id=source_id,
                    target_id=target_id,
                    relation=relation,
                )
                kg.add_edge(edge)

            logger.info(
                f"KG for '{card.title[:40]}': "
                f"{len(result.get('nodes', []))} nodes, {len(result.get('edges', []))} edges"
            )

        logger.info(f"Total KG: {len(kg.nodes)} nodes, {len(kg.edges)} edges")
        return kg
