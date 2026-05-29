"""搜索结果排序 — BM25 相关性 + 多维质量评分"""

from __future__ import annotations

import math
import re
from datetime import datetime

from src.agents_v3.research_workspace.search.base import SearchResult

# ── 常量 ──────────────────────────────────────────────

_SOURCE_PRIORITY = {
    "openalex": 0.9,
    "semantic_scholar": 0.8,
    "arxiv": 0.7,
    "pubmed": 0.7,
}

# BM25 参数（针对学术短文本调优）
_BM25_K1 = 1.5   # 词频饱和度
_BM25_B = 0.4    # 文档长度归一化（学术摘要较短，用较小值）

# 字段权重（用于拼接文档）
_FIELD_WEIGHTS = {
    "title": 3.0,
    "abstract": 1.5,
    "keywords": 2.0,
    "concepts": 1.0,
    "venue": 0.5,
}

# 最终权重（质量优先，适合"挑好论文"场景）
_FINAL_WEIGHTS = {
    "relevance": 0.35,
    "quality": 0.50,
    "source_priority": 0.15,
}

_RRF_K = 60


# ── 分词 ──────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """分词：小写化，按非字母数字分割，保留>=2字符的词"""
    return [w for w in re.split(r"[^\w]+", text.lower()) if len(w) >= 2]


# ── BM25 ─────────────────────────────────────────────

class BM25:
    """Okapi BM25 实现"""

    def __init__(self, corpus: list[list[str]], k1: float = _BM25_K1, b: float = _BM25_B):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.avgdl = sum(len(doc) for doc in corpus) / max(self.corpus_size, 1)

        # 文档频率：每个词出现在多少文档中
        self.df: dict[str, int] = {}
        # 每篇文档的词频
        self.doc_tfs: list[dict[str, int]] = []
        # 每篇文档的长度
        self.doc_lens: list[int] = []

        for doc in corpus:
            tf: dict[str, int] = {}
            for term in doc:
                tf[term] = tf.get(term, 0) + 1
            self.doc_tfs.append(tf)
            self.doc_lens.append(len(doc))
            for term in set(doc):
                self.df[term] = self.df.get(term, 0) + 1

    def idf(self, term: str) -> float:
        """Robertson-Sparck Jones IDF"""
        n = self.df.get(term, 0)
        return math.log((self.corpus_size - n + 0.5) / (n + 0.5) + 1)

    def score(self, doc_idx: int, query_terms: list[str]) -> float:
        """计算单篇文档对查询的 BM25 分数"""
        tf = self.doc_tfs[doc_idx]
        dl = self.doc_lens[doc_idx]
        score = 0.0
        for qt in query_terms:
            f = tf.get(qt, 0)
            if f == 0:
                continue
            idf = self.idf(qt)
            numerator = f * (self.k1 + 1)
            denominator = f + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1))
            score += idf * numerator / denominator
        return score


# ── 排序服务 ──────────────────────────────────────────

