"""子图隔离 - Subgraph Isolation

将复杂流程封装为独立子图，每个子图：
1. 有自己的内部状态管理
2. 失败不影响外部状态
3. 支持部分成功（即使部分论文阅读失败也继续）
4. 可以独立重试

主要用途：
- 阅读子图：多篇论文并行/串行阅读，单篇失败不影响整体
- 搜索子图：多引擎搜索，结果合并
- 写作子图：多章节并行写作
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, TypeVar
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SubgraphStatus(str, Enum):
    """子图执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SubgraphResult:
    """子图执行结果"""
    status: SubgraphStatus
    outputs: List[Any] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    skipped: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_count(self) -> int:
        return len(self.outputs)

    @property
    def failure_count(self) -> int:
        return len(self.errors)

    @property
    def is_success(self) -> bool:
        return self.status in (SubgraphStatus.COMPLETED, SubgraphStatus.PARTIAL_FAILED)

    @property
    def success_ratio(self) -> float:
        total = self.success_count + self.failure_count + len(self.skipped)
        if total == 0:
            return 0.0
        return self.success_count / total


class IsolatedSubgraph:
    """
    隔离子图基类

    提供：
    1. 内部状态隔离
    2. 错误捕获和隔离
    3. 部分成功容忍
    4. 结果汇总
    """

    def __init__(self, name: str, max_failures: int = 3):
        self.name = name
        self.max_failures = max_failures
        self._internal_state: Dict[str, Any] = {}
        self._results: List[Any] = []
        self._errors: List[Dict[str, Any]] = []
        self._skipped: List[Any] = []

    async def execute(self, inputs: List[Any]) -> SubgraphResult:
        """执行子图，返回汇总结果"""
        raise NotImplementedError

    async def _execute_item(
        self,
        item: Any,
        handler: Callable
    ) -> Optional[Any]:
        """执行单个项目，捕获错误"""
        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(item)
            else:
                return handler(item)
        except Exception as e:
            logger.warning(f"[{self.name}] Item failed: {e}")
            self._errors.append({
                "item": str(item)[:100],
                "error": str(e),
                "type": type(e).__name__
            })
            return None

    def _create_result(self, status: SubgraphStatus = None) -> SubgraphResult:
        """创建结果对象"""
        if status is None:
            if len(self._errors) == 0:
                status = SubgraphStatus.COMPLETED
            elif len(self._errors) <= self.max_failures:
                status = SubgraphStatus.PARTIAL_FAILED
            else:
                status = SubgraphStatus.FAILED

        return SubgraphResult(
            status=status,
            outputs=self._results,
            errors=self._errors,
            skipped=self._skipped,
            metadata={
                "name": self.name,
                "total_inputs": len(self._results) + len(self._errors) + len(self._skipped)
            }
        )

    def reset(self):
        """重置内部状态"""
        self._internal_state = {}
        self._results = []
        self._errors = []
        self._skipped = []


