"""State models for Agent system"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """工具调用记录"""
    tool_name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="调用参数")
    result: Optional[Any] = Field(None, description="执行结果")
    success: bool = Field(True, description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")
    duration_ms: float = Field(0.0, description="执行时长(毫秒)")
    timestamp: datetime = Field(default_factory=datetime.now, description="调用时间")


class AgentMessage(BaseModel):
    """消息结构"""
    role: str = Field(..., description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentContext(BaseModel):
    """Agent执行上下文"""
    task_id: str = Field(default="", description="任务ID")
    task_type: str = Field(default="", description="任务类型")
    task_description: str = Field(default="", description="任务描述")
    current_step: int = Field(default=0, description="当前步骤")
    iteration_count: int = Field(default=0, description="当前迭代次数")
    max_iterations: int = Field(default=5, description="最大迭代次数")
    messages: List[AgentMessage] = Field(default_factory=list, description="消息历史")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="工具调用记录")

    def add_tool_call(self, tool_name: str, arguments: Dict, result: Any = None, error: Optional[str] = None):
        """添加工具调用记录"""
        self.tool_calls.append(ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            success=error is None,
            error=error
        ))


class AgentState(BaseModel):
    """Agent状态"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(default="initialized", description="状态: initialized/running/completed/failed")
    context: AgentContext = Field(default_factory=AgentContext, description="执行上下文")
    result: Optional[Any] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def add_error(self, error_msg: str) -> None:
        """添加错误信息"""
        if self.error:
            self.error += f"; {error_msg}"
        else:
            self.error = error_msg
