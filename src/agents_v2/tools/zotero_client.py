"""
Zotero API Client - 参考文献管理集成

Zotero是免费开源的参考文献管理软件，支持:
- 文献检索
- BibTeX导出
- 多格式引用生成
- 个人文献库管理

API文档: https://www.zotero.org/support/dev/web_api/v3/start
"""

from src.agents_v2.logging_config import get_logging_logger

import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = get_logging_logger(__name__)


@dataclass
class ZoteroConfig:
    """Zotero配置"""
    api_key: str = ""
    user_id: str = ""
    library_type: str = "user"  # "user" or "group"
    base_url: str = "https://api.zotero.org"

    @classmethod
    def from_env(cls) -> "ZoteroConfig":
        """从环境变量创建配置"""
        return cls(
            api_key=os.getenv("ZOTERO_API_KEY", ""),
            user_id=os.getenv("ZOTERO_USER_ID", ""),
            library_type=os.getenv("ZOTERO_LIBRARY_TYPE", "user"),
        )

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.api_key and self.user_id)


class ZoteroItem:
    """Zotero文献条目"""

    def __init__(self, data: Dict[str, Any]):
        self.key = data.get("key", "")
        self.version = data.get("version", 0)
        self.item_type = data.get("itemType", "")
        self.data = data

    @property
    def title(self) -> str:
        return self.data.get("title", "")

    @property
    def authors(self) -> List[str]:
        creators = self.data.get("creators", [])
        authors = []
        for creator in creators:
            if creator.get("creatorType") == "author":
                name = creator.get("lastName", "") or creator.get("name", "")
                first_name = creator.get("firstName", "")
                if first_name:
                    name = f"{name}, {first_name}"
                authors.append(name)
        return authors

    @property
    def year(self) -> str:
        date = self.data.get("date", "")
        if date:
            # 尝试提取年份
            import re
            year_match = re.search(r"\d{4}", date)
            if year_match:
                return year_match.group(0)
        return ""

    @property
    def doi(self) -> str:
        return self.data.get("DOI", "")

    @property
    def url(self) -> str:
        return self.data.get("url", "")

    @property
    def abstract(self) -> str:
        return self.data.get("abstractNote", "")

    @property
    def journal(self) -> str:
        return self.data.get("publicationTitle", "") or self.data.get("bookTitle", "")

    @property
    def volume(self) -> str:
        return self.data.get("volume", "")

    @property
    def issue(self) -> str:
        return self.data.get("issue", "")

    @property
    def pages(self) -> str:
        return self.data.get("pages", "")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "key": self.key,
            "item_type": self.item_type,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "doi": self.doi,
            "url": self.url,
            "abstract": self.abstract,
            "journal": self.journal,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
        }

    def to_bibtex(self) -> str:
        """转换为BibTeX格式"""
        # 生成cite key
        first_author = self.authors[0].split(",")[0].strip() if self.authors else "unknown"
        year = self.year or "nd"
        cite_key = f"{first_author}{year}"

        lines = [f"@{self.item_type or 'misc'}{{{cite_key},"]

        if self.title:
            lines.append(f"  title = {{{self.title}}},")

        if self.authors:
            author_str = " and ".join(self.authors)
            lines.append(f"  author = {{{author_str}}},")

        if self.year:
            lines.append(f"  year = {{{self.year}}},")

        if self.journal:
            lines.append(f"  journal = {{{self.journal}}},")

        if self.volume:
            lines.append(f"  volume = {{{self.volume}}},")

        if self.issue:
            lines.append(f"  number = {{{self.issue}}},")

        if self.pages:
            lines.append(f"  pages = {{{self.pages}}},")

        if self.doi:
            lines.append(f"  doi = {{{self.doi}}},")

        if self.url:
            lines.append(f"  url = {{{self.url}}},")

        lines.append("}")
        return "\n".join(lines)

    def to_citation(self, style: str = "apa") -> str:
        """转换为引用格式"""
        author_str = ", ".join(self.authors) if self.authors else "Unknown"
        year = self.year or "n.d."
        title = self.title or "Untitled"

        if style.lower() == "apa":
            citation = f"{author_str} ({year}). {title}."
            if self.journal:
                citation += f" {self.journal}."
            if self.doi:
                citation += f" https://doi.org/{self.doi}"
            return citation

        elif style.lower() == "ieee":
            authors_ieee = ", ".join(self.authors) if self.authors else "Unknown"
            citation = f'{authors_ieee}, "{title},"'
            if self.journal:
                citation += f" {self.journal},"
            citation += f" {year}."
            return citation

        else:  # 默认APA
            return f"{author_str} ({year}). {title}."


