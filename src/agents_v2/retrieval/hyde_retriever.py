"""
HyDE检索增强模块

HyDE (Hypothetical Document Embeddings) 是一种检索增强技术，
通过生成假设性文档来增强检索效果。

核心思想：
1. 从查询生成假设性答案/文档
2. 用假设性文档的embedding去检索
3. 与实际文档对比融合

设计原则:
- 生成假设性文档不是最终答案，是检索辅助
- 保持生成的可控性
- 与现有检索系统兼容
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HypotheticalDocument:
    """假设性文档"""
    content: str
    query: str
    confidence: float = 0.5
    generation_method: str = "llm"
    facets: List[str] = field(default_factory=list)  # 查询的不同方面


@dataclass
class HydeResult:
    """HyDE检索结果"""
    hypothetical_doc: HypotheticalDocument
    retrieved_docs: List[str]
    fused_scores: Dict[int, float]  # doc_index -> fused_score
    hyde_benefit: float = 0.0  # 相比直接检索的提升


class HypotheticalDocumentGenerator:
    """假设性文档生成器"""

    def __init__(self, llm: Any = None):
        self.llm = llm

    async def generate(
        self,
        query: str,
        generation_type: str = "answer"
    ) -> HypotheticalDocument:
        """生成假设性文档

        Args:
            query: 查询
            generation_type: 生成类型 ("answer", "document", "passage")

        Returns:
            HypotheticalDocument: 假设性文档
        """
        if not self.llm:
            # 无LLM时返回简单版本
            return self._generate_simple(query)

        try:
            if generation_type == "answer":
                content = await self._generate_answer(query)
            elif generation_type == "document":
                content = await self._generate_document(query)
            else:
                content = await self._generate_passage(query)

            return HypotheticalDocument(
                content=content,
                query=query,
                confidence=0.7,
                generation_method="llm",
                facets=self._extract_facets(content)
            )

        except Exception as e:
            logger.error(f"Hypothetical document generation failed: {e}")
            return self._generate_simple(query)

    async def _generate_answer(self, query: str) -> str:
        """生成假设性答案"""
        prompt = f"""
假设你是一个论文写作助手。请为以下查询生成一个假设性的答案。

查询：{query}

要求：
1. 生成一个可能正确的答案（即使不完全准确也没关系）
2. 答案应该包含一些具体的细节和概念
3. 长度控制在100-200字
4. 使用学术风格的表达

假设性答案：
"""
        messages = [
            # SystemMessage(content="You are a helpful assistant that generates hypothetical answers for retrieval enhancement."),
            # HumanMessage(content=prompt)
        ]
        # 使用同步方式简化
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [
            SystemMessage(content="You are a helpful assistant that generates hypothetical answers for retrieval enhancement."),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)
        return content.strip()

    async def _generate_document(self, query: str) -> str:
        """生成假设性文档（论文摘要风格）"""
        prompt = f"""
假设你是一个论文写作助手。请为以下查询生成一个假设性的论文摘要。

查询：{query}

要求：
1. 生成一个假设的论文摘要，包含背景、方法、结果和结论
2. 可以编造具体的方法名、数据集名（用于检索匹配）
3. 长度控制在150-300字
4. 使用学术风格的表达

假设性摘要：
"""
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [
            SystemMessage(content="You are a research paper writing assistant."),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)
        return content.strip()

    async def _generate_passage(self, query: str) -> str:
        """生成假设性段落"""
        prompt = f"""
请为以下查询生成一个假设性的相关段落。

查询：{query}

要求：
1. 生成一段可能相关的文本
2. 包含一些领域相关的术语和概念
3. 长度控制在100-150字

