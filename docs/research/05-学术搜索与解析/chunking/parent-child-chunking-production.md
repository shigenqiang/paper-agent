# 父子分块生产实现调研报告

**调研时间**: 2026-06-01
**调研来源**: GitHub 开源项目源码、LlamaIndex/LangChain/Haystack/RAGFlow 官方实现、Anthropic/Vectara 技术文档、arXiv 学术论文

---

## 1. 核心架构

### 1.1 双集合存储模式

生产系统普遍采用**两个独立集合**存储父子块：

```
┌─────────────────────────────────────────┐
│  VectorDB                                │
│  ┌─────────────────┐  ┌──────────────┐  │
│  │ rt_children      │  │ rt_parents   │  │
│  │ (嵌入+检索)      │  │ (原文存储)    │  │
│  │                  │  │              │  │
│  │ child_001 ───────┼──→ parent_001  │  │
│  │ child_002 ───────┼──→ parent_001  │  │
│  │ child_003 ───────┼──→ parent_002  │  │
│  └─────────────────┘  └──────────────┘  │
└─────────────────────────────────────────┘
```

**关键设计**：
- 子块集合：存储嵌入向量，用于语义检索
- 父块集合：存储原文，不存储嵌入（节省成本）
- 子块通过 `parent_id` 元数据关联父块

### 1.2 检索流程

```
用户查询
    │
    ▼
嵌入查询 ──→ 子块集合 ──→ Top-K 子块
                              │
                              ▼
                        提取 parent_id
                              │
                              ▼
                        父块集合.get(parent_ids)
                              │
                              ▼
                        返回父块给 LLM
```

---

## 2. 开源框架实现

### 2.1 LangChain ParentDocumentRetriever

**来源**: GitHub `langchain-ai/langchain`

#### 核心组件

```python
from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import InMemoryStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

# 配置
child_splitter = RecursiveCharacterTextSplitter(chunk_size=400)
parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000)

# 创建检索器
retriever = ParentDocumentRetriever(
    vectorstore=Chroma(embedding_function=embeddings),
    docstore=InMemoryStore(),
    child_splitter=child_splitter,
    parent_splitter=parent_splitter,
)

# 索引文档
retriever.add_documents(documents)

# 检索
results = retriever.get_relevant_documents("query")
```

**关键设计**：
- 子块嵌入到向量库，父块原文存到 DocStore
- 支持多种向量数据库（Chroma、Pinecone、Qdrant 等）
- 比例：父块 2000 tokens / 子块 400 tokens = 5:1

### 2.2 LlamaIndex AutoMergingRetriever + HierarchicalNodeParser

**来源**: GitHub `run-llama/llama_index`

#### 多级层次结构

```python
# 默认三级分块
chunk_sizes = [2048, 512, 128]

# 每级使用 SentenceSplitter
for chunk_size in chunk_sizes:
    node_parser_map[chunk_size] = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=20,
    )
```

#### 递归分块逻辑

```python
def _recursively_get_nodes_from_nodes(self, nodes, level):
    sub_nodes = []
    for node in nodes:
        cur_sub_nodes = self.node_parser_map[level].get_nodes_from_documents([node])
        if level > 0:
            for sub_node in cur_sub_nodes:
                _add_parent_child_relationship(parent_node=node, child_node=sub_node)
        sub_nodes.extend(cur_sub_nodes)

    if level < len(self.node_parser_ids) - 1:
        sub_sub_nodes = self._recursively_get_nodes_from_nodes(sub_nodes, level + 1)
    else:
        sub_sub_nodes = []

    return sub_nodes + sub_sub_nodes
```

#### 合并策略（AutoMergingRetriever）

```python
def _get_parents_and_merge(self, nodes):
    parent_nodes = {}
    parent_cur_children_dict = defaultdict(list)

    for node in nodes:
        if node.node.parent_node is None:
            continue
        parent_node_id = node.node.parent_node.node_id
        if parent_node_id not in parent_nodes:
            parent_node = self._storage_context.docstore.get_document(parent_node_id)
            parent_nodes[parent_node_id] = parent_node
        parent_cur_children_dict[parent_node_id].append(node)

    for parent_node_id, parent_node in parent_nodes.items():
        parent_child_nodes = parent_node.child_nodes
        parent_num_children = len(parent_child_nodes) if parent_child_nodes else 1
        ratio = len(parent_cur_children_dict[parent_node_id]) / parent_num_children

        if ratio > self._simple_ratio_thresh:  # 默认 0.5
            # 合并为父节点
            avg_score = sum([n.get_score() for n in parent_cur_children]) / len(parent_cur_children)
            nodes_to_add[parent_node_id] = NodeWithScore(node=parent_node, score=avg_score)
```

