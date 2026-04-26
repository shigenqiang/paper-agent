"""Task model for Agent system"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Task(BaseModel):
    """任务结构"""
    task_id: str = Field(..., description="任务ID")
    task_type: str = Field(..., description="任务类型")
    description: str = Field(default="", description="任务描述")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="输入数据")
    context: Optional[Dict[str, Any]] = Field(default=None, description="上下文")
    requirements: List[str] = Field(default_factory=list, description="需求列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    status: str = Field(default="pending", description="状态: pending/running/completed/failed")
    result: Optional[Any] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
