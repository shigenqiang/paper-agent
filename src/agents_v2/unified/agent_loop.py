"""ReAct循环引擎 - Agent的核心引擎"""
from src.agents_v2.logging_config import get_logging_logger

import asyncio

import inspect
from typing import Any, Dict, List, Optional, Callable, TYPE_CHECKING
import time

if TYPE_CHECKING:
    from ..memory.hierarchical_memory import HierarchicalMemory

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage
)

from src.models.state import AgentContext, AgentState, ToolCall
from ..core.base_agent import BaseAgent, VirtualTool
from ..tools.registry import ToolRegistry, get_tool_registry

logger = get_logging_logger(__name__)


class TerminationCondition:
    """终止条件基类"""

    def is_met(self, context: 'AgentContext', iteration: int) -> bool:
        """检查是否满足终止条件"""
        raise NotImplementedError


class MaxIterationsCondition(TerminationCondition):
    """最大迭代次数终止条件"""

    def __init__(self, max_iterations: int):
        self.max_iterations = max_iterations

    def is_met(self, context: 'AgentContext', iteration: int) -> bool:
        return iteration >= self.max_iterations


class TimeoutCondition(TerminationCondition):
    """超时终止条件"""

    def __init__(self, timeout_seconds: float):
        self.timeout_seconds = timeout_seconds
        self.start_time: Optional[float] = None

    def start(self):
        self.start_time = time.time()

    def is_met(self, context: 'AgentContext', iteration: int) -> bool:
        if self.start_time is None:
            return False
        elapsed = time.time() - self.start_time
        return elapsed >= self.timeout_seconds


class QualityThresholdCondition(TerminationCondition):
    """质量阈值终止条件"""

    def __init__(self, threshold: float):
        self.threshold = threshold

    def is_met(self, context: 'AgentContext', iteration: int) -> bool:
        score = context.metadata.get("quality_score", 0) if context.metadata else 0
        return score >= self.threshold


class CancellationToken:
    """取消令牌"""

    def __init__(self):
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled


# CoT引导前缀 - 统一思维链提示
COT_GUIDANCE = """
## 思维链引导

回答时，请先进行逐步推理（Chain-of-Thought）：

1. **理解任务目标** - 明确需要完成什么
2. **分析当前状态** - 了解已有信息和限制条件
3. **制定执行计划** - 规划需要调用的工具和顺序
4. **逐步执行验证** - 每步完成后验证结果是否正确
5. **反思调整** - 如遇问题，思考替代方案

【重要】在调用工具前，先在脑海中形成解决思路。
"""

# Few-shot示例模板
FEW_SHOT_EXAMPLES = """
## 示例参考

以下是对话示例，帮助你理解任务的期望格式和质量标准：

### 示例1：主题选择
用户：我想研究人工智能在教育领域的应用
思考：
- 用户需求较宽泛，需要聚焦到具体问题
- 可以考虑AI+教育的技术结合点：智能辅导、自适应学习、教育机器人
- 需要评估创新性和可行性
输出：{{"title": "基于大语言模型的智能辅导系统研究", "feasibility": 0.85, ...}}

### 示例2：文献搜索
用户：搜索深度学习优化方法的最新进展
思考：
- 需要使用搜索工具查找最新论文
- 关键词：深度学习、优化方法、2024
- 需要筛选高质量论文（顶会、顶刊）
输出：{{"papers": [...], "total": 15, "gaps": [...]}}
"""


