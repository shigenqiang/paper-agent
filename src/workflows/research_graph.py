"""
容错研究Agent状态机 - 基于LangGraph

整合了：
1. 错误边界 + Fallback 机制
2. 多路径冗余搜索
3. 状态快照 + 回滚机制
4. 隔离子图隔离（阅读、写作）
5. 质量门控

架构（容错版）：
checkpoint → search(多引擎) → rank → reading(隔离)
    → analysis → critique → (迭代|写) → writing(隔离) → report

特点：
- 任一节点失败不会导致整体崩溃
- 支持部分成功继续推进
- 关键节点前保存快照，失败可回滚
"""
from typing import TypedDict, List, Dict, Any, Optional, Literal
from langgraph.graph import StateGraph, END, START
from langgraph.types import Command
import logging
import asyncio

logger = logging.getLogger(__name__)


class ResearchState(TypedDict):
    """研究流程的完整状态（支持容错）"""

    # ===== 输入 =====
    query: str
    session_id: str

    # ===== 规划阶段 =====
    query_analysis: Dict[str, Any]
    search_queries: List[str]
    similar_research: List[Dict]

    # ===== 迭代控制 =====
    iteration: int
    max_iterations: int
    critique_result: Dict[str, Any]
    additional_queries: List[str]
    critique_passed: bool

    # ===== 搜索结果 =====
    papers: List[Dict]
    papers_after_rank: List[Dict]
    search_engines_used: List[str]
    search_errors: List[Dict]

    # ===== 阅读结果 =====
    paper_analyses: List[Dict]
    failed_papers: int
    reading_status: str  # SubgraphStatus

    # ===== 分析结果 =====
    themes: List[Dict]
    contradictions: List[str]
    research_gaps: List[str]
    timeline: List[Dict]
    citation_graph: Dict

    # ===== 写作阶段 =====
    outline: str
    sections: List[str]
    current_section_index: int
    writted_sections: List[Dict]
    writing_status: str  # SubgraphStatus
    report: str

    # ===== 容错控制 =====
    _errors: List[Dict]  # 所有错误记录
    _checkpoint: Optional[Dict]  # 快照状态
    _checkpoint_name: Optional[str]
    _needs_rollback: bool
    _rollback_checkpoint: Optional[str]
    _rollback_count: int
    _rollback_reason: Optional[str]

    # ===== 系统状态 =====
    status: str
    errors: List[str]


# ========== 导入模块 ==========

def _import_nodes():
    """延迟导入节点（避免循环依赖）"""
    from src.agents.search.search_agent import search_node
    from src.agents.search.rcs_ranker import rcs_rank_node
    from src.agents.reading.isolated_reader import reading_pipeline
    from src.agents.analysis.analysis_agent import analyse_node
    from src.agents.critique.critique_agent import critique_agent
    from src.agents.critique.critique_node import critique_node, should_iterate
    from src.agents.critique.additional_search_node import additional_search_node
    from src.agents.writing.writing_agent import WritingWorkflow, condition_edge
    from src.agents.writing.writing_agent import writing_node
    from src.agents.memory.memory_nodes import (
        memory_retrieve_node,
        memory_store_node,
        session_start_node,
        session_end_node
    )
    return {
        "search_node": search_node,
        "rcs_rank_node": rcs_rank_node,
        "reading_pipeline": reading_pipeline,
        "analyse_node": analyse_node,
        "critique_node": critique_node,
        "additional_search_node": additional_search_node,
        "writing_outline_node": writing_outline_node,
        "writing_section_node": writing_section_node,
        "report_node": report_node,
        "memory_retrieve_node": memory_retrieve_node,
        "memory_store_node": memory_store_node,
        "session_start_node": session_start_node,
        "session_end_node": session_end_node,
    }


# ========== 容错节点实现 ==========

