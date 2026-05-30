"""搜索结果排序 — BM25 相关性 + 多维质量评分

所有参数从 config.yaml 读取，无硬编码。
"""

from __future__ import annotations

import math
import re
from datetime import datetime

from src.agents_v3.research_workspace.config import get_search_config
from src.agents_v3.research_workspace.search.base import SearchResult

# ── 从配置加载参数 ──────────────────────────────────────

def _cfg() -> dict:
    return get_search_config()


def _source_priority() -> dict[str, float]:
    return _cfg().get("source_priority", {
        "openalex": 0.9, "semantic_scholar": 0.8, "arxiv": 0.7, "pubmed": 0.7,
    })


def _field_weights() -> dict[str, float]:
    return _cfg().get("field_weights", {
        "abstract": 3.5, "title": 2.0, "keywords": 2.0, "concepts": 1.0, "venue": 0.5,
    })


def _final_weights() -> dict[str, float]:
    return _cfg().get("final_weights", {
        "relevance": 0.55, "quality": 0.25, "source_priority": 0.20,
    })


def _bm25_params() -> tuple[float, float]:
    bm25 = _cfg().get("bm25", {})
    return bm25.get("k1", 1.5), bm25.get("b", 0.4)


def _rrf_k() -> int:
    return _cfg().get("rrf_k", 60)


# ── 分词 ──────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """分词：小写化，按非字母数字分割，保留>=2字符的词"""
    return [w for w in re.split(r"[^\w]+", text.lower()) if len(w) >= 2]


# ── BM25 ─────────────────────────────────────────────

