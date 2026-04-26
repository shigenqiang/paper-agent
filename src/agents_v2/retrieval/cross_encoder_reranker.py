"""
交叉编码器重排序 - Cross-Encoder Reranker

使用交叉编码器进行精细化的两两排序，而非简单的向量相似度。
"""
import logging
from dataclasses import dataclass
from typing import Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RerankedDoc:
    """重排序后的文档"""
    doc: str
    score: float
    rank: int
    original_rank: int = 0
    metadata: dict = None


class CrossEncoderReranker:
    """Cross-Encoder重排序器

    使用交叉编码器对候选文档进行精细化的相关性排序。

    注意：这是一个基础实现，实际使用时需要加载真实的cross-encoder模型。
    可以使用 sentence-transformers 库：
        from sentence_transformers import CrossEncoder
        model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """初始化重排序器

        Args:
            model_name: 交叉编码器模型名称
        """
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        """加载交叉编码器模型"""
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
            logger.info(f"成功加载交叉编码器模型: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers未安装，使用简单的重排序实现")
            self.model = None
        except Exception as e:
            logger.error(f"加载交叉编码器模型失败: {e}")
            self.model = None

    async def rerank(self,
                    query: str,
                    candidates: List[str],
                    top_k: int = 10) -> List[RerankedDoc]:
        """对候选文档进行重排序

        Args:
            query: 查询字符串
            candidates: 候选文档列表
            top_k: 返回前k个

        Returns:
            List[RerankedDoc]: 按相关性排序的文档列表
        """
        if not candidates:
            return []

        if self.model:
            return await self._rerank_with_model(query, candidates, top_k)
        else:
            return self._rerank_simple(query, candidates, top_k)

    async def _rerank_with_model(self,
                                 query: str,
                                 candidates: List[str],
                                 top_k: int) -> List[RerankedDoc]:
        """使用交叉编码器模型进行重排序"""
        try:
            # 构造(query, doc)对
            pairs = [(query, doc) for doc in candidates]

            # 批量预测相关性分数
            scores = self.model.predict(pairs)

            # 转换为列表
            if hasattr(scores, 'tolist'):
                scores = scores.tolist()
            elif not isinstance(scores, list):
                scores = list(scores)

            # 按分数排序
            doc_scores = sorted(
                zip(candidates, scores),
                key=lambda x: x[1],
                reverse=True
            )

            # 构建结果
            reranked = []
            for idx, (doc, score) in enumerate(doc_scores[:top_k]):
                reranked.append(RerankedDoc(
                    doc=doc,
                    score=float(score),
                    rank=idx + 1,
                    original_rank=candidates.index(doc) if doc in candidates else -1,
                    metadata={"model": self.model_name}
                ))

            logger.info(f"使用模型对{len(candidates)}个文档进行重排序，返回top-{top_k}")
            return reranked

        except Exception as e:
            logger.error(f"模型重排序出错: {e}，使用简单重排序")
            return self._rerank_simple(query, candidates, top_k)

    def _rerank_simple(self, query: str, candidates: List[str], top_k: int) -> List[RerankedDoc]:
        """简单的重排序实现（无模型时使用）

        基于关键词匹配和位置信息进行简单排序。
        """
        query_terms = set(query.lower().split())
        query_terms.update(self._extract_key_phrases(query))

        doc_scores = []

        for idx, doc in enumerate(candidates):
            # 计算关键词重叠度
            doc_lower = doc.lower()
            doc_terms = set(doc_lower.split())
            doc_terms.update(self._extract_key_phrases(doc))

            # 词集合重叠
            overlap = len(query_terms & doc_terms)

            # 精确匹配分数
            exact_matches = sum(1 for term in query_terms if term in doc_lower)

            # 综合分数
            score = overlap * 0.5 + exact_matches * 1.0

            # 位置惩罚（越靠前的文档略微加分）
            position_bonus = max(0, 1.0 - (idx * 0.02))

            final_score = score + position_bonus

            doc_scores.append((doc, final_score, idx))

        # 排序
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        # 构建结果
        reranked = []
        for rank, (doc, score, original_idx) in enumerate(doc_scores[:top_k]):
            reranked.append(RerankedDoc(
                doc=doc,
                score=score,
                rank=rank + 1,
                original_rank=original_idx,
                metadata={"method": "simple_keyword_matching"}
            ))

        return reranked

    def _extract_key_phrases(self, text: str) -> set:
        """提取关键短语

        Args:
            text: 输入文本

        Returns:
            set: 关键短语集合
        """
        # 简单的n-gram提取
        words = text.lower().split()
        phrases = set()

        # 2-gram
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            phrases.add(phrase)

        # 3-gram
        for i in range(len(words) - 2):
            phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
            phrases.add(phrase)

        return phrases

    async def compute_similarity(self, query: str, document: str) -> float:
        """计算查询与单个文档的相似度

        Args:
            query: 查询字符串
            document: 文档内容

        Returns:
            float: 相似度分数
        """
        results = await self.rerank(query, [document], top_k=1)
        if results:
            return results[0].score
        return 0.0

    def get_scores_batch(self, query: str, documents: List[str]) -> List[float]:
        """批量计算相似度分数（同步版本）

        Args:
            query: 查询字符串
            documents: 文档列表

        Returns:
            List[float]: 每个文档的分数
        """
        if self.model:
            try:
                pairs = [(query, doc) for doc in documents]
                scores = self.model.predict(pairs)
                if hasattr(scores, 'tolist'):
                    return scores.tolist()
                return list(scores)
            except Exception as e:
                logger.error(f"批量评分出错: {e}")

        # 简单实现
        query_terms = set(query.lower().split())
        scores = []

        for doc in documents:
            doc_lower = doc.lower()
            doc_terms = set(doc_lower.split())
            overlap = len(query_terms & doc_terms)
            scores.append(float(overlap))

        return scores


class HybridReranker:
    """混合重排序器

    结合多种重排序策略：
    1. BM25分数
    2. 向量相似度
    3. 交叉编码器分数
    """

    def __init__(self,
                 vector_weight: float = 0.4,
                 cross_encoder_weight: float = 0.4,
                 bm25_weight: float = 0.2):
        """初始化混合重排序器

        Args:
            vector_weight: 向量相似度权重
            cross_encoder_weight: 交叉编码器权重
            bm25_weight: BM25权重
        """
        self.vector_weight = vector_weight
        self.cross_encoder_weight = cross_encoder_weight
        self.bm25_weight = bm25_weight

        self.cross_encoder = CrossEncoderReranker()

    async def rerank(self,
                     query: str,
                     candidates: List[str],
                     vector_scores: Optional[List[float]] = None,
                     bm25_scores: Optional[List[float]] = None,
                     top_k: int = 10) -> List[RerankedDoc]:
        """混合重排序

        Args:
            query: 查询字符串
            candidates: 候选文档列表
            vector_scores: 向量相似度分数（可选）
            bm25_scores: BM25分数（可选）
            top_k: 返回前k个

        Returns:
            List[RerankedDoc]: 重排序结果
        """
        if not candidates:
            return []

        n = len(candidates)

        # 归一化向量分数
        norm_vector = self._normalize_scores(vector_scores) if vector_scores else [0.5] * n

        # 获取交叉编码器分数
        cross_scores = []
        for doc in candidates:
            score = await self.cross_encoder.compute_similarity(query, doc)
            cross_scores.append(score)
        norm_cross = self._normalize_scores(cross_scores)

        # 归一化BM25分数
        norm_bm25 = self._normalize_scores(bm25_scores) if bm25_scores else [0.5] * n

        # 计算综合分数
        final_scores = []
        for i in range(n):
            combined = (
                norm_vector[i] * self.vector_weight +
                norm_cross[i] * self.cross_encoder_weight +
                norm_bm25[i] * self.bm25_weight
            )
            final_scores.append(combined)

        # 排序
        doc_scores = sorted(
            zip(candidates, final_scores),
            key=lambda x: x[1],
            reverse=True
        )

        # 构建结果
        reranked = []
        for rank, (doc, score) in enumerate(doc_scores[:top_k]):
            original_idx = candidates.index(doc) if doc in candidates else -1
            reranked.append(RerankedDoc(
                doc=doc,
                score=score,
                rank=rank + 1,
                original_rank=original_idx,
                metadata={
                    "vector_score": norm_vector[original_idx] if original_idx >= 0 else 0,
                    "cross_score": norm_cross[original_idx] if original_idx >= 0 else 0,
                    "bm25_score": norm_bm25[original_idx] if original_idx >= 0 else 0,
                    "method": "hybrid"
                }
            ))

        return reranked

    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """Min-Max归一化

        Args:
            scores: 原始分数列表

        Returns:
            List[float]: 归一化后的分数
        """
        if not scores:
            return []

        min_val = min(scores)
        max_val = max(scores)

        if max_val == min_val:
            return [0.5] * len(scores)

        return [(s - min_val) / (max_val - min_val) for s in scores]


# 便捷函数
async def rerank_documents(query: str,
                            candidates: List[str],
                            method: str = "cross_encoder",
                            top_k: int = 10) -> List[RerankedDoc]:
    """重排序文档的便捷函数

    Args:
        query: 查询字符串
        candidates: 候选文档
        method: 重排序方法 (cross_encoder/hybrid/simple)
        top_k: 返回前k个

    Returns:
        List[RerankedDoc]: 重排序结果
    """
    if method == "cross_encoder":
        reranker = CrossEncoderReranker()
    elif method == "hybrid":
        reranker = HybridReranker()
    else:
        reranker = CrossEncoderReranker()

    return await reranker.rerank(query, candidates, top_k)
