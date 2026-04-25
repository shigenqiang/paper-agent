# 智能问答 Agent 系统工程化落地调研报告

> 调研时间：2026年4月
> 适用范围：统计学问答系统、论文写作助手、RAG-based QA 系统

---

## 一、背景与目的

随着 LLM 技术成熟，智能问答已成为落地最广泛的应用场景之一。本报告聚焦**真实场景落地**的关键细节，涵盖架构设计、召回优化、置信度控制、成本管理等核心环节，旨在为论文 Agent 这类专业领域问答系统提供可落地的技术参考。

---

## 二、核心架构：RAG 模式

业界主流方案基于 **RAG (Retrieval-Augmented Generation)** 架构，核心流程如下：

```
文档 → 分块(Chunking) → 向量化(Embedding) → 索引存储
用户查询 → 向量化 → 相似度检索 → 重排序(Rerank) → 上下文组装 → LLM生成 → 答案
```

### 2.1 三大核心模块

| 模块 | 职责 | 技术选型 |
|------|------|----------|
| **检索 (Retrieval)** | 从知识库召回相关文档 | 向量检索(ANN)、BM25关键词检索 |
| **增强 (Augmentation)** | 组装 Prompt 上下文 | Prompt 模板、上下文裁剪 |
| **生成 (Generation)** | LLM 基于上下文生成答案 | GPT-4/Claude/Qwen 等 |

### 2.2 论文 Agent 的 RAG 架构

结合项目需求（统计学问答 + 论文写作），推荐架构如下：

```
用户提问
    │
    ▼
QueryRouter (问题路由)
    ├── 基础查询 → 知识库直接回答
    ├── 专业问题 → PaperSearch → ReportGenerator
    └── 前沿探索 → arXiv/PubMed 搜索
```

---

## 三、关键技术细节

### 3.1 混合搜索策略

**单靠向量检索存在"语义相似但不相关"的根本缺陷**，业界黄金组合是：

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

### 3.2 分块策略 (Chunking)

分块不是调参数，是在做**信息粒度的取舍**。这是最容易出问题的环节：

| 策略 | 配置 | 适用场景 |
|------|------|----------|
| 递归字符分割 | 512 token, 50-100 token overlap | 通用场景，作为起点 |
| 语义分割 | 基于 LLM 判断边界 | 需要保持语义完整性 |
| Parent-Child | 小 chunk(100-200) 检索，大 chunk(1000-2000) 返回 | 复杂文档结构 |

**典型失败模式**：
- Chunk 太小：丢失上下文，关系割裂
- Chunk 太大（>2500 token）：生成质量断崖式下跌，上下文被稀释

**推荐配置**（基于 2026 年测试数据）：
- 简单问答：4K-8K context
- 复杂分析：16K-32K context
- 超长文档（论文）：64K+ context（如 Qwen2.5、Claude3.5 支持）

### 3.3 向量检索优化

| 特性 | Bi-Encoder | Cross-Encoder |
|------|-----------|---------------|
| 处理方式 | 查询和文档独立编码 | 拼接后联合编码 |
| 文档向量 | 可离线预计算 | 需要实时计算 |
| 检索速度 | 快（ANN 搜索） | 慢（需遍历） |
| 精度 | 捕获概念相似 | 捕获精确交互 |
| 适用规模 | 亿级文档 | 万级文档 |

**推荐方案**：
1. 大规模检索：Bi-Encoder（向量索引）+ ANN 快速召回
2. 高精度场景：Cross-Encoder 二次精排
3. ColBERT：late interaction 机制，兼具效率和精度

### 3.4 重排序模型选型

| 模型 | 上下文长度 | 精度 | 适用场景 |
|------|-----------|------|----------|
| BGE-Reranker-v2-m3 | 8192 token | 高 | 中文高精度场景 |
| Cohere Rerank | 512 | 高 | 多语言场景 |
| Jina Reranker | 8192 | 中 | 快响场景 |