**关键设计**：
- 支持多级层次（默认 3 级：2048 → 512 → 128）
- `simple_ratio_thresh = 0.5`：当检索到的子节点超过 50% 时合并为父节点
- 使用平均分数作为父节点的相似度分数

### 2.3 Haystack HierarchicalDocumentSplitter + AutoMergingRetriever

**来源**: GitHub `deepset-ai/haystack`

#### 分块配置

```python
from haystack.components.preprocessors import HierarchicalDocumentSplitter

splitter = HierarchicalDocumentSplitter(
    block_sizes={10, 3},  # 父块最多 10 词，子块最多 3 词
    split_overlap=0,
    split_by="word",
)

docs = splitter.run([original_document])
```

#### 元数据结构

每个文档自动生成层次元数据：
```python
Document(
    content="This is a simple test document",
    meta={
        'block_size': 0,
        'parent_id': None,
        'children_ids': ['5ff..', '8dc..'],
        'level': 0  # 0=根, 1=父块, 2=叶子子块
    }
)
```

#### AutoMergingRetriever 检索

```python
from haystack.components.retrievers.auto_merging_retriever import AutoMergingRetriever

# 存储叶子文档和父文档
leaf_doc_store = InMemoryDocumentStore()
parent_doc_store = InMemoryDocumentStore()

# 检索时，如果多个叶子文档匹配，合并为父文档
retriever = AutoMergingRetriever(
    leaf_doc_store=leaf_doc_store,
    parent_doc_store=parent_doc_store,
)
```

**关键设计**：
- `block_sizes` 参数定义层次级别（如 `{20, 5}` = 两级）
- 支持 `split_by`: "word", "sentence", "page", "passage"
- 文档自动携带 `parent_id`、`children_ids`、`level` 元数据

### 2.4 RAGFlow 父子分块机制

**来源**: GitHub `infiniflow/ragflow` (v0.23.0+)

#### 设计理念

RAGFlow 在 v0.23.0 引入父子分块机制，解决传统 "chunk-embed-retrieve" 流水线中的结构性矛盾：

> 单个文本块既要承担语义匹配（召回）又要承担上下文理解（利用）——两个本质上冲突的目标。召回需要细粒度、精确的块，而答案生成需要连贯、信息完整的上下文。

#### 实现特点

- **父块**：保持相对完整的语义单元，确保逻辑和背景完整性
- **子块**：从父块中进一步细分，用于精确召回
- **检索流程**：先基于子块定位最相关文本段，自动关联并召回父块
- **配置方式**：Web UI 中 "Child chunks are used for retrieval" 开关 + 子块分隔符

#### 配置参数

```json
{
  "parser_config": {
    "chunk_token_num": 512,
    "delimiter": "\n",
    "child_chunking": {
      "enabled": true,
      "delimiter": "\n"
    }
  }
}
```

**关键设计**：
- 与 TOC（目录）增强功能集成：LLM 生成文档结构，检索时自动补充缺失上下文
- 子块顺序可能与原文不一致（已知问题）
- SDK 检索目前只返回子块，Web UI 可返回父块（v0.23.1 限制）

---

## 3. 商业平台实现

### 3.1 Vectara — 句子窗口检索

**来源**: Vectara 官方文档

#### 核心理念

Vectara 从第一天就采用类似父子分块的策略：

> 全文档文本通过索引 API 发送，分块在后端自动完成。Vectara 使用高级 NLP 技术将文档分割成足够小的块，捕获干净的语义含义信号。查询时，用户可以通过 `sentences_before` 和 `sentences_after` 变量指定在小块周围包含多少上下文。

#### 实现方式

```python
# Vectara 集成 LangChain
from langchain_community.vectorstores import Vectara

# 自动分块 + 上下文窗口
vectara = Vectara.from_documents(documents)

# 查询时指定上下文窗口
results = vectara.similarity_search(
    query,
    sentences_before=3,  # 前 3 句
    sentences_after=3,   # 后 3 句
)
```

**关键设计**：
- 分块完全在后端自动完成
- 查询时动态调整上下文窗口大小
- 类似 LlamaIndex 的 `SentenceWindowNodeParser`

### 3.2 Anthropic Contextual Retrieval

**来源**: Anthropic 官方博客 + Claude Cookbook

#### 核心方法

Anthropic 提出 "Contextual Retrieval"，不是传统父子分块，但解决相同问题：

