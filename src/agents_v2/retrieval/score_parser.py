"""
Score Parser - Parse LLM scores from text

Extracts numeric scores from LLM responses.
"""
import re
from typing import Optional


class ScoreParser:
    """Parses numeric scores from LLM text responses"""

    # Regex patterns for score extraction
    DECIMAL_PATTERN = re.compile(r'0?\.\d+')
    INTEGER_PATTERN = re.compile(r'\d+')

    @classmethod
    def parse_score(cls, text: str, default: float = 0.5) -> float:
        """Parse score from text

        Args:
            text: Text containing score
            default: Default score if parsing fails

        Returns:
            float: Parsed score (0-1 range)
        """
        import re

        # Try to find a number (integer or decimal)
        number_pattern = re.compile(r'\d+\.?\d*')
        match = number_pattern.search(text)
        if match:
            score = float(match.group())
            # If > 1, assume it's out of 10
            if score > 1:
                score = score / 10.0
            return max(0.0, min(1.0, score))

        return default

    @classmethod
    def parse_boolean(cls, text: str) -> bool:
        """Parse boolean from text

        Args:
            text: Text to parse

        Returns:
            bool: True if text indicates yes/是, False otherwise
        """
        # Check for explicit "否" (no)
        if "否" in text:
            # Check if "是" also appears (contradiction)
            if "是" in text:
                return True  # Ambiguous, default to True
            return False
        return True


# Convenience functions
def parse_llm_score(text: str, default: float = 0.5) -> float:
    """Parse score from LLM response"""
    return ScoreParser.parse_score(text, default)


def parse_llm_boolean(text: str) -> bool:
    """Parse boolean from LLM response"""
    return ScoreParser.parse_boolean(text)
