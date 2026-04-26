"""
分层记忆系统 v3 - 基于Mem0/Zep架构

提供:
1. 短期记忆 - 当前任务上下文 (ShortTermMemory)
2. 会话记忆 - 跨Agent共享 (SessionMemory)
3. 长期记忆 - 跨任务持久化 (LongTermMemory)
4. 情景记忆 - 执行轨迹记录 (EpisodicMemory)
5. 统一接口 - UnifiedMemoryManager

核心服务:
- MemoryExtractor: 记忆提取 (LLM驱动)
- SummaryGenerator: 摘要生成
- RetrievalEngine: 检索引擎
- ForgettingController: 遗忘控制器
- EnhancedRetrievalEngine: 增强检索引擎

向量嵌入:
- OpenAIEmbedder: text-embedding-3-small/ada-002
- LocalEmbedder: sentence-transformers
"""
from .types import (
    MemoryType,
    ImportanceLevel,
    MemoryEntry,
    EpisodicEntry,
    UserPreference,
    ProcedureEntry
)
from .short_term import ShortTermMemory, ShortTermMemoryConfig
from .session import SessionMemory, SessionConfig
from .long_term import LongTermMemory, VectorStore, GraphStore
from .episodic import EpisodicMemory
from .relational import RelationalStorage, RelationalSchema
from .retrieval import (
    EnhancedRetrievalEngine,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStrategy,
    QueryType,
    HybridRetriever,
    BM25
)
from .embeddings import (
    BaseEmbedder,
    OpenAIEmbedder,
    LocalEmbedder,
    EmbeddingConfig,
    EmbeddingResult,
    VectorStore as EnhancedVectorStore,
    create_embedder
)
from .services import (
    MemoryExtractor,
    SummaryGenerator,
    RetrievalEngine,
    ForgettingController,
    MemoryCache,
    BatchMemoryOperations,
    AdaptiveCache,
    PrefetchStrategy,
    QueryCache,
    ConcurrentQueryOptimizer
)
from .unified import (
    UnifiedMemoryManager,
    UnifiedMemoryConfig,
    get_memory_manager,
    init_memory_for_task
)
from .context_persistence import (
    ContextCheckpoint,
    ContextPersistence,
    get_persistence
)
from .mcp_protocol import (
    MCPMemoryProtocol,
    MCPMemoryResource,
    MCPToolResult
)
from .monitoring import (
    MemoryStatsCollector,
    MemoryPerformanceMonitor,
    AccessAnalytics,
    LayerStats,
    AccessStats,
    RetrievalStats,
    RetentionStats,
    MemorySystemStats
)
from .compression import (
    MemoryCompressor,
    KeyPointExtractor,
    CompressedEntry,
    IncrementalCompressor
)
from .agent_bridge import (
    AgentMemoryBridge,
    ContextInjector
)
from .error_recovery import (
    MemoryErrorRecovery,
    MemoryCircuitBreaker,
    MemoryFallback,
    ResilientMemoryWrapper,
    RecoveryStats,
    FailureType
)
from .logging_tracing import (
    MemoryLogger,
    MemoryTracer,
    OperationLog,
    RetrievalLog,
    LogLevel
)
from .security import (
    MemoryAccessControl,
    DataSanitizer,
    AuditLogger,
    SecurityManager,
    Permission,
    AccessRule,
    AuditEntry
)
from .distributed import (
    DistributedMemoryManager,
    MemoryNode,
    NodeRegistry,
    NodeStatus,
    LoadBalancer,
    ConsistentHashing,
    DistributedOperationResult
)
from .postgres_storage import (
    PostgresConnection,
    VectorStorage,
    RelationalStorage,
    ConnectionPool,
    get_postgres_connection,
    initialize_postgres_memory
)
from .redis_cache import (
    RedisCache,
    DistributedCache,
    RedisPipeline,
    CacheStats,
    get_redis_cache
)
from .neo4j_store import (
    Neo4jGraphStore,
    GraphEntity,
    GraphRelation,
    get_neo4j_graph_store
)
from .config import (
    MemorySystemConfig,
    DatabaseConfig,
    VectorConfig,
    CacheConfig,
    RetrievalConfig,
    MemoryLayerConfig,
    SecurityConfig,
    PerformanceConfig,
    LoggingConfig,
    get_config,
    get_memory_config,
    validate_config
)

