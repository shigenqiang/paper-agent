"""
问题导向Agent基类 - 针对论文写作常见困难

设计原则：
1. 每个Agent针对一个具体问题
2. 输入-诊断-输出模式
3. 明确的改进建议
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import logging
import json
import os

logger = logging.getLogger(__name__)


class AgentOutput(BaseModel):
    """Agent输出"""
    success: bool = Field(..., description="是否成功")
    result: Any = Field(None, description="执行结果")
    agent_name: str = Field(..., description="执行Agent名称")
    diagnosed_issues: List[str] = Field(default_factory=list, description="诊断出的问题")
    recommendations: List[str] = Field(default_factory=list, description="改进建议")
    quality_score: float = Field(0.0, description="质量评分")
    error: Optional[str] = Field(None, description="错误信息")


# 统一 LLMConfig - 从 base_agent 导入，避免重复定义
from ..core.base_agent import LLMConfig


class ProblemAgentBase(ABC):
    """
    问题导向Agent基类

    每个Agent针对论文写作中的一个具体困难：
    1. 诊断问题
    2. 分析原因
    3. 提供改进建议
    """

    def __init__(
        self,
        name: str,
        target_problem: str,
        llm_config: Optional[LLMConfig] = None,
        description: str = "",
        system_prompt: str = ""
    ):
        self.name = name
        self.target_problem = target_problem
        self.description = description
        self.system_prompt = system_prompt
        self.llm_config = llm_config or LLMConfig()
        self._llm = None
        self._init_llm()
        self._setup_logging()

        logger.info(f"ProblemAgent {self.name} initialized, targeting: {target_problem}")

    @abstractmethod
    async def diagnose(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentOutput:
        """
        诊断问题

        Args:
            input_data: 输入数据
            context: 上下文

        Returns:
            AgentOutput: 包含诊断结果和改进建议
        """
        pass

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentOutput:
        """
        执行诊断 (与MasterSupervisor接口兼容)

        实际调用diagnose方法

        Args:
            input_data: 输入数据
            context: 上下文

        Returns:
            AgentOutput: 包含诊断结果和改进建议
        """
        return await self.diagnose(input_data, context)

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
                    base_url=base_url
                )
            elif provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                self._llm = ChatAnthropic(
                    model=self.llm_config.model_name,
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens,
                    api_key=api_key
                )
            else:
                raise ValueError(f"不支持的LLM提供商: {provider}")

        except Exception as e:
            logger.error(f"LLM初始化失败: {e}")
            self._llm = None

    async def _llm_call(self, prompt: str) -> str:
        """LLM调用封装"""
        cls_name = self.__class__.__name__

        if not self._llm:
            logger.warning(f"[{cls_name}:134] LLM未初始化，尝试重新初始化...")
            self._init_llm()
            if not self._llm:
                logger.error(f"[{cls_name}:138] LLM重试初始化后仍失败")
                raise RuntimeError("LLM未初始化")

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=self.system_prompt or "你是一个专业的学术写作助手。"),
                HumanMessage(content=prompt)
            ]

            logger.info(f"[{cls_name}:148] LLM调用开始，prompt长度={len(prompt)}")
            response = await self._llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            logger.info(f"[{cls_name}:153] LLM返回内容长度={len(content) if content else 0}")

            # 清理MiniMax模型的思考块
            content = self._clean_thinking_blocks(content)

            if not content or not content.strip():
                logger.error(f"[{cls_name}:160] LLM返回空内容，response类型={type(response)}")
                raise ValueError(f"[{cls_name}:160] LLM返回空内容，无法解析JSON")

            return content
        except ValueError:
            raise  # 重新抛出ValueError，保留原始堆栈
        except Exception as e:
            logger.error(f"[{cls_name}:165] LLM调用失败: {type(e).__name__}: {e}")
            raise ValueError(f"[{cls_name}:165] LLM调用失败: {type(e).__name__}: {e}") from e

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
        self.logger = logging.getLogger(f"ProblemAgent.{self.name}")

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentOutput:
        """执行诊断"""
        try:
            return await self.diagnose(input_data, context)
        except Exception as e:
            self.logger.error(f"Execute failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=[str(e)],
                recommendations=[],
                quality_score=0.0,
                error=str(e)
            )
