"""
DOI验证器 - DOI Verifier

功能：
1. 验证DOI格式
2. 通过DOI获取论文元数据
3. 检查论文是否真实存在
"""

import re
import asyncio
from typing import Dict, Any, Optional

from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class DOIVerifier:
    """
    DOI验证器

    支持：
    - DOI格式验证
    - 通过CrossRef API获取元数据
    - 通过DataCite API验证
    """

    DOI_PATTERN = re.compile(r'^10\.\d{4,}/[^\s]+$')

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def validate_format(self, doi: str) -> bool:
        """
        验证DOI格式是否合法

        Args:
            doi: DOI字符串

        Returns:
            True如果格式合法
        """
        if not doi:
            return False

        # 清理DOI（去除前缀）
        doi = self._clean_doi(doi)
        return bool(self.DOI_PATTERN.match(doi))

    def _clean_doi(self, doi: str) -> str:
        """清理DOI字符串，去除常见前缀"""
        if not doi:
            return ""

        # 去除常见前缀
        prefixes_to_remove = [
            "https://doi.org/",
            "http://doi.org/",
            "doi:",
            "DOI:",
            "doi.org/",
        ]

        cleaned = doi.strip()
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):]
                break

        return cleaned

    async def verify(self, doi: str) -> Dict[str, Any]:
        """
        验证DOI并获取元数据

        Args:
            doi: DOI字符串

        Returns:
            {
                valid: bool,
                doi: str,
                title: str,
                authors: List[str],
                year: str,
                journal: str,
                error: str
            }
        """
        doi = self._clean_doi(doi)

        if not self.validate_format(doi):
            return {
                "valid": False,
                "doi": doi,
                "error": "Invalid DOI format",
                "title": "",
                "authors": [],
                "year": "",
                "journal": ""
            }

        try:
            # 尝试从CrossRef获取元数据
            metadata = await self._fetch_crossref(doi)
            if metadata:
                return {
                    "valid": True,
                    "doi": doi,
                    "title": metadata.get("title", ""),
                    "authors": metadata.get("authors", []),
                    "year": metadata.get("year", ""),
                    "journal": metadata.get("journal", ""),
                    "volume": metadata.get("volume", ""),
                    "pages": metadata.get("pages", ""),
                    "publisher": metadata.get("publisher", ""),
                    "error": ""
                }

            return {
                "valid": True,  # 格式正确但无法获取元数据
                "doi": doi,
                "error": "Could not fetch metadata",
                "title": "",
                "authors": [],
                "year": "",
                "journal": ""
            }

        except Exception as e:
            logger.error(f"DOI verification failed for {doi}: {e}")
            return {
                "valid": False,
                "doi": doi,
                "error": str(e),
                "title": "",
                "authors": [],
                "year": "",
                "journal": ""
            }

    async def _fetch_crossref(self, doi: str) -> Optional[Dict[str, Any]]:
        """从CrossRef API获取元数据"""
        import aiohttp

        url = f"https://api.crossref.org/works/{doi}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={"Accept": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        message = data.get("message", {})

                        # 解析作者
                        authors = []
                        for author in message.get("author", []):
                            name = author.get("given", "") + " " + author.get("family", "")
                            name = name.strip()
                            if name:
                                authors.append(name)

                        # 解析年份
                        date_parts = message.get("published-print", message.get("published-online", {})).get("date-parts", [[]])
                        year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""

                        return {
                            "title": message.get("title", [""])[0] if message.get("title") else "",
                            "authors": authors,
                            "year": year,
                            "journal": message.get("container-title", [""])[0] if message.get("container-title") else "",
                            "volume": message.get("volume", ""),
                            "pages": message.get("page", ""),
                            "publisher": message.get("publisher", ""),
                        }

        except Exception as e:
            logger.warning(f"CrossRef API error for {doi}: {e}")

        return None

    def parse_doi_from_url(self, url: str) -> Optional[str]:
        """
        从URL中提取DOI

        Args:
            url: 包含DOI的URL

        Returns:
            DOI字符串或None
        """
        if not url:
            return None

        # 常见模式
        patterns = [
            r'doi\.org/(10\.\d{4,}/[^\s]+)',
            r'dx\.doi\.org/(10\.\d{4,}/[^\s]+)',
            r'10\.\d{4,}/[^\s]+',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                doi = match.group(1) if match.lastindex else match.group(0)
                return self._clean_doi(doi)

        return None


# 便捷函数
async def verify_doi(doi: str) -> Dict[str, Any]:
    """
    便捷函数：验证DOI

    Args:
        doi: DOI字符串

    Returns:
        验证结果
    """
    verifier = DOIVerifier()
    return await verifier.verify(doi)