# 学术写作助手 - 基于论文写作流程的Multi-Agent架构

## 背景与需求

### 用户明确要求
- **Multi-Agent系统** - 不是单Agent
- **不是Research/Analyst/Writer线性流程** - 这个流程不符合真实论文写作
- **基于真实论文写作流程**设计Agent

### 真实论文写作流程

根据学术写作规范，论文写作的真实步骤是：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    学术论文写作标准流程                                   │
│                                                                         │
│  1. Topic Selection ──────────────────────────────────────► 主题选择    │
│                          │                                              │
│  2. Literature Collection ─────► Literature Review ──────► 文献工作    │
│                          │                    │                          │
│                          │                    ▼                          │
│  3. Thesis Statement ◄────────────────── 研究问题凝练                   │
│                          │                                              │
│                          ▼                                              │
│  4. Outline ────────────────────────────────────────────► 大纲制定    │
│                          │                                              │
│                          ▼                                              │
│  5. Section Drafting ◄─────────────────────────────────► 分节撰写    │
│                          │                                              │
│                          ▼                                              │
│  6. Revision ──────────────────────────────────────────► 修订编辑    │
│                          │                                              │
│                          ▼                                              │
│  7. Final Review ───────────────────────────────────────► 最终审核    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 各阶段详解

#### Step 1: Topic Selection (主题选择)
- 确定研究领域
- 缩小主题范围
- 评估主题可行性
- **输出**: 具体研究问题

#### Step 2: Literature Collection & Review (文献收集与综述)
- 搜索相关文献
- 筛选高质量论文
- 阅读并提取关键信息
- 识别研究空白
- **输出**: 文献笔记、研究空白列表

#### Step 3: Thesis Statement (研究问题凝练)
- 明确研究动机
- 凝练研究目标
- 定义研究范围
- **输出**: 清晰的研究陈述/Thesis

#### Step 4: Outline (大纲制定)
- 设计论文结构
- 规划各章节内容
- 确定关键论点
- **输出**: 详细大纲

#### Step 5: Section Drafting (分节撰写)
- 按大纲撰写各章节
- 保持内容连贯性
- 添加引用和参考文献
- **输出**: 初稿各章节

#### Step 6: Revision (修订编辑)
- 内容修订
- 语言润色
- 格式调整
- **输出**: 修订稿

#### Step 7: Final Review (最终审核)
- 完整性检查
- 质量评估
- **输出**: 最终论文

---

## 新架构设计

### Agent团队设计

基于真实论文写作流程，设计以下Agent：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Supervisor Agent                                │
│   - 任务协调与分配                                                     │
│   - 质量门控决策                                                       │
│   - 迭代控制                                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│ TopicAgent    │         │ Literature    │         │ Thesis       │
│ (主题选择)    │◄───────►│ Agent         │◄───────►│ Agent        │
│               │         │ (文献工作)    │         │ (研究凝练)    │
└───────────────┘         └───────────────┘         └───────────────┘
        │                           │                           │
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    │
                                    ▼
                           ┌───────────────┐
                           │ Outline      │
                           │ Agent        │
                           │ (大纲制定)    │
                           └───────┬───────┘
                                   │
                                   ▼
                          ┌────────────────┐
                          │ DraftWriter   │
                          │ Agent         │
                          │ (分节撰写)    │
                          └───────┬───────┘
                                  │
                                  ▼
                          ┌────────────────┐
                          │ Editor        │
                          │ Agent         │
                          │ (修订编辑)    │
                          └───────┬───────┘
                                  │
                                  ▼
                          ┌────────────────┐
                          │ Reviewer      │
                          │ Agent         │
                          │ (最终审核)    │
                          └───────────────┘
