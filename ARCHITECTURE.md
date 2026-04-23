# Paper Agent v2 — 架构设计方案

> 基于现有代码分析 + 业界论文 Agent 调研 + Agent 框架对比

---

## 一、现有问题诊断

### 1.1 致命 Bug

| 文件 | 问题 | 影响 |
|---|---|---|
| `search_agent.py` | `paper_filter_node` 从未接入图，且对 Pydantic 模型用 `.get()` | 论文筛选完全失效 |
| `search_agent.py` | `search_node` 的 `interrupt()` 硬编码 `resume=True` | 人机检查形同虚设 |
| `writing_agent.py` | `condition_edge` 用局部变量代替状态变更，节索引永不前进 | 只写第一节，循环死锁 |
| `state_model.py` | `dict[list]` 作为 Pydantic default 无效 | 状态初始化崩溃 |
| `agents_v2/base_agent.py` | 导入路径 `..models.state` 不存在 | v2 框架完全无法加载 |
| `agents_v2/router_agent.py` | `execute()` 签名不匹配基类抽象方法 | 路由失效 |

### 1.2 架构缺陷

```
现有流水线（线性，一次性，无法回退）：
search → reading → analyse → writing → report

关键缺失：
✗ 无迭代精化：一次搜索不够，结果质量取决于运气
✗ 无 Critique 循环：写完就交稿，无人审校
✗ 搜索工具（MCP server）目录为空
✗ 内存系统完整但没有接入主流水线
✗ 子 Agent 无上下文隔离，20+ 篇论文直接塞进 context
✗ 硬编码路径 D:\pycharmprojects\...
```

---

## 二、业界标杆调研

### 2.1 PaperQA2（FutureHouse）— 超人类表现的秘诀

```
四步工具调用循环：
1. Paper Search       → 关键词检索
2. Gather Evidence    → 嵌入排序 + LLM 重排 + 上下文摘要（RCS）
3. Generate Answer    → 综合回答
4. Citation Traversal → 引用图前后向扩展，从高分论文出发

核心创新 — RCS（Re-ranking + Contextual Summarization）：
  检索 top-k 片段 → 并行送入 LLM 打分(1-10) + 300字摘要
  → 按分数重排 → 只保留高分摘要
  → 平均压缩 5.6 倍，保留关键信息

引用图遍历：
  高分论文 → Semantic Scholar API → 前向引用 + 后向引用
  → 去重（DOI/标题）→ 重叠过滤（alpha=1/3）
  → 每个方向 1 度

性能：平均 4+ 次工具调用，1.26 次搜索/问题
```

### 2.2 STORM / Co-STORM（Stanford）— 多视角大纲

```
Stage 1: Pre-writing
  1. 生成 N 个不同"视角"（初学者/专家/批评者/历史学家/实践者）
  2. 每个视角 → 模拟专家对话（ConvSimulator）
  3. 收集所有对话记录 + 引用 → 生成分级大纲

Stage 2: Writing
  4. 按大纲分节写作，每节使用对应引用
  5. 润色一致性

Co-STORM 增加：人类参与的圆桌讨论 + 动态思维导图
```

### 2.3 GPT Researcher — Planner-Executor-Publisher

```
Planner Agent  → 分解 N 个子问题
Executor Agents → N 个 Agent 并行搜索（asyncio）
Publisher       → 汇总为带引用的综合报告

Deep Research 模式：
  树状探索，默认 breadth=4, depth=2, concurrency=4
  每层分裂 4 个子方向，共 2 层 → 16 条并行路径
  动态路由 gpt-4o-mini / gpt-4o 控制成本
```

### 2.4 ResearchPilot（2026.03）— 类型化阶段合约

```
SearchAgent → ExtractionAgent → SynthesisAgent → WriterAgent
  DSPy 签名约束每阶段输入/输出类型
  SQLite 持久化 + Qdrant 语义搜索历史报告
  SSE 事件流：queued → agent_started → agent_progress → done
```

### 2.5 对标总结

