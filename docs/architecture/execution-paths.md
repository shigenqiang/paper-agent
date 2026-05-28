# Paper Agent 执行路径详解

> 本文档详细说明从用户请求到系统响应的完整执行路径

---

## 一、整体执行路径概览

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              用户请求入口                                         │
│  前端 (React 18) ──→ Axios ──→ HTTP + SSE ──→ API Gateway (aiohttp:8000)        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           API Gateway 层                                         │
│  api_key_auth_middleware → request_logging_middleware → error_handle_middleware │
│                                                                                  │
│  路由分发:                                                                        │
│    /api/papers   → paper_api.py                                                 │
│    /api/reports → reports_api.py                                                │
│    /api/route    → intent_router.py                                             │
│    /api/workflow → workflow_api.py → LangGraph Workflow                          │
│    /api/kg       → knowledge_graph_api.py                                       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
          ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
          │  IntentRouter   │  │ MasterSupervisor│  │ LangGraph       │
          │  意图路由        │  │  流水线编排     │  │  状态机工作流    │
          └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
                   │                   │                   │
                   └───────────────────┼───────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Agent 执行层                                           │
│                                                                                  │
│  新版: agents/ (ReAct Loop)                                                      │
│    ├── base/base_agent.py      — BaseAgent 标准接口                             │
│    └── loops/react_loop.py     — ReAct 执行器 (546行)                           │
│                                                                                  │
│  兼容: unified/ (向后兼容)                                                        │
│    ├── MasterSupervisor        — 6阶段流水线编排                                 │
│    └── PhaseSupervisor         — 阶段监督器                                      │
│                                                                                  │
│  角色: agents/roles/                                                              │
│    ├── planner/     — 规划Agent                                                  │
│    ├── polisher/   — 润色Agent                                                   │
│    ├── reviewer/   — 评审Agent                                                   │
│    ├── searcher/   — 搜索Agent                                                   │
│    ├── specialist/ — 专家Agent                                                   │
│    └── writer/      — 写作Agent                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           支撑服务层                                             │
│                                                                                  │
│  Memory System ──→ Storage Layer ──→ Evaluation ──→ Monitoring                   │
│  (memory/)        (storage/)       (evaluation/)   (monitoring/)                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、启动路径

### 2.1 服务启动

```
python -m src.main
      │
      ▼
src/main.py:main()
      │
      ▼
src.agents_v2.server.api_server:main()
      │
      ▼
create_app()
      │
      ├── 1. 注册中间件
      │     request_logging_middleware
      │     api_key_auth_middleware
      │     error_handle_middleware
      │
      ├── 2. 注册路由
      │     /health
      │     /api/papers/*     → paper_api.py
      │     /api/reports/*    → reports_api.py
      │     /api/workflow/*   → workflow_api.py
      │     /api/kg/*         → knowledge_graph_api.py
      │
      ▼
web.run_app(app, port=8000)
```

### 2.2 新版 Agent 初始化

```
# agents/base/base_agent.py

BaseAgent.__init__(name, llm_config, description, system_prompt)
      │
      ├── _init_llm()
      │     ├── ChatOpenAI / ChatAnthropic
      │     └── 模型配置 (provider, model_name, temperature)
      │
      ├── _setup_logging()
      │     └── get_logging_logger(f"Agent.{name}")
      │
      └── self.tools: List[Tool] = []
```

### 2.3 ReAct Loop 初始化

```
# agents/loops/react_loop.py

ReActExecutor.__init__(agent, max_iterations, max_tool_calls)
      │
      ├── self.agent = agent
      ├── self.max_iterations = 10
      ├── self.max_tool_calls = 5
      └── self._tool_call_count = 0
```

### 2.4 LangGraph Workflow 初始化

