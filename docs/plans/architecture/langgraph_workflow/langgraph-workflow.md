# LangGraph Workflow 工作流详解

> 位置: `src/agents_v2/langgraph_workflow/`

## 一、核心文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `unified_workflow.py` | 20,797 字节 | 统一工作流定义 |
| `state.py` | 5,436 字节 | PaperAgentState 状态定义 |
| `edges.py` | 1,701 字节 | 条件边定义 |
| `runner.py` | 3,112 字节 | 运行入口 |
| `workflow.py` | 9,237 字节 | 基础工作流 |

## 二、状态定义 (PaperAgentState)

```python
class PaperAgentState(TypedDict):
    """LangGraph 状态"""

    # 用户信息
    user_id: str
    session_id: str

    # 查询
    user_query: str

    # 论文数据
    papers: List[dict]              # 原始论文列表
    selected_papers: List[dict]    # 筛选后的论文

    # 写作数据
    outline: dict                  # 大纲
    draft: str                     # 初稿

    # 反馈
    feedback: str                  # 评审反馈
    iteration: int                 # 当前迭代
    max_iterations: int           # 最大迭代

    # 阶段
    current_phase: str             # 当前阶段
    phases_completed: List[str]   # 已完成阶段

    # 元数据
    timestamp: str
    errors: List[str]
    trace_id: str
```

## 三、5 条工作流路径

### 3.1 Search 工作流 (搜索)

```
router (intent=search)
  │
  └──→ crawler → selector → END

节点:
  - crawler: 多源论文检索 (arXiv/PubMed/Semantic Scholar/OpenAlex)
  - selector: LLM 评分筛选 Top 20
```

### 3.2 Writing 工作流 (写作)

```
router (intent=writing)
  │
  └──→ memory_recall → crawler → selector → [multimodal] → [kg]
                                              │
                                              ▼
                                         outline → writer → reviewer
                                                          │
                                                          ▼
                                                     evaluator
                                                          │
                                  ┌───────────────────────┴───────────────────────┐
                                  │                                               │
                            [分数 ≥ 7.0]                                   [分数 < 7.0]
                                  │                                               │
                                  ▼                                               ▼
                               END                                         返回 writer 返修
                                                                          (最多 max_iterations 次)
```

### 3.3 Report 工作流 (报告)

```
router (intent=report)
  │
  └──→ report_crawl → report_analyze → report_gen → END

节点:
  - report_crawl: 爬取报告数据
  - report_analyze: 分析报告内容
  - report_gen: 生成最终报告
```

### 3.4 QA 工作流 (问答)

```
router (intent=qa)
  │
  └──→ qa_search → qa_synthesize → qa_answer → END

节点:
  - qa_search: 搜索相关论文
  - qa_synthesize: 综合搜索结果
  - qa_answer: 生成回答
```

### 3.5 Revise 工作流 (修改)

```
router (intent=revise)
  │
  └──→ revise → refine → polish → END

节点:
  - revise: 修订内容
  - refine: 精炼表达
  - polish: 最终润色
```

## 四、LangGraph 节点详情

| 节点 | 文件大小 | 功能 |
|------|----------|------|
| `router.py` | 3,183 字节 | 意图分类，路由到对应工作流 |
| `crawler.py` | 13,304 字节 | 多源论文搜索 |
| `selector.py` | 4,785 字节 | LLM 评分筛选论文 |
| `outline.py` | 7,775 字节 | 基于论文生成大纲 |
| `writer.py` | 7,292 字节 | 逐节生成论文内容 |
| `reviewer.py` | 4,555 字节 | 质量评审，反馈改进 |
| `evaluator.py` | 10,915 字节 | 多维度评分，决策通过/返修 |
| `memory.py` | 7,895 字节 | 记忆召回与存储 |
| `multimodal.py` | 5,823 字节 | 论文图表理解 |
| `knowledge_graph.py` | 6,054 字节 | 知识图谱构建 |

## 五、Writer 节点详解