**配置建议**：
- Top-K：向量检索返回 20-50 个候选，Rerank 后保留 3-10 个
- RRF 参数：通常 k=60

---

## 四、Prompt Engineering 技巧

### 4.1 结构化 Prompt 设计

```python
# 典型 RAG Prompt 模板
template = """
<system>
你是一个专业的统计学问答助手。你需要基于给定的上下文回答问题。

规则：
1. 只使用上下文中的信息回答，不要编造
2. 如果上下文信息不足以回答，明确说明
3. 回答要准确、简洁、有条理
4. 涉及公式时请使用 LaTeX 格式
</system>

<context>
{context}
</context>

<question>
{question}
</question>

<answer>
"""
```

### 4.2 Few-shot 示例策略

示例要"典型+覆盖边界"：
- 知识库匹配场景：给 AI 示例"问：如何退款？"→ "答：根据退货政策..."
- 复杂推理场景：使用 Chain-of-Thought 引导
- 论文引用场景：展示如何标注参考文献格式

### 4.3 量化约束技巧

```python
# 量化要求示例
"回答控制在300字以内，分3点说明"

# 否定式约束示例
"不要解释概念，直接给出解决方案"
"不要提及未在知识库中出现的产品版本"

# 格式约束示例
"回答格式：1. ... 2. ... 3. ..."
"每篇论文按【作者(年份)】格式引用"
```

### 4.4 多来源信息标注

```python
# 多来源信息标注
"""
【知识库1：产品规则】
xxx

【论文来源：arXiv:2401.XXXXX】
xxx

【历史对话】
xxx
"""
```

---

## 五、多 Agent 协作架构

### 5.1 核心协作模式

| 模式 | 描述 | 适用场景 |
|------|------|----------|
| 顺序交接 | 任务在不同 Agent 间传递 | 流水线处理 |
| 并行处理 | 多个 Agent 同时处理子任务 | 快速响应 |
| 辩论与共识 | Agent 间讨论后达成一致 | 复杂决策 |
| 层级结构 | 规划 Agent + 执行 Agent | 复杂任务分解 |
| Critic-Reviewer | 一个生成一个审查 | 质量把控 |

### 5.2 论文 Agent 的多 Agent 架构

参考项目设计，采用双层 Supervisor 架构：

```
MasterSupervisor
    │
    ├── Diagnostic Phase (并行诊断)
    │   ├── TopicRefinerAgent
    │   ├── LiteratureMapperAgent
    │   └── MethodologyAdvisorAgent
    │
    ├── Pipeline Phase (顺序执行)
    │   ├── TopicAgent → LiteratureAgent → ThesisAgent
    │   └── OutlineAgent → DraftWriterAgent → EditorAgent
    │
    └── Polish Phase (针对性修复)
        ├── ChartFormatterAgent
        ├── LanguagePolisherAgent
        └── PlagiarismCheckerAgent
```

### 5.3 状态机模式 (LangGraph)

```python
# 典型状态机定义
states = ["idle", "retrieving", "generating", "reviewing", "completed"]

# 条件边定义
def route_next(state) -> str:
    if state == "retrieving":
        return "generating"
    elif state == "reviewing":
        return "completed" if is_acceptable() else "generating"
    return state

# ReAct 循环
while not finished:
    action = agent.select_action()  # 选择动作
    observation = agent.execute(action)  # 执行
    state.update(observation)  # 更新状态
```

---

## 六、拒答策略与置信度控制

**这是真实场景落地的关键 -- 不确定的答案宁可拒答，比答错好。**

### 6.1 拒答触发条件

| 条件 | 阈值建议 | 处理方式 |
|------|----------|----------|
| 检索相关性低 | similarity < 0.7 | 拒答或转人工 |
| 置信度评分低 | confidence < 0.5 | 拒答 |
| 信息不足 | retrieved docs < 2 | 拒答或模糊回答 |
| 超出知识范围 | 领域匹配度低 | 拒答 |

### 6.2 多维度置信度评估

