"""大模型知识抽取器"""
from typing import List, Dict, Any, Optional
import json
import re
import logging

from src.knowledge.extraction.base_extractor import (
    BaseExtractor,
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult
)

logger = logging.getLogger(__name__)


class LLMExtractor(BaseExtractor):
    """基于大语言模型的知识抽取器"""

    def __init__(
        self,
        llm,
        confidence_threshold: float = 0.5,
        max_retries: int = 3
    ):
        super().__init__(confidence_threshold)
        self.llm = llm
        self.max_retries = max_retries

    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        domain: str = "general",
        **kwargs
    ) -> List[ExtractedEntity]:
        """
        使用LLM抽取实体

        Args:
            text: 输入文本
            entity_types: 要抽取的实体类型列表，如["人名", "机构", "方法", "任务"]
            domain: 领域
        """
        if entity_types is None:
            entity_types = ["概念", "方法", "任务", "数据集", "指标"]

        prompt = self._build_entity_extraction_prompt(text, entity_types, domain)

        try:
            response = await self._invoke_llm_with_retry(prompt)
            entities = self._parse_entity_response(response, entity_types)

            logger.info(f"Extracted {len(entities)} entities using LLM")
            return entities

        except Exception as e:
            logger.error(f"LLM entity extraction failed: {e}")
            return []

    async def extract_relations(
        self,
        text: str,
        entities: List[ExtractedEntity],
        relation_types: Optional[List[str]] = None,
        **kwargs
    ) -> List[ExtractedRelation]:
        """
        使用LLM抽取关系

        Args:
            text: 输入文本
            entities: 已抽取的实体列表
            relation_types: 要抽取的关系类型列表
        """
        if relation_types is None:
            relation_types = ["包含", "属于", "解决", "使用", "改进"]

        # 构建实体文本
        entity_texts = [
            f"{e.id}: {e.text} ({e.type})"
            for e in entities
        ]

        prompt = self._build_relation_extraction_prompt(
            text,
            entity_texts,
            relation_types
        )

        try:
            response = await self._invoke_llm_with_retry(prompt)
            relations = self._parse_relation_response(response, entities)

            logger.info(f"Extracted {len(relations)} relations using LLM")
            return relations

        except Exception as e:
            logger.error(f"LLM relation extraction failed: {e}")
            return []

    def _build_entity_extraction_prompt(
        self,
        text: str,
        entity_types: List[str],
        domain: str
    ) -> str:
        """构建实体抽取提示词"""
        return f"""请从以下文本中抽取实体信息。

领域: {domain}

需要抽取的实体类型:
{', '.join(entity_types)}

文本:
{text}

请以JSON格式返回结果，格式如下:
{{
  "entities": [
    {{
      "text": "实体文本",
      "type": "实体类型",
      "confidence": 0.9,
      "description": "实体的简要描述"
    }}
  ]
}}

注意:
1. 只抽取明确提到的实体
2. confidence是0-1之间的浮点数
3. 确保JSON格式正确
"""

    def _build_relation_extraction_prompt(
        self,
        text: str,
        entity_texts: List[str],
        relation_types: List[str]
    ) -> str:
        """构建关系抽取提示词"""
        return f"""请从以下文本中抽取实体间的关系。

实体列表:
{chr(10).join(entity_texts)}

需要抽取的关系类型:
{', '.join(relation_types)}

文本:
{text}

请以JSON格式返回结果，格式如下:
{{
  "relations": [
    {{
      "source": "源实体ID",
      "target": "目标实体ID",
      "type": "关系类型",
      "confidence": 0.9,
      "description": "关系的简要描述"
    }}
  ]
}}

注意:
1. 只抽取明确存在的关系
2. source和target必须是上面列出的实体ID
3. confidence是0-1之间的浮点数
4. 确保JSON格式正确
"""

    async def _invoke_llm_with_retry(self, prompt: str) -> str:
        """带重试的LLM调用"""
        for attempt in range(self.max_retries):
            try:
                response = await self.llm.ainvoke({"messages": prompt})
                return response["messages"][-1].content
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"LLM invocation failed (attempt {attempt + 1}), retrying...")
                continue

    def _parse_entity_response(
        self,
        response: str,
        entity_types: List[str]
    ) -> List[ExtractedEntity]:
        """解析实体抽取响应"""
        entities = []

        try:
            # 尝试提取JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)

                for item in data.get("entities", []):
                    entity_id = self.create_entity_id(
                        item.get("text", ""),
                        item.get("type", "unknown")
                    )

                    entity = ExtractedEntity(
                        id=entity_id,
                        text=item.get("text", ""),
                        type=item.get("type", "unknown"),
                        confidence=float(item.get("confidence", 0.5)),
                        properties={
                            "description": item.get("description", "")
                        }
                    )

                    if entity.type in entity_types:
                        entities.append(entity)

        except Exception as e:
            logger.error(f"Failed to parse entity response: {e}")

        return entities

    def _parse_relation_response(
        self,
        response: str,
        entities: List[ExtractedEntity]
    ) -> List[ExtractedRelation]:
        """解析关系抽取响应"""
        relations = []

        # 创建实体ID到实体的映射
        entity_map = {e.id: e for e in entities}

        try:
            # 尝试提取JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)

                for item in data.get("relations", []):
                    source_id = item.get("source", "")
                    target_id = item.get("target", "")

                    # 验证实体是否存在
                    if source_id in entity_map and target_id in entity_map:
                        relation_id = self.create_relation_id(
                            source_id,
                            target_id,
                            item.get("type", "unknown")
                        )

                        relation = ExtractedRelation(
                            id=relation_id,
                            source_id=source_id,
                            target_id=target_id,
                            relation_type=item.get("type", "unknown"),
                            confidence=float(item.get("confidence", 0.5)),
                            properties={
                                "description": item.get("description", "")
                            }
                        )

                        relations.append(relation)

        except Exception as e:
            logger.error(f"Failed to parse relation response: {e}")

        return relations