```

### Agent职责

| Agent | 职责 | 核心能力 |
|-------|------|----------|
| **TopicAgent** | 主题选择与范围缩小 | 领域分析、可行性评估 |
| **LiteratureAgent** | 文献搜索、筛选、阅读 | 多源搜索、相关性排序、PDF阅读、信息提取 |
| **ThesisAgent** | 研究问题凝练 | 批判性分析、研究空白识别 |
| **OutlineAgent** | 大纲制定 | 结构化思维、内容规划 |
| **DraftWriterAgent** | 分节撰写 | 学术写作、引用管理 |
| **EditorAgent** | 修订编辑 | 语言润色、格式调整 |
| **ReviewerAgent** | 最终审核 | 质量评估、多视角Critique |

### 关键设计：非严格线性流程

```
┌─────────────────────────────────────────────────────────────┐
│                     实际协作模式                              │
│                                                             │
│   TopicAgent ──────────────┐                               │
│         │                  │                               │
│         ▼                  │                               │
│   LiteratureAgent ◄────────┴────────► ThesisAgent         │
│         │                                     │            │
│         │                                     ▼            │
│         │                              OutlineAgent        │
│         │                                     │            │
│         ▼                                     │            │
│   (可并行)                              DraftWriterAgent   │
│         │                                     │            │
│         └──────────────┬──────────────────────┘            │
│                        │                                   │
│                        ▼                                   │
│                   EditorAgent                              │
│                        │                                   │
│                        ▼                                   │
│                   ReviewerAgent                            │
└─────────────────────────────────────────────────────────────┘
```

**关键点**：
1. LiteratureAgent和ThesisAgent可以并行工作
2. OutlineAgent需要等待Topic和Literature的初步结果
3. DraftWriterAgent可以分段并行撰写不同章节
4. EditorAgent在DraftWriterAgent之后，但可以迭代

---

## 核心Agent详细设计

### 1. TopicAgent (主题选择)

```python
class TopicAgent(BaseAgent):
    """
    TopicAgent - 主题选择与范围缩小

    职责：
    - 分析研究领域
    - 生成候选主题
    - 评估可行性
    - 凝练具体研究问题
    """

    async def execute(self, input_data: Dict, context: Optional[Dict] = None) -> AgentOutput:
        user_request = input_data.get("user_request", "")

        # 1. 领域分析
        domain_analysis = await self._analyze_domain(user_request)

        # 2. 生成候选主题
        candidates = await self._generate_topic_candidates(domain_analysis)

        # 3. 评估可行性
        evaluated = await self._evaluate_feasibility(candidates)

        # 4. 选择最佳主题
        best_topic = await self._select_best_topic(evaluated)

        return AgentOutput(
            success=True,
            result={
                "selected_topic": best_topic,
                "alternative_topics": evaluated[1:],
                "domain_analysis": domain_analysis
            },
            agent_name=self.name,
            reasoning=f"Selected topic: {best_topic['title']}"
        )
```

### 2. LiteratureAgent (文献工作)

```python
class LiteratureAgent(BaseAgent):
    """
    LiteratureAgent - 文献收集与综述

    职责：
    - 多源文献搜索
    - 质量筛选
    - PDF阅读与信息提取
    - 识别研究空白
    """

    async def execute(self, input_data: Dict, context: Optional[Dict] = None) -> AgentOutput:
        topic = input_data.get("topic", "")
        research_question = context.get("research_question", "")

        # 1. 多角度搜索查询
        search_queries = await self._generate_search_queries(topic, research_question)

        # 2. 多引擎并行搜索
        all_papers = await self._multi_engine_search(search_queries)

        # 3. 质量筛选与排序
        ranked_papers = await self._rank_papers(all_papers, research_question)

        # 4. 深度阅读
        paper_analyses = await self._deep_read(ranked_papers[:20])

        # 5. 识别研究空白
        gaps = await self._identify_gaps(paper_analyses, research_question)

        return AgentOutput(
            success=True,
            result={
                "papers": ranked_papers,
                "paper_analyses": paper_analyses,
                "research_gaps": gaps,
                "search_queries": search_queries
            },
            agent_name=self.name,
            reasoning=f"Collected {len(ranked_papers)} papers, identified {len(gaps)} gaps"
        )
