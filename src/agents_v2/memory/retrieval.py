"""
增强检索引擎 - Enhanced Retrieval Engine

特性:
1. 混合搜索: 语义向量 + BM25关键词
2. 检索时机器学习: 根据查询类型选择最佳检索策略
3. 多层检索: ShortTerm → Session → LongTerm → Episodic
4. 检索时机决策: 基于上下文的智能检索触发
"""
import asyncio
import math
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from .types import MemoryEntry, MemoryType
from .long_term import LongTermMemory, VectorStore


class RetrievalStrategy(str, Enum):
    """检索策略"""
    SEMANTIC = "semantic"        # 语义向量检索
    KEYWORD = "keyword"          # BM25关键词检索
    HYBRID = "hybrid"           # 混合检索
    GRAPH = "graph"             # 图关系检索
    TEMPORAL = "temporal"       # 时序检索
    DIRECT = "direct"            # 直接键查找


class QueryType(str, Enum):
    """查询类型"""
    FACTUAL = "factual"         # 事实查询 "谁/什么/何时"
    PROCEDURAL = "procedural"   # 流程查询 "如何做"
    EXPLANATORY = "explanatory" # 解释查询 "为什么"
    TEMPORAL = "temporal"       # 时序查询 "之前发生了什么"
    ENTITY = "entity"          # 实体查询 "关于X的所有信息"


@dataclass
class RetrievalQuery:
    """检索查询"""
    text: str
    query_type: Optional[QueryType] = None
    memory_types: Optional[List[MemoryType]] = None
    tags: Optional[List[str]] = None
    time_range: Optional[Tuple[float, float]] = None  # (start, end)
    entity_id: Optional[str] = None
    limit: int = 10
    threshold: float = 0.1


@dataclass
class RetrievalResult:
    """检索结果"""
    entry: MemoryEntry
    score: float
    strategy: RetrievalStrategy
    matched_fields: List[str] = field(default_factory=list)


