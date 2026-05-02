"""
工具协同引擎 - Tool Coordination Engine

功能:
1. 工具依赖图管理
2. 执行计划生成
3. 并行执行优化
4. 循环检测
"""
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = get_logging_logger(__name__)


class DependencyType(str, Enum):
    """依赖类型"""
    REQUIRES = "requires"  # 强依赖：必须等待前置工具完成
    OPTIONAL = "optional"  # 可选依赖：结果可能被使用
    CONFLICTS = "conflicts"  # 冲突：不能同时执行


@dataclass
class ToolDependency:
    """工具依赖关系"""
    source_tool: str
    target_tool: str
    dependency_type: DependencyType = DependencyType.REQUIRES
    data_flow: Optional[str] = None  # 数据流字段名

    def __hash__(self):
        return hash((self.source_tool, self.target_tool, self.dependency_type))


@dataclass
class ExecutionPlan:
    """执行计划"""
    stages: List[List[str]]  # 分阶段的任务列表，同一阶段可并行
    total_tools: int
    estimated_duration_ms: float
    parallel_benefit: float = 1.0  # 并行化带来的加速比

    def get_flattened(self) -> List[str]:
        """获取扁平化的执行顺序"""
        result = []
        for stage in self.stages:
            result.extend(stage)
        return result


