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
import os

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
    # 诊断型Agent额外字段
    diagnosed_issues: List[str] = Field(default_factory=list, description="发现的问题列表")
    recommendations: List[str] = Field(default_factory=list, description="改进建议列表")


# 统一 LLMConfig - 从 base_agent 导入，避免重复定义
from ..core.base_agent import LLMConfig


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
            # 尝试加载 .env 文件
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass

            provider = self.llm_config.provider.lower()

            # 加载环境变量作为后备
            api_key = self.llm_config.api_key or os.getenv("OPENAI_API_KEY")
            base_url = self.llm_config.base_url or os.getenv("OPENAI_BASE_URL")

            if provider == "openai":
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=self.llm_config.model_name,
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens,
                    api_key=api_key,
                    base_url=base_url,
                    timeout=self.llm_config.timeout
                )
            elif provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                self._llm = ChatAnthropic(
                    model=self.llm_config.model_name,
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens,
                    api_key=api_key,
                    timeout=self.llm_config.timeout
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
            logger.warning("LLM未初始化，尝试重新初始化...")
            self._init_llm()
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
            return ""  # 返回空字符串而不是抛出异常

    def _clean_thinking_blocks(self, text: str) -> str:
        """清理思考块 (MiniMax等模型会输出)"""
        if not text:
            return text
        try:
            import re
            # 检查是否包含思考块标记
            marker = '<think>'
            if marker not in text:
                return text.strip()
            cleaned = re.sub(r'<think>.*?', '', text, flags=re.DOTALL)
            return cleaned.strip()
        except Exception as e:
            logger.warning(f"清理思考块失败: {e}")
            return text

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
