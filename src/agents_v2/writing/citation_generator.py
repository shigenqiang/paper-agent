"""
引用生成器 - Citation Generator

功能:
1. 引用生成
2. 参考文献格式化
3. 多格式支持
4. 引用一致性检查
5. 引用验证（DOI 解析、论文存在性校验）

设计原则:
- 多格式引用支持
- 自动引用提取
- 引用一致性验证
- CrossRef / Semantic Scholar 验证
"""
import json
import logging
import re
import ssl
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CitationStyle(str, Enum):
    """引用格式"""
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"
    GB_T = "gb_t"  # 中国国家标准


@dataclass
class Citation:
    """引用信息"""
    authors: List[str]
    year: str
    title: str
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    publisher: Optional[str] = None


@dataclass
class InTextCitation:
    """文中引用"""
    citation_key: str
    position: str  # e.g., "(Author, 2023)" or "[1]"
    start_index: int
    end_index: int


@dataclass
class CitationResult:
    """引用结果"""
    in_text_citations: List[InTextCitation]
    reference_list: List[str]
    formatted_references: Dict[CitationStyle, List[str]]


class CitationGenerator:
    """引用生成器"""

    def __init__(self, style: CitationStyle = CitationStyle.APA):
        self.style = style

    def format_citation(
        self,
        citation: Citation,
        style: Optional[CitationStyle] = None
    ) -> str:
        """格式化单条引用

        Args:
            citation: 引用信息
            style: 引用格式

        Returns:
            str: 格式化后的引用字符串
        """
        style = style or self.style

        if style == CitationStyle.APA:
            return self._format_apa(citation)
        elif style == CitationStyle.MLA:
            return self._format_mla(citation)
        elif style == CitationStyle.CHICAGO:
            return self._format_chicago(citation)
        elif style == CitationStyle.IEEE:
            return self._format_ieee(citation)
        elif style == CitationStyle.GB_T:
            return self._format_gb_t(citation)
        else:
            return self._format_apa(citation)

    def _format_apa(self, citation: Citation) -> str:
        """APA格式"""
        # Author, A. A., & Author, B. B. (Year). Title. Journal, Volume(Issue), Pages.
        authors = self._format_authors_apa(citation.authors)

        parts = [f"{authors} ({citation.year})."]

        # 标题
        if citation.title:
            parts.append(citation.title)

        # 期刊
        if citation.journal:
            journal_part = citation.journal
            if citation.volume:
                journal_part += f", {citation.volume}"
            if citation.issue:
                journal_part += f"({citation.issue})"
            if citation.pages:
                journal_part += f", {citation.pages}"
            parts.append(journal_part)

        # DOI
        if citation.doi:
            parts.append(f"https://doi.org/{citation.doi}")

        return "".join(f"{p}. " for p in parts).strip()

    def _format_mla(self, citation: Citation) -> str:
        """MLA格式"""
        authors = self._format_authors_mla(citation.authors)

        parts = [f"{authors}. \"{citation.title}.\""]

        if citation.journal:
            journal_part = f"{citation.journal}"
            if citation.volume:
                journal_part += f", vol. {citation.volume}"
            if citation.issue:
                journal_part += f", no. {citation.issue}"
            if citation.year:
                journal_part += f", {citation.year}"
            if citation.pages:
                journal_part += f", pp. {citation.pages}"
            parts.append(journal_part)

        return " ".join(parts).strip()

    def _format_chicago(self, citation: Citation) -> str:
        """Chicago格式"""
        authors = self._format_authors_chicago(citation.authors)

        parts = [f"{authors}. \"{citation.title}.\""]

        if citation.journal:
            journal_part = f"{citation.journal}"
            if citation.volume:
                journal_part += f" {citation.volume}"
            if citation.issue:
                journal_part += f", no. {citation.issue}"
            if citation.year:
                journal_part += f" ({citation.year})"
            if citation.pages:
                journal_part += f": {citation.pages}"
            parts.append(journal_part)

        if citation.doi:
            parts.append(f"https://doi.org/{citation.doi}")

        return " ".join(parts).strip()

    def _format_ieee(self, citation: Citation) -> str:
        """IEEE格式"""
        authors = self._format_authors_ieee(citation.authors)

        parts = [f"{authors}, \"{citation.title},\""]

        if citation.journal:
            journal_part = f"{citation.journal}"
            if citation.volume:
                journal_part += f", vol. {citation.volume}"
            if citation.issue:
                journal_part += f", no. {citation.issue}"
            if citation.pages:
                journal_part += f", pp. {citation.pages}"
            if citation.year:
                journal_part += f", {citation.year}"
            parts.append(journal_part)

        return " ".join(parts).strip()

    def _format_gb_t(self, citation: Citation) -> str:
        """中国国家标准格式"""
        authors = ", ".join(citation.authors)

        parts = [f"{authors}. {citation.title}"]

        if citation.journal:
            journal_part = f"{citation.journal}"
            if citation.volume:
                journal_part += f", {citation.volume}"
            if citation.issue:
                journal_part += f"({citation.issue})"
            if citation.pages:
                journal_part += f": {citation.pages}"
            if citation.year:
                journal_part += f", {citation.year}"
            parts.append(journal_part)

        if citation.doi:
            parts.append(f"DOI: {citation.doi}")

        return "".join(f"{p}." for p in parts).strip()

    def _format_authors_apa(self, authors: List[str]) -> str:
        """APA格式作者"""
        if not authors:
            return ""
        if len(authors) == 1:
            return authors[0]
        if len(authors) == 2:
            return f"{authors[0]}, & {authors[1]}"
        if len(authors) > 2:
            return f"{', '.join(authors[:-1])}, & {authors[-1]}"
        return ", ".join(authors)

    def _format_authors_mla(self, authors: List[str]) -> str:
        """MLA格式作者"""
        if not authors:
            return ""
        if len(authors) == 1:
            return authors[0]
        if len(authors) == 2:
            return f"{authors[0]}, and {authors[1]}"
        if len(authors) > 2:
            return f"{authors[0]}, et al."
        return ", ".join(authors)

    def _format_authors_chicago(self, authors: List[str]) -> str:
        """Chicago格式作者"""
        if not authors:
            return ""
        if len(authors) == 1:
            return authors[0]
        if len(authors) == 2:
            return f"{authors[0]} and {authors[1]}"
        if len(authors) > 2:
            return f"{authors[0]} et al."
        return ", ".join(authors)

    def _format_authors_ieee(self, authors: List[str]) -> str:
        """IEEE格式作者"""
        if not authors:
            return ""
        # IEEE使用首字母缩写
        formatted = []
        for author in authors:
            parts = author.split()
            if len(parts) > 1:
                initials = " ".join(p[0] + "." for p in parts[1:])
                formatted.append(f"{parts[0]}, {initials}")
            else:
                formatted.append(author)
        return ", ".join(formatted)

    def extract_citations_from_text(
        self,
        text: str
    ) -> List[Tuple[str, int, int]]:
        """从文本中提取引用标记

        Args:
            text: 文本

        Returns:
            List[Tuple[str, int, int]]: [(citation_key, start, end)]
        """
        citations = []

        # 提取 [1], [1,2], [1-3] 格式
        pattern = r'\[(\d+(?:[,-]\d+)*)\]'
        for match in re.finditer(pattern, text):
            citations.append((match.group(0), match.start(), match.end()))

        # 提取 (Author, Year) 格式
        pattern = r'\(([A-Za-z]+(?:\s+et\s+al\.?)?,?\s*\d{4})\)'
        for match in re.finditer(pattern, text):
            citations.append((match.group(0), match.start(), match.end()))

        return citations

    def generate_reference_list(
        self,
        citations: List[Citation],
        style: Optional[CitationStyle] = None
    ) -> List[str]:
        """生成参考文献列表

        Args:
            citations: 引用列表
            style: 引用格式

        Returns:
            List[str]: 格式化后的参考文献列表
        """
        style = style or self.style
        references = []

        for citation in citations:
            ref = self.format_citation(citation, style)
            references.append(ref)

        return references


