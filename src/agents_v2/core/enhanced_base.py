"""
学术写作助手 - 增强Agent基类

基于新的架构设计，提供标准化的Agent接口和工具。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import json
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


class AgentCapability(BaseModel):
    """Agent能力描述"""
    task_types: List[str] = Field(..., description="能处理的任务类型")
    description: str = Field(..., description="能力描述")
    input_schema: Optional[Dict] = Field(None, description="输入Schema")
    output_schema: Optional[Dict] = Field(None, description="输出Schema")


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: str = Field(default="openai", description="LLM提供商")
    model_name: str = Field(default="gpt-4", description="模型名称")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=4096, description="最大token数")
    api_key: Optional[str] = Field(None, description="API密钥")
    base_url: Optional[str] = Field(None, description="API基础URL")


# ============ Agent基类 ============

class BaseAgent(ABC):
    """
    学术写作助手Agent基类

    设计原则：
    1. 简化的输入输出格式
    2. 工具注册机制
    3. LLM调用封装
    4. 日志记录
    5. 清晰的能力定义
    6. 质量评分
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
        self.capabilities = self._get_capabilities()
        self._llm = None
        self._init_llm()
        self._setup_logging()

        logger.info(f"Agent {self.name} initialized with {len(self.tools)} tools")

    @abstractmethod
    def _get_capabilities(self) -> AgentCapability:
        """定义Agent的能力"""
        pass

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

    def can_handle(self, task_type: str) -> bool:
        """判断该Agent是否能处理指定类型的任务"""
        return task_type in self.capabilities.task_types

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

    async def think(
        self,
        context: Dict[str, Any],
        prompt_template: str = ""
    ) -> str:
        """
        思考下一步行动 (ReAct模式)

        Args:
            context: 当前上下文
            prompt_template: 提示模板

        Returns:
            思考结果 (JSON格式)
        """
        prompt = prompt_template or self.system_prompt
        prompt += f"""

## 当前状态
{json.dumps(context, ensure_ascii=False, indent=2)}

## 可用工具
{self._format_tools()}

请思考下一步应该采取的行动。输出JSON格式：
{{
    "thought": "你的思考过程",
    "action": "建议的行动",
    "reasoning": "推理依据"
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
                SystemMessage(content=self.system_prompt or "你是一个专业的AI助手。"),
                HumanMessage(content=prompt)
            ]

            response = await self._llm.ainvoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return ""  # 返回空字符串而不是抛出异常

    def _format_tools(self) -> str:
        """格式化工具列表"""
        if not self.tools:
            return "（无工具）"

        lines = []
        for tool in self.tools:
            lines.append(f"- {tool.__name__}: {tool.__doc__ or 'Tool'}")

        return "\n".join(lines)

    def _setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger(f"Agent.{self.name}")
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


# ============ 专业Agent类 ============

class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent - 协调者

    职责：
    - 接收用户请求，解析研究主题
    - 将任务分解并分配给专业Agent
    - 协调Agent之间的通信
    - 控制全局迭代和终止条件
    - 做出最终质量决策
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个学术写作助手的协调者(Supervisor)。
你的职责是：
1. 理解用户的研究需求
2. 制定研究计划
3. 协调各个专业Agent的工作
4. 监控质量并做出决策
5. 控制迭代和终止条件

你需要全面考虑，确保研究的深度和广度。"""
        super().__init__(
            name="supervisor",
            llm_config=llm_config,
            description="学术写作助手协调者",
            system_prompt=system_prompt
        )

    def _get_capabilities(self) -> AgentCapability:
        return AgentCapability(
            task_types=["coordinate", "plan", "decide", "delegate"],
            description="协调各Agent工作，制定研究计划，做出质量决策"
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """协调执行"""
        user_request = input_data.get("user_request", "")
        current_phase = input_data.get("phase", "planning")

        try:
            # 分析用户请求
            analysis = await self._analyze_request(user_request)

            # 制定任务计划
            task_plan = await self._create_task_plan(analysis, current_phase)

            # 确定下一步行动
            next_action = await self._decide_next_action(task_plan, current_phase)

            return AgentOutput(
                success=True,
                result={
                    "analysis": analysis,
                    "task_plan": task_plan,
                    "next_action": next_action,
                    "current_phase": current_phase
                },
                agent_name=self.name,
                reasoning=analysis.get("reasoning", ""),
                next_actions=[next_action],
                quality_score=analysis.get("quality_score", 0.8)
            )

        except Exception as e:
            self.logger.error(f"Supervisor执行失败: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _analyze_request(self, user_request: str) -> Dict[str, Any]:
        """分析用户请求"""
        prompt = f"""
分析以下研究请求：

{user_request}

请输出JSON格式的分析结果：
{{
    "main_topic": "主要研究主题",
    "sub_topics": ["子主题1", "子主题2"],
    "research_depth": "浅/中/深",
    "expected_outcome": "预期产出",
    "constraints": ["约束1", "约束2"],
    "reasoning": "分析推理过程",
    "quality_score": 0.0-1.0
}}
"""
        response = await self._llm_call(prompt)
        try:
            return json.loads(response)
        except:
            return {"main_topic": user_request, "reasoning": "解析失败"}

    async def _create_task_plan(
        self,
        analysis: Dict[str, Any],
        current_phase: str
    ) -> Dict[str, Any]:
        """创建任务计划"""
        prompt = f"""
基于以下分析，创建研究任务计划：

分析结果：{json.dumps(analysis, ensure_ascii=False)}

当前阶段：{current_phase}

请输出JSON格式的任务计划：
{{
    "tasks": [
        {{
            "task_id": "task_1",
            "task_type": "research/analysis/writing/review",
            "description": "任务描述",
            "priority": 1-3,
            "dependencies": []
        }}
    ],
    "estimated_duration": "预计时长",
    "phase_transitions": ["planning -> research -> ..."]
}}
"""
        response = await self._llm_call(prompt)
        try:
            return json.loads(response)
        except:
            return {"tasks": [], "estimated_duration": "未知"}

    async def _decide_next_action(
        self,
        task_plan: Dict[str, Any],
        current_phase: str
    ) -> str:
        """决定下一步行动"""
        # 根据当前阶段决定下一步
        phase_transitions = {
            "planning": "research",
            "research": "analysis",
            "analysis": "review",
            "review": "writing" if task_plan.get("critique_passed") else "research",
            "writing": "completed"
        }
        return phase_transitions.get(current_phase, "completed")


class ResearchPlannerAgent(BaseAgent):
    """
    Research Planner Agent - 规划者

    职责：
    - 分析研究主题，生成多角度搜索策略
    - 确定任务优先级和依赖关系
    - 制定增量处理计划
    - 根据反馈动态调整计划
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个研究规划专家。
你的职责是：
1. 将复杂的研究主题分解为具体的搜索任务
2. 确定搜索优先级和策略
3. 制定增量处理计划
4. 评估搜索结果质量

请生成全面且可执行的搜索计划。"""
        super().__init__(
            name="research_planner",
            llm_config=llm_config,
            description="研究规划专家",
            system_prompt=system_prompt
        )

    def _get_capabilities(self) -> AgentCapability:
        return AgentCapability(
            task_types=["plan_search", "decompose", "prioritize"],
            description="研究规划：分解任务，生成搜索策略"
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """执行规划"""
        query = input_data.get("query", "")
        constraints = input_data.get("constraints", {})

        try:
            # 生成多角度搜索查询
            search_queries = await self._generate_search_queries(query, constraints)

            # 确定任务优先级
            task_queue = await self._prioritize_tasks(search_queries)

            # 创建执行计划
            execution_plan = await self._create_execution_plan(task_queue)

            return AgentOutput(
                success=True,
                result={
                    "search_queries": search_queries,
                    "task_queue": task_queue,
                    "execution_plan": execution_plan
                },
                agent_name=self.name,
                reasoning=f"生成了{len(search_queries)}个搜索查询",
                next_actions=["execute_search"]
            )

        except Exception as e:
            self.logger.error(f"ResearchPlanner执行失败: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _generate_search_queries(
        self,
        query: str,
        constraints: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """生成多角度搜索查询"""
        prompt = f"""
为以下研究主题生成多个搜索角度：

研究主题：{query}
约束条件：{json.dumps(constraints, ensure_ascii=False)}

请生成5-10个不同角度的搜索查询，每个查询应：
1. 覆盖不同的子主题或方面
2. 使用不同的关键词组合
3. 包含同义词和相关术语

输出JSON格式：
{{
    "queries": [
        {{"query": "搜索查询内容", "strategy": "基础/扩展/验证", "aspect": "方法/应用/趋势"}},
        ...
    ]
}}
"""
        response = await self._llm_call(prompt)
        try:
            data = json.loads(response)
            return data.get("queries", [])
        except:
            return [{"query": query, "strategy": "基础", "aspect": "综合"}]

    async def _prioritize_tasks(
        self,
        search_queries: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """确定任务优先级"""
        tasks = []
        for i, q in enumerate(search_queries):
            tasks.append({
                "task_id": f"search_{i}",
                "query": q.get("query"),
                "priority": 1 if i < 3 else 2,  # 前3个高优先级
                "status": "pending",
                "dependencies": []
            })
        return tasks

    async def _create_execution_plan(
        self,
        task_queue: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建执行计划"""
        return {
            "total_tasks": len(task_queue),
            "high_priority_tasks": sum(1 for t in task_queue if t.get("priority") == 1),
            "estimated_batches": (len(task_queue) + 4) // 5,  # 每批5个
            "parallel_execution": True
        }
