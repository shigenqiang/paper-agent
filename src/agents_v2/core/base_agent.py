"""Agent基础框架 - 新架构核心"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.agents_v2.logging_config import get_logging_logger

import json
import os

from src.models.state import AgentContext, AgentState, AgentMessage
from src.models.task import Task

logger = get_logging_logger(__name__)


class AgentInput(BaseModel):
    """Agent输入标准格式"""
    task_type: str = Field(..., description="任务类型")
    task_description: str = Field(..., description="任务描述")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="任务输入数据")
    context: Optional[str] = Field(None, description="上下文信息")
    requirements: List[str] = Field(default_factory=list, description="需求列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class AgentOutput(BaseModel):
    """Agent输出标准格式"""
    success: bool = Field(..., description="是否成功")
    result: Any = Field(None, description="执行结果")
    agent_name: str = Field(..., description="执行Agent名称")
    reasoning: Optional[str] = Field(None, description="推理过程")
    next_actions: List[str] = Field(default_factory=list, description="建议的后续操作")
    error: Optional[str] = Field(None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    tool_calls: List[str] = Field(default_factory=list, description="使用的工具列表")


class AgentCapability(BaseModel):
    """Agent能力描述"""
    task_types: List[str] = Field(..., description="能处理的任务类型")
    description: str = Field(..., description="能力描述")
    input_schema: Optional[Dict] = Field(None, description="输入Schema")
    output_schema: Optional[Dict] = Field(None, description="输出Schema")


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: str = Field(default="openai", description="LLM提供商")
    model_name: str = Field(default="MiniMax-M2.7", description="模型名称")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=2048, description="最大token数")
    api_key: Optional[str] = Field(None, description="API密钥")
    base_url: Optional[str] = Field(None, description="API基础URL")
    timeout: Optional[int] = Field(default=120, description="请求超时时间(秒)")


class Tool(BaseModel):
    """工具定义"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="参数Schema")


