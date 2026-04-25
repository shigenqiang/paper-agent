"""
Planner-Orchestrated Research Agent架构

核心思想：用一个Planner作为中枢，动态调度各子Agent，而非固定线性流程。

改进点：
1. Planner中枢：统一调度，动态路由
2. 非阻塞流程：各阶段可并行，不必等待全部完成
3. 增量处理：边搜边读边分析，不用等全部完成
4. 容错设计：任何阶段失败都有降级和回滚
5. 动态调度：根据状态决定下一步，不是固定流程

流程图：
                    ┌─────────────────────────────────────────┐
                    │              Planner                    │
                    │  - 任务分解                            │
                    │  - 状态监控                            │
                    │  - 动态调度                            │
                    │  - 失败处理                            │
                    └──────────────────┬──────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         │                             │                             │
         ▼                             ▼                             ▼
  ┌──────────────┐           ┌──────────────┐           ┌──────────────┐
  │    Search    │◄─────────►│    Read      │◄─────────►│   Analyse    │
  │   (并行)     │   增量     │   (增量)     │   增量     │   (增量)     │
  │              │   迭代     │              │   更新     │              │
  └──────┬───────┘           └──────┬───────┘           └──────┬───────┘
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     │
                                     ▼
                            ┌──────────────┐
                            │   Critique   │
                            │   (多视角)   │
                            └──────┬───────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 │                 │                 │
                 ▼                 ▼                 ▼
          ┌────────────┐   ┌────────────┐   ┌────────────┐
          │   Write    │   │  Supplement │   │   Done     │
          │  (增量)    │   │  (补充)    │   │            │
          └────────────┘   └────────────┘   └────────────┘
"""
from typing import TypedDict, List, Dict, Any, Optional, Literal
from langgraph.graph import StateGraph, END, START
from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy
import asyncio
import logging

logger = logging.getLogger(__name__)


class Phase(str, Enum):
    """研究流程阶段"""
    PLANNING = "planning"
    SEARCHING = "searching"
    READING = "reading"
    ANALYZING = "analyzing"
    CRITIQUING = "critiquing"
    WRITING = "writing"
    SUPPLEMENT = "supplement"
    DONE = "done"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    """任务单元"""
    task_id: str
    task_type: str  # search, read, analyse, write, critique
    params: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class PhaseResult:
    """阶段结果"""
    phase: Phase
    success: bool
    data: Any = None
    error: Optional[str] = None
    partial: bool = False  # 是否部分成功


class PlannerState(TypedDict):
    """Planner协调状态"""

    # ===== 输入 =====
    query: str
    session_id: str

    # ===== 规划 =====
    phase: Phase
    tasks: List[Dict[str, Any]]  # 任务队列
    completed_tasks: List[Dict[str, Any]]  # 已完成任务

    # ===== 数据积累 =====
    papers: List[Dict]  # 所有找到的论文
    pending_papers: List[Dict]  # 待阅读论文
    read_papers: List[Dict]  # 已阅读论文
    analyses: List[Dict]  # 分析结果

    # ===== 质量控制 =====
    critique_score: float
    critique_passed: bool
    critique_details: Dict[str, Any]
    iteration: int
    max_iterations: int

    # ===== 写作 =====
    outline: List[Dict]
    writted_sections: List[Dict]
    current_section: int

    # ===== 容错 =====
    errors: List[Dict]
    checkpoints: Dict[str, Dict]
    rollback_count: int

    # ===== 结果 =====
    report: str
    status: str


# ========== Planner核心 ==========

