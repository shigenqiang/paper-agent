# 论文Agent - 智能论文调研与知识图谱系统

> 基于多Agent协作的学术论文自动调研与综述生成系统
>
> **文档版本**: v2.0
> **更新日期**: 2026-04-26

---

## 一、项目概述

### 1.1 核心目标

构建一个智能的学术论文调研系统，能够：
- **智能路由**：自动判断问题类型，决定处理策略
- **论文搜索**：自动从arXiv/PubMed搜索相关统计学论文
- **专业报告**：基于真实论文给出带参考文献的专业回答
- **报告推送**：自动订阅并总结最新统计学论文，支持日报/周报/月报

### 1.2 应用场景

| 场景 | 说明 |
|------|------|
| 快速调研 | 快速了解某研究领域的前沿进展 |
| 论文搜索 | 寻找特定研究方向的开创性工作 |
| 专业问答 | 获取跨学科的研究洞察 |
| 文献追踪 | 每日/每周/每月推送论文摘要报告 |
| 论文写作 | 从选题到完稿的全流程辅助 |
| 智能改稿 | 解析导师意见，自动优化文本 |

### 1.3 质量承诺

- **来源可靠**：仅从arXiv、PubMed等权威学术平台获取论文
- **引用完整**：每条结论都标明来源论文
- **事实核查**：交叉验证关键发现

---

## 二、系统架构

### 2.1 整体架构

```
用户提问
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│                    QueryRouter (问题路由)                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │ 简单统计   │  │ 专业问题   │  │ 概念解释   │              │
│  │ 直接回答   │  │ 搜索论文   │  │ LLM回答    │              │
│  └────────────┘  └────────────┘  └────────────┘              │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│              PaperSearchAgent (论文搜索Agent)                   │
│  ├── arXiv搜索        - 机器学习、统计理论论文                  │
│  ├── PubMed搜索       - 生物统计、医学应用论文                   │
│  └── 语义排序         - 基于问题相关性排序                      │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│              ReportGenerator (报告生成Agent)                   │
│  ├── 摘要提取       - 提炼每篇论文核心贡献                      │
│  ├── 对比分析       - 比较不同论文的方法和结论                   │
│  └── 专业报告       - 生成结构化报告，含参考文献                 │
└────────────────────────────────────────────────────────────────┘
```

### 2.2 路由决策规则

| 问题类型 | 特征 | 处理方式 |
|----------|------|----------|
| **基础查询** | 定义、公式、概念 | 直接从知识库回答 |
| **专业问题** | 方法论、理论证明 | 搜索论文后回答 |
| **前沿探索** | 最新技术、发展趋势 | 搜索arXiv最新论文 |
| **应用咨询** | 实际数据分析 | 搜索PubMed案例 |

---

## 三、核心模块设计

### 3.1 统计学问答系统 (QA)

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `QueryRouter` | 判断问题类型，决定处理策略 | 用户问题 | 路由决策 + 处理路径 |
| `PaperSearchAgent` | 搜索统计学论文 | 查询关键词 | 相关论文列表 |
| `ReportGenerator` | 生成专业报告 | 论文列表 | 结构化报告 |
| `DailyWatcher` | 每日论文监控（论文过少时跳过） | 订阅关键词 | 每日摘要报告 |
| `WeeklyReportGenerator` | 周报生成 | 周论文数据 | 周度总结报告 |
| `MonthlyReportGenerator` | 月报生成 | 月论文数据 | 月度分析报告 |
| `CitationManager` | 管理参考文献 | 论文列表 | 格式化引用 |

**报告生成规则：**
- **日报**：当日论文 ≥ 3篇 时生成，不足则跳过
- **周报**：每周一生成上周总结
- **月报**：每月1日生成上月分析

### 3.2 统一Agent框架 (Unified)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MasterSupervisor                                │
│                    (全局状态管理 + 路由决策)                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
    ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
    │   Diagnostic   │     │   Pipeline    │     │   Problem     │
    │   Phase        │     │   Phase       │     │   Solving     │
    └───────────────┘     └───────────────┘     └───────────────┘
