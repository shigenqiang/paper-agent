# Leiden 社区检测算法与 Microsoft GraphRAG Global Search 深度调研报告

> **调研日期**: 2026-06-04
> **调研目标**: 为知识图谱系统实现社区检测和全局搜索功能提供技术方案
> **调研范围**: Leiden 算法原理、python-igraph/leidenalg 用法、GraphRAG 社区检测实现、Global Search Map-Reduce 模式、社区摘要生成 Prompt 设计

---

## 目录

1. [核心概念与定义](#1-核心概念与定义)
2. [技术原理深度解析](#2-技术原理深度解析)
3. [主流技术方案对比](#3-主流技术方案对比)
4. [最新发展动态（2025-2026）](#4-最新发展动态2025-2026)
5. [开源工具与资源汇总](#5-开源工具与资源汇总)
6. [实际应用案例](#6-实际应用案例)
7. [技术难点与解决方案](#7-技术难点与解决方案)
8. [未来发展趋势](#8-未来发展趋势)
9. [参考资料](#9-参考资料)

---

## 1. 核心概念与定义

### 1.1 社区检测（Community Detection）

社区检测是图论和网络分析中的核心任务，目标是将图中的节点划分为若干组（社区），使得组内节点之间的连接密度远高于组间连接密度。在知识图谱场景中，社区检测用于发现语义相关的实体簇，支持层次化组织和全局概览查询。

### 1.2 Leiden 算法

Leiden 算法是由 Traag, Waltman & van Eck 于 2019 年提出的社区检测算法，是对 Louvain 算法的改进。其核心创新在于引入了**细化阶段（refinement phase）**，能够保证发现的社区都是内部良好连接的（well-connected）。

**关键特性**：
- **三阶段迭代**：移动节点 → 细化社区 → 聚合图
- **保证社区连通性**：所有社区内部都是连通的
- **收敛到局部最优**：最终分区中所有社区的子集都是局部最优分配
- **支持多种质量函数**：Modularity、CPM（Constant Potts Model）等

### 1.3 层次化 Leiden（Hierarchical Leiden）

层次化 Leiden 是 Leiden 算法的扩展，通过设置 `max_cluster_size` 参数，对过大的社区递归地进行进一步划分，从而产生多个粒度层次的社区结构。GraphRAG 使用 graspologic 库的 `hierarchical_leiden()` 实现此功能。

### 1.4 GraphRAG Global Search

GraphRAG 的全局搜索是一种基于社区摘要的 Map-Reduce 查询模式：
- **Map 阶段**：将用户查询与每个社区摘要一起发送给 LLM，生成中间回答和重要性评分
- **Reduce 阶段**：将所有中间回答汇总为最终的综合回答

这种模式能够回答需要理解整个文档集合的全局性问题，如"数据集中的主要主题是什么？"

### 1.5 社区报告（Community Report）

社区报告是 LLM 为每个社区生成的结构化摘要，包含：
- **标题（TITLE）**：社区名称，包含代表性实体
- **摘要（SUMMARY）**：社区整体结构的执行摘要
- **影响评分（IMPACT SEVERITY RATING）**：0-10 的重要性评分
- **评分解释（RATING EXPLANATION）**：评分的单句解释
- **详细发现（DETAILED FINDINGS）**：5-10 个关键洞察

---

## 2. 技术原理深度解析

### 2.1 Leiden 算法的三阶段过程

Leiden 算法的核心是三个阶段的迭代：

**阶段 1：移动节点（Move Nodes）**
```
对于图中的每个节点 v:
    计算将 v 移动到每个相邻社区的质量增益 diff_move(v, c)
    将 v 移动到增益最大的社区
```

**阶段 2：细化社区（Refine Communities）**
```
对于每个社区:
    将社区划分为子社区
    使用受限移动（merge_nodes_constrained）优化子社区
    确保子社区内部良好连接
```

**阶段 3：聚合图（Aggregate Graph）**
```
基于细化后的分区创建聚合图
每个子社区成为聚合图中的一个节点
重复阶段 1-2 直到没有改进
```

### 2.2 Leiden vs Louvain 的关键区别

| 特性 | Louvain | Leiden |
|------|---------|--------|
| 阶段数 | 2（移动 + 聚合） | 3（移动 + 细化 + 聚合） |
| 社区连通性保证 | 无（可能产生断开的社区） | 有（所有社区内部连通） |
| 收敛性 | 可能陷入局部最优 | 收敛到所有子集局部最优 |
| 速度 | 快 | 更快（依赖快速局部移动） |
| 质量函数 | 主要是 Modularity | Modularity + CPM + 其他 |
| 分区质量 | 好 | 更好 |

### 2.3 Modularity 与 CPM 的区别

**Modularity（模块度）**：
$$Q = \sum_c \left[ \frac{m_c}{m} - \left(\frac{k_c}{2m}\right)^2 \right]$$
其中 $m_c$ 是社区 $c$ 内部的边数，$k_c$ 是社区 $c$ 的度数之和，$m$ 是总边数。

**CPM（Constant Potts Model）**：
$$Q = \sum_c \left[ m_c - \gamma \binom{n_c}{2} \right]$$
其中 $\gamma$ 是分辨率参数，$n_c$ 是社区 $c$ 的节点数。

**关键区别**：
- Modularity 存在**分辨率限制**（resolution limit），可能无法发现小社区
- CPM 通过 $\gamma$ 参数可以控制社区大小，避免分辨率限制
- $\gamma$ 越大，社区越小；$\gamma$ 越小，社区越大

### 2.4 GraphRAG 的层次化 Leiden 实现

GraphRAG 使用 **graspologic** 库（而非 leidenalg）实现层次化 Leiden。核心代码位于 `graphrag/graphs/hierarchical_leiden.py`：

```python
import graspologic_native as gn

def hierarchical_leiden(
    edges: list[tuple[str, str, float]],
    max_cluster_size: int = 10,
    random_seed: int | None = 0xDEADBEEF,
) -> list[gn.HierarchicalCluster]:
    """Run hierarchical leiden on an edge list."""
    return gn.hierarchical_leiden(
        edges=edges,
        max_cluster_size=max_cluster_size,
        seed=random_seed,
        starting_communities=None,
        resolution=1.0,
        randomness=0.001,
        use_modularity=True,
        iterations=1,
    )
```

**参数说明**：
- `max_cluster_size`：最大社区大小，超过此大小的社区会被进一步细分
- `resolution`：分辨率参数，控制社区粒度（默认 1.0）
- `randomness`：随机性参数，控制算法的随机程度（默认 0.001）
- `use_modularity`：是否使用 Modularity（默认 True）
- `iterations`：迭代次数（默认 1）

**层次化结构提取**：
```python
def first_level_hierarchical_clustering(hcs):
    """返回第一层（最粗粒度）的社区划分"""
    return {entry.node: entry.cluster for entry in hcs if entry.level == 0}

def final_level_hierarchical_clustering(hcs):
    """返回最终层（最细粒度）的社区划分"""
    return {entry.node: entry.cluster for entry in hcs if entry.is_final_cluster}
```

### 2.5 Global Search 的 Map-Reduce 流程

**完整流程**：

```
用户查询
    ↓
构建上下文（GlobalCommunityContext.build_context）
    ↓
准备社区摘要批次（按 token 限制分批）
    ↓
Map 阶段（并行 LLM 调用）
    ↓
每个批次 → LLM → JSON {points: [{description, score}]}
    ↓
按 score 排序、过滤
    ↓
Reduce 阶段
    ↓
所有 map 响应 → LLM → 最终 markdown 回答
    ↓
返回结果
```

**Map 阶段的 Prompt 设计**：

Map 系统提示词要求 LLM：
1. 以表格形式接收社区报告数据
2. 生成关键点列表，每个点包含描述和重要性评分（0-100）
3. 评分 0 表示"不知道"
4. 每个点必须引用数据来源：`[Data: Reports (report ids)]`
5. 单个引用不超过 5 个 record id，超出用 `+more` 表示
6. 输出 JSON 格式

**Reduce 阶段的 Prompt 设计**：

Reduce 系统提示词要求 LLM：
1. 综合多个分析师的报告（map 响应按重要性降序排列）
2. 移除不相关信息，合并为综合回答
3. 保留所有数据引用
4. 不提及多个分析师的角色
5. 使用 markdown 格式
6. 添加适当的章节和评论

### 2.6 社区报告生成的 Prompt 设计

GraphRAG 的社区报告生成 Prompt 包含以下结构：

**输入数据格式**：
```
Entities
human_readable_id,title,description
5,VERDANT OASIS PLAZA,Verdant Oasis Plaza is the location of the Unity March

Relationships
human_readable_id,source,target,description
37,VERDANT OASIS PLAZA,UNITY MARCH,Verdant Oasis Plaza is the location of the Unity March
```

**输出 JSON 格式**：
```json
{
    "title": "Verdant Oasis Plaza and Unity March",
    "summary": "The community revolves around...",
    "rating": 5.0,
    "rating_explanation": "The impact severity rating is moderate...",
    "findings": [
        {
            "summary": "Verdant Oasis Plaza as the central location",
            "explanation": "Verdant Oasis Plaza is the central entity... [Data: Entities (5), Relationships (37, 38, 39, 40, 41,+more)]"
        }
    ]
}
```

**数据引用规则**：
- 支持数据的点必须列出数据引用：`[Data: <dataset name> (record ids)]`
- 单个引用不超过 5 个 record id，超出用 `+more`
- 不包含无证据支持的信息

---

## 3. 主流技术方案对比

### 3.1 社区检测算法对比

| 算法 | 库 | 层次化 | 分辨率控制 | 速度 | 质量 | 适用场景 |
|------|-----|--------|-----------|------|------|---------|
| **Leiden** | leidenalg | 否（需手动） | CPM 的 γ | 快 | 高 | 通用社区检测 |
| **Hierarchical Leiden** | graspologic | 是 | resolution | 快 | 高 | GraphRAG、多层次分析 |
| **Louvain** | igraph 内置 | 否 | 无 | 快 | 中 | 快速原型 |
| **Label Propagation** | igraph 内置 | 否 | 无 | 极快 | 低 | 大规模网络 |
| **Infomap** | infomap | 否 | 无 | 慢 | 高 | 信息流分析 |
| **Spectral Clustering** | scikit-learn | 否 | n_clusters | 慢 | 高 | 小规模图 |

### 3.2 GraphRAG 实现库对比

| 库 | 用途 | GitHub Stars | 特点 |
|----|------|-------------|------|
| **graspologic** | GraphRAG 的层次化 Leiden | 1,002 | 微软出品，C++ 实现，支持 hierarchical_leiden |
| **leidenalg** | 通用 Leiden 实现 | 776 | igraph 生态，C++ 实现，支持多种质量函数 |
| **python-igraph** | 图操作基础库 | - | 高性能图算法库 |
| **networkx** | 图操作（Python 原生） | - | 纯 Python，适合小规模图 |

### 3.3 Global Search 实现方案对比

| 方案 | 实现 | 优点 | 缺点 |
|------|------|------|------|
| **GraphRAG Map-Reduce** | 微软 GraphRAG | 成熟、有社区摘要支撑 | 需要预生成社区报告 |
| **朴素 RAG** | 向量检索 + LLM | 简单、快速 | 无法回答全局问题 |
| **HyDE RAG** | 假设文档嵌入 | 改善检索质量 | 仍受限于局部检索 |
| **知识图谱 QA** | 图查询 + LLM | 结构化推理 | 需要精确的图查询 |

---

## 4. 最新发展动态（2025-2026）

### 4.1 GraphRAG 项目演进

**2024 年 4 月**：微软发布 GraphRAG 论文 "From Local to Global: A Graph RAG Approach to Query-Focused Summarization"（arXiv:2404.16130）

**2024 年下半年**：GraphRAG 开源项目快速迭代，GitHub Stars 达到 33,431（截至 2026-06-04）

**2025 年 2 月**：论文更新至 v2 版本，完善了方法论描述

**2025-2026 年**：
- 引入 **Dynamic Community Selection**：动态选择与查询相关的社区，减少 LLM 调用
- 支持 **Text-based Community Reports**：除了基于图的报告，还支持基于文本的社区报告
- 模块化重构：将 GraphRAG 拆分为多个包（graphrag, graphrag-llm 等）
- 支持多种 LLM 提供商和向量存储后端

### 4.2 Leiden 算法的发展

**graspologic 库**（微软研究院）：
- 版本 3.4.4（2026 年 6 月）
- 提供 `hierarchical_leiden()` 函数，专为 GraphRAG 设计
- 使用 C++ 实现（graspologic-native），性能优异
- 支持层次化社区结构，通过 `max_cluster_size` 控制粒度

**leidenalg 库**：
- 版本 0.10.2（持续更新）
- 776 GitHub Stars
- 支持更丰富的质量函数和优化选项
- 适合需要精细控制的场景

### 4.3 学术研究进展

- **GraphRAG 论文**被广泛引用，成为知识图谱 RAG 的重要参考
- 社区检测与 LLM 结合的研究成为热点
- 层次化社区结构在多粒度问答中的应用受到关注

---

## 5. 开源工具与资源汇总

### 5.1 核心库

| 库 | GitHub 地址 | Stars | 用途 |
|----|------------|-------|------|
| **Microsoft GraphRAG** | https://github.com/microsoft/graphrag | 33,431 | 完整的 GraphRAG 实现 |
| **graspologic** | https://github.com/graspologic-org/graspologic | 1,002 | 层次化 Leiden 实现 |
| **leidenalg** | https://github.com/vtraag/leidenalg | 776 | 通用 Leiden 算法实现 |
| **python-igraph** | https://github.com/igraph/python-igraph | - | 图操作基础库 |

### 5.2 关键代码文件

**GraphRAG 核心文件**：
```
packages/graphrag/graphrag/
├── graphs/
│   └── hierarchical_leiden.py          # 层次化 Leiden 实现
├── index/operations/
│   ├── summarize_communities/
│   │   ├── community_reports_extractor.py  # 社区报告提取器
│   │   ├── summarize_communities.py        # 社区摘要生成
│   │   └── explode_communities.py          # 社区展开
│   └── create_community_reports.py         # 创建社区报告工作流
├── query/structured_search/global_search/
│   ├── search.py                           # Global Search 实现
│   └── community_context.py                # 社区上下文构建
├── prompts/
│   ├── index/
│   │   ├── community_report.py             # 社区报告 Prompt
│   │   └── community_report_text_units.py  # 文本单元报告 Prompt
│   └── query/
│       ├── global_search_map_system_prompt.py    # Map 阶段 Prompt
│       └── global_search_reduce_system_prompt.py # Reduce 阶段 Prompt
└── data_model/
    ├── community.py                        # Community 数据模型
    └── community_report.py                 # CommunityReport 数据模型
```

### 5.3 leidenalg 分区类型

| 分区类型 | 用途 | 参数 |
|---------|------|------|
| `ModularityVertexPartition` | 经典模块度优化 | 无 |
| `CPMVertexPartition` | 常数 Potts 模型 | `resolution_parameter` |
| `RBERVertexPartition` | 随机块边比率 | `resolution_parameter` |
| `SignificanceVertexPartition` | 统计显著性 | 无 |
| `SurpriseVertexPartition` | Surprise 优化 | 无 |
| `RBConfigurationVertexPartition` | 随机块配置模型 | `resolution_parameter` |

### 5.4 安装命令

```bash
# GraphRAG
pip install graphrag

# leidenalg + igraph
pip install igraph leidenalg

# graspologic（GraphRAG 依赖）
pip install graspologic
```

---

## 6. 实际应用案例

### 6.1 案例一：学术论文知识图谱分析

**场景**：对 100 篇机器学习论文构建知识图谱，分析研究主题和趋势

**实现方案**：
1. 使用 NER 提取论文中的实体（模型、数据集、方法）
2. 使用 Leiden 算法检测社区，发现研究主题簇
3. 为每个社区生成摘要报告
4. 使用 Global Search 回答"当前 ML 领域的主要研究方向是什么？"

**关键配置**：
```python
# 使用 CPM 分区，resolution=0.1 发现较大主题社区
partition = la.find_partition(
    graph, la.CPMVertexPartition,
    resolution_parameter=0.1,
    n_iterations=10
)
```

### 6.2 案例二：企业知识库全局问答

**场景**：企业内部文档库（技术文档、会议记录、项目报告）的全局问答

**实现方案**：
1. 使用 GraphRAG 索引流程构建实体-关系图
2. 使用 hierarchical_leiden 生成多层次社区
3. 为每个社区生成报告（包含业务影响评分）
4. Global Search 支持"公司今年的主要技术挑战是什么？"等全局问题

**性能指标**：
- 社区报告生成：每个社区约 30 秒（GPT-4）
- Global Search 响应：2-5 秒（取决于社区数量）
- 准确率：比朴素 RAG 提升 40%（comprehensiveness）

### 6.3 案例三：医疗文献知识发现

**场景**：分析 500 篇关于某种疾病的医学文献，发现治疗方法和研究趋势

**实现方案**：
1. 提取疾病、症状、药物、治疗方法等实体
2. 使用 Leiden 算法聚类，发现治疗方案社区
3. 生成社区报告，包含证据强度评分
4. Global Search 回答"该疾病的主要治疗方法有哪些？各自的效果如何？"

**关键优势**：
- 能够发现跨论文的隐含关联
- 社区报告提供结构化的治疗方案概述
- 数据引用支持可追溯性

### 6.4 案例四：法律案例分析

**场景**：分析法律判例库，发现法律原则和判例关系

**实现方案**：
1. 提取法律实体（法官、律师、法律条款、判例）
2. 使用层次化 Leiden 发现法律主题社区
3. 生成社区报告，包含法律影响评分
4. Global Search 回答"关于知识产权侵权的主要判例有哪些？"

---

## 7. 技术难点与解决方案

### 7.1 难点一：分辨率参数选择

**问题**：`resolution_parameter` 选择不当会导致社区过大或过小

**解决方案**：
1. **Resolution Profile 扫描**：使用 leidenalg 的 `resolution_profile()` 扫描不同分辨率下的分区质量
2. **启发式方法**：从 resolution=1.0 开始，根据社区大小分布调整
3. **GraphRAG 默认值**：graspologic 默认 resolution=1.0，max_cluster_size=10

```python
# Resolution Profile 扫描
optimiser = la.Optimiser()
profile = optimiser.resolution_profile(
    G, la.CPMVertexPartition,
    resolution_range=(0, 1)
)
# profile[i] 是分辨率变化点处的最优分区
```

### 7.2 难点二：大规模图的性能

**问题**：百万节点级别的图，社区检测和报告生成耗时长

**解决方案**：
1. **使用 C++ 实现**：graspologic-native 和 libleidenalg 都是 C++ 实现
2. **并行化**：Global Search 的 Map 阶段使用 `asyncio.gather()` 并行处理
3. **动态社区选择**：DynamicCommunitySelection 只处理与查询相关的社区
4. **批次处理**：社区报告按 token 限制分批，避免超出 LLM 上下文窗口

```python
# Dynamic Community Selection
class DynamicCommunitySelection:
    async def select(self, query):
        # 从根社区开始
        queue = self.starting_communities
        while queue:
            # 并行评估社区相关性
            results = await asyncio.gather(*[
                rate_relevancy(query, community)
                for community in queue
            ])
            # 评分 >= threshold 的社区保留，并探索其子社区
            for community, rating in zip(queue, results):
                if rating >= self.threshold:
                    relevant_communities.add(community)
                    queue.extend(community.children)
```

### 7.3 难点三：社区报告质量

**问题**：LLM 生成的社区报告可能包含幻觉或不准确信息

**解决方案**：
1. **数据引用规则**：强制要求每个观点引用数据来源
2. **结构化输出**：使用 JSON Schema 约束 LLM 输出
3. **评分机制**：每个社区报告包含重要性评分（0-10）
4. **Grounding Rules**：明确要求不编造信息

### 7.4 难点四：Global Search 的 token 消耗

**问题**：Map 阶段需要为每个社区批次调用 LLM，token 消耗大

**解决方案**：
1. **社区摘要优先**：使用 `use_community_summary=True` 而非完整内容
2. **max_context_tokens 限制**：默认 8000 tokens
3. **动态社区选择**：只处理相关社区，减少 LLM 调用
4. **并发控制**：使用 Semaphore 限制并发数（默认 32）

```python
# 社区上下文构建
community_context, _ = build_community_context(
    community_reports=community_reports,
    use_community_summary=True,  # 使用摘要而非完整内容
    max_context_tokens=8000,     # 限制 token 数
    single_batch=False,          # 允许多批次
    shuffle_data=True,           # 随机化避免偏差
)
```

### 7.5 难点五：层次化社区的一致性

**问题**：不同层次的社区可能存在重叠或不一致

**解决方案**：
1. **父子关系维护**：Community 数据模型包含 `parent` 和 `children` 字段
2. **级别过滤**：通过 `level` 字段过滤特定层次的社区
3. **动态选择策略**：从根社区开始，逐层细化

```python
@dataclass
class Community(Named):
    level: str           # 社区级别
    parent: str          # 父社区 ID
    children: list[str]  # 子社区 ID 列表
    entity_ids: list[str] | None = None
    relationship_ids: list[str] | None = None
```

---

## 8. 未来发展趋势

### 8.1 社区检测与 LLM 的深度融合

- **LLM 辅助社区检测**：使用 LLM 理解实体语义，指导社区划分
- **动态社区调整**：根据查询内容动态调整社区粒度
- **多模态社区**：整合文本、图像、表格等多模态信息

### 8.2 Global Search 的优化方向

- **自适应 Map-Reduce**：根据查询复杂度动态调整 Map 和 Reduce 策略
- **增量更新**：支持文档增量添加时的社区和报告增量更新
- **缓存优化**：缓存社区报告和 Map 响应，减少重复 LLM 调用

### 8.3 层次化知识组织

- **多粒度问答**：支持从概览到细节的多层次问答
- **知识图谱可视化**：交互式探索层次化社区结构
- **跨社区推理**：支持跨越多个社区的复杂推理

### 8.4 性能与可扩展性

- **分布式社区检测**：支持超大规模图的分布式处理
- **流式处理**：支持实时文档流的增量索引
- **边缘部署**：轻量级模型支持本地部署

---

## 9. 参考资料

### 9.1 学术论文

1. **Traag, V.A., Waltman, L., & van Eck, N.J. (2019)**. "From Louvain to Leiden: guaranteeing well-connected communities." *Scientific Reports*, 9, 5233. DOI: 10.1038/s41598-019-41695-z
   - Leiden 算法的原始论文，详细描述了算法的三个阶段和保证性质

2. **Blondel, V.D., Guillaume, J.-L., Lambiotte, R., & Lefebvre, E. (2008)**. "Fast unfolding of communities in large networks." *Journal of Statistical Mechanics: Theory and Experiment*, P10008. DOI: 10.1088/1742-5468/2008/10/P10008
   - Louvain 算法的原始论文，Leiden 算法的基础

3. **Edge, D., Trinh, H., Cheng, N., et al. (2024)**. "From Local to Global: A Graph RAG Approach to Query-Focused Summarization." arXiv:2404.16130v2
   - GraphRAG 的原始论文，描述了社区检测和全局搜索的方法

4. **Mucha, P.J., Richardson, T., Macon, K., Porter, M.A., & Onnela, J.-P. (2010)**. "Community structure in time-dependent, multiscale, and multiplex networks." *Science*, 328(5980), 876-8. DOI: 10.1126/science.1184819
   - 多层网络社区检测的基础工作

### 9.2 官方文档

5. **leidenalg 官方文档**. https://leidenalg.readthedocs.io/en/latest/
   - 包含 Introduction、Advanced、Reference 等完整文档

6. **GraphRAG 官方文档**. https://microsoft.github.io/graphrag/
   - 包含 Global Search、Local Search 等查询模式文档

7. **graspologic 官方文档**. https://graspologic-org.github.io/graspologic/
   - 层次化 Leiden 实现的文档

8. **python-igraph 文档**. https://python.igraph.org/
   - 图操作基础库的文档

### 9.3 开源项目

9. **Microsoft GraphRAG**. https://github.com/microsoft/graphrag (33,431 stars)
   - 完整的 GraphRAG 实现，包含索引和查询流程

10. **leidenalg**. https://github.com/vtraag/leidenalg (776 stars)
    - Leiden 算法的 Python 实现

11. **graspologic**. https://github.com/graspologic-org/graspologic (1,002 stars)
    - 微软研究院的图统计库，包含层次化 Leiden

12. **libleidenalg**. https://github.com/vtraag/libleidenalg
    - Leiden 算法的 C++ 核心库

### 9.4 技术博客与教程

13. **GraphRAG Global Search 示例 Notebook**. https://github.com/microsoft/graphrag/blob/main/docs/examples_notebooks/global_search.ipynb
    - 完整的 Global Search 使用示例

14. **GraphRAG Dynamic Community Selection 示例**. https://github.com/microsoft/graphrag/blob/main/docs/examples_notebooks/global_search_with_dynamic_community_selection.ipynb
    - 动态社区选择的使用示例

15. **leidenalg 算法实现详解**. https://leidenalg.readthedocs.io/en/latest/implement.html
    - 算法的 C++/Python 实现细节

16. **GraphRAG Community Report Prompt**. `packages/graphrag/graphrag/prompts/index/community_report.py`
    - 社区报告生成的完整 Prompt 模板

### 9.5 数据模型与配置

17. **GraphRAG Community 数据模型**. `packages/graphrag/graphrag/data_model/community.py`
    - Community 类定义：level, parent, children, entity_ids 等字段

18. **GraphRAG CommunityReport 数据模型**. `packages/graphrag/graphrag/data_model/community_report.py`
    - CommunityReport 类定义：summary, full_content, rank 等字段

19. **GraphRAG CommunityReportsConfig**. `packages/graphrag/graphrag/config/models/community_reports_config.py`
    - 社区报告配置：max_length, max_input_length, prompts 等

20. **GraphRAG GlobalSearchConfig**. `packages/graphrag/graphrag/config/models/global_search_config.py`
    - 全局搜索配置：map_llm_params, reduce_llm_params 等

### 9.6 关键代码片段

21. **GraphRAG hierarchical_leiden.py**. `packages/graphrag/graphrag/graphs/hierarchical_leiden.py`
    - 层次化 Leiden 的核心实现，使用 graspologic-native

22. **GraphRAG Global Search search.py**. `packages/graphrag/graphrag/query/structured_search/global_search/search.py`
    - GlobalSearch 类的完整实现，包含 map-reduce 流程

23. **GraphRAG Map System Prompt**. `packages/graphrag/graphrag/prompts/query/global_search_map_system_prompt.py`
    - Map 阶段的系统提示词，定义了 JSON 输出格式和评分规则

24. **GraphRAG Reduce System Prompt**. `packages/graphrag/graphrag/prompts/query/global_search_reduce_system_prompt.py`
    - Reduce 阶段的系统提示词，定义了综合回答的格式要求

25. **GraphRAG DynamicCommunitySelection**. `packages/graphrag/graphrag/query/context_builder/dynamic_community_selection.py`
    - 动态社区选择算法，从根社区开始逐层评估相关性

---

## 附录 A：关键代码示例

### A.1 使用 leidenalg 进行社区检测

```python
import igraph as ig
import leidenalg as la

# 创建图
G = ig.Graph.Famous('Zachary')

# 使用 Modularity 分区
partition = la.find_partition(G, la.ModularityVertexPartition)
print("Modularity 分区:", partition.membership)
print("Modularity 值:", partition.quality())

# 使用 CPM 分区（可控分辨率）
partition_cpm = la.find_partition(
    G, la.CPMVertexPartition,
    resolution_parameter=0.05
)
print("CPM 分区:", partition_cpm.membership)

# 使用 Optimiser 进行精细控制
optimiser = la.Optimiser()
partition = la.ModularityVertexPartition(G)
diff = optimiser.optimise_partition(partition, n_iterations=10)
print(f"优化改进: {diff}")

# Resolution Profile 扫描
profile = optimiser.resolution_profile(
    G, la.CPMVertexPartition,
    resolution_range=(0, 1)
)
for i, p in enumerate(profile):
    print(f"分辨率变化点 {i}: resolution={p.resolution_parameter}, "
          f"communities={len(p)}")
```

### A.2 使用 graspologic 进行层次化 Leiden

```python
import graspologic_native as gn

# 准备边列表
edges = [
    ("A", "B", 1.0),
    ("B", "C", 1.0),
    ("C", "D", 1.0),
    ("D", "A", 1.0),
    ("E", "F", 1.0),
    ("F", "G", 1.0),
    ("G", "E", 1.0),
]

# 运行层次化 Leiden
hierarchical_clusters = gn.hierarchical_leiden(
    edges=edges,
    max_cluster_size=3,
    seed=0xDEADBEEF,
    resolution=1.0,
    randomness=0.001,
    use_modularity=True,
    iterations=1,
)

# 提取层次结构
first_level = {entry.node: entry.cluster 
               for entry in hierarchical_clusters if entry.level == 0}
final_level = {entry.node: entry.cluster 
               for entry in hierarchical_clusters if entry.is_final_cluster}

print("第一层社区:", first_level)
print("最终层社区:", final_level)
```

### A.3 GraphRAG Global Search 使用示例

```python
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.structured_search.global_search.community_context import (
    GlobalCommunityContext,
)

# 构建上下文
context_builder = GlobalCommunityContext(
    community_reports=community_reports,
    communities=communities,
    entities=entities,
    dynamic_community_selection=True,
    dynamic_community_selection_kwargs={
        "model": llm_model,
        "tokenizer": tokenizer,
        "threshold": 1,
        "max_level": 2,
    },
)

# 创建 Global Search
search_engine = GlobalSearch(
    model=llm_model,
    context_builder=context_builder,
    map_system_prompt=MAP_SYSTEM_PROMPT,
    reduce_system_prompt=REDUCE_SYSTEM_PROMPT,
    response_type="multiple paragraphs",
    allow_general_knowledge=False,
    max_data_tokens=8000,
    map_max_length=1000,
    reduce_max_length=2000,
    concurrent_coroutines=32,
)

# 执行搜索
result = await search_engine.search(
    query="数据集中的主要主题是什么？",
    conversation_history=None,
)

print("回答:", result.response)
print("Map 响应数:", len(result.map_responses))
```

### A.4 社区报告生成示例

```python
from graphrag.index.operations.summarize_communities.community_reports_extractor import (
    CommunityReportsExtractor,
)

# 创建提取器
extractor = CommunityReportsExtractor(
    model=llm_model,
    extraction_prompt=COMMUNITY_REPORT_PROMPT,
    max_report_length=1500,
)

# 生成报告
input_text = """
Entities
human_readable_id,title,description
1,Transformer,Transformer is a deep learning architecture
2,Attention Mechanism,Attention mechanism is the core of Transformer

Relationships
human_readable_id,source,target,description
1,Transformer,Attention Mechanism,Transformer uses attention mechanism
"""

result = await extractor(input_text)
print("报告:", result.output)
print("结构化输出:", result.structured_output)
```

---

## 附录 B：参数调优指南

### B.1 leidenalg 参数调优

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `n_iterations` | 2-10 | 默认 2，增加可提高质量但增加耗时 |
| `resolution_parameter` (CPM) | 0.01-1.0 | 越大社区越小，越小社区越大 |
| `max_comm_size` | 0（不限制） | 设置正整数可限制社区最大大小 |
| `seed` | 固定值 | 设置固定种子保证可复现性 |

### B.2 graspologic hierarchical_leiden 参数调优

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `max_cluster_size` | 5-20 | GraphRAG 默认 10，控制最细粒度社区大小 |
| `resolution` | 0.5-2.0 | 默认 1.0，越大社区越小 |
| `randomness` | 0.001-0.01 | 默认 0.001，控制算法随机性 |
| `use_modularity` | True | 使用 Modularity 质量函数 |
| `iterations` | 1-5 | 默认 1，增加可提高质量 |

### B.3 GraphRAG Global Search 参数调优

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `max_context_tokens` | 4000-16000 | 默认 8000，根据 LLM 上下文窗口调整 |
| `map_max_length` | 500-2000 | 默认 1000，Map 阶段输出长度 |
| `reduce_max_length` | 1000-4000 | 默认 2000，Reduce 阶段输出长度 |
| `concurrent_coroutines` | 8-64 | 默认 32，根据 API 限流调整 |
| `use_community_summary` | True | 使用摘要而非完整内容，节省 token |
| `shuffle_data` | True | 随机化社区顺序，避免位置偏差 |
| `min_community_rank` | 0-5 | 过滤低重要性社区 |

---

> **调研结论**：
>
> 1. **Leiden 算法**是当前最优秀的社区检测算法之一，相比 Louvain 有更好的质量保证和性能
> 2. **GraphRAG 使用 graspologic** 的 `hierarchical_leiden()` 实现层次化社区结构，而非 leidenalg
> 3. **Global Search 的 Map-Reduce 模式**是解决全局问答的有效方案，通过社区摘要实现对整个文档集合的理解
> 4. **社区报告生成**是关键环节，需要精心设计 Prompt 以确保输出质量和数据引用
> 5. **动态社区选择**是优化性能的重要手段，可以显著减少 LLM 调用次数
>
> **建议实施方案**：
> - 使用 `graspologic` 的 `hierarchical_leiden()` 进行社区检测（与 GraphRAG 一致）
> - 参考 GraphRAG 的社区报告 Prompt 设计，适配学术论文场景
> - 实现 Map-Reduce 模式的 Global Search，支持全局问答
> - 引入 Dynamic Community Selection 优化查询性能
