"""Graph-First RAG混合检索器"""
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class RetrievedDocument(BaseModel):
    """检索到的文档"""
    content: str
    source_id: str
    score: float
    source_type: str  # "graph" or "vector"
    metadata: Optional[Dict[str, Any]] = None


class GraphFirstRetriever:
    """先图后向量的并行RAG策略"""

    def __init__(
        self,
        graph_retriever,
        vector_retriever,
        graph_weight: float = 0.6,
        vector_weight: float = 0.4
    ):
        self.graph_retriever = graph_retriever
        self.vector_retriever = vector_retriever
        self.graph_weight = graph_weight
        self.vector_weight = vector_weight

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        graph_top_k: int = 5,
        vector_top_k: int = 5
    ) -> List[RetrievedDocument]:
        """
        并行检索图谱和向量
        先从图谱检索1-hop子图，再从向量库扩展
        """
        logger.info(f"Starting Graph-First retrieval for query: {query}")

        # 并行检索
        graph_results, vector_results = await asyncio.gather(
            self._retrieve_from_graph(query, graph_top_k),
            self._retrieve_from_vector(query, vector_top_k)
        )

        # 融合结果
        fused_results = self._fuse_results(
            graph_results,
            vector_results,
            top_k
        )

        logger.info(f"Retrieved {len(fused_results)} documents")
        return fused_results

    async def _retrieve_from_graph(
        self,
        query: str,
        top_k: int
    ) -> List[RetrievedDocument]:
        """从图谱检索"""
        try:
            results = await self.graph_retriever.retrieve(query, top_k)
            return [
                RetrievedDocument(
                    content=r.get("content", ""),
                    source_id=r.get("id", ""),
                    score=r.get("score", 0.0),
                    source_type="graph",
                    metadata=r
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"Graph retrieval error: {e}")
            return []

    async def _retrieve_from_vector(
        self,
        query: str,
        top_k: int
    ) -> List[RetrievedDocument]:
        """从向量库检索"""
        try:
            results = await self.vector_retriever.search(query, top_k)
            return [
                RetrievedDocument(
                    content=r.get("content", ""),
                    source_id=r.get("id", ""),
                    score=r.get("score", 0.0),
                    source_type="vector",
                    metadata=r
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"Vector retrieval error: {e}")
            return []

    def _fuse_results(
        self,
        graph_results: List[RetrievedDocument],
        vector_results: List[RetrievedDocument],
        top_k: int
    ) -> List[RetrievedDocument]:
        """融合图谱和向量检索结果"""
        # 创建文档ID到结果的映射
        all_docs = {}

        # 添加图谱结果
        for doc in graph_results:
            if doc.source_id not in all_docs:
                all_docs[doc.source_id] = doc
            else:
                # 如果已存在，更新分数
                all_docs[doc.source_id].score = max(
                    all_docs[doc.source_id].score,
                    doc.score
                )

        # 添加向量结果
        for doc in vector_results:
            if doc.source_id not in all_docs:
                all_docs[doc.source_id] = doc
            else:
                # 融合分数
                existing_doc = all_docs[doc.source_id]
                if existing_doc.source_type == "graph":
                    # 图谱结果与向量结果融合
                    existing_doc.score = (
                        existing_doc.score * self.graph_weight +
                        doc.score * self.vector_weight
                    )
                    existing_doc.source_type = "hybrid"

        # 按分数排序
        sorted_docs = sorted(
            all_docs.values(),
            key=lambda x: x.score,
            reverse=True
        )

        return sorted_docs[:top_k]

    async def retrieve_with_context(
        self,
        query: str,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """检索并返回上下文信息"""
        results = await self.retrieve(query, top_k)

        # 构建上下文
        context = {
            "query": query,
            "total_results": len(results),
            "graph_results": len([r for r in results if r.source_type == "graph"]),
            "vector_results": len([r for r in results if r.source_type == "vector"]),
            "hybrid_results": len([r for r in results if r.source_type == "hybrid"]),
            "documents": [
                {
                    "content": doc.content,
                    "source_id": doc.source_id,
                    "score": doc.score,
                    "source_type": doc.source_type
                }
                for doc in results
            ]
        }

        return context
