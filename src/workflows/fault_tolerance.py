"""容错机制 - Error Boundary、Fallback、Checkpoint"""
import logging
from typing import Dict, Any, Callable, Optional, TypeVar
from functools import wraps
from copy import deepcopy
import asyncio

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorHandler:
    """错误处理器基类"""

    def __init__(self, error_type: str, fallback_fn: Optional[Callable] = None):
        self.error_type = error_type
        self.fallback_fn = fallback_fn

    async def handle(self, state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """处理错误，返回降级后的状态"""
        logger.warning(f"[{self.error_type}] {type(error).__name__}: {error}")
        state["_errors"] = state.get("_errors", [])
        state["_errors"].append({
            "node": self.error_type,
            "error": str(error),
            "type": type(error).__name__
        })

        if self.fallback_fn:
            return await self.fallback_fn(state, error)
        return state


class FallbackErrorHandler(ErrorHandler):
    """带fallback的错误处理"""

    def __init__(self, error_type: str, fallback_fn: Callable, fallback_value: Any = None):
        super().__init__(error_type, fallback_fn)
        self.fallback_value = fallback_value

    async def handle(self, state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        state = await super().handle(state, error)

        # 尝试fallback
        try:
            if asyncio.iscoroutinefunction(self.fallback_fn):
                result = await self.fallback_fn(state, error)
                state.update(result)
            else:
                result = self.fallback_fn(state, error)
                if isinstance(result, dict):
                    state.update(result)
        except Exception as e:
            logger.error(f"Fallback also failed: {e}")
            state[f"{self.error_type}_failed"] = True
            state[f"{self.error_type}_fallback_value"] = self.fallback_value

        return state


def with_error_boundary(error_type: str, fallback_fn: Optional[Callable] = None,
                        default_value: Any = None, store_checkpoint: bool = False):
    """
    错误边界装饰器

    Args:
        error_type: 节点名称（用于日志）
        fallback_fn: 降级函数，接收 (state, error)
        default_value: 降级默认值
        store_checkpoint: 是否在该节点前存储检查点
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
            # 存储检查点
            if store_checkpoint:
                state["_checkpoint"] = deepcopy(state)
                state["_checkpoint_name"] = error_type
                logger.info(f"Checkpoint saved at {error_type}")

            try:
                result = await func(state, *args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"[{error_type}] Error: {e}")

                # 记录错误
                if "_errors" not in state:
                    state["_errors"] = []
                state["_errors"].append({
                    "node": error_type,
                    "error": str(e),
                    "type": type(e).__name__
                })

                # 尝试fallback
                if fallback_fn:
                    try:
                        if asyncio.iscoroutinefunction(fallback_fn):
                            return await fallback_fn(state, e)
                        else:
                            return fallback_fn(state, e)
                    except Exception as fallback_error:
                        logger.error(f"Fallback failed: {fallback_error}")
                        state[f"{error_type}_fallback"] = default_value
                        return state

                # 无fallback，返回降级状态
                state[f"{error_type}_failed"] = True
                state[f"{error_type}_result"] = default_value
                return state

        return wrapper
    return decorator


class CheckpointManager:
    """检查点管理器"""

    def __init__(self, max_checkpoints: int = 5):
        self.checkpoints: Dict[str, Dict[str, Any]] = {}
        self.max_checkpoints = max_checkpoints

    def save(self, name: str, state: Dict[str, Any]) -> None:
        """保存检查点"""
        self.checkpoints[name] = deepcopy(state)

        # 限制检查点数量
        if len(self.checkpoints) > self.max_checkpoints:
            oldest = list(self.checkpoints.keys())[0]
            del self.checkpoints[oldest]

        logger.info(f"Checkpoint saved: {name}")

    def restore(self, name: str) -> Optional[Dict[str, Any]]:
        """恢复检查点"""
        if name in self.checkpoints:
            logger.info(f"Checkpoint restored: {name}")
            return deepcopy(self.checkpoints[name])
        logger.warning(f"Checkpoint not found: {name}")
        return None

    def restore_latest(self) -> Optional[Dict[str, Any]]:
        """恢复最新检查点"""
        if self.checkpoints:
            name = list(self.checkpoints.keys())[-1]
            return self.restore(name)
        return None

    def list_checkpoints(self) -> list:
        return list(self.checkpoints.keys())


class ParallelExecutor:
    """并行执行器 - 允许部分失败"""

    @staticmethod
    async def execute_with_fallback(
        tasks: list,
        success_key: str = "results",
        error_key: str = "errors",
        min_success_ratio: float = 0.5
    ) -> Dict[str, Any]:
        """
        并行执行任务，允许部分失败

        Args:
            tasks: async任务列表
            success_key: 成功结果key
            error_key: 错误信息key
            min_success_ratio: 最小成功比例，低于此比例则整体失败

        Returns:
            {"results": [...], "errors": [...], "partial_failed": bool}
        """
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_results = []
        errors = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append({"index": i, "error": str(result)})
            else:
                success_results.append(result)

        # 检查是否满足最小成功比例
        total = len(tasks)
        success_count = len(success_results)
        success_ratio = success_count / total if total > 0 else 0

        return {
            success_key: success_results,
            error_key: errors,
            "partial_failed": len(errors) > 0,
            "success_ratio": success_ratio,
            "success_count": success_count,
            "total_count": total
        }

    @staticmethod
    async def execute_with_quorum(
        tasks: list,
        quorum_size: int = None,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """
        Quorum执行 - 等待多数完成即可

        Args:
            tasks: async任务列表
            quorum_size: 多数阈值（默认 len(tasks)/2 + 1）
            timeout: 超时时间

        Returns:
            {"results": [...], "quorum_reached": bool}
        """
        if quorum_size is None:
            quorum_size = len(tasks) // 2 + 1

        async def run_with_timeout():
            results = []
            errors = []
            pending = set()

            for i, task in enumerate(tasks):
                pending.add(asyncio.create_task(task))

            while pending and len(results) < quorum_size:
                done, pending = await asyncio.wait(
                    pending,
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED
                )

                for d in done:
                    try:
                        result = d.result()
                        results.append(result)
                    except Exception as e:
                        errors.append(str(e))

                    # 如果已经达到quorum，停止等待
                    if len(results) >= quorum_size:
                        break

            return results, errors

        results, errors = await run_with_timeout()

        return {
            "results": results,
            "quorum_reached": len(results) >= quorum_size,
            "results_count": len(results),
            "quorum_size": quorum_size,
            "errors": errors
        }


class RetryPolicy:
    """重试策略"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        exponential_backoff: bool = True,
        retry_on: tuple = (Exception,)
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.exponential_backoff = exponential_backoff
        self.retry_on = retry_on

    async def execute(self, fn: Callable, *args, **kwargs) -> Any:
        """执行带重试的函数"""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(fn):
                    return await fn(*args, **kwargs)
                else:
                    return fn(*args, **kwargs)
            except self.retry_on as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt if self.exponential_backoff else 1)
                    logger.warning(f"Retry {attempt + 1}/{self.max_retries} after {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All retries exhausted: {e}")

        raise last_error


class FallbackStrategies:
    """
    预定义降级策略集合

    提供各种场景的默认降级处理：
    - 搜索失败：使用缓存、历史数据、空结果
    - 阅读失败：跳过该论文、使用摘要
    - 分析失败：使用简化算法、返回空结果
    - 写作失败：使用模板、返回草稿
    """

    # ========== 搜索降级 ==========

    @staticmethod
    async def fallback_search_empty(state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """搜索失败降级：返回空列表"""
        logger.warning(f"Search fallback: returning empty list")
        return {
            "papers": [],
            "search_fallback_used": True,
            "search_error": str(error)
        }

    @staticmethod
    async def fallback_search_from_memory(state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """搜索失败降级：从记忆系统检索历史结果"""
        logger.warning(f"Search fallback: attempting memory retrieval")
        try:
            from src.agents.memory.memory_nodes import get_memory_manager
            memory = get_memory_manager()
            query = state.get("query", "")

            results = await memory.retrieve(query=query, top_k=10, include_short_term=True)

            if results:
                papers = []
                for r in results:
                    if isinstance(r, dict):
                        papers.append(r)
                    elif hasattr(r, 'content'):
                        # 尝试从记忆内容重建论文对象
                        papers.append({
                            "title": r.content[:100],
                            "abstract": r.content,
                            "source": "memory_cache"
                        })

                if papers:
                    logger.info(f"Search fallback: found {len(papers)} from memory")
                    return {
                        "papers": papers,
                        "search_fallback_used": True,
                        "search_fallback_source": "memory"
                    }

        except Exception as mem_error:
            logger.error(f"Memory fallback also failed: {mem_error}")

        return await FallbackStrategies.fallback_search_empty(state, error)

    @staticmethod
    async def fallback_search_broaden_query(state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """搜索失败降级：扩大查询范围"""
        logger.warning(f"Search fallback: broadening query")
        original_query = state.get("query", "")

        # 简化查询，移除复杂修饰
        broadened = original_query.split(";")[0].split(" and ")[0].split(" OR ")[0]
        if not broadened:
            broadened = original_query[:len(original_query)//2] if len(original_query) > 10 else original_query

        state["query"] = broadened
        state["search_broadened"] = True

        return state

    # ========== 阅读降级 ==========

    @staticmethod
    async def fallback_reading_skip(state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """阅读失败降级：跳过该论文"""
        failed_paper = state.get("current_paper", {})
        title = failed_paper.get("title", "unknown") if isinstance(failed_paper, dict) else "unknown"

        logger.warning(f"Reading fallback: skipping paper {title}")

        existing_analyses = state.get("paper_analyses", [])
        existing_analyses.append({
            "title": title,
            "analysis": None,
            "failed": True,
            "error": str(error)
        })

        return {
            "paper_analyses": existing_analyses,
            "reading_fallback_used": True
        }

    @staticmethod
    async def fallback_reading_abstract_only(state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """阅读失败降级：仅使用摘要"""
        paper = state.get("current_paper", {})
        if not isinstance(paper, dict):
            paper = {"title": "unknown", "abstract": ""}

        logger.warning(f"Reading fallback: using abstract only for {paper.get('title', 'unknown')}")

        # 创建最小化分析结果
        minimal_analysis = {
            "title": paper.get("title", "unknown"),
            "abstract": paper.get("abstract", ""),
            "source": "abstract_only",
            "analysis": {
                "summary": paper.get("abstract", "")[:500],
                "contributions": [],
                "methods": [],
                "datasets": [],
                "limitations": []
            }
        }

        existing = state.get("paper_analyses", [])
        existing.append(minimal_analysis)

        return {"paper_analyses": existing}

    # ========== 分析降级 ==========

    @staticmethod
    async def fallback_analysis_minimal(state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """分析失败降级：返回最小分析结果"""
        logger.warning(f"Analysis fallback: returning minimal results")

        paper_analyses = state.get("paper_analyses", [])

        # 从已有论文分析中提取基本信息
        themes = []
        research_gaps = []
        contradictions = []

        for analysis in paper_analyses:
            if isinstance(analysis, dict) and analysis.get("analysis"):
                # 尝试提取
                a = analysis.get("analysis", {})
                if a.get("summary"):
                    themes.append({"name": "主题", "description": a.get("summary", "")[:200]})

        return {
            "themes": themes or [{"name": "未分类", "description": "分析失败"}],
            "research_gaps": research_gaps,
            "contradictions": contradictions,
            "analysis_fallback_used": True
        }

    @staticmethod
    async def fallback_analysis_by_keyword(state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """分析失败降级：基于关键词简单分类"""
        logger.warning(f"Analysis fallback: keyword-based classification")

        papers = state.get("papers", [])
        themes = {}

        keywords = ["transformer", "attention", "graph", "neural", "learning", "model", "network", "data"]

        for paper in papers:
            if not isinstance(paper, dict):
                continue

            text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()

            for kw in keywords:
                if kw in text:
                    if kw not in themes:
                        themes[kw] = []
                    themes[kw].append(paper.get("title", ""))

        theme_list = [
            {"name": k, "papers": v, "description": f"包含关键词: {k}"}
            for k, v in themes.items()
        ]

        return {
            "themes": theme_list or [{"name": "未分类", "papers": [], "description": "无主题"}],
            "analysis_fallback_used": True,
            "analysis_method": "keyword_based"
        }

    # ========== 写作降级 ==========

    @staticmethod
    async def fallback_writing_template(state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """写作失败降级：使用模板"""
        logger.warning(f"Writing fallback: using template")

        sections = state.get("sections", [])
        query = state.get("query", "未知主题")

        template_sections = []
        for i, section in enumerate(sections):
            title = section.get("title", f"第{i+1}节") if isinstance(section, dict) else f"第{i+1}节"

            template_sections.append({
                "index": i,
                "title": title,
                "content": f"## {title}\n\n本节内容正在准备中，请稍候。\n\n**主题**: {query}\n**状态**: 因处理过程中的问题，内容暂未生成。",
                "completed": False,
                "fallback": True
            })

        existing = state.get("writted_sections", [])
        existing.extend(template_sections)

        return {
            "writted_sections": existing,
            "writing_fallback_used": True
        }

    @staticmethod
    async def fallback_writing_outline_only(state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """写作失败降级：仅返回大纲"""
        logger.warning(f"Writing fallback: outline only")

        sections = state.get("sections", [])
        outline_text = "# 研究报告大纲\n\n"

        for i, section in enumerate(sections):
            title = section.get("title", f"第{i+1}节") if isinstance(section, dict) else f"第{i+1}节"
            outline_text += f"{i+1}. {title}\n"

        outline_text += f"\n**研究主题**: {state.get('query', '未知')}\n"
        outline_text += "\n*注：详细内容的生成遇到问题，请稍后重试或调整查询范围。*"

        return {
            "outline": outline_text,
            "writted_sections": [{"title": "摘要", "content": outline_text, "completed": True, "outline_only": True}],
            "writing_fallback_used": True,
            "writing_method": "outline_only"
        }

    # ========== Critique降级 ==========

    @staticmethod
    async def fallback_critique_force_proceed(state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """Critique失败降级：强制通过进入写作"""
        logger.warning(f"Critique fallback: forcing to proceed")

        return {
            "critique_passed": True,
            "critique_fallback_used": True,
            "critique_result": {
                "score": 0.5,
                "passed": True,
                "fallback_reason": str(error)
            }
        }

    @staticmethod
    async def fallback_critique_reduce_requirements(state: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """Critique失败降级：降低要求重试"""
        logger.warning(f"Critique fallback: reducing requirements")

        current_iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", 3)

        # 放宽阈值
        state["_reduced_critique_threshold"] = True

        # 如果已经是最后一次迭代，强制通过
        if current_iteration >= max_iterations - 1:
            return await FallbackStrategies.fallback_critique_force_proceed(state, error)

        return state