```

### 3. ThesisAgent (研究问题凝练)

```python
class ThesisAgent(BaseAgent):
    """
    ThesisAgent - 研究问题凝练

    职责：
    - 分析文献综述
    - 凝练研究动机
    - 明确研究目标
    - 定义研究范围
    """

    async def execute(self, input_data: Dict, context: Optional[Dict] = None) -> AgentOutput:
        literature_result = context.get("literature_result", {})
        topic = input_data.get("topic", "")

        paper_analyses = literature_result.get("paper_analyses", [])
        existing_gaps = literature_result.get("research_gaps", [])

        # 1. 分析现有研究
        analysis = await self._analyze_existing_research(paper_analyses)

        # 2. 凝练研究动机
        motivation = await self._refine_motivation(topic, analysis, existing_gaps)

        # 3. 明确研究目标
        objectives = await self._define_objectives(motivation, existing_gaps)

        # 4. 形成Thesis Statement
        thesis = await self._formulate_thesis(topic, motivation, objectives)

        return AgentOutput(
            success=True,
            result={
                "thesis_statement": thesis,
                "research_motivation": motivation,
                "research_objectives": objectives,
                "scope": await self._define_scope(objectives)
            },
            agent_name=self.name,
            reasoning="Thesis formulated based on literature analysis"
        )
```

### 4. OutlineAgent (大纲制定)

```python
class OutlineAgent(BaseAgent):
    """
    OutlineAgent - 大纲制定

    职责：
    - 设计论文结构
    - 规划各章节内容
    - 确定关键论点
    """

    async def execute(self, input_data: Dict, context: Optional[Dict] = None) -> AgentOutput:
        thesis = context.get("thesis_statement", "")
        literature = context.get("literature_result", {})

        # 1. 设计章节结构
        structure = await self._design_structure(thesis)

        # 2. 规划各章节内容
        chapter_plans = await self._plan_chapters(structure, literature)

        # 3. 确定关键论点
        key_arguments = await self._identify_key_arguments(thesis, literature)

        # 4. 整合大纲
        outline = {
            "structure": structure,
            "chapters": chapter_plans,
            "key_arguments": key_arguments
        }

        return AgentOutput(
            success=True,
            result={"outline": outline},
            agent_name=self.name,
            reasoning=f"Created outline with {len(chapter_plans)} chapters"
        )
```

### 5. DraftWriterAgent (分节撰写)

```python
class DraftWriterAgent(BaseAgent):
    """
    DraftWriterAgent - 分节撰写

    职责：
    - 按大纲撰写各章节
    - 保持内容连贯性
    - 添加引用
    """

    async def execute(self, input_data: Dict, context: Optional[Dict] = None) -> AgentOutput:
        outline = context.get("outline", {})
        literature = context.get("literature_result", {})
        thesis = context.get("thesis_statement", "")

        # 1. 获取章节列表
        chapters = outline.get("chapters", [])

        # 2. 并行撰写各章节
        written_chapters = []
        for chapter in chapters:
            section = await self._write_chapter(chapter, thesis, literature, context)
            written_chapters.append(section)

        # 3. 整合初稿
        draft = self._compile_draft(written_chapters)

        return AgentOutput(
            success=True,
            result={
                "chapters": written_chapters,
                "full_draft": draft
            },
            agent_name=self.name,
            reasoning=f"Written {len(written_chapters)} sections"
        )
```

### 6. EditorAgent (修订编辑)

```python
class EditorAgent(BaseAgent):
    """
    EditorAgent - 修订编辑

    职责：
    - 内容修订
    - 语言润色
    - 格式调整
    """

    async def execute(self, input_data: Dict, context: Optional[Dict] = None) -> AgentOutput:
        draft = context.get("full_draft", "")
        outline = context.get("outline", {})

        # 1. 内容修订
        revised = await self._revise_content(draft, outline)

        # 2. 语言润色
        polished = await self._polish_language(revised)

        # 3. 格式调整
        formatted = await self._adjust_format(polished)

        # 4. 生成最终稿
        final_draft = formatted

        return AgentOutput(
            success=True,
            result={"final_draft": final_draft},
            agent_name=self.name,
            reasoning="Draft revised and polished"
        )