| 项目 | 最值得借鉴的点 |
|---|---|
| PaperQA2 | RCS 重排压缩、引用图遍历、迭代查询扩展 |
| STORM | 多视角提问 → 分级大纲 → 分节合成 |
| GPT Researcher | Planner-Executor-Publisher、树状并行探索 |
| ResearchPilot | DSPy 类型化合约、SSE 流式事件推送 |
| Consensus | 共识/矛盾检测、深度搜索（20 次搜索 → 1000+ 篇） |
| Undermind | 自适应连续搜索，LLM 动态调整查询方向 |

---

## 三、设计方案

### 3.1 整体架构：分层多 Agent + Plan-and-Execute + 迭代精化

```
┌────────────────────────────────────────────────────────────┐
│                    Coordinator Agent                        │
│                                                            │
│  Input: 用户查询（"大语言模型的幻觉问题"）                      │
│  Phase 1: Plan     → 分解子问题 + 多角度搜索词                 │
│  Phase 2: Execute  → 调度子 Agent 流水线                      │
│  Phase 3: Critique → 评估覆盖度 → 决定是否迭代                  │
│  Phase 4: Report   → 生成最终报告                             │
│                                                            │
│  最大迭代次数: 3（防止无限循环 + 成本控制）                      │
└────────────────────────────────────────────────────────────┘
       │
       ├───── [1] Query Agent ─────────────────────────────┐
       │      · 查询意图理解（澄清模糊查询）                    │
       │      · 生成 3-5 个不同角度的搜索词                     │
       │      · 识别核心概念、时间范围、领域                     │
       │      · 查询历史搜索（Memory 接入）                     │
       │                                                    │
       ├───── [2] Search Agents（并行）──────────────────────┤
       │      · Semantic Scholar API（200M+ 论文）            │
       │      · arXiv API（预印本、全文文本）                    │
       │      · 去重（DOI/标题归一化）                          │
       │      · RCS 相关性排序（PaperQA2 启发）                │
       │                                                    │
       ├───── [3] Reading Agents（并行，子 Agent 隔离）─────────┤
       │      · PDF 下载 + 解析（按节分块：摘要/方法/结果/结论）    │
       │      · 提取结构化数据：贡献、方法、数据集、指标、局限性     │
       │      · 每篇论文独立子 Agent（不污染主上下文）             │
       │      · 结果聚合为结构化摘要（每篇 ~300 字）              │
       │                                                    │
       ├───── [4] Analysis Agent ──────────────────────────┤
       │      · KMeans 聚类 → 主题发现（已有，保留）              │
       │      · 跨论文对比（方法/结果/数据集）                    │
       │      · 共识 vs 矛盾检测                               │
       │      · 研究空白识别                                  │
       │      · 时间线分析（领域演进）                           │
       │      · 引用图构建 → 关键论文发现                        │
       │                                                    │
       ├───── [5] Critique Agent（新增，STORM 启发）─────────────┤
       │      · 从 3 个视角提问：初学者/专家/批评者              │
       │      · 检查：覆盖度？矛盾解释了吗？最新论文查了吗？        │
       │      · 若发现空白 → 生成补充搜索词                      │
       │      → 回到 [2] 补充搜索（最多 3 次迭代）               │
       │      → 若通过 → 进入写作                              │
       │                                                    │
       └───── [6] Writing Agent ────────────────────────────┘
              · 多视角大纲生成（STORM 启发）
              · 分节写作 + 引用格式化 [R1], [R2]...
              · 自我审校循环：APPROVED / RETRIEVAL（已有，修复）
              · 最终报告 Markdown
```

### 3.2 LangGraph 状态机

