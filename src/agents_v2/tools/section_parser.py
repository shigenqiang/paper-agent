"""
Section Parser - Parse paper sections

Detects and extracts paper sections from text.
"""
import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class ParsedSection:
    """Parsed section"""
    title: str
    level: int  # 1 = main section, 2 = subsection
    start_pos: int
    end_pos: int
    content: str = ""


class SectionParser:
    """Parses paper sections from text"""

    # Section title patterns (in priority order)
    SECTION_PATTERNS = [
        # Level 1 sections
        (r'^Abstract$', 1),
        (r'^Introduction$', 1),
        (r'^Background$', 1),
        (r'^Related Work$', 1),
        (r'^Literature Review$', 1),
        (r'^Preliminaries$', 1),
        (r'^Methodology$', 1),
        (r'^Methods?$', 1),
        (r'^Approach$', 1),
        (r'^Proposed Method$', 1),
        (r'^Algorithm$', 1),
        (r'^Experiments?$', 1),
        (r'^Experimental Results?$', 1),
        (r'^Results?$', 1),
        (r'^Discussion$', 1),
        (r'^Conclusion[s]?$', 1),
        (r'^References$', 1),
        (r'^Bibliography$', 1),
        (r'^Acknowledgments?$', 1),
        # Level 2 sections (subsections)
        (r'^\d+\.\d+\s+[A-Z]', 2),
        (r'^[A-Z][a-z]+\s+[A-Z]', 2),
    ]

    def parse(self, text: str) -> List[ParsedSection]:
        """Parse sections from text

        Args:
            text: Full paper text

        Returns:
            List of ParsedSection
        """
        sections = []
        current_section = None
        lines = text.split('\n')

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            matched_level = None
            for pattern, level in self.SECTION_PATTERNS:
                if re.match(pattern, line_stripped, re.MULTILINE | re.IGNORECASE):
                    matched_level = level
                    break

            if matched_level:
                # Save previous section
                if current_section:
                    current_section.end_pos = i
                    current_section.content = text[current_section.start_pos:i]

                # Start new section
                current_section = ParsedSection(
                    title=line_stripped,
                    level=matched_level,
                    start_pos=i,
                    end_pos=i
                )
                sections.append(current_section)

        # Finalize last section
        if current_section:
            current_section.end_pos = len(lines)
            current_section.content = text[current_section.start_pos:len(lines)]

        return sections

    def get_section_by_title(self, sections: List[ParsedSection], title: str) -> ParsedSection:
        """Get a section by its title

        Args:
            sections: List of parsed sections
            title: Section title to find

        Returns:
            ParsedSection or None
        """
        title_lower = title.lower()
        for section in sections:
            if section.title.lower() == title_lower:
                return section
        return None

    def get_main_sections(self, sections: List[ParsedSection]) -> List[ParsedSection]:
        """Get only level 1 (main) sections

        Args:
            sections: List of parsed sections

        Returns:
            List of main sections
        """
        return [s for s in sections if s.level == 1]


def parse_sections(text: str) -> List[ParsedSection]:
    """Convenience function to parse sections

    Args:
        text: Paper text

    Returns:
        List of ParsedSection
    """
    return SectionParser().parse(text)