async def safe_search_node(state: ResearchState) -> ResearchState:
    """
    容错搜索节点 - 多引擎并行 + fallback
    """
    from src.workflows.multi_path_search import redundant_search_node

    query = state.get("query", "")
    if not query:
        state["status"] = "error"
        state["errors"].append("Empty query")
        return state

    try:
        # 多路径冗余搜索
        search_state = {"query": query}
        result = await redundant_search_node(search_state)

        papers = result.get("papers", [])
        state["papers"] = papers
        state["search_engines_used"] = result.get("engines_used", ["mcp"])
        state["search_errors"] = result.get("errors", [])

        if not papers:
            logger.warning("Search returned no results, will try fallback")
            state["_needs_fallback"] = True
        else:
            logger.info(f"Search completed: {len(papers)} papers")

    except Exception as e:
        logger.error(f"Search node failed: {e}")
        state["_errors"] = state.get("_errors", [])
        state["_errors"].append({"node": "search", "error": str(e)})
        state["papers"] = []  # 空结果但不中断

    return state


async def safe_reading_node(state: ResearchState) -> ResearchState:
    """
    容错阅读节点 - 子图隔离，单篇失败不影响整体
    """
    from src.workflows.subgraph_isolation import ReadingSubgraph

    papers = state.get("papers_after_rank", state.get("papers", []))
    if not papers:
        state["reading_status"] = "skipped"
        state["paper_analyses"] = []
        return state

    try:
        # 创建阅读子图（允许5篇失败）
        reading_subgraph = ReadingSubgraph(max_failures=5)

        # 并行阅读，但限制并发数
        result = await reading_subgraph.execute_sequential(papers, max_concurrent=3)

        # 更新状态
        state["paper_analyses"] = result.outputs
        state["failed_papers"] = result.failure_count
        state["reading_status"] = result.status.value

        if result.status.value == "failed":
            logger.error(f"Reading subgraph failed: {result.failure_count} papers failed")
            state["_errors"] = state.get("_errors", [])
            state["_errors"].append({
                "node": "reading",
                "errors": result.errors
            })
        elif result.status.value == "partial_failed":
            logger.warning(f"Reading partial failed: {result.failure_count} failed, {result.success_count} succeeded")

    except Exception as e:
        logger.error(f"Reading node failed: {e}")
        state["reading_status"] = "failed"
        state["_errors"] = state.get("_errors", [])
        state["_errors"].append({"node": "reading", "error": str(e)})

    return state


async def safe_analysis_node(state: ResearchState) -> ResearchState:
    """
    容错分析节点 - 带质量门
    """
    from src.workflows.checkpoint_rollback import QualityGate, get_pipeline_state

    paper_analyses = state.get("paper_analyses", [])
    if not paper_analyses:
        logger.warning("No paper analyses to analyze")
        state["status"] = "analysis_empty"
        return state

    try:
        # 检查质量门
        gate = QualityGate()
        gate.add_threshold("paper_count", min_val=3, required=False)

        quality_result = gate.evaluate({"paper_count": len(paper_analyses)})

        if not quality_result.passed:
            logger.warning(f"Quality gate not passed: {quality_result.violations}")
            # 但仍然继续，不强制回滚

        # 保存检查点
        ps = get_pipeline_state()
        ps.save("before_analysis", dict(state), "analysis_node")

        # 执行分析
        from src.agents.analysis.analysis_agent import analyse_node

        # 简化：直接调用analyse_node
        result = await analyse_node(state)

        state["themes"] = result.get("themes", state.get("themes", []))
        state["contradictions"] = result.get("contradictions", [])
        state["research_gaps"] = result.get("research_gaps", [])

    except Exception as e:
        logger.error(f"Analysis node failed: {e}")
        state["_errors"] = state.get("_errors", [])
        state["_errors"].append({"node": "analysis", "error": str(e)})

        # 尝试回滚
        ps = get_pipeline_state()
        restored = ps.restore("before_analysis")
        if restored:
            logger.info("Rolled back to before_analysis checkpoint")
            state.update(restored)
            state["_rollback"] = True

    return state


