"""Agent基类定义"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class BaseAgent(ABC, BaseModel):
    """Agent抽象基类"""

    name: str
    description: str
    llm: Any = None

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行Agent的主要逻辑"""
        pass

    def get_name(self) -> str:
        """获取Agent名称"""
        return self.name

    def get_description(self) -> str:
        """获取Agent描述"""
        return self.description
