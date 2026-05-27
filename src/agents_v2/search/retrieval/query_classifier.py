"""
Query Type Classifier - Query classification module

Classifies queries into types: FACT_LOOKUP, COMPLEX_REASONING, EXPLORATION,
COMPARISON, DEFINITION for dynamic retrieval strategy selection.
"""
from enum import Enum
from typing import Optional

from .keyword_sets import (
    REASONING_KEYWORDS,
    COMPARISON_KEYWORDS,
    DEFINITION_KEYWORDS,
    FACT_KEYWORDS,
    EXPLORATION_KEYWORDS,
    KEYWORD_GROUPS
)
from .priority_matcher import PriorityMatcher, create_priority_matcher
from .confidence_calculator import calculate_confidence


class QueryType(Enum):
    """Query type enumeration"""
    FACT_LOOKUP = "fact_lookup"
    COMPLEX_REASONING = "complex_reasoning"
    EXPLORATION = "exploration"
    COMPARISON = "comparison"
    DEFINITION = "definition"
    UNKNOWN = "unknown"


# Label to QueryType mapping
LABEL_TO_QUERY_TYPE = {
    "reasoning": QueryType.COMPLEX_REASONING,
    "comparison": QueryType.COMPARISON,
    "definition": QueryType.DEFINITION,
    "fact": QueryType.FACT_LOOKUP,
    "exploration": QueryType.EXPLORATION,
}

# QueryType to label mapping
QUERY_TYPE_TO_LABEL = {v: k for k, v in LABEL_TO_QUERY_TYPE.items()}


class QueryTypeClassifier:
    """Rule-based query classifier using priority-ordered keyword matching

    Uses PriorityMatcher for efficient keyword matching and ConfidenceCalculator
    for confidence scoring.
    """

    def __init__(self):
        """Initialize classifier with keyword sets"""
        self.reasoning_keywords = REASONING_KEYWORDS
        self.comparison_keywords = COMPARISON_KEYWORDS
        self.definition_keywords = DEFINITION_KEYWORDS
        self.fact_keywords = FACT_KEYWORDS
        self.exploration_keywords = EXPLORATION_KEYWORDS

        # Create priority matcher from keyword groups
        self._matcher = create_priority_matcher(KEYWORD_GROUPS)

    def classify(self, query: str) -> QueryType:
        """Classify query into QueryType

        Args:
            query: Query string to classify

        Returns:
            QueryType: Classified type
        """
        # Try keyword-based classification first
        label = self._matcher.match(query)

        if label:
            return LABEL_TO_QUERY_TYPE.get(label, QueryType.UNKNOWN)

        # Fall back to heuristics
        return self._classify_heuristic(query)

    def _classify_heuristic(self, query: str) -> QueryType:
        """Classify using heuristics when no keywords match

        Args:
            query: Query string

        Returns:
            QueryType: Heuristic classification
        """
        # Long query -> exploration
        if len(query) > 20:
            return QueryType.EXPLORATION

        # Short query -> fact lookup (default)
        return QueryType.FACT_LOOKUP

    def get_confidence(self, query: str) -> float:
        """Get classification confidence score (0-1)

        Args:
            query: Query string

        Returns:
            float: Confidence score
        """
        classified_label = None

        # Get the label that would match
        matched_label, _ = self._matcher.match_with_count(query)
        if matched_label:
            classified_label = matched_label
        else:
            # Use heuristic-based label
            classified_label = QUERY_TYPE_TO_LABEL.get(self._classify_heuristic(query))

        return calculate_confidence(query, classified_label, KEYWORD_GROUPS)

    def get_keyword_counts(self, query: str) -> dict:
        """Get keyword match counts for each type

        Args:
            query: Query string

        Returns:
            dict: Counts per keyword type
        """
        query_lower = query.lower()
        counts = {}

        for keywords, label in KEYWORD_GROUPS:
            counts[label] = sum(1 for kw in keywords if kw in query_lower)

        return counts


# Convenience function
def classify_query(query: str) -> QueryType:
    """Classify a query in one line

    Args:
        query: Query string to classify

    Returns:
        QueryType: Classified type
    """
    return QueryTypeClassifier().classify(query)
