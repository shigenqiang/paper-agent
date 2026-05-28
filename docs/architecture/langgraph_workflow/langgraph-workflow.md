# LangGraph Workflow 工作流详解

> 位置: `src/agents_v2/langgraph_workflow/`
> 版本: v4.0
> 更新日期: 2026-05-03

## 一、核心文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `unified_workflow.py` | ~20KB | 统一工作流定义 (UnifiedWorkflow) |
| `state.py` | ~5KB | 状态定义 (PaperAgentState) |
| `edges.py` | ~2KB | 条件边定义 |
| `runner.py` | ~3KB | 运行入口 |
| `workflow.py` | ~9KB | 基础工作流 |

## 二、状态定义 (PaperAgentState)

实际代码使用 `@dataclass Paper` + `PaperAgentState(dict子类)`:

```python
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class Paper:
    """论文数据结构"""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    year: int = 0
    venue: str = ""
    citations: int = 0
    paper_id: str = ""
    url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class PaperAgentState(dict):
    """LangGraph 状态 - 继承自 dict"""
    user_id: str = ""
    session_id: str = ""
    user_query: str = ""
    papers: List[Dict] = field(default_factory=list)
    selected_papers: List[Dict] = field(default_factory=list)
    outline: Dict = field(default_factory=dict)
    draft: str = ""
    feedback: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    # ... 更多字段
```

## 三、工作流路径 (6条)

### 3.1 Search 工作流 (搜索)

```
router (intent=search)
  │
  └──→ crawler → selector → END

节点:
  - crawler: 多源论文检索
  - selector: LLM 评分筛选
```

### 3.2 Writing 工作流 (写作) - 完整流程

```
router (intent=writing)
  │
  └──→ diagnostic → topic → literature → methodology
                │
                ▼ (质量门禁)
            ┌───────────────────────────┐
            │  HITL 中断点 (可选)       │
            └───────────────────────────┘
                │
                ▼
             outline → writing → review → evaluator
                                              │
                              ┌───────────────┴───────────────┐
                              │                               │
                        [分数 ≥ 7.0]                     [分数 < 7.0]
                              │                               │
                              ▼                               ▼
                           END                           返回 writing 返修
```

**关键节点**:
- `diagnostic`: 选题诊断 (守门员)
- `topic`: 选题生成
- `literature`: 文献搜索
- `methodology`: 方法论
- `hitl_intervene`: HITL 人工介入节点

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

### 3.4 QA 工作流 (问答) - 已集成 AcademicQASystem

```
router (intent=qa)
  │
  └──→ qa_search → qa_synthesize → qa_answer → END

节点:
  - qa_search: 搜索相关论文
  - qa_synthesize: 综合搜索结果 (规则引擎 + LLM)
  - qa_answer: 生成回答 (集成 AcademicQASystem)
```

**QA 严格模式特性**:
- CRAG 检索质量评估
- Self-RAG 反思生成
- 幻觉检测 (SelfCheckGPT)
- 置信度校准
- 多跳推理支持
- RAGAs 评估

### 3.5 Revision 工作流 (修改)

```
router (intent=revision)
  │
  └──→ revise → refine → polish → END

节点:
  - revise: 修订内容
  - refine: 精炼表达
  - polish: 最终润色
```

## 四、LangGraph 节点详情 (23个)

| 节点 | 文件 | 功能 |
|------|------|------|
| `router` | `nodes/router.py` | 意图分类，路由到对应工作流 |
| `diagnostic` | `nodes/diagnostic.py` | 选题诊断 (守门员) |
| `topic` | `nodes/topic.py` | 选题生成 |
| `literature` | `nodes/literature.py` | 文献搜索 |
| `methodology` | `nodes/methodology.py` | 方法论 |
| `crawler` | `nodes/crawler.py` | 多源论文搜索 |
| `selector` | `nodes/selector.py` | LLM 评分筛选 |
| `outline` | `nodes/outline.py` | 大纲生成 |
| `writing` | `nodes/writing.py` | 论文写作 |
| `review` | `nodes/reviewer.py` | 评审反馈 |
| `evaluator` | `nodes/evaluator.py` | 多维度评分 |
| `hitl_intervene` | - | HITL 人工介入 |
| `memory_recall` | `nodes/memory.py` | 记忆召回 |
| `memory_remember` | `nodes/memory.py` | 记忆存储 |
| `multimodal` | `nodes/multimodal.py` | 图文理解 |
| `kg` | `nodes/knowledge_graph.py` | 知识图谱 |
| `report_crawl` | `nodes/report_crawl.py` | 报告爬取 |
| `report_analyze` | `nodes/report_analyze.py` | 报告分析 |
| `report_gen` | `nodes/report_gen.py` | 报告生成 |
| `qa_search` | `nodes/qa_search.py` | QA 搜索 |
| `qa_synthesize` | `nodes/qa_synthesize.py` | QA 综合 |
| `qa_answer` | `nodes/qa_answer.py` | QA 回答 |
| `revise` | `nodes/revise.py` | 修订 |
| `refine` | `nodes/refine.py` | 精炼 |
| `polish` | `nodes/polish.py` | 润色 |

