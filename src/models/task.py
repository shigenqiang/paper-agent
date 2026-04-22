"""任务模型 - 任务图和依赖关系管理"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from .state import TaskStatus, TaskPriority


class Task(BaseModel):
    """任务基类"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="任务ID")
    task_type: str = Field(..., description="任务类型")
    task_name: str = Field(..., description="任务名称")
    task_description: str = Field(..., description="任务描述")

    # 状态和优先级
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="任务优先级")

    # 依赖关系
    dependencies: List[str] = Field(default_factory=list, description="依赖的任务ID列表")
    dependents: List[str] = Field(default_factory=list, description="依赖此任务的任务ID列表")

    # 执行信息
    assigned_agent: Optional[str] = Field(None, description="分配的Agent")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration_seconds: Optional[float] = Field(None, description="执行时长(秒)")

    # 结果
    result: Optional[Any] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="任务元数据")
    worktree_id: Optional[str] = Field(None, description="关联的Worktree ID")

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    def can_start(self, completed_tasks: Set[str]) -> bool:
        """判断任务是否可以开始"""
        # 检查状态
        if self.status != TaskStatus.PENDING:
            return False

        # 检查依赖是否都已完成
        return all(dep in completed_tasks for dep in self.dependencies)

    def mark_started(self, agent: str):
        """标记任务开始"""
        self.status = TaskStatus.RUNNING
        self.assigned_agent = agent
        self.start_time = datetime.now()
        self.updated_at = datetime.now()

    def mark_completed(self, result: Any = None):
        """标记任务完成"""
        self.status = TaskStatus.COMPLETED
        self.end_time = datetime.now()
        self.updated_at = datetime.now()
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        if result is not None:
            self.result = result

    def mark_failed(self, error: str):
        """标记任务失败"""
        self.status = TaskStatus.FAILED
        self.end_time = datetime.now()
        self.updated_at = datetime.now()
        self.error = error
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    def mark_cancelled(self):
        """标记任务取消"""
        self.status = TaskStatus.CANCELLED
        self.updated_at = datetime.now()

    def add_dependency(self, task_id: str):
        """添加依赖"""
        if task_id not in self.dependencies:
            self.dependencies.append(task_id)

    def add_dependent(self, task_id: str):
        """添加依赖此任务的任务"""
        if task_id not in self.dependents:
            self.dependents.append(task_id)


class TaskGraph(BaseModel):
    """任务图 - 管理任务和依赖关系"""
    tasks: Dict[str, Task] = Field(default_factory=dict, description="所有任务")
    roots: List[str] = Field(default_factory=list, description="根任务ID列表")

    # 元数据
    graph_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="图ID")
    name: str = Field(default="default", description="任务图名称")
    description: str = Field(default="", description="任务图描述")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    def add_task(self, task: Task):
        """添加任务到图中"""
        self.tasks[task.task_id] = task
        self._update_roots()

    def add_tasks(self, tasks: List[Task]):
        """批量添加任务"""
        for task in tasks:
            self.add_task(task)

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)

    def get_ready_tasks(self) -> List[Task]:
        """获取可以执行的任务（依赖已满足）"""
        completed_tasks = {
            tid for tid, task in self.tasks.items()
            if task.status == TaskStatus.COMPLETED
        }

        ready_tasks = []
        for task in self.tasks.values():
            if task.can_start(completed_tasks):
                ready_tasks.append(task)

        return ready_tasks

    def get_pending_tasks(self) -> List[Task]:
        """获取所有待处理任务"""
        return [
            task for task in self.tasks.values()
            if task.status == TaskStatus.PENDING
        ]

    def get_running_tasks(self) -> List[Task]:
        """获取正在执行的任务"""
        return [
            task for task in self.tasks.values()
            if task.status == TaskStatus.RUNNING
        ]

    def is_complete(self) -> bool:
        """判断任务图是否完成"""
        return all(
            task.status == TaskStatus.COMPLETED
            for task in self.tasks.values()
        )

    def is_failed(self) -> bool:
        """判断任务图是否失败"""
        return any(
            task.status == TaskStatus.FAILED
            for task in self.tasks.values()
        )

    def get_progress(self) -> Dict[str, Any]:
        """获取任务图进度"""
        total = len(self.tasks)
        completed = sum(
            1 for task in self.tasks.values()
            if task.status == TaskStatus.COMPLETED
        )
        failed = sum(
            1 for task in self.tasks.values()
            if task.status == TaskStatus.FAILED
        )
        running = sum(
            1 for task in self.tasks.values()
            if task.status == TaskStatus.RUNNING
        )

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": total - completed - failed - running,
            "progress_percent": (completed / total * 100) if total > 0 else 0
        }

    def get_next_tasks(self, limit: int = 3) -> List[Task]:
        """获取下一批待执行任务（按优先级排序）"""
        ready_tasks = self.get_ready_tasks()
        # 按优先级和创建时间排序
        sorted_tasks = sorted(
            ready_tasks,
            key=lambda t: (-t.priority, t.created_at)
        )
        return sorted_tasks[:limit]

    def validate_dependencies(self) -> List[str]:
        """验证依赖关系的完整性"""
        errors = []
        all_task_ids = set(self.tasks.keys())

        for task_id, task in self.tasks.items():
            for dep_id in task.dependencies:
                if dep_id not in all_task_ids:
                    errors.append(
                        f"任务 {task_id} 的依赖 {dep_id} 不存在"
                    )

        return errors

    def _update_roots(self):
        """更新根任务列表"""
        # 找出没有依赖的任务
        self.roots = [
            task_id for task_id, task in self.tasks.items()
            if not task.dependencies
        ]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "description": self.description,
            "tasks": {
                task_id: task.model_dump()
                for task_id, task in self.tasks.items()
            },
            "progress": self.get_progress(),
            "status": "completed" if self.is_complete() else "failed" if self.is_failed() else "in_progress"
        }
