"""
DOI Utils - DOI验证与信息增强

提供:
- DOI格式验证
- DOI元数据获取
- DOI批量验证
- DOI解析与标准化
"""
from src.agents_v2.logging_config import get_logging_logger

import re

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = get_logging_logger(__name__)


@dataclass
class DOIResult:
    """DOI验证结果"""
    original: str
    normalized: str
    is_valid: bool
    error: str = ""
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "normalized": self.normalized,
            "is_valid": self.is_valid,
            "error": self.error,
            "metadata": self.metadata,
        }


class DOIVerifier:
    """DOI验证器"""

    # DOI正则表达式
    DOI_PATTERN = re.compile(
        r'^(?:https?://(?:dx\.)?doi\.org/|doi:)?'
        r'(10\.\d{4,}(?:\.\d+)*/\S+)$',
        re.IGNORECASE
    )

    # 可信的DOI前缀
    TRUSTED_PREFIXES = [
        "10.1000",      # IEEE
        "10.1001",      # ACM
        "10.1016",      # Elsevier (ScienceDirect)
        "10.1038",      # Nature
        "10.1126",      # Science
        "10.1073",      # PNAS
        "10.1177",      # SAGE
        "10.1093",      # Oxford (OUP)
        "10.1017",      # Cambridge (CUP)
        "10.1361",      # ASME
        "10.1115",      # ASME
        "10.1145",      # ACM (Computing)
        "10.5555",      # Various
        "10.48550",     # arXiv
        "10.36227",     # Nature Research
    ]

    def __init__(self, verify_with_api: bool = True):
        """
        Args:
            verify_with_api: 是否通过API验证DOI
        """
        self.verify_with_api = verify_with_api

    def normalize(self, doi: str) -> Optional[str]:
        """
        标准化DOI格式

        Args:
            doi: 原始DOI字符串

        Returns:
            标准化后的DOI或None
        """
        if not doi:
            return None

        # 移除URL前缀和空白
        doi = doi.strip()
        doi = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', doi, flags=re.IGNORECASE)
        doi = re.sub(r'^doi:', '', doi, flags=re.IGNORECASE)
        doi = doi.strip()

        # 验证格式
        match = self.DOI_PATTERN.match(doi)
        if not match:
            return None

        return match.group(1).lower()

    def validate(self, doi: str) -> DOIResult:
        """
        验证DOI格式

        Args:
            doi: DOI字符串

        Returns:
            DOIResult验证结果
        """
        original = doi
        normalized = self.normalize(doi)

        if not normalized:
            return DOIResult(
                original=original,
                normalized="",
                is_valid=False,
                error="Invalid DOI format"
            )

        # 检查是否包含可信前缀
        has_trusted_prefix = any(
            normalized.startswith(prefix)
            for prefix in self.TRUSTED_PREFIXES
        )

        # 检查基本格式
        if not normalized.startswith("10."):
            return DOIResult(
                original=original,
                normalized=normalized,
                is_valid=False,
                error="DOI must start with 10."
            )

        # 提取前缀后的部分
        suffix = normalized.split("/", 1)[-1] if "/" in normalized else ""
        if not suffix or len(suffix) < 5:
            return DOIResult(
                original=original,
                normalized=normalized,
                is_valid=False,
                error="DOI suffix too short"
            )

        return DOIResult(
            original=original,
            normalized=normalized,
            is_valid=True,
        )

    async def verify_with_crossref(self, doi: str) -> DOIResult:
        """
        通过CrossRef API验证DOI并获取元数据

        Args:
            doi: DOI字符串

        Returns:
            DOIResult包含元数据
        """
        result = self.validate(doi)
        if not result.is_valid:
            return result

        if not self.verify_with_api:
            return result

        try:
            import aiohttp

            url = f"https://api.crossref.org/works/{result.normalized}"
            headers = {
                "Accept": "application/json",
                "User-Agent": "PaperAgent/1.0 (mailto:paperagent@example.com)"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        message = data.get("message", {})
                        result.metadata = self._parse_crossref_response(message)
                        result.is_valid = True
                    elif resp.status == 404:
                        result.is_valid = False
                        result.error = "DOI not found in CrossRef"
                    else:
                        result.error = f"CrossRef API error: {resp.status}"

        except Exception as e:
            logger.error(f"DOI verification failed: {e}")
            result.error = f"Verification error: {str(e)}"

        return result

    def _parse_crossref_response(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """解析CrossRef API响应"""
        return {
            "title": message.get("title", [""])[0] if message.get("title") else "",
            "authors": self._parse_authors(message.get("author", [])),
            "year": message.get("published-print", {}).get("date-parts", [[0]])[0][0]
                    or message.get("published-online", {}).get("date-parts", [[0]])[0][0]
                    or 0,
            "journal": message.get("container-title", [""])[0] if message.get("container-title") else "",
            "volume": message.get("volume", ""),
            "issue": message.get("issue", ""),
            "pages": message.get("page", ""),
            "doi": message.get("DOI", ""),
            "publisher": message.get("publisher", ""),
            "type": message.get("type", ""),
            "is_oa": message.get("is-open-access", False),
            "citation_count": message.get("is-referenced-by-count", 0),
            "url": message.get("URL", ""),
        }

    def _parse_authors(self, authors: List[Dict[str, Any]]) -> List[str]:
        """解析作者列表"""
        result = []
        for author in authors:
            name = ""
            if author.get("given"):
                name = author["given"]
            if author.get("family"):
                name = f"{name} {author['family']}".strip()
            if not name and author.get("name"):
                name = author["name"]
            if name:
                result.append(name)
        return result

    async def batch_verify(self, dois: List[str]) -> List[DOIResult]:
        """
        批量验证DOI

        Args:
            dois: DOI列表

        Returns:
            验证结果列表
        """
        results = []
        for doi in dois:
            result = await self.verify_with_crossref(doi)
            results.append(result)
        return results


class DOIMetadataFetcher:
    """DOI元数据获取器"""

    # API端点
    CROSSREF_API = "https://api.crossref.org/works"
    DATACITE_API = "https://api.datacite.org/dois"

    async def fetch(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        获取DOI元数据

        Args:
            doi: DOI字符串

        Returns:
            元数据字典或None
        """
        verifier = DOIVerifier(verify_with_api=True)
        normalized = verifier.normalize(doi)
        if not normalized:
            return None

        # 尝试CrossRef
        metadata = await self._fetch_from_crossref(normalized)
        if metadata:
            metadata["source"] = "crossref"
            return metadata

        # 尝试DataCite
        metadata = await self._fetch_from_datacite(normalized)
        if metadata:
            metadata["source"] = "datacite"
            return metadata

        return None

    async def _fetch_from_crossref(self, doi: str) -> Optional[Dict[str, Any]]:
        """从CrossRef获取元数据"""
        try:
            import aiohttp

            url = f"{self.CROSSREF_API}/{doi}"
            headers = {
                "Accept": "application/json",
                "User-Agent": "PaperAgent/1.0 (mailto:paperagent@example.com)"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        message = data.get("message", {})
                        verifier = DOIVerifier(verify_with_api=False)
                        return verifier._parse_crossref_response(message)
                    return None

        except Exception as e:
            logger.error(f"CrossRef fetch failed: {e}")
            return None

    async def _fetch_from_datacite(self, doi: str) -> Optional[Dict[str, Any]]:
        """从DataCite获取元数据"""
        try:
            import aiohttp

            url = f"{self.DATACITE_API}/{doi}"
            headers = {"Accept": "application/vnd.api+json"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        attrs = data.get("data", {}).get("attributes", {})
                        return {
                            "title": attrs.get("titles", [{}])[0].get("title", "")
                                    if attrs.get("titles") else "",
                            "year": int(attrs.get("published", "").split("-")[0])
                                   if attrs.get("published") else 0,
                            "doi": doi,
                            "publisher": attrs.get("publisher", ""),
                            "type": attrs.get("types", {}).get("bibtex", ""),
                            "url": attrs.get("url", ""),
                        }
                    return None

        except Exception as e:
            logger.error(f"DataCite fetch failed: {e}")
            return None


async def verify_doi(doi: str) -> DOIResult:
    """
    便捷函数: 验证单个DOI

    Args:
        doi: DOI字符串

    Returns:
        DOIResult
    """
    verifier = DOIVerifier(verify_with_api=True)
    return await verifier.verify_with_crossref(doi)


async def verify_dois(dois: List[str]) -> List[DOIResult]:
    """
    便捷函数: 批量验证DOI

    Args:
        dois: DOI列表

    Returns:
        DOIResult列表
    """
    verifier = DOIVerifier(verify_with_api=True)
    return await verifier.batch_verify(dois)


async def fetch_doi_metadata(doi: str) -> Optional[Dict[str, Any]]:
    """
    便捷函数: 获取DOI元数据

    Args:
        doi: DOI字符串

    Returns:
        元数据字典
    """
    fetcher = DOIMetadataFetcher()
    return await fetcher.fetch(doi)


def extract_doi_from_text(text: str) -> List[str]:
    """
    从文本中提取DOI

    Args:
        text: 文本内容

    Returns:
        DOI列表
    """
    # DOI匹配模式
    pattern = r'10\.\d{4,}(?:\.\d+)*/[^\s"\'<>,\]\)]+'
    matches = re.findall(pattern, text)

    # 标准化和去重
    verifier = DOIVerifier(verify_with_api=False)
    dois = []
    seen = set()

    for doi in matches:
        normalized = verifier.normalize(doi)
        if normalized and normalized not in seen:
            dois.append(normalized)
            seen.add(normalized)

    return dois


def build_citation_from_doi(doi: str, style: str = "apa") -> str:
    """
    通过DOI构建引用

    Args:
        doi: DOI字符串
        style: 引用格式 (apa, ieee)

    Returns:
        引用字符串
    """
    # 返回DOI链接作为占位符
    if style.lower() == "apa":
        return f"https://doi.org/{doi}"
    elif style.lower() == "ieee":
        return f"[Online]. Available: https://doi.org/{doi}"
    return f"https://doi.org/{doi}"