async def safe_writing_node(state: ResearchState) -> ResearchState:
    """
    容错写作节点 - 子图隔离，单章节失败不影响其他章节
    """
    from src.workflows.subgraph_isolation import WritingSubgraph

    sections = state.get("sections", [])
    if not sections:
        logger.warning("No sections to write")
        state["writing_status"] = "skipped"
        return state

    try:
        # 保存检查点
        from src.workflows.checkpoint_rollback import get_pipeline_state
        ps = get_pipeline_state()
        ps.save("before_writing", dict(state), "writing_node")

        # 创建写作子图
        writing_subgraph = WritingSubgraph(max_failures=2)

        sections_data = [
            {"title": s.get("title", f"Section {i}"), "outline": s.get("outline", ""), "index": i}
            for i, s in enumerate(sections)
        ]

        result = await writing_subgraph.execute_parallel(sections_data, max_concurrent=2)

        state["writted_sections"] = result.outputs
        state["writing_status"] = result.status.value

        if result.status.value == "failed":
            logger.error(f"Writing subgraph failed")
            state["_errors"] = state.get("_errors", [])
            state["_errors"].append({"node": "writing", "errors": result.errors})

            # 回滚
            restored = ps.restore("before_writing")
            if restored:
                state.update(restored)
                state["_rollback"] = True

    except Exception as e:
        logger.error(f"Writing node failed: {e}")
        state["_errors"] = state.get("_errors", [])
        state["_errors"].append({"node": "writing", "error": str(e)})

    return state


# ========== 原有节点（简化版） ==========

async def query_node_func(state: ResearchState) -> ResearchState:
    """查询理解节点"""
    query = state.get("query", "")
    logger.info(f"Query node: {query}")

    if not query:
        state["status"] = "error"
        state["errors"].append("Empty query")
        return state

    search_queries = [query]
    state["search_queries"] = search_queries
    state["iteration"] = 0
    state["max_iterations"] = 3
    state["status"] = "planning"
    state["_errors"] = []
    state["_rollback_count"] = 0

    return state


async def rank_node(state: ResearchState) -> ResearchState:
    """RCS重排序节点"""
    from src.agents.search.rcs_ranker import rcs_rank_node

    papers = state.get("papers", [])
    if not papers:
        logger.warning("No papers to rank")
        return state

    query = state.get("query", "")
    if not query:
        return state

    try:
        rank_state = {"query": query, "papers": papers}
        result = await rcs_rank_node(rank_state)

        state["papers_after_rank"] = result.get("papers_after_rank", result.get("papers", []))

    except Exception as e:
        logger.error(f"Ranking failed: {e}")
        state["papers_after_rank"] = papers  # 降级使用原始顺序

    return state


async def critique_with_rollback(state: ResearchState) -> ResearchState:
    """
    Critique节点 - 失败可回滚
    """
    from src.workflows.checkpoint_rollback import get_pipeline_state

    try:
        from src.agents.critique.critique_node import critique_node

        # 保存检查点
        ps = get_pipeline_state()
        ps.save("before_critique", dict(state), "critique_node")

        result = await critique_node(state)

        # 检查critique结果
        critique_passed = result.get("critique_passed", False)
        state["critique_passed"] = critique_passed

        if not critique_passed and result.get("iteration", 0) >= state.get("max_iterations", 3):
            # 达到最大迭代，强制推进
            logger.warning("Max iterations reached, forcing to proceed")
            state["critique_passed"] = True

    except Exception as e:
        logger.error(f"Critique failed: {e}")
        state["_errors"] = state.get("_errors", [])
        state["_errors"].append({"node": "critique", "error": str(e)})

        # 回滚
        ps = get_pipeline_state()
        restored = ps.restore("before_critique")
        if restored:
            state.update(restored)
            state["_rollback"] = True
            state["critique_passed"] = True  # 强制通过，避免死循环

    return state


async def writing_outline_node(state: ResearchState) -> ResearchState:
    """写作大纲节点"""
    from src.agents.writing.director import writing_director_node

    sections = state.get("sections", [])
    if sections:
        # 已有大纲，跳过
        return state

    try:
        writing_state = {
            "user_request": state.get("query", ""),
            "global_analysis": state.get("themes", []),
            "sections": [],
            "writted_sections": [],
            "current_section_index": -1,
            "retrieved_docs": []
        }

        result = await writing_director_node(writing_state)
        sections = result.get("sections", [])

        state["sections"] = sections
        state["current_section_index"] = 0
        state["writted_sections"] = []
        state["status"] = "writing"

    except Exception as e:
        logger.error(f"Writing outline failed: {e}")
        state["errors"].append(f"Outline generation failed: {e}")
        # 不中断，使用默认大纲
        state["sections"] = [
            {"title": "摘要", "outline": "研究摘要"},
            {"title": "引言", "outline": "研究背景"},
            {"title": "方法", "outline": "研究方法"},
            {"title": "结果", "outline": "研究发现"},
            {"title": "结论", "outline": "研究结论"}
        ]

    return state