class ResearchPlanner:
    """
    研究流程Planner - 动态调度各子Agent

    核心职责：
    1. 任务分解：将研究目标分解为可执行的任务
    2. 状态监控：跟踪各任务的状态和进度
    3. 动态调度：根据状态决定下一步行动
    4. 失败处理：任务失败时决定重试、降级或跳过
    """

    def __init__(self, max_concurrent: int = 3, max_iterations: int = 3):
        self.max_concurrent = max_concurrent
        self.max_iterations = max_iterations
        self._tasks: Dict[str, Task] = {}
        self._checkpoints: Dict[str, Dict] = {}

    def plan(self, query: str) -> List[Task]:
        """
        规划阶段：将查询分解为任务

        1. 生成多角度搜索任务
        2. 预设阅读任务（根据搜索结果动态添加）
        3. 预设分析任务
        """
        tasks = []

        # 1. 搜索任务 - 多角度
        search_queries = self._generate_search_queries(query)
        for i, sq in enumerate(search_queries):
            tasks.append(Task(
                task_id=f"search_{i}",
                task_type="search",
                params={"query": sq, "query_index": i}
            ))

        # 2. 初始化阅读和分析任务（等搜索结果）
        tasks.append(Task(
            task_id="read_initial",
            task_type="read",
            params={"priority": "high", "batch_size": 5}
        ))

        tasks.append(Task(
            task_id="analyse",
            task_type="analyse",
            params={"incremental": True}
        ))

        # 3. Critique和写作任务
        tasks.append(Task(
            task_id="critique",
            task_type="critique",
            params={}
        ))

        return tasks

    def _generate_search_queries(self, query: str) -> List[str]:
        """生成多角度搜索词"""
        # 简化版本，实际应该用LLM生成
        return [
            query,
            f"{query} methodology",
            f"{query} survey review",
            f"{query} recent advances 2024 2025"
        ]

    def get_next_tasks(self, state: PlannerState, count: int = 3) -> List[Task]:
        """
        动态获取下一批任务

        根据当前状态返回可执行的任务：
        - 优先返回等待中的搜索任务
        - 返回可并行的阅读任务
        - 返回可增量的分析任务
        """
        pending = [t for t in self._tasks.values()
                   if t.status == TaskStatus.PENDING]

        # 优先搜索任务
        search_tasks = [t for t in pending if t.task_type == "search"]
        if search_tasks:
            return search_tasks[:count]

        # 然后是阅读任务（如果有论文待读）
        if state.get("pending_papers"):
            read_tasks = [t for t in pending if t.task_type == "read"]
            if read_tasks:
                return [read_tasks[0]]

        # 分析任务（增量）
        if state.get("read_papers") and not state.get("analyses"):
            analyse_tasks = [t for t in pending if t.task_type == "analyse"]
            if analyse_tasks:
                return [analyse_tasks[0]]

        return pending[:count]

    def update_task_status(self, task_id: str, status: TaskStatus,
                          result: Any = None, error: str = None):
        """更新任务状态"""
        if task_id in self._tasks:
            self._tasks[task_id].status = status
            if result is not None:
                self._tasks[task_id].result = result
            if error:
                self._tasks[task_id].error = error

    def should_retry(self, task: Task) -> bool:
        """判断任务是否应该重试"""
        if task.status == TaskStatus.FAILED:
            return task.retry_count < task.max_retries
        return False

    def save_checkpoint(self, name: str, state: Dict):
        """保存检查点"""
        self._checkpoints[name] = deepcopy(state)

    def restore_checkpoint(self, name: str) -> Optional[Dict]:
        """恢复检查点"""
        return self._checkpoints.get(name)


# ========== LangGraph节点 ==========

_planner: Optional[ResearchPlanner] = None


def get_planner() -> ResearchPlanner:
    global _planner
    if _planner is None:
        _planner = ResearchPlanner()
    return _planner


async def planner_node(state: PlannerState) -> PlannerState:
    """
    Planner节点 - 负责任务分解和调度

    这是整个流程的中枢，不是固定流向，而是根据状态决定下一步
    """
    planner = get_planner()

    # 如果是初始状态，进行规划
    if state.get("phase") == Phase.PLANNING.value or not state.get("tasks"):
        query = state.get("query", "")
        tasks = planner.plan(query)

        state["tasks"] = [t.__dict__ for t in tasks]
        state["phase"] = Phase.SEARCHING.value
        state["status"] = "planning_completed"

        logger.info(f"Planner: created {len(tasks)} tasks for query '{query}'")

    return state