```

**核心组件**：
- `MasterSupervisor` - 全局协调器
- `PhaseSupervisor` - 单阶段协调器
- `PaperState` - 全局状态管理
- `CircuitBreaker` - 熔断器模式

### 3.3 问题导向型Agent (Problem-Oriented)

针对论文写作中的具体困难设计的7个Agent：

| Agent | 针对问题 | 职责 |
|-------|----------|------|
| `TopicRefinerAgent` | 选题困难 | 分析想法、评估可行性、优化选题 |
| `LiteratureMapperAgent` | 文献综述不充分 | 全面搜索、分类整理、识别空白 |
| `MethodologyAdvisorAgent` | 研究方法不当 | 推荐方法、检查严谨性 |
| `ArgumentBuilderAgent` | 论证逻辑不严密 | 构建框架、检查连贯性 |
| `SectionDifferentiatorAgent` | 摘要与结论重复 | 检查差异、指导差异化 |
| `DiscussionDeepenerAgent` | 讨论部分薄弱 | 深化讨论、对比已有研究 |
| `LanguagePolisherAgent` | 语言表达问题 | 语法检查、规范术语 |

---

## 四、高级 RAG 技术详解

### 4.1 Query Decomposition（查询分解）

将复杂问题拆解为多个简单子问题，适用于多跳推理场景。

```python
class QueryDecomposer:
    def decompose(self, query: str) -> List[str]:
        """将复杂问题分解为子问题列表"""
        decomposition_prompt = f"""请将以下复杂问题分解为3-5个简单的子问题。
每个子问题应该能够通过单次检索直接回答。

复杂问题: {query}

要求:
1. 分解后的子问题应该覆盖原问题的各个维度
2. 每个子问题应该足够简单，可以直接回答
3. 使用数字列表格式输出

子问题:"""
        response = self.llm.generate(decomposition_prompt)
        return self._parse_sub_questions(response)
```

### 4.2 HyDE (Hypothetical Document Embeddings)

不直接用用户查询去找相似文档，而是先用 LLM 生成一个"假设性答案文档"，然后用这个假设文档去找真实相似的文档。

```python
class HyDERewriter:
    def retrieve_with_hyde(self, query: str, top_k: int = 5):
        """使用 HyDE 进行检索"""
        hyp_doc = self.generate_hypothetical_document(query)
        hyp_embedding = self.embedding_model.embed_query(hyp_doc)
        return self.vectorstore.similarity_search_by_vector(
            embedding=hyp_embedding, k=top_k
        )
```

**局限性**：幻觉传播问题、计算开销、敏感领域慎用

### 4.3 Corrective RAG (CRAG)

在生成之前增加一个"检索结果评估"步骤，根据评估结果决定是接受、纠正还是重新检索。

```python
class RetrievalQuality(Enum):
    HIGH = "high"      # 检索结果质量高，直接使用
    MEDIUM = "medium"  # 质量中等，需要补充
    LOW = "low"        # 质量低，需要重新检索或降级
    EMPTY = "empty"    # 没有检索到结果
```

### 4.4 Self-RAG

通过自我反思机制，让模型学会判断何时需要检索、如何评估检索结果。

```python
class SelfRAG:
    REFLECTION_TOKENS = {
        "[检索]": "需要检索外部知识",
        "[不检索]": "不需要检索，现有知识足够",
        "[相关]": "检索结果与问题相关",
        "[不相关]": "检索结果与问题不相关",
        "[支持]": "生成内容被检索结果支持",
        "[部分支持]": "生成内容部分被检索结果支持",
        "[矛盾]": "生成内容与检索结果矛盾",
    }
```

---

## 五、关键技术细节

### 5.1 混合搜索策略

**BM25 广度检索 + 向量深度检索 + 交叉编码器重排**

```
BM25检索 (关键词精准匹配，如产品编号、错误码、公式符号)
    ↓
向量检索 (语义相似扩展)
    ↓
RRF融合 (Reciprocal Rank Fusion, k=60)
    ↓