class CitationStyleAdapter:
    """引用格式适配器"""

    def __init__(self):
        self._adapters: Dict[CitationStyle, CitationGenerator] = {}

    def get_adapter(self, style: CitationStyle) -> CitationGenerator:
        """获取指定格式的适配器"""
        if style not in self._adapters:
            self._adapters[style] = CitationGenerator(style=style)
        return self._adapters[style]

    def convert_style(
        self,
        citation: Citation,
        from_style: CitationStyle,
        to_style: CitationStyle
    ) -> str:
        """转换引用格式"""
        from_adapter = self.get_adapter(from_style)
        to_adapter = self.get_adapter(to_style)

        # 先格式化为中间格式
        intermediate = from_adapter.format_citation(citation, from_style)
        # 然后解析并重新格式化
        # 简化处理：直接使用citation数据重新格式化
        return to_adapter.format_citation(citation, to_style)


# 便捷函数
def format_citation(
    citation: Citation,
    style: CitationStyle = CitationStyle.APA
) -> str:
    """便捷引用格式化函数"""
    generator = CitationGenerator(style=style)
    return generator.format_citation(citation, style)


def generate_references(
    citations: List[Citation],
    style: CitationStyle = CitationStyle.APA
) -> List[str]:
    """便捷参考文献生成函数"""
    generator = CitationGenerator(style=style)
    return generator.generate_reference_list(citations, style)


