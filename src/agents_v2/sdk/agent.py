"""
Claude Agent SDK-style Agent class.

Key features over BaseAgent:
  - Lifecycle hooks: on_start / pre_tool_use / post_tool_use / on_finish
  - Tool use loop with auto tool execution
  - Subagents mechanism for delegating work
  - Auto context compression (delegates to context.py)
  - MCP-native tool registration bridge
  - Permission system for tool execution
"""
import asyncio
import inspect
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from .tool import ToolDefinition, ToolRegistry, tool_registry, get_tool_schemas
from .context import ContextCompressor

logger = logging.getLogger(__name__)


class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    TOOL_USE = "tool_use"
    FINISHED = "finished"
    ERROR = "error"


class Permission(Enum):
    """Tool execution permission levels."""
    ALWAYS = "always"
    ASK = "ask"
    NEVER = "never"


@dataclass
class ToolCallRequest:
    """A tool call requested by the LLM."""
    tool_name: str
    tool_args: Dict[str, Any]
    call_id: str = ""


@dataclass
class ToolCallResult:
    """Result of a tool execution."""
    tool_name: str
    result: Any
    success: bool
    error: Optional[str] = None
    duration_ms: float = 0.0
    call_id: str = ""


@dataclass
class AgentConfig:
    """Configuration for an SDK-style Agent."""
    model: str = "MiniMax-M2.7"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    max_tool_iterations: int = 10
    # Context compression
    enable_auto_compression: bool = True
    compression_threshold_tokens: int = 80000
    # Permissions
    default_permission: Permission = Permission.ALWAYS