class BaseAgent(ABC):
    """
    Agent基类 - 所有Agent的标准接口

    设计原则 (来自Learn Claude Code/Nanobot):
    1. 简化的输入输出格式
    2. 工具注册机制
    3. LLM调用封装
    4. 日志记录
    5. 清晰的能力定义
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
        self.tools: List[Tool] = []
        self.capabilities = self._get_capabilities()

        # 初始化LLM
        self._init_llm()

        # 设置日志
        self._setup_logging()

        logger.info(f"Agent {self.name} initialized with {len(self.tools)} tools")

    @abstractmethod
    def _get_capabilities(self) -> AgentCapability:
        """定义Agent的能力"""
        pass

    @abstractmethod
    async def execute(self, input_data: AgentInput, context: Optional[AgentContext] = None) -> AgentOutput:
        """
        执行Agent的主要任务

        Args:
            input_data: 输入数据
            context: Agent上下文（可选）

        Returns:
            AgentOutput: 执行结果
        """
        pass

    def can_handle(self, task_type: str) -> bool:
        """判断该Agent是否能处理指定类型的任务"""
        return task_type in self.capabilities.task_types

    def add_tool(self, tool: Tool):
        """添加工具到Agent"""
        self.tools.append(tool)
        logger.info(f"Agent {self.name} added tool: {tool.name}")

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """获取工具Schema列表（用于LLM Function Calling）"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for tool in self.tools
        ]

    async def think(
        self,
        context: AgentContext,
        task_description: str = ""
    ) -> str:
        """
        思考下一步行动 (ReAct模式)

        Args:
            context: 当前上下文
            task_description: 任务描述

        Returns:
            思考结果 (JSON格式)
        """
        # 构建思考prompt
        prompt = self.system_prompt or f"你是{self.name}，一个专业的AI助手。"

        prompt += f"""

## 上下文
{context.task_description}
任务ID: {context.task_id}
任务类型: {context.task_type}
当前步骤: {context.current_step}
迭代次数: {context.iteration_count}/{context.max_iterations}

## 历史消息
{self._format_messages(context.messages)}

## 可用工具
{self._format_tools()}

## 你的能力
{self.capabilities.description}
可处理任务类型: {', '.join(self.capabilities.task_types)}

请思考下一步应该采取的行动。考虑：
1. 当前最需要什么信息？
2. 应该使用什么工具？
3. 如何完成当前任务？

请以JSON格式返回你的思考：
{{
  "thought": "你的思考过程",
  "next_action": "建议的下一步行动",
  "reasoning": "推理依据",
  "required_tools": ["需要的工具列表"]
}}
"""

        try:
            response = await self._llm_call(prompt)
            return response
        except Exception as e:
            logger.error(f"思考失败: {e}")
            return json.dumps({"error": str(e)})

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
                self.llm = ChatOpenAI(
                    model=self.llm_config.model_name,
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens,
                    api_key=api_key,
                    base_url=base_url
                )
            elif provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                self.llm = ChatAnthropic(
                    model=self.llm_config.model_name,
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens,
                    api_key=api_key
                )
            else:
                raise ValueError(f"不支持的LLM提供商: {provider}")

            logger.info(f"Initialized LLM: {self.llm_config.provider} - {self.llm_config.model_name}")
        except Exception as e:
            logger.error(f"LLM初始化失败: {e}")
            self.llm = None

    async def _llm_call(self, prompt: str) -> str:
        """LLM调用封装"""
        if not self.llm:
            logger.warning("LLM未初始化，尝试重新初始化...")
            self._init_llm()
            if not self.llm:
                raise RuntimeError("LLM未初始化")

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=self.system_prompt or "你是一个AI助手。"),
                HumanMessage(content=prompt)
            ]

            response = await self.llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            # 清理MiniMax模型的思考块
            content = self._clean_thinking_blocks(content)

            return content
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return ""  # 返回空字符串而不是抛出异常

    def _clean_thinking_blocks(self, text: str) -> str:
        """清理思考块 (MiniMax等模型会输出)"""
        import re
        # 移除 <think>...</think> 块
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # 清理多余的空白
        cleaned = cleaned.strip()
        return cleaned

    def _format_messages(self, messages: List[AgentMessage]) -> str:
        """格式化消息历史"""
        if not messages:
            return "（无消息）"

        lines = []
        for msg in messages[-10:]:  # 只显示最近10条
            role_map = {
                "system": "系统",
                "user": "用户",
                "assistant": "助手",
                "tool": "工具"
            }
            role = role_map.get(msg.role, msg.role)
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            lines.append(f"[{role}]: {content}")

        return "\n".join(lines)

    def _format_tools(self) -> str:
        """格式化工具列表"""
        if not self.tools:
            return "（无工具）"

        lines = []
        for tool in self.tools:
            lines.append(f"- {tool.name}: {tool.description}")

        return "\n".join(lines)

    def _setup_logging(self):
        """设置日志"""
        self.logger = get_logging_logger(f"Agent.{self.name}")
        self.logger.setLevel(logging.INFO)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": {
                "task_types": self.capabilities.task_types,
                "description": self.capabilities.description
            },
            "tools_count": len(self.tools),
            "system_prompt": self.system_prompt
        }


# 虚拟工具 - 用于结构化输出 (来自Nanobot的设计)
class VirtualTool:
    """
    虚拟工具 - 不真正执行，仅用于约束LLM输出格式

    用途:
    - 强制LLM输出JSON
    - 约束输出字段
    - 类型验证

    来自Nanobot的设计理念：利用Function Calling协议，而不是Prompt指令
    """

    @staticmethod
    def create_schema(name: str, properties: Dict[str, Any], required: List[str]) -> Dict[str, Any]:
        """
        创建虚拟工具Schema

        Args:
            name: 工具名称
            properties: 字段定义
            required: 必填字段列表

        Returns:
            工具Schema
        """
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": f"提交{name}结果",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
