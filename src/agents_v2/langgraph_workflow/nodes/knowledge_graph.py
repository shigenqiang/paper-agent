"""
Knowledge Graph Node - LangGraph 工作流知识图谱节点

集成知识图谱服务，提供实体抽取、关系构建和图推理查询。
"""

from typing import Any, Dict, List, Optional

from ..state import PaperAgentState, Paper

logger = get_logging_logger(__name__)


class KnowledgeGraphNode:
    """知识图谱节点 - LangGraph 节点

    功能：
    1. 从论文中自动抽取实体和关系
    2. 构建论文知识图谱
    3. 基于图谱的关联推理
    4. 发现跨论文的知识关联
    """

    def __init__(self, kg_service=None):
        """
        Args:
            kg_service: KnowledgeGraphService 实例（可选）
        """
        self._kg_service = kg_service

    def extract_and_build(self, state: PaperAgentState) -> PaperAgentState:
        """从选中论文中抽取实体和关系，构建知识图谱"""
        papers = state.selected_papers or state.papers
        if not papers:
            return state

        # 如果有 KG 服务，使用服务进行图构建
        if self._kg_service:
            return self._build_via_service(state, papers)

        # 否则使用规则提取
        return self._build_via_rules(state, papers)

    def _build_via_service(self, state: PaperAgentState, papers: List[Paper]) -> PaperAgentState:
        """通过 KG 服务构建"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            entities = []
            relations = []

            for paper in papers[:10]:
                # 使用服务提取实体
                result = loop.run_until_complete(
                    self._kg_service.extract_entities(
                        text=f"{paper.title}. {paper.abstract}",
                        source_id=paper.id,
                    )
                )
                entities.extend(result.get("entities", []))
                relations.extend(result.get("relations", []))

            state["knowledge_graph"] = {
                "entities": entities,
                "relations": relations,
                "total_entities": len(entities),
                "total_relations": len(relations),
            }

            logger.info(f"[KG] 抽取了 {len(entities)} 个实体, {len(relations)} 个关系")
        except Exception as e:
            logger.warning(f"[KG] KG 服务调用失败，使用规则提取: {e}")
            return self._build_via_rules(state, papers)

        return state

    def _build_via_rules(self, state: PaperAgentState, papers: List[Paper]) -> PaperAgentState:
        """基于规则提取实体和关系"""
        entities = []
        relations = []

        for paper in papers[:15]:
            # 提取方法/模型名称（粗略启发式）
            title_words = paper.title.split()
            for word in title_words:
                if word[0].isupper() and len(word) > 2 and word not in {"The", "For", "And", "Using", "With", "From", "Based", "Via"}:
                    entities.append({
                        "name": word,
                        "type": "method_or_model",
                        "source_paper": paper.id,
                    })

            # 提取作者关联
            for author in paper.authors[:3]:
                entities.append({
                    "name": author,
                    "type": "author",
                    "source_paper": paper.id,
                })
                relations.append({
                    "subject": author,
                    "predicate": "authored",
                    "object": paper.id,
                })

        # 去重实体
        seen = set()
        unique_entities = []
        for e in entities:
            key = f"{e['name']}_{e['type']}"
            if key not in seen:
                seen.add(key)
                unique_entities.append(e)

        # 发现跨论文关联（共同作者、相似方法名）
        paper_ids = {p.id for p in papers}
        for paper in papers:
            for other in papers:
                if paper.id >= other.id:
                    continue
                # 共同作者
                common_authors = set(paper.authors) & set(other.authors)
                for author in common_authors:
                    relations.append({
                        "subject": paper.id,
                        "predicate": "shares_author",
                        "object": other.id,
                        "detail": author,
                    })

        state["knowledge_graph"] = {
            "entities": unique_entities,
            "relations": relations,
            "total_entities": len(unique_entities),
            "total_relations": len(relations),
        }

        logger.info(
            f"[KG] 规则提取: {len(unique_entities)} 个实体, {len(relations)} 个关系"
        )

        return state

    def query_related(self, state: PaperAgentState) -> PaperAgentState:
        """基于知识图谱发现关联论文"""
        kg_data = state.get("knowledge_graph", {})
        relations = kg_data.get("relations", [])

        if not relations:
            return state

        # 通过关系发现关联的论文对
        related_pairs = set()
        for rel in relations:
            if rel.get("predicate") == "shares_author":
                pair = tuple(sorted([rel["subject"], rel["object"]]))
                related_pairs.add(pair)

        state["knowledge_graph"]["related_paper_pairs"] = list(related_pairs)

        logger.info(f"[KG] 发现 {len(related_pairs)} 对关联论文")
        return state


def create_knowledge_graph_node(kg_service=None) -> KnowledgeGraphNode:
    """便捷函数：创建知识图谱节点"""
    return KnowledgeGraphNode(kg_service=kg_service)