class BM25:
    """Okapi BM25 实现"""

    def __init__(self, corpus: list[list[str]], k1: float | None = None, b: float | None = None):
        default_k1, default_b = _bm25_params()
        self.k1 = k1 if k1 is not None else default_k1
        self.b = b if b is not None else default_b
        self.corpus_size = len(corpus)
        self.avgdl = sum(len(doc) for doc in corpus) / max(self.corpus_size, 1)

        self.df: dict[str, int] = {}
        self.doc_tfs: list[dict[str, int]] = []
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
        n = self.df.get(term, 0)
        return math.log((self.corpus_size - n + 0.5) / (n + 0.5) + 1)

    def score(self, doc_idx: int, query_terms: list[str]) -> float:
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

    # 停用词列表（用于提取核心短语）
    _STOP_WORDS = frozenset({
        "a", "an", "the", "of", "for", "and", "with", "from", "based", "on",
        "using", "via", "in", "to", "about", "novel", "efficient", "new",
        "approach", "method", "methods", "framework", "model", "study",
        "research", "survey", "analysis", "system", "application",
    })

    def __init__(self, query: str = ""):
        self.query_terms = _tokenize(query) if query else []
        self._max_citations = 1
        self.query_phrase = ""
        self.core_phrases: list[str] = []
        if query:
            self._extract_phrases(query)

    def _extract_phrases(self, query: str) -> None:
        """提取查询短语和核心子短语"""
        q = query.strip().lower()
        self.query_phrase = q

        # 提取核心子短语：去掉停用词后的连续词组
        words = q.split()
        core_words = [w for w in words if w not in self._STOP_WORDS]
        if len(core_words) >= 2:
            self.core_phrases.append(" ".join(core_words))

        # 也保留原始查询中的 2-gram 和 3-gram
        for n in (3, 2):
            for i in range(len(words) - n + 1):
                gram = " ".join(words[i:i + n])
                # 跳过纯停用词 n-gram
                if not all(w in self._STOP_WORDS for w in words[i:i + n]):
                    self.core_phrases.append(gram)

    def rank(self, results: list[SearchResult], query: str = "") -> list[SearchResult]:
        """计算分数并排序"""
        if query:
            self.query_terms = _tokenize(query)
            self._extract_phrases(query)

        if not results:
            return results

        self._max_citations = max((r.citations or 0) for r in results) or 1

        query_set = set(self.query_terms)
        raw_scores = []
        for r in results:
            raw_scores.append(self._compute_relevance(r, query_set))

        max_score = max(raw_scores) if raw_scores else 1.0
        if max_score == 0:
            max_score = 1.0

        for i, r in enumerate(results):
            r.relevance_score = round(raw_scores[i] / max_score, 3)
            r.quality_score = round(self._compute_quality(r), 3)
            r.final_score = round(self._compute_final(r), 3)

        results.sort(key=lambda r: r.final_score, reverse=True)
        for i, r in enumerate(results):
            r.source_rank = i + 1

        return results

    def _compute_relevance(self, r: SearchResult, query_set: set[str]) -> float:
        """相关度 = 查询词覆盖率 × 字段加权 TF + 短语匹配加分"""
        if not query_set:
            return 0.0

        weights = _field_weights()
        field_texts = {
            "abstract": (r.abstract, weights.get("abstract", 3.5)),
            "title": (r.title, weights.get("title", 2.0)),
            "keywords": (" ".join(r.keywords), weights.get("keywords", 2.0)),
            "concepts": (" ".join(r.concepts), weights.get("concepts", 1.0)),
            "venue": (r.venue, weights.get("venue", 0.5)),
        }

        weighted_tf = 0.0
        matched_terms: set[str] = set()
        for _, (text, weight) in field_texts.items():
            if not text:
                continue
            tokens = _tokenize(text)
            for term in tokens:
                if term in query_set:
                    weighted_tf += weight
                    matched_terms.add(term)

        coverage = len(matched_terms) / len(query_set) if query_set else 0.0
        base_score = weighted_tf * coverage

        # 短语匹配加分：标题或摘要包含完整查询短语时，大幅加分
        phrase_bonus = self._phrase_match_bonus(r)
        return base_score * (1.0 + phrase_bonus)

    def _phrase_match_bonus(self, r: SearchResult) -> float:
        """短语匹配加分：标题或摘要包含完整查询短语时返回较大值"""
        if not self.query_phrase:
            return 0.0

        title = (r.title or "").lower()
        abstract = (r.abstract or "").lower()

        bonus = 0.0
        if self.query_phrase in title:
            bonus += 2.0  # 标题包含完整短语，加 200%
        if self.query_phrase in abstract:
            bonus += 1.0  # 摘要包含完整短语，加 100%

        # 也检查核心子短语（去掉停用词后的核心部分）
        for sub in self.core_phrases:
            if sub in title:
                bonus += 0.5
            elif sub in abstract:
                bonus += 0.2

        return bonus

    def _build_document(self, r: SearchResult) -> list[str]:
        """将论文各字段按权重拼接为词列表（用于 BM25）"""
        tokens: list[str] = []
        weights = _field_weights()
        field_texts = {
            "title": r.title,
            "abstract": r.abstract,
            "keywords": " ".join(r.keywords),
            "concepts": " ".join(r.concepts),
            "venue": r.venue,
        }
        for field, text in field_texts.items():
            if text:
                weight = weights.get(field, 1.0)
                repeat = max(1, round(weight))
                tokens.extend(_tokenize(text) * repeat)
        return tokens

    def _compute_quality(self, r: SearchResult) -> float:
        """质量分：引用数 75% + 引用速度 10% + 新近性 15%"""
        citation = self._citation_norm(r.citations)
        velocity = self._citation_velocity(r)
        recency = self._recency_score(r.year)
        return 0.75 * citation + 0.10 * velocity + 0.15 * recency

    def _citation_velocity(self, r: SearchResult) -> float:
        if not r.citations or r.citations <= 0:
            return 0.0
        if not r.year:
            return self._citation_norm(r.citations)
        age = max(1, datetime.now().year - r.year)
        velocity = r.citations / age
        return min(1.0, math.log(1 + velocity) / math.log(1 + self._max_citations))

    def _compute_final(self, r: SearchResult) -> float:
        """最终分 = 相关性 + 质量分 + 来源优先级"""
        fw = _final_weights()
        sp = _source_priority()
        return (
            fw.get("relevance", 0.55) * r.relevance_score
            + fw.get("quality", 0.25) * r.quality_score
            + fw.get("source_priority", 0.20) * sp.get(r.source, 0.5)
        )

    def _citation_norm(self, citations: int | None) -> float:
        if not citations or citations <= 0:
            return 0.0
        return math.sqrt(citations) / math.sqrt(self._max_citations)

    @staticmethod
    def _recency_score(year: int | None) -> float:
        if not year:
            return 0.3
        age = max(0, datetime.now().year - year)
        return math.exp(-0.08 * age)

    @staticmethod
    def _metadata_completeness(r: SearchResult) -> float:
        fields = [r.title, r.abstract, r.authors, r.doi, r.year, r.venue, r.pdf_url]
        filled = sum(1 for f in fields if f)
        return filled / len(fields)

    def rrf_fuse(self, source_rankings: list[list[SearchResult]]) -> list[SearchResult]:
        """RRF 多源融合排序"""
        rrf_scores: dict[str, float] = {}
        result_map: dict[str, SearchResult] = {}
        k = _rrf_k()

        for ranking in source_rankings:
            for rank, r in enumerate(ranking):
                key = r.result_id
                rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
                result_map[key] = r

        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        results = []
        for rid in sorted_ids:
            r = result_map[rid]
            r.final_score = rrf_scores[rid]
            results.append(r)

        return results