__all__ = [
    # 类型定义
    "MemoryType",
    "ImportanceLevel",
    "MemoryEntry",
    "EpisodicEntry",
    "UserPreference",
    "ProcedureEntry",
    # 短期记忆
    "ShortTermMemory",
    "ShortTermMemoryConfig",
    # 会话记忆
    "SessionMemory",
    "SessionConfig",
    # 长期记忆
    "LongTermMemory",
    "VectorStore",
    "GraphStore",
    # 情景记忆
    "EpisodicMemory",
    # 关系数据库
    "RelationalStorage",
    "RelationalSchema",
    # 检索系统
    "EnhancedRetrievalEngine",
    "RetrievalQuery",
    "RetrievalResult",
    "RetrievalStrategy",
    "QueryType",
    "HybridRetriever",
    "BM25",
    # 向量嵌入
    "BaseEmbedder",
    "OpenAIEmbedder",
    "LocalEmbedder",
    "EmbeddingConfig",
    "EmbeddingResult",
    "EnhancedVectorStore",
    "create_embedder",
    # 核心服务
    "MemoryExtractor",
    "SummaryGenerator",
    "RetrievalEngine",
    "ForgettingController",
    "MemoryCache",
    "BatchMemoryOperations",
    "AdaptiveCache",
    "PrefetchStrategy",
    "QueryCache",
    "ConcurrentQueryOptimizer",
    # 统一管理器
    "UnifiedMemoryManager",
    "UnifiedMemoryConfig",
    "get_memory_manager",
    "init_memory_for_task",
    # 检查点
    "ContextCheckpoint",
    "ContextPersistence",
    "get_persistence",
    # MCP协议
    "MCPMemoryProtocol",
    "MCPMemoryResource",
    "MCPToolResult",
    # 监控面板
    "MemoryStatsCollector",
    "MemoryPerformanceMonitor",
    "AccessAnalytics",
    "LayerStats",
    "AccessStats",
    "RetrievalStats",
    "RetentionStats",
    "MemorySystemStats",
    # 压缩
    "MemoryCompressor",
    "KeyPointExtractor",
    "CompressedEntry",
    "IncrementalCompressor",
    # Agent桥接
    "AgentMemoryBridge",
    "ContextInjector",
    # 错误恢复
    "MemoryErrorRecovery",
    "MemoryCircuitBreaker",
    "MemoryFallback",
    "ResilientMemoryWrapper",
    "RecoveryStats",
    "FailureType",
    # 日志追踪
    "MemoryLogger",
    "MemoryTracer",
    "OperationLog",
    "RetrievalLog",
    "LogLevel",
    # 安全
    "MemoryAccessControl",
    "DataSanitizer",
    "AuditLogger",
    "SecurityManager",
    "Permission",
    "AccessRule",
    "AuditEntry",
    # 分布式
    "DistributedMemoryManager",
    "MemoryNode",
    "NodeRegistry",
    "NodeStatus",
    "LoadBalancer",
    "ConsistentHashing",
    "DistributedOperationResult",
    # PostgreSQL存储
    "PostgresConnection",
    "VectorStorage",
    "RelationalStorage",
    "ConnectionPool",
    "get_postgres_connection",
    "initialize_postgres_memory",
    # Redis缓存
    "RedisCache",
    "DistributedCache",
    "RedisPipeline",
    "CacheStats",
    "get_redis_cache",
    # Neo4j图存储
    "Neo4jGraphStore",
    "GraphEntity",
    "GraphRelation",
    "get_neo4j_graph_store",
    # 配置
    "MemorySystemConfig",
    "DatabaseConfig",
    "VectorConfig",
    "CacheConfig",
    "RetrievalConfig",
    "MemoryLayerConfig",
    "SecurityConfig",
    "PerformanceConfig",
    "LoggingConfig",
    "get_config",
    "get_memory_config",
    "validate_config"
]