## 五、UnifiedWorkflow 架构

```python
class UnifiedWorkflow:
    """统一工作流 - 整合所有工作流路径"""

    def __init__(
        self,
        llm=None,
        enable_memory: bool = True,
        enable_multimodal: bool = True,
        enable_kg: bool = True,
        enable_evaluation: bool = True,
        enable_hitl: bool = False,
    ):

        # 初始化所有节点
        self.router = RouteNode(...)
        self.diagnostic = DiagnosticNode(...)
        self.topic = TopicNode(...)
        self.literature = LiteratureNode(...)
        self.methodology = MethodologyNode(...)
        self.writing_node = WritingNode(...)

        # 可选节点
        if enable_memory:
            self.memory = MemoryNode()
        if enable_multimodal:
            self.multimodal = MultimodalNode()
        if enable_kg:
            self.kg = KnowledgeGraphNode()
        if enable_evaluation:
            self.evaluator = EvaluatorNode()

        # 报告/QA/修改节点
        self.report_crawl = ReportCrawlNode()
        self.report_analyze = ReportAnalyzeNode()
        self.report_gen = ReportGenNode(...)
        self.qa_search = QASearchNode()
        self.qa_synthesize = QASynthesizeNode()
        self.qa_answer = QAAnswerNode(...)
        self.revise = ReviseNode(...)
        self.refine = RefineNode(...)
        self.polish = PolishNode(...)
```

## 六、诊断节点与质量门禁

```python
# 诊断后的质量门禁
workflow.add_conditional_edges(
    "diagnostic",
    diagnostic_quality_gate,
    {
        "outline": "topic",           # 质量达标，进入选题
        "hitl_intervene": "hitl_intervene",  # 需要人工介入
        "diagnostic_retry": "diagnostic",     # 迭代重试
    },
)

# HITL 恢复后分流
workflow.add_conditional_edges(
    "hitl_intervene",
    hitl_decision_router,
    {
        "continue": "topic",   # 批准继续
        "revise": "diagnostic", # 退回诊断
        "terminate": END,       # 终止
    },
)
```

## 七、 HITL 中断点

```python
HITL_INTERRUPT_POINTS = {
    "after_diagnostic_topic": "diagnostic",  # 诊断发现选题问题
    "after_outline": "outline",               # 大纲生成后
    "after_review": "review",                 # 审查后
    "after_polish": "polish",                 # 润色后
}
```

## 八、边定义 (edges.py)

```python
def route_by_intent(state: dict) -> str:
    """根据意图路由"""
    intent = state.get("intent", "search")
    return {
        "search": "crawler",
        "writing": "diagnostic",
        "report": "report_crawl",
        "qa": "qa_search",
        "revision": "revise",
    }.get(intent, "crawler")

def diagnostic_quality_gate(state: dict) -> str:
    """诊断质量门禁"""
    diagnostic = state.get("diagnostic_result", {})
    severity = diagnostic.get("severity", {})

    if severity.get("total", 0) == 0:
        return "outline"  # 无问题，通过
    elif severity.get("critical", 0) > 0:
        return "hitl_intervene"  # 严重问题，需人工介入
    else:
        return "diagnostic_retry"  # 一般问题，重试

def should_continue(state: dict) -> str:
    """判断是否继续迭代"""
    if state.get("evaluation_passed"):
        return "done"
    return "write"
```

## 九、Checkpoint 与恢复

```python
from langgraph.checkpoint.memory import MemorySaver

# 启用 HITL 时使用 checkpointer
workflow = UnifiedWorkflow(
    llm=llm,
    enable_hitl=True,
).compile()

# 从检查点恢复
config = {"configurable": {"thread_id": "session123"}}
result = await workflow.app.ainvoke(initial_state, config=config)
```

## 十、QA 工作流集成 AcademicQASystem

QA 节点中的 `QAAnswerNode` 已集成 `AcademicQASystem`:

```python
class QAAnswerNode:
    def __init__(self, llm_provider=None, use_academic_qa: bool = True):
        if use_academic_qa:
            from ...academic_qa import AcademicQASystem, AcademicQAConfig
            config = AcademicQAConfig(
                llm=llm_provider,
                enable_crag=True,
                enable_self_rag=True,
                enable_hallucination_detection=True,
                enable_confidence_calibration=True,
                enable_multi_hop=True,
            )
            self._academic_qa_system = AcademicQASystem(config=config)

    async def __call__(self, state):
        # 使用 AcademicQASystem 生成答案
        qa_result = await self._academic_qa_system.ask(
            query=state["user_query"],
            contexts=self._build_contexts(state["qa_synthesis"], state["papers"]),
            mode="strict"
        )
        # ...
```

---

**更新日期**: 2026-05-03
**基于代码**: `src/agents_v2/langgraph_workflow/unified_workflow.py`