> 传统 RAG 解决方案在编码信息时移除上下文，导致系统无法从知识库中检索到相关信息。

#### 两种子技术

1. **Contextual Embeddings**：在每个块前添加文档级上下文描述
2. **Contextual BM25**：结合 BM25 关键词检索

#### 实现效果

- 减少 49% 的检索失败
- 结合 Reranking 后减少 67% 的检索失败

#### 成本计算

```
假设：800 token 块，8k token 文档，50 token 上下文指令，100 token 上下文
一次性上下文化成本：$1.02 / 百万文档 token
使用 Prompt Caching 后成本显著降低
```

**关键设计**：
- 不是传统父子分块，而是 "上下文增强分块"
- 使用 Claude 的 Prompt Caching 降低成本
- 结合 Voyage AI 嵌入 + Cohere Reranking

### 3.3 Unstructured.io — 上下文感知分块

**来源**: Unstructured 官方文档

#### 分块策略

Unstructured 提供多种智能分块策略：

1. **By Character**：顺序合并元素，最大化填充每个块
2. **By Title**：利用文档元素类型理解结构，保持章节边界
3. **By Page**：按页面分块
4. **By Similarity**：基于语义相似度分块
5. **Contextual Chunking**（2025 新增）：在每个块前添加上下文描述

#### Contextual Chunking 实现

```python
# 启用上下文分块
# 在 Chunker 节点设置中启用 Contextual chunking
# 上下文信息格式：
# Prefix: [上下文描述];
# Original: [原始块内容]
```

**关键设计**：
- 上下文信息通常为 2-3 句话
- 在生成嵌入之前应用
- 显著提高检索准确性

### 3.4 向量数据库支持

#### Pinecone

```python
# 使用 namespace 隔离父子块
index.upsert(vectors=[{
    "id": "child_001",
    "values": embedding,
    "metadata": {
        "parent_id": "parent_001",
        "text": "子块文本",
    }
}], namespace="children")

# 检索后通过 metadata 获取父块
results = index.query(vector=query_embedding, top_k=10)
parent_ids = [r.metadata["parent_id"] for r in results]
parents = index.fetch(ids=parent_ids, namespace="parents")
```

#### Weaviate

- 支持 hybrid search（dense + sparse）
- 通过 cross-reference 关联父子块
- `relativeScoreFusion` 保留原始搜索指标的细微差别

#### Qdrant

- 高性能元数据过滤（in-graph filtering）
- 支持 dense + sparse 向量混合检索
- 适合大规模自托管部署

---

## 4. 学术研究

### 4.1 HiChunk — 层次化分块评估框架

**来源**: arXiv 2509.11552v2

#### 核心贡献

1. **HiCBench**：评估分块方法对 RAG 全流水线影响的基准
2. **HiChunk**：文档层次化结构框架，允许 RAG 系统动态调整检索块的语义粒度

#### Auto-Merge 检索算法

```
遍历查询排序的块 C[1:M]sorted：
  1. 记录当前已用 token 预算: tk_cur = Σ len(n) for n in node_ret
  2. 将 C[i] 添加到 node_ret
  3. 获取 C[i] 的父节点 p
  4. 合并条件：
     - Cond1: p 的子节点与 node_ret 的交集 ≥ 2
     - Cond2: 交集中子节点的文本长度 ≥ θ*
       其中 θ*(tk_cur, p) = len(p)/3 × (1 + tk_cur/T)
       随着 tk_cur 增加，θ* 从 len(p)/3 渐增到 2×len(p)/3
```

**关键设计**：
- 排名越靠前的块越容易向上合并
- 自适应阈值 θ* 平衡语义丰富度和完整性
- 实验证明 HiChunk 在合理时间消耗内实现更好的分块质量

### 4.2 Hierarchical Parent-Child Retrieval for Multi-Turn RAG

**来源**: arXiv 2605.00631

#### 实现细节

```
文档分段：规则句子分割器
子块构建：3 句话滑动窗口，步长 2 句
嵌入模型：BAAI/bge-large-en-v1.5
重排序：BAAI/bge-reranker-v2-m3（余弦相似度）
初始候选集：k = 50 子块
父块聚合：maximum-score aggregation
最终返回：top-n = 5 父文档
向量存储：Weaviate hybrid（α = 0.7，70% dense + 30% sparse）
```

**关键设计**：
- 子块 = 3 句话重叠窗口
- 父块分数 = max(子块分数)（非平均）
- 混合检索：dense + sparse