Cross-Encoder重排序 (精排，保留 Top 3-10)
```

### 5.2 分块策略 (Chunking)

| 策略 | 配置 | 适用场景 |
|------|------|----------|
| 递归字符分割 | 512 token, 50-100 token overlap | 通用场景，作为起点 |
| 语义分割 | 基于 LLM 判断边界 | 需要保持语义完整性 |
| Parent-Child | 小 chunk(100-200) 检索，大 chunk(1000-2000) 返回 | 复杂文档结构 |

**推荐配置**：
- 简单问答：4K-8K context
- 复杂分析：16K-32K context
- 超长文档（论文）：64K+ context

### 5.3 向量检索优化

| 特性 | Bi-Encoder | Cross-Encoder |
|------|-----------|---------------|
| 处理方式 | 查询和文档独立编码 | 拼接后联合编码 |
| 文档向量 | 可离线预计算 | 需要实时计算 |
| 检索速度 | 快（ANN 搜索） | 慢（需遍历） |
| 精度 | 捕获概念相似 | 捕获精确交互 |
| 适用规模 | 亿级文档 | 万级文档 |

### 5.4 重排序模型选型

| 模型 | 上下文长度 | 精度 | 适用场景 |
|------|-----------|------|----------|
| BGE-Reranker-v2-m3 | 8192 token | 高 | 中文高精度场景 |
| Cohere Rerank | 512 | 高 | 多语言场景 |
| Jina Reranker | 8192 | 中 | 快响场景 |

**配置建议**：向量检索返回 20-50 个候选，Rerank 后保留 3-10 个

---

## 六、工程化细节

### 6.1 端到端延迟优化

```python
LATENCY_OPTIMIZATION_CHECKLIST = {
    "pre_retrieval": [
        "query caching enabled",
        "async embedding generation",
        "connection pooling for vector DB"
    ],
    "retrieval": [
        "use ANN index (HNSW/IVF)",
        "appropriate nprobe/ef_construction",
        "result caching",
        "parallel retrieval for multi-query"
    ],
    "post_retrieval": [
        "async document loading",
        "early exit for high-confidence retrieval",
        "streaming cross-encoder scoring"
    ],
    "generation": [
        "streaming output",
        "token-level early stopping",
        "batching for multiple requests"
    ]
}
```

### 6.2 缓存策略（Semantic Cache）

```python
class SemanticCache:
    async def get_or_compute(
        self,
        query: str,
        compute_func: Callable,
        similarity_threshold: float = 0.85,
        ttl_seconds: int = 3600
    ) -> Tuple[Any, bool, float]:
        """获取缓存或计算"""
        query_embedding = await self.embedding_model.aembed_query(query)
        cached = await self.cache_store.get_similar(
            embedding=query_embedding,
            threshold=similarity_threshold
        )

        if cached:
            return cached["result"], True, cached["similarity"]

        result = await compute_func(query, **kwargs)
        await self.cache_store.store(...)
        return result, False, 0.0
```

**多级缓存架构**：精确匹配缓存 → 语义相似缓存 → 热点缓存

### 6.3 批量处理与并发

```python
class BatchProcessor:
    def __init__(
        self,
        batch_size: int = 32,
        max_wait_ms: int = 100,
        max_concurrent_batches: int = 5
    ):
        self.batch_size = batch_size
        self.max_wait_ms = max_wait_ms
        self.semaphore = asyncio.Semaphore(max_concurrent_batches)
