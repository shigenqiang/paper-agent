"""
ReAct Executor - ReAct执行器

实现详细的思考-行动-观察循环 (Thought -> Action -> Observation)

每轮执行:
1. Thought: 分析当前状态，决定下一步
2. Action: 执行行动（工具调用或LLM生成）
3. Observation: 观察结果，更新状态
4. 判断是否继续或结束
"""
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from src.agents_v2.logging_config import get_logging_logger

import time

logger = get_logging_logger(__name__)


class ActionType(str, Enum):
    """行动类型"""
    TOOL_CALL = "tool_call"
    LLM_GENERATE = "llm_generate"
    FINAL_ANSWER = "final_answer"
    WAIT_INPUT = "wait_input"


@dataclass
class ThoughtStep:
    """思考步骤"""
    iteration: int
    thought: str
    confidence: float
    reasoning: str = ""


@dataclass
class ActionStep:
    """行动步骤"""
    iteration: int
    action_type: ActionType
    tool_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Any = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class ObservationStep:
    """观察步骤"""
    iteration: int
    observation: str
    state_update: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FinishStep:
    """完成步骤"""
    iteration: int
    final_answer: Any
    quality_score: float = 1.0


@dataclass
class ReActResult:
    """ReAct执行结果"""
    success: bool
    final_answer: Any = None
    trace: List[Any] = field(default_factory=list)
    iterations: int = 0
    total_time_ms: float = 0.0
    error: Optional[str] = None
    quality_score: float = 0.0


@dataclass
class Thought:
    """思考结果"""
    reasoning: str
    confidence: float
    next_action: "NextAction"


@dataclass
class NextAction:
    """下一步行动"""
    type: ActionType
    tool_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    answer: Optional[Any] = None