class ZoteroClient:
    """
    Zotero API客户端

    支持:
    - 搜索个人/群组文献库
    - 获取文献详情
    - 导出BibTeX
    - 添加新文献
    """

    def __init__(self, config: Optional[ZoteroConfig] = None):
        self.config = config or ZoteroConfig.from_env()
        self._enabled = self.config.is_configured()

    def is_available(self) -> bool:
        """检查Zotero API是否可用"""
        return self._enabled

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Zotero-API-Key": self.config.api_key,
            "Zotero-API-Version": "3",
            "Content-Type": "application/json",
        }

    def _get_base_url(self) -> str:
        """获取API基础URL"""
        if self.config.library_type == "group":
            return f"{self.config.base_url}/groups/{self.config.user_id}"
        else:
            return f"{self.config.base_url}/users/{self.config.user_id}"

    async def search_items(
        self,
        query: str,
        limit: int = 25,
        item_type: Optional[str] = None,
    ) -> List[ZoteroItem]:
        """
        搜索文献

        Args:
            query: 搜索关键词
            limit: 返回结果数量限制
            item_type: 文献类型过滤 (journalArticle, book, etc.)

        Returns:
            ZoteroItem列表
        """
        if not self.is_available():
            logger.warning("Zotero API not configured")
            return []

        try:
            import aiohttp

            url = f"{self._get_base_url()}/items"
            params = {
                "q": query,
                "format": "json",
                "limit": min(limit, 100),
            }

            if item_type:
                params["itemType"] = item_type

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params, headers=self._get_headers()
                ) as resp:
                    if resp.status == 403:
                        logger.error("Zotero API authentication failed")
                        return []
                    if resp.status != 200:
                        logger.error(f"Zotero API error: {resp.status}")
                        return []

                    data = await resp.json()
                    return [ZoteroItem(item) for item in data]

        except Exception as e:
            logger.error(f"Zotero search failed: {e}")
            return []

    async def get_item(self, item_key: str) -> Optional[ZoteroItem]:
        """
        获取单个文献

        Args:
            item_key: 文献Key

        Returns:
            ZoteroItem或None
        """
        if not self.is_available():
            return None

        try:
            import aiohttp

            url = f"{self._get_base_url()}/items/{item_key}"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=self._get_headers()
                ) as resp:
                    if resp.status == 404:
                        return None
                    if resp.status != 200:
                        logger.error(f"Zotero API error: {resp.status}")
                        return None

                    data = await resp.json()
                    return ZoteroItem(data)

        except Exception as e:
            logger.error(f"Zotero get item failed: {e}")
            return None

    async def get_items_top(
        self,
        limit: int = 25,
        collection_key: Optional[str] = None,
    ) -> List[ZoteroItem]:
        """
        获取顶层文献

        Args:
            limit: 返回结果数量限制
            collection_key: 收藏夹Key

        Returns:
            ZoteroItem列表
        """
        if not self.is_available():
            return []

        try:
            import aiohttp

            if collection_key:
                url = f"{self._get_base_url()}/collections/{collection_key}/items"
            else:
                url = f"{self._get_base_url()}/items/top"

            params = {
                "format": "json",
                "limit": min(limit, 100),
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params, headers=self._get_headers()
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"Zotero API error: {resp.status}")
                        return []

                    data = await resp.json()
                    return [ZoteroItem(item) for item in data]

        except Exception as e:
            logger.error(f"Zotero get items failed: {e}")
            return []

    async def add_item(
        self,
        item_data: Dict[str, Any],
    ) -> Optional[ZoteroItem]:
        """
        添加新文献

        Args:
            item_data: 文献数据

        Returns:
            新创建的ZoteroItem或None
        """
        if not self.is_available():
            return None

        try:
            import aiohttp

            url = f"{self._get_base_url()}/items"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=item_data,
                    headers=self._get_headers()
                ) as resp:
                    if resp.status == 403:
                        logger.error("Zotero API write permission denied")
                        return None
                    if resp.status != 200:
                        logger.error(f"Zotero API error: {resp.status}")
                        return None

                    data = await resp.json()
                    return ZoteroItem(data)

        except Exception as e:
            logger.error(f"Zotero add item failed: {e}")
            return None

    async def export_bibtex(
        self,
        item_keys: Optional[List[str]] = None,
        collection_key: Optional[str] = None,
    ) -> str:
        """
        导出BibTeX格式

        Args:
            item_keys: 文献Key列表，为空则导出全部
            collection_key: 收藏夹Key

        Returns:
            BibTeX格式字符串
        """
        if not self.is_available():
            return ""

        try:
            import aiohttp

            if collection_key:
                url = f"{self._get_base_url()}/collections/{collection_key}/items"
            elif item_keys:
                url = f"{self._get_base_url()}/items"
                params = {"itemKey": ",".join(item_keys)}
            else:
                url = f"{self._get_base_url()}/items/top"

            headers = self._get_headers()
            headers["Accept"] = "application/x-bibtex"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params if item_keys else None,
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"Zotero BibTeX export failed: {resp.status}")
                        return ""

                    return await resp.text()

        except Exception as e:
            logger.error(f"Zotero BibTeX export failed: {e}")
            return ""

    async def search_and_format(
        self,
        query: str,
        style: str = "apa",
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        搜索文献并格式化

        Args:
            query: 搜索关键词
            style: 引用格式 (apa, ieee, mla, chicago)
            limit: 结果数量限制

        Returns:
            包含搜索结果和格式化引用的字典
        """
        items = await self.search_items(query, limit=limit)

        if not items:
            return {
                "success": True,
                "query": query,
                "count": 0,
                "items": [],
                "citations": [],
            }

        citations = []
        for item in items:
            citations.append({
                "key": item.key,
                "citation": item.to_citation(style),
                "bibtex": item.to_bibtex(),
                **item.to_dict(),
            })

        return {
            "success": True,
            "query": query,
            "count": len(items),
            "items": [item.to_dict() for item in items],
            "citations": citations,
            "style": style,
        }


async def search_zotero(
    query: str,
    limit: int = 10,
    style: str = "apa",
) -> Dict[str, Any]:
    """
    便捷函数: 搜索Zotero文献库

    Args:
        query: 搜索关键词
        limit: 结果数量限制
        style: 引用格式

    Returns:
        搜索结果
    """
    client = ZoteroClient()
    return await client.search_and_format(query, style=style, limit=limit)


async def export_zotero_bibtex(
    item_keys: Optional[List[str]] = None,
    collection_key: Optional[str] = None,
) -> str:
    """
    便捷函数: 导出BibTeX

    Args:
        item_keys: 文献Key列表
        collection_key: 收藏夹Key

    Returns:
        BibTeX格式字符串
    """
    client = ZoteroClient()
    return await client.export_bibtex(item_keys, collection_key)


def get_tool_spec():
    """获取工具规格"""
    from .tool_spec import ToolSpec, ParameterSpec, ParameterType

    return ToolSpec(
        name="zotero_search",
        description="搜索Zotero个人文献库，获取格式化引用和BibTeX",
        parameters=[
            ParameterSpec(
                name="query",
                description="搜索关键词",
                type=ParameterType.STRING,
                required=True,
            ),
            ParameterSpec(
                name="limit",
                description="结果数量限制",
                type=ParameterType.INTEGER,
                required=False,
                default=10,
            ),
            ParameterSpec(
                name="style",
                description="引用格式: apa, ieee, mla, chicago",
                type=ParameterType.STRING,
                required=False,
                default="apa",
            ),
        ],
        handler=search_zotero,
        category="reference",
    )