class RankingService:
    """搜索结果排序服务"""

    def __init__(self, query: str = ""):
        self.query_terms = _tokenize(query) if query else []
        self._max_citations = 1

    def rank(self, results: list[SearchResult], query: str = "") -> list[SearchResult]:
        """计算分数并排序"""
        if query:
            self.query_terms = _tokenize(query)

        if not results:
            return results

        # 预计算引用数百分位（用于更好的区分度）
        self._max_citations = max((r.citations or 0) for r in results) or 1
        self._citation_percentiles = self._compute_citation_percentiles(results)

        # 构建 BM25 语料（将各字段按权重拼接为词列表）
        corpus = [self._build_document(r) for r in results]
        bm25 = BM25(corpus)

        # 计算 BM25 原始分数
        raw_scores = []
        for i, r in enumerate(results):
            raw_scores.append(bm25.score(i, self.query_terms))

        # 归一化 BM25 分数到 [0, 1]
        max_score = max(raw_scores) if raw_scores else 1.0
        if max_score == 0:
            max_score = 1.0

        for i, r in enumerate(results):
            bm25_norm = raw_scores[i] / max_score
            r.relevance_score = round(bm25_norm, 3)
            r.quality_score = round(self._compute_quality(r), 3)
            r.final_score = round(self._compute_final(r), 3)

        results.sort(key=lambda r: r.final_score, reverse=True)
        for i, r in enumerate(results):
            r.source_rank = i + 1

        return results

    def _build_document(self, r: SearchResult) -> list[str]:
        """将论文各字段按权重拼接为词列表（用于 BM25）"""
        tokens: list[str] = []
        field_texts = {
            "title": r.title,
            "abstract": r.abstract,
            "keywords": " ".join(r.keywords),
            "concepts": " ".join(r.concepts),
            "venue": r.venue,
        }
        for field, text in field_texts.items():
            if text:
                weight = _FIELD_WEIGHTS[field]
                # 按权重重复 tokens（整数倍）
                repeat = max(1, int(weight))
                tokens.extend(_tokenize(text) * repeat)
        return tokens

    def _compute_quality(self, r: SearchResult) -> float:
        """质量分：引用数 75% + 引用速度 10% + 新近性 15%

        引用数：学术影响力核心指标，百分位归一化
        引用速度：年均引用数，微调
        新近性：微调，避免完全忽略新论文
        """
        citation = self._citation_norm(r.citations)
        velocity = self._citation_velocity(r)
        recency = self._recency_score(r.year)

        return (
            0.75 * citation
            + 0.10 * velocity
            + 0.15 * recency
        )

    def _citation_velocity(self, r: SearchResult) -> float:
        """引用速度：年均引用数，归一化到 [0, 1]"""
        if not r.citations or r.citations <= 0:
            return 0.0
        if not r.year:
            return self._citation_norm(r.citations)
        age = max(1, datetime.now().year - r.year)
        velocity = r.citations / age
        # 用 log 压缩，限制在 [0, 1]
        return min(1.0, math.log(1 + velocity) / math.log(1 + self._max_citations))

    def _compute_final(self, r: SearchResult) -> float:
        """最终分 = 相关性 + 质量分 + 来源优先级"""
        return (
            _FINAL_WEIGHTS["relevance"] * r.relevance_score
            + _FINAL_WEIGHTS["quality"] * r.quality_score
            + _FINAL_WEIGHTS["source_priority"] * _SOURCE_PRIORITY.get(r.source, 0.5)
        )

    def _citation_norm(self, citations: int | None) -> float:
        """引用数归一化（平方根，高引用论文区分度更好）"""
        if not citations or citations <= 0:
            return 0.0
        return math.sqrt(citations) / math.sqrt(self._max_citations)

    @staticmethod
    def _compute_citation_percentiles(results: list[SearchResult]) -> dict[int, float]:
        """计算引用数的百分位排名，返回 {citations: percentile} 映射"""
        citation_values = sorted(set(r.citations or 0 for r in results))
        n = len(citation_values)
        if n <= 1:
            return {citation_values[0]: 1.0} if n == 1 else {}
        percentile_map = {}
        for i, val in enumerate(citation_values):
            percentile_map[val] = i / (n - 1)
        return percentile_map

    @staticmethod
    def _recency_score(year: int | None) -> float:
        """新近性：指数衰减 e^(-0.08 * age)，对经典论文更宽容"""
        if not year:
            return 0.3
        age = max(0, datetime.now().year - year)
        return math.exp(-0.08 * age)

    @staticmethod
    def _metadata_completeness(r: SearchResult) -> float:
        """元数据完整度"""
        fields = [r.title, r.abstract, r.authors, r.doi, r.year, r.venue, r.pdf_url]
        filled = sum(1 for f in fields if f)
        return filled / len(fields)

    def rrf_fuse(self, source_rankings: list[list[SearchResult]]) -> list[SearchResult]:
        """RRF 多源融合排序"""
        rrf_scores: dict[str, float] = {}
        result_map: dict[str, SearchResult] = {}

        for ranking in source_rankings:
            for rank, r in enumerate(ranking):
                key = r.result_id
                rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (_RRF_K + rank + 1)
                result_map[key] = r

        sorted_ids = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
        results = []
        for rid in sorted_ids:
            r = result_map[rid]
            r.final_score = rrf_scores[rid]
            results.append(r)

        return results