```python
class ResearchState(TypedDict):
    # ─── 输入 ───
    query: str                        # 用户原始查询

    # ─── 规划阶段 ───
    sub_questions: list[str]         # 分解的子问题
    search_queries: list[str]        # 多角度搜索词
    search_plan: dict                # 搜索计划（来源、数量、时间范围）

    # ─── 搜索结果 ───
    papers: list[Paper]              # 去重排序后的论文列表

    # ─── 阅读结果 ───
    paper_analyses: list[PaperAnalysis]  # 结构化提取结果

    # ─── 分析结果 ───
    themes: list[Theme]              # 聚类主题
    contradictions: list[str]        # 矛盾发现
    research_gaps: list[str]         # 研究空白
    timeline: list[Event]            # 领域时间线
    citation_graph: CitationGraph    # 引用关系

    # ─── 迭代控制 ───
    iteration: int                   # 当前迭代次数
    max_iterations: int              # 最大迭代次数（默认 3）
    critique_passed: bool            # Critique 是否通过
    additional_queries: list[str]    # Critique 产生的补充查询

    # ─── 写作 ───
    outline: Outline                 # 分级大纲
    sections: list[Section]          # 分节内容
    report: str                      # 最终报告 Markdown

    # ─── 系统 ───
    status: ResearchStatus           # 当前状态
    events: list[AgentEvent]         # SSE 事件流
    error: str | None                # 错误信息
```

### 3.3 图结构定义

```
START
  │
  ▼
query_node                          # 查询理解 + 搜索词生成
  │
  ├─ [parallel] ──────────────────────────────────┐
  │                                                │
  ▼                                                ▼
search_semantic_scholar                    search_arxiv
  │                                                │
  └─ [merge] ──────────────────────────────────────┘
             │
             ▼
      dedup_and_rank_node              # 去重 + RCS 相关性排序
             │
             ▼
      reading_pipeline                   # 并行阅读
        │
        ├─ reading_node_1 (Paper 1)      # 每个论文独立子 Agent
        ├─ reading_node_2 (Paper 2)      # 上下文隔离
        ├─ reading_node_3 (Paper 3)
        └─ ...
             │
             ▼
      analysis_node                       # 聚类 + 对比 + 空白识别
             │
             ▼
      critique_node ←─────────────────────────────────────┐
             │                                             │
             ├─ gaps_found AND iteration < max_iter         │
             │   │                                         │
             │   ▼                                         │
             │  additional_search_node  ── 生成补充查询 ────┘
             │
             └─ critique_passed
                    │
                    ▼
              writing_outline_node                   # 大纲生成
                    │
                    ▼
              writing_section_node                  # 分节写作（循环）
                    │
                    ▼
              review_node                           # 自我审校
                    │
                    ├─ RETRIEVAL → retrieval_node → 回到 writing
                    │
                    └─ APPROVED
                           │
                           ▼
                      report_node
                           │
                           ▼
                         END
```

### 3.4 条件边实现

```python
def should_iterate(state: ResearchState) -> str:
    """Critique 后的分支决策"""
    if not state["critique_passed"] and state["iteration"] < state["max_iterations"]:
        return "additional_search"
    return "writing"


def review_decision(state: ResearchState) -> str:
    """写作审校后的分支决策"""
    last_section = state["sections"][-1]
    if last_section.status == "RETRIEVAL":
        return "retrieval"
    if last_section.status == "APPROVED":
        next_idx = last_section.index + 1
        if next_idx < len(state["outline"].sections):
            return "next_section"
        return "report"
    return "review"  # 继续修改当前节
```

### 3.5 搜索工具（MCP Server）—— 填补空目录