class AgentLoop:
    """
    ReAct循环引擎 - Agent的核心

    设计原则 (来自Nanobot + Learn Claude Code s01):
    1. 最小循环: Observation → Reasoning → Action
    2. LLM驱动: 让模型决定何时调用工具
    3. 清晰的终止条件
    4. 工具结果反馈到上下文
    5. 迭代次数限制

    核心代码 (最小循环):
    ```
    while True:
        response = llm.chat(messages, tools=tools)

        if response.stop_reason != "tool_use":
            return  # 回复用户

        results = execute_tools(response.tool_calls)
        messages.append(tool_results)
        # 继续循环
    ```
    """

    # 类级别的CoT和Few-shot配置
    enable_cot_guidance: bool = True
    enable_few_shot: bool = True

    def __init__(
        self,
        agent: BaseAgent,
        llm,
        system_prompt: Optional[str] = None,
        max_iterations: int = 20,
        timeout_seconds: Optional[float] = None,
        tool_registry: Optional[ToolRegistry] = None,
        memory: Optional[HierarchicalMemory] = None,
        termination_conditions: Optional[List[TerminationCondition]] = None,
        enable_cot: bool = True,
        enable_fewshot: bool = True
    ):
        self.agent = agent
        self.llm = llm
        self.system_prompt = system_prompt or agent.system_prompt
        self.max_iterations = max_iterations
        self.timeout_seconds = timeout_seconds

        # 提示词优化开关
        self.enable_cot = enable_cot
        self.enable_fewshot = enable_fewshot

        # 工具注册表（可选，用于统一管理工具）
        self.tool_registry = tool_registry

        # 分层记忆系统（可选）
        self.memory = memory

        # 工具处理器（兼容性保留）
        self.tool_handlers: Dict[str, Callable] = {}

        # 终止条件
        self.termination_conditions = termination_conditions or []
        self._timeout_condition = TimeoutCondition(timeout_seconds) if timeout_seconds else None
        if self._timeout_condition:
            self.termination_conditions.append(self._timeout_condition)

        # 取消令牌
        self.cancellation_token = CancellationToken()

        # 暂停控制
        self._paused = False
        self._pause_event = asyncio.Event() if asyncio else None

        # 统计信息
        self.stats = {
            "total_iterations": 0,
            "total_tool_calls": 0,
            "total_tokens": 0,
            "total_time_ms": 0,
            "memory_hits": 0,
            "memory_misses": 0,
            "termination_reason": None
        }

        self._setup_handlers()

    def register_tool_handler(self, tool_name: str, handler: Callable):
        """注册工具处理器"""
        self.tool_handlers[tool_name] = handler
        logger.info(f"Registered tool handler: {tool_name}")

    def _setup_handlers(self):
        """设置默认工具处理器"""
        # 从Agent的工具列表中注册处理器
        for tool in self.agent.tools:
            if tool.name not in self.tool_handlers:
                # 创建默认处理器
                self.tool_handlers[tool.name] = self._create_default_handler(tool.name)

        # 从工具注册表中注册处理器（如果有）
        if self.tool_registry:
            for tool_name in self.tool_registry.list_tools():
                if tool_name not in self.tool_handlers:
                    spec = self.tool_registry.get(tool_name)
                    if spec and spec.handler:
                        self.tool_handlers[tool_name] = spec.handler

    def _create_default_handler(self, tool_name: str) -> Callable:
        """创建默认工具处理器"""
        async def handler(**kwargs):
            logger.warning(f"No handler registered for tool: {tool_name}")
            return {"error": f"Tool {tool_name} not implemented"}

        return handler

    async def run(
        self,
        context: AgentContext,
        agent_state: Optional[AgentState] = None
    ) -> Dict[str, Any]:
        """
        运行ReAct循环

        Args:
            context: Agent上下文
            agent_state: Agent状态（可选）

        Returns:
            执行结果字典
        """
        # 1. 从记忆系统获取相关上下文
        if self.memory:
            # 获取任务相关的历史上下文
            relevant_context = self._get_relevant_memory(context)
            if relevant_context:
                messages = self._build_initial_messages(context, relevant_context)
            else:
                messages = self._build_initial_messages(context)
        else:
            messages = self._build_initial_messages(context)

        logger.info(f"Starting ReAct loop for {self.agent.name}")
        logger.info(f"Task: {context.task_type} - {context.task_description}")

        # ReAct循环
        iteration = 0
        start_time = time.time()

        # 启动超时计时器
        if self._timeout_condition:
            self._timeout_condition.start()

        while True:
            # 检查终止条件
            if self._check_termination(iteration, context):
                break

            # 检查取消
            if self.cancellation_token.is_cancelled:
                self.stats["termination_reason"] = "cancelled"
                logger.info("Agent loop cancelled")
                break

            # 暂停检查
            if self._paused:
                logger.info("Agent loop paused, waiting...")
                await self._pause_event.wait()
                if self.cancellation_token.is_cancelled:
                    break

            iteration += 1
            logger.info(f"Iteration {iteration}/{self.max_iterations}")

            # 1. Reasoning - 调用LLM
            response = await self._llm_invoke(messages, context)
            self.stats["total_iterations"] += 1

            # 添加AI消息到上下文
            messages.append(AIMessage(content=response.content))

            # 2. 判断是否需要行动
            if not self._should_use_tools(response):
                # LLM决定回复用户，结束循环
                logger.info(f"LLM decided to respond (no tool use)")
                self.stats["termination_reason"] = "llm_response"
                break

            # 3. Action - 执行工具
            tool_results = await self._execute_tools(response, context, agent_state)
            self.stats["total_tool_calls"] += len(tool_results)

            # 添加工具结果到消息
            for result in tool_results:
                messages.append(ToolMessage(
                    content=result["content"],
                    tool_call_id=result["tool_call_id"]
                ))

            # 更新上下文
            context.increment_iteration()

            # 更新Agent状态
            if agent_state:
                agent_state.current_step = f"iteration_{iteration}"

        # 计算总时长
        total_time = (time.time() - start_time) * 1000
        self.stats["total_time_ms"] = total_time
        if not self.stats["termination_reason"]:
            self.stats["termination_reason"] = "completed"

        # 4. 存储结果到记忆系统
        if self.memory:
            self._store_to_memory(context, agent_state)

        # 返回结果
        return {
            "success": True,
            "final_response": messages[-1].content if messages else None,
            "messages": [msg.content for msg in messages],
            "stats": self.stats,
            "iterations": iteration,
            "tool_calls": len([call for call in context.tool_calls if call.duration_ms]),
            "termination_reason": self.stats["termination_reason"]
        }

    def _check_termination(self, iteration: int, context: AgentContext) -> bool:
        """检查是否满足终止条件"""
        # 迭代次数检查
        if iteration >= self.max_iterations:
            self.stats["termination_reason"] = "max_iterations"
            logger.warning(f"Max iterations ({self.max_iterations}) reached")
            return True

        # 超时检查
        if self._timeout_condition and self._timeout_condition.is_met(context, iteration):
            self.stats["termination_reason"] = "timeout"
            logger.warning(f"Timeout ({self.timeout_seconds}s) reached")
            return True

        # 其他终止条件
        for condition in self.termination_conditions:
            if isinstance(condition, (MaxIterationsCondition, TimeoutCondition)):
                continue  # 已处理
            if condition.is_met(context, iteration):
                self.stats["termination_reason"] = type(condition).__name__
                logger.info(f"Termination condition met: {type(condition).__name__}")
                return True

        return False

    def pause(self):
        """暂停循环"""
        self._paused = True
        logger.info("Agent loop paused")

    def resume(self):
        """恢复循环"""
        self._paused = False
        self._pause_event.set()
        logger.info("Agent loop resumed")

    def stop(self):
        """停止循环（发送取消信号）"""
        self.cancellation_token.cancel()
        if self._paused:
            self.resume()  # 唤醒等待的协程
        logger.info("Agent loop stop requested")

    def _get_relevant_memory(self, context: AgentContext) -> Optional[Dict[str, Any]]:
        """从记忆系统获取相关上下文"""
        if not self.memory:
            return None

        try:
            # 尝试通过任务ID检索
            cached = self.memory.recall(f"task_{context.task_id}")
            if cached:
                self.stats["memory_hits"] += 1
                return cached

            # 尝试通过任务类型检索
            similar = self.memory.search(context.task_type, limit=3)
            if similar:
                self.stats["memory_hits"] += 1
                return {"similar_tasks": [s.value for s in similar]}

            self.stats["memory_misses"] += 1
        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}")
            self.stats["memory_misses"] += 1

        return None

    def _store_to_memory(
        self,
        context: AgentContext,
        agent_state: Optional[AgentState]
    ) -> None:
        """存储执行结果到记忆系统"""
        if not self.memory:
            return

        try:
            # 存储任务结果
            task_key = f"task_{context.task_id}"
            result_data = {
                "task_id": context.task_id,
                "task_type": context.task_type,
                "task_description": context.task_description,
                "iterations": context.iteration_count,
                "tool_calls": [tc.tool_name for tc in context.tool_calls],
                "success": agent_state.status == "completed" if agent_state else True
            }

            # 存储到短期记忆
            self.memory.remember(
                key=task_key,
                value=result_data,
                tags=[context.task_type, "task_result"]
            )

            # 如果任务成功，持久化到长期记忆
            if agent_state and agent_state.status == "completed":
                self.memory.remember(
                    key=task_key,
                    value=result_data,
                    tags=[context.task_type, "task_result"],
                    persist=True
                )

            logger.debug(f"Stored result to memory: {task_key}")
        except Exception as e:
            logger.warning(f"Memory storage failed: {e}")

    def _build_initial_messages(
        self,
        context: AgentContext,
        relevant_context: Optional[Dict[str, Any]] = None
    ) -> List:
        """构建初始消息列表"""
        messages = []

        # 系统消息 - 组合基础prompt + CoT引导 + Few-shot示例
        prompt_parts = []

        if self.system_prompt:
            prompt_parts.append(self.system_prompt)

        # 添加CoT思维链引导
        if self.enable_cot and hasattr(self, 'enable_cot') and self.enable_cot:
            prompt_parts.append(COT_GUIDANCE)

        # 添加Few-shot示例
        if self.enable_fewshot and hasattr(self, 'enable_fewshot') and self.enable_fewshot:
            prompt_parts.append(FEW_SHOT_EXAMPLES)

        if prompt_parts:
            messages.append(SystemMessage(content="\n\n".join(prompt_parts)))

        # 用户任务消息
        task_prompt = self._build_task_prompt(context, relevant_context)
        messages.append(HumanMessage(content=task_prompt))

        # 添加历史消息
        for msg in context.messages:
            if msg.role == "system":
                messages.append(SystemMessage(content=msg.content))
            elif msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
            elif msg.role == "tool":
                messages.append(ToolMessage(content=msg.content))

        return messages

    def _build_task_prompt(
        self,
        context: AgentContext,
        relevant_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建任务提示词"""
        prompt_parts = [
            f"## 任务",
            f"任务ID: {context.task_id}",
            f"任务类型: {context.task_type}",
            f"任务描述: {context.task_description}",
        ]

        # 添加记忆中的相关上下文
        if relevant_context:
            if "similar_tasks" in relevant_context:
                prompt_parts.append("\n## 相关历史任务")
                for i, task in enumerate(relevant_context["similar_tasks"][:3], 1):
                    prompt_parts.append(f"- 任务{i}: {task.get('task_description', 'N/A')}")
            elif "task_id" in relevant_context:
                # 直接复用之前的任务结果
                prompt_parts.append("\n## 历史上下文")
                prompt_parts.append(f"之前的任务结果: {relevant_context}")

        if context.metadata:
            prompt_parts.append(f"\n## 任务元数据")
            for key, value in context.metadata.items():
                prompt_parts.append(f"{key}: {value}")

        # 添加可用工具
        if self.agent.tools:
            prompt_parts.append(f"\n## 可用工具")
            for tool in self.agent.tools:
                prompt_parts.append(f"- {tool.name}: {tool.description}")

        return "\n".join(prompt_parts)

    async def _llm_invoke(self, messages: List, context: AgentContext) -> Any:
        """调用LLM"""
        try:
            # 准备工具列表：优先使用注册表，否则使用agent的
            if self.tool_registry:
                tools = self.tool_registry.get_schemas()
            else:
                tools = self.agent.get_tool_schemas()

            # 调用LLM
            response = await self.llm.ainvoke(messages, tools=tools)

            # 记录token使用（如果可用）
            if hasattr(response, 'usage_metadata'):
                self.stats["total_tokens"] += response.usage_metadata.get('total_tokens', 0)

            return response
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            raise

    def _should_use_tools(self, response) -> bool:
        """判断LLM是否决定使用工具"""
        # 检查response是否有tool_calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            return len(response.tool_calls) > 0

        # 检查content中的tool_use标记
        if hasattr(response, 'stop_reason'):
            return response.stop_reason == "tool_use"

        return False

    async def _execute_tools(
        self,
        response,
        context: AgentContext,
        agent_state: Optional[AgentState]
    ) -> List[Dict[str, Any]]:
        """执行LLM请求的工具调用"""
        results = []

        # 获取工具调用列表
        tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []

        for tool_call in tool_calls:
            tool_name = tool_call.name
            arguments = tool_call.input

            logger.info(f"Executing tool: {tool_name} with args: {arguments}")

            # 记录工具调用
            tool_call_record = ToolCall(
                tool_name=tool_name,
                arguments=arguments
            )

            start_time = time.time()

            try:
                # 优先使用注册表执行，否则使用handler
                if self.tool_registry and tool_name in self.tool_registry.list_tools():
                    # 使用注册表执行（带验证）
                    exec_result = await self.tool_registry.execute(tool_name, arguments)
                    if exec_result.success:
                        result = exec_result.result
                        tool_call_record.error = None
                    else:
                        raise ValueError(exec_result.error)
                else:
                    # 使用handler执行
                    handler = self.tool_handlers.get(tool_name)
                    if handler:
                        if inspect.iscoroutinefunction(handler):
                            result = await handler(**arguments)
                        else:
                            result = handler(**arguments)
                    else:
                        raise ValueError(f"Tool handler not found: {tool_name}")

                tool_call_record.result = result

                # 添加到结果列表
                results.append({
                    "content": str(result),
                    "tool_call_id": tool_call.id
                })

                # 更新上下文
                context.add_tool_call(tool_name, arguments, result)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Tool execution failed: {tool_name} - {error_msg}")
                tool_call_record.error = error_msg
                results.append({
                    "content": f"Error: {error_msg}",
                    "tool_call_id": tool_call.id
                })

                # 更新Agent状态
                if agent_state:
                    agent_state.add_error(f"Tool {tool_name} failed: {error_msg}")

            finally:
                # 记录执行时长
                tool_call_record.duration_ms = (time.time() - start_time) * 1000
                context.tool_calls.append(tool_call_record)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取循环统计信息"""
        return self.stats.copy()


class VirtualToolLoop(AgentLoop):
    """
    带虚拟工具支持的Agent循环

    虚拟工具用途：
    - 强制LLM输出特定格式的JSON
    - 类型验证
    - Schema约束

    来自Nanobot的设计
    """

    def __init__(self, agent: BaseAgent, llm, virtual_tools: List[Dict] = None):
        super().__init__(agent, llm)

        # 虚拟工具列表（不实际执行）
        self.virtual_tools = virtual_tools or []

    async def run_with_virtual_tool(
        self,
        context: AgentContext,
        virtual_tool_name: str,
        virtual_tool_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        运行循环并收集虚拟工具的输出

        Args:
            context: Agent上下文
            virtual_tool_name: 虚拟工具名称
            virtual_tool_schema: 虚拟工具Schema

        Returns:
            包含虚拟工具输出的结果
        """
        # 构建初始消息
        messages = self._build_initial_messages(context)

        # 添加虚拟工具到工具列表
        all_tools = self.agent.get_tool_schemas() + [virtual_tool_schema]

        # 运行单次LLM调用（获取虚拟工具的输出）
        response = await self.llm.ainvoke(messages, tools=all_tools)

        # 提取虚拟工具的输出
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.name == virtual_tool_name:
                    return {
                        "success": True,
                        "virtual_tool_output": tool_call.input,
                        "full_response": response
                    }

        return {
            "success": False,
            "error": "Virtual tool not called"
        }