class Agent:
    """Claude Agent SDK-style Agent.

    Key features:
    - Lifecycle hooks: on_start, pre_tool_use, post_tool_use, on_finish
    - Tool use loop with automatic execution and retry
    - Subagents for task delegation
    - Auto context compression
    - MCP-native tool registration

    Usage:
        agent = Agent(
            name="search_agent",
            system_prompt="You are a research assistant...",
            config=AgentConfig(model="MiniMax-M2.7"),
        )

        @agent.tool
        async def search_papers(query: str) -> dict:
            '''Search academic papers.'''
            ...

        result = await agent.run("Find papers about graph neural networks")
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        config: Optional[AgentConfig] = None,
        tools: Optional[List[Union[Callable, ToolDefinition]]] = None,
        skills: Optional[List[str]] = None,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.config = config or AgentConfig()
        self.state = AgentState.IDLE
        self.logger = logging.getLogger(f"SDKAgent.{name}")

        # Tool management
        self._local_tools: Dict[str, ToolDefinition] = {}
        self._permissions: Dict[str, Permission] = {}
        self._tool_registry = ToolRegistry()

        if tools:
            for t in tools:
                self.add_tool(t)

        # Skills (SKILL.md names to activate)
        self._skill_names: List[str] = skills or []
        self._active_skills: Dict[str, Any] = {}

        # Execution tracking
        self._iteration_count = 0
        self._tool_history: List[ToolCallResult] = []
        self._messages: List[Dict[str, Any]] = []

        # Hooks — can be set by subclasses or externally
        self._hooks: Dict[str, List[Callable]] = {
            "on_start": [],
            "pre_tool_use": [],
            "post_tool_use": [],
            "on_finish": [],
            "on_error": [],
        }

        # Context compression
        self._compressor = ContextCompressor(
            threshold_tokens=self.config.compression_threshold_tokens
        ) if self.config.enable_auto_compression else None

        # Subagents
        self._subagents: Dict[str, "Agent"] = {}

        # LLM client (lazy init)
        self._client = None

    # ── Tool management ──────────────────────────────────────────────

    def tool(self, func: Optional[Callable] = None, *,
             name: Optional[str] = None,
             permission: Permission = Permission.ALWAYS):
        """Decorator: register a function as a tool on this agent.

        Usage:
            @agent.tool
            async def my_tool(x: str) -> str:
                '''Tool description.'''
                ...

            @agent.tool(permission=Permission.ASK)
            async def dangerous_tool(x: str) -> str: ...
        """
        from .tool import tool as tool_decorator

        def _register(fn):
            decorated = tool_decorator(name=name, register=False)(fn)
            tool_def = decorated.tool_def
            self._add_tool_def(tool_def, permission)
            return decorated

        if func is not None:
            return _register(func)
        return _register

    def add_tool(self, tool: Union[Callable, ToolDefinition], permission: Permission = Permission.ALWAYS):
        """Add a pre-existing tool or function to this agent."""
        from .tool import tool as tool_decorator

        if isinstance(tool, ToolDefinition):
            self._add_tool_def(tool, permission)
        elif callable(tool):
            decorated = tool_decorator(register=False)(tool)
            self._add_tool_def(decorated.tool_def, permission)
        else:
            raise TypeError(f"Expected callable or ToolDefinition, got {type(tool)}")

    def _add_tool_def(self, tool_def: ToolDefinition, permission: Permission):
        self._local_tools[tool_def.name] = tool_def
        self._permissions[tool_def.name] = permission
        self._tool_registry.register(tool_def)

    def set_permission(self, tool_name: str, permission: Permission):
        """Change the permission level for a tool."""
        self._permissions[tool_name] = permission

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._local_tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._local_tools.values())

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [t.schema for t in self._local_tools.values()]

    # ── Subagents ────────────────────────────────────────────────────

    def subagent(self, name: str, system_prompt: str, tools: Optional[List[Callable]] = None) -> "Agent":
        """Register a subagent for task delegation.

        Similar to Claude Agent SDK's subagent mechanism — the parent agent
        can delegate work to subagents via tool calls.
        """
        sub = Agent(
            name=f"{self.name}.{name}",
            system_prompt=system_prompt,
            config=self.config,
            tools=tools,
        )
        self._subagents[name] = sub

        # Auto-register a tool that the parent can call to delegate to this subagent
        async def delegate_to_subagent(task: str) -> str:
            """Delegate a task to the subagent."""
            return await sub.run(task)

        delegate_to_subagent.__name__ = f"delegate_to_{name}"
        delegate_to_subagent.__doc__ = f"Delegate task to {name} subagent."
        self.add_tool(delegate_to_subagent)

        return sub

    def get_subagent(self, name: str) -> Optional["Agent"]:
        return self._subagents.get(name)

    # ── Hooks ─────────────────────────────────────────────────────────

    def on_start(self, func: Callable):
        """Register a hook called before the agent starts running.

        Signature: async def hook(agent: Agent, task: str) -> Optional[str]
        Return a string to override the initial system prompt, or None.
        """
        self._hooks["on_start"].append(func)
        return func

    def pre_tool_use(self, func: Callable):
        """Register a hook called before each tool execution.

        Signature: async def hook(agent: Agent, tool_call: ToolCallRequest) -> Optional[ToolCallRequest]
        Return a modified ToolCallRequest to override, or None to proceed.
        Return a ToolCallRequest with tool_name="" to skip execution.
        """
        self._hooks["pre_tool_use"].append(func)
        return func

    def post_tool_use(self, func: Callable):
        """Register a hook called after each tool execution.

        Signature: async def hook(agent: Agent, result: ToolCallResult) -> Optional[ToolCallResult]
        """
        self._hooks["post_tool_use"].append(func)
        return func

    def on_finish(self, func: Callable):
        """Register a hook called after the agent finishes.

        Signature: async def hook(agent: Agent, final_result: str) -> None
        """
        self._hooks["on_finish"].append(func)
        return func

    def on_error(self, func: Callable):
        """Register a hook called when an error occurs.

        Signature: async def hook(agent: Agent, error: Exception) -> Optional[str]
        Return a string to use as fallback response, or None to re-raise.
        """
        self._hooks["on_error"].append(func)
        return func

    # ── Main execution loop ───────────────────────────────────────────

    async def run(self, task: str, context_messages: Optional[List[Dict[str, Any]]] = None) -> str:
        """Run the agent on a task. Main entry point.

        Args:
            task: The user's task description.
            context_messages: Previous conversation messages (optional).

        Returns:
            The agent's final text response.
        """
        self.state = AgentState.THINKING
        start_time = time.time()

        try:
            # Fire on_start hooks
            for hook in self._hooks["on_start"]:
                override = await hook(self, task)
                if override:
                    task = override

            # Build initial messages
            self._messages = list(context_messages or [])
            self._messages.append({"role": "system", "content": self.system_prompt})
            self._messages.append({"role": "user", "content": task})

            # Main tool-use loop
            for iteration in range(self.config.max_tool_iterations):
                self._iteration_count = iteration + 1

                # Auto-compress context if needed
                if self._compressor:
                    self._messages = await self._compressor.compress(self._messages)

                # Call LLM
                response = await self._call_llm(self._messages)

                # Check if the response contains tool calls
                tool_calls = self._extract_tool_calls(response)

                if not tool_calls:
                    # No tool calls — this is the final response
                    self.state = AgentState.FINISHED
                    self.logger.info(f"Agent finished after {iteration + 1} iterations "
                                   f"({(time.time() - start_time):.1f}s)")

                    for hook in self._hooks["on_finish"]:
                        await hook(self, response)

                    return response

                # Execute tool calls
                self.state = AgentState.TOOL_USE
                for tc in tool_calls:
                    result = await self._execute_tool(tc)
                    self._tool_history.append(result)

                # Append assistant response + tool results to messages
                self._messages.append({"role": "assistant", "content": response})

                for tc, result in zip(tool_calls, self._tool_history[-len(tool_calls):]):
                    self._messages.append({
                        "role": "tool",
                        "content": json.dumps(result.result, ensure_ascii=False)
                        if result.success else f"Error: {result.error}",
                        "tool_call_id": tc.call_id or result.call_id,
                    })

            # Max iterations reached
            self.state = AgentState.FINISHED
            self.logger.warning(f"Max tool iterations ({self.config.max_tool_iterations}) reached")
            final = await self._force_final_answer()
            return final

        except Exception as e:
            self.state = AgentState.ERROR
            self.logger.error(f"Agent error: {e}")

            for hook in self._hooks["on_error"]:
                fallback = await hook(self, e)
                if fallback:
                    return fallback

            raise

    # ── Internal: LLM call ────────────────────────────────────────────

    async def _call_llm(self, messages: List[Dict[str, Any]]) -> str:
        """Call the LLM with messages and tool schemas."""
        try:
            from openai import OpenAI

            api_key = self.config.api_key or os.getenv("OPENAI_API_KEY", "")
            base_url = self.config.base_url or os.getenv("OPENAI_BASE_URL", "https://api.minimax.chat/v1")

            client = OpenAI(api_key=api_key, base_url=base_url)

            kwargs = {
                "model": self.config.model,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            }

            # Include tools if available
            schemas = self.get_tool_schemas()
            if schemas:
                kwargs["tools"] = schemas
                kwargs["tool_choice"] = "auto"

            response = client.chat.completions.create(**kwargs)

            if hasattr(response, 'choices') and response.choices:
                msg = response.choices[0].message
                # Handle tool calls
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # Build a combined response with tool calls embedded
                    parts = []
                    if msg.content:
                        parts.append(msg.content)
                    for tc in msg.tool_calls:
                        parts.append(
                            f"\n<tool_call name=\"{tc.function.name}\">"
                            f"{tc.function.arguments}</tool_call>"
                        )
                    return "\n".join(parts)
                return msg.content or ""
            return str(response)
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            raise

    # ── Internal: Tool execution ──────────────────────────────────────

    def _extract_tool_calls(self, response: str) -> List[ToolCallRequest]:
        """Extract tool call requests from LLM response text.

        Supports both:
        1. Structured tool_calls from API response (handled in _call_llm via tags)
        2. XML-style <tool_call name="...">...</tool_call> in raw text
        """
        import re
        calls = []

        # Parse <tool_call name="X">...</tool_call> patterns
        pattern = r'<tool_call\s+name="([^"]+)"\s*>(.*?)</tool_call>'
        for match in re.finditer(pattern, response, re.DOTALL):
            tool_name = match.group(1)
            args_str = match.group(2).strip()
            try:
                args = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args = {"raw_input": args_str}
            calls.append(ToolCallRequest(tool_name=tool_name, tool_args=args))
            self.logger.debug(f"Parsed tool call: {tool_name}")

        return calls

    async def _execute_tool(self, tool_call: ToolCallRequest) -> ToolCallResult:
        """Execute a single tool call with hooks and permissions."""
        tool_name = tool_call.tool_name
        tool_def = self._local_tools.get(tool_name)

        if not tool_def:
            return ToolCallResult(
                tool_name=tool_name, result=None, success=False,
                error=f"Tool '{tool_name}' not found",
                call_id=tool_call.call_id
            )

        # Check permissions
        permission = self._permissions.get(tool_name, self.config.default_permission)
        if permission == Permission.NEVER:
            return ToolCallResult(
                tool_name=tool_name, result=None, success=False,
                error=f"Tool '{tool_name}' is disabled (NEVER permission)",
                call_id=tool_call.call_id
            )

        # Fire pre_tool_use hooks
        for hook in self._hooks["pre_tool_use"]:
            modified = await hook(self, tool_call)
            if modified:
                tool_call = modified
            if not tool_call.tool_name:  # Hook requested skip
                return ToolCallResult(
                    tool_name=tool_name, result="Skipped by hook",
                    success=True, call_id=tool_call.call_id
                )

        # Execute
        start = time.time()
        try:
            if inspect.iscoroutinefunction(tool_def.func):
                result = await tool_def.func(**tool_call.tool_args)
            else:
                result = tool_def.func(**tool_call.tool_args)

            duration_ms = (time.time() - start) * 1000
            tool_def.call_count += 1
            tool_def.total_duration_ms += duration_ms

            tool_result = ToolCallResult(
                tool_name=tool_name, result=result, success=True,
                duration_ms=duration_ms, call_id=tool_call.call_id
            )
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            tool_result = ToolCallResult(
                tool_name=tool_name, result=None, success=False,
                error=str(e), duration_ms=duration_ms, call_id=tool_call.call_id
            )

        # Fire post_tool_use hooks
        for hook in self._hooks["post_tool_use"]:
            modified = await hook(self, tool_result)
            if modified:
                tool_result = modified

        return tool_result

    async def _force_final_answer(self) -> str:
        """Ask the LLM to provide a final answer based on tool results."""
        self._messages.append({
            "role": "user",
            "content": "Please provide your final answer based on all tool results above. "
                       "Do not call any more tools."
        })
        try:
            return await self._call_llm(self._messages)
        except Exception:
            return "Max tool iterations reached. Unable to produce final answer."

    # ── Skills integration ────────────────────────────────────────────

    async def load_skills(self) -> None:
        """Load and activate SKILL.md definitions for this agent."""
        if not self._skill_names:
            return

        from ..skills.loader import SkillsLoader
        loader = SkillsLoader()
        await loader.scan_definitions()

        for name in self._skill_names:
            skill = await loader.activate(name)
            if skill and skill.body:
                self._active_skills[name] = skill
                # Append skill body to system prompt
                self.system_prompt += f"\n\n## Skill: {name}\n{skill.body}"
                self.logger.info(f"Loaded skill: {name}")

    # ── Misc ──────────────────────────────────────────────────────────

    @property
    def iteration_count(self) -> int:
        return self._iteration_count

    @property
    def tool_history(self) -> List[ToolCallResult]:
        return list(self._tool_history)

    @property
    def messages(self) -> List[Dict[str, Any]]:
        return list(self._messages)