```

### 6.4 错误重试与降级

```python
class RetryManager:
    async def execute_with_retry(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        exponential_base: float = 2.0,
    ) -> Any:
        for attempt in range(max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except retryable_exceptions as e:
                if attempt == max_retries:
                    break
                delay = min(base_delay * (exponential_base ** attempt), 60.0)
                await asyncio.sleep(delay)
        raise MaxRetriesExceeded(f"Max retries ({max_retries}) exceeded")
```

---

## 七、质量保证细节

### 7.1 答案事实性校验

```python
class FactualityChecker:
    def verify_claims(
        self,
        answer: str,
        source_documents: List[str]
    ) -> Dict:
        """验证答案中的声明"""
        claims = self._extract_claims(answer)
        verification_results = []
        for claim in claims:
            result = self._verify_single_claim(claim, source_documents)
            verification_results.append(result)
        return self._summarize_verification(verification_results)
```

### 7.2 引用追溯机制

```python
class CitationTracker:
    def trace_generated_content(
        self,
        answer: str,
        source_documents: List[str]
    ) -> List[Dict]:
        """追溯生成内容的信息来源"""
        traced_content = []
        for sentence in sentences:
            best_match = None
            best_similarity = 0
            for j, doc in enumerate(source_documents):
                similarity = self._calculate_similarity(sentence, doc)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = j
            traced_content.append({
                "sentence": sentence,
                "source_document_index": best_match,
                "confidence": best_similarity,
                "is_generated": best_similarity < 0.3
            })
        return traced_content
```

### 7.3 置信度校准

```python
confidence_score = {
    "retrieval_score": 0.85,
    "context_coverage": 0.9,
    "answer_consistency": 0.8,
    "groundedness": 0.75
}

final_score = weighted_mean(confidence_score, weights=[0.3, 0.3, 0.2, 0.2])
```

### 7.4 拒答策略

| 条件 | 阈值建议 | 处理方式 |
|------|----------|----------|
| 检索相关性低 | similarity < 0.7 | 拒答或转人工 |
| 置信度评分低 | confidence < 0.5 | 拒答 |
| 信息不足 | retrieved docs < 2 | 拒答或模糊回答 |
| 超出知识范围 | 领域匹配度低 | 拒答 |

---

## 八、目录结构

```
src/agents_v2/
├── qa/                          # 统计学问答系统
│   ├── base_qa_agent.py         # QA Agent基类
│   ├── query_router.py          # 问题路由
│   ├── paper_search.py          # 论文搜索(arXiv/PubMed)
│   ├── report_generator.py      # 报告生成
│   ├── daily_watcher.py         # 每日监控
│   ├── weekly_report.py         # 周报生成
│   ├── monthly_report.py        # 月报生成
│   └── citation_manager.py      # 引用管理
│
├── unified/                      # 统一Agent框架
│   ├── state_model.py           # 状态模型
│   ├── circuit_breaker.py       # 熔断器
│   ├── error_handler.py         # 错误处理（智能分类+降级）
│   ├── phase_supervisor.py      # 阶段协调
│   ├── intent_router.py         # 意图路由
│   └── master_supervisor.py     # 全局协调
│
├── paper_agents/                 # Pipeline型Agent (论文写作流程)
│   ├── base_paper_agent.py     # Paper Agent基类
│   ├── topic_agent.py           # 主题选择
│   ├── literature_agent.py      # 文献工作
│   ├── thesis_agent.py          # Thesis凝练
│   ├── outline_agent.py         # 大纲制定
│   ├── draft_writer.py          # 分节撰写
│   ├── editor_agent.py          # 修订编辑
│   └── reviewer_agent.py        # 最终审核
│
├── problem_oriented/            # 问题导向Agent
│   ├── base_problem_agent.py   # Problem Agent基类
│   ├── topic_refiner.py        # 选题精炼
│   ├── literature_mapper.py     # 文献映射
│   ├── methodology_advisor.py  # 方法指导
│   ├── argument_builder.py     # 论证构建
│   ├── section_differentiator.py # 差异化写作
│   ├── discussion_deepener.py   # 讨论深化
│   ├── chart_formatter.py      # 图表规范化
│   ├── language_polisher.py     # 语言润色
│   └── plagiarism_checker.py   # 查重检测
│
├── writing/                      # 论文写作全流程Agent
│   ├── base_writing_agent.py   # Writing Agent基类
│   ├── literature_review.py    # 文献综述
│   ├── outline_generator.py    # 大纲生成
│   ├── draft_generator.py      # 全文初稿
│   ├── report_refiner.py       # 报告精炼
│   ├── proposal_generator.py    # 开题报告
│   ├── reference_processor.py   # 参考文献处理
│   ├── smart_reviser.py        # 智能改稿
│   └── language_polisher.py    # 语言润色
│
└── demo.py                       # 演示脚本
```

---

## 九、实施计划

### Phase 1: 核心功能 (已完成 ✅)

| 模块 | 状态 | 说明 |
|------|------|------|
| QueryRouter | ✅ | 问题类型判断和路由决策 |
| PaperSearchAgent | ✅ | arXiv/PubMed论文搜索 |
| ReportGenerator | ✅ | 专业报告生成 |
| DailyWatcher | ✅ | 每日论文监控（论文过少时跳过） |
| WeeklyReportGenerator | ✅ | 周报生成 |
| MonthlyReportGenerator | ✅ | 月报生成 |
| CitationManager | ✅ | 参考文献格式化 |

### Phase 2: 统一框架 (已完成 ✅)

| 模块 | 状态 | 说明 |
|------|------|------|
| StateModel | ✅ | PaperState, ProblemType等 |
| CircuitBreaker | ✅ | CLOSED/OPEN/HALF_OPEN状态机 |
| FallbackHandler | ✅ | 降级处理策略 |
| ErrorHandler | ✅ | 智能错误分类+日志优化 |
| PhaseSupervisor | ✅ | 阶段协调 |
| MasterSupervisor | ✅ | 全局协调 |
| IntentRouter | ✅ | 意图路由 |

### Phase 3: 问题导向Agent (已完成 ✅)

| Agent | 状态 | 说明 |
|-------|------|------|
| TopicRefinerAgent | ✅ | 选题精炼 |
| LiteratureMapperAgent | ✅ | 文献映射 |
| MethodologyAdvisorAgent | ✅ | 方法指导 |
| ArgumentBuilderAgent | ✅ | 论证构建 |
| SectionDifferentiatorAgent | ✅ | 差异化写作 |
| DiscussionDeepenerAgent | ✅ | 讨论深化 |
| ChartFormatterAgent | ✅ | 图表规范化 |
| LanguagePolisherAgent | ✅ | 语言润色 |
| PlagiarismCheckerAgent | ✅ | 查重检测 |

### Phase 4: Pipeline Agent (已完成 ✅)

| Agent | 状态 | 说明 |
|-------|------|------|
| TopicAgent | ✅ | 主题选择 |
| LiteratureAgent | ✅ | 文献工作 |
| ThesisAgent | ✅ | Thesis凝练 |
| OutlineAgent | ✅ | 大纲制定 |
| DraftWriterAgent | ✅ | 分节撰写 |
| EditorAgent | ✅ | 修订编辑 |
| ReviewerAgent | ✅ | 最终审核 |

### Phase 5: 论文写作全流程Agent (已完成 ✅)

| Agent | 状态 | 说明 |
|-------|------|------|
| LiteratureReviewAgent | ✅ | 文献综述 |
| OutlineGeneratorAgent | ✅ | 大纲生成 |
| DraftGeneratorAgent | ✅ | 全文初稿 |
| ReportRefinerAgent | ✅ | 报告精炼 |
| ProposalGeneratorAgent | ✅ | 开题报告 |
| ReferenceProcessorAgent | ✅ | 参考文献处理 |
| SmartReviserAgent | ✅ | 智能改稿 |
| LanguagePolisherAgent | ✅ | 语言润色 |

### Phase 6: 高级功能Agent (待开发)

| 功能模块 | Agent | 描述 | 优先级 | 参考 |
|----------|-------|------|--------|------|
| **引文网络分析** | `CitationNetworkAgent` | 追踪论文的引用和被引用关系 | 高 | Paper-Agent |
| **PDF深度解析** | `PDFParserAgent` | 直接读取本地PDF提取内容进行问答 | 高 | GPT Academic |
| **知识图谱生成** | `KnowledgeGraphAgent` | 将论文内容转为结构化知识图谱 | 中 | Paper Circle |
| **快捷命令系统** | `CommandSystemAgent` | 自定义快捷键触发特定功能 | 中 | GPT Academic |
| **插件扩展机制** | `PluginSystem` | 允许用户添加自定义功能模块 | 低 | GPT Academic |
| **研究空白识别** | `ResearchGapFinder` | 自动识别文献中的研究空白点 | 中 | Paper-Agent |

---

## 十、技术规格

### 10.1 熔断器状态机

```
CLOSED → (失败阈值) → OPEN
OPEN → (超时恢复) → HALF_OPEN
HALF_OPEN → (成功) → CLOSED
HALF_OPEN → (失败) → OPEN
```

### 10.2 降级策略

每个阶段都有降级输出：
- topic: 默认选题
- literature: 空文献列表
- writing: 基本大纲
- polish: 保持原样

### 10.3 质量门控

| 阶段 | 最小要求 |
|------|---------|
| research | 10篇论文, 0.6相关性 |
| analysis | 3个主题, 1个研究空白 |
| writing | 5个章节, 0.7连贯性 |

### 10.4 配置参数速查表

```python
RETRIEVAL_CONFIG = {
    "embedding_model": "bge-large-zh",
    "chunk_size": 512,
    "chunk_overlap": 100,
    "vector_db": "milvus",
    "top_k": 5,
    "reranker": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "rerank_top_k": 3,
    "hybrid_search": True,
    "keyword_weight": 0.3,
    "vector_weight": 0.7
}

GENERATION_CONFIG = {
    "model": "gpt-4-turbo",
    "temperature": 0.3,
    "max_tokens": 2000,
    "top_p": 0.9,
}

RAG_OPTIMIZATION_CONFIG = {
    "hyde_enabled": True,
    "hyde_temperature": 0.7,
    "crag_enabled": True,
    "quality_threshold": 0.5,
    "max_correction_iterations": 2,
    "self_rag_enabled": False,
}
```

---

## 十一、使用示例

### 统计学问答

```python
from src.agents_v2.qa import QueryRouter, PaperSearchAgent, ReportGenerator

# 用户提问
question = "什么是贝叶斯分层模型？它在医学研究中的应用有哪些？"

# 路由决策
router = QueryRouter()
decision = await router.execute(question)
print(f"路由决策: {decision['suggested_path']}")

# 搜索论文
searcher = PaperSearchAgent()
papers = await searcher.execute(decision['suggested_path'])
print(f"找到 {len(papers)} 篇相关论文")

# 生成报告
generator = ReportGenerator()
report = await generator.execute(papers, question)
print(report["summary"])
```

### 每日论文订阅

```python
from src.agents_v2.qa import DailyWatcher

watcher = DailyWatcher(
    keywords=["statistical learning", "causal inference"],
)
report = await watcher.execute()
# 仅当论文数 >= 3 时生成报告，否则返回 None
if report:
    print(report["daily_summary"])
```

### 周报生成

```python
from src.agents_v2.qa import WeeklyReportGenerator

weekly = WeeklyReportGenerator(
    keywords=["statistical learning", "causal inference"],
)
report = await weekly.execute()
print(report["weekly_summary"])
```

### 月报生成

```python
from src.agents_v2.qa import MonthlyReportGenerator

monthly = MonthlyReportGenerator(
    keywords=["statistical learning", "causal inference"],
)
report = await monthly.execute()
print(report["monthly_summary"])
```

---

## 十二、扩展指南

### 12.1 新增问答场景

1. 在 `qa/` 目录实现新的Agent
2. 继承 `BaseQAAgent`
3. 注册到 `QueryRouter`

### 12.2 自定义路由规则

继承 `QueryRouter` 重写 `_classify_question`

### 12.3 新增论文数据源

继承 `PaperSearchAgent` 实现 `_search_source`

---

## 十三、监控与评估体系

### 13.1 RAG 评估框架

**RAGAs 指标体系**：

| 指标 | 评估对象 | 说明 |
|------|----------|------|
| Context Precision | 检索器 | 相关块排在前的程度 |
| Context Recall | 检索器 | 召回相关事实的比例 |
| Faithfulness | 生成器 | 答案基于上下文程度 |
| Answer Relevance | 端到端 | 答案直接回答问题程度 |
| Factual Correctness | 生成器 | 答案事实准确性 |

### 13.2 核心监控指标

```python
metrics = {
    # 业务指标
    "support_ticket_reduction": "工单减少率",
    "user_retention": "用户留存率",

    # 技术指标
    "retrieval_latency_p99": "检索延迟 P99",
    "generation_latency_p99": "生成延迟 P99",
    "context_precision": "上下文精确率",
    "answer_faithfulness": "答案忠实度",

    # 成本指标
    "cost_per_query": "单次查询成本",
    "token_usage": "Token 消耗量"
}
```

---

## 十四、常见错误案例速查

| 错误类型 | 错误表现 | 根因 | 解决方案 |
|---------|---------|------|---------|
| 分块过大 | 检索噪音多 | chunk_overlap 不够 | 增加 overlap 或按语义分块 |
| 向量漂移 | 相似查询返回不同结果 | embedding 模型不稳定 | 固定模型版本，增加缓存 |
| 幻觉增加 | 答案与检索内容矛盾 | prompt 约束不足 | 增加 faithfulness 提示 |
| 延迟过高 | 首 token 时间 > 2s | 同步阻塞调用 | 改为异步，增加流式输出 |
| 缓存失效 | 相同查询重复计算 | 相似度阈值过高 | 降低阈值到 0.8-0.85 |
| 状态丢失 | 多轮对话忘记之前内容 | 上下文截断不当 | 保留关键实体的完整上下文 |

---

## 十五、参考资源

| 资源 | 说明 |
|------|------|
| [Anthropic: Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) | 核心设计原则 |
| [arXiv API](https://arxiv.org/help/api) | 论文搜索API |
| [PubMed E-utilities](https://www.ncbi.nlm.nih.gov/home/develop/api/) | 生物医学文献API |
| [LangGraph Documentation](https://langchain.dev/langgraph) | 工作流编排 |
| [RAGAs Evaluation Framework](https://docs.ragas.io/) | RAG 评估工具 |
| [BGE-M3 Embedding Model](https://github.com/AI-Godel/BGE-M3) | 向量模型 |

---

**文档版本**: v2.0
**创建日期**: 2026-04-23
**最后更新**: 2026-04-26