### 4.3 Sentence Window Retrieval — ARAGOG 评测第一

**来源**: ARAGOG benchmark (2025)

在 ARAGOG 头对头评估中，Sentence Window Retrieval 在检索精度上排名第一，击败：
- HyDE
- Document Summary Index
- Multi-query
- MMR
- Cohere Rerank
- LLM Rerank

**实现方式**：
- 索引单个句子用于精确匹配
- 检索时返回句子周围的窗口用于生成上下文

---

## 5. 生产实现详细对比

### 5.1 分块参数对比

| 产品/框架 | 父块大小 | 子块大小 | 比例 | 分块单元 |
|-----------|----------|----------|------|----------|
| LangChain 默认 | 2000 tokens | 400 tokens | 5:1 | 字符递归 |
| LlamaIndex 三级 | 2048/512/128 tokens | - | 多级 | 句子 |
| Haystack | block_sizes={10,3} words | - | 多级 | 词/句子/段落 |
| RAGFlow | chunk_token_num | child delimiter | 可配 | token |
| rt-healthcare-rag | 2200 chars | 600 chars | 3.7:1 | 字符 |
| Anthropic Contextual | 800 tokens + 上下文 | - | - | token + 上下文 |
| arXiv 2605.00631 | 全文档 | 3 句话窗口 | - | 句子滑动窗口 |

### 5.2 Overlap 策略对比

| 产品/框架 | 父块 overlap | 子块 overlap | 说明 |
|-----------|-------------|-------------|------|
| LangChain | 可配 | 可配 | RecursiveCharacterTextSplitter |
| LlamaIndex | 20 tokens | 20 tokens | 固定值 |
| Haystack | split_overlap 参数 | split_overlap 参数 | 按词/句子单位 |
| rt-healthcare-rag | 200 chars (~10%) | 120 chars (~20%) | 字符级 |
| arXiv 2605.00631 | 无 | 步长 2 句（3 句窗口） | 句子级滑动 |

### 5.3 检索参数对比

| 产品/框架 | Top-K 子块 | 最大父块数 | 合并策略 |
|-----------|-----------|-----------|----------|
| rt-healthcare-rag | 12 | 4 | 去重取唯一 parent_id |
| LlamaIndex AutoMerging | 可配 | - | ratio > 0.5 合并 |
| Haystack AutoMerging | 可配 | - | 基于 threshold |
| arXiv 2605.00631 | 50 | 5 | maximum-score aggregation |
| HiChunk | 可配 | - | 自适应 θ* 阈值 |

### 5.4 存储方式对比

| 产品/框架 | 子块存储 | 父块存储 | 关联方式 |
|-----------|----------|----------|----------|
| LangChain | VectorStore | InMemoryStore | parent_id |
| LlamaIndex | VectorStore | DocStore | parent_node 关系 |
| Haystack | InMemoryDocumentStore | InMemoryDocumentStore | parent_id + children_ids 元数据 |
| RAGFlow | 内部存储 | 内部存储 | 父子关系内置 |
| rt-healthcare-rag | Chroma (children) | Chroma (parents) | parent_id 元数据 |
| Pinecone | namespace="children" | namespace="parents" | parent_id metadata |
| Weaviate | hybrid vector store | 同一 store | cross-reference |
| arXiv 2605.00631 | Weaviate | Weaviate | parent_id metadata |

---

## 6. 生产环境最佳实践

### 6.1 分块策略

1. **先切父块，再切子块**
   - 保证子块不跨父块边界
   - 父子关系清晰

2. **父块大小建议**
   - 学术论文：按章节分块（1500-3000 tokens）
   - 通用文档：按段落分块（1000-2000 tokens）
   - 对话记录：按轮次分块（500-1000 tokens）

3. **子块大小建议**
   - 200-600 tokens
   - 保证语义完整性
   - 实践表明 200 tokens 是实用最小值

4. **父子比例**
   - 推荐 3-5 倍（如 200-token 子块配 600-800-token 父块）

### 6.2 检索策略

1. **子块检索数量**
   - 通常 10-50 个（初筛）
   - arXiv 论文使用 k=50 初筛

2. **父块返回数量**
   - 通常 3-5 个
   - 避免超过 LLM 上下文窗口

3. **合并策略**
   - 比例阈值：0.3-0.5（LlamaIndex 默认 0.5）
   - Maximum-score aggregation（arXiv 论文验证有效）
   - 自适应阈值（HiChunk 的 θ* 策略）