class ReadingSubgraph(IsolatedSubgraph):
    """
    阅读子图 - 隔离论文阅读过程

    特点：
    1. 单篇论文阅读失败不影响其他论文
    2. 记录每篇论文的阅读状态
    3. 支持跳过失败项继续处理
    4. 返回所有论文的分析结果
    """

    def __init__(self, name: str = "reading_subgraph", max_failures: int = 5):
        super().__init__(name, max_failures)
        self.paper_results: Dict[str, Any] = {}

    async def execute(self, papers: List[Dict[str, Any]]) -> SubgraphResult:
        """
        执行隔离阅读

        Args:
            papers: 论文列表，每篇包含 title, abstract 等

        Returns:
            SubgraphResult with all paper analyses
        """
        self.reset()

        if not papers:
            self._skipped.append("no_papers")
            return self._create_result(SubgraphStatus.SKIPPED)

        logger.info(f"[ReadingSubgraph] Starting {len(papers)} papers")

        # 创建阅读任务
        tasks = []
        for i, paper in enumerate(papers):
            task = self._read_paper(paper, i)
            tasks.append(task)

        # 并行执行（可以改为串行如果需要控制并发）
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self._errors.append({
                    "index": i,
                    "paper": papers[i].get("title", "unknown")[:50],
                    "error": str(result)
                })
            elif result is not None:
                self._results.append(result)

        # 确定最终状态
        status = SubgraphStatus.COMPLETED
        if len(self._errors) > self.max_failures:
            status = SubgraphStatus.FAILED
        elif len(self._errors) > 0:
            status = SubgraphStatus.PARTIAL_FAILED

        return self._create_result(status)

    async def _read_paper(self, paper: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """阅读单篇论文"""
        title = paper.get("title", f"paper_{index}")

        try:
            # 这里调用实际的阅读逻辑
            # 简化版本，实际应该调用 isolated_reader
            from src.agents.reading.isolated_reader import IsolatedPaperReader

            reader = IsolatedPaperReader()
            result = await reader.read_paper(paper)

            self.paper_results[title] = result

            return {
                "title": title,
                "analysis": result,
                "success": True
            }

        except Exception as e:
            logger.warning(f"Failed to read paper {index}: {title[:30]} - {e}")
            self._errors.append({
                "index": index,
                "title": title[:50],
                "error": str(e)
            })
            return None

    async def execute_sequential(
        self,
        papers: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> SubgraphResult:
        """
        顺序阅读（限制并发）

        当需要控制API调用频率时使用
        """
        self.reset()

        if not papers:
            return self._create_result(SubgraphStatus.SKIPPED)

        total = len(papers)
        logger.info(f"[ReadingSubgraph] Sequential reading {total} papers, max_concurrent={max_concurrent}")

        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)

        async def read_with_semaphore(paper, index):
            async with semaphore:
                return await self._read_paper(paper, index)

        tasks = [read_with_semaphore(paper, i) for i, paper in enumerate(papers)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self._errors.append({"index": i, "error": str(result)})
            elif result is not None:
                self._results.append(result)

        return self._create_result()


class WritingSubgraph(IsolatedSubgraph):
    """
    写作子图 - 隔离章节写作过程

    特点：
    1. 单章节失败不影响其他章节
    2. 记录每章节写作状态
    3. 支持按优先级顺序写作
    4. 允许跳过非关键章节
    """

    def __init__(self, name: str = "writing_subgraph", max_failures: int = 2):
        super().__init__(name, max_failures)
        self.section_results: Dict[int, Any] = {}

    async def execute(
        self,
        sections: List[Dict[str, Any]],
        skip_on_failure: bool = True
    ) -> SubgraphResult:
        """
        执行隔离写作

        Args:
            sections: 章节列表，每节包含 index, title, content 等
            skip_on_failure: 单节失败是否跳过继续

        Returns:
            SubgraphResult with all written sections
        """
        self.reset()

        if not sections:
            self._skipped.append("no_sections")
            return self._create_result(SubgraphStatus.SKIPPED)

        logger.info(f"[WritingSubgraph] Starting {len(sections)} sections")

        for i, section in enumerate(sections):
            section_title = section.get("title", f"section_{i}")

            try:
                result = await self._write_section(section, i)

                if result:
                    self._results.append(result)
                    self.section_results[i] = result
                else:
                    # 写作返回None可能是因为质量问题
                    self._skipped.append(section_title)

            except Exception as e:
                logger.error(f"Section {i} failed: {e}")
                self._errors.append({
                    "index": i,
                    "title": section_title,
                    "error": str(e)
                })

                if skip_on_failure:
                    continue
                else:
                    # 遇到致命错误，停止
                    break

        # 计算状态
        status = SubgraphStatus.COMPLETED
        if len(self._errors) > self.max_failures:
            status = SubgraphStatus.FAILED
        elif len(self._errors) > 0 or len(self._skipped) > 0:
            status = SubgraphStatus.PARTIAL_FAILED

        return self._create_result(status)

    async def _write_section(self, section: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """写单个章节"""
        title = section.get("title", f"Section {index}")

        try:
            # 调用实际的章节写作逻辑
            from src.agents.writing.writer import section_writing_node

            writing_state = {
                "section_index": index,
                "section_title": title,
                "section_content": section.get("outline", ""),
                "context": section.get("context", {}),
                "writted_sections": [s.get("content") for s in self._results if s]
            }

            result = await section_writing_node(writing_state)

            if result and result.get("content"):
                return {
                    "index": index,
                    "title": title,
                    "content": result.get("content"),
                    "success": True
                }

            return None

        except Exception as e:
            raise Exception(f"Writing section {index} ({title[:20]}): {e}")

    async def execute_parallel(
        self,
        sections: List[Dict[str, Any]],
        max_concurrent: int = 2
    ) -> SubgraphResult:
        """
        并行写作（限制并发）

        适用于章节之间依赖不强的情况
        """
        self.reset()

        if not sections:
            return self._create_result(SubgraphStatus.SKIPPED)

        semaphore = asyncio.Semaphore(max_concurrent)

        async def write_with_semaphore(section, index):
            async with semaphore:
                return await self._write_section(section, index)

        tasks = [write_with_semaphore(section, i) for i, section in enumerate(sections)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self._errors.append({"index": i, "error": str(result)})
            elif result is not None:
                self._results.append(result)

        return self._create_result()


class SearchSubgraph(IsolatedSubgraph):
    """
    搜索子图 - 隔离多引擎搜索过程

    特点：
    1. 多引擎并行搜索
    2. 单引擎失败不影响整体
    3. 结果自动去重合并
    4. 支持引擎优先级
    """

    def __init__(self, name: str = "search_subgraph", max_failures: int = 2):
        super().__init__(name, max_failures)
        self.engine_results: Dict[str, List[Dict]] = {}

    async def execute(
        self,
        query: str,
        engines: List[str] = None,
        timeout: float = 30.0
    ) -> SubgraphResult:
        """
        执行隔离搜索

        Args:
            query: 搜索查询
            engines: 引擎列表，默认 ["mcp", "local"]
            timeout: 单引擎超时时间

        Returns:
            SubgraphResult with merged papers from all engines
        """
        self.reset()

        if not query:
            return self._create_result(SubgraphStatus.SKIPPED)

        engines = engines or ["mcp", "local"]

        logger.info(f"[SearchSubgraph] Searching with {len(engines)} engines")

        # 并行执行所有引擎搜索
        tasks = []
        for engine in engines:
            task = self._search_with_engine(engine, query, timeout)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        all_papers = []
        for i, result in enumerate(results):
            engine_name = engines[i] if i < len(engines) else f"engine_{i}"

            if isinstance(result, Exception):
                self._errors.append({
                    "engine": engine_name,
                    "error": str(result)
                })
            elif result and isinstance(result, list):
                self.engine_results[engine_name] = result
                all_papers.extend(result)
                self._results.append({"engine": engine_name, "count": len(result)})

        # 去重
        unique_papers = self._deduplicate_papers(all_papers)

        # 更新结果
        self._results = [{"papers": unique_papers, "total": len(unique_papers)}]

        status = SubgraphStatus.COMPLETED
        if len(self._errors) >= len(engines):
            status = SubgraphStatus.FAILED
        elif len(self._errors) > 0:
            status = SubgraphStatus.PARTIAL_FAILED

        return self._create_result(status)

    async def _search_with_engine(
        self,
        engine: str,
        query: str,
        timeout: float
    ) -> Optional[List[Dict[str, Any]]]:
        """使用指定引擎搜索"""
        try:
            if engine == "mcp":
                return await self._search_mcp(query, timeout)
            elif engine == "local":
                return await self._search_local(query, timeout)
            else:
                logger.warning(f"Unknown engine: {engine}")
                return []
        except Exception as e:
            logger.error(f"Engine {engine} failed: {e}")
            raise

    async def _search_mcp(self, query: str, timeout: float) -> List[Dict[str, Any]]:
        """MCP引擎搜索"""
        from src.workflows.multi_path_search import redundant_search_node

        state = {"query": query}
        result = await asyncio.wait_for(
            redundant_search_node(state),
            timeout=timeout
        )

        return result.get("papers", [])

    async def _search_local(self, query: str, timeout: float) -> List[Dict[str, Any]]:
        """本地数据库搜索（模拟）"""
        # 实际应该调用本地数据库搜索
        await asyncio.sleep(0.1)  # 模拟
        return []

    def _deduplicate_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重论文"""
        seen = set()
        unique = []

        for paper in papers:
            title = paper.get("title", "")
            if title and title not in seen:
                seen.add(title)
                unique.append(paper)

        return unique


# ========== LangGraph 子图节点工厂 ==========

def create_subgraph_node(
    subgraph: IsolatedSubgraph,
    input_key: str,
    output_key: str
):
    """
    创建子图节点工厂

    使用示例:
        reading_subgraph = ReadingSubgraph()
        reading_node = create_subgraph_node(
            reading_subgraph,
            input_key="papers",
            output_key="paper_analyses"
        )
    """
    async def subgraph_node(state: Dict[str, Any]) -> Dict[str, Any]:
        inputs = state.get(input_key, [])

        if not inputs:
            logger.warning(f"[{subgraph.name}] No inputs for key '{input_key}'")
            state[f"{output_key}_status"] = SubgraphStatus.SKIPPED
            return state

        result = await subgraph.execute(inputs)

        # 更新状态
        state[f"{output_key}_status"] = result.status
        state[f"{output_key}_result"] = result.outputs
        state[f"{output_key}_errors"] = result.errors
        state[f"{output_key}_success_ratio"] = result.success_ratio

        # 关键结果直接放到state顶层
        if result.outputs:
            state[output_key] = result.outputs

        return state

    return subgraph_node


def create_fault_tolerant_node(
    node_fn: Callable,
    fallback_fn: Optional[Callable] = None,
    checkpoint_name: str = None,
    snapshot_manager = None
):
    """
    创建容错节点

    使用示例:
        safe_search_node = create_fault_tolerant_node(
            search_node,
            fallback_fn=fallback_search,
            checkpoint_name="before_search"
        )
    """
    async def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
        # 保存检查点
        if checkpoint_name and snapshot_manager:
            snapshot_manager.save(checkpoint_name, state, node_name=node_fn.__name__)

        try:
            result = await node_fn(state)
            return result
        except Exception as e:
            logger.error(f"Node {node_fn.__name__} failed: {e}")

            # 记录错误
            if "_errors" not in state:
                state["_errors"] = []
            state["_errors"].append({
                "node": node_fn.__name__,
                "error": str(e)
            })

            # 尝试fallback
            if fallback_fn:
                try:
                    if asyncio.iscoroutinefunction(fallback_fn):
                        return await fallback_fn(state, e)
                    else:
                        return fallback_fn(state, e)
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")

            # Fallback也失败，返回降级状态
            state[f"{node_fn.__name__}_failed"] = True
            state[f"{node_fn.__name__}_error"] = str(e)
            return state

    return wrapper