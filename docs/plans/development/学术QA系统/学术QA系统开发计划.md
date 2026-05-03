# 学术QA系统开发计划

> 本文档基于学术QA系统深度调研报告编写，用于指导实际开发
> 调研来源：
> - 智能问答Agent调研报告（2026年4月）
> - 学术问答系统深度调研报告（2026年5月3日，60次搜索）
>
> 开发目标：构建面向学术领域的严谨问答系统，支持引用溯源和多跳推理

---

## 目录

1. [系统架构设计](#1-系统架构设计)
2. [核心模块开发计划](#2-核心模块开发计划)
3. [严谨性保证开发计划](#3-严谨性保证开发计划)
4. [引用溯源开发计划](#4-引用溯源开发计划)
5. [多跳推理开发计划](#5-多跳推理开发计划)
6. [幻觉检测与评估开发计划](#6-幻觉检测与评估开发计划)
7. [技术选型与工具清单](#7-技术选型与工具清单)
8. [开发优先级与时间线](#8-开发优先级与时间线)
9. [关键资源链接](#9-关键资源链接)

---

## 1. 系统架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户查询输入                              │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      问题处理模块                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ 问题分类    │  │ 关键词提取  │  │ 复杂度判断   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                                ↓
                    ┌─────────────┴─────────────┐
                    ↓                           ↓
            ┌───────────────┐           ┌───────────────┐
            │  单跳问答流程  │           │  多跳问答流程  │
            └───────────────┘           └───────────────┘
                    ↓                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                      检索增强模块                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ BM25检索    │  │ 向量检索    │  │ 混合检索融合 │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                      ↓                     ↓                    │
│              ┌─────────────┐      ┌─────────────┐             │
│              │ Cross-Encoder重排 │     │ 质量评估(CRAG) │        │
│              └─────────────┘      └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      生成模块                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Self-RAG反思 │  │ 答案生成   │  │ 幻觉检测    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      引用溯源模块                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Tool Calling │  │ 引用标注   │  │ 格式规范化   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                        答案输出                                 │
│     (带引用、可追溯、含置信度的学术级答案)                        │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 数据流设计

```
文档输入
    ↓
文档解析 (PDF/Markdown/HTML)
    ↓
分块处理 (Chunking)
    ↓
元数据提取 (标题、作者、日期、页码)
    ↓
向量化与索引
    ↓
存储 (向量数据库 + 元数据数据库)

用户查询
    ↓
查询向量化
    ↓
混合检索 (BM25 + 向量)
    ↓
重排序 (Cross-Encoder)
    ↓
质量评估 (CRAG轻量级评估器)
    ↓
上下文组装
    ↓
答案生成 (LLM + Self-RAG)
    ↓
幻觉检测 (SelfCheckGPT)
    ↓
引用溯源 (CitationTracker)
    ↓
答案输出
```

### 1.3 状态管理

```python
# 学术QA系统状态定义
AcademicQAState = {
    # 对话级别
    "conversation_id": str,
    "turn_count": int,
    "history": List[Turn],
    
    # 查询级别
    "query": str,
    "query_type": str,  # "factoid" / "non-factoid" / "multi-hop"
    "complexity": str,   # "simple" / "medium" / "complex"
    
    # 检索级别
    "retrieved_docs": List[Document],
    "retrieval_quality": str,  # "high" / "medium" / "low"
    "reranked_docs": List[Document],
    
    # 生成级别
    "answer": str,
    "citations": List[Citation],
    "hallucination_score": float,
    "confidence": float,
    
    # 元信息
    "used_retrieval": bool,
    "reflection_log": List[str],
}
```

---

## 2. 核心模块开发计划

### 2.1 模块清单

| 模块 | 优先级 | 说明 |
|------|--------|------|
| 文档解析器 | P0 | PDF/Markdown/HTML解析 |
| 分块处理器 | P0 | 递归字符/语义分块 |
| 混合检索器 | P0 | BM25 + 向量 + RRF融合 |
| 重排序器 | P0 | Cross-Encoder精排 |
| 引用溯源器 | P0 | Tool Calling输出 |
| 答案生成器 | P0 | LLM生成 |
| CRAG评估器 | P1 | 检索质量评估 |
| Self-RAG | P1 | 反思机制 |
| 幻觉检测器 | P1 | SelfCheckGPT |
| 多跳推理器 | P2 | Query Decomposition |
| 置信度校准 | P2 | 多维度评估 |

### 2.2 文档解析器开发

```python
# doc_parser.py
class AcademicDocumentParser:
    """学术文档解析器"""
    
    SUPPORTED_FORMATS = ["pdf", "markdown", "html", "docx"]
    
    def __init__(self):
        self.pdf_parser = PDFPlumberParser()
        self.markdown_parser = MarkdownParser()
        self.html_parser = BeautifulSoupParser()
    
    def parse(self, file_path: str) -> Document:
        """解析学术文档"""
        ext = self._get_extension(file_path)
        
        if ext == "pdf":
            return self._parse_pdf(file_path)
        elif ext == "markdown":
            return self._parse_markdown(file_path)
        # ...
    
    def _parse_pdf(self, file_path: str) -> Document:
        """解析PDF，提取元数据"""
        # 提取标题、作者、摘要、参考文献
        text = self.pdf_parser.extract_text(file_path)
        metadata = self.pdf_parser.extract_metadata(file_path)
        sections = self.pdf_parser.extract_sections(file_path)
        
        return Document(
            content=text,
            metadata={
                "title": metadata.get("title"),
                "authors": metadata.get("authors"),
                "abstract": metadata.get("abstract"),
                "references": metadata.get("references"),
                "sections": sections,
                "file_path": file_path,
            }
        )
```

### 2.3 分块处理器开发

```python
# chunker.py
class AcademicChunker:
    """学术文档分块器"""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 100,
        split_by: str = "semantic"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.split_by = split_by
    
    def chunk(self, document: Document) -> List[Chunk]:
        """分块处理"""
        if self.split_by == "recursive":
            return self._recursive_chunk(document)
        elif self.split_by == "semantic":
            return self._semantic_chunk(document)
        elif self.split_by == "parent_child":
            return self._parent_child_chunk(document)
    
    def _semantic_chunk(self, document: Document) -> List[Chunk]:
        """语义分块 - 尊重学术文档结构"""
        chunks = []
        
        # 按章节分割
        sections = self._split_by_sections(document)
        
        for section in sections:
            # 按段落分割
            paragraphs = self._split_by_paragraphs(section)
            
            current_chunk = []
            current_tokens = 0
            
            for para in paragraphs:
                para_tokens = self._estimate_tokens(para)
                
                if current_tokens + para_tokens > self.chunk_size:
                    # 保存当前chunk
                    if current_chunk:
                        chunks.append(self._create_chunk(current_chunk, document))
                    
                    # 开始新chunk，保留overlap
                    overlap_text = current_chunk[-1][-self.chunk_overlap:] if current_chunk else ""
                    current_chunk = [overlap_text + para]
                    current_tokens = self._estimate_tokens(current_chunk)
                else:
                    current_chunk.append(para)
                    current_tokens += para_tokens
            
            # 处理最后一个chunk
            if current_chunk:
                chunks.append(self._create_chunk(current_chunk, document))
        
        return chunks
```

### 2.4 混合检索器开发

```python
# hybrid_retriever.py
class HybridRetriever:
    """混合检索器：BM25 + 向量 + RRF融合"""
    
    def __init__(
        self,
        vector_store,
        bm25_index,
        embedding_model,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ):
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.embedding_model = embedding_model
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
    
    def retrieve(
        self,
        query: str,
        top_k: int = 20
    ) -> List[RetrievedDoc]:
        """混合检索"""
        # 1. BM25检索
        bm25_results = self.bm25_index.search(query, k=top_k)
        
        # 2. 向量检索
        query_embedding = self.embedding_model.embed_query(query)
        vector_results = self.vector_store.similarity_search_by_vector(
            embedding=query_embedding,
            k=top_k
        )
        
        # 3. RRF融合
        fused_results = self._reciprocal_rank_fusion(
            bm25_results,
            vector_results,
            k=60
        )
        
        return fused_results[:top_k]
    
    def _reciprocal_rank_fusion(
        self,
        results_a: List,
        results_b: List,
        k: int = 60
    ) -> List:
        """RRF融合算法"""
        scores = {}
        
        for i, doc in enumerate(results_a):
            doc_id = doc.id
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + i + 1)
        
        for i, doc in enumerate(results_b):
            doc_id = doc.id
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + i + 1)
        
        sorted_docs = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [self._get_doc_by_id(doc_id) for doc_id in sorted_docs]
```

---

## 3. 严谨性保证开发计划

### 3.1 Self-RAG实现

```python
# self_rag.py
class SelfRAG:
    """Self-RAG 反思机制实现"""
    
    REFLECTION_TOKENS = {
        "[检索]": "需要检索外部知识",
        "[不检索]": "不需要检索，现有知识足够",
        "[相关]": "检索结果与问题相关，5分满分",
        "[不相关]": "检索结果与问题不相关",
        "[支持]": "生成内容被检索结果完全支持",
        "[部分支持]": "生成内容部分被检索结果支持",
        "[矛盾]": "生成内容与检索结果矛盾",
    }
    
    def __init__(self, llm, retriever):
        self.llm = llm
        self.retriever = retriever
    
    def reflective_generate(self, query: str) -> Dict:
        """带反思的生成"""
        # 1. 判断是否需要检索
        use_retrieval = self._should_retrieve(query)
        
        context = []
        reflection_log = []
        
        if use_retrieval:
            # 2. 检索相关文档
            retrieved_docs = self.retriever.retrieve(query, top_k=5)
            context = [doc.page_content for doc in retrieved_docs]
            
            # 3. 评估检索结果相关性
            relevance_scores = []
            for doc in retrieved_docs:
                score = self._evaluate_relevance(query, doc)
                relevance_scores.append(score)
                reflection_log.append(f"[相关] 文档{doc.id}: {score}/5")
            
            # 4. 过滤低相关文档
            if any(s < 3 for s in relevance_scores):
                retrieved_docs = self._filter_relevant_docs(
                    query, retrieved_docs, relevance_scores
                )
                context = [doc.page_content for doc in retrieved_docs]
        
        # 5. 生成答案
        answer = self._generate_with_reflection(query, context, use_retrieval)
        
        # 6. 评估生成质量
        if context:
            groundedness = self._evaluate_groundedness(answer, context)
            reflection_log.append(f"[支持] 事实支撑评估: {groundedness}/5")
        
        return {
            "answer": answer,
            "used_retrieval": use_retrieval,
            "context": context[:2] if context else [],
            "reflection_log": reflection_log,
        }
    
    def _should_retrieve(self, query: str) -> bool:
        """判断是否需要检索"""
        prompt = f"""分析以下用户问题，判断是否需要从外部知识库检索信息来回答。

问题: {query}

判断标准:
- 需要检索: 问题涉及特定事实、数据、日期、专业知识、最新研究等
- 不需要检索: 问题涉及通用常识、观点询问、主观评价等

请只输出"检索"或"不检索"，不要解释。"""
        
        response = self.llm.generate(prompt)
        return "检索" in response.strip()
    
    def _evaluate_relevance(self, query: str, doc: Document) -> int:
        """评估文档相关性 (1-5分)"""
        prompt = f"""评估以下检索结果对于回答用户问题的相关性。

用户问题: {query}

检索文档: {doc.page_content[:500]}...

评分标准 (1-5分):
- 5分: 完全相关，直接支持答案
- 4分: 高度相关，提供重要支持
- 3分: 中度相关，部分支持
- 2分: 低度相关，边际支持
- 1分: 不相关，无法支持答案

请只输出一个数字分数，不要解释。"""
        
        response = self.llm.generate(prompt)
        try:
            return int(response.strip())
        except:
            return 3
```

### 3.2 CRAG实现

```python
# crag.py
class CorrectiveRAG:
    """CRAG 纠错型检索增强生成"""
    
    class RetrievalQuality(Enum):
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"
        EMPTY = "empty"
    
    def __init__(self, llm, retriever):
        self.llm = llm
        self.retriever = retriever
        self.evaluator = RetrievalEvaluator()
    
    def query(self, query: str) -> Dict:
        """完整的CRAG查询流程"""
        # 1. 初始检索
        retrieved_docs = self.retriever.retrieve(query, top_k=10)
        
        # 2. 评估检索质量
        quality, evaluation = self._evaluate_retrieval_quality(
            query, retrieved_docs
        )
        
        # 3. 根据质量决定处理策略
        if quality == self.RetrievalQuality.HIGH:
            context = self._format_docs(retrieved_docs[:5])
            answer = self._generate_with_context(query, context)
            source = "direct_retrieval"
            
        elif quality == self.RetrievalQuality.MEDIUM:
            corrected_docs = self._correct_retrieval(
                query, retrieved_docs, evaluation
            )
            context = self._format_docs(corrected_docs[:5])
            answer = self._generate_with_context(query, context)
            source = "corrected_retrieval"
            
        elif quality == self.RetrievalQuality.LOW:
            new_docs = self._retry_retrieval(query)
            if new_docs:
                context = self._format_docs(new_docs[:5])
                answer = self._generate_with_context(query, context)
                source = "retry_retrieval"
            else:
                answer = self._fallback_when_empty(query)
                source = "fallback"
        else:
            answer = self._fallback_when_empty(query)
            source = "fallback"
        
        return {
            "answer": answer,
            "source": source,
            "quality": quality.value,
            "evaluation": evaluation
        }
    
    def _evaluate_retrieval_quality(self, query: str, retrieved_docs: List):
        """评估检索结果质量"""
        if not retrieved_docs:
            return self.RetrievalQuality.EMPTY, "未检索到任何文档"
        
        # 使用轻量级评估器分类
        category = self.evaluator.classify(query, retrieved_docs)
        
        if category == "correct":
            return self.RetrievalQuality.HIGH, "检索结果包含正确答案"
        elif category == "incorrect":
            return self.RetrievalQuality.LOW, "检索结果不包含答案"
        else:
            return self.RetrievalQuality.MEDIUM, "检索结果可能包含答案"
```

---

## 4. 引用溯源开发计划

### 4.1 引用溯源架构

```
索引阶段
    ↓
文档分块时保留元数据
├── 文档ID
├── 页码
├── 段落编号
├── 章节标题
└── 来源信息
    ↓
存储到向量数据库
    ↓
查询阶段
    ↓
检索到相关chunk
    ↓
生成答案时标注引用
    ↓
Tool Calling输出
    ↓
用户可点击查看原文
```

### 4.2 引用溯源器实现

```python
# citation_tracker.py
class CitationTracker:
    """引用溯源器"""
    
    def __init__(self, document_store):
        self.document_store = document_store
    
    def trace_generated_content(
        self,
        answer: str,
        source_documents: List[Document],
        threshold: float = 0.3
    ) -> List[Dict]:
        """追溯生成内容的来源"""
        traced_content = []
        sentences = self._split_sentences(answer)
        
        for sentence in sentences:
            if not sentence.strip():
                continue
            
            best_match = None
            best_similarity = 0
            
            for doc in source_documents:
                similarity = self._calculate_similarity(sentence, doc.page_content)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = doc
            
            traced_content.append({
                "sentence": sentence,
                "source_document": best_match,
                "source_metadata": {
                    "title": best_match.metadata.get("title") if best_match else None,
                    "authors": best_match.metadata.get("authors") if best_match else None,
                    "page": best_match.metadata.get("page") if best_match else None,
                    "chunk_id": best_match.metadata.get("chunk_id") if best_match else None,
                } if best_match else None,
                "confidence": best_similarity,
                "is_generated": best_similarity < threshold  # 纯生成内容
            })
        
        return traced_content
    
    def format_citation(self, citation: Dict, style: str = "gb7714") -> str:
        """格式化引用"""
        if style == "gb7714":
            return self._format_gb7714(citation)
        elif style == "apa":
            return self._format_apa(citation)
        else:
            return self._format_plain(citation)
    
    def _format_gb7714(self, citation: Dict) -> str:
        """GB/T 7714-2015格式"""
        metadata = citation["source_metadata"]
        if not metadata:
            return "[未知来源]"
        
        authors = metadata.get("authors", [])
        title = metadata.get("title", "未知标题")
        year = metadata.get("year", "n.d.")
        
        if authors:
            author_str = ", ".join(authors[:3])  # 只显示前3位
            if len(authors) > 3:
                author_str += " et al."
            return f"[{author_str}, {year}] {title}"
        else:
            return f"[{title}, {year}]"
```

### 4.3 Tool Calling引用输出

```python
# citation_output.py
class CitationOutput:
    """带引用的结构化输出"""
    
    TOOL_SCHEMA = {
        "name": "generate_academic_answer",
        "description": "生成学术级答案，包含可验证的引用来源",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "答案文本"
                },
                "citations": {
                    "type": "array",
                    "description": "引用列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source_id": {"type": "string"},
                            "source_title": {"type": "string"},
                            "authors": {"type": "array"},
                            "year": {"type": "integer"},
                            "page": {"type": "string"},
                            "relevance": {"type": "number"},
                            "quoted_text": {"type": "string"}
                        }
                    }
                },
                "confidence": {"type": "number"},
                "hallucination_risk": {"type": "string"}
            },
            "required": ["answer", "citations", "confidence"]
        }
    }
    
    def generate_with_citations(
        self,
        query: str,
        context: List[Document],
        llm
    ) -> Dict:
        """生成带引用的答案"""
        prompt = f"""基于以下学术文献内容回答问题。
请确保：
1. 答案准确基于提供的文献
2. 每个重要论点都标注引用来源
3. 如文献不足，明确说明

文献内容:
{self._format_context(context)}

问题: {query}

请用以下JSON格式输出答案:
{{
    "answer": "答案文本",
    "citations": [
        {{
            "source_id": "文献ID",
            "source_title": "文献标题",
            "authors": ["作者1", "作者2"],
            "year": 年份,
            "page": "页码",
            "relevance": 0.95,
            "quoted_text": "相关引用文本"
        }}
    ],
    "confidence": 0.85,
    "hallucination_risk": "low"
}}"""
        
        response = llm.generate_with_structured_output(
            prompt,
            output_schema=self.TOOL_SCHEMA
        )
        
        return response
```

---

## 5. 多跳推理开发计划

### 5.1 多跳推理流程

```
用户问题
    ↓
复杂度判断
    ↓
┌─────────────────┐
│  是否多跳问题？  │
└─────────────────┘
        ↓
    Yes → 问题分解
        ↓
    子问题1 → 检索 → 答案1
    子问题2 → 检索 → 答案2
    ...
        ↓
    答案聚合
        ↓
    最终答案 + 推理链
```

### 5.2 Query Decomposition实现

```python
# query_decomposer.py
class QueryDecomposer:
    """查询分解器 - 多跳推理支持"""
    
    def __init__(self, llm):
        self.llm = llm
    
    def decompose(self, query: str) -> List[str]:
        """将复杂问题分解为子问题"""
        decomposition_prompt = f"""将以下复杂学术问题分解为简单的子问题。
每个子问题应该能够通过单次检索直接回答。

复杂问题: {query}

要求:
1. 分解后的子问题应该覆盖原问题的各个维度
2. 每个子问题应该足够简单，可以直接回答
3. 子问题之间应该有清晰的逻辑关联
4. 使用数字列表格式输出

子问题:"""
        
        response = self.llm.generate(decomposition_prompt)
        sub_questions = self._parse_sub_questions(response)
        
        return sub_questions
    
    def should_decompose(self, query: str) -> bool:
        """判断是否需要分解"""
        complexity_indicators = [
            "为什么", "如何", "分析", "比较", "关系",
            "多少个", "哪个更重要", "从...到...",
            "对比", "区别", "联系", "原因", "结果"
        ]
        
        # 多跳关键词
        multi_hop_keywords = [
            "和...相比", "与其...不如", "先...后",
            "因为...所以", "虽然...但是",
            "谁在什么时候做了什么", "某人的观点是"
        ]
        
        score = sum(1 for ind in complexity_indicators if ind in query)
        
        # 包含多跳关键词必定需要分解
        for keyword in multi_hop_keywords:
            if keyword in query:
                return True
        
        return score >= 2
    
    def _parse_sub_questions(self, response: str) -> List[str]:
        """解析子问题"""
        lines = response.strip().split("\n")
        sub_questions = []
        
        for line in lines:
            line = line.strip()
            # 匹配数字列表格式: 1. xxx 或 1、xxx
            if line and (line[0].isdigit() or line[0] in "０１２３４５６７８９"):
                # 移除序号
                content = line.split(".", 1)[-1] if "." in line else line.split("、", 1)[-1]
                content = content.strip()
                if content:
                    sub_questions.append(content)
        
        return sub_questions
```

### 5.3 答案聚合器实现

```python
# answer_aggregator.py
class AnswerAggregator:
    """多跳答案聚合器"""
    
    def __init__(self, llm):
        self.llm = llm
    
    def aggregate(
        self,
        query: str,
        sub_questions: List[str],
        sub_answers: List[Dict]
    ) -> Dict:
        """聚合多个子答案"""
        # 1. 构建推理链
        reasoning_chain = self._build_reasoning_chain(
            query, sub_questions, sub_answers
        )
        
        # 2. 综合答案
        final_answer = self._generate_final_answer(
            query, reasoning_chain
        )
        
        # 3. 聚合引用
        all_citations = self._aggregate_citations(sub_answers)
        
        return {
            "answer": final_answer,
            "reasoning_chain": reasoning_chain,
            "citations": all_citations,
            "confidence": self._calculate_confidence(sub_answers),
            "sub_questions": sub_questions,
            "sub_answers": sub_answers
        }
    
    def _build_reasoning_chain(
        self,
        query: str,
        sub_questions: List[str],
        sub_answers: List[Dict]
    ) -> List[Dict]:
        """构建推理链"""
        chain = []
        
        for i, (q, a) in enumerate(zip(sub_questions, sub_answers)):
            chain.append({
                "step": i + 1,
                "question": q,
                "answer": a.get("answer"),
                "citations": a.get("citations", []),
                "confidence": a.get("confidence", 0)
            })
        
        return chain
```

---

## 6. 幻觉检测与评估开发计划

### 6.1 SelfCheckGPT实现

```python
# hallucination_detector.py
class HallucinationDetector:
    """幻觉检测器 - 基于SelfCheckGPT"""
    
    def __init__(self, llm, num_samples: int = 5):
        self.llm = llm
        self.num_samples = num_samples
    
    def detect_hallucination(
        self,
        question: str,
        answer: str
    ) -> Dict:
        """检测答案中的幻觉"""
        # 1. 多次采样
        sampled_answers = [
            self.llm.generate(question)
            for _ in range(self.num_samples)
        ]
        
        # 2. 提取声明
        statements = self._extract_statements(answer)
        
        # 3. 一致性检查
        consistency_scores = []
        for stmt in statements:
            support_count = sum(
                1 for ans in sampled_answers
                if self._stmt_in_answer(stmt, ans)
            )
            consistency_scores.append(support_count / self.num_samples)
        
        # 4. 计算幻觉分数
        hallucination_scores = [
            1 - score for score in consistency_scores
        ]
        
        return {
            "overall_score": sum(hallucination_scores) / len(hallucination_scores),
            "statements": [
                {
                    "text": stmt,
                    "consistency": score,
                    "hallucination_score": 1 - score,
                    "is_suspicious": score < 0.5
                }
                for stmt, score in zip(statements, consistency_scores)
            ],
            "sampled_answers": sampled_answers
        }
    
    def _extract_statements(self, text: str) -> List[str]:
        """从文本中提取声明"""
        prompt = f"""从以下文本中提取所有可验证的事实声明。
每个声明应该是一个完整的陈述句，可以被判断真伪。

文本: {text}

格式:
1. [声明1]
2. [声明2]
..."""
        
        response = self.llm.generate(prompt)
        return self._parse_statements(response)
    
    def _stmt_in_answer(self, stmt: str, answer: str) -> bool:
        """检查声明是否在答案中"""
        # 简化的语义匹配
        stmt_tokens = set(stmt.lower().split())
        answer_tokens = set(answer.lower().split())
        
        overlap = len(stmt_tokens & answer_tokens) / len(stmt_tokens)
        return overlap > 0.7
```

### 6.2 RAGAs评估集成

```python
# evaluator.py
class RAGAEvaluator:
    """RAGAs评估框架集成"""
    
    def __init__(self, llm):
        self.llm = llm
    
    def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        reference_answer: str = None
    ) -> Dict:
        """评估RAG系统质量"""
        return {
            "faithfulness": self._evaluate_faithfulness(
                question, answer, contexts
            ),
            "answer_relevance": self._evaluate_answer_relevance(
                question, answer
            ),
            "context_precision": self._evaluate_context_precision(
                question, contexts
            ),
            "context_recall": self._evaluate_context_recall(
                contexts, reference_answer
            ) if reference_answer else None
        }
    
    def _evaluate_faithfulness(
        self,
        question: str,
        answer: str,
        contexts: List[str]
    ) -> float:
        """评估忠实度"""
        statements = self._extract_statements(answer)
        
        verified_count = 0
        for stmt in statements:
            can_infer = self._can_infer_from_context(stmt, contexts)
            if can_infer:
                verified_count += 1
        
        return verified_count / len(statements) if statements else 0
    
    def _can_infer_from_context(
        self,
        statement: str,
        contexts: List[str]
    ) -> bool:
        """判断声明是否可以从上下文推断"""
        prompt = f"""判断以下声明是否可以从提供的上下文推断出来。

声明: {statement}

上下文:
{chr(10).join(contexts)}

请判断: 能推断出来 / 不能推断出来"""
        
        response = self.llm.generate(prompt)
        return "能推断出来" in response
```

---

## 7. 技术选型与工具清单

### 7.1 核心工具选型

| 类别 | 推荐工具 | 备选 |
|------|---------|------|
| **LLM底座** | Claude Opus 4.7 / DeepSeek-R1 | GPT-4o / Qwen2.5 |
| **Embedding** | BGE-M3 / OpenAI-embedding-3 | M3E / Yuan-embedding |
| **向量数据库** | Qdrant / Milvus | FAISS / Chroma |
| **重排序** | BGE-Reranker-v2-m3 | Cohere Rerank |
| **RAG框架** | LangChain / LlamaIndex | Haystack |
| **评估框架** | RAGAs / TruLens | ARES |
| **文档解析** | PDFPlumber / Marker | Unstructured |

### 7.2 配置参数速查

```python
# 学术QA系统配置
CONFIG = {
    # 检索配置
    "retrieval": {
        "embedding_model": "bge-m3",
        "chunk_size": 512,
        "chunk_overlap": 100,
        "top_k": 20,
        "rerank_top_k": 5,
        "hybrid_search": True,
        "vector_weight": 0.7,
        "keyword_weight": 0.3,
        "rrf_k": 60
    },
    
    # 生成配置
    "generation": {
        "model": "claude-opus-4.7",
        "temperature": 0.3,
        "max_tokens": 2000
    },
    
    # 严谨性配置
    "strictness": {
        "self_rag_enabled": True,
        "crag_enabled": True,
        "quality_threshold": 0.5,
        "relevance_threshold": 3  # Self-RAG最低相关性评分
    },
    
    # 引用配置
    "citation": {
        "enabled": True,
        "style": "gb7714",  # 或 "apa"
        "min_relevance": 0.7
    },
    
    # 幻觉检测配置
    "hallucination": {
        "enabled": True,
        "selfcheck_samples": 5,
        "suspicious_threshold": 0.5
    },
    
    # 多跳推理配置
    "multi_hop": {
        "enabled": True,
        "decomposition_threshold": 2,
        "max_sub_questions": 5
    },
    
    # 置信度配置
    "confidence": {
        "enabled": True,
        "calibration_weights": {
            "retrieval_relevance": 0.25,
            "answer_completeness": 0.15,
            "internal_consistency": 0.15,
            "groundedness": 0.30,
            "uncertainty_expression": 0.15
        }
    }
}
```

---

## 8. 开发优先级与时间线

### 8.1 第一阶段：核心功能（P0）

| 任务 | 优先级 | 预计工时 |
|------|--------|---------|
| 文档解析器 | P0 | 2天 |
| 分块处理器 | P0 | 1天 |
| 混合检索器 | P0 | 2天 |
| 重排序器 | P0 | 1天 |
| 基础RAG生成 | P0 | 2天 |
| 引用溯源 | P0 | 2天 |

### 8.2 第二阶段：严谨性增强（P1）

| 任务 | 优先级 | 预计工时 |
|------|--------|---------|
| CRAG评估器 | P1 | 2天 |
| Self-RAG | P1 | 3天 |
| 幻觉检测 | P1 | 2天 |
| 置信度校准 | P1 | 2天 |

### 8.3 第三阶段：高级功能（P2）

| 任务 | 优先级 | 预计工时 |
|------|--------|---------|
| Query Decomposition | P2 | 3天 |
| 多跳推理 | P2 | 3天 |
| RAGAs评估集成 | P2 | 2天 |
| 答案聚合 | P2 | 2天 |

### 8.4 总工时估算

| 阶段 | 优先级 | 预计工时 |
|------|--------|---------|
| 第一阶段 | P0 | 10天 |
| 第二阶段 | P1 | 9天 |
| 第三阶段 | P2 | 10天 |
| **总计** | - | **29天** |

---

## 9. 关键资源链接

### 开源项目

| 项目 | 链接 | 说明 |
|------|------|------|
| Self-RAG | https://github.com/AkariAsai/self-rag | 反思机制RAG |
| MultiHopKG | https://github.com/salesforce/MultiHopKG | 多跳推理框架 |
| GraphRAG | https://github.com/microsoft/GraphRAG | 微软知识图谱RAG |
| RAGAs | https://github.com/explodinggradients/ragas | RAG评估框架 |
| TruLens | https://github.com/truera/trulens | RAG三元组评估 |
| Haystack | https://github.com/deepset-ai/haystack | 端到端NLP框架 |

### 论文文献

| 论文 | 会议 | 说明 |
|------|------|------|
| Self-RAG | ICLR 2024 | 反思令牌RAG |
| CRAG | arXiv 2024 | 纠错型RAG |
| Semantic Entropy | Nature 2024 | 语义熵幻觉检测 |
| G-Retriever | NeurIPS 2024 | 图检索增强 |

### 文档资料

| 资源 | 链接 |
|------|------|
| RAGAs文档 | https://docs.ragas.io/ |
| LangChain文档 | https://python.langchain.com |
| Claude API文档 | https://docs.anthropic.com/ |

---

*本开发计划基于学术QA系统深度调研报告编写*
*最后更新：2026年5月3日*
