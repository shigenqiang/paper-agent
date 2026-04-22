"""简化的状态模型 - 基于Learn Claude Code的设计理念"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class TaskStatus(str):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int):
    """任务优先级枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AgentMessage(BaseModel):
    """Agent消息标准格式"""
    role: str = Field(..., description="消息角色: system, user, assistant, tool")
    content: str = Field(..., description="消息内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="消息元数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间戳")


class ToolCall(BaseModel):
    """工具调用记录"""
    tool_name: str = Field(..., description="工具名称")
    tool_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="工具调用ID")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    result: Optional[Any] = Field(None, description="工具执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    duration_ms: Optional[float] = Field(None, description="执行时长(毫秒)")


class AgentContext(BaseModel):
    """Agent上下文 - 简化的上下文管理"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="任务ID")
    task_type: str = Field(..., description="任务类型")
    task_description: str = Field(..., description="任务描述")

    # 消息历史 (ReAct循环使用)
    messages: List[AgentMessage] = Field(default_factory=list, description="消息历史")

    # 工具调用历史
    tool_calls: List[ToolCall] = Field(default_factory=list, description="工具调用历史")

    # 状态跟踪
    current_step: str = Field(default="init", description="当前步骤")
    iteration_count: int = Field(default=0, description="迭代次数")
    max_iterations: int = Field(default=20, description="最大迭代次数")

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    # 工作目录 (用于Worktree隔离)
    worktree_path: Optional[str] = Field(None, description="工作目录路径")

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """添加消息到上下文"""
        self.messages.append(AgentMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        ))

    def add_tool_call(self, tool_name: str, arguments: Dict, result: Any = None, error: str = None):
        """添加工具调用记录"""
        self.tool_calls.append(ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            error=error
        ))

    def should_continue(self) -> bool:
        """判断是否应该继续循环"""
        if self.iteration_count >= self.max_iterations:
            return False
        return True

    def increment_iteration(self):
        """增加迭代计数"""
        self.iteration_count += 1


class AgentState(BaseModel):
    """Agent状态 - 简化的状态管理"""
    status: Literal["idle", "thinking", "acting", "waiting", "error", "done"] = Field(default="idle", description="Agent状态")
    current_agent: Optional[str] = Field(None, description="当前执行的Agent")
    current_task: Optional[str] = Field(None, description="当前任务")
    context: Optional[AgentContext] = Field(None, description="当前上下文")

    # 错误处理
    errors: List[str] = Field(default_factory=list, description="错误列表")
    retry_count: int = Field(default=0, description="重试次数")
    max_retries: int = Field(default=3, description="最大重试次数")

    def set_status(self, status: str, current_agent: str = None):
        """设置Agent状态"""
        self.status = status
        if current_agent:
            self.current_agent = current_agent

    def add_error(self, error: str):
        """添加错误"""
        self.errors.append(error)
        self.retry_count += 1

    def should_retry(self) -> bool:
        """判断是否应该重试"""
        return self.retry_count < self.max_retries

    def clear_errors(self):
        """清除错误"""
        self.errors = []
        self.retry_count = 0


class WorkflowState(BaseModel):
    """工作流状态 - 编排器使用"""
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="工作流ID")
    user_request: str = Field(..., description="用户请求")
    task_graph: Dict[str, Any] = Field(default_factory=dict, description="任务图")

    # 执行状态
    completed_tasks: List[str] = Field(default_factory=list, description="已完成的任务")
    failed_tasks: List[str] = Field(default_factory=list, description="失败的任务")
    pending_tasks: List[str] = Field(default_factory=list, description="待处理的任务")

    # 结果收集
    results: Dict[str, Any] = Field(default_factory=dict, description="各Agent的结果")
    final_output: Optional[str] = Field(None, description="最终输出")

    # 状态跟踪
    status: Literal["planning", "executing", "reviewing", "completed", "failed"] = Field(default="planning")
    current_step: str = Field(default="init", description="当前步骤")

    # 质量控制
    review_results: List[Dict[str, Any]] = Field(default_factory=list, description="评审结果")
    quality_score: Optional[float] = Field(None, description="综合质量评分")
    passes_threshold: bool = Field(True, description="是否通过质量阈值")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    def add_result(self, task_id: str, agent_name: str, result: Any):
        """添加Agent结果"""
        self.results[task_id] = {
            "agent": agent_name,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }

    def mark_completed(self, task_id: str):
        """标记任务完成"""
        if task_id in self.pending_tasks:
            self.pending_tasks.remove(task_id)
        self.completed_tasks.append(task_id)

    def mark_failed(self, task_id: str, error: str):
        """标记任务失败"""
        if task_id in self.pending_tasks:
            self.pending_tasks.remove(task_id)
        self.failed_tasks.append(task_id)
        # 添加到工作流状态
        self.add_error(error)

    def add_error(self, error: str):
        """添加错误"""
        # 添加到当前步骤的结果中
        self.results[f"error_{self.current_step}"] = {
            "error": error,
            "timestamp": datetime.now().isoformat()
        }

    def get_progress(self) -> float:
        """获取进度百分比"""
        total = len(self.completed_tasks) + len(self.pending_tasks) + len(self.failed_tasks)
        if total == 0:
            return 0.0
        return (len(self.completed_tasks) / total) * 100
