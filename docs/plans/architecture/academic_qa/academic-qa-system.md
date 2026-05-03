# 学术QA系统 - Academic QA System

> 版本：v1.0
> 更新日期：2026-05-03
> 状态：已实现

## 概述

学术QA系统是一个面向学术领域的严谨问答系统，具备以下核心能力：

- **多跳推理**：支持复杂问题的分解与推理链构建
- **引用溯源**：精确追踪答案的事实来源
- **幻觉检测**：基于SelfCheckGPT的幻觉检测机制
- **置信度校准**：多维度置信度评估
- **CRAG纠错**：检索质量评估与自动纠错
- **Self-RAG**：反思机制提升答案质量
- **RAGAs评估**：标准化的RAG系统评估

---

## 系统位置

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
```

---

## 核心模块

### 模块清单 (16个模块文件)

| 组件 | 文件 | 说明 |
|------|------|------|
| DocumentParser | doc_parser.py | 文档解析器 |
| AcademicChunker | chunker.py | 学术文档分块器 |
| HybridRetriever | hybrid_retriever.py | 混合检索器 (BM25 + 向量 + RRF) |
| CitationTracker | citation_tracker.py | 引用溯源器 |
| AnswerGenerator | answer_generator.py | 答案生成器 |
| CRAGEvaluator | crag.py | CRAG 纠错型检索评估 |
| SelfRAGController | self_rag.py | Self-RAG 反思机制 |
| HallucinationDetector | hallucination_detector.py | 幻觉检测器 |
| ConfidenceCalibrator | confidence_calibrator.py | 置信度校准器 |
| QueryDecomposer | query_decomposer.py | 查询分解器（多跳推理） |
| MultiHopReasoner | multi_hop_reasoner.py | 多跳推理器 |
| RAGAsEvaluator | ragas_evaluator.py | RAGAs 评估框架 |
| AnswerAggregator | answer_aggregator.py | 答案聚合器 |
| kg_integration | kg_integration.py | 知识图谱集成模块 |

### 知识图谱集成模块

| 组件 | 说明 |
|------|------|
| KGRetrieverWrapper | 知识图谱检索包装器 |
| KGAnswerEnricher | 知识图谱答案增强器 |
| KGMultiHopReasoner | 图谱多跳推理器 |
| AcademicQAKGIntegration | 知识图谱集成系统 |

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

## 核心类定义

### AcademicQASystem (system.py)

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

## 开发计划

### 现状

系统已实现完整的学术QA功能，包括：
- 16个核心模块全部实现
- 支持单跳和多跳问答模式
- 集成CRAG、Self-RAG、幻觉检测等严格性保障机制
- 支持知识图谱集成

### 待完善功能

1. **评估增强**
   - RAGAs指标标准化
   - 多维度质量报告

2. **性能优化**
   - 检索速度优化
   - 缓存机制

3. **扩展功能**
   - 更多引用格式支持
   - 批量处理能力

---

*最后更新：2026年5月3日*