async def search_dispatcher_node(state: PlannerState) -> PlannerState:
    """
    搜索分发器 - 调度搜索任务

    特点：可以并行执行多个搜索任务
    """
    planner = get_planner()

    # 获取待执行的搜索任务
    pending_tasks = [t for t in state.get("tasks", [])
                     if t.get("task_type") == "search"
                     and t.get("status") == TaskStatus.PENDING.value]

    if not pending_tasks:
        # 所有搜索任务已完成，转到阅读
        state["phase"] = Phase.READING.value
        return state

    # 更新任务状态为running
    for task in pending_tasks[:planner.max_concurrent]:
        task["status"] = TaskStatus.RUNNING.value

    state["status"] = f"searching {len(pending_tasks)} tasks"

    # 注意：实际搜索由子Agent执行，这里只做调度
    return state


async def search_executor_node(state: PlannerState) -> PlannerState:
    """
    搜索执行器 - 执行单个搜索任务

    使用多路径冗余搜索，允许部分失败
    """
    from src.workflows.multi_path_search import redundant_search_node, RedundantSearcher

    query = state.get("query", "")
    if not query:
        state["errors"] = state.get("errors", [])
        state["errors"].append({"node": "search", "error": "Empty query"})
        return state

    try:
        # 多路径冗余搜索
        searcher = RedundantSearcher()
        papers = await searcher.parallel_search(query)

        # 合并到已有论文列表
        existing_titles = {p.get("title") for p in state.get("papers", [])}
        new_papers = [p for p in papers if p.get("title") not in existing_titles]

        state["papers"] = state.get("papers", []) + new_papers

        # 更新待阅读论文
        state["pending_papers"] = state.get("pending_papers", []) + new_papers

        logger.info(f"Search completed: {len(new_papers)} new papers, total: {len(state['papers'])}")

    except Exception as e:
        logger.error(f"Search failed: {e}")
        state["errors"] = state.get("errors", [])
        state["errors"].append({"node": "search", "error": str(e)})

        # 降级：使用空结果继续
        state["papers"] = state.get("papers", [])
        state["pending_papers"] = state.get("pending_papers", [])

    # 标记任务完成
    state["phase"] = Phase.READING.value
    return state


async def read_dispatcher_node(state: PlannerState) -> PlannerState:
    """
    阅读分发器 - 决定何时开始阅读

    特点：不需要等所有搜索完成，只要有论文就开始阅读
    """
    pending = state.get("pending_papers", [])
    read = state.get("read_papers", [])

    if not pending:
        # 没有待读论文，检查是否需要补充搜索
        if state.get("phase") == Phase.READING.value:
            state["phase"] = Phase.ANALYZING.value
        return state

    # 边搜边读：pending论文达到一定数量就开始读
    # 不需要等所有搜索完成
    if len(pending) >= 3 or (not pending and read):
        state["phase"] = Phase.READING.value
        state["status"] = f"reading: {len(pending)} pending, {len(read)} completed"

    return state