class StructuredLLMExtractor(LLMExtractor):
    """结构化的大模型抽取器 - 按照概念图谱结构抽取"""

    def __init__(
        self,
        llm,
        concept_graph,
        confidence_threshold: float = 0.5
    ):
        super().__init__(llm, confidence_threshold)
        self.concept_graph = concept_graph

    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        **kwargs
    ) -> List[ExtractedEntity]:
        """
        按照概念图谱结构抽取实体
        """
        if entity_types is None:
            # 从概念图谱获取概念类型
            entity_types = self._get_concept_types()

        prompt = self._build_structured_extraction_prompt(text, entity_types)

        try:
            response = await self._invoke_llm_with_retry(prompt)
            entities = self._parse_structured_entity_response(response)

            logger.info(f"Extracted {len(entities)} entities using structured LLM")
            return entities

        except Exception as e:
            logger.error(f"Structured LLM entity extraction failed: {e}")
            return []

    def _get_concept_types(self) -> List[str]:
        """从概念图谱获取概念类型"""
        if self.concept_graph and hasattr(self.concept_graph, 'get_all_types'):
            return self.concept_graph.get_all_types()
        return ["概念", "方法", "任务", "数据集", "指标"]

    def _build_structured_extraction_prompt(
        self,
        text: str,
        entity_types: List[str]
    ) -> str:
        """构建结构化抽取提示词"""
        type_descriptions = "\n".join([
            f"- {t}: 请从文本中识别{t}"
            for t in entity_types
        ])

        return f"""请按照以下结构从文本中抽取实体信息。

实体类型:
{type_descriptions}

文本:
{text}

请以JSON格式返回结果，格式如下:
{{
  "entities": [
    {{
      "text": "实体文本",
      "type": "实体类型",
      "confidence": 0.9,
      "definition": "实体的定义或说明",
      "properties": {{
        "key": "value"
      }}
    }}
  ]
}}

注意:
1. 确保抽取的实体类型在上述列表中
2. definition字段应包含实体的简要定义
3. properties可以包含额外的属性
"""

    def _parse_structured_entity_response(self, response: str) -> List[ExtractedEntity]:
        """解析结构化实体抽取响应"""
        entities = []

        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)

                for item in data.get("entities", []):
                    entity_id = self.create_entity_id(
                        item.get("text", ""),
                        item.get("type", "unknown")
                    )

                    entity = ExtractedEntity(
                        id=entity_id,
                        text=item.get("text", ""),
                        type=item.get("type", "unknown"),
                        confidence=float(item.get("confidence", 0.5)),
                        properties={
                            "definition": item.get("definition", ""),
                            **item.get("properties", {})
                        }
                    )

                    entities.append(entity)

        except Exception as e:
            logger.error(f"Failed to parse structured entity response: {e}")

        return entities
