"""
统一配置管理 - Unified Configuration

提供:
- MemorySystemConfig: 记忆系统配置
- get_config: 获取配置单例
- validate_config: 配置验证
"""
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DatabaseConfig:
    """数据库配置"""
    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: str = "memory_db"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    @property
    def postgres_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@dataclass
class VectorConfig:
    """向量配置"""
    dimension: int = 1536
    model: str = "text-embedding-3-small"
    provider: str = "openai"  # openai/local
    local_model_path: Optional[str] = None

    # HNSW索引参数
    hnsw_m: int = 16
    hnsw_ef_construction: int = 64
    hnsw_ef_search: int = 64


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    max_size: int = 10000
    ttl_seconds: int = 3600
    redis_enabled: bool = True


@dataclass
class RetrievalConfig:
    """检索配置"""
    enabled: bool = True
    retrieval_interval_seconds: float = 60.0
    min_messages_before_retrieval: int = 5
    min_context_length: int = 100
    max_results: int = 10


@dataclass
class MemoryLayerConfig:
    """记忆层配置"""
    # 短期记忆
    short_term_max_items: int = 100
    short_term_ttl_seconds: float = 3600

    # 会话记忆
    session_max_entries: int = 500
    session_summary_trigger: int = 30

    # 长期记忆
    long_term_persist_threshold: float = 0.7

    # 遗忘配置
    forgetting_threshold: float = 0.1
    forgetting_interval_seconds: float = 3600


@dataclass
class SecurityConfig:
    """安全配置"""
    enable_access_control: bool = False
    enable_audit_log: bool = True
    enable_data_sanitization: bool = True
    sensitive_fields: List[str] = field(default_factory=lambda: [
        "password", "secret", "api_key", "token", "credential"
    ])


@dataclass
class PerformanceConfig:
    """性能配置"""
    max_concurrent_queries: int = 10
    max_batch_size: int = 50
    query_timeout_seconds: float = 30.0
    operation_timeout_seconds: float = 60.0


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    enable_operation_log: bool = True
    enable_retrieval_log: bool = True
    enable_audit_log: bool = True
    log_max_entries: int = 10000


@dataclass
class MemorySystemConfig:
    """记忆系统完整配置"""
    # 版本
    version: str = "4.0"

    # 数据库配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)

    # 向量配置
    vector: VectorConfig = field(default_factory=VectorConfig)

    # 缓存配置
    cache: CacheConfig = field(default_factory=CacheConfig)

    # 检索配置
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)

    # 记忆层配置
    memory_layers: MemoryLayerConfig = field(default_factory=MemoryLayerConfig)

    # 安全配置
    security: SecurityConfig = field(default_factory=SecurityConfig)

    # 性能配置
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)

    # 日志配置
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # LLM配置
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.7

    @classmethod
    def from_env(cls) -> "MemorySystemConfig":
        """从环境变量加载配置"""
        return cls(
            database=DatabaseConfig(
                postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
                postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
                postgres_database=os.getenv("POSTGRES_DATABASE", "memory_db"),
                postgres_user=os.getenv("POSTGRES_USER", "postgres"),
                postgres_password=os.getenv("POSTGRES_PASSWORD", "postgres"),
                redis_host=os.getenv("REDIS_HOST", "localhost"),
                redis_port=int(os.getenv("REDIS_PORT", "6379")),
                redis_db=int(os.getenv("REDIS_DB", "0")),
                redis_password=os.getenv("REDIS_PASSWORD"),
                neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
                neo4j_password=os.getenv("NEO4J_PASSWORD", "password")
            ),
            vector=VectorConfig(
                dimension=int(os.getenv("VECTOR_DIMENSION", "1536")),
                model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
                provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
                local_model_path=os.getenv("LOCAL_MODEL_PATH")
            ),
            cache=CacheConfig(
                enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
                max_size=int(os.getenv("CACHE_MAX_SIZE", "10000")),
                ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "3600")),
                redis_enabled=os.getenv("REDIS_ENABLED", "true").lower() == "true"
            ),
            retrieval=RetrievalConfig(
                enabled=os.getenv("RETRIEVAL_ENABLED", "true").lower() == "true",
                retrieval_interval_seconds=float(os.getenv("RETRIEVAL_INTERVAL", "60")),
                min_messages_before_retrieval=int(os.getenv("MIN_MESSAGES", "5")),
                min_context_length=int(os.getenv("MIN_CONTEXT_LENGTH", "100"))
            ),
            llm_provider=os.getenv("LLM_PROVIDER", "openai"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4"),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7"))
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "version": self.version,
            "database": {
                "postgres": {
                    "host": self.database.postgres_host,
                    "port": self.database.postgres_port,
                    "database": self.database.postgres_database
                },
                "redis": {
                    "host": self.database.redis_host,
                    "port": self.database.redis_port,
                    "db": self.database.redis_db
                },
                "neo4j": {
                    "uri": self.database.neo4j_uri
                }
            },
            "vector": {
                "dimension": self.vector.dimension,
                "model": self.vector.model,
                "provider": self.vector.provider
            },
            "cache": {
                "enabled": self.cache.enabled,
                "max_size": self.cache.max_size,
                "ttl_seconds": self.cache.ttl_seconds
            },
            "retrieval": {
                "enabled": self.retrieval.enabled,
                "interval_seconds": self.retrieval.retrieval_interval_seconds
            },
            "llm": {
                "provider": self.llm_provider,
                "model": self.llm_model,
                "temperature": self.llm_temperature
            }
        }


def get_config() -> MemorySystemConfig:
    """获取配置单例"""
    return MemorySystemConfig.from_env()


def validate_config(config: MemorySystemConfig) -> List[str]:
    """
    验证配置

    Args:
        config: 配置对象

    Returns:
        错误列表(空表示配置有效)
    """
    errors = []

    # 验证数据库配置
    if not config.database.postgres_host:
        errors.append("PostgreSQL host is required")

    if config.vector.dimension not in [384, 768, 1024, 1536, 3072]:
        errors.append(f"Invalid vector dimension: {config.vector.dimension}")

    if config.cache.max_size <= 0:
        errors.append("Cache max_size must be positive")

    if config.cache.ttl_seconds <= 0:
        errors.append("Cache TTL must be positive")

    # 验证LLM配置
    if config.llm_provider not in ["openai", "anthropic", "local"]:
        errors.append(f"Invalid LLM provider: {config.llm_provider}")

    return errors


# 配置单例
_config_instance: Optional[MemorySystemConfig] = None


def get_memory_config() -> MemorySystemConfig:
    """获取记忆系统配置单例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = MemorySystemConfig.from_env()
    return _config_instance
