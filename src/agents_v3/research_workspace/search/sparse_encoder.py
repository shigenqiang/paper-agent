"""TF-IDF 稀疏向量编码器

将文本编码为稀疏向量 {index: weight}，用于 Qdrant sparse vector 存储和检索。
"""

from __future__ import annotations

from loguru import logger


class SparseEncoder:
    """TF-IDF 稀疏向量编码器"""

    def __init__(self, max_features: int = 10000):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            sublinear_tf=True,  # 1 + log(tf)，类似 BM25 的词频饱和
            norm="l2",
            token_pattern=r"(?u)\b\w[\w-]{1,}\b",  # 至少2字符的词
        )
        self._fitted = False

    def fit(self, corpus: list[str]) -> None:
        """用语料库训练 TF-IDF"""
        if not corpus:
            return
        self.vectorizer.fit(corpus)
        self._fitted = True
        vocab_size = len(self.vectorizer.vocabulary_)
        logger.info(f"SparseEncoder fitted: vocab_size={vocab_size}")

    def encode(self, text: str) -> dict[int, float]:
        """编码单条文本为稀疏向量 {index: weight}"""
        if not self._fitted:
            raise RuntimeError("SparseEncoder not fitted. Call fit() first.")
        vec = self.vectorizer.transform([text])
        indices = vec.indices.tolist()
        values = vec.data.tolist()
        return dict(zip(indices, values))

    def encode_batch(self, texts: list[str]) -> list[dict[int, float]]:
        """批量编码为稀疏向量列表"""
        if not self._fitted:
            raise RuntimeError("SparseEncoder not fitted. Call fit() first.")
        if not texts:
            return []
        vecs = self.vectorizer.transform(texts)
        result = []
        for i in range(vecs.shape[0]):
            row = vecs[i]
            indices = row.indices.tolist()
            values = row.data.tolist()
            result.append(dict(zip(indices, values)))
        return result

    def fit_encode(self, corpus: list[str]) -> list[dict[int, float]]:
        """fit + encode batch，一步完成"""
        self.fit(corpus)
        return self.encode_batch(corpus)

    def encode_query(self, query: str) -> dict[int, float]:
        """编码查询文本（等同于 encode，保持 API 对称）"""
        return self.encode(query)
