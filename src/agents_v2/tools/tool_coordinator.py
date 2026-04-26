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
import logging

logger = logging.getLogger(__name__)


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
