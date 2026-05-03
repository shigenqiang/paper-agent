"""
学术论文知识图谱构建模块
Academic Paper Knowledge Graph Builder
"""

from .schema.academic_kg_schema import AcademicKGSchema, Entity, Relation, EntityType, RelationType
from .storage.neo4j_client import Neo4jClient
from .storage.vector_store import VectorStoreClient
from .storage.graph_builder import AcademicGraphBuilder
from .parser.pdf_parser import PDFAcademicParser
from .extraction.ner import AcademicNER
from .extraction.relation_extractor import AcademicRelationExtractor
from .fusion.entity_aligner import AuthorDisambiguation, EntityAligner
from .fusion.conflict_resolver import ConflictResolver, ResolutionStrategy
from .embedding.kg_embedder import KGEmbedder
from .embedding.text_embedder import TextEmbedder
from .graphrag.subgraph_retriever import SubgraphRetriever, CommunitySummary
from .graphrag.reasoner import KGReasoner, ReasoningMode, ReasoningStep, ReasoningResult
from .graphrag.answer_generator import GraphRAGAnswerGenerator, GraphRAGAnswer
from .visualization.graph_visualizer import KnowledgeGraphVisualizer, VisualizationConfig

__version__ = "0.1.0"

__all__ = [
    # Schema
    "AcademicKGSchema",
    "Entity",
    "Relation",
    "EntityType",
    "RelationType",
    # Storage
    "Neo4jClient",
    "VectorStoreClient",
    "AcademicGraphBuilder",
    # Parser
    "PDFAcademicParser",
    # Extraction
    "AcademicNER",
    "AcademicRelationExtractor",
    # Fusion
    "AuthorDisambiguation",
    "EntityAligner",
    "ConflictResolver",
    "ResolutionStrategy",
    # Embedding
    "KGEmbedder",
    "TextEmbedder",
    # GraphRAG
    "SubgraphRetriever",
    "CommunitySummary",
    "KGReasoner",
    "ReasoningMode",
    "ReasoningStep",
    "ReasoningResult",
    "GraphRAGAnswerGenerator",
    "GraphRAGAnswer",
    # Visualization
    "KnowledgeGraphVisualizer",
    "VisualizationConfig",
]