class BM25:
    """
    BM25 检索算法

    基于Lucene的BM25评分实现
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.avg_doc_length = 0
        self.doc_count = 0
        self.doc_lengths: Dict[str, int] = {}
        self.term_doc_freqs: Dict[str, int] = {}
        self.doc_term_freqs: Dict[str, Dict[str, int]] = {}

    def index(self, doc_id: str, text: str) -> None:
        """索引文档"""
        # 分词
        terms = self._tokenize(text)
        self.doc_lengths[doc_id] = len(terms)
        self.doc_term_freqs[doc_id] = defaultdict(int)

        for term in terms:
            self.doc_term_freqs[doc_id][term] += 1
            self.term_doc_freqs[term] = self.term_doc_freqs.get(term, 0) + 1

        self.doc_count += 1
        self.avg_doc_length = sum(self.doc_lengths.values()) / self.doc_count

    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        # 停用词过滤
        stop_words = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'to', 'of', 'in', 'for', 'on', 'with', 'at',
            'by', 'from', 'as', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'under', 'again',
            'further', 'then', 'once', 'here', 'there', 'when', 'where',
            'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
            'so', 'than', 'too', 'very', 'just', 'but', 'and', 'or', 'if'
        }
        return [t for t in tokens if t not in stop_words and len(t) > 1]

    def score(self, doc_id: str, query_terms: List[str]) -> float:
        """计算文档与查询的BM25得分"""
        if doc_id not in self.doc_lengths:
            return 0.0

        doc_len = self.doc_lengths[doc_id]
        term_freqs = self.doc_term_freqs.get(doc_id, {})

        score = 0.0
        for term in query_terms:
            if term not in self.term_doc_freqs:
                continue

            tf = term_freqs.get(term, 0)
            df = self.term_doc_freqs[term]

            # IDF
            idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1)

            # TF normalization
            tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length))

            score += idf * tf_norm

        return score

    def search(self, query: str, doc_ids: List[str], limit: int = 10) -> List[Tuple[str, float]]:
        """搜索"""
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        scores = []
        for doc_id in doc_ids:
            score = self.score(doc_id, query_terms)
            if score > 0:
                scores.append((doc_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:limit]


class HybridRetriever:
    """
    混合检索器

    结合:
    - 语义向量检索 (VectorStore)
    - BM25关键词检索
    - 图关系检索
    """

    def __init__(
        self,
        vector_store: VectorStore,
        relational_store: Optional[Any] = None
    ):
        self.vector_store = vector_store
        self.relational_store = relational_store
        self.bm25 = BM25()
        self._bm25_indexed: bool = False

    def index_for_bm25(self, items: Dict[str, str]) -> None:
        """
        为BM25建立索引

        Args:
            items: {key: text_content}
        """
        for key, text in items.items():
            self.bm25.index(key, text)
        self._bm25_indexed = True

    async def hybrid_search(
        self,
        query: str,
        doc_ids: List[str],
        limit: int = 10,
        alpha: float = 0.5  # 向量权重
    ) -> List[Tuple[str, float]]:
        """
        混合搜索

        Args:
            query: 查询文本
            doc_ids: 要搜索的文档ID列表
            limit: 返回数量
            alpha: 向量检索权重 (1-alpha为BM25权重)

        Returns:
            [(doc_id, score)]
        """
        # 向量检索
        vector_results = await self.vector_store.search(query, limit=limit)
        vector_scores = {r["key"]: r["similarity"] for r in vector_results}

        # BM25检索
        bm25_scores = {}
        if self._bm25_indexed:
            bm25_results = self.bm25.search(query, doc_ids, limit=limit)
            bm25_scores = {k: v for k, v in bm25_results}

        # 分数归一化
        max_vector = max(vector_scores.values()) if vector_scores else 1.0
        max_bm25 = max(bm25_scores.values()) if bm25_scores else 1.0

        # 混合评分
        hybrid_scores = {}
        all_keys = set(vector_scores.keys()) | set(bm25_scores.keys())

        for key in all_keys:
            vec_score = vector_scores.get(key, 0) / max_vector if max_vector > 0 else 0
            bm25_score = bm25_scores.get(key, 0) / max_bm25 if max_bm25 > 0 else 0
            hybrid_scores[key] = alpha * vec_score + (1 - alpha) * bm25_score

        # 排序
        sorted_scores = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:limit]


class EnhancedRetrievalEngine:
    """
    增强检索引擎

    功能:
    1. 查询类型识别
    2. 策略自动选择
    3. 多层记忆检索
    4. 检索时机决策
    """

    # 查询类型关键词
    QUERY_TYPE_PATTERNS = {
        QueryType.FACTUAL: [
            r'^谁', r'^什么', r'^何时', r'^多少',
            r'who', r'what', r'when', r'how many'
        ],
        QueryType.PROCEDURAL: [
            r'^如何', r'^怎么', r'^怎样',
            r'^步骤', r'^流程',
            r'how to', r'how do', r'steps', r'process'
        ],
        QueryType.EXPLANATORY: [
            r'^为什么', r'^为何',
            r'^解释', r'^原因',
            r'why', r'explain', r'reason'
        ],
        QueryType.TEMPORAL: [
            r'^之前', r'^后来', r'^然后',
            r'^最后', r'^之前',
            r'before', r'after', r'previously', r'later'
        ],
        QueryType.ENTITY: [
            r'^关于.*的所有',
            r'^X的信息',
            r'all about', r'information about'
        ]
    }

    def __init__(
        self,
        long_term_memory: LongTermMemory,
        relational_store: Optional[Any] = None
    ):
        self.long_term_memory = long_term_memory
        self.relational_store = relational_store
        self.hybrid_retriever = HybridRetriever(
            vector_store=long_term_memory.vector_store,
            relational_store=relational_store
        )

        # 检索历史 (用于学习)
        self._retrieval_history: List[Dict] = []
        self._query_type_stats: Dict[QueryType, int] = defaultdict(int)

    def classify_query(self, query: str) -> QueryType:
        """
        分类查询类型

        Args:
            query: 查询文本

        Returns:
            QueryType
        """
        query_lower = query.lower().strip()

        for qtype, patterns in self.QUERY_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    self._query_type_stats[qtype] += 1
                    return qtype

        # 默认根据内容特征判断
        if any(kw in query_lower for kw in ['how', '如何', '步骤']):
            return QueryType.PROCEDURAL
        elif any(kw in query_lower for kw in ['before', 'after', '之前', '之后']):
            return QueryType.TEMPORAL
        elif any(kw in query_lower for kw in ['why', '为什么']):
            return QueryType.EXPLANATORY
        else:
            return QueryType.FACTUAL

    def select_strategy(
        self,
        query_type: QueryType,
        memory_types: List[MemoryType]
    ) -> List[RetrievalStrategy]:
        """
        选择检索策略

        Args:
            query_type: 查询类型
            memory_types: 目标记忆类型

        Returns:
            策略列表 (按优先级排序)
        """
        # 基于查询类型选择
        strategy_map = {
            QueryType.FACTUAL: [RetrievalStrategy.HYBRID, RetrievalStrategy.SEMANTIC],
            QueryType.PROCEDURAL: [RetrievalStrategy.KEYWORD, RetrievalStrategy.HYBRID],
            QueryType.EXPLANATORY: [RetrievalStrategy.SEMANTIC, RetrievalStrategy.HYBRID],
            QueryType.TEMPORAL: [RetrievalStrategy.TEMPORAL, RetrievalStrategy.HYBRID],
            QueryType.ENTITY: [RetrievalStrategy.GRAPH, RetrievalStrategy.HYBRID]
        }

        return strategy_map.get(query_type, [RetrievalStrategy.HYBRID])

    def select_memory_layers(
        self,
        query_type: QueryType,
        context: Optional[Dict[str, Any]] = None
    ) -> List[MemoryType]:
        """
        选择要检索的记忆层

        Args:
            query_type: 查询类型
            context: 上下文信息

        Returns:
            MemoryType列表 (按检索优先级排序)
        """
        # 基于查询类型选择层次
        layer_map = {
            QueryType.FACTUAL: [
                MemoryType.LONG_TERM,
                MemoryType.SESSION,
                MemoryType.SHORT_TERM
            ],
            QueryType.PROCEDURAL: [
                MemoryType.PROCEDURAL,
                MemoryType.LONG_TERM,
                MemoryType.SESSION
            ],
            QueryType.EXPLANATORY: [
                MemoryType.LONG_TERM,
                MemoryType.SESSION,
                MemoryType.EPISODIC
            ],
            QueryType.TEMPORAL: [
                MemoryType.EPISODIC,
                MemoryType.SESSION,
                MemoryType.LONG_TERM
            ],
            QueryType.ENTITY: [
                MemoryType.LONG_TERM,
                MemoryType.USER_PROFILE,
                MemoryType.SESSION
            ]
        }

        return layer_map.get(query_type, [
            MemoryType.LONG_TERM,
            MemoryType.SESSION,
            MemoryType.SHORT_TERM
        ])

    async def retrieve(
        self,
        query: RetrievalQuery,
        context: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """
        统一检索接口

        Args:
            query: 检索查询
            context: 上下文 (包含short_term, session等)

        Returns:
            检索结果列表
        """
        # 1. 分类查询
        query_type = query.query_type or self.classify_query(query.text)

        # 2. 选择策略
        strategies = self.select_strategy(query_type, query.memory_types or [])

        # 3. 选择记忆层
        memory_layers = query.memory_types or self.select_memory_layers(query_type, context)

        # 4. 执行检索
        all_results: List[RetrievalResult] = []

        for layer in memory_layers:
            results = await self._retrieve_from_layer(
                query=query,
                layer=layer,
                strategies=strategies,
                context=context
            )
            all_results.extend(results)

        # 5. 结果融合
        fused = self._fuse_results(all_results, query)

        # 6. 记录检索历史
        self._log_retrieval(query, fused)

        return fused[:query.limit]

    async def _retrieve_from_layer(
        self,
        query: RetrievalQuery,
        layer: MemoryType,
        strategies: List[RetrievalStrategy],
        context: Optional[Dict[str, Any]]
    ) -> List[RetrievalResult]:
        """从特定层检索"""
        results: List[RetrievalResult] = []

        if layer == MemoryType.LONG_TERM:
            # 使用混合检索
            for strategy in strategies:
                if strategy == RetrievalStrategy.HYBRID:
                    hybrid_results = await self._hybrid_retrieve(query.text, limit=query.limit)
                    results.extend(hybrid_results)
                elif strategy == RetrievalStrategy.SEMANTIC:
                    semantic_results = await self._semantic_retrieve(query.text, limit=query.limit)
                    results.extend(semantic_results)
                elif strategy == RetrievalStrategy.KEYWORD:
                    keyword_results = await self._keyword_retrieve(query.text, limit=query.limit)
                    results.extend(keyword_results)

        elif layer == MemoryType.SHORT_TERM and context:
            short_term = context.get("short_term")
            if short_term:
                search_results = await short_term.search(query.text, limit=query.limit)
                for entry in search_results:
                    results.append(RetrievalResult(
                        entry=entry,
                        score=0.9,  # 短期记忆高相关性
                        strategy=RetrievalStrategy.DIRECT,
                        matched_fields=["content"]
                    ))

        elif layer == MemoryType.SESSION and context:
            session = context.get("session")
            if session:
                messages = await session.get_messages(limit=query.limit)
                for msg in messages:
                    entry = MemoryEntry(
                        id=msg.get("message_id", ""),
                        memory_type=MemoryType.SESSION,
                        content=msg.get("content", ""),
                        metadata=msg
                    )
                    # 简单关键词匹配
                    if query.text.lower() in str(entry.content).lower():
                        results.append(RetrievalResult(
                            entry=entry,
                            score=0.7,
                            strategy=RetrievalStrategy.KEYWORD,
                            matched_fields=["content"]
                        ))

        elif layer == MemoryType.EPISODIC and context:
            episodic = context.get("episodic")
            if episodic:
                episodes = await episodic.search_episodes(
                    query=query.text,
                    limit=query.limit
                )
                for ep in episodes:
                    entry = MemoryEntry(
                        id=ep.episode_id,
                        memory_type=MemoryType.EPISODIC,
                        content=ep.action,
                        metadata=ep.to_dict()
                    )
                    results.append(RetrievalResult(
                        entry=entry,
                        score=0.6,
                        strategy=RetrievalStrategy.TEMPORAL,
                        matched_fields=["action", "result"]
                    ))

        elif layer == MemoryType.USER_PROFILE and self.relational_store:
            prefs = self.relational_store.get_user_preferences(query.text)
            for pref in prefs:
                entry = MemoryEntry(
                    id=f"pref_{pref['user_id']}_{pref['preference_key']}",
                    memory_type=MemoryType.USER_PROFILE,
                    content=pref["preference_value"],
                    metadata=pref
                )
                results.append(RetrievalResult(
                    entry=entry,
                    score=0.8,
                    strategy=RetrievalStrategy.DIRECT,
                    matched_fields=["preference_value"]
                ))

        elif layer == MemoryType.PROCEDURAL and self.relational_store:
            procs = self.relational_store.list_procedures(limit=query.limit)
            for proc in procs:
                if query.text.lower() in proc["name"].lower() or query.text.lower() in proc["description"].lower():
                    entry = MemoryEntry(
                        id=proc["procedure_id"],
                        memory_type=MemoryType.PROCEDURAL,
                        content=proc,
                        metadata=proc
                    )
                    results.append(RetrievalResult(
                        entry=entry,
                        score=0.7 + proc["success_rate"] * 0.3,
                        strategy=RetrievalStrategy.KEYWORD,
                        matched_fields=["name", "description"]
                    ))

        return results

    async def _hybrid_retrieve(
        self,
        query: str,
        limit: int
    ) -> List[RetrievalResult]:
        """混合检索"""
        results: List[RetrievalResult] = []

        # 获取所有key
        all_keys = self.long_term_memory.vector_store.keys()

        # 执行混合搜索
        hybrid_scores = await self.hybrid_retriever.hybrid_search(
            query=query,
            doc_ids=all_keys,
            limit=limit,
            alpha=0.5
        )

        for key, score in hybrid_scores:
            if score > 0.1:
                content = await self.long_term_memory.recall(key)
                if content:
                    results.append(RetrievalResult(
                        entry=MemoryEntry(
                            id=key,
                            memory_type=MemoryType.LONG_TERM,
                            content=content
                        ),
                        score=score,
                        strategy=RetrievalStrategy.HYBRID,
                        matched_fields=["content"]
                    ))

        return results

    async def _semantic_retrieve(
        self,
        query: str,
        limit: int
    ) -> List[RetrievalResult]:
        """语义检索"""
        results: List[RetrievalResult] = []

        search_results = await self.long_term_memory.vector_store.search(query, limit=limit)

        for r in search_results:
            results.append(RetrievalResult(
                entry=MemoryEntry(
                    id=r["key"],
                    memory_type=MemoryType.LONG_TERM,
                    content=r["content"]
                ),
                score=r["similarity"],
                strategy=RetrievalStrategy.SEMANTIC,
                matched_fields=["content"]
            ))

        return results

    async def _keyword_retrieve(
        self,
        query: str,
        limit: int
    ) -> List[RetrievalResult]:
        """关键词检索"""
        results: List[RetrievalResult] = []

        search_results = await self.long_term_memory.search(query, limit=limit)

        for entry in search_results:
            results.append(RetrievalResult(
                entry=entry,
                score=0.5,  # 简单匹配给中等分数
                strategy=RetrievalStrategy.KEYWORD,
                matched_fields=["content", "tags"]
            ))

        return results

    def _fuse_results(
        self,
        results: List[RetrievalResult],
        query: RetrievalQuery
    ) -> List[RetrievalResult]:
        """融合多策略结果"""

        # 按entry id去重，保留最高分
        best_results: Dict[str, RetrievalResult] = {}

        for result in results:
            entry_id = result.entry.id
            if entry_id not in best_results or result.score > best_results[entry_id].score:
                best_results[entry_id] = result

        # 排序
        fused = list(best_results.values())
        fused.sort(key=lambda x: x.score, reverse=True)

        return fused

    def _log_retrieval(
        self,
        query: RetrievalQuery,
        results: List[RetrievalResult]
    ) -> None:
        """记录检索历史"""
        self._retrieval_history.append({
            "query": query.text,
            "query_type": query.query_type,
            "result_count": len(results),
            "top_score": results[0].score if results else 0,
            "timestamp": time.time()
        })

        # 只保留最近1000条
        if len(self._retrieval_history) > 1000:
            self._retrieval_history = self._retrieval_history[-1000:]

    def should_retrieve(
        self,
        context: Dict[str, Any],
        trigger_conditions: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        决策是否应该触发检索

        基于:
        1. 上下文长度
        2. 距离上次检索的时间
        3. 查询类型
        4. 显式触发条件

        Args:
            context: 当前上下文
            trigger_conditions: 触发条件配置

        Returns:
            (should_retrieve, reason)
        """
        conditions = trigger_conditions or {
            "min_context_length": 5,
            "min_messages_since_retrieval": 10,
            "retrieval_interval_seconds": 60
        }

        # 检查显式触发
        if context.get("force_retrieve"):
            return True, "explicit_trigger"

        # 检查上下文长度
        messages = context.get("messages", [])
        if len(messages) < conditions.get("min_context_length", 5):
            return False, "context_too_short"

        # 检查距离上次检索的时间
        last_retrieval = context.get("last_retrieval_time", 0)
        time_since = time.time() - last_retrieval
        if time_since < conditions.get("retrieval_interval_seconds", 60):
            return False, "too_soon_since_last_retrieval"

        # 检查消息数量
        messages_since = context.get("messages_since_retrieval", len(messages))
        if messages_since < conditions.get("min_messages_since_retrieval", 10):
            return False, "not_enough_messages_since_retrieval"

        # 检查查询是否相关
        recent_query = context.get("recent_query", "")
        if recent_query and self._is_exploratory_query(recent_query):
            return True, "exploratory_query_detected"

        return True, "periodic_retrieval"

    def _is_exploratory_query(self, query: str) -> bool:
        """判断是否为探索性查询"""
        exploratory_keywords = {
            "还有什么", "其他", "另外", "更多",
            "what else", "anything else", "more", "additional"
        }
        return any(kw in query.lower() for kw in exploratory_keywords)

    def get_retrieval_suggestions(self, context: Dict[str, Any]) -> List[str]:
        """
        基于上下文提供检索建议

        Args:
            context: 当前上下文

        Returns:
            建议的查询列表
        """
        suggestions = []

        # 基于最近对话
        messages = context.get("messages", [])
        if messages:
            last_msg = messages[-1].get("content", "")
            if "?" in last_msg:
                suggestions.append(last_msg)

        # 基于用户画像
        if context.get("user_preferences"):
            for key in context["user_preferences"]:
                suggestions.append(f"关于{key}的偏好")

        # 基于最近任务
        if context.get("recent_tasks"):
            for task in context["recent_tasks"][-3:]:
                suggestions.append(f"之前{task}的结果")

        return suggestions[:5]
