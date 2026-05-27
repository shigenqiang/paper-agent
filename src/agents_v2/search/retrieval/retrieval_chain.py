"""
Enhanced Retrieval Chain - 增强检索链路

整合查询改写、扩展、多源检索和结果融合的完整检索链路。
"""
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from ..workflow.routing.intent_classifier import IntentType


class RetrievalStrategy(str, Enum):
    """检索策略"""
    FAST = "fast"
    ACCURATE = "accurate"
    BALANCED = "balanced"
    COMPREHENSIVE = "comprehensive"


@dataclass
class RetrievalResult:
    """检索结果"""
    query: str
    documents: List[Dict[str, Any]] = field(default_factory=list)
    total_hits: int = 0
    retrieval_time_ms: float = 0.0
    sources_used: List[str] = field(default_factory=list)
    strategy: RetrievalStrategy = RetrievalStrategy.BALANCED
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return len(self.documents) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "documents": self.documents,
            "total_hits": self.total_hits,
            "retrieval_time_ms": self.retrieval_time_ms,
            "sources_used": self.sources_used,
            "strategy": self.strategy.value if isinstance(self.strategy, Enum) else self.strategy,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


@dataclass
class SourceConfig:
    """数据源配置"""
    name: str
    enabled: bool = True
    priority: int = 1
    max_results: int = 10