async def read_executor_node(state: PlannerState) -> PlannerState:
    """
    阅读执行器 - 执行论文阅读（增量）

    特点：
    1. 每次只读几篇，不用全部读完
    2. 单篇失败不影响其他
    3. 读完后立即可以进行分析
    """
    from src.workflows.subgraph_isolation import ReadingSubgraph

    pending = state.get("pending_papers", [])
    if not pending:
        state["phase"] = Phase.ANALYZING.value
        return state

    # 每次读3篇（增量）
    batch_size = 3
    batch = pending[:batch_size]

    try:
        reading_subgraph = ReadingSubgraph(max_failures=2)

        # 并行阅读
        result = await reading_subgraph.execute(batch)

        # 更新状态
        read_papers = state.get("read_papers", [])
        read_papers.extend(batch)
        state["read_papers"] = read_papers

        # 剩余待读
        state["pending_papers"] = pending[batch_size:]

        # 保存分析结果
        analyses = state.get("analyses", [])
        analyses.extend(result.outputs)
        state["analyses"] = analyses

        logger.info(f"Read completed: {len(batch)} papers, "
                   f"total read: {len(read_papers)}, "
                   f"pending: {len(state['pending_papers'])}")

        # 如果还有待读，继续读
        if state.get("pending_papers"):
            state["phase"] = Phase.READING.value
        else:
            # 读完，进入分析
            state["phase"] = Phase.ANALYZING.value

    except Exception as e:
        logger.error(f"Read failed: {e}")
        state["errors"] = state.get("errors", [])
        state["errors"].append({"node": "read", "error": str(e)})
        state["phase"] = Phase.ANALYZING.value

    return state


async def analyse_incremental_node(state: PlannerState) -> PlannerState:
    """
    增量分析节点 - 有多少分析多少

    特点：不用等所有论文读完，只要有分析结果就开始
    """
    analyses = state.get("analyses", [])

    if not analyses:
        state["phase"] = Phase.CRITIQUING.value
        return state

    try:
        from src.agents.analysis.analysis_agent import analyse_node

        # 调用分析Agent（简化版本）
        result = await analyse_node(state)

        state["themes"] = result.get("themes", [])
        state["contradictions"] = result.get("contradictions", [])
        state["research_gaps"] = result.get("research_gaps", [])

        logger.info(f"Analysis completed: {len(state.get('themes', []))} themes")

        # 增量分析完成后，进入Critique
        state["phase"] = Phase.CRITIQUING.value

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        state["errors"] = state.get("errors", [])
        state["errors"].append({"node": "analyse", "error": str(e)})

        # 降级：使用已有分析结果继续
        state["themes"] = state.get("themes", [{"name": "分析中", "description": "部分分析"}])
        state["phase"] = Phase.CRITIQUING.value

    return state


async def critique_node(state: PlannerState) -> PlannerState:
    """
    Critique节点 - 多视角审查

    特点：
    1. 可以多次迭代
    2. 不通过可以触发补充搜索
    3. 强制通过机制避免死循环
    """
    from src.agents.critique.critique_agent import critique_agent

    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 3)

    if iteration >= max_iterations:
        # 达到最大迭代，强制通过
        state["critique_passed"] = True
        state["phase"] = Phase.WRITING.value
        logger.warning("Max critique iterations reached, forcing to proceed")
        return state

    try:
        # 多视角Critique
        result = await critique_agent.analyse(state)

        state["critique_score"] = result.get("score", 0)
        state["critique_details"] = result

        # 判断是否通过
        passed = result.get("passed", False)
        state["critique_passed"] = passed

        if passed:
            logger.info(f"Critique passed with score {result.get('score', 0)}")
            state["phase"] = Phase.WRITING.value
        else:
            # 不通过，需要补充
            logger.info("Critique not passed, need supplement")
            state["phase"] = Phase.SUPPLEMENT.value

    except Exception as e:
        logger.error(f"Critique failed: {e}")
        state["errors"] = state.get("errors", [])
        state["errors"].append({"node": "critique", "error": str(e)})

        # 降级：强制通过
        state["critique_passed"] = True
        state["phase"] = Phase.WRITING.value

    return state


