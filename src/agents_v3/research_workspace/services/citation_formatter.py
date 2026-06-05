"""引用格式化工具 — 支持 APA / GB-T 7714 / BibTeX / Simple"""

from __future__ import annotations

from typing import Any


class CitationFormatter:
    """将论文元数据格式化为不同引用样式"""

    @staticmethod
    def format_simple(paper: dict[str, Any]) -> str:
        """简单格式: [paper_id] Authors (Year). Title."""
        authors = ", ".join(paper.get("authors", [])[:3])
        year = paper.get("year", "n.d.")
        title = paper.get("title", "N/A")
        pid = paper.get("paper_id", "")
        ref = f"[{pid}] {authors} ({year}). {title}."
        if paper.get("doi"):
            ref += f" DOI: {paper['doi']}"
        return ref

    @staticmethod
    def format_apa(paper: dict[str, Any]) -> str:
        """APA 7th: Author, A. A., & Author, B. B. (Year). Title. Venue. DOI"""
        authors = paper.get("authors", [])
        year = paper.get("year", "n.d.")
        title = paper.get("title", "N/A")
        venue = paper.get("venue", "")
        doi = paper.get("doi", "")

        # APA author format: Last, F. M.
        formatted_authors = []
        for a in authors[:7]:
            parts = a.strip().split()
            if len(parts) >= 2:
                formatted_authors.append(f"{parts[-1]}, {''.join(p[0] + '.' for p in parts[:-1] if p)}")
            else:
                formatted_authors.append(a)
        if len(authors) > 7:
            formatted_authors.append("... " + _apa_last_author(authors[-1]))

        author_str = ", ".join(formatted_authors)
        ref = f"{author_str} ({year}). {title}."
        if venue:
            ref += f" {venue}."
        if doi:
            ref += f" https://doi.org/{doi}"
        return ref

    @staticmethod
    def format_gbt7714(paper: dict[str, Any]) -> str:
        """GB/T 7714-2015: 作者. 题名[文献类型]. 刊名, 年, 卷(期): 页码."""
        authors = paper.get("authors", [])
        year = paper.get("year", "")
        title = paper.get("title", "N/A")
        venue = paper.get("venue", "")
        doi = paper.get("doi", "")

        # GB/T 7714: 前 3 作者全列，超过 3 个加"等"或"et al"
        is_chinese = any(_is_cjk(a) for a in authors[:1])
        if len(authors) <= 3:
            author_str = ", ".join(authors)
        else:
            suffix = "等" if is_chinese else ", et al"
            author_str = ", ".join(authors[:3]) + suffix

        ref = f"{author_str}. {title}[J]."
        if venue:
            ref += f" {venue},"
        if year:
            ref += f" {year}."
        if doi:
            ref += f" DOI: {doi}."
        return ref

    @staticmethod
    def format_bibtex(paper: dict[str, Any]) -> str:
        """BibTeX 格式"""
        authors = paper.get("authors", [])
        year = paper.get("year", "")
        title = paper.get("title", "N/A")
        venue = paper.get("venue", "")
        doi = paper.get("doi", "")
        pid = paper.get("paper_id", "unknown")

        # BibTeX key: first_author_last_name + year
        key = _bibtex_key(authors, year, pid)

        author_str = " and ".join(authors) if authors else "Unknown"
        lines = [f"@article{{{key},"]
        lines.append(f"  title = {{{title}}},")
        lines.append(f"  author = {{{author_str}}},")
        if year:
            lines.append(f"  year = {{{year}}},")
        if venue:
            lines.append(f"  journal = {{{venue}}},")
        if doi:
            lines.append(f"  doi = {{{doi}}},")
        lines.append("}")
        return "\n".join(lines)

    @classmethod
    def format(cls, paper: dict[str, Any], style: str = "simple") -> str:
        """统一入口"""
        formatters = {
            "simple": cls.format_simple,
            "apa": cls.format_apa,
            "gbt7714": cls.format_gbt7714,
            "bibtex": cls.format_bibtex,
        }
        fn = formatters.get(style, cls.format_simple)
        return fn(paper)


def _apa_last_author(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return f"{parts[-1]}, {''.join(p[0] + '.' for p in parts[:-1] if p)}"
    return name


def _is_cjk(text: str) -> bool:
    for ch in text:
        if "一" <= ch <= "鿿":
            return True
    return False


def _bibtex_key(authors: list[str], year: str, pid: str) -> str:
    if authors:
        last = authors[0].split()[-1].lower() if authors[0] else "unknown"
        return f"{last}{year or 'nd'}"
    return pid.replace(":", "_")
