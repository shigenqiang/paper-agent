"""
知识图谱模块测试
"""
import pytest
from src.agents_v2.knowledge_graph import (
    KnowledgeGraphGenerator, EntityExtractor, RelationExtractor,
    EntityType, RelationType, ExtractedEntity, ExtractedRelation,
    KnowledgeGraphResult
)


class TestEntityType:
    """实体类型枚举测试"""

    def test_entity_types_exist(self):
        assert EntityType.METHOD is not None
        assert EntityType.DATASET is not None
        assert EntityType.TASK is not None
        assert EntityType.METRIC is not None
        assert EntityType.AUTHOR is not None
        assert EntityType.MODEL is not None


class TestRelationType:
    """关系类型枚举测试"""

    def test_relation_types_exist(self):
        assert RelationType.PROPOSED_BY is not None
        assert RelationType.USES is not None
        assert RelationType.CITES is not None
        assert RelationType.COMPARED_WITH is not None


class TestExtractedEntity:
    """提取实体测试"""

    def test_create_entity(self):
        entity = ExtractedEntity(
            name="Transformer",
            type=EntityType.MODEL,
            properties={"year": 2017},
            mentions=["Transformer model"]
        )
        assert entity.name == "Transformer"
        assert entity.type == EntityType.MODEL
        assert entity.properties["year"] == 2017
        assert len(entity.mentions) == 1


class TestExtractedRelation:
    """提取关系测试"""

    def test_create_relation(self):
        relation = ExtractedRelation(
            source="ModelA",
            target="DatasetB",
            relation=RelationType.USES,
            context="experiments on DatasetB"
        )
        assert relation.source == "ModelA"
        assert relation.target == "DatasetB"
        assert relation.relation == RelationType.USES
        assert relation.context == "experiments on DatasetB"


class TestKnowledgeGraphResult:
    """知识图谱结果测试"""

    def test_successful_result(self):
        entities = [ExtractedEntity("Test", EntityType.METHOD, mentions=[])]
        result = KnowledgeGraphResult(
            success=True,
            paper_id="paper_1",
            entities=entities,
            relations=[]
        )
        assert result.success is True
        assert result.paper_id == "paper_1"
        assert len(result.entities) == 1

    def test_failed_result(self):
        result = KnowledgeGraphResult(
            success=False,
            paper_id="paper_1",
            error="Extraction failed"
        )
        assert result.success is False
        assert result.error == "Extraction failed"


class TestEntityExtractor:
    """实体提取器测试"""

    def setup_method(self):
        self.extractor = EntityExtractor()

    def test_extract_method_entities(self):
        text = "We propose a new Transformer model that uses self-attention."
        entities = self.extractor.extract_from_text(text, "Test Paper")
        assert len(entities) > 0

    def test_extract_metric_entities(self):
        text = "Our method achieves 95% accuracy on the benchmark."
        entities = self.extractor.extract_from_text(text, "Test Paper")
        metric_entities = [e for e in entities if e.type == EntityType.METRIC]
        assert len(metric_entities) >= 1

    def test_extract_task_entities(self):
        text = "Applied to image classification and object detection tasks."
        entities = self.extractor.extract_from_text(text, "Test Paper")
        task_entities = [e for e in entities if e.type == EntityType.TASK]
        assert len(task_entities) >= 1

    def test_extract_dataset_entities(self):
        text = "Experiments on ImageNet and COCO dataset show improvement."
        entities = self.extractor.extract_from_text(text, "Test Paper")
        dataset_entities = [e for e in entities if e.type == EntityType.DATASET]
        assert len(dataset_entities) >= 1

    def test_empty_text(self):
        entities = self.extractor.extract_from_text("", "Empty Paper")
        assert isinstance(entities, list)


class TestRelationExtractor:
    """关系提取器测试"""

    def setup_method(self):
        self.extractor = RelationExtractor()

    def test_extract_proposes_relation(self):
        text = "We propose a new method called X."
        entities = [ExtractedEntity("X", EntityType.METHOD, mentions=["X"])]
        relations = self.extractor.extract_from_text(text, entities, None)
        # Relation extractor looks for PROPOSED_BY relations
        assert isinstance(relations, list)

    def test_extract_uses_relation(self):
        text = "Our method uses the Adam optimizer."
        entities = [
            ExtractedEntity("Adam", EntityType.METHOD, mentions=["Adam"]),
            ExtractedEntity("OurMethod", EntityType.METHOD, mentions=["method"])
        ]
        relations = self.extractor.extract_from_text(text, entities, None)
        assert isinstance(relations, list)

    def test_empty_text(self):
        relations = self.extractor.extract_from_text("", [], None)
        assert len(relations) == 0

    def test_empty_entities(self):
        text = "Some text without known entities."
        relations = self.extractor.extract_from_text(text, [], None)
        assert isinstance(relations, list)


class TestKnowledgeGraphGenerator:
    """知识图谱生成器测试"""

    def setup_method(self):
        self.generator = KnowledgeGraphGenerator()

    @pytest.mark.asyncio
    async def test_generate_from_paper(self):
        result = await self.generator.generate_from_paper(
            paper_id="test_paper",
            title="Test Paper on Machine Learning",
            abstract="This paper proposes a new method.",
            full_text="Experiments on ImageNet dataset show results."
        )
        assert result.success is True
        assert result.paper_id == "test_paper"
        assert isinstance(result.entities, list)
        assert isinstance(result.relations, list)

    @pytest.mark.asyncio
    async def test_generate_with_minimal_input(self):
        result = await self.generator.generate_from_paper(
            paper_id="minimal_paper",
            title="Minimal Paper",
            abstract="A paper.",
            full_text=""
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_generate_handles_exception(self):
        # Even with problematic input, should not crash
        result = await self.generator.generate_from_paper(
            paper_id="error_paper",
            title="Error Paper",
            abstract="Test",
            full_text="Test"
        )
        assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
