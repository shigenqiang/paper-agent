"""
知识图谱生成器 - 从论文中提取实体和关系

功能:
1. 论文实体提取（作者、方法、数据集、任务等）
2. 关系抽取（提出、使用、改进、对比等）
3. Neo4j存储集成
4. 图查询和分析
"""
import re
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .memory.neo4j_store import Neo4jGraphStore, GraphEntity, GraphRelation

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """实体类型"""
    PAPER = "Paper"
    AUTHOR = "Author"
    METHOD = "Method"
    DATASET = "Dataset"
    TASK = "Task"
    METRIC = "Metric"
    MODEL = "Model"
    CODE = "Code"
    RESULT = "Result"
    CONCLUSION = "Conclusion"


class RelationType(str, Enum):
    """关系类型"""
    PROPOSED_BY = "PROPOSED_BY"       # 方法由作者提出
    AUTHORED_BY = "AUTHORED_BY"       # 论文由作者完成
    USES = "USES"                      # 方法使用数据集/工具
    ACHIEVES = "ACHIEVES"              # 方法达成指标
    COMPARED_WITH = "COMPARED_WITH"   # 方法对比
    IMPROVES_ON = "IMPROVES_ON"       # 方法改进
    EXTENDS = "EXTENDS"                # 方法扩展
    CITES = "CITES"                   # 论文引用
    PERFORMS = "PERFORMS"             # 方法执行任务
    PUBLISHED_IN = "PUBLISHED_IN"     # 论文发表于


@dataclass
class ExtractedEntity:
    """提取的实体"""
    name: str
    type: EntityType
    properties: Dict[str, Any] = field(default_factory=dict)
    mentions: List[str] = field(default_factory=list)  # 原文提及


@dataclass
class ExtractedRelation:
    """提取的关系"""
    source: str  # 源实体名
    target: str  # 目标实体名
    relation: RelationType
    properties: Dict[str, Any] = field(default_factory=dict)
    context: str = ""  # 原文上下文


@dataclass
class KnowledgeGraphResult:
    """知识图谱生成结果"""
    success: bool
    paper_id: str
    entities: List[ExtractedEntity] = field(default_factory=list)
    relations: List[ExtractedRelation] = field(default_factory=list)
    error: Optional[str] = None


class EntityExtractor:
    """实体提取器"""

    # 实体模式定义
    ENTITY_PATTERNS = {
        EntityType.METHOD: [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:method|approach|technique|algorithm)\b',
            r'(?:proposed|presented|introduced)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*?)\s+network\b',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*?)\s+model\b',
        ],
        EntityType.DATASET: [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*?)\s+(?:dataset|corpus|benchmark)\b',
            r'\b([A-Z][a-z]+)\s+(?:dataset|corpus)\b',
            r'(?:on|using)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*?)\s+(?:dataset|bench)',
        ],
        EntityType.METRIC: [
            r'\b(accuracy|precision|recall|F1\s*score|AUC|ROC|BLEU|ROUGE|MAP|mRR)\b',
            r'\b(\d+\.?\d*)\s*%\s+(?:accuracy|precision|recall)\b',
        ],
        EntityType.TASK: [
            r'\b([a-z]+\s+(?:recognition|detection|segmentation|generation|classification|parsing|extraction|summarization))\b',
            r'(?:for|on)\s+([a-z]+\s+(?:task|problem))\b',
        ],
        EntityType.AUTHOR: [
            r'\b([A-Z][a-z]+(?:\s+[A-Z]\.?\s*[A-Z]?\.?)?)\s*,?\s*(?:and|et\s+al\.)\b',
            r'\b([A-Z][a-z]+)\s+(?:et\s+al|and)\b',
        ],
    }

    def extract_from_text(self, text: str, paper_title: str = "") -> List[ExtractedEntity]:
        """从文本提取实体"""
        entities = []
        seen = set()

        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    name = match.group(1) if match.groups() else match.group(0)
                    name = name.strip()

                    # 过滤太短的名字
                    if len(name) < 2:
                        continue

                    # 避免重复
                    key = (name.lower(), entity_type.value)
                    if key in seen:
                        continue
                    seen.add(key)

                    # 过滤常见词
                    if self._is_common_word(name):
                        continue

                    entity = ExtractedEntity(
                        name=name,
                        type=entity_type,
                        mentions=[match.group(0)]
                    )
                    entities.append(entity)

        # 论文标题作为Paper实体
        if paper_title:
            entities.append(ExtractedEntity(
                name=paper_title,
                type=EntityType.PAPER,
                mentions=[paper_title]
            ))

        return entities

    def _is_common_word(self, word: str) -> bool:
        """判断是否是常见词（非实体）"""
        common = {
            'this', 'that', 'these', 'those', 'paper', 'work', 'study',
            'article', 'section', 'chapter', 'figure', 'table', 'result',
            'experiment', 'method', 'approach', 'proposed', 'using', 'based'
        }
        return word.lower() in common


