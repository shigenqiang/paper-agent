"""
混合检索器 - Hybrid Retriever

支持 BM25 + 向量检索 + RRF 融合的混合检索。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.agents_v2.logging_config import get_logging_logger

import asyncio

logger = get_logging_logger(__name__)


@dataclass
class RetrievalResult:
    """检索结果"""
    chunk_id: str
    content: str
    score: float
    rank: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""  # "bm25", "vector", "rrf"


class HybridRetriever:
    """混合检索器

    结合 BM25 关键词检索和向量语义检索，
    使用 RRF (Reciprocal Rank Fusion) 进行结果融合。
    """

    def __init__(
        self,
        vector_store: Optional[Any] = None,
        bm25_index: Optional[Any] = None,
        embedding_model: Optional[Any] = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        rrf_k: int = 60,
    ):
        """初始化混合检索器

        Args:
            vector_store: 向量数据库实例（如 Qdrant, Milvus）
            bm25_index: BM25 索引实例（如 rank_bm25）
            embedding_model: Embedding 模型
            vector_weight: 向量检索权重
            keyword_weight: BM25 权重
            rrf_k: RRF 融合参数
        """
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.embedding_model = embedding_model
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.rrf_k = rrf_k

    async def retrieve(
        self,
        query: str,
        top_k: int = 20,
        rerank: bool = True,
    ) -> List[RetrievalResult]:
        """混合检索

        Args:
            query: 查询字符串
            top_k: 返回前k个结果
            rerank: 是否使用 RRF 融合

        Returns:
            List[RetrievalResult]: 按相关性排序的检索结果
        """
        bm25_results = []
        vector_results = []

        # BM25 检索
        if self.bm25_index:
            bm25_results = await self._bm25_search(query, top_k)

        # 向量检索
        if self.vector_store and self.embedding_model:
            vector_results = await self._vector_search(query, top_k)

        # 如果只有一个检索器有结果，直接返回
        if not bm25_results and not vector_results:
            logger.warning("No retrieval results from any source")
            return []

        if not bm25_results:
            return vector_results[:top_k]
        if not vector_results:
            return bm25_results[:top_k]

        # RRF 融合
        if rerank:
            fused = self._rrf_fusion(bm25_results, vector_results)
            return fused[:top_k]
        else:
            # 简单加权
            return self._weighted_fusion(bm25_results, vector_results)[:top_k]

    async def _bm25_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """BM25 检索"""
        try:
            if hasattr(self.bm25_index, 'search'):
                results = self.bm25_index.search(query, k=top_k)
            elif hasattr(self.bm25_index, 'get_scores'):
                scores = self.bm25_index.get_scores(query)
                # 排序取前k
                doc_ids = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
                results = []
                for i, doc_id in enumerate(doc_ids):
                    results.append(RetrievalResult(
                        chunk_id=str(doc_id),
                        content=f"Document {doc_id}",
                        score=float(scores[doc_id]),
                        rank=i + 1,
                        source="bm25"
                    ))
            else:
                results = []

            # 标注来源
            for r in results:
                r.source = "bm25"
            return results

        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []

    async def _vector_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """向量检索"""
        try:
            # 获取查询向量
            if hasattr(self.embedding_model, 'embed_query'):
                query_embedding = await self.embedding_model.embed_query(query)
            elif hasattr(self.embedding_model, 'encode'):
                query_embedding = self.embedding_model.encode(query)
            else:
                logger.error("Embedding model has no embed_query or encode method")
                return []

            # 向量数据库搜索
            if hasattr(self.vector_store, 'similarity_search_by_vector'):
                docs = self.vector_store.similarity_search_by_vector(
                    embedding=query_embedding,
                    k=top_k
                )
                results = []
                for i, doc in enumerate(docs):
                    results.append(RetrievalResult(
                        chunk_id=doc.get("id", doc.get("chunk_id", str(i))),
                        content=doc.get("content", doc.get("page_content", str(doc))),
                        score=doc.get("score", 0.0),
                        rank=i + 1,
                        metadata=doc.get("metadata", {}),
                        source="vector"
                    ))
                return results
            else:
                logger.error("Vector store has no similarity_search_by_vector method")
                return []

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def _rrf_fusion(
        self,
        results_a: List[RetrievalResult],
        results_b: List[RetrievalResult],
        k: int = 60,
    ) -> List[RetrievalResult]:
        """RRF (Reciprocal Rank Fusion) 融合

        RRF 是一种无参数的结果融合方法，通过排名倒数来融合多个结果集。
        公式: score(d) = Σ(1 / (k + rank(d)))

        Args:
            results_a: BM25 结果
            results_b: 向量结果
            k: RRF 参数，通常设为 60

        Returns:
            List[RetrievalResult]: 融合后的结果
        """
        # 构建 ID 到结果映射
        id_to_result = {}

        # 处理结果 A (BM25)
        for r in results_a:
            r.source = "bm25"
            id_to_result[r.chunk_id] = r

        # 处理结果 B (Vector)
        for r in results_b:
            r.source = "vector"
            if r.chunk_id in id_to_result:
                # 合并分数
                existing = id_to_result[r.chunk_id]
                # 记录两个来源的分数
                existing.metadata["bm25_score"] = existing.score
                existing.metadata["vector_score"] = r.score
                existing.source = "rrf"
            else:
                r.source = "vector"
                id_to_result[r.chunk_id] = r

        # 计算 RRF 分数
        rrf_scores = {}

        # BM25 排名
        for rank, result in enumerate(results_a):
            doc_id = result.chunk_id
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank + 1)

        # Vector 排名
        for rank, result in enumerate(results_b):
            doc_id = result.chunk_id
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank + 1)

        # 按 RRF 分数排序
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # 构建最终结果
        final_results = []
        for rank, doc_id in enumerate(sorted_ids):
            result = id_to_result[doc_id]
            result.score = rrf_scores[doc_id]
            result.rank = rank + 1
            final_results.append(result)

        logger.info(f"RRF fusion: {len(results_a)} bm25 + {len(results_b)} vector -> {len(final_results)} results")
        return final_results

    def _weighted_fusion(
        self,
        results_a: List[RetrievalResult],
        results_b: List[RetrievalResult],
    ) -> List[RetrievalResult]:
        """加权融合

        直接按权重加权分数。
        """
        # 获取所有文档的归一化分数
        all_ids = set(r.chunk_id for r in results_a) | set(r.chunk_id for r in results_b)

        max_a = max((r.score for r in results_a), default=1.0)
        max_b = max((r.score for r in results_b), default=1.0)

        weighted_scores = {}

        for r in results_a:
            normalized = r.score / max_a
            weighted_scores[r.chunk_id] = (
                weighted_scores.get(r.chunk_id, 0) + normalized * self.keyword_weight
            )

        for r in results_b:
            normalized = r.score / max_b
            weighted_scores[r.chunk_id] = (
                weighted_scores.get(r.chunk_id, 0) + normalized * self.vector_weight
            )

        # 排序
        sorted_ids = sorted(weighted_scores.keys(), key=lambda x: weighted_scores[x], reverse=True)

        final_results = []
        for rank, doc_id in enumerate(sorted_ids):
            result = results_a[0].__class__(
                chunk_id=doc_id,
                content="",  # 需要从原始结果获取
                score=weighted_scores[doc_id],
                rank=rank + 1,
                source="weighted_fusion"
            )
            final_results.append(result)

        return final_results

    async def index_documents(
        self,
        documents: List[Dict[str, Any]],
        chunk_size: int = 512,
        chunk_overlap: int = 100,
    ) -> Dict[str, Any]:
        """索引文档到向量存储

        Args:
            documents: 文档列表，每项需包含 content 字段
            chunk_size: 块大小
            chunk_overlap: 块重叠大小

        Returns:
            Dict[str, Any]: 索引结果
        """
        if not self.vector_store:
            logger.error("No vector store configured")
            return {"num_documents": 0, "num_chunks": 0, "chunks": []}

        if not self.embedding_model:
            logger.error("No embedding model configured")
            return {"num_documents": 0, "num_chunks": 0, "chunks": []}

        from .chunker import AcademicChunker
        chunker = AcademicChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        all_chunks = []
        indexed_count = 0

        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            # 分块
            chunks = chunker.chunk(content, metadata)

            for chunk in chunks:
                # 生成embedding
                if hasattr(self.embedding_model, 'get_embedding'):
                    vector = self.embedding_model.get_embedding(chunk.content)
                elif hasattr(self.embedding_model, 'encode'):
                    vectors = self.embedding_model.encode([chunk.content])
                    vector = vectors[0] if vectors else None
                else:
                    logger.error("Embedding model has no get_embedding or encode method")
                    continue

                if vector is None:
                    continue

                # 存储到向量库（确保ID唯一）
                chunk_id = f"doc_{indexed_count}_chunk_{len(all_chunks)}"
                self.vector_store.upsert(
                    id=chunk_id,
                    vector=vector,
                    payload={
                        "content": chunk.content,
                        "metadata": chunk.metadata,
                    }
                )

                all_chunks.append({
                    "chunk_id": chunk_id,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                })
                indexed_count += 1

        logger.info(f"Indexed {len(documents)} documents into {len(all_chunks)} chunks")

        return {
            "num_documents": len(documents),
            "num_chunks": len(all_chunks),
            "chunks": all_chunks,
        }


class BM25Index:
    """简单的 BM25 索引实现

    如果没有外部 BM25 库，使用这个内置实现。
    """

    def __init__(self, documents: List[str], k1: float = 1.5, b: float = 0.75):
        """初始化 BM25 索引

        Args:
            documents: 文档列表
            k1: BM25 参数
            b: BM25 参数
        """
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.avgdl = sum(len(d.split()) for d in documents) / len(documents) if documents else 0
        self.doc_lengths = [len(d.split()) for d in documents]
        self.doc_freqs = {}
        self.idf = {}

        self._build_index()

    def _build_index(self):
        """构建索引"""
        # 统计词频和文档频率
        for doc in self.documents:
            words = set(doc.lower().split())
            for word in words:
                if word not in self.doc_freqs:
                    self.doc_freqs[word] = 0
                self.doc_freqs[word] += 1

        # 计算 IDF
        N = len(self.documents)
        for word, df in self.doc_freqs.items():
            self.idf[word] = (N - df + 0.5) / (df + 0.5)

    def search(self, query: str, k: int = 10) -> List[RetrievalResult]:
        """搜索

        Args:
            query: 查询字符串
            k: 返回数量

        Returns:
            List[RetrievalResult]: 搜索结果
        """
        query_words = query.lower().split()
        scores = []

        for i, doc in enumerate(self.documents):
            score = self._calculate_score(doc, query_words)
            scores.append((i, score))

        # 排序
        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for rank, (doc_id, score) in enumerate(scores[:k]):
            results.append(RetrievalResult(
                chunk_id=f"doc_{doc_id}",
                content=self.documents[doc_id],
                score=score,
                rank=rank + 1,
                source="bm25"
            ))

        return results

    def _calculate_score(self, doc: str, query_words: List[str]) -> float:
        """计算 BM25 分数"""
        doc_words = doc.lower().split()
        doc_len = len(doc_words)
        word_freqs = {}

        for word in doc_words:
            if word not in word_freqs:
                word_freqs[word] = 0
            word_freqs[word] += 1

        score = 0.0
        for word in query_words:
            if word in word_freqs:
                freq = word_freqs[word]
                idf = self.idf.get(word, 0)
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                score += idf * numerator / denominator

        return score


# 便捷函数
async def hybrid_retrieve(
    query: str,
    documents: List[str],
    top_k: int = 20,
    **kwargs
) -> List[RetrievalResult]:
    """混合检索的便捷函数"""
    # 创建 BM25 索引
    bm25 = BM25Index(documents)

    retriever = HybridRetriever(bm25_index=bm25, **kwargs)
    return await retriever.retrieve(query, top_k)