async def writing_section_node(state: ResearchState) -> ResearchState:
    """写作小节节点"""
    from src.agents.writing.writer import section_writing_node

    sections = state.get("sections", [])
    current_index = state.get("current_section_index", 0)
    writted = state.get("writted_sections", [])

    if current_index >= len(sections):
        # 所有章节写完
        return state

    try:
        section = sections[current_index]
        writing_state = {
            "user_request": state.get("query", ""),
            "global_analysis": str(state.get("themes", [])),
            "sections": sections,
            "writted_sections": writted,
            "current_section_index": current_index,
            "retrieved_docs": []
        }

        result = await section_writing_node(writing_state)

        writted = result.get("writted_sections", writted)
        next_index = result.get("current_section_index", current_index + 1)

        state["writted_sections"] = writted
        state["current_section_index"] = next_index

    except Exception as e:
        logger.error(f"Writing section {current_index} failed: {e}")
        state["_errors"] = state.get("_errors", [])
        state["_errors"].append({"node": f"writing_section_{current_index}", "error": str(e)})

        # 跳过当前章节，继续下一个
        state["current_section_index"] = current_index + 1

    return state


async def report_node(state: ResearchState) -> ResearchState:
    """报告生成节点"""
    try:
        sections_content = []
        for section in state.get("writted_sections", []):
            if isinstance(section, dict):
                content = section.get("content", "")
            else:
                content = str(section)
            sections_content.append(content)

        report_content = "\n\n".join(sections_content)
        state["report"] = report_content
        state["status"] = "completed"

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        state["errors"].append(f"Report generation failed: {e}")
        state["report"] = "报告生成失败，请检查错误日志"

    return state


def should_continue_writing(state: ResearchState) -> str:
    """判断写作是否继续"""
    current_index = state.get("current_section_index", 0)
    sections = state.get("sections", [])

    if current_index >= len(sections):
        return "report_node"

    return "writing_section_node"


# ========== 构建容错图 ==========

def build_fault_tolerant_graph():
    """构建容错研究流程图"""

    builder = StateGraph(ResearchState)

    # ===== 添加节点 =====
    # 会话管理
    builder.add_node("session_start", session_start_node)

    # 查询理解
    builder.add_node("query_node", query_node_func)

    # 搜索（容错版）
    builder.add_node("search_node", safe_search_node)

    # 排序
    builder.add_node("rank_node", rank_node)

    # 阅读（容错版）
    builder.add_node("reading_node", safe_reading_node)

    # 分析（容错版）
    builder.add_node("analysis_node", safe_analysis_node)

    # Critique（容错版）
    builder.add_node("critique_node", critique_with_rollback)

    # 补充搜索
    builder.add_node("additional_search_node", additional_search_node)

    # 写作
    builder.add_node("writing_outline_node", writing_outline_node)
    builder.add_node("writing_section_node", writing_section_node)

    # 报告
    builder.add_node("report_node", report_node)

    # 会话结束
    builder.add_node("session_end", session_end_node)

    # ===== 设置入口 =====
    builder.set_entry_point("session_start")

    # ===== 构建流程 =====
    # 会话 → 查询
    builder.add_edge("session_start", "query_node")

    # 查询 → 搜索 → 排序 → 阅读 → 分析
    builder.add_edge("query_node", "search_node")
    builder.add_edge("search_node", "rank_node")
    builder.add_edge("rank_node", "reading_node")
    builder.add_edge("reading_node", "analysis_node")

    # 分析 → Critique
    builder.add_edge("analysis_node", "critique_node")

    # Critique后的条件分支
    builder.add_conditional_edges(
        "critique_node",
        should_iterate,
        {
            "additional_search": "additional_search_node",
            "writing": "writing_outline_node"
        }
    )

    # 补充搜索 → 回到排序（迭代）
    builder.add_edge("additional_search_node", "rank_node")

    # 写作流程
    builder.add_edge("writing_outline_node", "writing_section_node")

    # 写作的条件边
    builder.add_conditional_edges(
        "writing_section_node",
        should_continue_writing,
        {
            "writing_section_node": "writing_section_node",
            "report_node": "report_node"
        }
    )

    # 报告 → 会话结束
    builder.add_edge("report_node", "session_end")
    builder.add_edge("session_end", END)

    return builder.compile()