```python
# 多维度置信度评估
confidence_score = {
    "retrieval_score": 0.85,      # 检索相关性
    "context_coverage": 0.9,      # 上下文覆盖率
    "answer_consistency": 0.8,    # 答案一致性
    "groundedness": 0.75         # 有据可查性
}

# 综合评分
final_score = weighted_mean(confidence_score, weights=[0.3, 0.3, 0.2, 0.2])

# 决策
if final_score < threshold:
    return {"allow_answer": False, "response": "抱歉，无法准确回答，建议联系人工客服。"}
```

### 6.3 CRAG (Corrective-RAG) 策略

```python
def crag_strategy(documents, query):
    for doc in documents:
        score = rerank_model.predict(query, doc)
        if score > 0.8:
            return "direct_generate"  # 正确 → 直接生成
        elif score > 0.5:
            return "knowledge_refine"  # 模糊 → 知识细化 + 过滤
        else:
            return "web_search"  # 错误 → 网络搜索补充
```

---

## 七、监控与评估体系

### 7.1 RAG 评估框架

**RAGAs 指标体系**：

| 指标 | 评估对象 | 说明 |
|------|----------|------|
| Context Precision | 检索器 | 相关块排在前的程度 |
| Context Recall | 检索器 | 召回相关事实的比例 |
| Faithfulness | 生成器 | 答案基于上下文程度 |
| Answer Relevance | 端到端 | 答案直接回答问题程度 |
| Factual Correctness | 生成器 | 答案事实准确性 |

**TruLens RAG 三元组**：
1. **上下文相关性** (Context Relevance)
2. **忠实度/基础性** (Faithfulness/Groundedness)
3. **答案相关性** (Answer Relevance)

### 7.2 核心监控指标

```python
# 核心监控指标
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

### 7.3 A/B 测试策略

**实验设计要点**：
1. 单一变量原则：每次只改一个因素
2. 流量分配：5%-50% 渐进式
3. 统计显著性：至少 1000 样本

**常见 A/B 测试场景**：
- 分块策略对比（固定 vs 语义）
- 向量模型对比（BGE vs M3E）
- Prompt 模板对比
- Rerank 策略对比

---

## 八、LangGraph 应用

### 8.1 LangGraph 核心概念

**五大核心能力**：
1. **持久化执行**：失败后从断点恢复，支持长时任务
2. **人机协同**：关键节点人工拦截、修改状态
3. **全方位记忆**：跨会话持久化
4. **调试支持**：可视化执行流程
5. **生产级部署**：可扩展有状态系统

### 8.2 LangGraph 对象

| 对象 | 作用 |
|------|------|
| Node | 执行单元（Function/Runnable） |
| Edge | 节点连接（Conditional/Static） |
| State | 在节点间流转的共享状态 |
| Graph | 编译后的可执行图 |

---

## 九、技术选型总结

### 9.1 Embedding 模型选择

| 模型 | 语言 | 维度 | 特点 |
|------|------|------|------|
| BGE-M3 | 中英 | 1024 | 支持长文本，多语言 |
| M3E | 中英 | 1536 | 多语言统一空间 |
| OpenAI-embedding-3 | 英文为主 | 1536 | 精度高，商用首选 |
| Yuan-embedding | 中文 | 512 | 小体积，中文场景 |

### 9.2 向量数据库选择

| 数据库 | 特点 | 适用规模 |
|--------|------|----------|
| Milvus | 支持混合检索，分布式 | 亿级 |
| Chroma | 轻量，LangChain 集成好 | 千万级 |
| Qdrant | 高性能，支持过滤 | 千万级 |
| Weaviate | 混合搜索，原生 GraphQL | 千万级 |

### 9.3 LLM 选择

| 模型 | 适用场景 | 成本 |
|------|----------|------|
| GPT-4 | 高质量生成，复杂推理 | 高 |
| Claude-3.5 | 长上下文，学术写作 | 高 |
| Qwen2.5 | 中文场景，开源可控 | 低 |
| LLaMA-3 | 通用场景 | 中 |

---

## 十、常见陷阱与最佳实践

### 10.1 检索端陷阱

1. **向量检索的语义相似陷阱**：产品编号、错误码等精确信息匹配差
   - 解决：混合搜索 + BM25 补充

2. **分块大小失衡**：太小丢上下文，太大引入噪声
   - 解决：Parent-Child 策略，小块检索大块返回

3. **上下文稀释**：大 chunk 淹没关键信息
   - 解决：控制 chunk 在 512-1024 token

### 10.2 生成端陷阱

1. **幻觉**：LLM 编造不存在的信息
   - 解决：强制要求引用上下文，Faithfulness 监控

2. **答非所问**：检索相关但非目标
   - 解决：Answer Relevance 监控，拒答策略

3. **上下文遗忘**：超长对话丢失早期信息
   - 解决：滑动窗口记忆，重要信息摘要

### 10.3 生产环境陷阱

1. **延迟过高**：检索+生成链路长
   - 解决：异步处理，预计算向量，并行化

2. **成本失控**：Token 消耗大
   - 解决：精确控制 context 长度，缓存复用

3. **效果不稳定**：无法量化优化
   - 解决：建立评估体系，A/B 测试驱动

### 10.4 最佳实践建议

1. **从简单开始**：先跑通流程，再逐步优化
2. **量化评估**：用 RAGAs 等框架建立评估基线
3. **真实测试**：用真实用户问题而非测试集
4. **监控链路**：端到端延迟、成本、质量三位一体
5. **渐进优化**：每次只改一个因素，验证效果
6. **拒答优先**：不确定时主动拒答，比答错好

---

## 十一、完整技术栈参考

```yaml
# 数据层
文档处理: Unstructured / PDFPlumber
分块: RecursiveCharacterTextSplitter
向量化: BGE-M3 / OpenAI-embedding

