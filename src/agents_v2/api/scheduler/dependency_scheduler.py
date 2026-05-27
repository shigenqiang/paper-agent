"""
Dependency Scheduler - 依赖调度器

基于任务依赖图的并行调度器。
"""
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from src.agents_v2.logging_config import get_logging_logger

import asyncio

logger = get_logging_logger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """任务"""
    task_id: str
    name: str
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务ID
    executable: Optional[Callable] = None
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None


@dataclass
class ExecutionResult:
    """执行结果"""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0


class DependencyScheduler:
    """
    依赖调度器

    基于任务依赖图进行拓扑排序和并行调度。

    使用示例:
        scheduler = DependencyScheduler()

        # 添加任务
        scheduler.add_task(Task(
            task_id="t1",
            name="Task 1",
            executable=async_func1
        ))
        scheduler.add_task(Task(
            task_id="t2",
            name="Task 2",
            dependencies=["t1"],  # 依赖t1
            executable=async_func2
        ))

        # 执行
        results = await scheduler.execute_all()

        # 获取结果
        result = results["t2"]
    """

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._tasks: Dict[str, Task] = {}
        self._task_results: Dict[str, ExecutionResult] = {}
        self._running_tasks: Set[str] = set()
        self._completed_tasks: Set[str] = set()

    def add_task(self, task: Task) -> None:
        """添加任务"""
        self._tasks[task.task_id] = task

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._tasks.get(task_id)

    def get_ready_tasks(self) -> List[Task]:
        """获取就绪的任务（所有依赖已完成）"""
        ready = []

        for task in self._tasks.values():
            if task.status != TaskStatus.PENDING:
                continue

            # 检查所有依赖是否完成
            deps_completed = all(
                self._tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
                if dep_id in self._tasks
            )

            if deps_completed:
                ready.append(task)

        return ready

    def get_execution_order(self) -> List[List[str]]:
        """
        获取执行顺序（拓扑排序分组）

        Returns:
            按执行批次分组的任务ID列表
        """
        levels: List[List[str]] = []
        remaining = set(self._tasks.keys())
        completed = set()

        while remaining:
            # 找到这一批可以执行的任务
            current_level = []

            for task_id in remaining:
                task = self._tasks[task_id]
                deps_met = all(dep in completed for dep in task.dependencies if dep in self._tasks)

                if deps_met:
                    current_level.append(task_id)

            if not current_level:
                # 有循环依赖
                logger.error(f"Circular dependency detected. Remaining: {remaining}")
                break

            levels.append(current_level)

            # 更新状态
            for task_id in current_level:
                remaining.remove(task_id)
                completed.add(task_id)

        return levels

    async def execute_all(self) -> Dict[str, ExecutionResult]:
        """
        执行所有任务

        Returns:
            Dict[str, ExecutionResult]: 任务ID到执行结果的映射
        """
        execution_order = self.get_execution_order()

        for level_tasks in execution_order:
            # 这一批任务可以并行执行
            level_results = await asyncio.gather(
                *[self._execute_task(task_id) for task_id in level_tasks],
                return_exceptions=True
            )

            # 处理结果
            for task_id, result in zip(level_tasks, level_results):
                if isinstance(result, Exception):
                    self._task_results[task_id] = ExecutionResult(
                        task_id=task_id,
                        success=False,
                        error=str(result)
                    )
                else:
                    self._task_results[task_id] = result

        return self._task_results

    async def _execute_task(self, task_id: str) -> ExecutionResult:
        """执行单个任务"""
        task = self._tasks.get(task_id)
        if not task:
            return ExecutionResult(
                task_id=task_id,
                success=False,
                error="Task not found"
            )

        task.status = TaskStatus.RUNNING
        self._running_tasks.add(task_id)

        start_time = asyncio.get_event_loop().time()

        try:
            # 等待依赖任务的结果
            dep_results = {
                dep_id: self._task_results.get(dep_id)
                for dep_id in task.dependencies
                if dep_id in self._task_results
            }

            # 准备参数
            args = task.args
            kwargs = task.kwargs.copy()
            kwargs["dependencies"] = dep_results

            # 执行
            if task.executable:
                if asyncio.iscoroutinefunction(task.executable):
                    result = await task.executable(*args, **kwargs)
                else:
                    result = task.executable(*args, **kwargs)
            else:
                result = None

            task.status = TaskStatus.COMPLETED
            task.result = result
            self._completed_tasks.add(task_id)

            execution_time = asyncio.get_event_loop().time() - start_time

            return ExecutionResult(
                task_id=task_id,
                success=True,
                result=result,
                execution_time=execution_time
            )

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            task.status = TaskStatus.FAILED
            task.error = str(e)

            execution_time = asyncio.get_event_loop().time() - start_time

            return ExecutionResult(
                task_id=task_id,
                success=False,
                error=str(e),
                execution_time=execution_time
            )

        finally:
            self._running_tasks.discard(task_id)

    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            "total_tasks": len(self._tasks),
            "pending": sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING),
            "running": len(self._running_tasks),
            "completed": len(self._completed_tasks),
            "execution_order": self.get_execution_order()
        }

    def cancel(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            return True

        return False

    def clear(self) -> None:
        """清空所有任务"""
        self._tasks.clear()
        self._task_results.clear()
        self._running_tasks.clear()
        self._completed_tasks.clear()


class TaskBuilder:
    """任务构建器"""

    def __init__(self):
        self._tasks: List[Task] = []

    def add(
        self,
        task_id: str,
        name: str,
        executable: Optional[Callable] = None,
        dependencies: Optional[List[str]] = None
    ) -> "TaskBuilder":
        """添加任务"""
        self._tasks.append(Task(
            task_id=task_id,
            name=name,
            executable=executable,
            dependencies=dependencies or []
        ))
        return self

    def build(self) -> List[Task]:
        """构建任务列表"""
        return self._tasks


def create_scheduler(max_concurrent: int = 5) -> DependencyScheduler:
    """创建调度器"""
    return DependencyScheduler(max_concurrent=max_concurrent)
