"""
Retrieval模块 - 智能检索相关组件

包含:
- QueryTypeClassifier: 查询类型分类器
- DynamicRetrievalPlanner: 动态检索规划器
- SELF-RAGController: 自我反思RAG控制器
- CrossEncoderReranker: 交叉编码器重排序
- IterativeRetriever: 迭代式检索引擎
- ResultFuser: 多源结果融合
- Deduplicator: 检索结果去重
- AdaptiveRetrieval: 自适应检索
"""
from .query_classifier import QueryType, QueryTypeClassifier, classify_query
from .dynamic_planner import (
    DynamicRetrievalPlanner,
    RetrievalPlan,
    RetrievalStrategy,
    STRATEGY_CONFIGS,
    create_retrieval_plan
)
from .self_rag_controller import (
    SELF_RAGController,
    RAGResponse,
    DocumentEvaluation,
    self_rag_answer
)
from .cross_encoder_reranker import (
    CrossEncoderReranker,
    HybridReranker,
    RerankedDoc,
    rerank_documents
)
from .iterative_retriever import (
    IterativeRetriever,
    AdaptiveRetriever,
    RetrievalResult,
    RetrievalStep,
    iterative_retrieve
)
from .result_fuser import (
    ResultFuser,
    FusionStrategy,
    FusionConfig,
    ScoredItem,
    fuse_results
)
from .deduplicator import (
    Deduplicator,
    DeduplicationStrategy,
    DedupConfig,
    deduplicate
)
from .adaptive_retrieval import (
    AdaptiveRetrievalPlanner,
    RetrievalStrategy as AdaptiveRetrievalStrategy,
    adaptive_retrieve
)

__all__ = [
    # 查询类型分类器
    "QueryType",
    "QueryTypeClassifier",
    "classify_query",

    # 动态规划器
    "DynamicRetrievalPlanner",
    "RetrievalPlan",
    "RetrievalStrategy",
    "STRATEGY_CONFIGS",
    "create_retrieval_plan",

    # SELF-RAG控制器
    "SELF_RAGController",
    "RAGResponse",
    "DocumentEvaluation",
    "self_rag_answer",

    # 重排序器
    "CrossEncoderReranker",
    "HybridReranker",
    "RerankedDoc",
    "rerank_documents",

    # 迭代检索器
    "IterativeRetriever",
    "AdaptiveRetriever",
    "RetrievalResult",
    "RetrievalStep",
    "iterative_retrieve",

    # 结果融合
    "ResultFuser",
    "FusionStrategy",
    "FusionConfig",
    "ScoredItem",
    "fuse_results",

    # 去重
    "Deduplicator",
    "DeduplicationStrategy",
    "DedupConfig",
    "deduplicate",

    # 自适应检索
    "AdaptiveRetrievalPlanner",
    "adaptive_retrieve"
]