async def supplement_node(state: PlannerState) -> PlannerState:
    """
    补充阶段 - 根据Critique反馈补充搜索或阅读

    特点：
    1. 根据Critique的missing_topics生成补充查询
    2. 可以触发新的搜索或阅读任务
    """
    critique_details = state.get("critique_details", {})
    missing = critique_details.get("missing_topics", [])

    if not missing:
        state["phase"] = Phase.WRITING.value
        return state

    iteration = state.get("iteration", 0) + 1
    state["iteration"] = iteration

    # 生成补充查询
    additional_queries = critique_details.get("suggested_queries", [])

    if additional_queries:
        # 添加新的搜索任务
        tasks = state.get("tasks", [])
        for i, q in enumerate(additional_queries[:3]):  # 最多3个补充查询
            tasks.append({
                "task_id": f"search_supplement_{iteration}_{i}",
                "task_type": "search",
                "params": {"query": q},
                "status": TaskStatus.PENDING.value
            })
        state["tasks"] = tasks

    # 增加迭代次数
    state["phase"] = Phase.SEARCHING.value
    logger.info(f"Supplement: added {len(additional_queries)} search queries, iteration {iteration}")

    return state


async def write_node(state: PlannerState) -> PlannerState:
    """
    写作节点 - 增量写作

    特点：
    1. 可以边写边补充
    2. 有大纲后就开始写
    3. 章节可并行
    """
    if not state.get("outline"):
        # 生成大纲
        state["outline"] = [
            {"title": "摘要", "outline": "研究概述"},
            {"title": "引言", "outline": "研究背景"},
            {"title": "方法", "outline": "研究方法"},
            {"title": "结果", "outline": "研究发现"},
            {"title": "讨论", "outline": "讨论与局限性"},
            {"title": "结论", "outline": "研究结论"}
        ]
        state["current_section"] = 0
        state["writted_sections"] = []

    sections = state.get("outline", [])
    current = state.get("current_section", 0)

    if current >= len(sections):
        # 所有章节写完，生成报告
        state["phase"] = Phase.DONE.value
        state["report"] = "\n\n".join([
            s.get("content", "") for s in state.get("writted_sections", [])
        ])
        return state

    try:
        from src.agents.writing.writer import section_writing_node

        section = sections[current]
        writing_state = {
            "section_index": current,
            "section_title": section.get("title", ""),
            "global_analysis": str(state.get("themes", [])),
            "writted_sections": state.get("writted_sections", [])
        }

        result = await section_writing_node(writing_state)

        # 更新已写章节
        sections_written = state.get("writted_sections", [])
        sections_written.extend(result.get("writted_sections", []))
        state["writted_sections"] = sections_written

        # 下一节
        state["current_section"] = current + 1

        logger.info(f"Writing: completed section {current + 1}/{len(sections)}")

        # 如果还有章节没写完，继续写
        if state.get("current_section", 0) < len(sections):
            state["phase"] = Phase.WRITING.value
        else:
            state["phase"] = Phase.DONE.value

    except Exception as e:
        logger.error(f"Writing section {current} failed: {e}")
        state["errors"] = state.get("errors", [])
        state["errors"].append({"node": "writing", "section": current, "error": str(e)})

        # 跳过失败章节继续
        state["current_section"] = current + 1
        state["phase"] = Phase.WRITING.value

    return state


async def done_node(state: PlannerState) -> PlannerState:
    """完成节点"""
    # 合并所有章节为最终报告
    sections = state.get("writted_sections", [])

    report_parts = []
    for section in sections:
        if isinstance(section, dict):
            title = section.get("title", "")
            content = section.get("content", "")
            report_parts.append(f"## {title}\n\n{content}")
        else:
            report_parts.append(str(section))

    state["report"] = "\n\n".join(report_parts)
    state["status"] = "completed"

    logger.info(f"Research completed! Report length: {len(state['report'])} chars")

    return state


# ========== 动态路由条件 ==========

def should_dispatch_search(state: PlannerState) -> str:
    """判断是否继续搜索"""
    if state.get("phase") == Phase.PLANNING.value:
        return "planner"

    pending_search = [t for t in state.get("tasks", [])
                      if t.get("task_type") == "search"
                      and t.get("status") == TaskStatus.PENDING.value]

    if pending_search:
        return "search_dispatcher"

    return "read_dispatcher"


