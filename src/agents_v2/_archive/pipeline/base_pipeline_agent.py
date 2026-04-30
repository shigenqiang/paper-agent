"""
Pipeline Agent基类 - 论文写作流程Agent基础类

设计原则:
1. 每个Agent代表论文写作的一个步骤
2. 输入-处理-输出模式
3. 与MasterSupervisor无缝集成
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import logging
import json

logger = logging.getLogger(__name__)


class PipelineOutput(BaseModel):
    """Pipeline Agent输出"""
    success: bool = Field(..., description="是否成功")
    result: Any = Field(None, description="执行结果")
    agent_name: str = Field(..., description="执行Agent名称")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="输出数据")
    next_agents: List[str] = Field(default_factory=list, description="后续Agent建议")
    quality_score: float = Field(0.0, description="质量评分")
    error: Optional[str] = Field(None, description="错误信息")


# 统一 LLMConfig - 从 base_agent 导入，避免重复定义
from ...core.base_agent import LLMConfig


class PipelineAgentBase(ABC):
    """
    Pipeline Agent基类

    每个Agent代表论文写作流程中的一个步骤:
    1. TopicAgent - 选题
    2. LiteratureAgent - 文献综述
    3. ThesisAgent - Thesis凝练
    4. OutlineAgent - 大纲生成
    5. DraftWriterAgent - 初稿撰写
    6. EditorAgent - 编辑
    7. ReviewerAgent - 评审
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        system_prompt: str = "",
        llm_config: Optional[LLMConfig] = None,
        output_schema: Optional[str] = None
    ):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.llm_config = llm_config or LLMConfig()
        self.output_schema = output_schema
        self._llm = None
        self._init_llm()
        self._setup_logging()

        logger.info(f"PipelineAgent {self.name} initialized")

    @abstractmethod
    async def process(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> PipelineOutput:
        """
        处理输入数据

        Args:
            input_data: 输入数据
            context: 上下文

        Returns:
            PipelineOutput: 包含处理结果和建议的后续Agent
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
                logger.warning(f"Unknown LLM provider: {provider}, using mock")
                self._llm = None

        except Exception as e:
            logger.error(f"LLM initialization failed: {e}")
            self._llm = None

    async def _llm_call(self, prompt: str, schema: Optional[str] = None) -> str:
        """LLM调用封装"""
        if not self._llm:
            return self._mock_response(prompt)

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ]

            response = await self._llm.ainvoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _mock_response(self, prompt: str) -> str:
        """模拟响应（当LLM不可用时）"""
        return json.dumps({
            "result": f"Mock response for {self.name}",
            "status": "simulated"
        })

    def _setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger(f"PipelineAgent.{self.name}")

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> PipelineOutput:
        """执行处理"""
        try:
            result = await self.process(input_data, context)
            result.agent_name = self.name
            return result
        except Exception as e:
            self.logger.error(f"Execute failed: {e}")
            return PipelineOutput(
                success=False,
                result=None,
                agent_name=self.name,
                output_data={},
                next_agents=[],
                quality_score=0.0,
                error=str(e)
            )

    def get_output_schema_prompt(self) -> str:
        """获取输出schema提示"""
        if self.output_schema:
            return f"\n\n请按以下JSON格式输出:\n{self.output_schema}"
        return ""