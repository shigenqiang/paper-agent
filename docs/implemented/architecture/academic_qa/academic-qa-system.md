# 学术QA系统 - Academic QA System

> 面向学术领域的严谨问答系统，支持引用溯源和多跳推理。

## 目录

1. [系统概述](#系统概述)
2. [架构设计](#架构设计)
3. [核心模块](#核心模块)
4. [API接口](#api接口)
5. [使用示例](#使用示例)

---

## 系统概述

学术QA系统是一个面向学术领域的严谨问答系统，具备以下核心能力：

- **多跳推理**：支持复杂问题的分解与推理链构建
- **引用溯源**：精确追踪答案的事实来源
- **幻觉检测**：基于SelfCheckGPT的幻觉检测机制
- **置信度校准**：多维度置信度评估
- **CRAG纠错**：检索质量评估与自动纠错
- **Self-RAG**：反思机制提升答案质量
- **RAGAs评估**：标准化的RAG系统评估

### 系统位置

```
src/agents_v2/academic_qa/
├── __init__.py          # 模块导出
├── system.py            # 统一系统入口
├── kg_integration.py    # 知识图谱集成
├── doc_parser.py        # 文档解析器
├── chunker.py           # 学术文档分块器
├── hybrid_retriever.py  # 混合检索器
├── citation_tracker.py  # 引用溯源器
├── answer_generator.py  # 答案生成器
├── crag.py              # CRAG评估器
├── self_rag.py          # Self-RAG控制器
├── hallucination_detector.py  # 幻觉检测器
├── confidence_calibrator.py  # 置信度校准器
├── query_decomposer.py   # 查询分解器
├── multi_hop_reasoner.py # 多跳推理器
├── ragas_evaluator.py   # RAGAs评估器
└── answer_aggregator.py # 答案聚合器

模块清单 (16个模块文件):
- DocumentParser: 文档解析器
- AcademicChunker: 学术文档分块器
- HybridRetriever: 混合检索器 (BM25 + 向量 + RRF)
- CitationTracker: 引用溯源器
- AnswerGenerator: 答案生成器
- CRAGEvaluator: CRAG 纠错型检索评估
- SelfRAGController: Self-RAG 反思机制
- HallucinationDetector: 幻觉检测器
- ConfidenceCalibrator: 置信度校准器
- QueryDecomposer: 查询分解器（多跳推理）
- MultiHopReasoner: 多跳推理器
- RAGAsEvaluator: RAGAs 评估框架
- AnswerAggregator: 答案聚合器
- kg_integration: 知识图谱集成模块
  - KGRetrieverWrapper: 知识图谱检索包装器
  - KGAnswerEnricher: 知识图谱答案增强器
  - KGMultiHopReasoner: 图谱多跳推理器
  - AcademicQAKGIntegration: 知识图谱集成系统
```

---

## 架构设计

### 整体架构

```
用户查询
    ↓
┌─────────────────────────────────────────────────────────────┐
│                    AcademicQASystem                          │
│                   (统一系统入口)                              │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│              问题复杂度判断 (_is_multi_hop)                   │
└─────────────────────────────────────────────────────────────┘
         ↓                    ↓
    ┌─────────┐          ┌─────────┐
    │ 单跳模式 │          │ 多跳模式 │
    └─────────┘          └─────────┘
         ↓                    ↓
┌─────────────────────────────────────────────────────────────┐
│                    检索增强模块                              │
│  HybridRetriever (BM25 + 向量 + RRF融合)                     │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│                   Self-RAG 反思生成                          │
│  - 判断是否需要检索                                          │
│  - 评估检索结果相关性                                         │
│  - 生成带反思的答案                                          │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│                   严格性增强模块                              │
│  - CRAG 检索质量评估                                         │
│  - 幻觉检测 (SelfCheckGPT)                                   │
│  - 置信度校准                                               │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│                   引用溯源模块                               │
│  CitationTracker - 追踪答案的事实来源                        │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│                   答案输出                                   │
│  AcademicQAResult - 含引用、置信度、幻觉分数                   │
└─────────────────────────────────────────────────────────────┘
```

### 数据流

```
输入: query, documents (可选), contexts (可选), mode

1. 复杂度判断
   query → _is_multi_hop() → is_multi_hop ∈ {True, False}

2a. 单跳模式
    _single_hop_answer()
    ├── HybridRetriever.retrieve()
    ├── SelfRAGController.reflective_generate()
    ├── AnswerGenerator.generate()
    └── CitationTracker.trace_content()

2b. 多跳模式
    _multi_hop_answer()
    ├── QueryDecomposer.decompose()
    ├── MultiHopReasoner.reason()
    └── AnswerAggregator.aggregate()

3. 严格性增强 (mode="strict")
    _apply_crag() → CRAGEvaluator.evaluate()

4. 幻觉检测
    HallucinationDetector.detect() → hallucination_score

5. 置信度校准
    ConfidenceCalibrator.calibrate() → confidence

6. RAGAs评估
    RAGAsEvaluator.evaluate() → ragas_metrics

输出: AcademicQAResult
```

---

## 核心模块

### 1. AcademicQASystem (system.py)

统一系统入口，整合所有模块。

**主要类：**

```python
@dataclass
class AcademicQAConfig:
    """学术QA系统配置"""
    llm: Optional[Any] = None
    vector_store: Optional[Any] = None
    bm25_index: Optional[Any] = None
    embedding_model: Optional[Any] = None
    top_k: int = 20
    rerank_top_k: int = 5
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    enable_crag: bool = True
    enable_self_rag: bool = True
    enable_hallucination_detection: bool = True
    enable_confidence_calibration: bool = True
    enable_multi_hop: bool = True
    max_sub_questions: int = 5
    citation_style: str = "gb7714"
    max_citations: int = 10

@dataclass
class AcademicQAResult:
    """学术QA系统结果"""
    answer: str
    citations: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    hallucination_score: float = 0.0
    hallucination_risk: str = "unknown"
    reasoning_chain: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ragas_metrics: Optional[Dict[str, float]] = None
    errors: List[str] = field(default_factory=list)

class AcademicQASystem:
    async def ask(
        self,
        query: str,
        documents: Optional[List[Dict[str, Any]]] = None,
        contexts: Optional[List[str]] = None,
        mode: str = "strict"
    ) -> AcademicQAResult
```

### 2. DocumentParser (doc_parser.py)

文档解析器，支持多种格式。

```python
class DocumentParser:
    """学术文档解析器"""

    def parse(self, file_path: str) -> ParsedDocument:
        """解析文档"""

    def parse_content(self, content: str, source: str = "unknown") -> ParsedDocument:
        """解析文档内容"""
```

### 3. AcademicChunker (chunker.py)

学术文档分块器，基于语义的分块策略。

```python
class AcademicChunker:
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 100,
        split_by: str = "semantic"
    )

    def chunk(self, content: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """分块处理"""
```

### 4. HybridRetriever (hybrid_retriever.py)

混合检索器，结合BM25和向量检索。

```python
class HybridRetriever:
    def __init__(
        self,
        vector_store=None,
        bm25_index=None,
        embedding_model=None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    )

    async def retrieve(
        self,
        query: str,
        top_k: int = 20,
        rerank: bool = True
    ) -> List[RetrievalResult]
```

### 5. CitationTracker (citation_tracker.py)

引用溯源器，支持GB/T 7714和APA格式。

```python
class CitationTracker:
    def __init__(
        self,
        style: str = "gb7714",
        max_citations: int = 10
    )

    def trace_content(
        self,
        answer: str,
        source_documents: List[Dict[str, Any]]
    ) -> List[TracedContent]

    def format_citation(self, citation: Citation, style: str) -> str:
        """格式化引用"""
```

### 6. CRAGEvaluator (crag.py)

CRAG纠错型检索评估器。

```python
class CRAGEvaluator:
    async def evaluate(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]]
    ) -> CRAGResult
```

### 7. SelfRAGController (self_rag.py)

Self-RAG反思控制器。

```python
class SelfRAGController:
    async def reflective_generate(
        self,
        query: str
    ) -> SelfRAGResult
```

### 8. HallucinationDetector (hallucination_detector.py)

幻觉检测器，基于SelfCheckGPT。

```python
class HallucinationDetector:
    async def detect(
        self,
        question: str,
        answer: str
    ) -> HallucinationReport
```

### 9. ConfidenceCalibrator (confidence_calibrator.py)

置信度校准器。

```python
class ConfidenceCalibrator:
    async def calibrate(
        self,
        question: str,
        answer: str,
        contexts: List[str]
    ) -> ConfidenceScore
```

### 10. QueryDecomposer (query_decomposer.py)

查询分解器，支持多跳推理。

```python
class QueryDecomposer:
    async def decompose(
        self,
        query: str
    ) -> List[SubQuestion]
```

### 11. MultiHopReasoner (multi_hop_reasoner.py)

多跳推理器。

```python
class MultiHopReasoner:
    async def reason(
        self,
        query: str,
        top_k: int = 5
    ) -> MultiHopResult
```

### 12. RAGAsEvaluator (ragas_evaluator.py)

RAGAs评估框架。

```python
class RAGAsEvaluator:
    async def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str]
    ) -> RAGAsMetrics
```

### 13. AnswerAggregator (answer_aggregator.py)

答案聚合器。

```python
class AnswerAggregator:
    async def aggregate(
        self,
        original_query: str,
        sub_questions: List[Any],
        sub_answers: List[Any]
    ) -> AggregatedResult
```

---

## API接口

### 初始化

```python
from src.agents_v2.academic_qa import (
    AcademicQASystem,
    AcademicQAConfig,
    create_academic_qa_system
)

# 方式1: 直接创建
config = AcademicQAConfig(
    llm=llm,
    vector_store=vector_store,
    enable_crag=True,
    enable_self_rag=True,
    enable_hallucination_detection=True,
    enable_confidence_calibration=True,
    enable_multi_hop=True,
)
system = AcademicQASystem(config=config)

# 方式2: 便捷函数
system = await create_academic_qa_system(llm=llm, vector_store=vector_store)
```

### 问答

```python
# 基本问答
result = await system.ask(
    query="问题",
    documents=[{"content": "...", "metadata": {...}}],
    mode="strict"
)

# 使用直接提供的上下文
result = await system.ask(
    query="问题",
    contexts=["上下文1", "上下文2"],
    mode="strict"
)

# 访问结果
print(result.answer)                    # 答案文本
print(result.citations)                # 引用列表
print(result.confidence)               # 置信度
print(result.hallucination_score)     # 幻觉分数
print(result.hallucination_risk)       # 幻觉风险等级
print(result.ragas_metrics)           # RAGAs评估指标
```

### 格式化答案

```python
formatted = system.format_answer_with_citations(result)
print(formatted)
# 输出:
# 答案文本...
#
# ## 参考文献
# [1] 论文标题1
# [2] 论文标题2
#
# 置信度: 0.85
# 幻觉风险: low
```

### 文档摄入

```python
result = await system.ingest_documents(
    documents=[{"content": "文档内容", "metadata": {"title": "标题"}}],
    chunk_size=512
)
print(result["num_chunks"])  # 分块数量
```

---

## 使用示例

### 独立使用

```python
from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

# 创建系统
config = AcademicQAConfig(
    llm=llm,
    top_k=20,
    enable_crag=True,
    enable_self_rag=True,
    enable_hallucination_detection=True,
    enable_confidence_calibration=True,
)
system = AcademicQASystem(config=config)

# 执行问答
result = await system.ask(
    query="机器学习在医学诊断中的应用有哪些最新进展？",
    contexts=[
        "深度学习在医学影像诊断中表现出色，CNN架构被广泛用于X光和MRI分析。",
        "Transformer模型在医学NLP任务中取得了显著成果，如医学命名实体识别。",
        "强化学习在治疗方案优化中开始受到关注。"
    ]
)

print(f"答案: {result.answer}")
print(f"置信度: {result.confidence}")
print(f"幻觉风险: {result.hallucination_risk}")
```

### 集成到LangGraph

```python
from src.agents_v2.langgraph_workflow import UnifiedWorkflow

# 创建工作流
workflow = UnifiedWorkflow(llm=llm)

# 编译
app = workflow.compile()

# 运行QA路径
result = await app.ainvoke({
    "user_query": "问题",
    "route_path": "qa"
})

# result["answer"] 即为最终答案
```

---

## 知识图谱集成

### kg_integration.py - 知识图谱集成模块

```python
class AcademicQAKGIntegration:
    """学术QA与知识图谱集成"""

    def __init__(
        self,
        llm: Optional[Any] = None,
        kg_qa: Optional[Any] = None,
        enable_kg_retrieval: bool = True,
        enable_kg_enrichment: bool = True,
        enable_kg_multihop: bool = True,
        vector_weight: float = 0.3,
        graph_weight: float = 0.4,
        keyword_weight: float = 0.3,
    )

    async def ask(
        self,
        query: str,
        documents: Optional[List[Dict[str, Any]]] = None,
        contexts: Optional[List[str]] = None,
        mode: str = "strict"
    ) -> Dict[str, Any]
```

### 集成功能

1. **KGRetrieverWrapper** - 知识图谱检索器包装器
   - 将 GraphRAG 检索能力包装为 AcademicQASystem 可用接口
   - 支持向量检索 + 图检索 + 关键词检索融合

2. **KGAnswerEnricher** - 答案增强器
   - 从答案中提取实体并链接到知识图谱
   - 补充相关实体关系和证据

3. **KGMultiHopReasoner** - 图谱多跳推理器
   - 利用知识图谱的图结构增强多跳推理
   - 构建增强推理链

4. **AcademicQAKGIntegration** - 统一集成类
   - 混合检索：文档检索 + 知识图谱检索
   - 子图增强：在上下文中包含知识图谱子图
   - 答案增强：使用图谱关系补充答案

### 使用示例

```python
from src.agents_v2.academic_qa import AcademicQAKGIntegration
from src.agents_v2.knowledge_graph import create_graphrag_qa

# 创建知识图谱
kg_qa = create_graphrag_qa()

# 构建索引
kg_qa.build_index(
    entities=[("paper_1", "Paper", "Transformer论文")],
    relations=[("paper_1", "paper_2", "cites")]
)

# 创建集成系统
qa_kg = AcademicQAKGIntegration(
    llm=llm,
    kg_qa=kg_qa,
    enable_kg_retrieval=True,
    enable_kg_enrichment=True,
    enable_kg_multihop=True,
)

# 执行问答
result = await qa_kg.ask(
    query="Transformer和BERT有什么关系？",
    contexts=["Transformer是一种架构...", "BERT是Transformer的变体..."]
)

print(result["answer"])
print(f"知识图谱实体: {result['kg_context']['entity_map']}")
```

---

## 模块依赖关系

```
AcademicQASystem
├── HybridRetriever
│   ├── vector_store
│   ├── bm25_index
│   └── embedding_model
├── CitationTracker
├── AnswerGenerator
│   └── llm
├── CRAGEvaluator
│   └── llm
├── SelfRAGController
│   ├── llm
│   └── retriever
├── HallucinationDetector
│   └── llm
├── ConfidenceCalibrator
│   └── llm
├── QueryDecomposer (optional)
│   └── llm
├── MultiHopReasoner (optional)
│   ├── llm
│   └── retriever
├── AnswerAggregator (optional)
│   └── llm
└── RAGAsEvaluator
    └── llm
```

---

## 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `llm` | Any | None | LLM实例 |
| `vector_store` | Any | None | 向量存储 |
| `bm25_index` | Any | None | BM25索引 |
| `embedding_model` | Any | None | Embedding模型 |
| `top_k` | int | 20 | 检索返回数量 |
| `rerank_top_k` | int | 5 | 重排后返回数量 |
| `vector_weight` | float | 0.7 | 向量检索权重 |
| `keyword_weight` | float | 0.3 | 关键词检索权重 |
| `enable_crag` | bool | True | 启用CRAG |
| `enable_self_rag` | bool | True | 启用Self-RAG |
| `enable_hallucination_detection` | bool | True | 启用幻觉检测 |
| `enable_confidence_calibration` | bool | True | 启用置信度校准 |
| `enable_multi_hop` | bool | True | 启用多跳推理 |
| `citation_style` | str | "gb7714" | 引用格式 |
| `max_citations` | int | 10 | 最大引用数 |

---

*最后更新：2026年5月3日*
