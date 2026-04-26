"""
研究空白分析与知识图谱集成模块

功能：
- 结合知识图谱实体关系进行更精准的空白识别
- 利用图结构发现间接关联的研究空白
- 基于知识图谱路径分析的研究机会评估
"""
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

from .research_gap import (
    ResearchGapAnalyzer,
    ResearchGap,
    GapAnalysisResult,
    GapType,
    OpportunityScore
)
from .knowledge_graph import (
    KnowledgeGraphGenerator,
    EntityType,
    RelationType,
    ExtractedEntity,
    ExtractedRelation
)

logger = logging.getLogger(__name__)


class GapAwareKnowledgeGraphGenerator(KnowledgeGraphGenerator):
    """
    支持研究空白分析的知识图谱生成器

    在生成图谱时考虑研究空白因素
    """

    async def generate_with_gap_analysis(
        self,
        paper_id: str,
        title: str,
        abstract: str,
        full_text: str = "",
        references: Optional[List[Any]] = None
    ) -> Tuple[GapAnalysisResult, Dict[str, Any]]:
        """
        生成知识图谱并进行空白分析

        Returns:
            Tuple[GapAnalysisResult, Dict]: (空白分析结果, 图谱数据)
        """
        from .research_gap import ResearchGapAnalyzer

        # 1. 生成基础图谱
        kg_result = await self.generate_from_paper(
            paper_id, title, abstract, full_text, references
        )

        if not kg_result.success:
            return GapAnalysisResult(
                topic=title,
                total_papers_analyzed=1,
                gaps_identified=[],
                gap_categories={},
                most_promising_gap=None,
                research_recommendations=["知识图谱生成失败"],
                confidence_level=0.0
            ), {}

        # 2. 将图谱实体转换为论文分析格式
        paper_analyses = self._entities_to_paper_analyses(kg_result.entities)

        # 3. 进行研究空白分析
        gap_analyzer = ResearchGapAnalyzer()
        gap_result = await gap_analyzer.analyze(title, paper_analyses)

        # 4. 利用图谱关系增强空白分析
        gap_result = await self._enhance_gaps_with_graph(
            gap_result, kg_result.entities, kg_result.relations
        )

        return gap_result, {
            "entities": kg_result.entities,
            "relations": kg_result.relations
        }

    def _entities_to_paper_analyses(
        self,
        entities: List[ExtractedEntity]
    ) -> List[Dict[str, Any]]:
        """将实体转换为论文分析格式"""
        analyses = []

        # 按论文分组
        papers: Dict[str, List[ExtractedEntity]] = {}
        for entity in entities:
            if entity.type == EntityType.PAPER:
                papers[entity.name] = []

        # 收集每篇论文的实体
        for entity in entities:
            if entity.type == EntityType.PAPER and entity.name in papers:
                papers[entity.name].append(entity)

        # 转换为分析格式
        for paper_name, paper_entities in papers.items():
            analysis = {"title": paper_name}

            methods = [e.name for e in paper_entities if e.type == EntityType.METHOD]
            datasets = [e.name for e in paper_entities if e.type == EntityType.DATASET]

            if methods:
                analysis["key_methodology"] = ", ".join(methods)
            if datasets:
                analysis["datasets"] = datasets

            analyses.append(analysis)

        return analyses if analyses else [{"title": "Extracted entities"}]

    async def _enhance_gaps_with_graph(
        self,
        gap_result: GapAnalysisResult,
        entities: List[ExtractedEntity],
        relations: List[ExtractedRelation]
    ) -> GapAnalysisResult:
        """利用图谱关系增强空白分析"""
        if not entities:
            return gap_result

        # 分析实体的连通性
        connected_entities = self._analyze_connectivity(entities, relations)

        # 分析方法之间的关系
        method_relations = self._analyze_method_relations(relations)

        # 增强每个空白的评分
        enhanced_gaps = []
        for gap in gap_result.gaps_identified:
            gap = self._enhance_single_gap(gap, connected_entities, method_relations)
            enhanced_gaps.append(gap)

        gap_result.gaps_identified = enhanced_gaps

        # 添加图谱洞察到建议
        graph_insights = self._generate_graph_insights(
            connected_entities, method_relations, entities
        )
        gap_result.research_recommendations.extend(graph_insights)

        return gap_result

    def _analyze_connectivity(
        self,
        entities: List[ExtractedEntity],
        relations: List[ExtractedRelation]
    ) -> Dict[str, Set[str]]:
        """分析实体连通性"""
        connectivity: Dict[str, Set[str]] = {}

        for entity in entities:
            connectivity[entity.name] = set()

        for relation in relations:
            if relation.source in connectivity:
                connectivity[relation.source].add(relation.target)
            if relation.target in connectivity:
                connectivity[relation.target].add(relation.source)

        return connectivity

    def _analyze_method_relations(
        self,
        relations: List[ExtractedRelation]
    ) -> Dict[str, List[str]]:
        """分析方法间的关系"""
        method_relations: Dict[str, List[str]] = {
            "proposes": [],
            "extends": [],
            "compares": [],
            "improves": []
        }

        for relation in relations:
            if relation.relation == RelationType.PROPOSED_BY:
                method_relations["proposes"].append(relation.source)
            elif relation.relation == RelationType.EXTENDS:
                method_relations["extends"].append(f"{relation.source}->{relation.target}")
            elif relation.relation == RelationType.COMPARED_WITH:
                method_relations["compares"].append(f"{relation.source} vs {relation.target}")
            elif relation.relation == RelationType.IMPROVES_ON:
                method_relations["improves"].append(f"{relation.source}->{relation.target}")

        return method_relations

    def _enhance_single_gap(
        self,
        gap: ResearchGap,
        connectivity: Dict[str, Set[str]],
        method_relations: Dict[str, List[str]]
    ) -> ResearchGap:
        """增强单个空白的评分"""
        # 检查空白描述中的方法是否与其他方法有关联
        gap_text_lower = gap.description.lower()

        # 如果提到某个方法但该方法在图中没有太多连接，可能有机会
        for method_list_key in ["proposes", "extends"]:
            for method in method_relations.get(method_list_key, []):
                if method.lower() in gap_text_lower:
                    # 该方法有明确的提出/扩展关系，增加可行性评分
                    if gap.feasibility < 7.0:
                        gap.feasibility = min(10.0, gap.feasibility + 0.5)

        # 检查创新性 - 如果是新的方法组合，可能更有创新性
        if len(method_relations.get("compares", [])) > 3:
            if gap.gap_type == GapType.COMPARATIVE:
                gap.novelty = min(10.0, gap.novelty + 1.0)

        return gap

    def _generate_graph_insights(
        self,
        connectivity: Dict[str, Set[str]],
        method_relations: Dict[str, List[str]],
        entities: List[ExtractedEntity]
    ) -> List[str]:
        """从图谱分析中生成洞察"""
        insights = []

        # 分析孤立实体（可能的研究空白）
        isolated = [name for name, connections in connectivity.items() if len(connections) == 0]
        if isolated:
            insights.append(f"发现{len(isolated)}个孤立实体，可能代表未被充分研究的方向")

        # 分析方法密度
        method_count = sum(1 for e in entities if e.type == EntityType.METHOD)
        relation_count = sum(len(r) for r in method_relations.values())

        if method_count > 0 and relation_count / method_count < 0.5:
            insights.append("方法间的关联研究较少，存在方法对比空白")

        # 分析数据集覆盖
        datasets = [e.name for e in entities if e.type == EntityType.DATASET]
        if len(datasets) < 3:
            insights.append("数据集覆盖有限，可能存在跨数据集泛化的研究机会")

        return insights


