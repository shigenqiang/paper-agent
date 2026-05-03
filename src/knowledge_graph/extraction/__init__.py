"""Extraction module - 信息抽取"""

from .ner import AcademicNER
from .relation_extractor import AcademicRelationExtractor

__all__ = [
    "AcademicNER",
    "AcademicRelationExtractor",
]
