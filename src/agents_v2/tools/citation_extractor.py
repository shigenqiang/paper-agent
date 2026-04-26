"""
Citation Extractor - Extract citations from text

Extracts reference numbers from paper text.
"""
import re
from typing import List


class CitationExtractor:
    """Extracts citation markers from text"""

    # Pattern matches [1], [1,2], [1-3], [1,2-5]
    CITATION_PATTERN = re.compile(r'\[(\d+(?:[,-]\d+)*)\]')

    def extract(self, text: str) -> List[str]:
        """Extract all citation markers from text

        Args:
            text: Text containing citations like [1], [1,2], [1-3]

        Returns:
            List of citation numbers as strings
        """
        citations = []
        matches = self.CITATION_PATTERN.finditer(text)

        for match in matches:
            citation = match.group(1)
            expanded = self._expand_citation(citation)
            citations.extend(expanded)

        return list(set(citations))  # Deduplicate

    def _expand_citation(self, citation: str) -> List[str]:
        """Expand citation ranges like '1-3' to ['1', '2', '3']

        Args:
            citation: Citation string like '1', '1,2', '1-3'

        Returns:
            List of individual citation numbers
        """
        result = []

        for part in citation.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-')
                if start.isdigit() and end.isdigit():
                    result.extend(str(i) for i in range(int(start), int(end) + 1))
            elif part.isdigit():
                result.append(part)

        return result


def extract_citations(text: str) -> List[str]:
    """Convenience function to extract citations

    Args:
        text: Text containing citations

    Returns:
        List of citation numbers
    """
    return CitationExtractor().extract(text)