假设性段落：
"""
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)
        return content.strip()

    def _generate_simple(self, query: str) -> HypotheticalDocument:
        """生成简单版本（无LLM时使用）"""
        # 简单的启发式生成
        content = f"关于{query}的研究表明，该领域的主要方法包括以下几点。"

        return HypotheticalDocument(
            content=content,
            query=query,
            confidence=0.3,
            generation_method="simple",
            facets=[query]
        )

    def _extract_facets(self, content: str) -> List[str]:
        """提取消内容中的不同方面

        用于多角度检索
        """
        # 简单的方面提取
        facets = []

        # 检测方法相关
        method_keywords = ["方法", "method", "approach", "algorithm", "model"]
        if any(kw in content.lower() for kw in method_keywords):
            facets.append("method")

        # 检测数据集相关
        dataset_keywords = ["数据集", "dataset", "data", "experiment", "实验"]
        if any(kw in content.lower() for kw in dataset_keywords):
            facets.append("dataset")

        # 检测结果相关
        result_keywords = ["结果", "result", "performance", "accuracy", "效果"]
        if any(kw in content.lower() for kw in result_keywords):
            facets.append("result")

        return facets if facets else ["general"]


class HyDERetriever:
    """HyDE检索器

    使用假设性文档增强检索效果
    """

    def __init__(
        self,
        base_retriever: Any,
        embedder: Any = None,
        llm: Any = None
    ):
        """初始化HyDE检索器

        Args:
            base_retriever: 基础检索器
            embedder: 嵌入器（用于向量化假设性文档）
            llm: LLM（用于生成假设性文档）
        """
        self.base_retriever = base_retriever
        self.embedder = embedder
        self.generator = HypotheticalDocumentGenerator(llm)

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        use_hyde: bool = True
    ) -> List[Any]:
        """检索

        Args:
            query: 查询
            top_k: 返回数量
            use_hyde: 是否使用HyDE

        Returns:
            List: 检索结果
        """
        if not use_hyde or not self.embedder:
            # 直接检索
            return await self.base_retriever.retrieve(query, top_k)

        # HyDE增强检索
        result = await self.hyde_retrieve(query, top_k)
        return result

    async def hyde_retrieve(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Any]:
        """HyDE检索

        流程：
        1. 生成假设性文档
        2. 向量化假设性文档
        3. 检索相似文档
        4. 融合结果
        """
        # 1. 生成假设性文档
        hypothetical_doc = await self.generator.generate(query, "document")

        # 2. 向量化
        hypothetical_embedding = await self._embed(hypothetical_doc.content)

        # 3. 用假设性文档检索
        hyde_results = await self.base_retriever.retrieve(
            hypothetical_doc.content,
            top_k * 2  # 检索更多以保证融合后有足够结果
        )

        # 4. 同时用原始查询检索
        original_results = await self.base_retriever.retrieve(query, top_k * 2)

        # 5. 融合结果
        fused = self._fuse_results(
            original_results,
            hyde_results,
            hypothetical_embedding,
            top_k
        )

        return fused

    async def _embed(self, text: str) -> List[float]:
        """向量化文本

        如果没有embedder，返回简单向量
        """
        if self.embedder:
            return await self.embedder.embed(text)

        # 简单模拟：返回文本长度的哈希作为伪嵌入
        import hashlib
        embedding = [float(c) / 255.0 for c in hashlib.md5(text.encode()).digest()[:16]]
        return embedding

    def _fuse_results(
        self,
        original_results: List[Any],
        hyde_results: List[Any],
        hyde_embedding: List[float],
        top_k: int
    ) -> List[Any]:
        """融合原始检索和HyDE检索的结果

        Args:
            original_results: 原始查询检索结果
            hyde_results: 假设性文档检索结果
            hyde_embedding: 假设性文档的embedding
            top_k: 返回数量

        Returns:
            List: 融合后的结果
        """
        # 创建分数映射
        doc_scores = {}

        # 原始查询结果（权重0.6）
        for i, doc in enumerate(original_results):
            doc_id = self._get_doc_id(doc, i)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 0.6 * (1.0 / (i + 1))

        # HyDE结果（权重0.4）
        for i, doc in enumerate(hyde_results):
            doc_id = self._get_doc_id(doc, i + len(original_results))
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 0.4 * (1.0 / (i + 1))

        # 按分数排序
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        # 构建结果
        results = []
        seen_docs = set()

        for doc_id, score in sorted_docs:
            if len(results) >= top_k:
                break

            # 获取原始文档
            doc = self._get_doc_by_id(doc_id, original_results, hyde_results)
            if doc and doc_id not in seen_docs:
                results.append(doc)
                seen_docs.add(doc_id)

        return results

    def _get_doc_id(self, doc: Any, index: int) -> str:
        """获取文档ID"""
        if hasattr(doc, 'doc_id'):
            return doc.doc_id
        elif hasattr(doc, 'id'):
            return doc.id
        else:
            return f"doc_{index}"

    def _get_doc_by_id(
        self,
        doc_id: str,
        original_results: List[Any],
        hyde_results: List[Any]
    ) -> Optional[Any]:
        """根据ID获取文档"""
        all_results = original_results + hyde_results

        for doc in all_results:
            if self._get_doc_id(doc, 0) == doc_id:
                return doc

        # 简单fallback
        for doc in all_results:
            if hasattr(doc, 'content'):
                if str(hash(doc.content)) == doc_id:
                    return doc

        return None if not all_results else all_results[0]


class MultiFacetHyDE:
    """多角度HyDE

    从查询的不同角度生成多个假设性文档
    """

    def __init__(self, hyde_retriever: HyDERetriever):
        self.hyde_retriever = hyde_retriever

    async def retrieve_with_facets(
        self,
        query: str,
        facets: List[str] = None,
        top_k: int = 10
    ) -> Tuple[List[Any], Dict[str, float]]:
        """多角度检索

        Args:
            query: 查询
            facets: 查询的不同方面（如方法、数据集、结果）
            top_k: 返回数量

        Returns:
            Tuple[List[Any], Dict[str, float]]: (检索结果, 各角度的分数)
        """
        if facets is None:
            # 自动检测方面
            generator = HypotheticalDocumentGenerator()
            hypothetical = await generator.generate(query)
            facets = hypothetical.facets

        all_scores = {}
        facet_results = {}

        for facet in facets:
            # 为每个角度生成专门的假设性文档
            facet_query = f"{query} {facet}"

            # 检索
            results = await self.hyde_retriever.retrieve(facet_query, top_k)

            # 记录分数
            for i, doc in enumerate(results):
                doc_id = self.hyde_retriever._get_doc_id(doc, i)
                all_scores[doc_id] = all_scores.get(doc_id, 0) + (1.0 / (i + 1))

            facet_results[facet] = results

        # 融合所有角度的结果
        fused = self._fuse_facet_results(all_scores, top_k)

        return fused, all_scores

    def _fuse_facet_results(
        self,
        all_scores: Dict[str, float],
        top_k: int
    ) -> List[Any]:
        """融合各角度的结果"""
        sorted_items = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
        return [doc_id for doc_id, score in sorted_items[:top_k]]


# 便捷函数
async def hyde_search(
    query: str,
    retriever: Any,
    embedder: Any = None,
    llm: Any = None
) -> List[Any]:
    """HyDE检索的便捷函数

    Args:
        query: 查询
        retriever: 基础检索器
        embedder: 嵌入器
        llm: LLM

    Returns:
        List: 检索结果
    """
    hyde_retriever = HyDERetriever(retriever, embedder, llm)
    return await hyde_retriever.retrieve(query)