class ReActExecutor:
    """
    ReAct执行器

    实现详细的思考-行动-观察循环

    使用示例:
        executor = ReActExecutor(
            agent=my_agent,
            max_iterations=10,
            max_tool_calls=5
        )

        result = await executor.execute(
            task="帮我写一篇关于深度学习的论文",
            context={"topic": "深度学习"}
        )

        print(f"Final answer: {result.final_answer}")
        print(f"Iterations: {result.iterations}")
    """

    def __init__(
        self,
        agent: Any,
        max_iterations: int = 10,
        max_tool_calls: int = 5,
        thought_model: Optional[str] = None
    ):
        """
        初始化ReAct执行器

        Args:
            agent: Agent实例
            max_iterations: 最大迭代次数
            max_tool_calls: 最大工具调用次数
            thought_model: 用于思考的模型（可选，默认使用主模型）
        """
        self.agent = agent
        self.max_iterations = max_iterations
        self.max_tool_calls = max_tool_calls
        self.thought_model = thought_model

        self._tool_call_count = 0

    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        callbacks: Optional[Dict[str, Callable]] = None
    ) -> ReActResult:
        """
        执行ReAct循环

        Args:
            task: 任务描述
            context: 执行上下文
            callbacks: 回调函数

        Returns:
            ReActResult: 包含完整的执行轨迹
        """
        start_time = time.time()
        self._tool_call_count = 0

        trace = []
        current_state = {
            "task": task,
            "observations": [],
            "context": context or {},
            "next_action": None
        }

        callbacks = callbacks or {}

        for iteration in range(self.max_iterations):
            try:
                # 1. Thought阶段
                thought = await self._think(current_state, context)
                trace.append(ThoughtStep(
                    iteration=iteration,
                    thought=thought.reasoning,
                    confidence=thought.confidence
                ))

                # 触发思考回调
                if "on_thought" in callbacks:
                    callbacks["on_thought"](thought)

                # 2. 决定行动
                if thought.next_action.type == ActionType.TOOL_CALL:
                    # 工具调用
                    action_result = await self._execute_tool(
                        thought.next_action.tool_name,
                        thought.next_action.parameters
                    )

                    trace.append(ActionStep(
                        iteration=iteration,
                        action_type=ActionType.TOOL_CALL,
                        tool_name=thought.next_action.tool_name,
                        parameters=thought.next_action.parameters,
                        result=action_result.get("result"),
                        success=action_result.get("success", True)
                    ))

                    self._tool_call_count += 1

                    # 3. Observation
                    observation = self._process_observation(action_result)
                    current_state["observations"].append(observation)
                    trace.append(ObservationStep(
                        iteration=iteration,
                        observation=observation
                    ))

                    if "on_observation" in callbacks:
                        callbacks["on_observation"](observation)

                elif thought.next_action.type == ActionType.FINAL_ANSWER:
                    # 完成
                    trace.append(FinishStep(
                        iteration=iteration,
                        final_answer=thought.next_action.answer,
                        quality_score=self._estimate_answer_quality(thought.next_action.answer)
                    ))

                    total_time_ms = (time.time() - start_time) * 1000

                    return ReActResult(
                        success=True,
                        final_answer=thought.next_action.answer,
                        trace=trace,
                        iterations=iteration + 1,
                        total_time_ms=total_time_ms,
                        quality_score=self._estimate_answer_quality(thought.next_action.answer)
                    )

                elif thought.next_action.type == ActionType.WAIT_INPUT:
                    # 等待输入
                    trace.append(ActionStep(
                        iteration=iteration,
                        action_type=ActionType.WAIT_INPUT,
                        result="Waiting for user input"
                    ))

                # 检查是否超时或达到最大调用次数
                if self._tool_call_count >= self.max_tool_calls:
                    logger.info(f"Max tool calls ({self.max_tool_calls}) reached")
                    break

            except Exception as e:
                logger.error(f"Error in iteration {iteration}: {e}")
                trace.append(ActionStep(
                    iteration=iteration,
                    action_type=ActionType.LLM_GENERATE,
                    success=False,
                    error=str(e)
                ))

                # 如果是致命错误，提前结束
                if self._is_fatal_error(e):
                    break

        # 达到最大迭代
        final_answer = current_state["observations"][-1] if current_state["observations"] else None
        total_time_ms = (time.time() - start_time) * 1000

        return ReActResult(
            success=False,
            final_answer=final_answer,
            trace=trace,
            iterations=self.max_iterations,
            total_time_ms=total_time_ms,
            error="Max iterations exceeded"
        )

    async def _think(
        self,
        state: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Thought:
        """
        思考下一步行动

        使用专门的小模型进行快速决策
        大模型只在关键节点使用
        """
        prompt = self._build_thinking_prompt(state, context)

        # 调用LLM
        response = await self._call_llm(prompt)

        return self._parse_thought(response)

    def _build_thinking_prompt(
        self,
        state: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """构建思考提示"""
        recent_observations = state["observations"][-3:] if state["observations"] else []

        observations_text = "无"
        if recent_observations:
            observations_text = "\n".join([f"- {obs}" for obs in recent_observations])

        tools_text = self._format_available_tools()

        return f"""分析以下任务并决定下一步行动:

当前任务: {state['task']}

最近的观察结果:
{observations_text}

可用工具:
{tools_text}

请决定下一步行动。考虑：
1. 当前最需要什么信息？
2. 是否有足够的信息生成答案？
3. 应该使用哪个工具？

请用JSON格式回复:
{{
    "reasoning": "你的思考过程",
    "confidence": 0.0-1.0之间的置信度,
    "next_action": {{
        "type": "tool_call" | "final_answer" | "wait_input",
        "tool_name": "工具名称（如果是tool_call）",
        "parameters": {{...}}（如果是tool_call）,
        "answer": "最终答案（如果是final_answer）"
    }}
}}
"""

    def _format_available_tools(self) -> str:
        """格式化可用工具列表"""
        if not hasattr(self.agent, 'tools') or not self.agent.tools:
            return "（无工具可用）"

        lines = []
        for tool in self.agent.tools:
            lines.append(f"- {tool.name}: {tool.description}")

        return "\n".join(lines)

    async def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        if hasattr(self.agent, 'llm') and self.agent.llm:
            try:
                response = await self.agent.llm.ainvoke(prompt)
                return response.content if hasattr(response, 'content') else str(response)
            except Exception as e:
                logger.warning(f"LLM call failed: {e}")
                return ""

        # 如果没有LLM，返回默认值
        return '{"reasoning": "No LLM available", "confidence": 0.5, "next_action": {"type": "final_answer", "answer": null}}'

    def _parse_thought(self, response: str) -> Thought:
        """解析思考响应"""
        import json

        try:
            # 尝试解析JSON
            data = json.loads(response)

            action_type_str = data.get("next_action", {}).get("type", "final_answer")
            action_type = ActionType(action_type_str)

            next_action = NextAction(
                type=action_type,
                tool_name=data.get("next_action", {}).get("tool_name"),
                parameters=data.get("next_action", {}).get("parameters"),
                answer=data.get("next_action", {}).get("answer")
            )

            return Thought(
                reasoning=data.get("reasoning", ""),
                confidence=data.get("confidence", 0.5),
                next_action=next_action
            )

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse thought response: {e}")

            # 返回默认思考
            return Thought(
                reasoning="Failed to parse LLM response",
                confidence=0.0,
                next_action=NextAction(type=ActionType.FINAL_ANSWER, answer=None)
            )

    async def _execute_tool(
        self,
        tool_name: str,
        parameters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """执行工具"""
        if not tool_name:
            return {"success": False, "error": "No tool specified"}

        try:
            # 查找工具
            tool = self._find_tool(tool_name)
            if not tool:
                return {"success": False, "error": f"Tool not found: {tool_name}"}

            # 执行工具
            if hasattr(tool, 'ainvoke'):
                result = await tool.ainvoke(parameters or {})
            elif hasattr(tool, 'invoke'):
                result = tool.invoke(parameters or {})
            else:
                result = tool(parameters or {})

            return {
                "success": True,
                "result": result,
                "tool_name": tool_name
            }

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name
            }

    def _find_tool(self, tool_name: str) -> Optional[Any]:
        """查找工具"""
        if not hasattr(self.agent, 'tools') or not self.agent.tools:
            return None

        for tool in self.agent.tools:
            if hasattr(tool, 'name') and tool.name == tool_name:
                return tool
            if hasattr(tool, '__name__') and tool.__name__ == tool_name:
                return tool

        return None

    def _process_observation(self, action_result: Dict[str, Any]) -> str:
        """处理观察结果"""
        if not action_result.get("success", False):
            return f"Error: {action_result.get('error', 'Unknown error')}"

        result = action_result.get("result")
        if result is None:
            return "No result"

        if isinstance(result, str):
            return result[:500] + "..." if len(str(result)) > 500 else str(result)
        else:
            return f"Result received: {type(result).__name__}"

    def _estimate_answer_quality(self, answer: Any) -> float:
        """估计答案质量"""
        if answer is None:
            return 0.0

        if isinstance(answer, str):
            if len(answer) > 100:
                return 0.7
            elif len(answer) > 50:
                return 0.5
            else:
                return 0.3

        if isinstance(answer, dict):
            if len(answer) > 5:
                return 0.7
            elif len(answer) > 0:
                return 0.5

        return 0.5

    def _is_fatal_error(self, error: Exception) -> bool:
        """判断是否是致命错误"""
        fatal_errors = (
            KeyboardInterrupt,
            SystemExit,
            MemoryError
        )
        return isinstance(error, fatal_errors)


class SimpleReActExecutor:
    """
    简化版ReAct执行器

    用于不需要完整ReAct循环的简单场景
    """

    def __init__(self, agent: Any):
        self.agent = agent

    async def execute_simple(
        self,
        task: str,
        tools: Optional[List[Callable]] = None
    ) -> Dict[str, Any]:
        """
        简单执行

        Args:
            task: 任务
            tools: 可用工具

        Returns:
            执行结果
        """
        tools = tools or []

        # 简单循环：尝试使用工具直到成功或用尽
        for tool in tools:
            try:
                if hasattr(tool, 'ainvoke'):
                    result = await tool.ainvoke({"task": task})
                else:
                    result = tool({"task": task})

                return {
                    "success": True,
                    "result": result,
                    "tool_used": getattr(tool, '__name__', str(tool))
                }
            except Exception as e:
                logger.warning(f"Tool {tool} failed: {e}")
                continue

        # 所有工具都失败
        return {
            "success": False,
            "error": "All tools failed"
        }


def create_react_executor(
    agent: Any,
    max_iterations: int = 10,
    max_tool_calls: int = 5
) -> ReActExecutor:
    """创建ReAct执行器"""
    return ReActExecutor(
        agent=agent,
        max_iterations=max_iterations,
        max_tool_calls=max_tool_calls
    )