```

### 7. ReviewerAgent (最终审核)

```python
class ReviewerAgent(BaseAgent):
    """
    ReviewerAgent - 最终审核

    职责：
    - 多视角Critique
    - 质量评估
    - 决定是否通过
    """

    async def execute(self, input_data: Dict, context: Optional[Dict] = None) -> AgentOutput:
        paper = context.get("final_draft", "")
        thesis = context.get("thesis_statement", "")

        # 1. 多视角审核
        critiques = await self._multi_perspective_review(paper, thesis)

        # 2. 质量评分
        quality_score = await self._calculate_quality_score(critiques)

        # 3. 决策
        passed = quality_score >= 7.0

        return AgentOutput(
            success=True,
            result={
                "passed": passed,
                "quality_score": quality_score,
                "critiques": critiques
            },
            agent_name=self.name,
            reasoning=f"Review complete, score: {quality_score}/10"
        )
```

---

## Supervisor Agent

```python
class SupervisorAgent(BaseAgent):
    """
    Supervisor - 任务协调与质量控制

    职责：
    1. 协调各Agent工作
    2. 管理状态流转
    3. 执行Validation Gate
    4. 控制迭代
    """

    async def execute(self, input_data: Dict, context: Optional[Dict] = None) -> AgentOutput:
        user_request = input_data.get("user_request", "")

        # 初始化状态
        state = create_initial_state(user_request)

        # 1. TopicAgent
        topic_result = await self._run_agent("topic", {"user_request": user_request}, state)

        # 2. LiteratureAgent + ThesisAgent (并行)
        lit_result, thesis_result = await asyncio.gather(
            self._run_agent("literature", {"topic": topic_result.result["selected_topic"]}, state),
            self._run_agent("thesis", {"topic": topic_result.result["selected_topic"]}, state)
        )
        state.update({"literature_result": lit_result.result, "thesis_statement": thesis_result.result["thesis_statement"]})

        # 3. OutlineAgent
        outline_result = await self._run_agent("outline", {}, state)
        state["outline"] = outline_result.result["outline"]

        # 4. DraftWriterAgent
        draft_result = await self._run_agent("draft", {}, state)
        state["full_draft"] = draft_result.result["full_draft"]

        # 5. EditorAgent
        editor_result = await self._run_agent("editor", {}, state)
        state["final_draft"] = editor_result.result["final_draft"]

        # 6. ReviewerAgent
        review_result = await self._run_agent("reviewer", {}, state)

        # 7. 如果Reviewer不通过，迭代改进
        if not review_result.result["passed"]:
            for iteration in range(3):
                # 收集反馈
                feedback = review_result.result["critiques"]

                # 针对性修改
                state["feedback"] = feedback
                draft_result = await self._run_agent("draft", {}, state)
                state["full_draft"] = draft_result.result["full_draft"]

                editor_result = await self._run_agent("editor", {}, state)
                state["final_draft"] = editor_result.result["final_draft"]

                review_result = await self._run_agent("reviewer", {}, state)

                if review_result.result["passed"]:
                    break

        return AgentOutput(
            success=True,
            result={
                "paper": state["final_draft"],
                "topic": topic_result.result["selected_topic"],
                "thesis": state.get("thesis_statement", ""),
                "quality_score": review_result.result.get("quality_score", 0)
            },
            agent_name=self.name,
            reasoning="Complete paper generated"
        )