def should_read(state: PlannerState) -> str:
    """判断是否继续阅读"""
    if state.get("phase") == Phase.READING.value:
        return "read_executor"

    if state.get("analyses"):
        return "analyse_incremental"

    return "critique"


def should_critique(state: PlannerState) -> str:
    """判断Critique结果"""
    if state.get("critique_passed"):
        return "write"

    return "supplement"


def should_write(state: PlannerState) -> str:
    """判断写作是否继续"""
    if state.get("phase") == Phase.DONE.value:
        return "done"

    return "write"


# ========== 构建图 ==========

def build_planner_graph():
    """构建Planner-Orchestrated研究图"""

    builder = StateGraph(PlannerState)

    # 节点
    builder.add_node("planner", planner_node)
    builder.add_node("search_dispatcher", search_dispatcher_node)
    builder.add_node("search_executor", search_executor_node)
    builder.add_node("read_dispatcher", read_dispatcher_node)
    builder.add_node("read_executor", read_executor_node)
    builder.add_node("analyse_incremental", analyse_incremental_node)
    builder.add_node("critique", critique_node)
    builder.add_node("supplement", supplement_node)
    builder.add_node("write", write_node)
    builder.add_node("done", done_node)

    # 入口
    builder.set_entry_point("planner")

    # Planner → 根据状态分发任务
    builder.add_conditional_edges(
        "planner",
        should_dispatch_search,
        {
            "planner": "planner",
            "search_dispatcher": "search_dispatcher",
            "read_dispatcher": "read_dispatcher"
        }
    )

    # 搜索流程
    builder.add_edge("search_dispatcher", "search_executor")
    builder.add_edge("search_executor", "read_dispatcher")

    # 阅读流程
    builder.add_conditional_edges(
        "read_dispatcher",
        should_read,
        {
            "read_executor": "read_executor",
            "analyse_incremental": "analyse_incremental"
        }
    )
    builder.add_edge("read_executor", "read_dispatcher")

    # 分析 → Critique
    builder.add_edge("analyse_incremental", "critique")

    # Critique → 补充或写作
    builder.add_conditional_edges(
        "critique",
        should_critique,
        {
            "supplement": "supplement",
            "write": "write"
        }
    )

    # 补充 → 回到搜索
    builder.add_edge("supplement", "search_dispatcher")

    # 写作 → 完成或继续
    builder.add_conditional_edges(
        "write",
        should_write,
        {
            "write": "write",
            "done": "done"
        }
    )

    # 完成
    builder.add_edge("done", END)

    return builder.compile()


# ========== 全局实例 ==========

_planner_graph = None


def get_planner_graph():
    global _planner_graph
    if _planner_graph is None:
        _planner_graph = build_planner_graph()
    return _planner_graph


async def run_research_planner(query: str, session_id: str = "default") -> Dict[str, Any]:
    """运行Planner-Orchestrated研究流程"""

    graph = get_planner_graph()

    initial_state = PlannerState(
        query=query,
        session_id=session_id,
        phase=Phase.PLANNING.value,
        tasks=[],
        completed_tasks=[],
        papers=[],
        pending_papers=[],
        read_papers=[],
        analyses=[],
        critique_score=0,
        critique_passed=False,
        critique_details={},
        iteration=0,
        max_iterations=3,
        outline=[],
        writted_sections=[],
        current_section=0,
        errors=[],
        checkpoints={},
        rollback_count=0,
        report="",
        status="init"
    )

    result = await graph.ainvoke(initial_state)
    return result


if __name__ == "__main__":
    import asyncio

    result = asyncio.run(run_research_planner("大语言模型在自动驾驶中的应用"))
    print(f"Final status: {result.get('status')}")
    print(f"Report length: {len(result.get('report', ''))} chars")
    print(f"Errors: {len(result.get('errors', []))}")
    print(f"Iterations: {result.get('iteration', 0)}")
