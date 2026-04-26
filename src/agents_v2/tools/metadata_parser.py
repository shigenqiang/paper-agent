"""
Metadata Parser - Parse paper metadata from text

Extracts title, authors, abstract, keywords, DOI from paper text.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ParsedMetadata:
    """Parsed paper metadata"""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    publication_date: str = ""
    doi: str = ""
    journal: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""


class MetadataParser:
    """Parses metadata from paper text"""

    ABSTRACT_PATTERN = re.compile(
        r'(?:Abstract|摘要)\s*[:：]?\s*(.*?)(?=\n\s*(?:Keywords|关键词|1\.|Introduction))',
        re.DOTALL | re.IGNORECASE
    )

    KEYWORDS_PATTERN = re.compile(
        r'(?:Keywords?|关键词)\s*[:：]?\s*(.*?)(?:\n|$)',
        re.IGNORECASE
    )

    DOI_PATTERN = re.compile(
        r'doi[:\s]*(?:https?://)?(?:dx\.)?doi\.org/(.*?)(?:\s|$)',
        re.IGNORECASE
    )

    AUTHOR_PATTERN = re.compile(
        r'(?:Authors?|作者)\s*[:：]?\s*(.*?)(?:\n|$)',
        re.IGNORECASE
    )

    def parse(self, text: str, first_n_lines: int = 20) -> ParsedMetadata:
        """Parse metadata from paper text

        Args:
            text: Full paper text
            first_n_lines: Number of lines to search for title

        Returns:
            ParsedMetadata
        """
        metadata = ParsedMetadata()

        # Extract title (first substantial line)
        lines = text.split('\n')[:first_n_lines]
        metadata.title = self._extract_title(lines)

        # Extract abstract
        abstract_match = self.ABSTRACT_PATTERN.search(text)
        if abstract_match:
            metadata.abstract = abstract_match.group(1).strip()

        # Extract keywords
        keywords_match = self.KEYWORDS_PATTERN.search(text)
        if keywords_match:
            kw_text = keywords_match.group(1)
            metadata.keywords = [k.strip() for k in re.split(r'[,，;；]', kw_text) if k.strip()]

        # Extract DOI
        doi_match = self.DOI_PATTERN.search(text)
        if doi_match:
            metadata.doi = doi_match.group(1).strip()

        # Extract authors
        author_match = self.AUTHOR_PATTERN.search(text)
        if author_match:
            authors_str = author_match.group(1)
            metadata.authors = [a.strip() for a in re.split(r'[,，;；\n]', authors_str) if a.strip()]

        return metadata

    def _extract_title(self, lines: List[str]) -> str:
        """Extract title from first lines

        Args:
            lines: First N lines of text

        Returns:
            Title string
        """
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip abstract/keywords markers
            if line.lower().startswith('abstract'):
                break
            if line.lower().startswith('摘要'):
                break
            if line.lower().startswith('keywords'):
                break
            if line.lower().startswith('关键词'):
                break

            # Skip page numbers (just digits)
            if re.match(r'^\d+$', line):
                continue

            # Skip short lines with colons (likely headers)
            if len(line) < 100 and ':' in line:
                continue

            # Found title
            if len(line) > 5:
                return line

        return ""


def parse_metadata(text: str) -> ParsedMetadata:
    """Convenience function to parse metadata

    Args:
        text: Paper text

    Returns:
        ParsedMetadata
    """
    return MetadataParser().parse(text)