class RelationExtractor:
    """关系提取器"""

    RELATION_PATTERNS = {
        RelationType.PROPOSED_BY: [
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:method|approach)\s+(?:is\s+)?proposed', r'by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:is\s+)?(?:proposed|presented|introduced)'),
        ],
        RelationType.USES: [
            (r'(?:using|employ|adopt)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', r'(?:on|with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'),
            (r'trained\s+on\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'),
        ],
        RelationType.COMPARED_WITH: [
            (r'compared\s+(?:with|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', None),
            (r'outperforms?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', None),
            (r'better\s+than\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', None),
        ],
        RelationType.ACHIEVES: [
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+achieves?\s+(\d+\.?\d*)%?', None),
            (r'achieves?\s+(\d+\.?\d*)%?\s+(?:accuracy|performance)', None),
        ],
        RelationType.PERFORMS: [
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:for|on)\s+([a-z]+\s+tasks?)', None),
        ],
        RelationType.CITES: [
            (r'\[(\d+)\]', None),  # 引用编号
        ],
    }

    def extract_from_text(
        self,
        text: str,
        entities: List[ExtractedEntity],
        references: Optional[List[str]] = None
    ) -> List[ExtractedRelation]:
        """从文本提取关系"""
        relations = []
        seen = set()

        # 实体名称映射（用于匹配）
        entity_names = {e.name.lower(): e.name for e in entities}

        for relation_type, patterns in self.RELATION_PATTERNS.items():
            for pattern_group in patterns:
                if isinstance(pattern_group, tuple):
                    pattern = pattern_group[0]
                else:
                    pattern = pattern_group

                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # 提取涉及到的实体
                    source = None
                    target = None

                    if match.groups():
                        for group in match.groups():
                            if group:
                                group_lower = group.lower()
                                if group_lower in entity_names:
                                    if source is None:
                                        source = entity_names[group_lower]
                                    else:
                                        target = entity_names[group_lower]

                    # 对于CITES关系，使用引用编号
                    if relation_type == RelationType.CITES and match.groups():
                        ref_num = match.group(1)
                        if references and int(ref_num) <= len(references):
                            cited_paper = references[int(ref_num) - 1]
                            if cited_paper.raw_text:
                                target = cited_paper.raw_text[:50]  # 简化表示

                    if source and target:
                        key = (source.lower(), target.lower(), relation_type.value)
                        if key not in seen:
                            seen.add(key)
                            relations.append(ExtractedRelation(
                                source=source,
                                target=target,
                                relation=relation_type,
                                context=match.group(0)
                            ))

        return relations