```python
# langgraph_workflow/nodes/writer.py

async def writer_node(state: PaperAgentState) -> PaperAgentState:
    """
    写作节点：逐节生成论文内容

    输入:
      - selected_papers: 筛选后的论文列表
      - outline: 大纲结构

    处理:
      1. 遍历大纲章节
      2. 对每节调用 LLM 生成内容
      3. 引用相关论文
      4. 合并为完整初稿

    输出:
      - draft: 完整论文初稿
    """
    papers = state["selected_papers"]
    outline = state["outline"]

    sections = []
    for chapter in outline["chapters"]:
        section_content = await llm.ainvoke([
            SystemMessage(f"你是一个学术论文写作专家..."),
            HumanMessage(f"根据以下论文写第{chapter['title']}节:\n{papers}")
        ])
        sections.append(section_content)

    draft = "\n\n".join(sections)
    return {"draft": draft}
```

## 六、Evaluator 节点详解

```python
# langgraph_workflow/nodes/evaluator.py

async def evaluator_node(state: PaperAgentState) -> PaperAgentState:
    """
    评估节点：多维度评分 + 决策

    评分维度:
      - 结构 (structure): 0-10
      - 逻辑 (logic): 0-10
      - 原创性 (originality): 0-10
      - 语言 (language): 0-10
      - 引用 (citation): 0-10
      - 完整性 (completeness): 0-10
      - 格式 (format): 0-10

    决策规则:
      - 平均分 ≥ 7.0 → 通过 (END)
      - 平均分 < 7.0 → 返修 (返回 writer)
      - 迭代次数 ≥ max_iterations → 强制通过 (防止无限循环)
    """
    draft = state["draft"]
    iteration = state["iteration"]

    scores = await llm.ainvoke([
        SystemMessage("你是一个论文质量评审专家..."),
        HumanMessage(f"评审以下论文:\n{draft}")
    ])

    avg_score = sum(scores.values()) / len(scores)

    if avg_score >= 7.0 or iteration >= state["max_iterations"]:
        return {"evaluation_passed": True}
    else:
        return {
            "evaluation_passed": False,
            "iteration": iteration + 1
        }
```

## 七、边定义 (edges.py)

```python
def route_by_intent(state: PaperAgentState) -> str:
    """根据意图路由"""
    intent = state.get("intent", "search")
    intent_to_workflow = {
        "search": "search_workflow",
        "writing": "writing_workflow",
        "report": "report_workflow",
        "qa": "qa_workflow",
        "revise": "revise_workflow",
    }
    return intent_to_workflow.get(intent, "search_workflow")

def should_continue(state: PaperAgentState) -> str:
    """判断是否继续迭代"""
    if state.get("evaluation_passed"):
        return "end"
    return "continue"
```

## 八、Runner 执行入口

```python
# langgraph_workflow/runner.py

class WorkflowRunner:
    def __init__(self, llm_config: LLMConfig):
        self.llm_config = llm_config
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(PaperAgentState)

        # 添加节点
        workflow.add_node("router", router_node)
        workflow.add_node("crawler", crawler_node)
        # ... 更多节点

        # 添加边
        workflow.add_edge("router", "crawler")
        # ...

        # 添加条件边
        workflow.add_conditional_edges(
            "evaluator",
            should_continue,
            {"end": END, "continue": "writer"}
        )

        return workflow.compile()

    async def run(self, user_input: dict) -> dict:
        result = await self.graph.ainvoke(user_input)
        return result
```

## 九、Checkpoint 与恢复

```python
# LangGraph 内置 Checkpointer

from langgraph.checkpoint import MemorySaver

checkpointer = MemorySaver()

workflow = StateGraph(PaperAgentState).compile(
    checkpointer=checkpointer,
    interrupt_before=["writer", "reviewer"]  # HITL 中断点
)

# 从检查点恢复
config = {"configurable": {"thread_id": "session123"}}
result = workflow.invoke(None, config=config)
```

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/langgraph_workflow/`