```python
# paper_for_search/paper_search_mcp/server.py
from fastmcp import FastMCP
import arxiv
import requests

mcp = FastMCP("paper-search")

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

@mcp.tool()
async def search_semantic_scholar(
    query: str,
    limit: int = 20,
    year_start: int = 2020,
    year_end: int = 2026,
    fields: str = "title,authors,year,abstract,citationCount,tldr,openAccessPdf"
) -> list[dict]:
    """Search Semantic Scholar for academic papers."""
    resp = requests.get(SEMANTIC_SCHOLAR_URL, params={
        "query": query,
        "limit": limit,
        "year": f"{year_start}-{year_end}",
        "fields": fields,
    })
    resp.raise_for_status()
    return resp.json().get("data", [])


@mcp.tool()
async def search_arxiv(query: str, max_results: int = 20) -> list[dict]:
    """Search arXiv preprint server."""
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    results = []
    for paper in search.results():
        results.append({
            "title": paper.title,
            "authors": [a.name for a in paper.authors],
            "year": paper.published.year,
            "abstract": paper.summary,
            "url": paper.entry_id,
            "pdf_url": paper.pdf_url,
        })
    return results


@mcp.tool()
async def download_paper_pdf(pdf_url: str, save_path: str) -> str:
    """Download a paper PDF from URL."""
    import urllib.request
    urllib.request.urlretrieve(pdf_url, save_path)
    return f"Saved to {save_path}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### 3.6 RCS 相关性排序（PaperQA2 启发）

```python
async def rcs_rank(query: str, papers: list[Paper], k: int = 50) -> list[Paper]:
    """
    Re-ranking + Contextual Summarization
    1. Embed query + abstract → 初排
    2. LLM 对每篇打分(1-10) + 300字摘要
    3. 按分数重排
    """
    # Step 1: 向量初排（用已有 embedding model）
    query_emb = embed_model.encode(query)
    paper_embs = embed_model.encode([p.abstract for p in papers])
    scores = cosine_similarity([query_emb], paper_embs)[0]
    top_candidates = sorted(zip(papers, scores), key=lambda x: -x[1])[:k]

    # Step 2: LLM 重排 + 摘要
    prompts = [
        f"""Query: {query}
Paper: {title}\nAbstract: {abstract}
Score 1-10 for relevance. Output JSON: {{"score": int, "summary": "300 words"}}"""
        for title, abstract in [(p.title, p.abstract) for p, _ in top_candidates]
    ]
    # 并行调用
    responses = await asyncio.gather(*[call_llm(p) for p in prompts])

    # Step 3: 重排
    results = []
    for (paper, _), resp in zip(top_candidates, responses):
        data = json.loads(resp)
        paper.relevance_score = data["score"] / 10
        paper.summary = data["summary"]
        results.append(paper)

    return sorted(results, key=lambda p: -p.relevance_score)
```

### 3.7 Critique Agent（STORM 多视角启发）

```python
PERSPECTIVES = [
    {
        "role": "初学者",
        "prompt": "作为刚接触这个领域的学生，你会问哪些基础问题？"
                  "哪些概念、术语、背景信息可能缺失？"
    },
    {
        "role": "专家",
        "prompt": "作为该领域的资深研究者，评估现有覆盖的深度和广度。"
                  "哪些重要论文/方法/发现被遗漏了？"
                  "哪些论点缺乏足够的证据支持？"
    },
    {
        "role": "批评者",
        "prompt": "作为该领域的批评者，找出论证中的薄弱环节。"
                  "哪些矛盾没有被充分讨论？"
                  "哪些假设可能有问题？"
    },
]

async def critique(state: ResearchState) -> dict:
    """多视角审查，返回是否通过 + 补充搜索词"""
    critiques = []
    for perspective in PERSPECTIVES:
        prompt = f"""
研究主题: {state['query']}
当前发现:
  - 论文数量: {len(state['papers'])}
  - 主题聚类: {state['themes']}
  - 研究空白: {state['research_gaps']}
  - 矛盾发现: {state['contradictions']}

{perspective['prompt']}

请输出 JSON: {{"score": 1-10, "missing_topics": [...], "suggested_queries": [...]}}"""
        resp = json.loads(await call_llm(prompt))
        critiques.append(resp)

    avg_score = sum(c["score"] for c in critiques) / len(critiques)
    all_missing = set()
    all_queries = set()
    for c in critiques:
        all_missing.update(c.get("missing_topics", []))
        all_queries.update(c.get("suggested_queries", []))

    return {
        "critique_passed": avg_score >= 7,
        "additional_queries": list(all_queries),
        "missing_topics": list(all_missing),
    }
```

### 3.8 子 Agent 上下文隔离方案

```python
# 解决 20+ 篇论文塞爆 context 的问题
# 方案：每篇论文独立子 Agent，只返回结构化摘要