class KnowledgeGraphGenerator:
    """
    知识图谱生成器

    从论文内容生成知识图谱，存储到Neo4j
    """

    def __init__(self, neo4j_store: Optional[Neo4jGraphStore] = None):
        self.neo4j = neo4j_store
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()

    async def generate_from_paper(
        self,
        paper_id: str,
        title: str,
        abstract: str,
        full_text: str = "",
        references: Optional[List[Any]] = None
    ) -> KnowledgeGraphResult:
        """
        从论文生成知识图谱

        Args:
            paper_id: 论文ID
            title: 论文标题
            abstract: 摘要
            full_text: 全文（可选）
            references: 参考文献列表

        Returns:
            KnowledgeGraphResult
        """
        try:
            # 合并文本
            all_text = f"{title}\n\n{abstract}\n\n{full_text}"

            # 提取实体
            entities = self.entity_extractor.extract_from_text(all_text, title)

            # 提取关系
            relations = self.relation_extractor.extract_from_text(
                all_text, entities, references
            )

            # 存储到Neo4j
            if self.neo4j:
                await self._store_to_neo4j(paper_id, entities, relations)

            return KnowledgeGraphResult(
                success=True,
                paper_id=paper_id,
                entities=entities,
                relations=relations
            )

        except Exception as e:
            logger.error(f"Knowledge graph generation failed: {e}")
            return KnowledgeGraphResult(
                success=False,
                paper_id=paper_id,
                error=str(e)
            )

    async def _store_to_neo4j(
        self,
        paper_id: str,
        entities: List[ExtractedEntity],
        relations: List[ExtractedRelation]
    ) -> None:
        """存储到Neo4j"""
        if not self.neo4j:
            return

        for entity in entities:
            await self.neo4j.add_entity(
                entity_id=f"{paper_id}_{entity.name}".replace(" ", "_"),
                entity_type=entity.type.value,
                properties={
                    "name": entity.name,
                    "paper_id": paper_id,
                    "mentions": entity.mentions,
                    **entity.properties
                }
            )

        for relation in relations:
            source_id = f"{paper_id}_{relation.source}".replace(" ", "_")
            target_id = f"{paper_id}_{relation.target}".replace(" ", "_")

            await self.neo4j.add_relation(
                source_id=source_id,
                target_id=target_id,
                relation_type=relation.relation.value,
                properties={
                    "context": relation.context,
                    **relation.properties
                }
            )

    async def query_graph(
        self,
        entity_name: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """查询图谱"""
        if not self.neo4j:
            return {}

        # 查询直接关联的实体
        query = f"""
        MATCH (e:Entity {{name: $name}})-[r]-(other)
        RETURN other.name AS name, other.entity_type AS type, type(r) AS relation
        LIMIT 50
        """

        with self.neo4j._get_driver().session() as session:
            result = session.run(query, name=entity_name)
            return {"results": [dict(record) for record in result]}

    async def find_shortest_path(
        self,
        entity1: str,
        entity2: str
    ) -> List[Dict[str, Any]]:
        """找两个实体之间的最短路径"""
        if not self.neo4j:
            return []

        query = f"""
        MATCH path = shortestPath((e1:Entity {{name: $name1}})-[*]-(e2:Entity {{name: $name2}}))
        RETURN path
        LIMIT 1
        """

        with self.neo4j._get_driver().session() as session:
            result = session.run(query, name1=entity1, name2=entity2)
            return [dict(record) for record in result]

    async def get_paper_graph(self, paper_id: str) -> Dict[str, Any]:
        """获取某篇论文的完整子图"""
        if not self.neo4j:
            return {}

        query = f"""
        MATCH (e:Entity {{paper_id: $paper_id}})-[r]-(other)
        RETURN e, other, type(r) AS relation
        """

        with self.neo4j._get_driver().session() as session:
            result = session.run(query, paper_id=paper_id)
            return {"entities": [dict(record["e"]) for record in result],
                    "relations": [dict(record) for record in result]}


# 便捷函数
async def generate_knowledge_graph(
    paper_id: str,
    title: str,
    abstract: str,
    full_text: str = "",
    neo4j_uri: str = "bolt://localhost:7687",
    neo4j_password: str = None
) -> KnowledgeGraphResult:
    """从论文生成知识图谱"""
    store = Neo4jGraphStore(uri=neo4j_uri, password=neo4j_password)
    generator = KnowledgeGraphGenerator(neo4j_store=store)
    return await generator.generate_from_paper(paper_id, title, abstract, full_text)


def get_tool_spec():
    """获取工具规格"""
    from .tools.tool_spec import ToolSpec, ParameterSpec, ParameterType

    return ToolSpec(
        name="generate_knowledge_graph",
        description="从论文内容生成知识图谱，提取实体和关系",
        parameters=[
            ParameterSpec(
                name="paper_id",
                description="论文ID",
                type=ParameterType.STRING,
                required=True
            ),
            ParameterSpec(
                name="title",
                description="论文标题",
                type=ParameterType.STRING,
                required=True
            ),
            ParameterSpec(
                name="abstract",
                description="论文摘要",
                type=ParameterType.STRING,
                required=True
            ),
            ParameterSpec(
                name="full_text",
                description="论文全文（可选）",
                type=ParameterType.STRING,
                required=False
            )
        ],
        handler=generate_knowledge_graph,
        category="knowledge"
    )