class EnhancedRetrievalChain:
    """
    增强检索链路

    功能:
    - 查询理解与改写
    - 多源并行检索
    - 结果融合与重排序
    - 迭代检索优化

    使用示例:
        chain = EnhancedRetrievalChain()

        result = await chain.retrieve(
            query="machine learning optimization",
            intent=IntentType.LITERATURE_SEARCH
        )

        for doc in result.documents:
            print(doc["title"])
    """

    def __init__(
        self,
        enable_rewrite: bool = True,
        enable_expansion: bool = True,
        enable_reranking: bool = True,
        max_sources: int = 3
    ):
        """
        初始化检索链路

        Args:
            enable_rewrite: 是否启用查询改写
            enable_expansion: 是否启用查询扩展
            enable_reranking: 是否启用重排序
            max_sources: 最大数据源数
        """
        self.enable_rewrite = enable_rewrite
        self.enable_expansion = enable_expansion
        self.enable_reranking = enable_reranking
        self.max_sources = max_sources

        self._sources: Dict[str, SourceConfig] = {
            "arxiv": SourceConfig(name="arxiv", priority=1, max_results=10),
            "pubmed": SourceConfig(name="pubmed", priority=2, max_results=10),
            "semantic_scholar": SourceConfig(name="semantic_scholar", priority=3, max_results=5),
        }

        self._query_rewriter: Optional[Callable] = None
        self._query_expander: Optional[Callable] = None
        self._reranker: Optional[Callable] = None

    def set_query_rewriter(self, rewriter: Callable):
        """设置查询改写器"""
        self._query_rewriter = rewriter

    def set_query_expander(self, expander: Callable):
        """设置查询扩展器"""
        self._query_expander = expander

    def set_reranker(self, reranker: Callable):
        """设置重排序器"""
        self._reranker = reranker

    async def retrieve(
        self,
        query: str,
        intent: Optional[IntentType] = None,
        strategy: RetrievalStrategy = RetrievalStrategy.BALANCED,
        filters: Optional[Dict[str, Any]] = None
    ) -> RetrievalResult:
        """
        执行检索

        Args:
            query: 检索查询
            intent: 意图类型
            strategy: 检索策略
            filters: 过滤条件

        Returns:
            RetrievalResult: 检索结果
        """
        import time
        start_time = time.time()

        # 1. 查询理解与改写
        processed_query = await self._process_query(query)

        # 2. 确定要使用的源
        sources = self._select_sources(strategy)

        # 3. 并行检索
        results = await self._parallel_search(processed_query, sources, filters)

        # 4. 结果融合
        fused_results = self._fuse_results(results, strategy)

        # 5. 重排序
        if self.enable_reranking and self._reranker:
            fused_results = await self._rerank(processed_query, fused_results)

        retrieval_time = (time.time() - start_time) * 1000

        return RetrievalResult(
            query=query,
            documents=fused_results,
            total_hits=len(fused_results),
            retrieval_time_ms=retrieval_time,
            sources_used=[s.name for s in sources],
            strategy=strategy,
            confidence=0.85 if fused_results else 0.0,
            metadata={
                "processed_query": processed_query,
                "original_query": query,
                "filters": filters or {}
            }
        )

    async def _process_query(self, query: str) -> str:
        """处理查询（改写和扩展）"""
        processed = query

        # 查询改写
        if self.enable_rewrite and self._query_rewriter:
            try:
                rewritten = await self._query_rewriter(query)
                if rewritten and rewritten != query:
                    processed = rewritten
            except Exception:
                pass

        # 查询扩展
        if self.enable_expansion and self._query_expander:
            try:
                expanded = await self._query_expander(processed)
                if expanded and expanded != processed:
                    processed = expanded
            except Exception:
                pass

        return processed

    def _select_sources(self, strategy: RetrievalStrategy) -> List[SourceConfig]:
        """选择数据源"""
        enabled_sources = [s for s in self._sources.values() if s.enabled]

        if strategy == RetrievalStrategy.FAST:
            # 只使用最快的源
            return sorted(enabled_sources, key=lambda s: s.priority)[:1]
        elif strategy == RetrievalStrategy.ACCURATE:
            # 使用所有源
            return sorted(enabled_sources, key=lambda s: s.priority)
        elif strategy == RetrievalStrategy.BALANCED:
            # 使用前两个源
            return sorted(enabled_sources, key=lambda s: s.priority)[:2]
        else:  # COMPREHENSIVE
            return sorted(enabled_sources, key=lambda s: s.priority)[:self.max_sources]

    async def _parallel_search(
        self,
        query: str,
        sources: List[SourceConfig],
        filters: Optional[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """并行搜索多个源"""
        async def search_source(source: SourceConfig) -> Tuple[str, List[Dict[str, Any]]]:
            try:
                # 模拟检索（实际会调用真实的数据源）
                docs = await self._mock_search(source.name, query, source.max_results)
                return source.name, docs
            except Exception as e:
                print(f"Search failed for {source.name}: {e}")
                return source.name, []

        results = await asyncio.gather(*[search_source(s) for s in sources])
        return dict(results)

    async def _mock_search(
        self,
        source: str,
        query: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """模拟搜索（实际环境中会调用真实API）"""
        # 返回模拟结果
        return [
            {
                "id": f"{source}_{i}",
                "title": f"Sample paper {i} for '{query}'",
                "source": source,
                "score": 1.0 - (i * 0.1),
                "abstract": f"This is a sample abstract for document {i}..."
            }
            for i in range(min(max_results, 5))
        ]

    def _fuse_results(
        self,
        results: Dict[str, List[Dict[str, Any]]],
        strategy: RetrievalStrategy
    ) -> List[Dict[str, Any]]:
        """融合多个源的结果"""
        fused = []
        seen_ids = set()

        # 按策略确定融合顺序
        if strategy == RetrievalStrategy.BALANCED:
            # 交替添加不同源的文档
            max_len = max(len(docs) for docs in results.values()) if results else 0
            for i in range(max_len):
                for source, docs in results.items():
                    if i < len(docs):
                        doc = docs[i]
                        if doc["id"] not in seen_ids:
                            fused.append(doc)
                            seen_ids.add(doc["id"])
        else:
            # 按分数排序
            all_docs = []
            for source, docs in results.items():
                all_docs.extend(docs)

            # 按分数排序
            all_docs.sort(key=lambda d: d.get("score", 0), reverse=True)

            for doc in all_docs:
                if doc["id"] not in seen_ids:
                    fused.append(doc)
                    seen_ids.add(doc["id"])

        return fused

    async def _rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """重排序文档"""
        if not self._reranker or not documents:
            return documents

        try:
            reranked = await self._reranker(query, documents)
            return reranked
        except Exception as e:
            print(f"Reranking failed: {e}")
            return documents

    def add_source(self, source: SourceConfig):
        """添加数据源"""
        self._sources[source.name] = source

    def remove_source(self, name: str):
        """移除数据源"""
        if name in self._sources:
            del self._sources[name]

    def enable_source(self, name: str):
        """启用数据源"""
        if name in self._sources:
            self._sources[name].enabled = True

    def disable_source(self, name: str):
        """禁用数据源"""
        if name in self._sources:
            self._sources[name].enabled = False


async def simple_retrieve(query: str) -> RetrievalResult:
    """便捷函数：简单检索"""
    chain = EnhancedRetrievalChain()
    return await chain.retrieve(query)