# ========== 会话节点 ==========

async def session_start_node(state: ResearchState) -> ResearchState:
    """会话开始"""
    from src.workflows.checkpoint_rollback import get_pipeline_state
    from src.agents.memory.memory_nodes import get_memory_manager

    try:
        memory = get_memory_manager()
        session_id = state.get("session_id", "default")
        memory.create_session(session_id)

        query = state.get("query", "")
        if query:
            memory.add_message(session_id=session_id, role="user", content=query)

        # 重置回滚控制器
        ps = get_pipeline_state()
        ps.reset_rollback_count()

        state["session_id"] = session_id
        logger.info(f"Session started: {session_id}")

    except Exception as e:
        logger.error(f"Session start failed: {e}")

    return state


async def session_end_node(state: ResearchState) -> ResearchState:
    """会话结束"""
    from src.agents.memory.memory_nodes import get_memory_manager

    try:
        memory = get_memory_manager()
        session_id = state.get("session_id", "default")
        memory.close_session(session_id, save=True)

        # 存储研究结果到记忆
        query = state.get("query", "")
        if query:
            memory.add_insight(
                insight=f"研究主题: {query}",
                importance=0.8,
                source="research_pipeline"
            )

        logger.info(f"Session ended: {session_id}")

    except Exception as e:
        logger.error(f"Session end failed: {e}")

    return state


# ========== 创建默认图实例 ==========

_fault_tolerant_graph = None


def get_fault_tolerant_graph():
    """获取容错研究流程图"""
    global _fault_tolerant_graph
    if _fault_tolerant_graph is None:
        _fault_tolerant_graph = build_fault_tolerant_graph()
    return _fault_tolerant_graph


async def run_research(query: str, session_id: str = "default") -> Dict[str, Any]:
    """运行容错研究流程"""

    nodes = _import_nodes()

    # 确保所有节点函数在全局作用域
    globals().update(nodes)

    graph = get_fault_tolerant_graph()

    initial_state = ResearchState(
        query=query,
        session_id=session_id,
        query_analysis={},
        search_queries=[],
        similar_research=[],
        iteration=0,
        max_iterations=3,
        critique_result={},
        additional_queries=[],
        critique_passed=False,
        papers=[],
        papers_after_rank=[],
        paper_analyses=[],
        failed_papers=0,
        reading_status="pending",
        themes=[],
        contradictions=[],
        research_gaps=[],
        timeline=[],
        citation_graph={},
        outline="",
        sections=[],
        current_section_index=0,
        writted_sections=[],
        writing_status="pending",
        report="",
        _errors=[],
        _checkpoint=None,
        _checkpoint_name=None,
        _needs_rollback=False,
        _rollback_checkpoint=None,
        _rollback_count=0,
        _rollback_reason=None,
        status="init",
        errors=[]
    )

    result = await graph.ainvoke(initial_state)
    return result


# ========== 兼容性：保留原接口 ==========

def get_research_graph():
    """获取研究流程图（兼容原接口）"""
    return get_fault_tolerant_graph()


async def run_research_old_interface(query: str, session_id: str = "default") -> Dict[str, Any]:
    """使用旧接口运行研究"""
    return await run_research(query, session_id)


if __name__ == "__main__":
    import asyncio

    result = asyncio.run(run_research("大语言模型在自动驾驶中的应用"))
    print(f"Final status: {result.get('status')}")
    print(f"Report length: {len(result.get('report', ''))} chars")
    print(f"Errors: {len(result.get('_errors', []))}")
    print(f"Rollback count: {result.get('_rollback_count', 0)}")