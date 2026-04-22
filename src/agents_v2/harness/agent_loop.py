"""ReAct循环引擎 - Agent的核心引擎"""
import logging
from typing import Any, Dict, List, Optional, Callable
import time

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage
)

from ..models.state import AgentContext, AgentState, ToolCall
from .base_agent import BaseAgent, VirtualTool

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        agent: BaseAgent,
        llm,
        system_prompt: Optional[str] = None,
        max_iterations: int = 20
    ):
        self.agent = agent
        self.llm = llm
        self.system_prompt = system_prompt or agent.system_prompt
        self.max_iterations = max_iterations

        # 工具处理器
        self.tool_handlers: Dict[str, Callable] = {}

        # 统计信息
        self.stats = {
            "total_iterations": 0,
            "total_tool_calls": 0,
            "total_tokens": 0,
            "total_time_ms": 0
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
        # 初始化消息
        messages = self._build_initial_messages(context)

        logger.info(f"Starting ReAct loop for {self.agent.name}")
        logger.info(f"Task: {context.task_type} - {context.task_description}")

        # ReAct循环
        iteration = 0
        start_time = time.time()

        while iteration < self.max_iterations and context.should_continue():
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

        # 返回结果
        return {
            "success": True,
            "final_response": messages[-1].content if messages else None,
            "messages": [msg.content for msg in messages],
            "stats": self.stats,
            "iterations": iteration,
            "tool_calls": len([call for call in context.tool_calls if call.duration_ms])
        }

    def _build_initial_messages(self, context: AgentContext) -> List:
        """构建初始消息列表"""
        messages = []

        # 系统消息
        if self.system_prompt:
            messages.append(SystemMessage(content=self.system_prompt))

        # 用户任务消息
        task_prompt = self._build_task_prompt(context)
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

    def _build_task_prompt(self, context: AgentContext) -> str:
        """构建任务提示词"""
        prompt_parts = [
            f"## 任务",
            f"任务ID: {context.task_id}",
            f"任务类型: {context.task_type}",
            f"任务描述: {context.task_description}",
        ]

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
            # 准备工具列表
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
                # 执行工具
                handler = self.tool_handlers.get(tool_name)
                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(**arguments)
                    else:
                        result = handler(**arguments)
                    tool_call_record.result = result
                    tool_call_record.error = None
                else:
                    raise ValueError(f"Tool handler not found: {tool_name}")

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


# 导入支持
import asyncio
