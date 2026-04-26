"""
Reference Parser - Parse reference strings

Parses bibliographic references into structured data.
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedReference:
    """Parsed reference entry"""
    index: int
    raw_text: str
    authors: list = None
    title: str = ""
    year: str = ""
    journal: str = ""
    volume: str = ""
    pages: str = ""
    doi: str = ""

    def __post_init__(self):
        if self.authors is None:
            self.authors = []


class ReferenceParser:
    """Parses reference strings into structured data"""

    YEAR_PATTERN = re.compile(r'\((\d{4})\)|(\d{4})')
    DOI_PATTERN = re.compile(r'doi[:\s]*(.+?)(?:\s|$)', re.IGNORECASE)
    SENTENCE_END_PATTERN = re.compile(r'\.\s+[A-Z]')

    def parse(self, index: int, raw_text: str) -> ParsedReference:
        """Parse a reference string

        Args:
            index: Reference number
            raw_text: Raw reference text

        Returns:
            ParsedReference
        """
        ref = ParsedReference(index=index, raw_text=raw_text)

        # Extract year
        year_match = self.YEAR_PATTERN.search(raw_text)
        if year_match:
            ref.year = year_match.group(1) or year_match.group(2)

        # Extract DOI
        doi_match = self.DOI_PATTERN.search(raw_text)
        if doi_match:
            ref.doi = doi_match.group(1).strip().rstrip('.,')

        # Parse structure
        self._parse_structure(raw_text, ref)

        return ref

    def _parse_structure(self, text: str, ref: ParsedReference) -> None:
        """Parse the structure of a reference

        Strategy: Find sentence boundaries (". " followed by uppercase)
        to separate authors, title, and journal info.
        """
        # Find all sentence boundaries
        boundaries = []
        for match in self.SENTENCE_END_PATTERN.finditer(text):
            end_pos = match.start()
            next_pos = match.end()
            boundaries.append((end_pos, next_pos))

        for end_pos, next_pos in boundaries:
            after_dot = text[next_pos:]
            if after_dot.startswith('and '):
                continue

            # This is a sentence boundary - text before is authors
            author_part = text[:end_pos].strip()
            title_and_rest = text[next_pos:]

            # Find the end of the title (next sentence boundary)
            title_match = re.match(r'^([^.]+)\.\s*(.*)', title_and_rest)
            if title_match:
                ref.title = title_match.group(1).strip()

                # Parse authors
                ref.authors = [a.strip() for a in re.split(r'\s+and\s+', author_part) if a.strip()]

                # Parse journal info (everything after title)
                rest = title_match.group(2).strip()
                rest = re.sub(r'^[\[\],:\s]+', '', rest)

                # Extract year from rest
                rest_year = re.search(r'(\d{4})', rest)
                if rest_year:
                    ref.year = rest_year.group(1)
                    ref.journal = rest[:rest_year.start()].strip().rstrip(',').strip()
                else:
                    ref.journal = rest

                break


class ReferenceSectionParser:
    """Parses the references section of a paper"""

    REFERENCE_SECTION_PATTERN = re.compile(
        r'(?:References|Bibliography|参考文献)\s*\n(.*)',
        re.DOTALL | re.IGNORECASE
    )

    # Pattern for numbered references [1] ...
    NUMBERED_PATTERN = re.compile(r'\[(\d+)\]\s*(.*?)(?=\n\[\d+\]|$)', re.DOTALL)

    # Pattern for author-year references
    AUTHOR_YEAR_PATTERN = re.compile(r'\[([^\]]+)\]\s*(.*?)(?=\n\s*\[|$)', re.DOTALL)

    def __init__(self):
        self.parser = ReferenceParser()

    def parse_section(self, text: str) -> list:
        """Parse the references section

        Args:
            text: Full text containing references section

        Returns:
            List of ParsedReference
        """
        # Find references section
        match = self.REFERENCE_SECTION_PATTERN.search(text)
        if not match:
            return []

        ref_text = match.group(1)

        # Try numbered pattern first
        references = []
        for match in self.NUMBERED_PATTERN.finditer(ref_text):
            index = int(match.group(1))
            raw = match.group(2).strip()
            if len(raw) > 10:  # Filter short matches
                ref = self.parser.parse(index, raw)
                references.append(ref)

        return references


def parse_reference(index: int, raw_text: str) -> ParsedReference:
    """Convenience function to parse a reference

    Args:
        index: Reference number
        raw_text: Raw reference text

    Returns:
        ParsedReference
    """
    return ReferenceParser().parse(index, raw_text)