4. **混合检索**
   - Dense + Sparse（BM25）结合
   - Weaviate α=0.7（70% dense + 30% sparse）
   - Anthropic: Contextual Embeddings + Contextual BM25

### 6.3 存储优化

1. **父块不存储嵌入**
   - 节省存储空间和嵌入成本
   - 父块只在检索后按需获取

2. **子块 ID 包含父块信息**
   - 如 `{parent_id}:{child_index}`
   - 便于快速定位父块

3. **元数据设计**
   - parent_id：关联父块
   - section_type：章节类型
   - source：来源文档
   - level：层次级别

### 6.4 2026 年新趋势

1. **上下文增强分块**（Anthropic/Unstructured）
   - 在块前添加文档级上下文描述
   - 减少 49-67% 检索失败

2. **混合检索 + Reranking**
   - Dense + Sparse + Reranking 三阶段
   - 检索质量提升 40-60%

3. **自适应分块**
   - 根据查询类型动态选择分块策略
   - 事实型查询 → 小块，分析型查询 → 大块

4. **多模态父子分块**
   - 支持图片、表格、公式的父子关系
   - 图片描述作为子块，图片作为父块

---

## 7. 与当前项目的对比

### 7.1 当前实现

```python
# parser_service.py
def _create_parent_chunks(self, child_chunks, paper_id, target_tokens=2000):
    # 按 section_type 分组
    # 连续同 section 的子块归为一组
    # 每组累积到 ~target_tokens 后创建 parent chunk
    # 子块记录 parent_id
```

**优点**：
- 按章节语义分块，保持语义完整性
- 支持多种 chunk_type

**可改进点**：
1. 父块大小固定（2000 tokens），可考虑动态调整
2. 缺少 overlap 策略
3. 检索时未实现比例合并策略
4. 未使用混合检索（dense + sparse）

### 7.2 改进建议

1. **增加父块 overlap**
   ```python
   # 当前：无 overlap
   # 建议：父块间 10% overlap
   PARENT_OVERLAP = int(target_tokens * 0.1)
   ```

2. **实现比例合并检索**（参考 LlamaIndex AutoMergingRetriever）
   ```python
   # 检索时，如果同一父块的子块超过 50%，返回父块
   if ratio > 0.5:
       return parent_chunk
   else:
       return child_chunks
   ```

3. **实现 Maximum-score 聚合**（参考 arXiv 2605.00631）
   ```python
   # 父块分数 = max(子块分数)，而非平均
   parent_score = max(child_scores)
   ```

4. **增加上下文增强**（参考 Anthropic Contextual Retrieval）
   ```python
   # 在每个子块前添加文档级上下文
   contextual_chunk = f"文档: {doc_title}, 章节: {section_name}\n{chunk_text}"
   ```

5. **支持混合检索**
   ```python
   # Dense + BM25 + Reranking
   dense_results = vector_search(query, top_k=50)
   bm25_results = bm25_search(query, top_k=50)
   merged = rrf_fusion(dense_results, bm25_results)
   reranked = reranker.rerank(query, merged, top_k=10)
   ```

---

## 8. 参考资料

### 开源框架
1. **LangChain ParentDocumentRetriever** - github.com/langchain-ai/langchain
2. **LlamaIndex AutoMergingRetriever** - github.com/run-llama/llama_index
3. **LlamaIndex HierarchicalNodeParser** - github.com/run-llama/llama_index
4. **Haystack HierarchicalDocumentSplitter** - github.com/deepset-ai/haystack
5. **RAGFlow** - github.com/infiniflow/ragflow (v0.23.0+)
6. **rt-healthcare-rag** - GitHub Charan-Ellendula/rt-healthcare-rag

### 商业平台
7. **Anthropic Contextual Retrieval** - anthropic.com/engineering/contextual-retrieval
8. **Vectara Chunking** - vectara.com/blog/grounded-generation-done-right-chunking
9. **Unstructured.io** - docs.unstructured.io/concepts/chunking
10. **Pinecone** - Parent-Child Vector (community.pinecone.io)

### 学术论文
11. **HiChunk** - arXiv 2509.11552v2 (2025)
12. **Hierarchical Parent-Child Retrieval for Multi-Turn RAG** - arXiv 2605.00631 (2026)
13. **ARAGOG Benchmark** - Sentence Window Retrieval 评测第一

### 技术博客
14. **RAG Chunking Strategies 2026** - daily.dev
15. **Chunking Strategies for RAG** - Firecrawl (2026)
16. **12 Advanced RAG Techniques** - Atlan (2026)
17. **Improving Retrieval with Auto-Merging** - Haystack Blog