async def read_paper_isolated(paper: Paper) -> PaperAnalysis:
    """独立上下文的子 Agent — 处理单篇论文"""
    # 下载 PDF → 解析为节 → 逐节提取 → 汇总
    pdf_path = await download_pdf(paper.pdf_url)
    sections = parse_pdf_sections(pdf_path)  # {abstract, method, results, ...}

    # 逐节提取（限制每节 token 数）
    extraction = await extract_structured_data({
        "title": paper.title,
        "abstract": sections.get("abstract", ""),
        "method": sections.get("method", "")[:2000],   # 截断防溢出
        "results": sections.get("results", "")[:2000],
    })

    # 生成 ~300 字摘要（压缩 5.6 倍）
    summary = await generate_summary(paper.title, extraction)

    return PaperAnalysis(
        paper_id=paper.id,
        contributions=extraction.contributions,
        methods=extraction.methods,
        datasets=extraction.datasets,
        results=extraction.results,
        limitations=extraction.limitations,
        summary=summary,  # 仅 300 字，不污染主上下文
    )
```

### 3.9 SSE 事件流设计（前后端契约）

```
事件类型                    数据字段                    用途
────────────────────────────────────────────────────────────
status                    {status: "planning"}         更新进度条
paper_found               Paper 对象                    添加到论文列表
paper_read                {paper_id, analysis}         阅读完成
analysis_update           {themes, gaps}               分析结果更新
writing_update            {report, section}            报告内容
critique_result           {passed, missing}            Critique 结果
error                     {message}                    错误提示
done                      {}                           研究完成
```

前端通过 `EventSource` 连接 `/api/research/stream/{task_id}`：
```typescript
const es = new EventSource(`/api/research/stream/${taskId}`);
es.addEventListener("agent_event", (e) => {
  const event = JSON.parse(e.data);
  switch (event.type) {
    case "paper_found": addPaper(event.data); break;
    case "writing_update": setReport(event.data.report); break;
    case "done": setStatus("done"); es.close(); break;
  }
});
```

### 3.10 Memory 系统集成

```python
# 在 query_node 中查询历史搜索
async def query_node(state: ResearchState):
    memory = get_memory_manager()
    # 查找相似的历史研究
    similar = memory.search_semantic(state["query"], limit=3)
    if similar:
        # 避免重复搜索相同主题
        state["search_queries"] = deduplicate_with_history(
            generate_search_queries(state["query"]),
            similar
        )
    return state

# 在 analysis_node 后存储发现
async def analysis_node(state: ResearchState):
    themes = await cluster_papers(state["paper_analyses"])
    memory = get_memory_manager()
    memory.store_themes(state["query"], themes)  # 持久化到磁盘
    memory.store_findings(state["query"], {
        "themes": themes,
        "gaps": state["research_gaps"],
    })
    state["themes"] = themes
    return state
