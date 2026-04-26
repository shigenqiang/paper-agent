"""
Priority Matcher - Priority-based keyword matching

Implements priority-ordered keyword matching for query classification.
Higher priority keywords are checked first.
"""
from typing import List, Tuple, Set, Optional


class PriorityMatcher:
    """Priority-based keyword matcher

    Checks keywords in priority order and returns the first match.
    """

    def __init__(self, keyword_groups: List[Tuple[Set[str], str]]):
        """Initialize with keyword groups in priority order

        Args:
            keyword_groups: List of (keywords_set, label) tuples
                           Higher index = lower priority
        """
        self.keyword_groups = keyword_groups

    def match(self, text: str) -> Optional[str]:
        """Find the first matching keyword group label

        Args:
            text: Text to search in (will be lowercased)

        Returns:
            Label of first matching group, or None if no match
        """
        text_lower = text.lower()

        for keywords, label in self.keyword_groups:
            if self._contains_any(text_lower, keywords):
                return label

        return None

    def match_with_count(self, text: str) -> Tuple[Optional[str], int]:
        """Find matching label and count of keyword matches

        Args:
            text: Text to search in

        Returns:
            Tuple of (label, match_count) for the first matching group
        """
        text_lower = text.lower()

        for keywords, label in self.keyword_groups:
            count = self._count_matches(text_lower, keywords)
            if count > 0:
                return label, count

        return None, 0

    def _contains_any(self, text: str, keywords: Set[str]) -> bool:
        """Check if text contains any keyword"""
        for keyword in keywords:
            if keyword in text:
                return True
        return False

    def _count_matches(self, text: str, keywords: Set[str]) -> int:
        """Count how many keywords appear in text"""
        return sum(1 for keyword in keywords if keyword in text)

    def get_match_confidence(self, text: str, label: str) -> float:
        """Calculate confidence for a given label match

        Args:
            text: Text that matched
            label: The label that matched

        Returns:
            Confidence score (0-1)
        """
        for keywords, lbl in self.keyword_groups:
            if lbl == label:
                count = self._count_matches(text.lower(), keywords)
                return min(1.0, count / 2.0)
        return 0.5


# Factory function to create matcher from KEYWORD_GROUPS
def create_priority_matcher(keyword_groups: List[Tuple[Set[str], str]]) -> PriorityMatcher:
    """Create a PriorityMatcher from keyword groups

    Args:
        keyword_groups: List of (keywords_set, label) tuples

    Returns:
        PriorityMatcher instance
    """
    return PriorityMatcher(keyword_groups)
