"""
Writing Agent基类 - 论文写作全流程Agent基类

基于论文Agent基类，针对写作流程做了优化
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class WritingInput(BaseModel):
    """标准输入"""
    task_type: str = Field(..., description="任务类型")
    task_description: str = Field(..., description="任务描述")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="任务输入数据")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    requirements: List[str] = Field(default_factory=list, description="需求列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class WritingOutput(BaseModel):
    """标准输出"""
    success: bool = Field(..., description="是否成功")
    result: Any = Field(None, description="执行结果")
    agent_name: str = Field(..., description="执行Agent名称")
    reasoning: Optional[str] = Field(None, description="推理过程")
    next_actions: List[str] = Field(default_factory=list, description="建议的后续操作")
    error: Optional[str] = Field(None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    quality_score: float = Field(0.0, description="质量评分")


# 统一 LLMConfig - 从 base_agent 导入，避免重复定义
from ..base_agent import LLMConfig


class WritingAgentBase(ABC):
    """
    Writing Agent基类 - 所有论文写作全流程Agent的基类

    设计原则：
    1. 统一的输入输出格式
    2. LLM调用封装
    3. 日志记录
    4. 质量评分
    """

    def __init__(
        self,
        name: str,
        llm_config: Optional[LLMConfig] = None,
        description: str = "",
        system_prompt: str = ""
    ):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.llm_config = llm_config or LLMConfig()
        self._llm = None
        self._init_llm()
        self._setup_logging()

        logger.info(f"WritingAgent {self.name} initialized")

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> WritingOutput:
        """
        执行Agent的主要任务

        Args:
            input_data: 输入数据
            context: 执行上下文

        Returns:
            WritingOutput: 执行结果
        """
        pass

    def _init_llm(self):
        """初始化LLM"""
        try:
            provider = self.llm_config.provider.lower()

            if provider == "openai":
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=self.llm_config.model_name,
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens,
                    api_key=self.llm_config.api_key,
                    base_url=self.llm_config.base_url
                )
            elif provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                self._llm = ChatAnthropic(
                    model=self.llm_config.model_name,
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens,
                    api_key=self.llm_config.api_key
                )
            else:
                raise ValueError(f"不支持的LLM提供商: {provider}")

            logger.info(f"Initialized LLM: {self.llm_config.provider} - {self.llm_config.model_name}")
        except Exception as e:
            logger.error(f"LLM初始化失败: {e}")
            self._llm = None

    async def _llm_call(self, prompt: str) -> str:
        """LLM调用封装"""
        if not self._llm:
            raise RuntimeError("LLM未初始化")

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=self.system_prompt or "你是一个专业的学术写作助手。"),
                HumanMessage(content=prompt)
            ]

            response = await self._llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            # 清理MiniMax模型的思考块
            content = self._clean_thinking_blocks(content)

            return content
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            raise

    def _clean_thinking_blocks(self, text: str) -> str:
        """清理思考块 (MiniMax等模型会输出)"""
        import re
        # 移除 <think>...</think> 块
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # 清理多余的空白
        cleaned = cleaned.strip()
        return cleaned

    def _setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger(f"WritingAgent.{self.name}")
        self.logger.setLevel(logging.INFO)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt
        }
