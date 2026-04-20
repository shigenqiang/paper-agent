# 记忆系统使用指南

## 概述

记忆系统提供了完整的长短期记忆管理功能，包括：

- **短期记忆（ShortTermMemory）**：工作记忆，存储当前对话的上下文
- **长期记忆（SemanticMemory）**：语义记忆，存储结构化的知识和历史信息
- **情景记忆（EpisodicMemory）**：情景记忆，存储具体的事件和经历
- **对话总结（ConversationSummarizer）**：自动提炼对话历史中的关键信息
- **记忆持久化（MemoryStorage）**：将记忆保存到文件系统
- **语义检索（MemoryRetriever）**：基于内容的智能检索
- **统一管理器（UnifiedMemoryManager）**：整合所有记忆模块

## 快速开始

### 基本使用

```python
from src.memory import UnifiedMemoryManager
import asyncio

# 初始化记忆管理器
memory_manager = UnifiedMemoryManager()

# 创建会话
session_id = "user_session_001"
memory_manager.create_session(session_id)

# 添加对话消息
memory_manager.add_message(
    session_id,
    "user",
    "我对机器学习很感兴趣"
)

memory_manager.add_message(
    session_id,
    "assistant",
    "机器学习是人工智能的一个分支"
)

# 添加语义记忆
memory_manager.add_fact(
    "机器学习是人工智能的一个分支",
    importance=0.9
)

# 检索相关记忆
async def search():
    results = await memory_manager.retrieve("机器学习", session_id=session_id)
    for result in results:
        print(f"{result.source}: {result.content}")

asyncio.run(search())

# 保存并关闭会话
memory_manager.close_session(session_id, save=True)
```

## 短期记忆

短期记忆用于存储当前对话的上下文。

```python
from src.memory import ShortTermMemory

# 创建短期记忆
stm = ShortTermMemory(
    session_id="session_001",
    max_turns=20,
    context_window=5
)

# 添加对话轮次
stm.add_turn("user", "你好")
stm.add_turn("assistant", "你好！有什么可以帮助你的？")

# 获取最近的对话
recent_turns = stm.get_recent_turns(n=2)

# 获取上下文窗口
context = stm.get_context_window()

# 设置和获取上下文
stm.set_context("topic", "机器学习")
topic = stm.get_context("topic")
```

## 长期记忆

长期记忆用于存储结构化的知识。

```python
from src.memory import SemanticMemory, MemoryType

# 创建长期记忆
sem_mem = SemanticMemory()

# 添加记忆
memory_id = sem_mem.add_memory(
    content="深度学习是机器学习的一个分支",
    memory_type=MemoryType.CONCEPT,
    importance=0.9,
    tags=["深度学习", "机器学习"],
    source="user_conversation"
)

# 获取记忆
memory = sem_mem.get_memory(memory_id)

# 搜索记忆
results = sem_mem.search_by_content("深度学习", top_k=5)

# 根据标签搜索
results = sem_mem.search_by_tags(["深度学习"], top_k=5)

# 根据类型获取
concepts = sem_mem.get_by_type(MemoryType.CONCEPT)

# 更新记忆
sem_mem.update_memory(
    memory_id,
    importance=0.95,
    tags=["深度学习", "机器学习", "神经网络"]
)

# 删除记忆
sem_mem.delete_memory(memory_id)
```

## 情景记忆

情景记忆用于存储事件和经历。

```python
from src.memory import EpisodicMemory, EventType

# 创建情景记忆
epi_mem = EpisodicMemory()

# 开始情景
episode_id = epi_mem.start_episode(
    title="学习机器学习",
    description="用户学习机器学习的过程",
    session_id="session_001",
    tags=["学习", "机器学习"]
)

# 添加事件
event_id = epi_mem.add_event(
    event_type=EventType.QUERY,
    description="用户询问关于机器学习的问题",
    session_id="session_001",
    participants=["user"],
    importance=0.7
)

# 结束情景
epi_mem.end_episode(episode_id, summary="用户完成了机器学习的基础学习")

# 搜索情景
episodes = epi_mem.search_episodes("机器学习", session_id="session_001")

# 搜索事件
events = epi_mem.search_events("查询", event_type=EventType.QUERY)
```

## 对话总结

自动提炼对话历史中的关键信息。

```python
from src.memory import UnifiedMemoryManager
import asyncio

memory_manager = UnifiedMemoryManager()

# 添加一些对话后
async def summarize():
    session = memory_manager.get_session("session_001")
    summary = await memory_manager.summarizer.summarize_conversation(
        session,
        "session_001"
    )

    print(f"主要话题: {summary.main_topic}")
    print(f"关键点: {summary.key_points}")
    print(f"用户偏好: {summary.user_preferences}")
    print(f"待办事项: {summary.action_items}")

asyncio.run(summarize())
```

