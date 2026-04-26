"""
Confidence Calculator - Classification confidence scoring

Calculates confidence scores for query type classifications.
"""
from typing import Set, Optional


class ConfidenceCalculator:
    """Calculates confidence scores for query classifications"""

    # Heuristic thresholds
    LONG_QUERY_THRESHOLD = 20
    HIGH_CONFIDENCE_KEYWORDS = 2

    def __init__(self, keyword_groups):
        """Initialize with keyword groups

        Args:
            keyword_groups: List of (keywords_set, label) tuples
        """
        self.keyword_groups = keyword_groups

    def calculate(self, text: str, classified_label: Optional[str]) -> float:
        """Calculate confidence score for a classification

        Args:
            text: Query text
            classified_label: The label the query was classified as

        Returns:
            Confidence score (0-1)
        """
        if classified_label is None:
            return self._heuristic_confidence(text)

        # Count keyword matches for the classified type
        match_count = self._count_matches_for_label(text, classified_label)

        if match_count > 0:
            return min(1.0, match_count / self.HIGH_CONFIDENCE_KEYWORDS)

        # No direct keyword match - use heuristic
        return self._heuristic_confidence_for_label(text, classified_label)

    def _count_matches_for_label(self, text: str, label: str) -> int:
        """Count keyword matches for a specific label"""
        text_lower = text.lower()
        for keywords, lbl in self.keyword_groups:
            if lbl == label:
                return sum(1 for kw in keywords if kw in text_lower)
        return 0

    def _heuristic_confidence(self, text: str) -> float:
        """Calculate heuristic confidence when no keyword matched"""
        if len(text) > self.LONG_QUERY_THRESHOLD:
            return 0.6  # Medium confidence for long query as exploration
        return 0.5  # Default

    def _heuristic_confidence_for_label(self, text: str, label: str) -> float:
        """Calculate heuristic confidence for a specific label"""
        if label == "exploration" and len(text) > self.LONG_QUERY_THRESHOLD:
            return 0.6
        elif label == "fact" and len(text) <= self.LONG_QUERY_THRESHOLD:
            return 0.6
        return 0.5


def calculate_confidence(text: str, classified_label: Optional[str],
                        keyword_groups) -> float:
    """Convenience function to calculate confidence

    Args:
        text: Query text
        classified_label: Classified label
        keyword_groups: Keyword groups from keyword_sets

    Returns:
        Confidence score (0-1)
    """
    calculator = ConfidenceCalculator(keyword_groups)
    return calculator.calculate(text, classified_label)
