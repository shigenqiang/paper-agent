"""
知识图谱模块

子模块:
- kg_community: 社区检测算法 (Leiden/Louvain/LPA)
- kg_hybrid_retriever: 混合检索 (向量+图+MMR)
- kg_batch_operations: 批量导入与事务管理
- kg_vector_store: 向量存储 (内存/Qdrant)
- kg_embeddings: 图嵌入 (TransE/ComplEx)
- kg_summarizer: 子图摘要生成 (GraphRAG)
- kg_graphrag: GraphRAG问答流程
- kg_extractors: 信息提取 (实体/关系)
- kg_schema: 数据模型与索引
- kg_service: 统一服务API
"""
from .kg_community import (
    Community,
    CommunityHierarchy,
    CommunityAlgorithm,
    LouvainDetector,
    LeidenDetector,
    LabelPropagationDetector,
    detect_communities
)
from .kg_hybrid_retriever import (
    RetrievalResult,
    QueryContext,
    VectorSearcher,
    GraphTraverser,
    MMRReranker,
    HybridRetriever,
    EntityLinker,
    RetrievalMethod
)
from .kg_batch_operations import (
    BatchResult,
    IncrementalUpdate,
    BatchImporter,
    IncrementalUpdater,
    TransactionManager,
    BatchMode
)
from .kg_vector_store import (
    VectorSearchResult,
    BaseVectorStore,
    InMemoryVectorStore,
    QdrantVectorStore,
    EmbeddingModel,
    create_vector_store
)
from .kg_embeddings import (
    EmbeddingResult,
    TransE,
    ComplEx,
    EmbeddingTrainer
)
from .kg_summarizer import (
    GraphNode,
    GraphEdge,
    Subgraph,
    EntityContext,
    SubgraphSummary,
    SubgraphExtractor,
    GraphSentenceGenerator,
    EntityDescriptionGenerator,
    SubgraphSummarizer
)
from .kg_graphrag import (
    QueryType,
    Query,
    RetrievalItem,
    GraphRAGContext,
    QueryClassifier,
    GraphRAGRetriever,
    GraphRAGQA,
    create_graphrag_qa
)
from .kg_extractors import (
    EntityType,
    RelationType,
    ExtractedEntity,
    ExtractedRelation,
    KnowledgeGraphResult,
    EntityExtractor,
    RelationExtractor,
    KnowledgeGraphGenerator
)
from .kg_schema import (
    NodeType,
    PropertyDefinition,
    NodeSchema,
    RelationshipSchema,
    SchemaManager,
    QueryOptimizer,
    IndexManager,
    DataModelValidator,
    create_default_schema_manager
)
from .kg_service import (
    ServiceConfig,
    KnowledgeGraphService,
    BatchKnowledgeGraphService,
    create_service,
    create_batch_service
)

__all__ = [
    # 社区检测
    "Community",
    "CommunityHierarchy",
    "CommunityAlgorithm",
    "LouvainDetector",
    "LeidenDetector",
    "LabelPropagationDetector",
    "detect_communities",
    # 混合检索
    "RetrievalResult",
    "QueryContext",
    "VectorSearcher",
    "GraphTraverser",
    "MMRReranker",
    "HybridRetriever",
    "EntityLinker",
    "RetrievalMethod",
    # 批量操作
    "BatchResult",
    "IncrementalUpdate",
    "BatchImporter",
    "IncrementalUpdater",
    "TransactionManager",
    "BatchMode",
    # 向量存储
    "VectorSearchResult",
    "BaseVectorStore",
    "InMemoryVectorStore",
    "QdrantVectorStore",
    "EmbeddingModel",
    "create_vector_store",
    # 图嵌入
    "EmbeddingResult",
    "TransE",
    "ComplEx",
    "EmbeddingTrainer",
    # 子图摘要
    "GraphNode",
    "GraphEdge",
    "Subgraph",
    "EntityContext",
    "SubgraphSummary",
    "SubgraphExtractor",
    "GraphSentenceGenerator",
    "EntityDescriptionGenerator",
    "SubgraphSummarizer",
    # GraphRAG
    "QueryType",
    "Query",
    "RetrievalItem",
    "GraphRAGContext",
    "QueryClassifier",
    "GraphRAGRetriever",
    "GraphRAGQA",
    "create_graphrag_qa",
    # 信息提取
    "EntityType",
    "RelationType",
    "ExtractedEntity",
    "ExtractedRelation",
    "KnowledgeGraphResult",
    "EntityExtractor",
    "RelationExtractor",
    "KnowledgeGraphGenerator",
    # 数据模型与索引
    "NodeType",
    "PropertyDefinition",
    "NodeSchema",
    "RelationshipSchema",
    "SchemaManager",
    "QueryOptimizer",
    "IndexManager",
    "DataModelValidator",
    "create_default_schema_manager",
    # 统一服务API
    "ServiceConfig",
    "KnowledgeGraphService",
    "BatchKnowledgeGraphService",
    "create_service",
    "create_batch_service"
]
