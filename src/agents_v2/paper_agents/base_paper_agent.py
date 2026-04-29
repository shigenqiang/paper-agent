"""
Paper Agent基类 - 基于论文写作流程的Agent基类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import json
import asyncio
import os

logger = logging.getLogger(__name__)


# ============ Agent输入输出模型 ============

class AgentInput(BaseModel):
    """Agent标准输入"""
    task_type: str = Field(..., description="任务类型")
    task_description: str = Field(..., description="任务描述")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="任务输入数据")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    requirements: List[str] = Field(default_factory=list, description="需求列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class AgentOutput(BaseModel):
    """Agent标准输出"""
    success: bool = Field(..., description="是否成功")
    result: Any = Field(None, description="执行结果")
    agent_name: str = Field(..., description="执行Agent名称")
    reasoning: Optional[str] = Field(None, description="推理过程")
    next_actions: List[str] = Field(default_factory=list, description="建议的后续操作")
    error: Optional[str] = Field(None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    quality_score: float = Field(0.0, description="质量评分")


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: str = Field(default="openai", description="LLM提供商")
    model_name: str = Field(default="gpt-4", description="模型名称")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=4096, description="最大token数")
    api_key: Optional[str] = Field(None, description="API密钥")
    base_url: Optional[str] = Field(None, description="API基础URL")


# ============ Agent基类 ============

class PaperAgentBase(ABC):
    """
    Paper Agent基类 - 所有论文写作Agent的基类

    设计原则：
    1. 统一的输入输出格式
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
        self.tools: List[Callable] = []
        self._llm = None
        self._init_llm()
        self._setup_logging()

        logger.info(f"Agent {self.name} initialized")

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentOutput:
        """
        执行Agent的主要任务

        Args:
            input_data: 输入数据
            context: 执行上下文

        Returns:
            AgentOutput: 执行结果
        """
        pass

    def add_tool(self, tool: Callable):
        """添加工具到Agent"""
        self.tools.append(tool)
        logger.info(f"Agent {self.name} added tool: {tool.__name__}")

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """获取工具Schema列表（用于LLM Function Calling）"""
        schemas = []
        for tool in self.tools:
            if hasattr(tool, "__name__"):
                schemas.append({
                    "type": "function",
                    "function": {
                        "name": tool.__name__,
                        "description": tool.__doc__ or "Tool",
                        "parameters": {"type": "object", "properties": {}}
                    }
                })
        return schemas

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
        """LLM调用封装 - 使用原生 OpenAI 客户端"""
        try:
            from openai import OpenAI

            api_key = self.llm_config.api_key or os.getenv("OPENAI_API_KEY", "")
            base_url = self.llm_config.base_url or os.getenv("OPENAI_BASE_URL", "https://api.minimax.chat/v1")
            model = self.llm_config.model_name or os.getenv("LLM_MODEL", "MiniMax-M2.7")

            client = OpenAI(api_key=api_key, base_url=base_url)

            # 构建消息
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                extra_body={"reasoning_split": False}
            )

            content = response.choices[0].message.content or ""

            # 清理思考块
            content = self._clean_thinking_blocks(content)

            return content
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            raise

    def _clean_thinking_blocks(self, text: str) -> str:
        """清理思考块 (MiniMax等模型会输出)

        MiniMax模型会将实际输出放在<think>...</think>块内部，
        而不是之后。需要从块内提取实际内容。
        """
        import re

        # 首先检查是否有<think>...</think>块
        thinking_match = re.search(r'<think>(.*?)</think>', text, flags=re.DOTALL)

        if thinking_match:
            thinking_content = thinking_match.group(1)

            # 从思考内容中提取实际输出
            # 尝试多种模式来找到实际内容
            output_patterns = [
                r'Thus output:\s*(\{[^}]+\})',
                r'output:\s*(\{[^}]+\})',
                r'Output:\s*(\{[^}]+\})',
                r'respond with:\s*(\{[^}]+\})',
                r'So (?:we|I) (?:should|would|need to) (?:output|respond with|return):\s*(\{[^}]+\})',
            ]

            cleaned = None
            for pattern in output_patterns:
                match = re.search(pattern, thinking_content, flags=re.DOTALL)
                if match:
                    cleaned = match.group(1)
                    break

            # 如果没找到特定模式，尝试查找JSON对象
            if not cleaned:
                # 在思考内容中查找JSON对象
                json_match = re.search(r'\{[^{}]*\}', thinking_content)
                if json_match:
                    cleaned = json_match.group()

            # 如果还是没找到，尝试在思考内容之后的部分找
            if not cleaned:
                after_thinking = text.split('</think>')[1] if ']]' in text else ''
                if after_thinking.strip():
                    cleaned = after_thinking.strip()

            if cleaned:
                # 修复UTF-8转义并清理
                cleaned = self._fix_utf8_escapes(cleaned)
                cleaned = self._remove_code_fences(cleaned)
                return cleaned

        # 情况2: 没有思考块，内容直接在text中
        cleaned = text.strip()
        cleaned = self._fix_utf8_escapes(cleaned)
        cleaned = self._remove_code_fences(cleaned)

        return cleaned

    def _remove_code_fences(self, text: str) -> str:
        """移除代码块标记 (```json ... ``` 或 ``` ... ```)"""
        import re
        # 匹配 ```json ... ``` 或 ``` ... ```
        cleaned = re.sub(r'```json\s*(.*?)\s*```', r'\1', text, flags=re.DOTALL)
        cleaned = re.sub(r'```\s*(.*?)\s*```', r'\1', cleaned, flags=re.DOTALL)
        return cleaned.strip()

    def _fix_utf8_escapes(self, text: str) -> str:
        """修复MiniMax返回的UTF-8字节转义序列

        MiniMax有时会在JSON字符串中返回UTF-8字节的转义序列，
        如 \\xe4\\xbd\\xa0 而不是实际的中文字符。
        这会导致JSON解析后中文显示为乱码。
        """
        import re
        # 匹配 \xNN 模式的字节序列（连续多个）
        def replace_escape(match):
            # 获取完整的匹配，如 \xe4\xbd\xa0
            full_match = match.group(0)
            try:
                # 将 \xNN 转换为实际字节
                bytes_list = []
                for i in range(0, len(full_match), 4):  # 4是因为 \xNN
                    hex_part = full_match[i+2:i+4]
                    bytes_list.append(int(hex_part, 16))
                result_bytes = bytes(bytes_list)
                return result_bytes.decode('utf-8')
            except Exception:
                return full_match

        # 匹配连续的反斜杠x十六进制模式
        cleaned = re.sub(r'(?:\\x[0-9a-fA-F]{2})+', replace_escape, text)
        return cleaned

    def _setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger(f"PaperAgent.{self.name}")
        self.logger.setLevel(logging.INFO)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "tools_count": len(self.tools),
            "system_prompt": self.system_prompt
        }
