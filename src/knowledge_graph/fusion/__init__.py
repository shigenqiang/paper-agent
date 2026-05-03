"""
知识融合模块
Knowledge Fusion Module
"""

from .entity_aligner import AuthorDisambiguation, EntityAligner
from .conflict_resolver import ConflictResolver

__all__ = [
    "AuthorDisambiguation",
    "EntityAligner",
    "ConflictResolver",
]