```

---

## 四、技术选型

| 决策点 | 选择 | 理由 |
|---|---|---|
| Agent 框架 | LangGraph（保留现有） | 有状态图 + 检查点 + 条件边，最适合结构化研究流水线 |
| 推理模式 | Plan-and-Execute | 比纯 ReAct 便宜 30-50%，适合可预测的研究流水线 |
| Critique 循环 | STORM 多视角 | Stanford 验证的多视角提问法，覆盖度高 |
| 相关性排序 | RCS（PaperQA2） | 嵌入初排 + LLM 重排 + 上下文摘要，超人类表现 |
| 论文搜索 | Semantic Scholar + arXiv | 覆盖最广、API 最稳定、免费 |
| PDF 解析 | PyMuPDF（已有）→ 可选 GROBID | 学术结构化提取更好 |
| 子 Agent 隔离 | 独立子 Agent + 结构化摘要 | 不污染主上下文，支持并行 |
| 流式通信 | SSE | 轻量、浏览器原生支持、单向推送够用 |
| 前端 | React 18 + Vite + Tailwind + Zustand | 轻量、开发体验好、已有生态 |
| 知识图谱 | Cytoscape.js | 轻量、交互好、适合概念节点可视化 |

---

## 五、实施优先级

### Phase 1：修复（1-2 天）
- [ ] 修复 `state_model.py` 的 Pydantic default bug
- [ ] 修复 `search_agent.py` 的 paper_filter_node 接入 + Pydantic get 问题
- [ ] 修复 `writing_agent.py` 的 condition_edge 索引推进 bug
- [ ] 修复 `agents_v2/base_agent.py` 的导入路径
- [ ] 修复 `agents_v2/router_agent.py` 的 execute 签名
- [ ] 消除重复的 SearchAgent 定义

### Phase 2：搜索工具（1 天）
- [ ] 实现 `paper_for_search/paper_search_mcp/server.py`（Semantic Scholar + arXiv）
- [ ] 测试 MCP 工具在 LangGraph 中的调用

### Phase 3：迭代精化（2-3 天）
- [ ] 在 LangGraph 中添加 Critique Agent 节点
- [ ] 实现 `should_iterate` 条件边
- [ ] 添加 additional_search_node
- [ ] 设置 max_iterations = 3

### Phase 4：RCS + 子 Agent 隔离（2-3 天）
- [ ] 实现 rcs_rank() 函数
- [ ] 改造 reading_node 为并行独立子 Agent
- [ ] 实现结构化摘要压缩

### Phase 5：前端对接（1-2 天）
- [ ] 后端 SSE 流式事件推送（已在 api.py 中实现框架）
- [ ] 前端 ResearchPage 实时进度更新
- [ ] 论文库/报告/知识图谱页面

### Phase 6：Memory + 知识图谱（2-3 天）
- [ ] 在 query_node 中接入历史搜索查询
- [ ] 在 analysis_node 后持久化主题发现
- [ ] 知识图谱页面数据接入

---

## 六、与现有代码的兼容关系

| 现有模块 | 保留/修改/替换 | 说明 |
|---|---|---|
| `src/core/state_model.py` | **修改** | 修复 bug + 扩展新字段 |
| `src/agents/search/` | **修改** | 修复 bug + 接入真实 MCP |
| `src/agents/reading/` | **修改** | 改为并行子 Agent + 结构化摘要 |
| `src/agents/analysis/` | **保留** | KMeans 聚类 + 深度分析逻辑可用 |
| `src/agents/writing/` | **修改** | 修复 condition_edge + 保留 APPROVED/RETRIEVAL |
| `src/agents/report/` | **保留** | 报告组装逻辑正确 |
| `src/agents/orchestrator.py` | **废弃** | 被新的 Coordinator Agent 替代 |
| `src/agents_v2/` | **保留** | BaseAgent ReAct 引擎可用于 Critique Agent |
| `src/memory/` | **保留+接入** | 完整但需要接入主流水线 |
| `src/knowledge/extraction/` | **保留** | 知识抽取逻辑正确 |
| `src/knowledge/concept_graph/` | **保留** | 图数据结构正确 |
| `src/knowledge/retrieval/` | **保留** | Graph-First RAG 逻辑正确 |
| `src/workflows/paper_workflow.py` | **修改** | 扩展图结构，增加 Critique 节点和条件边 |
| `src/services/milvus.py` | **保留** | 向量存储可用 |
| `models/routers/deberta_router.py` | **保留** | 复杂度分类可用于动态模型选择 |

---

## 七、关键创新点总结

1. **STORM 多视角 Critique 循环**：从初学者/专家/批评者三个视角审校，自动发现覆盖空白并触发补充搜索
2. **PaperQA2 RCS 排序**：嵌入初排 + LLM 重排 + 上下文摘要，大幅提高论文相关性
3. **子 Agent 上下文隔离**：每篇论文独立处理，只返回 ~300 字结构化摘要，避免 context 溢出
4. **Plan-and-Execute + LangGraph**：比纯 ReAct 更便宜、更可审计、更适合结构化研究流水线
5. **SSE 实时事件流**：前端可实时看到"正在搜索"、"发现论文"、"生成报告"等进度