# 存储层
向量数据库: Milvus / Qdrant
元数据存储: PostgreSQL / Redis

# 检索层
向量检索: ANN (HNSW/IVF)
关键词检索: BM25 / ElasticSearch
重排序: BGE-Reranker

# Agent层
框架: LangGraph / LangChain
LLM: GPT-4 / Claude-3.5 / Qwen2.5

# 评估层
评估框架: RAGAs / TruLens
监控: Prometheus / Grafana

# 部署层
API服务: FastAPI
容器化: Docker / Kubernetes
```

---

## 十二、论文 Agent 落地建议

结合项目实际情况（统计学问答 + 论文写作），建议：

### 12.1 短期优先级

1. **QueryRouter 准确率**：优先解决路由错误问题，这是所有流程的入口
2. **PaperSearch 召回率**：确保不遗漏重要论文，使用混合检索
3. **置信度评估**：建立拒答机制，避免生成错误答案

### 12.2 中期优化

1. **多 Agent 协作**：参考双层 Supervisor 架构
2. **记忆管理**：短期/长期/情景记忆，支持语义检索
3. **质量评估**：建立 RAGAs 评估体系

### 12.3 长期目标

1. **知识图谱**：CDC-BERTopic 主题检测 + Graph-First RAG
2. **实时学习**：从用户反馈中持续优化
3. **多模态**：支持图表、公式的智能问答

---

## 参考资源

| 资源 | 说明 |
|------|------|
| [Anthropic: Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) | 核心设计原则 |
| [LangGraph Documentation](https://langchain.dev/langgraph) | 工作流编排 |
| [RAGAs Evaluation Framework](https://docs.ragas.io/) | RAG 评估工具 |
| [BGE-M3 Embedding Model](https://github.com/AI-Godel/BGE-M3) | 向量模型 |
| [arXiv API](https://arxiv.org/help/api) | 论文搜索 API |
| [PubMed E-utilities](https://www.ncbi.nlm.nih.gov/home/develop/api/) | 生物医学文献 API |

---

*本报告持续更新，如有问题请联系维护者。*