"""
知识图谱统一服务API模块

功能:
1. 统一入口封装所有知识图谱功能
2. 简化的API接口
3. 错误处理和日志
4. 配置管理
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """服务配置"""
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    qdrant_url: str = "localhost:6333"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    vector_store_type: str = "memory"  # "memory" or "qdrant"
    enable_graphrag: bool = True
    enable_communities: bool = True


class KnowledgeGraphService:
    """
    知识图谱统一服务

    整合所有知识图谱功能，提供统一的API接口
    """

    def __init__(self, config: Optional[ServiceConfig] = None):
        """
        Args:
            config: 服务配置
        """
        self.config = config or ServiceConfig()
        self._initialized = False

        # 组件
        self._neo4j_driver = None
        self._vector_store = None
        self._embedding_model = None
        self._schema_manager = None

        # 子系统
        self._community_detector = None
        self._hybrid_retriever = None
        self._batch_importer = None
        self._graphrag_qa = None

    async def initialize(self) -> bool:
        """
        初始化服务

        Returns:
            是否成功
        """
        try:
            logger.info("Initializing Knowledge Graph Service...")

            # 初始化向量存储
            from .kg_vector_store import create_vector_store
            self._vector_store = create_vector_store(
                store_type=self.config.vector_store_type,
                dimension=self.config.embedding_dim
            )

            # 初始化Schema管理器
            from .kg_schema import SchemaManager
            self._schema_manager = SchemaManager()

            # 初始化社区检测
            from .kg_community import LouvainDetector
            self._community_detector = LouvainDetector()

            # 初始化混合检索
            from .kg_hybrid_retriever import HybridRetriever
            self._hybrid_retriever = HybridRetriever()

            # 初始化GraphRAG
            if self.config.enable_graphrag:
                from .kg_graphrag import create_graphrag_qa
                self._graphrag_qa = create_graphrag_qa()

            self._initialized = True
            logger.info("Knowledge Graph Service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Initialization error: {e}")
            return False

    # ==================== 实体操作 ====================

    def add_entity(
        self,
        entity_id: str,
        entity_type: str,
        properties: Dict[str, Any],
        embedding: Optional[List[float]] = None
    ) -> bool:
        """
        添加实体

        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            properties: 属性字典
            embedding: 向量嵌入

        Returns:
            是否成功
        """
        try:
            # 添加到向量存储
            if embedding and self._vector_store:
                self._vector_store.upsert(
                    id=entity_id,
                    vector=embedding,
                    payload={"type": entity_type, **properties}
                )

            # 添加到混合检索
            if self._hybrid_retriever and embedding:
                self._hybrid_retriever.add_entity(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    embedding=embedding,
                    properties=properties
                )

            return True

        except Exception as e:
            logger.error(f"Add entity error: {e}")
            return False

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加关系

        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            relation_type: 关系类型
            properties: 属性

        Returns:
            是否成功
        """
        try:
            if self._hybrid_retriever:
                self._hybrid_retriever.add_relation(
                    source_id=source_id,
                    target_id=target_id,
                    relation=relation_type
                )
            return True

        except Exception as e:
            logger.error(f"Add relation error: {e}")
            return False

    def delete_entity(self, entity_id: str) -> bool:
        """删除实体"""
        try:
            if self._vector_store:
                self._vector_store.delete(entity_id)
            return True

        except Exception as e:
            logger.error(f"Delete entity error: {e}")
            return False

    # ==================== 检索操作 ====================

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        混合检索

        Args:
            query_embedding: 查询向量
            top_k: 返回数量
            entity_type: 实体类型过滤

        Returns:
            检索结果列表
        """
        try:
            filter_payload = {"type": entity_type} if entity_type else None

            if self._vector_store:
                results = self._vector_store.search(
                    query_vector=query_embedding,
                    top_k=top_k,
                    filter_payload=filter_payload
                )
                return [
                    {
                        "entity_id": r.id,
                        "score": r.score,
                        "payload": r.payload
                    }
                    for r in results
                ]

            return []

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def retrieve(
        self,
        query_embedding: List[float],
        initial_entities: Optional[List[str]] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        混合检索 (向量+图)

        Args:
            query_embedding: 查询向量
            initial_entities: 初始实体列表
            top_k: 返回数量

        Returns:
            检索结果
        """
        try:
            if not self._hybrid_retriever:
                return []

            results = self._hybrid_retriever.retrieve(
                query_embedding=query_embedding,
                initial_entities=initial_entities,
                top_k=top_k
            )

            return [
                {
                    "entity_id": r.entity_id,
                    "entity_type": r.entity_type,
                    "score": r.score,
                    "method": r.method.value if hasattr(r.method, 'value') else r.method
                }
                for r in results
            ]

        except Exception as e:
            logger.error(f"Retrieve error: {e}")
            return []

    # ==================== 社区检测 ====================

    def detect_communities(
        self,
        algorithm: str = "louvain"
    ) -> List[Dict[str, Any]]:
        """
        检测社区

        Args:
            algorithm: 算法名称

        Returns:
            社区列表
        """
        try:
            if not self._hybrid_retriever:
                return []

            # 构建边列表
            edges = []
            for edge in self._hybrid_retriever.graph_traverser._edges:
                edges.append((edge[0], edge[1]))

            from .kg_community import detect_communities
            communities = detect_communities(edges, algorithm=algorithm)

            return [
                {
                    "community_id": i,
                    "members": list(c.members)
                }
                for i, c in enumerate(communities)
            ]

        except Exception as e:
            logger.error(f"Detect communities error: {e}")
            return []

    # ==================== GraphRAG ====================

    def query(
        self,
        question: str,
        query_embedding: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        GraphRAG问答

        Args:
            question: 问题
            query_embedding: 查询向量

        Returns:
            回答上下文
        """
        try:
            if not self._graphrag_qa:
                return {"error": "GraphRAG not enabled"}

            context = self._graphrag_qa.query(question, query_embedding)

            return {
                "query_type": context.query.query_type.value,
                "context_text": context.to_prompt_context(),
                "retrieved_items": [
                    {
                        "entity_id": item.entity_id,
                        "content": item.content,
                        "score": item.score
                    }
                    for item in context.retrieved_items
                ]
            }

        except Exception as e:
            logger.error(f"Query error: {e}")
            return {"error": str(e)}

    # ==================== 批量操作 ====================

    def batch_import(
        self,
        entities: List[Tuple[str, str, Dict]],
        relations: List[Tuple[str, str, str, Dict]]
    ) -> Dict[str, Any]:
        """
        批量导入

        Args:
            entities: [(entity_id, entity_type, properties), ...]
            relations: [(source_id, target_id, relation_type, properties), ...]

        Returns:
            导入结果
        """
        try:
            success_count = 0
            for entity_id, entity_type, properties in entities:
                if self.add_entity(entity_id, entity_type, properties):
                    success_count += 1

            for source_id, target_id, rel_type, properties in relations:
                if self.add_relation(source_id, target_id, rel_type, properties):
                    success_count += 1

            return {
                "success": True,
                "total": len(entities) + len(relations),
                "imported": success_count
            }

        except Exception as e:
            logger.error(f"Batch import error: {e}")
            return {"success": False, "error": str(e)}

    # ==================== 统计信息 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "initialized": self._initialized,
            "vector_store_type": self.config.vector_store_type,
        }

        if self._vector_store:
            stats["vector_count"] = self._vector_store.count()

        if self._hybrid_retriever:
            stats["node_count"] = len(self._hybrid_retriever.graph_traverser._nodes)
            stats["edge_count"] = len(self._hybrid_retriever.graph_traverser._edges)

        return stats

    def close(self) -> None:
        """关闭服务"""
        try:
            if self._neo4j_driver:
                self._neo4j_driver.close()

            logger.info("Knowledge Graph Service closed")

        except Exception as e:
            logger.error(f"Close error: {e}")


class BatchKnowledgeGraphService:
    """
    批量知识图谱服务

    适用于大规模数据处理
    """

    def __init__(self, config: Optional[ServiceConfig] = None):
        self.config = config or ServiceConfig()
        self._main_service = None

    def initialize(self) -> bool:
        """初始化"""
        self._main_service = KnowledgeGraphService(self.config)
        return True

    def process_batch(
        self,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量处理

        Args:
            items: [{"type": "entity" or "relation", ...}, ...]

        Returns:
            处理结果
        """
        if not self._main_service:
            return {"error": "Not initialized"}

        results = {"success": 0, "failed": 0}

        for item in items:
            item_type = item.get("type")
            try:
                if item_type == "entity":
                    success = self._main_service.add_entity(
                        entity_id=item["entity_id"],
                        entity_type=item["entity_type"],
                        properties=item.get("properties", {}),
                        embedding=item.get("embedding")
                    )
                elif item_type == "relation":
                    success = self._main_service.add_relation(
                        source_id=item["source_id"],
                        target_id=item["target_id"],
                        relation_type=item["relation_type"],
                        properties=item.get("properties")
                    )
                else:
                    continue

                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1

            except Exception as e:
                logger.error(f"Process item error: {e}")
                results["failed"] += 1

        return results

    def close(self) -> None:
        """关闭"""
        if self._main_service:
            self._main_service.close()


def create_service(config: Optional[ServiceConfig] = None) -> KnowledgeGraphService:
    """
    创建知识图谱服务

    Args:
        config: 服务配置

    Returns:
        KnowledgeGraphService实例
    """
    return KnowledgeGraphService(config)


def create_batch_service(config: Optional[ServiceConfig] = None) -> BatchKnowledgeGraphService:
    """
    创建批量服务

    Args:
        config: 服务配置

    Returns:
        BatchKnowledgeGraphService实例
    """
    return BatchKnowledgeGraphService(config)