```
WorkflowRunner.__init__(llm_config)
      │
      ▼
_build_graph()
      │
      ├── StateGraph(PaperAgentState).compile()
      │
      ├── 添加节点 (22个):
      │     router, crawler, selector, outline, writer,
      │     reviewer, evaluator, memory_recall, memory_remember,
      │     multimodal, knowledge_graph, qa_search, qa_synthesize,
      │     qa_answer, report_crawl, report_analyze, report_gen,
      │     revise, refine, polish
      │
      ├── 添加边
      │
      └── 添加条件边
            router → (search/writing/report/qa/revise)_workflow
            evaluator → (end/continue)
```

---

## 三、请求处理路径

### 3.1 论文搜索请求流程

```
用户输入: "帮我找几篇关于transformer注意力机制的论文"
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 1: HTTP 请求到 /api/papers                                             │
│         Headers: X-API-Key: <key>                                            │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 2: api_key_auth_middleware 认证                                         │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 3: paper_api.py: paper_chat()                                          │
│         - 解析请求体                                                          │
│         - 提取 user_id, session_id, query                                   │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 4: IntentRouter.route() — 意图路由 (11种意图)                            │
│         ┌──────────────────────────────────────────────────────────────┐   │
│         │ 4.1 关键词快速匹配 (INTENT_KEYWORDS)                           │   │
│         │      "找" → LITERATURE_SEARCH                                 │   │
│         │                                                              │   │
│         │ 4.2 LLM 辅助识别 (复杂/多意图时)                               │   │
│         │      ChatOpenAI.ainvoke([...])                               │   │
│         │                                                              │   │
│         │ 4.3 合并排序 + 置信度校准                                      │   │
│         │      keyword_match + llm_confidence → calibrated             │   │
│         │                                                              │   │
│         │ 4.4 意图冲突检测                                              │   │
│         │                                                              │   │
│         │ 4.5 查询 intent_agent_map → 路由结果                           │   │
│         └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 5: 路由到 PaperSearchAgent (search 模块)                                │
│         PaperSearchAgent.search(query, sources, max_results)                │
│         ┌──────────────────────────────────────────────────────────────┐   │
│         │ 5.1 获取搜索器实例                                             │   │
│         │      ArxivSearcher, PubMedSearcher, SemanticScholarSearcher │   │
│         │      OpenAlexSearcher, CrossRefSearcher                      │   │
│         │                                                              │   │
│         │ 5.2 并行执行搜索 (asyncio.gather)                             │   │
│         │      for source in sources:                                   │   │
│         │          tasks.append(searchers[source].search(query))       │   │
│         │                                                              │   │
│         │ 5.3 收集结果                                                   │   │
│         │      results = await asyncio.gather(*tasks)                  │   │
│         │                                                              │   │
│         │ 5.4 结果合并去重 (SearchResultMerger.merge)                   │   │
│         │      - 按相关性排序                                            │   │
│         │      - DOI 去重                                                │   │
│         │      - 合并作者列表                                            │   │
│         └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 6: 返回结果                                                            │
│         {                                                                  │
│           "papers": [...],    # 论文列表                                     │
│           "total": 50,        # 总数                                        │
│           "sources": ["arxiv", "pubmed", "semantic_scholar"]               │
│         }                                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 完整论文写作流程 (FULL_PAPER)

```
用户输入: "我想写一篇关于大语言模型安全的论文"
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ IntentRouter.route()                                                        │
│   → primary_intent: FULL_PAPER                                              │
│   → mode: pipeline                                                           │
│   → suggested_agents: [TopicAgent, LiteratureAgent, OutlineAgent,           │
│                        DraftWriterAgent, ReviewerAgent, PolisherAgent]     │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ MasterSupervisor.run() — 6阶段流水线编排                                      │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Phase 1: DIAGNOSTIC — 诊断分析                                         │  │
│  │                                                                        │  │
│  │   TopicRefiner + LiteratureMapper + MethodologyAdvisor                │  │
│  │        │                      │                      │                  │  │
│  │        └──────────────────────┼──────────────────────┘                  │  │
│  │                               ▼                                           │  │
│  │                    ResearchGap + ArgumentBuilder                        │  │
│  │                               │                                           │  │
│  │                               ▼                                           │  │
│  │                         PlagiarismChecker                               │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Phase 2: TOPIC — 选题阶段                                              │  │
│  │                                                                        │  │
│  │   TopicAgent.execute(user_input)                                      │  │
│  │        │                                                               │  │
│  │        ▼                                                               │  │
│  │   {topics: [{title, description, novelty}, ...]}                       │  │
│  │        │                                                               │  │
│  │        ▼                                                               │  │
│  │   HITLManager.interrupt("topic_selection") — 用户选择课题               │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Phase 3: LITERATURE — 文献调研                                        │  │
│  │                                                                        │  │
│  │   LiteratureAgent.search_and_review(topic, max_papers=20)             │  │
│  │        │                                                               │  │
│  │        ├── PaperSearchAgent.search(topic) → 多源并行搜索               │  │
│  │        │        │                                                      │  │
│  │        │        ├── ArxivSearcher.search()                            │  │
│  │        │        ├── PubMedSearcher.search()                         │  │
│  │        │        ├── SemanticScholarSearcher.search()                  │  │
│  │        │        └── OpenAlexSearcher.search()                        │  │
│  │        │                                                              │  │
│  │        ├── Selector.llm_filter() → LLM评分筛选Top 10                  │  │
│  │        │                                                              │  │
│  │        └── LiteratureReviewResult(papers, review, citation_graph)     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Phase 4: METHODOLOGY — 方法论                                         │  │
│  │                                                                        │  │
│  │   MethodologyAdvisor.analyze(topic, papers)                            │  │
│  │        │                                                               │  │
│  │        ▼                                                               │  │
│  │   {research_gaps, methodology_suggestions, experimental_approach}    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Phase 5: WRITING — 写作阶段                                            │  │
│  │                                                                        │  │
│  │   5.1 OutlineAgent.generate_outline(topic, papers)                    │  │
│  │   │        │                                                           │  │
│  │   │        ▼                                                           │  │
│  │   │   {title, chapters: [{title, sections: [...]}, ...]}             │  │
│  │   │        │                                                           │  │
│  │   │        ▼                                                           │  │
│  │   │   HITLManager.interrupt("outline_review") — 用户确认大纲           │  │
│  │   │                                                           │        │  │
│  │   │   ┌─────────────────────────────────────────────────────────────┐   │  │
│  │   │   │ DraftWriterAgent.write_draft(outline, papers)             │   │  │
│  │   │   │        │                                                   │   │  │
│  │   │   │        ├── 遍历大纲章节                                      │   │  │
│  │   │   │        ├── LLM 生成章节内容                                  │   │  │
│  │   │   │        ├── 引用相关论文 (# Citation)                         │   │  │
│  │   │   │        └── 合并为完整初稿                                   │   │  │
│  │   │   └─────────────────────────────────────────────────────────────┘   │  │
│  │   │        │                                                           │  │
│  │   │        ▼                                                           │  │
│  │   │   ReviewerAgent.review(draft) → {feedback, quality_score}          │  │
│  │   │        │                                                           │  │
│  │   │        ▼                                                           │  │
│  │   │   Evaluator.evaluate(draft) → avg_score                          │  │
│  │   │        │                                                           │  │
│  │   │        ├── score >= 7.0 → 通过                                    │  │
│  │   │        └── score < 7.0 → 返回 writer 返修 (最多 max_iterations)   │  │
│  │   │                                                           │        │  │
│  │   └───────────────────────────────────────────────────────────────────┘   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Phase 6: POLISH — 润色阶段                                            │  │
│  │                                                                        │  │
│  │   LanguagePolisher.polish(draft)                                      │  │
│  │        │                                                               │  │
│  │        ├── 语法检查                                                    │  │
│  │        ├── 表达优化                                                    │  │
│  │        ├── 格式规范化                                                  │  │
│  │        └── 最终论文输出                                                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 新版 ReAct Loop 执行流程

```
# agents/loops/react_loop.py

ReActExecutor.execute(task, context, callbacks)
      │
      ├── For iteration in range(max_iterations):
      │     │
      │     ├── 1. Thought: _think() → Thought(reasoning, confidence, next_action)
      │     │        │
      │     │        └── _build_thinking_prompt() + _call_llm()
      │     │
      │     ├── 2. Action:
      │     │     │
      │     │     ├── TOOL_CALL → _execute_tool(tool_name, parameters)
      │     │     │        │
      │     │     │        └── _find_tool() → tool.ainvoke()
      │     │     │
      │     │     ├── FINAL_ANSWER → ReActResult(final_answer, trace)
      │     │     │
      │     │     └── WAIT_INPUT → 等待用户输入
      │     │
      │     └── 3. Observation: _process_observation(result)
      │              │
      │              └── current_state["observations"].append()
      │
      └── Return ReActResult
```

---

## 四、LangGraph Workflow 执行路径

### 4.1 五条工作流路径

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LangGraph 工作流                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐                                                             │
│  │   router    │ ← 入口节点，意图分类                                         │
│  └──────┬──────┘                                                             │
│         │                                                                    │
│         ├──────────────────┬──────────────────┬──────────────────┐             │
│         ▼                  ▼                  ▼                  ▼             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  │   search    │  │   writing   │  │   report    │  │     qa      │  │   revise    │
│  │  workflow   │  │  workflow   │  │  workflow   │  │  workflow   │  │  workflow   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Search 工作流

```
router (intent=search)
  │
  ▼
crawler ──→ selector ──→ END

节点说明:
  - crawler: 多源论文检索 (arXiv/PubMed/Semantic Scholar/OpenAlex)
  - selector: LLM 评分筛选 Top 20
```

#### Writing 工作流

```
router (intent=writing)
  │
  ▼
memory_recall ──→ crawler ──→ selector ──→ [multimodal] ──→ [kg]
                                                          │
                                                          ▼
                                                     outline ──→ writer
                                                          │
                                                          ▼
                                                     reviewer
                                                          │
                                                          ▼
                                                     evaluator
                                                          │
                                    ┌─────────────────────┴─────────────────────┐
                                    │                                           │
                              [分数 ≥ 7.0]                               [分数 < 7.0]
                                    │                                           │
                                    ▼                                           ▼
                                 END                                       返回 writer
                                                                          (迭代 ≤ max)
```

#### Report 工作流

```
router (intent=report)
  │
  ▼
report_crawl ──→ report_analyze ──→ report_gen ──→ END
```

#### QA 工作流

```
router (intent=qa)
  │
  ▼
qa_search ──→ qa_synthesize ──→ qa_answer ──→ END
```

#### Revise 工作流

```
router (intent=revise)
  │
  ▼
revise ──→ refine ──→ polish ──→ END
```

### 4.2 状态定义 (PaperAgentState)

```python
class PaperAgentState(TypedDict):
    # 用户信息
    user_id: str
    session_id: str

    # 查询
    user_query: str

    # 论文数据
    papers: List[dict]              # 原始论文列表
    selected_papers: List[dict]      # 筛选后的论文

    # 写作数据
    outline: dict                    # 大纲
    draft: str                      # 初稿

    # 反馈
    feedback: str                    # 评审反馈
    iteration: int                 # 当前迭代
    max_iterations: int            # 最大迭代

    # 阶段
    current_phase: str               # 当前阶段
    phases_completed: List[str]    # 已完成阶段

    # 元数据
    timestamp: str
    errors: List[str]
    trace_id: str
```

### 4.3 Writer 节点执行流

```python
async def writer_node(state: PaperAgentState) -> PaperAgentState:
    """
    逐节生成论文内容
    """
    papers = state["selected_papers"]
    outline = state["outline"]

    sections = []
    for chapter in outline["chapters"]:
        # 1. 构建章节提示词
        prompt = f"""根据以下论文写第{chapter['title']}节:
        论文: {papers}
        章节: {chapter}"""

        # 2. 调用 LLM 生成
        section_content = await llm.ainvoke([
            SystemMessage("你是一个学术论文写作专家..."),
            HumanMessage(prompt)
        ])

        # 3. 添加引用标注
        section_with_citations = add_citations(section_content, papers)
        sections.append(section_with_citations)

    # 4. 合并为完整初稿
    draft = "\n\n".join(sections)
    return {"draft": draft}
```

### 4.4 Evaluator 节点执行流

```python
async def evaluator_node(state: PaperAgentState) -> PaperAgentState:
    """
    多维度评分 + 决策
    """
    draft = state["draft"]
    iteration = state["iteration"]
    max_iterations = state["max_iterations"]

    # 1. LLM 评分
    scores = await llm.ainvoke([
        SystemMessage("你是一个论文质量评审专家..."),
        HumanMessage(f"评审以下论文并给出7个维度评分:\n{draft}")
    ])

    # 评分维度
    # - structure: 0-10 (结构完整性)
    # - logic: 0-10 (逻辑连贯性)
    # - originality: 0-10 (创新性)
    # - language: 0-10 (语言质量)
    # - citation: 0-10 (引用准确性)
    # - completeness: 0-10 (内容完整性)
    # - format: 0-10 (格式规范性)

    avg_score = sum(scores.values()) / len(scores)

    # 2. 决策
    if avg_score >= 7.0 or iteration >= max_iterations:
        # 通过
        return {
            "evaluation_passed": True,
            "quality_score": avg_score,
            "scores": scores
        }
    else:
        # 返修
        return {
            "evaluation_passed": False,
            "quality_score": avg_score,
            "scores": scores,
            "iteration": iteration + 1
        }
```

---

## 五、意图路由路径

### 5.1 路由决策树

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ IntentRouter.route(user_input)                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 关键词匹配 (INTENT_KEYWORDS)                                          │    │
│  │                                                                       │    │
│  │   "找/搜索/论文"  → LITERATURE_SEARCH                                 │    │
│  │   "综述/比较"     → LITERATURE_REVIEW / LITERATURE_SUMMARY           │    │
│  │   "追踪/最新"     → LITERATURE_TRACKING                               │    │
│  │   "选题/课题"     → TOPIC_SELECT                                     │    │
│  │   "Thesis/论点"  → THESIS_FORMULATE                                 │    │
│  │   "大纲/章节"     → OUTLINE_GENERATE                                 │    │
│  │   "写作/撰写"     → DRAFT_WRITE                                      │    │
│  │   "修改/改稿"     → PAPER_REVISION                                  │    │
│  │   "报告/资讯"     → REPORT_REFINE                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│            │                                                                 │
│            ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ LLM 辅助识别 (复杂/多意图)                                            │    │
│  │                                                                       │    │
│  │   ChatOpenAI.ainvoke([                                              │    │
│  │     SystemMessage("你是一个意图识别专家..."),                         │    │
│  │     HumanMessage("分析用户输入的所有意图: {user_input}")             │    │
│  │   ])                                                                 │    │
│  │                                                                       │    │
│  │   → {intents: [{intent, confidence}, ...]}                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│            │                                                                 │
│            ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 置信度校准                                                           │    │
│  │                                                                       │    │
│  │   keyword_match=True  → +0.15                                       │    │
│  │   多意图 (>1)         → ×0.9                                         │    │
│  │   cap at 1.0          → min(confidence, 1.0)                         │    │
│  │                                                                       │    │
│  │   HIGH: ≥ 0.8                                                        │    │
│  │   MEDIUM: 0.5-0.8                                                    │    │
│  │   LOW: < 0.5                                                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│            │                                                                 │
│            ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 路由到 Agent                                                          │    │
│  │                                                                       │    │
│  │   LITERATURE_SEARCH → PaperSearchAgent                              │    │
│  │   LITERATURE_REVIEW → LiteratureAgent                               │    │
│  │   TOPIC_SELECT      → TopicAgent                                    │    │
│  │   OUTLINE_GENERATE  → OutlineAgent                                  │    │
│  │   DRAFT_WRITE       → DraftWriterAgent                              │    │
│  │   FULL_PAPER       → MasterSupervisor (5 Agent 流水线)            │    │
│  │   DIAGNOSTIC       → TopicRefiner + LiteratureMapper               │    │
│  │                              + MethodologyAdvisor                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 意图 → Agent 映射表

| IntentType | 值 | 映射Agent | 模块 | 说明 |
|-----------|---|-----------|------|------|
| LITERATURE_SEARCH | 搜索论文 | PaperSearchAgent | search | 多源聚合搜索 |
| LITERATURE_REVIEW | 文献综述 | LiteratureAgent | paper_agents | 检索+筛选+综述 |
| LITERATURE_TRACKING | 文献追踪 | LiteratureAgent | paper_agents | 增量监控 |
| LITERATURE_SUMMARY | 文献对比 | LiteratureAgent | paper_agents | 多论文对比 |
| TOPIC_SELECT | 选题 | TopicAgent | paper_agents | 候选课题生成 |
| THESIS_FORMULATE | Thesis凝练 | ThesisAgent | paper_agents | 论点提取 |
| OUTLINE_GENERATE | 大纲生成 | OutlineAgent | paper_agents | 层级化大纲 |
| DRAFT_WRITE | 初稿撰写 | DraftWriterAgent | paper_agents | 逐节生成 |
| PAPER_REVISION | 智能改稿 | SmartReviserAgent | writing | 迭代修订 |
| REPORT_REFINE | 报告精炼 | ReportRefinerAgent | writing | 多轮精炼 |
| FULL_PAPER | 完整论文 | MasterSupervisor | unified | 6阶段流水线 |
| DIAGNOSTIC | 诊断 | 3 Agent协作 | problem_oriented | 问题诊断 |

---

## 六、记忆系统执行路径

### 6.1 分层记忆流转

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           记忆系统架构                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐                                                           │
│  │  短期记忆     │ ← 当前任务内，当前Agent                                   │
│  │ (ShortTerm)  │                                                           │
│  │              │  容量: 500条目 LRU                                         │
│  │  TTL: 任务结束 │  存储: 内存 (OrderedDict)                                │
│  └──────┬───────┘                                                           │
│         │                                                                    │
│         │ 消息数 ≥ 30 OR 任务结束                                            │
│         ▼                                                                    │
│  ┌──────────────┐                                                           │
│  │  会话记忆     │ ← 任务内跨Agent共享                                        │
│  │ (Session)    │                                                           │
│  │              │  容量: 500条目                                              │
│  │  TTL: 会话结束 │  存储: 内存 + 文件 (data/memory/session.json)            │
│  └──────┬───────┘                                                           │
│         │                                                                    │
│         │ 重要性 ≥ 0.7 OR 用户标记                                           │
│         ▼                                                                    │
│  ┌──────────────┐                                                           │
│  │  长期记忆     │ ← 跨任务持久化                                             │
│  │ (LongTerm)   │                                                           │
│  │              │  容量: 无限制                                              │
│  │  持久化: SQLite │  存储: SQLite + ChromaDB 向量索引                        │
│  └──────┬───────┘                                                           │
│         │                                                                    │
│         │ retention < 0.1                                                   │
│         ▼                                                                    │
│  ┌──────────────┐                                                           │
│  │  情景记忆     │ ← 执行轨迹记录                                            │
│  │ (Episodic)   │                                                           │
│  │              │  存储: SQLite                                              │
│  │  时间线+因果  │  用于: 审计、回放、错误追溯                                │
│  └──────────────┘                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 记忆召回路径

```python
UnifiedMemoryManager.recall(query: str, top_k: int = 3) -> List[MemoryEntry]:
    """
    召回路径: 短期 → 会话 → 长期 → 向量搜索
    """
    # 1. 短期记忆精确匹配
    if value := self.short_term.get(key):
        return [MemoryEntry(content=value, source="short_term")]

    # 2. 会话记忆匹配
    if value := self.session.get(key):
        return [MemoryEntry(content=value, source="session")]

    # 3. 长期记忆向量搜索
    query_vector = self.embeddings.encode(query)
    results = self.long_term.search(query_vector, top_k)
    return results
```

### 6.3 记忆存储路径

```python
UnifiedMemoryManager.remember(key: str, value: Any, importance: float = 0.5):
    """
    存储路径:
    """
    # 1. 重要记忆 → 长期记忆
    if importance >= 0.7:
        self.long_term.store(key, value)

    # 2. 普通记忆 → 短期记忆
    else:
        self.short_term.store(key, value)

    # 3. 同时记录到情景记忆 (用于回放)
    self.episodic.record(
        event="memory_store",
        key=key,
        value=value,
        importance=importance
    )

    # 4. 检查是否需要压缩
    if self.short_term.size() >= self.compression_threshold:
        self._compress_memories()
```

---

## 七、存储层执行路径

### 7.1 双存储架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           存储层架构                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Storage Layer                                 │    │
│  │  storage/paper_db.py                                                 │    │
│  │                                                                        │    │
│  │   ┌─────────────────────┐         ┌─────────────────────┐            │    │
│  │   │      SQLite          │         │      ChromaDB        │            │    │
│  │   │   (元数据存储)        │         │   (向量存储)         │            │    │
│  │   │                      │         │                      │            │    │
│  │   │  Paper表:            │         │  collections:        │            │    │
│  │   │  - id               │         │  - paper_embeddings │            │    │
│  │   │  - title            │         │    (语义搜索)        │            │    │
│  │   │  - authors          │         │                      │            │    │
│  │   │  - year             │         │  - citation_graph    │            │    │
│  │   │  - abstract         │         │    (引用关系)        │            │    │
│  │   │  - doi              │         │                      │            │    │
│  │   │                      │         │                      │            │    │
│  │   │  Citations表:       │         │                      │            │    │
│  │   │  - paper_id         │         │                      │            │    │
│  │   │  - cited_paper_id   │         │                      │            │    │
│  │   │  - context          │         │                      │            │    │
│  │   └──────────┬──────────┘         └──────────┬──────────┘            │    │
│  │              │                               │                          │    │
│  │              └───────────────┬───────────────┘                          │    │
│  │                              ▼                                          │    │
│  │                    ┌─────────────────────┐                              │    │
│  │                    │    PaperDB         │                              │    │
│  │                    │    (统一接口)       │                              │    │
│  │                    │                    │                              │    │
│  │                    │  - store_paper()   │                              │    │
│  │                    │  - get_paper()     │                              │    │
│  │                    │  - search_papers() │                              │    │
│  │                    │  - find_duplicates()│                             │    │
│  │                    └─────────────────────┘                              │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 查重路径

```python
PaperDB.find_duplicates(paper: dict) -> List[dict]:
    """
    多维度查重:
    """
    # 1. DOI 精确匹配
    if paper.get("doi"):
        existing = self.sqlite.query(
            "SELECT * FROM papers WHERE doi = ?",
            (paper["doi"],)
        )
        if existing:
            return existing

    # 2. 标题相似度匹配 (模糊)
    if paper.get("title"):
        similar = self.chroma_db.similarity_search(
            paper["title"],
            collection="paper_titles",
            threshold=0.95
        )
        if similar:
            return similar

    # 3. 作者+年份 组合匹配
    if paper.get("authors") and paper.get("year"):
        existing = self.sqlite.query(
            "SELECT * FROM papers WHERE authors = ? AND year = ?",
            (json.dumps(paper["authors"]), paper["year"])
        )
        if existing:
            return existing

    return []  # 无重复
```

---

## 八、熔断保护路径

### 8.1 熔断状态机

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CircuitBreaker 状态机                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│     CLOSED                                          HALF_OPEN                │
│   ┌──────────┐                                   ┌──────────┐               │
│   │ 正常     │ ──(error_rate > 30% 连续失败≥5)──→│ 半开     │               │
│   │ 请求正常  │                                   │ 允许测试 │               │
│   │          │ ←───────(连续成功≥3)──────────────│ 请求    │               │
│   └──────────┘                                   └──────────┘               │
│       │                                                  │                  │
│       │ error_rate > 30% OR                             │ failure           │
│       │ 连续失败 ≥ 5 OR                                 │                   │
│       │ 超时 ≥ 5min                                     ▼                   │
│       ▼                                          ┌──────────┐               │
│   ┌──────────┐                                   │  OPEN    │               │
│   │  OPEN    │◄──────────────────────────────────│  熔断    │               │
│   │ 拒绝请求 │   冷却时间 60s 后自动转换            └──────────┘               │
│   └──────────┘                                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 熔断决策

```python
CircuitBreaker.call(func, *args, **kwargs):
    # 1. 检查状态
    if self.state == OPEN:
        # 熔断中，调用降级
        return self.fallback_handler.execute(func.__name__)

    # 2. 尝试执行
    try:
        result = func(*args, **kwargs)
        self._on_success()
        return result

    except Exception as e:
        self._on_failure(e)

        # 检查是否触发熔断
        if self._should_trip():
            self.state = OPEN
            self.fallback_handler.execute(func.__name__)

        raise e
```

---

## 九、模块演进说明

| 模块 | 状态 | 说明 |
|------|------|------|
| `server/` | **新增** | 从 api_server.py 迁移，HTTP服务入口 |
| `agents/` | **新增** | 新版Agent框架，ReAct Loop |
| `orchestration/` | **新增** | 编排兼容层 (导出 unified/) |
| `harness/` | **新增** | 质量保障兼容层 (导出 unified/) |
| `unified/` | 保留 | 向后兼容，继续使用 |
| `workflow/` | 预留 | 预留工作流目录（空） |

---

## 十、完整请求链路总结

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         完整请求链路                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [1] 前端请求                                                                │
│      React (port 5173) ──→ Axios ──→ aiohttp (port 8000)                   │
│                             Headers: {X-API-Key: <key>}                     │
│                                                                              │
│  [2] 网关认证                                                                │
│      server/api_server.py → api_key_auth_middleware                        │
│          │                                                                  │
│          ├── Valid → 继续                                                    │
│          └── Invalid → 401 Unauthorized                                     │
│                                                                              │
│  [3] 请求路由                                                                │
│      /api/papers/*    → api/paper_api.py                                    │
│      /api/reports/*   → api/reports_api.py                                  │
│      /api/route/*     → unified/intent_router.py                            │
│      /api/workflow/*  → api/workflow_api.py → langgraph_workflow             │
│      /api/kg/*        → api/knowledge_graph_api.py                           │
│                                                                              │
│  [4] 意图识别 (LLM辅助)                                                      │
│      unified/intent_router.py → IntentRouter.route()                        │
│          │                                                                  │
│          ├── 关键词快速匹配                                                   │
│          ├── LLM 辅助识别 (ChatOpenAI)                                       │
│          ├── 置信度校准                                                     │
│          └── 意图 → Agent 映射                                              │
│                                                                              │
│  [5] Agent 执行                                                             │
│      新版: agents/loops/react_loop.py → ReActExecutor                       │
│      兼容: unified/master_supervisor.py → MasterSupervisor                 │
│          │                                                                  │
│          ├── LLM 调用 (ChatOpenAI.ainvoke)                                  │
│          ├── Memory 记忆 (memory/unified.py)                                │
│          └── Search 搜索 (search/paper_search.py)                           │
│                                                                              │
│  [6] 质量保障                                                               │
│      unified/circuit_breaker.py → CircuitBreaker                            │
│      unified/hitl_manager.py → HITLManager                                  │
│      evaluation/quality_evaluator.py → Evaluator                           │
│                                                                              │
│  [7] 响应返回                                                                │
│      AgentOutput → SSE/JSON ──→ Axios ──→ React State                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

**文档版本**: v2.0
**更新日期**: 2026-05-03
**基于代码版本**: fresh-start branch
