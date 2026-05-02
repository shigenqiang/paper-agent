# Retrieval 检索增强详解

> 位置: `src/agents_v2/retrieval/`

## 一、架构概览

```
retrieval/
├── __init__.py
├── adaptive_retrieval.py       # 自适应检索
├── hyde_retriever.py          # HyDE检索
├── cross_encoder_reranker.py  # Cross-Encoder重排
├── self_rag_controller.py     # Self-RAG控制
├── confidence_calculator.py    # 置信度计算
├── deduplicator.py            # 去重
├── document_evaluator.py      # 文档评估
├── priority_matcher.py        # 优先级匹配
├── query_classifier.py        # 查询分类
├── result_fuser.py           # 结果融合
├── retrieval_chain.py         # 检索链
├── rewrite_validator.py       # 重写验证
├── score_parser.py            # 分数解析
└── keyword_sets.py            # 关键词集合
```

## 二、检索流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Retrieval Pipeline                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  用户查询 ──► QueryClassifier ──► QueryRewriter                      │
│                        │                    │                        │
│                        ▼                    ▼                        │
│               ┌────────────────┐   ┌────────────────┐               │
│               │  HyDE检索      │   │  自适应检索     │               │
│               │ (生成假设文档)  │   │  (动态策略)     │               │
│               └────────┬───────┘   └────────┬───────┘               │
│                        │                    │                        │
│                        └──────────┬──────────┘                        │
│                                   ▼                                  │
│                          ┌────────────────┐                           │
│                          │ Cross-Encoder  │                           │
│                          │    重排        │                           │
│                          └────────┬───────┘                           │
│                                   │                                  │
│                                   ▼                                  │
│                          ┌────────────────┐                           │
│                          │  结果融合      │                           │
│                          │ (RRF/MRR)      │                           │
│                          └────────┬───────┘                           │
│                                   │                                  │
│                                   ▼                                  │
│                           检索结果 Top-K                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 三、核心组件

### 3.1 AdaptiveRetrieval

```python
class AdaptiveRetrieval:
    """自适应检索 - 根据查询类型动态选择检索策略"""

    STRATEGIES = {
        "factual": "dense",      # 事实查询 → 向量检索
        "conceptual": "hybrid",  # 概念查询 → 混合检索
        "comparative": "sparse", # 比较查询 → 稀疏检索
        "temporal": "dense",     # 时间查询 → 向量检索
    }

    def retrieve(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Document]:
        """自适应检索"""
        # 1. 分类查询
        query_type = self.classifier.classify(query)

        # 2. 选择策略
        strategy = self.STRATEGIES.get(query_type, "hybrid")

        # 3. 执行检索
        if strategy == "dense":
            return self.dense_retriever.search(query, top_k)
        elif strategy == "sparse":
            return self.sparse_retriever.search(query, top_k)
        else:
            return self.hybrid_retriever.search(query, top_k)
```

### 3.2 HyDERetriever

```python
class HyDERetriever:
    """HyDE (Hypothetical Document Embeddings) 检索"""

    async def retrieve(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Document]:
        """
        1. LLM生成假设性回答/文档
        2. 向量化假设文档
        3. 检索相似文档
        """
        # 生成假设文档
        hypothetical_doc = await self._generate_hypothetical_doc(query)

        # 向量化
        doc_vector = self.embeddings.encode(hypothetical_doc)

        # 检索
        return self.vector_store.search(doc_vector, top_k)

    async def _generate_hypothetical_doc(self, query: str) -> str:
        """生成假设性文档"""
        prompt = f"""假设你是一个专家，请针对以下问题写一篇简短的回答:
问题: {query}

请生成一个假设性的回答/文档，用于检索相关材料。"""
        return await self.llm.ainvoke([HumanMessage(prompt)])
```

### 3.3 CrossEncoderReranker

```python
class CrossEncoderReranker:
    """Cross-Encoder重排"""

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 5
    ) -> List[Document]:
        """
        使用Cross-Encoder对文档进行精细排序
        比向量检索更精确但计算更慢
        """
        # 构建query-document pairs
        pairs = [(query, doc.content) for doc in documents]

        # 计算相关性分数
        scores = self.cross_encoder.predict(pairs)

        # 按分数排序
        scored_docs = zip(documents, scores)
        sorted_docs = sorted(scored_docs, key=lambda x: x[1], reverse=True)

        return [doc for doc, score in sorted_docs[:top_k]]
```

### 3.4 SelfRAGController

```python
class SelfRAGController:
    """Self-RAG 自适应检索增强"""

    async def rag(
        self,
        query: str,
        retrievers: List[BaseRetriever]
    ) -> RAGResponse:
        """
        1. 判断是否需要检索
        2. 判断是否需要生成
        3. 评估生成质量
        """
        # 是否检索？
        need_retrieval = await self._judge_retrieval(query)

        if not need_retrieval:
            return await self._direct_generate(query)

        # 检索
        retrieved_docs = await self._parallel_retrieve(query, retrievers)

        # 是否引用？
        is_relevant = await self._check_relevance(query, retrieved_docs)

        if not is_relevant:
            return await self._direct_generate(query)

        # 生成（带引用）
        response = await self._generate_with_citation(query, retrieved_docs)

        # 评估响应
        is_grounded = await self._check_grounding(response, retrieved_docs)

        return RAGResponse(
            answer=response.answer,
            docs=retrieved_docs,
            citations=response.citations,
            grounded=is_grounded
        )
```

## 四、结果融合

### 4.1 RRF (Reciprocal Rank Fusion)

```python
class ResultFuser:
    """结果融合"""

    def rrf_fusion(
        self,
        results_list: List[List[Document]],
        k: int = 60
    ) -> List[Document]:
        """
        RRF融合 - 将多个检索结果合并排序

        公式: RRF(d) = Σ 1/(k + rank(d))

        Args:
            results_list: 多个检索结果列表
            k: 融合参数 (通常60)
        """
        scores = defaultdict(float)

        for results in results_list:
            for rank, doc in enumerate(results):
                doc_id = doc.id
                scores[doc_id] += 1 / (k + rank + 1)

        # 按分数排序
        sorted_docs = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [self.doc_store.get(doc_id) for doc_id, score in sorted_docs]
```

### 4.2 加权融合

```python
def weighted_fusion(
    results_list: List[List[Document]],
    weights: List[float]
) -> List[Document]:
    """加权融合"""
    scores = defaultdict(float)

    for results, weight in zip(results_list, weights):
        for rank, doc in enumerate(results):
            scores[doc.id] += weight * (1 / (rank + 1))

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

## 五、置信度计算

```python
class ConfidenceCalculator:
    """检索结果置信度计算"""

    def calculate(
        self,
        query: str,
        doc: Document,
        retrieval_score: float
    ) -> ConfidenceScore:
        """计算检索结果置信度"""
        # 1. 向量相似度
        vector_score = retrieval_score

        # 2. 查询-文档关键词匹配度
        keyword_score = self._keyword_overlap(query, doc)

        # 3. 文档质量分数
        quality_score = doc.quality_score

        # 4. 时效性分数
        recency_score = self._recency_score(doc)

        # 综合评分
        final_score = (
            0.4 * vector_score +
            0.2 * keyword_score +
            0.25 * quality_score +
            0.15 * recency_score
        )

        return ConfidenceScore(
            score=final_score,
            level=self._score_to_level(final_score),
            breakdown={
                "vector": vector_score,
                "keyword": keyword_score,
                "quality": quality_score,
                "recency": recency_score
            }
        )
```

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/retrieval/`