class GraphBasedGapDiscovery:
    """
    基于图的研究空白发现

    利用知识图谱结构发现传统方法难以识别的研究空白
    """

    def __init__(self, kg_generator: KnowledgeGraphGenerator):
        self.kg = kg_generator

    async def discover_gaps_from_graph(
        self,
        topic: str,
        min_centrality: float = 0.1
    ) -> List[ResearchGap]:
        """
        从知识图谱发现研究空白

        Args:
            topic: 研究主题
            min_centrality: 最小中心性阈值（低于此值的实体可能是空白区域）
        """
        gaps = []

        try:
            # 1. 获取该主题相关的所有实体
            related_entities = await self._get_related_entities(topic)

            if not related_entities:
                return gaps

            # 2. 计算实体中心性
            centralities = self._calculate_centralities(related_entities)

            # 3. 识别低中心性区域（可能是研究空白）
            gaps.extend(self._discover_low_centrality_gaps(
                related_entities, centralities, topic
            ))

            # 4. 识别缺失的关系类型
            gaps.extend(await self._discover_missing_relation_gaps(
                related_entities, topic
            ))

            # 5. 识别方法孤岛
            gaps.extend(self._discover_method_islands(related_entities, topic))

        except Exception as e:
            logger.error(f"Graph-based gap discovery failed: {e}")

        return gaps

    async def _get_related_entities(self, topic: str) -> List[Dict[str, Any]]:
        """获取与主题相关的实体"""
        try:
            result = await self.kg.query_graph(topic, depth=2)
            return result.get("results", [])
        except Exception:
            return []

    def _calculate_centralities(
        self,
        entities: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """计算实体中心性"""
        # 简化的中心性计算
        if not entities:
            return {}

        counts = {}
        for entity in entities:
            name = entity.get("name", "")
            if name:
                counts[name] = counts.get(name, 0) + 1

        max_count = max(counts.values()) if counts else 1
        return {name: count / max_count for name, count in counts.items()}

    def _discover_low_centrality_gaps(
        self,
        entities: List[Dict[str, Any]],
        centralities: Dict[str, float],
        topic: str
    ) -> List[ResearchGap]:
        """发现低中心性区域（研究空白）"""
        gaps = []

        low_centrality = [
            (name, centrality)
            for name, centrality in centralities.items()
            if centrality < 0.2
        ]

        for name, centrality in low_centrality[:5]:
            gaps.append(ResearchGap(
                gap_type=GapType.METHODOLOGICAL,
                description=f"'{name}'与其他研究关联较少，可能是未被充分探索的方向",
                evidence=[f"中心性仅为{centrality:.2f}"],
                potential_direction=f"探索{name}与其他方法的结合",
                opportunity_score=OpportunityScore.MEDIUM,
                feasibility=5.0,
                novelty=6.0,
                impact_potential=5.0,
                required_resources=["领域专家咨询"],
                related_methods=[name],
                risk_factors=["研究基础薄弱"]
            ))

        return gaps

    async def _discover_missing_relation_gaps(
        self,
        entities: List[Dict[str, Any]],
        topic: str
    ) -> List[ResearchGap]:
        """发现缺失关系类型的空白"""
        gaps = []

        # 检查是否有方法但没有比较关系
        methods = [e.get("name") for e in entities if e.get("type") == "Method"]

        if len(methods) >= 3:
            # 存在多个方法但可能缺乏系统对比
            gaps.append(ResearchGap(
                gap_type=GapType.COMPARATIVE,
                description=f"该领域存在{len(methods)}种方法，但可能缺乏系统对比研究",
                evidence=["存在多种方法但关系不明确"],
                potential_direction="开展多方法系统对比实验",
                opportunity_score=OpportunityScore.HIGH,
                feasibility=7.0,
                novelty=5.0,
                impact_potential=6.0,
                required_resources=["对比实验设计"],
                related_methods=methods[:3],
                risk_factors=[]
            ))

        return gaps

    def _discover_method_islands(
        self,
        entities: List[Dict[str, Any]],
        topic: str
    ) -> List[ResearchGap]:
        """发现方法孤岛（孤立的方法实体）"""
        gaps = []

        # 识别只连接到一个其他实体的方法
        method_entities = [e for e in entities if e.get("type") == "Method"]

        island_methods = []
        for entity in method_entities:
            # 这里需要更复杂的图分析，简化处理
            if len(entities) > 1:
                island_methods.append(entity.get("name", ""))

        if island_methods:
            gaps.append(ResearchGap(
                gap_type=GapType.APPLICATION,
                description=f"发现{len(island_methods)}个相对孤立的方法，可能存在应用空白",
                evidence=["这些方法与其他研究关联较少"],
                potential_direction="探索这些方法的新应用场景",
                opportunity_score=OpportunityScore.MEDIUM,
                feasibility=6.0,
                novelty=5.0,
                impact_potential=5.0,
                required_resources=["应用场景调研"],
                related_methods=island_methods[:3],
                risk_factors=["应用前景不确定"]
            ))

        return gaps


# 便捷函数
async def integrated_gap_analysis(
    topic: str,
    paper_analyses: List[Dict[str, Any]],
    entities: List[ExtractedEntity] = None,
    relations: List[ExtractedRelation] = None,
    kg_generator: KnowledgeGraphGenerator = None
) -> GapAnalysisResult:
    """
    集成的研究空白分析

    结合论文分析和知识图谱进行更全面的空白识别
    """
    # 1. 基础研究空白分析
    analyzer = ResearchGapAnalyzer()
    result = await analyzer.analyze(topic, paper_analyses)

    # 2. 如果有知识图谱数据，增强分析
    if entities and relations and kg_generator:
        kg_enhanced = GapAwareKnowledgeGraphGenerator(neo4j_store=kg_generator.neo4j)
        kg_enhanced._enhance_gaps_with_graph(result, entities, relations)

    return result