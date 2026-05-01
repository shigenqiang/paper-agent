"""
Intelligent Context Injector - 智能上下文注入器

根据当前任务动态决定上下文中应包含什么。

优先级:
1. 系统指令 (必须保留)
2. 用户输入 (必须保留)
3. 相关记忆 (高优先级)
4. 最近对话 (根据token限制)
5. 用户偏好 (低优先级)
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """记忆条目"""
    memory_id: str
    content: str
    memory_type: str
    importance: float = 0.5
    created_at: float = 0.0
    last_accessed: float = 0.0
    access_count: int = 0
    tags: List[str] = field(default_factory=list)


@dataclass
class Message:
    """消息"""
    role: str  # "system", "user", "assistant"
    content: str
    timestamp: float = 0.0


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str = ""
    preferences: Dict[str, Any] = field(default_factory=dict)
    expertise_areas: List[str] = field(default_factory=list)


class TokenCounter:
    """Token计数器（估算）"""

    def count(self, text: str) -> int:
        """
        估算token数量

        规则:
        - 中文: 2 tokens/字
        - 英文: 1.5 tokens/词
        """
        if not text:
            return 0

        chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
        english_words = len(text.split()) - chinese_chars

        return int(chinese_chars * 2 + english_words * 1.5)


class IntelligentContextInjector:
    """
    智能上下文注入器

    根据当前任务动态决定上下文中应包含什么

    使用示例:
        injector = IntelligentContextInjector(max_context_tokens=128000)

        context = injector.build_context(
            task="帮我写一篇关于深度学习的论文",
            agent_capabilities=capabilities,
            memory_state=memory,
            session_history=messages,
            user_profile=profile
        )

        print(context)
    """

    # 保留给系统的token
    SYSTEM_TOKEN_RESERVE = 2000

    def __init__(
        self,
        max_context_tokens: int = 128000,
        token_reserve: int = 2000
    ):
        """
        初始化智能上下文注入器

        Args:
            max_context_tokens: 最大上下文token数
            token_reserve: 保留给系统的token数
        """
        self.max_context_tokens = max_context_tokens
        self.token_reserve = token_reserve
        self._token_counter = TokenCounter()

    def build_context(
        self,
        task: str,
        agent_capabilities: Any,
        memory_state: Any,
        session_history: List[Message],
        user_profile: UserProfile
    ) -> str:
        """
        构建智能上下文

        Args:
            task: 当前任务
            agent_capabilities: Agent能力
            memory_state: 记忆状态
            session_history: 会话历史
            user_profile: 用户画像

        Returns:
            构建好的上下文字符串
        """
        remaining_tokens = self.max_context_tokens - self.token_reserve

        context_parts = []

        # 1. 用户输入（完整保留）
        user_input = self._format_user_input(task)
        context_parts.append(user_input)
        remaining_tokens -= self._token_counter.count(user_input)

        # 2. 相关记忆（智能检索）
        relevant_memories = self._retrieve_relevant_memories(task, memory_state, limit=5000)
        if relevant_memories:
            memories_text = f"## 相关记忆\n{relevant_memories}"
            context_parts.append(memories_text)
            remaining_tokens -= self._token_counter.count(relevant_memories)

        # 3. 会话历史（最近优先，智能截断）
        if remaining_tokens > 500:
            session_context = self._build_session_context(session_history, remaining_tokens)
            if session_context:
                context_parts.append(f"## 对话历史\n{session_context}")
                remaining_tokens -= self._token_counter.count(session_context)

        # 4. 用户偏好（简短总结）
        if remaining_tokens > 1000:
            preference_summary = self._summarize_preferences(user_profile)
            if preference_summary:
                context_parts.append(f"## 用户偏好\n{preference_summary}")

        return "\n\n".join(context_parts)

    def _format_user_input(self, task: str) -> str:
        """格式化用户输入"""
        return f"""## 用户请求
{task}
"""

    def _retrieve_relevant_memories(
        self,
        task: str,
        memory_state: Any,
        limit: int
    ) -> str:
        """
        检索相关记忆

        Args:
            task: 当前任务
            memory_state: 记忆状态
            limit: token限制

        Returns:
            格式化后的相关记忆
        """
        if not memory_state:
            return ""

        try:
            # 尝试调用memory_state的search方法
            if hasattr(memory_state, 'search_by_task'):
                task_memories = memory_state.search_by_task(task)
            else:
                task_memories = []

            if hasattr(memory_state, 'search_by_preferences'):
                preference_memories = memory_state.search_by_preferences(task)
            else:
                preference_memories = []

            # 优先级排序
            combined = self._prioritize_memories(task_memories, preference_memories)

            # 截断到限制
            result = self._truncate_to_limit(combined, limit)

            return result

        except Exception as e:
            logger.warning(f"Failed to retrieve memories: {e}")
            return ""

    def _prioritize_memories(
        self,
        task_memories: List[Any],
        preference_memories: List[Any]
    ) -> List[Any]:
        """优先级排序"""
        scored = []

        # 任务相关记忆
        for mem in task_memories:
            if hasattr(mem, 'importance'):
                score = mem.importance * 0.7 + 0.3
            else:
                score = 0.5
            scored.append((score, mem))

        # 偏好相关记忆
        for mem in preference_memories:
            if hasattr(mem, 'importance'):
                score = mem.importance * 0.5 + 0.5
            else:
                score = 0.5

            # 避免重复
            if mem not in [m for _, m in scored]:
                scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored]

    def _truncate_to_limit(
        self,
        memories: List[Any],
        limit: int
    ) -> str:
        """截断到token限制"""
        result_parts = []
        current_tokens = 0

        for mem in memories:
            if hasattr(mem, 'content'):
                mem_text = f"- [{mem.memory_type}] {mem.content}"
            else:
                mem_text = f"- {str(mem)}"

            mem_tokens = self._token_counter.count(mem_text)

            if current_tokens + mem_tokens > limit:
                break

            result_parts.append(mem_text)
            current_tokens += mem_tokens

        return "\n".join(result_parts)

    def _build_session_context(
        self,
        session_history: List[Message],
        remaining_tokens: int
    ) -> str:
        """构建会话上下文"""
        if not session_history:
            return ""

        # 从最近的消息开始
        messages_to_include = []
        current_tokens = 0

        for msg in reversed(session_history[-20:]):  # 最多20条
            role_map = {
                "system": "系统",
                "user": "用户",
                "assistant": "助手",
                "tool": "工具"
            }
            role = role_map.get(msg.role, msg.role)
            content = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
            msg_text = f"[{role}]: {content}"

            msg_tokens = self._token_counter.count(msg_text)

            if current_tokens + msg_tokens > remaining_tokens:
                break

            messages_to_include.insert(0, msg_text)
            current_tokens += msg_tokens

        return "\n".join(messages_to_include)

    def _summarize_preferences(self, user_profile: UserProfile) -> str:
        """总结用户偏好"""
        parts = []

        # 专业领域
        if user_profile.expertise_areas:
            areas = ", ".join(user_profile.expertise_areas[:5])
            parts.append(f"专业领域: {areas}")

        # 写作偏好
        if user_profile.preferences:
            writing_style = user_profile.preferences.get("writing_style")
            if writing_style:
                parts.append(f"写作风格: {writing_style}")

            language = user_profile.preferences.get("language", "中文")
            parts.append(f"语言: {language}")

        return "\n".join(parts)


class ContextBuilder:
    """
    上下文构建器

    提供更灵活的上下文构建方式
    """

    def __init__(self, max_tokens: int = 128000):
        self.max_tokens = max_tokens
        self._token_counter = TokenCounter()
        self._parts: List[tuple] = []  # (priority, content)

    def add(
        self,
        content: str,
        priority: int = 5,
        token_count: Optional[int] = None
    ) -> "ContextBuilder":
        """
        添加上下文部分

        Args:
            content: 内容
            priority: 优先级 (1-10, 越高越重要)
            token_count: token数量（可选，自动计算）

        Returns:
            self
        """
        if not content:
            return self

        tokens = token_count or self._token_counter.count(content)
        self._parts.append((priority, content, tokens))
        return self

    def build(self) -> str:
        """构建最终上下文"""
        # 按优先级排序
        sorted_parts = sorted(self._parts, key=lambda x: x[0], reverse=True)

        total_tokens = 0
        result_parts = []

        for priority, content, tokens in sorted_parts:
            if total_tokens + tokens > self.max_tokens:
                # 截断而不是丢弃
                remaining = self.max_tokens - total_tokens
                if remaining > 100:  # 至少保留一些内容
                    content = self._truncate_to_tokens(content, remaining)
                    result_parts.append(content)
                    total_tokens += self._token_counter.count(content)
                break

            result_parts.append(content)
            total_tokens += tokens

        return "\n\n".join(result_parts)

    def _truncate_to_tokens(self, content: str, max_tokens: int) -> str:
        """截断内容到指定token数"""
        lines = content.split("\n")
        result = []
        current_tokens = 0

        for line in lines:
            line_tokens = self._token_counter.count(line)
            if current_tokens + line_tokens > max_tokens:
                break
            result.append(line)
            current_tokens += line_tokens

        return "\n".join(result)

    def clear(self) -> "ContextBuilder":
        """清空所有部分"""
        self._parts.clear()
        return self


def create_context_injector(
    max_context_tokens: int = 128000
) -> IntelligentContextInjector:
    """创建智能上下文注入器"""
    return IntelligentContextInjector(max_context_tokens=max_context_tokens)


def create_context_builder(max_tokens: int = 128000) -> ContextBuilder:
    """创建上下文构建器"""
    return ContextBuilder(max_tokens=max_tokens)
