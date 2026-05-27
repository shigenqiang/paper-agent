"""
PDF paper parser.

Extracts title, authors, abstract, and full text from PDF files.
Uses PyMuPDF (fitz) for PDF parsing.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from src.agent_v3.core.exceptions import ParseError
from src.agent_v3.models import Paper, PaperChunk, PaperMetadata

logger = logging.getLogger(__name__)


class PDFParser:
    """Parse academic PDF papers into Paper objects."""

    def parse(self, pdf_path: str) -> Paper:
        """
        Parse a PDF file into a Paper object.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Paper with metadata, full_text, and chunks
        """
        path = Path(pdf_path)
        if not path.exists():
            raise ParseError(f"PDF not found: {pdf_path}")

        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ParseError("PyMuPDF not installed. Run: pip install pymupdf")

        doc = fitz.open(str(path))

        # Extract full text
        pages = []
        for page in doc:
            pages.append(page.get_text())
        full_text = "\n\n".join(pages)

        # Extract metadata from first page
        first_page_text = pages[0] if pages else ""
        metadata = self._extract_metadata(first_page_text, doc)

        # Create chunks by section
        chunks = self._create_chunks(metadata.title, full_text)

        doc.close()

        return Paper(
            metadata=metadata,
            full_text=full_text,
            chunks=chunks,
            pdf_path=str(path),
        )

    def _extract_metadata(self, first_page: str, doc) -> PaperMetadata:
        """Extract paper metadata from first page text."""
        lines = [l.strip() for l in first_page.split("\n") if l.strip()]

        # Title: usually the first non-empty line
        title = lines[0] if lines else "Untitled"

        # Authors: look for lines with common patterns
        authors = []
        for line in lines[1:5]:
            # Skip lines that look like abstracts or institution info
            if len(line) > 100:
                break
            if any(
                kw in line.lower()
                for kw in [
                    "abstract",
                    "university",
                    "department",
                    "institute",
                    "college",
                ]
            ):
                break
            # Check for author-like patterns (names with commas)
            if re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", line):
                authors = [a.strip() for a in re.split(r"[,;]", line) if a.strip()]

        # Abstract
        abstract = ""
        abstract_match = re.search(
            r"(?:abstract|摘\s*要)[:\s]*(.*?)(?:(?:introduction|keywords|1\.|引言|关键词)|\n\n)",
            first_page,
            re.IGNORECASE | re.DOTALL,
        )
        if abstract_match:
            abstract = abstract_match.group(1).strip()

        # Year
        year = None
        year_match = re.search(r"(19|20)\d{2}", first_page)
        if year_match:
            year = int(year_match.group(0))

        return PaperMetadata(
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
        )

    def _create_chunks(self, title: str, full_text: str) -> list[PaperChunk]:
        """Split text into chunks by section."""
        chunks = []

        # Section patterns
        section_patterns = [
            (r"(?:abstract|摘\s*要)", "abstract"),
            (r"(?:introduction|1\.?\s*引言|1\.?\s*Introduction)", "introduction"),
            (r"(?:related work|2\.?\s*相关工作|2\.?\s*Related)", "related_work"),
            (r"(?:method|approach|3\.?\s*方法|3\.?\s*Method)", "method"),
            (r"(?:experiment|evaluation|4\.?\s*实验|4\.?\s*Experiment)", "experiments"),
            (r"(?:result|5\.?\s*结果|5\.?\s*Result)", "results"),
            (r"(?:discussion|6\.?\s*讨论|6\.?\s*Discussion)", "discussion"),
            (r"(?:conclusion|7\.?\s*结论|7\.?\s*Conclusion)", "conclusion"),
            (r"(?:reference|参考文献|References)", "references"),
        ]

        # Find section boundaries
        boundaries = []
        for pattern, section_name in section_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                boundaries.append((match.start(), section_name))

        boundaries.sort(key=lambda x: x[0])

        # Create chunks for each section
        for i, (start, section) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(full_text)
            text = full_text[start:end].strip()
            if len(text) > 50:  # Skip very short sections
                chunks.append(
                    PaperChunk(
                        paper_id="",
                        section=section,
                        text=text[:8000],  # Cap chunk size
                    )
                )

        # If no sections found, create one big chunk
        if not chunks:
            chunks.append(
                PaperChunk(
                    paper_id="",
                    section="full",
                    text=full_text[:8000],
                )
            )

        return chunks


def parse_pdf(pdf_path: str) -> Paper:
    """Convenience function to parse a PDF."""
    return PDFParser().parse(pdf_path)
