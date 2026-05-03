"""
学术论文知识图谱配置
"""
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Neo4jConfig(BaseModel):
    """Neo4j图数据库配置"""
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"


class VectorStoreConfig(BaseModel):
    """向量数据库配置"""
    type: str = "qdrant"
    url: str = "http://localhost:6333"
    collection_name: str = "academic_kg"
    embedding_dim: int = 256


class NERConfig(BaseModel):
    """NER模型配置"""
    model_name: str = "dmis-lab/biobert-base-cased-v1.2"
    max_length: int = 512
    batch_size: int = 16
    device: str = "cuda"
    entity_types: list = ["Paper", "Author", "Institution", "Venue", "Keyword", "Method", "Dataset"]


class RelationExtractionConfig(BaseModel):
    """关系抽取配置"""
    model_name: str = "roberta-base"
    batch_size: int = 8
    relation_types: list = [
        "AUTHORED_BY", "AFFILIATED_WITH", "PUBLISHED_IN",
        "HAS_KEYWORD", "CITES", "USES_METHOD", "USES_DATASET", "COLLABORATES_WITH"
    ]


class EmbeddingConfig(BaseModel):
    """嵌入配置"""
    text_embedder: str = "bge-m3"
    kg_embedder: str = "RotatE"
    embedding_dim: int = 256


class GraphRAGConfig(BaseModel):
    """GraphRAG配置"""
    subgraph_depth: int = 2
    top_k_entities: int = 10
    community_threshold: float = 0.5
    max_nodes_visualization: int = 100


class KnowledgeGraphConfig(BaseSettings):
    """知识图谱系统配置"""
    # 项目根目录
    project_root: Path = Path(__file__).parent.parent.parent.parent

    # 数据目录
    data_dir: Path = project_root / "data" / "knowledge_graph"
    raw_data_dir: Path = data_dir / "raw"
    processed_data_dir: Path = data_dir / "processed"

    # Neo4j配置
    neo4j: Neo4jConfig = Neo4jConfig()

    # 向量存储配置
    vector_store: VectorStoreConfig = VectorStoreConfig()

    # NER配置
    ner: NERConfig = NERConfig()

    # 关系抽取配置
    relation_extraction: RelationExtractionConfig = RelationExtractionConfig()

    # 嵌入配置
    embedding: EmbeddingConfig = EmbeddingConfig()

    # GraphRAG配置
    graphrag: GraphRAGConfig = GraphRAGConfig()

    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None

    class Config:
        env_prefix = "KG_"
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
config = KnowledgeGraphConfig()


def get_config() -> KnowledgeGraphConfig:
    """获取配置实例"""
    return config
