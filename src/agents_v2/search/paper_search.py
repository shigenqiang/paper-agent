"""
PaperSearch - 论文搜索

提供论文内容搜索、过滤和排序功能
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import re


@dataclass
class SearchResult:
    """搜索结果"""
    paper_id: str
    version_id: str
    title: str
    snippet: str
    score: float
    matched_terms: List[str]
    created_at: datetime


class PaperSearch:
    """论文搜索引擎"""

    def __init__(self, version_manager=None):
        self.version_manager = version_manager
        self.index: Dict[str, Dict] = {}  # paper_id -> index data

    def _tokenize(self, text: str) -> List[str]:
        """分词 - 简单的空格分词和小写化"""
        text = text.lower()
        # 移除标点符号
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        # 移除短词
        return [t for t in tokens if len(t) >= 2]

    def _compute_score(self, tokens: List[str], indexed_tokens: List[str]) -> float:
        """计算相关性分数"""
        if not indexed_tokens:
            return 0.0

        token_set = set(tokens)
        indexed_set = set(indexed_tokens)

        intersection = token_set & indexed_set
        union = token_set | indexed_set

        if not intersection:
            return 0.0

        # Jaccard相似度
        jaccard = len(intersection) / len(union)

        # 考虑词频
        term_count = len([t for t in indexed_tokens if t in token_set])
        tf = term_count / len(indexed_tokens) if indexed_tokens else 0

        return 0.7 * jaccard + 0.3 * tf

    async def index_paper(
        self,
        paper_id: str,
        content: str,
        title: str = "",
        metadata: Optional[Dict] = None
    ):
        """索引论文内容"""
        tokens = self._tokenize(content)
        title_tokens = self._tokenize(title) if title else []

        self.index[paper_id] = {
            "tokens": tokens,
            "title_tokens": title_tokens,
            "content": content[:1000],  # 保存前1000字符作为snippet
            "metadata": metadata or {},
            "indexed_at": datetime.now()
        }

    async def remove_from_index(self, paper_id: str):
        """从索引中移除论文"""
        if paper_id in self.index:
            del self.index[paper_id]

    async def search(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Tuple[List[SearchResult], int]:
        """
        搜索论文

        Args:
            query: 搜索关键词
            filters: 过滤条件 {owner_id, date_from, date_to, tags}
            limit: 返回结果数量限制
            offset: 偏移量

        Returns:
            (搜索结果列表, 总数)
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return [], 0

        results: List[SearchResult] = []

        for paper_id, index_data in self.index.items():
            # 应用过滤器
            if filters:
                if "owner_id" in filters:
                    owner_id = filters["owner_id"]
                    metadata = index_data.get("metadata", {})
                    if metadata.get("owner_id") != owner_id:
                        continue

                if "date_from" in filters:
                    indexed_at = index_data.get("indexed_at")
                    if indexed_at and indexed_at < filters["date_from"]:
                        continue

                if "date_to" in filters:
                    indexed_at = index_data.get("indexed_at")
                    if indexed_at and indexed_at > filters["date_to"]:
                        continue

            # 计算分数
            all_tokens = index_data["tokens"] + index_data.get("title_tokens", [])
            score = self._compute_score(query_tokens, all_tokens)

            if score > 0:
                # 提取匹配片段
                snippet = self._extract_snippet(index_data["content"], query_tokens)

                results.append(SearchResult(
                    paper_id=paper_id,
                    version_id=index_data.get("version_id", ""),
                    title=index_data.get("metadata", {}).get("title", "Untitled"),
                    snippet=snippet,
                    score=score,
                    matched_terms=[t for t in query_tokens if t in all_tokens],
                    created_at=index_data.get("indexed_at", datetime.now())
                ))

        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)

        # 应用分页
        total = len(results)
        results = results[offset:offset + limit]

        return results, total

    def _extract_snippet(self, content: str, query_tokens: List[str], context_length: int = 100) -> str:
        """提取包含搜索词的片段"""
        content_lower = content.lower()

        for token in query_tokens:
            idx = content_lower.find(token)
            if idx != -1:
                start = max(0, idx - context_length)
                end = min(len(content), idx + context_length)
                snippet = content[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
                return snippet

        # 如果没有精确匹配，返回开头
        return content[:context_length * 2] + "..."

    async def search_by_date(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 10
    ) -> List[SearchResult]:
        """按日期范围搜索"""
        return (await self.search("", filters={"date_from": date_from, "date_to": date_to}, limit=limit))[0]

    async def get_trending(self, limit: int = 10) -> List[SearchResult]:
        """获取热门论文（简单实现：按索引时间排序）"""
        results = []
        for paper_id, index_data in self.index.items():
            results.append(SearchResult(
                paper_id=paper_id,
                version_id=index_data.get("version_id", ""),
                title=index_data.get("metadata", {}).get("title", "Untitled"),
                snippet=index_data["content"][:100] + "...",
                score=0.0,
                matched_terms=[],
                created_at=index_data.get("indexed_at", datetime.now())
            ))

        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:limit]


# 全局搜索实例
_paper_search: Optional[PaperSearch] = None


def get_paper_search() -> PaperSearch:
    """获取全局论文搜索引擎"""
    global _paper_search
    if _paper_search is None:
        _paper_search = PaperSearch()
    return _paper_search