# ===================================================================
# 引用验证 - Citation Verification
# ===================================================================


@dataclass
class VerificationResult:
    """引用验证结果"""
    citation: Citation
    doi_valid: bool = False           # DOI 格式是否有效
    doi_resolved: bool = False        # DOI 能否解析到真实论文
    paper_exists: bool = False        # 论文是否存在于学术数据库
    resolved_metadata: Optional[Dict[str, Any]] = None  # 从数据库解析到的元数据
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.doi_valid and (self.doi_resolved or self.paper_exists)

    def to_dict(self) -> dict:
        return {
            "doi_valid": self.doi_valid,
            "doi_resolved": self.doi_resolved,
            "paper_exists": self.paper_exists,
            "is_valid": self.is_valid,
            "resolved_metadata": self.resolved_metadata,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class CitationVerifier:
    """引用验证器

    支持：
    1. DOI 格式验证（正则）
    2. DOI 解析（CrossRef API）
    3. 论文存在性校验（Semantic Scholar API）
    4. 批量验证

    使用示例:
        verifier = CitationVerifier()
        result = await verifier.verify(Citation(
            authors=["Smith, J."], year="2023", title="...", doi="10.1234/abcd"
        ))
        print(result.is_valid)
    """

    # DOI 正则（宽松匹配）
    DOI_PATTERN = re.compile(r'^10\.\d{4,9}/[^\s]+$')

    # CrossRef API
    CROSSREF_API = "https://api.crossref.org/works/{doi}"

    # Semantic Scholar API
    SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper"
    SEMANTIC_SCHOLAR_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        # SSL context for bypassing cert verification in dev
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    def validate_doi_format(self, doi: str) -> bool:
        """验证 DOI 格式是否有效

        Args:
            doi: DOI 字符串

        Returns:
            bool: 格式是否有效
        """
        if not doi:
            return False
        # 清理前缀
        doi = doi.strip()
        if doi.startswith("https://doi.org/"):
            doi = doi[len("https://doi.org/"):]
        elif doi.startswith("http://dx.doi.org/"):
            doi = doi[len("http://dx.doi.org/"):]
        return bool(self.DOI_PATTERN.match(doi))

    def _http_get_json(self, url: str) -> Optional[Dict]:
        """发送 HTTP GET 请求并返回 JSON"""
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "PaperAgent/1.0 (mailto:agent@example.com)",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=self.timeout, context=self._ssl_ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.debug(f"HTTP GET failed for {url}: {e}")
            return None

    async def resolve_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """通过 CrossRef 解析 DOI 元数据

        Args:
            doi: DOI 字符串

        Returns:
            dict: 论文元数据，或 None（解析失败）
        """
        doi = doi.strip()
        if doi.startswith("https://doi.org/"):
            doi = doi[len("https://doi.org/"):]
        elif doi.startswith("http://dx.doi.org/"):
            doi = doi[len("http://dx.doi.org/"):]

        url = self.CROSSREF_API.format(doi=doi)
        data = self._http_get_json(url)

        if not data or "message" not in data:
            return None

        msg = data["message"]

        # 提取关键元数据
        authors = []
        for author in msg.get("author", []):
            name_parts = []
            if "family" in author:
                name_parts.append(author["family"])
            if "given" in author:
                name_parts.append(author["given"])
            if name_parts:
                authors.append(", ".join(name_parts))

        title = ""
        if "title" in msg and msg["title"]:
            title = msg["title"][0]

        journal = ""
        if "container-title" in msg and msg["container-title"]:
            journal = msg["container-title"][0]

        year = ""
        if "published" in msg:
            pub = msg["published"]
            if "date-parts" in pub and pub["date-parts"]:
                year = str(pub["date-parts"][0][0])

        return {
            "authors": authors,
            "title": title,
            "journal": journal,
            "year": year,
            "doi": msg.get("DOI", doi),
            "volume": msg.get("volume", ""),
            "issue": msg.get("issue", ""),
            "pages": msg.get("page", ""),
            "url": msg.get("URL", ""),
            "type": msg.get("type", ""),
        }

    async def check_paper_exists(
        self,
        title: str,
        authors: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """通过 Semantic Scholar 检查论文是否存在

        Args:
            title: 论文标题
            authors: 作者列表（可选，用于提高匹配精度）

        Returns:
            dict: 匹配到的论文信息，或 None
        """
        if not title:
            return None

        # 使用 Semantic Scholar search API
        import urllib.parse
        params = urllib.parse.urlencode({
            "query": title,
            "limit": 3,
            "fields": "title,authors,year,venue,externalIds,citationCount",
        })
        url = f"{self.SEMANTIC_SCHOLAR_SEARCH}?{params}"
        data = self._http_get_json(url)

        if not data or "data" not in data:
            return None

        # 在结果中查找最匹配的
        for paper in data["data"]:
            paper_title = paper.get("title", "").lower()
            if title.lower() in paper_title or paper_title in title.lower():
                return {
                    "title": paper.get("title", ""),
                    "authors": [a.get("name", "") for a in paper.get("authors", [])],
                    "year": str(paper.get("year", "")),
                    "venue": paper.get("venue", ""),
                    "doi": paper.get("externalIds", {}).get("DOI", ""),
                    "citation_count": paper.get("citationCount", 0),
                }

        return None

    async def verify(self, citation: Citation) -> VerificationResult:
        """验证单条引用

        Args:
            citation: 引用信息

        Returns:
            VerificationResult
        """
        result = VerificationResult(citation=citation)

        # 1. DOI 格式验证
        if citation.doi:
            result.doi_valid = self.validate_doi_format(citation.doi)
            if not result.doi_valid:
                result.errors.append(f"DOI 格式无效: {citation.doi}")

            # 2. DOI 解析
            if result.doi_valid:
                metadata = await self.resolve_doi(citation.doi)
                if metadata:
                    result.doi_resolved = True
                    result.resolved_metadata = metadata
                    # 检查元数据是否与引用一致
                    if citation.title and metadata.get("title"):
                        if citation.title.lower() not in metadata["title"].lower():
                            result.warnings.append(
                                f"标题不匹配: 引用标题 '{citation[:50]}...' vs 解析标题 '{metadata['title'][:50]}...'"
                            )
                else:
                    result.errors.append(f"DOI 无法解析: {citation.doi}")
        else:
            result.warnings.append("未提供 DOI")

        # 3. 论文存在性校验（通过标题搜索）
        if citation.title:
            paper = await self.check_paper_exists(citation.title, citation.authors)
            if paper:
                result.paper_exists = True
                if not result.resolved_metadata:
                    result.resolved_metadata = paper
            elif not result.doi_resolved:
                result.errors.append(f"论文在学术数据库中未找到: {citation.title[:50]}...")
        else:
            result.errors.append("引用缺少标题")

        return result

    async def verify_batch(
        self,
        citations: List[Citation],
        max_concurrent: int = 3,
    ) -> List[VerificationResult]:
        """批量验证引用

        Args:
            citations: 引用列表
            max_concurrent: 最大并发数

        Returns:
            List[VerificationResult]
        """
        results = []
        for citation in citations:
            result = await self.verify(citation)
            results.append(result)
        return results

    def generate_verification_report(
        self,
        results: List[VerificationResult],
    ) -> Dict[str, Any]:
        """生成验证报告

        Args:
            results: 验证结果列表

        Returns:
            dict: 验证报告
        """
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        invalid = total - valid
        doi_provided = sum(1 for r in results if r.citation.doi)
        doi_valid = sum(1 for r in results if r.doi_valid)
        doi_resolved = sum(1 for r in results if r.doi_resolved)
        paper_found = sum(1 for r in results if r.paper_exists)

        all_errors = []
        all_warnings = []
        for r in results:
            all_errors.extend(r.errors)
            all_warnings.extend(r.warnings)

        return {
            "total": total,
            "valid": valid,
            "invalid": invalid,
            "valid_rate": round(valid / total, 3) if total > 0 else 0.0,
            "doi_provided": doi_provided,
            "doi_valid": doi_valid,
            "doi_resolved": doi_resolved,
            "paper_found": paper_found,
            "errors": all_errors,
            "warnings": all_warnings,
        }


# 便捷函数
async def verify_citation(citation: Citation) -> VerificationResult:
    """验证单条引用"""
    verifier = CitationVerifier()
    return await verifier.verify(citation)


async def verify_references(citations: List[Citation]) -> Dict[str, Any]:
    """验证引用列表并生成报告"""
    verifier = CitationVerifier()
    results = await verifier.verify_batch(citations)
    return verifier.generate_verification_report(results)