```

---

## 工作流编排

### DAG结构

```
                    ┌──────────────┐
                    │   Topic      │
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │Literature│   │  Thesis  │   │ (并行)   │
    │  Agent   │◄──┤  Agent   │◄──┘          │
    └────┬─────┘   └────┬─────┘              │
         │              │                    │
         └──────────────┼────────────────────┘
                        │
                        ▼
                 ┌──────────────┐
                 │   Outline    │
                 │    Agent     │
                 └──────┬───────┘
                        │
          ┌─────────────┴─────────────┐
          │                           │
          ▼                           ▼
   ┌─────────────┐             ┌─────────────┐
   │  Section 1  │             │  Section 2  │ (并行)
   └──────┬──────┘             └──────┬──────┘
          │                           │
          └─────────────┬─────────────┘
                        │
                        ▼
                 ┌──────────────┐
                 │   Editor     │
                 │    Agent     │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │   Reviewer   │
                 │    Agent     │
                 └──────────────┘
```

### Validation Gate

| 阶段 | 验证条件 | 失败处理 |
|------|----------|----------|
| Topic | 主题明确、可行 | 重新选择 |
| Literature | 论文数≥10, 相关性≥0.6 | 扩大搜索 |
| Thesis | 研究问题清晰、可验证 | 重新凝练 |
| Outline | 章节≥5, 结构完整 | 重新规划 |
| Draft | 章节完整、引用充分 | 补充撰写 |
| Review | 评分≥7.0 或 迭代≥3 | 强制通过 |

---

## 实施计划

### Phase 1: 核心Agent实现 (3-4天)
- [ ] TopicAgent 实现
- [ ] LiteratureAgent 实现
- [ ] ThesisAgent 实现
- [ ] OutlineAgent 实现

### Phase 2: 写作Agent实现 (2-3天)
- [ ] DraftWriterAgent 实现
- [ ] EditorAgent 实现
- [ ] ReviewerAgent 实现

### Phase 3: Supervisor集成 (2天)
- [ ] Supervisor Agent 实现
- [ ] DAG工作流编排
- [ ] Validation Gate 集成

### Phase 4: 测试与优化 (2天)
- [ ] 端到端测试
- [ ] 错误处理测试
- [ ] 性能优化

---

## 文件结构

```
src/
├── agents_v2/
│   ├── paper_agents/
│   │   ├── __init__.py
│   │   ├── topic_agent.py       # 主题选择
│   │   ├── literature_agent.py  # 文献工作
│   │   ├── thesis_agent.py      # 研究凝练
│   │   ├── outline_agent.py     # 大纲制定
│   │   ├── draft_writer.py      # 分节撰写
│   │   ├── editor_agent.py      # 修订编辑
│   │   └── reviewer_agent.py    # 最终审核
│   │
│   ├── supervisor/
│   │   ├── __init__.py
│   │   └── supervisor_agent.py  # 协调者
│   │
│   └── workflow/
│       ├── __init__.py
│       └── paper_workflow.py    # DAG工作流
│
└── state/
    └── paper_state.py           # 状态模型
```

---

## 优势分析

| 特性 | 旧架构 (Research→Analyst→Writer) | 新架构 (论文写作流程) |
|------|--------------------------------|---------------------|
| **Agent设计** | 按功能分工 | 按写作步骤分工 |
| **流程匹配** | 不符合真实写作 | 完全匹配真实写作 |
| **协作模式** | 严格线性 | 可并行协作 |
| **上下文传递** | Agent间损失 | 线性传递，损失少 |
| **质量控制** | 最后Critique | 每步都有质量门控 |
| **迭代粒度** | 全局迭代 | 局部迭代（具体章节） |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 多Agent并行协调复杂 | 可能死锁或状态不一致 | Supervisor统一协调 |
| 文献收集耗时长 | 整体延迟增加 | 并行搜索、多引擎 |
| 写作风格不一致 | 各章节风格差异 | Editor统一润色 |
| 上下文丢失 | Agent间传递损失 | 状态快照保存 |

---

*文档版本: v3.0 - 基于论文写作流程的Multi-Agent架构*
*最后更新: 2026-04-26*