## 记忆检索

智能检索相关记忆。

```python
from src.memory import UnifiedMemoryManager
import asyncio

memory_manager = UnifiedMemoryManager()

async def retrieve_memories():
    # 基本检索
    results = await memory_manager.retrieve(
        query="机器学习",
        session_id="session_001",
        top_k=10
    )

    # 格式化检索结果
    context = await memory_manager.retrieve_context(
        query="机器学习",
        session_id="session_001",
        top_k=5
    )
    print(context)

asyncio.run(retrieve_memories())
```

## 记忆持久化

保存和加载记忆。

```python
from src.memory import UnifiedMemoryManager

memory_manager = UnifiedMemoryManager()

# 保存所有记忆
memory_manager.save_all()

# 备份记忆
memory_manager.backup("backup_20240420")

# 恢复记忆
memory_manager.restore("backup_20240420")

# 获取存储统计
stats = memory_manager.get_stats()
print(f"存储大小: {stats['storage']['total_size_mb']} MB")
```

## 统一管理器

使用统一管理器整合所有功能。

```python
from src.memory import UnifiedMemoryManager, MemoryType
import asyncio

memory_manager = UnifiedMemoryManager()

# 会话管理
session = memory_manager.get_or_create_session("user_001")

# 添加消息
memory_manager.add_message("user_001", "user", "你好")
memory_manager.add_message("user_001", "assistant", "你好！")

# 添加不同类型的记忆
memory_manager.add_fact("这是一个重要的事实", importance=0.9)
memory_manager.add_preference("用户喜欢简洁的回答")
memory_manager.add_insight("用户对技术细节感兴趣")

# 检索
async def search():
    results = await memory_manager.retrieve("技术", session_id="user_001")
    for result in results:
        print(f"{result.source}: {result.content}")

asyncio.run(search())

# 获取统计
stats = memory_manager.get_stats()
print(f"活跃会话: {stats['sessions']['active']}")
print(f"语义记忆: {stats['semantic_memory']['total']}")
```

## 最佳实践

1. **会话管理**
   - 每个用户使用独立的session_id
   - 定期关闭不需要的会话以释放内存

2. **记忆分类**
   - 使用MemoryType正确分类记忆
   - 为重要信息设置高importance值
   - 使用tags便于后续检索

3. **性能优化**
   - 限制短期记忆的max_turns
   - 定期清理低重要性的旧记忆
   - 使用向量嵌入提高检索效率

4. **持久化**
   - 定期调用save_all()保存记忆
   - 重要操作前创建备份
   - 定期清理旧的备份文件

## API参考

### UnifiedMemoryManager

```python
class UnifiedMemoryManager:
    def __init__(self, storage_dir: str = "data/memory", embedding_service: Optional[Any] = None)
    def create_session(self, session_id: str) -> ShortTermMemory
    def get_session(self, session_id: str) -> Optional[ShortTermMemory]
    def close_session(self, session_id: str, save: bool = True) -> bool
    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool
    async def retrieve(self, query: str, session_id: Optional[str] = None, top_k: int = 10, include_short_term: bool = True) -> List[RetrievalResult]
    async def retrieve_context(self, query: str, session_id: str, top_k: int = 5) -> str
    def add_semantic_memory(self, content: str, memory_type: MemoryType, importance: float = 0.5, tags: Optional[List[str]] = None, source: Optional[str] = None) -> str
    def add_fact(self, fact: str, importance: float = 0.7, source: Optional[str] = None) -> str
    def add_preference(self, preference: str, source: Optional[str] = None) -> str
    def add_insight(self, insight: str, importance: float = 0.8, source: Optional[str] = None) -> str
    def save_all(self) -> bool
    def backup(self, backup_name: Optional[str] = None) -> bool
    def restore(self, backup_name: str) -> bool
    def get_stats(self) -> Dict[str, Any]
```

### MemoryType

```python
class MemoryType(str, Enum):
    FACT = "fact"           # 事实性知识
    CONCEPT = "concept"     # 概念定义
    PROCEDURE = "procedure" # 过程/方法
    EXPERIENCE = "experience" # 经验
    REFERENCE = "reference" # 参考文献
    INSIGHT = "insight"     # 洞察/发现
```

## 示例

查看 `examples/memory_example.py` 获取完整的使用示例。

## 测试

运行测试：

```bash
pytest tests/unit/test_memory.py
pytest tests/unit/test_unified_memory.py
```