class ToolCoordinationEngine:
    """
    工具协同引擎

    功能:
    - 管理工具间的依赖关系
    - 生成最优执行计划
    - 支持并行执行
    - 循环检测
    """

    def __init__(self):
        self._dependencies: Dict[str, List[ToolDependency]] = {}  # tool -> outgoing edges
        self._reverse_deps: Dict[str, List[ToolDependency]] = {}  # tool -> incoming edges
        self._tool_metadata: Dict[str, Dict[str, Any]] = {}  # tool -> metadata

    def register_tool(
        self,
        tool_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        注册工具

        Args:
            tool_name: 工具名称
            metadata: 工具元数据（如预估执行时间）
        """
        if tool_name not in self._dependencies:
            self._dependencies[tool_name] = []
        if tool_name not in self._reverse_deps:
            self._reverse_deps[tool_name] = []

        if metadata:
            self._tool_metadata[tool_name] = metadata

    def add_dependency(
        self,
        source_tool: str,
        target_tool: str,
        dep_type: DependencyType = DependencyType.REQUIRES,
        data_flow: Optional[str] = None
    ) -> None:
        """
        添加工具依赖

        Args:
            source_tool: 源工具（先执行）
            target_tool: 目标工具（后执行）
            dep_type: 依赖类型
            data_flow: 数据流字段
        """
        # 注册工具（如果未注册）
        self.register_tool(source_tool)
        self.register_tool(target_tool)

        dep = ToolDependency(
            source_tool=source_tool,
            target_tool=target_tool,
            dependency_type=dep_type,
            data_flow=data_flow
        )

        self._dependencies[source_tool].append(dep)
        self._reverse_deps[target_tool].append(dep)

        logger.debug(f"Added dependency: {source_tool} -> {target_tool} ({dep_type})")

    def remove_dependency(
        self,
        source_tool: str,
        target_tool: str
    ) -> bool:
        """移除依赖"""
        removed = False

        # 从源工具的出边移除
        if source_tool in self._dependencies:
            self._dependencies[source_tool] = [
                d for d in self._dependencies[source_tool]
                if d.target_tool != target_tool
            ]

        # 从目标工具的入边移除
        if target_tool in self._reverse_deps:
            self._reverse_deps[target_tool] = [
                d for d in self._reverse_deps[target_tool]
                if d.source_tool != source_tool
            ]

        return removed

    def get_dependencies(self, tool_name: str) -> List[ToolDependency]:
        """获取工具的出向依赖"""
        return self._dependencies.get(tool_name, [])

    def get_dependents(self, tool_name: str) -> List[ToolDependency]:
        """获取工具的入向依赖（谁依赖这个工具）"""
        return self._reverse_deps.get(tool_name, [])

    def get_execution_order(self, tools: List[str]) -> List[str]:
        """
        获取工具的执行顺序（拓扑排序）

        Args:
            tools: 工具列表

        Returns:
            排序后的工具列表
        """
        # 计算入度
        in_degree = {t: 0 for t in tools}
        adj_list = {t: [] for t in tools}

        for tool in tools:
            for dep in self._dependencies.get(tool, []):
                if dep.target_tool in tools:
                    adj_list[dep.source_tool].append(dep.target_tool)
                    in_degree[dep.target_tool] += 1

        # Kahn算法
        queue = [t for t in tools if in_degree[t] == 0]
        result = []

        while queue:
            # 优先选择没有依赖的工具（可并行）
            current = queue.pop(0)
            result.append(current)

            for neighbor in adj_list[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 检查是否有环
        if len(result) != len(tools):
            logger.warning(f"Circular dependency detected, partial order: {result}")
            # 返回部分结果
            return result

        return result

    def generate_execution_plan(
        self,
        tools: List[str],
        tool_durations: Optional[Dict[str, float]] = None
    ) -> ExecutionPlan:
        """
        生成执行计划

        Args:
            tools: 需要执行的工具列表
            tool_durations: 工具预估执行时间（毫秒）

        Returns:
            ExecutionPlan
        """
        if not tools:
            return ExecutionPlan(stages=[], total_tools=0, estimated_duration_ms=0)

        if tool_durations is None:
            tool_durations = {t: 1000.0 for t in tools}  # 默认1秒

        # 构建依赖子图
        relevant_deps = self._filter_dependencies(tools)

        # 计算每个工具的直接依赖
        direct_deps = {}
        for tool in tools:
            direct_deps[tool] = set()
            for dep in relevant_deps:
                if dep.target_tool == tool:
                    direct_deps[tool].add(dep.source_tool)

        # 计算层级（按照依赖深度）
        levels: Dict[str, int] = {}
        remaining = set(tools)

        while remaining:
            # 找到没有未处理依赖的工具
            ready = [t for t in remaining if not (direct_deps[t] & remaining)]

            if not ready:
                # 循环依赖，随机选择一个
                logger.warning("Circular dependency detected, forcing progress")
                ready = [list(remaining)[0]]

            for tool in ready:
                # 计算层级
                deps_level = max([levels[d] for d in direct_deps[tool] if d in levels], default=-1)
                levels[tool] = deps_level + 1
                remaining.remove(tool)

        # 按层级分组
        max_level = max(levels.values(), default=0)
        stages = [[] for _ in range(max_level + 1)]
        for tool, level in levels.items():
            stages[level].append(tool)

        # 计算总时长
        total_time = sum(tool_durations.get(t, 1000) for t in tools)
        parallel_time = sum(
            max(tool_durations.get(t, 1000) for t in stage)
            for stage in stages
        )

        return ExecutionPlan(
            stages=stages,
            total_tools=len(tools),
            estimated_duration_ms=parallel_time,
            parallel_benefit=total_time / parallel_time if parallel_time > 0 else 1.0
        )

    def _filter_dependencies(self, tools: List[str]) -> List[ToolDependency]:
        """过滤出与给定工具相关的依赖"""
        result = []
        tools_set = set(tools)

        for tool in tools:
            for dep in self._dependencies.get(tool, []):
                if dep.target_tool in tools_set:
                    result.append(dep)

        return result

    def detect_cycles(self) -> List[List[str]]:
        """
        检测循环依赖

        Returns:
            环列表，每个环是一个工具名称列表
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(tool: str) -> bool:
            visited.add(tool)
            rec_stack.add(tool)
            path.append(tool)

            for dep in self._dependencies.get(tool, []):
                neighbor = dep.target_tool
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # 发现环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    return True

            path.pop()
            rec_stack.remove(tool)
            return False

        for tool in self._dependencies:
            if tool not in visited:
                dfs(tool)

        return cycles

    def get_parallelizable_groups(self, tools: List[str]) -> List[List[str]]:
        """
        获取可以并行执行的工具组

        Args:
            tools: 工具列表

        Returns:
            可并行执行的工具分组
        """
        plan = self.generate_execution_plan(tools)
        return plan.stages

    def suggest_parallelization(
        self,
        tools: List[str],
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        建议并行化方案

        Args:
            tools: 工具列表
            max_concurrent: 最大并发数

        Returns:
            并行化建议
        """
        plan = self.generate_execution_plan(tools)

        # 分析各阶段的并行潜力
        stage_analysis = []
        for i, stage in enumerate(plan.stages):
            stage_analysis.append({
                "stage": i,
                "tools": stage,
                "can_run_parallel": len(stage) > 1,
                "recommended_workers": min(len(stage), max_concurrent) if len(stage) > 1 else 1
            })

        return {
            "execution_plan": {
                "stages": plan.stages,
                "total_tools": plan.total_tools,
                "estimated_duration_ms": plan.estimated_duration_ms,
                "parallel_benefit": plan.parallel_benefit
            },
            "stage_analysis": stage_analysis,
            "recommendations": self._generate_recommendations(plan, max_concurrent)
        }

    def _generate_recommendations(
        self,
        plan: ExecutionPlan,
        max_concurrent: int
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []

        if plan.parallel_benefit > 2.0:
            recommendations.append(
                f"High parallelization benefit ({plan.parallel_benefit:.1f}x). "
                "Consider increasing concurrent workers."
            )

        for i, stage in enumerate(plan.stages):
            if len(stage) > max_concurrent:
                recommendations.append(
                    f"Stage {i} has {len(stage)} tools but max concurrent is {max_concurrent}. "
                    "Consider splitting or increasing limit."
                )

        # 检查是否可以进一步并行化
        sequential_pairs = 0
        for i in range(len(plan.stages) - 1):
            if len(plan.stages[i]) == 1 and len(plan.stages[i + 1]) == 1:
                sequential_pairs += 1

        if sequential_pairs > 2:
            recommendations.append(
                f"Found {sequential_pairs} sequential tool pairs. "
                "Check if dependencies can be relaxed for better parallelism."
            )

        return recommendations

    def clear(self) -> None:
        """清空所有依赖和注册信息"""
        self._dependencies.clear()
        self._reverse_deps.clear()
        self._tool_metadata.clear()


# 全局实例
_coordination_engine: Optional[ToolCoordinationEngine] = None


def get_coordination_engine() -> ToolCoordinationEngine:
    """获取工具协同引擎单例"""
    global _coordination_engine
    if _coordination_engine is None:
        _coordination_engine = ToolCoordinationEngine()
    return _coordination_engine


# ==================== 工具执行器 ====================

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from abc import ABC, abstractmethod
from src.agents_v2.logging_config import get_logging_logger

import asyncio
from datetime import datetime
from .tool_spec import ToolResult


@dataclass
class ExecutionContext:
    """执行上下文"""
    tool_name: str
    args: Dict[str, Any]
    start_time: datetime
    attempt: int = 1
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ToolMiddleware(ABC):
    """工具中间件基类"""

    @abstractmethod
    async def before_execute(
        self,
        context: ExecutionContext
    ) -> ExecutionContext:
        """执行前调用"""
        pass

    @abstractmethod
    async def after_execute(
        self,
        context: ExecutionContext,
        result: ToolResult
    ) -> ToolResult:
        """执行后调用"""
        pass


class RetryMiddleware(ToolMiddleware):
    """重试中间件"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 10.0,
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    async def before_execute(self, context: ExecutionContext) -> ExecutionContext:
        return context

    async def after_execute(
        self,
        context: ExecutionContext,
        result: ToolResult
    ) -> ToolResult:
        if result.success or context.attempt >= self.max_retries:
            return result

        # 计算延迟
        delay = min(
            self.base_delay * (self.exponential_base ** (context.attempt - 1)),
            self.max_delay
        )
        logger.warning(
            f"Tool {context.tool_name} failed (attempt {context.attempt}), "
            f"retrying in {delay:.1f}s..."
        )
        await asyncio.sleep(delay)

        # 返回特殊标记触发重试
        result.retry = True
        return result


class TimeoutMiddleware(ToolMiddleware):
    """超时中间件"""

    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout

    async def before_execute(self, context: ExecutionContext) -> ExecutionContext:
        timeout = context.metadata.get("timeout", self.default_timeout)
        context.metadata["timeout"] = timeout
        return context

    async def after_execute(
        self,
        context: ExecutionContext,
        result: ToolResult
    ) -> ToolResult:
        return result


class RateLimitMiddleware(ToolMiddleware):
    """限流中间件"""

    def __init__(self, max_calls_per_minute: int = 60):
        self.max_calls = max_calls_per_minute
        self.calls: List[float] = []

    async def before_execute(self, context: ExecutionContext) -> ExecutionContext:
        now = time.time()
        # 清理过期的调用记录
        self.calls = [t for t in self.calls if now - t < 60]

        if len(self.calls) >= self.max_calls:
            wait_time = 60 - (now - self.calls[0]) if self.calls else 60
            logger.warning(
                f"Rate limit reached for {context.tool_name}, "
                f"waiting {wait_time:.1f}s"
            )
            await asyncio.sleep(wait_time)
            self.calls = [t for t in self.calls if now - t < 60]

        self.calls.append(now)
        return context

    async def after_execute(
        self,
        context: ExecutionContext,
        result: ToolResult
    ) -> ToolResult:
        return result


class ToolExecutor:
    """
    工具执行器

    特性:
    - 中间件支持（拦截器链）
    - 重试机制
    - 超时控制
    - 熔断器集成
    - 执行日志
    """

    def __init__(
        self,
        registry: 'ToolRegistry',  # 前向引用
        circuit_breaker: Optional['CircuitBreaker'] = None
    ):
        self.registry = registry
        self.circuit_breaker = circuit_breaker
        self.middlewares: List[ToolMiddleware] = [
            RateLimitMiddleware(),
            TimeoutMiddleware(),
            RetryMiddleware(),
        ]
        self.execution_log: List[Dict] = []

    def add_middleware(self, middleware: ToolMiddleware) -> None:
        """添加中间件"""
        self.middlewares.append(middleware)

    async def execute(
        self,
        tool_name: str,
        args: Dict[str, Any],
        timeout: Optional[float] = None,
        retry: bool = True
    ) -> ToolResult:
        """
        执行工具

        Args:
            tool_name: 工具名称
            args: 工具参数
            timeout: 超时时间（秒）
            retry: 是否启用重试

        Returns:
            ToolResult
        """
        context = ExecutionContext(
            tool_name=tool_name,
            args=args,
            start_time=datetime.now(),
            metadata={"timeout": timeout} if timeout else {}
        )

        attempt = 0
        max_attempts = 1 if not retry else 10  # 重试由RetryMiddleware控制

        while attempt < max_attempts:
            attempt += 1
            context.attempt = attempt

            try:
                # 通过中间件链处理
                ctx = context
                for mw in self.middlewares:
                    ctx = await mw.before_execute(ctx)

                # 执行工具
                spec = self.registry.get(tool_name)
                if not spec:
                    return ToolResult(
                        success=False,
                        error=f"Tool not found: {tool_name}"
                    )

                # 带超时执行
                result = await self._execute_with_timeout(
                    spec, args, ctx.metadata.get("timeout")
                )

                # 通过中间件链后处理
                for mw in self.middlewares:
                    result = await mw.after_execute(ctx, result)

                # 记录执行
                self._log_execution(ctx, result)

                # 检查是否需要重试
                if not hasattr(result, 'retry') or not result.retry:
                    return result

            except asyncio.TimeoutError:
                result = ToolResult(
                    success=False,
                    error=f"Tool execution timed out after {ctx.metadata.get('timeout')}s"
                )
                self._log_execution(ctx, result)
                return result

            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                result = ToolResult(success=False, error=str(e))
                self._log_execution(ctx, result)
                return result

        return result

    async def _execute_with_timeout(
        self,
        spec: 'ToolSpec',
        args: Dict[str, Any],
        timeout: Optional[float]
    ) -> ToolResult:
        """带超时的执行"""
        if timeout:
            try:
                return await asyncio.wait_for(
                    self._do_execute(spec, args),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                raise
        else:
            return await self._do_execute(spec, args)

    async def _do_execute(
        self,
        spec: 'ToolSpec',
        args: Dict[str, Any]
    ) -> ToolResult:
        """实际执行"""
        try:
            handler = spec.handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**args)
            else:
                result = handler(**args)

            if isinstance(result, ToolResult):
                return result
            return ToolResult(success=True, result=result)

        except Exception as e:
            logger.error(f"Tool handler error: {e}")
            return ToolResult(success=False, error=str(e))

    def _log_execution(
        self,
        context: ExecutionContext,
        result: ToolResult
    ) -> None:
        """记录执行日志"""
        duration = (datetime.now() - context.start_time).total_seconds()
        entry = {
            "tool_name": context.tool_name,
            "args": context.args,
            "attempt": context.attempt,
            "success": result.success,
            "error": result.error,
            "duration": duration,
            "timestamp": context.start_time.isoformat()
        }
        self.execution_log.append(entry)

        # 保持日志在合理大小
        if len(self.execution_log) > 1000:
            self.execution_log = self.execution_log[-500:]

    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        if not self.execution_log:
            return {"total": 0, "success_rate": 0}

        total = len(self.execution_log)
        successes = sum(1 for e in self.execution_log if e["success"])
        avg_duration = sum(e["duration"] for e in self.execution_log) / total

        return {
            "total": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": successes / total if total > 0 else 0,
            "avg_duration": avg_duration
        }


# 全局执行器实例
_executor: Optional[ToolExecutor] = None


def get_tool_executor() -> ToolExecutor:
    """获取工具执行器单例"""
    global _executor
    if _executor is None:
        from .registry import ToolRegistry
        from ..unified.circuit_breaker import CircuitBreaker

        registry = ToolRegistry()
        cb = CircuitBreaker(name="tool_circuit_breaker")
        _executor = ToolExecutor(registry, cb)
    return _executor
