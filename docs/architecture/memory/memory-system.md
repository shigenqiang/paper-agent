# Memory System 记忆系统详解

> 位置: `src/agents_v2/memory/`
> 版本: v4.0
> 更新日期: 2026-05-03
> 代码版本: `__version__ = "4.0"`
> 基于调研: `docs/research/07-记忆系统/`

---

## 一、架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        分层记忆系统 (Memory System v4)                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│    短期记忆           │  │    会话记忆           │  │    长期记忆           │
│  (ShortTermMemory)    │  │  (SessionMemory)      │  │  (LongTermMemory)     │
│                       │  │                       │  │                       │
│  范围: 当前任务        │  │  范围: 任务内跨Agent   │  │  范围: 跨任务持久化     │
│  存储: 内存 (LRU)      │  │  存储: 内存/文件       │  │  存储: SQLite/向量库   │
│  容量: 500条目         │  │  容量: 500条目         │  │  容量: 无限制          │
│  TTL: 任务结束清除     │  │  TTL: 会话结束清除     │  │  特性: 持久化          │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │    情景记忆 (EpisodicMemory)   │
                    │                               │
                    │  范围: 执行轨迹记录             │
                    │  存储: SQLite                  │
                    │  特性: 时间线, 因果关系         │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │    统一记忆管理器               │
                    │  (UnifiedMemoryManager)        │
                    │                               │
                    │  核心服务:                      │
                    │  - MemoryExtractor (LLM驱动)    │
                    │  - SummaryGenerator (自动摘要)  │
                    │  - EnhancedRetrievalEngine      │
                    │  - ForgettingController         │
                    └───────────────────────────────┘
```

---

## 二、存储架构 (v4.0 SQLite 单一存储)

### 2.1 多存储层次

| 记忆层 | 存储介质 | 淘汰策略 |
|-------|---------|---------|
| **ShortTerm** | 内存 (OrderedDict LRU) | LRU + TTL(1h) |
| **Session** | SQLite + JSON | TTL(会话结束) |
| **LongTerm** | SQLite + 向量索引 | 重要性衰减 |
| **Episodic** | SQLite | 时间线记录 |
| **UserProfile** | SQLite | 置信度衰减 |

### 2.2 SQLite 表结构

```sql
-- 会话表
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    messages TEXT DEFAULT '[]',
    summary TEXT,
    created_at REAL,
    last_accessed REAL
);

-- 实体索引表
CREATE TABLE memory_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id TEXT UNIQUE NOT NULL,
    memory_type TEXT,
    importance REAL DEFAULT 0.5,
    tags TEXT,
    created_at REAL,
    last_accessed REAL
);

-- 情景记忆表
CREATE TABLE episodic_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    event_type TEXT,
    content TEXT,
    timestamp REAL
);
```

### 2.3 SQLite 存储结构

- 使用 SQLite 作为统一存储
- 存储路径: `.memory/memory.db`
- 无外部依赖（PostgreSQL, Qdrant, Neo4j 已移除）

---

## 三、重要性等级与保留策略 (v3.0)

### 3.1 五级重要性体系

| 等级 | 分数 | 语义 | S参数（秒）| 保留时间 |
|------|------|------|-----------|---------|
| **CRITICAL** | 1.0 | 永不遗忘 | ∞ | 永不 |
| **HIGH** | 0.8 | 长期保留 | 604,800 (7天) | 7天 |
| **MEDIUM** | 0.5 | 标准衰减 | 86,400 (1天) | 1天 |
| **LOW** | 0.3 | 快速遗忘 | 3,600 (1小时) | 1小时 |
| **FORGOTTEN** | <0.1 | 已删除 | <3,600 | - |

### 3.2 保留分数计算公式

**核心公式**: `retention = importance × e^(-t/S)`

```python
def retention_score(self) -> float:
    t = time.time() - self.last_accessed
    S = self.get_strength_parameter()  # CRITICAL=∞, HIGH=7天, MEDIUM=1天, LOW=1小时
    if S == float('inf'):
        return 1.0
    return self.importance * math.exp(-t / S)
```

### 3.3 S参数衰减曲线

```
保留率
100% ─────────────────────────────────────────── CRITICAL (∞)
 70% │───────── HIGH (7天半衰)
     │
 50% │────────────────── MEDIUM (1天半衰)
     │
 37% ───────────────────────────────────────────
     │──── LOW (1小时半衰)
  0% └──────────────────────────────────────────► 时间
    0    1h    1d    7d    30d
```

---

## 四、记忆流转规则

### 4.1 流转触发条件

| 阶段 | 触发条件 | 操作 |
|------|---------|------|
| STG → SESSION | 消息数 ≥ 30 OR 任务结束 | 批量存储到会话存储 |
| STG → LONG_TERM | 重要性 ≥ 0.7 OR 用户标记 | 存入长期记忆 |
| LONG_TERM → FORGOTTEN | retention < 0.1 | 删除 |
| 任意 → COMPRESS | token超限 | LLM生成摘要 |

### 4.2 双向流转图

```
                    新记忆                              召回路径
                      │                                  │
                      ▼                                  │
┌──────────┐    [消息≥30]    ┌──────────┐                │
│ ShortTerm│ ────────────► │ Session  │                │
│ (内存)   │                │ (PG JSONB)│                │
└────┬─────┘                └────┬─────┘                │
     │                           │                        │
     │[重要性≥0.7]              │                        │
     ▼                           ▼                        │
┌──────────┐               ┌──────────┐                 │
│ LongTerm │               │ LongTerm │                 │
│ (Qdrant) │               │ (Neo4j)  │                 │
└────┬─────┘               └──────────┘                 │
     │                                                  │
     │[召回触发]                                        │
     │  - 短期未命中                                    │
     │  - 频繁访问(7天≥5次)                             │
     │  - 高相关性(>0.8)                                │
     │  - Top3检索结果                                  │
     └──────────────────────────────────────────────► ┌──────────┐
                                                       │ ShortTerm│
                                                       │ (缓存)   │
                                                       └──────────┘
```

### 4.3 召回触发机制

| 触发情况 | 触发条件 | 示例 |
|------|---------|------|
| **用户提问涉及历史** | 问题含"之前"、"上次"等 | "之前那个项目怎么样了" |
| **会话冷启动** | 新会话开始 | 加载用户偏好、历史任务 |
| **Context快满** | 使用率 > 90% | 压缩历史，保留关键记忆 |
| **Agent主动需要** | 推理中发现需要背景 | "我需要看看用户的代码风格" |

---

## 五、核心模块

### 5.1 unified.py — 统一记忆管理器

```python
class UnifiedMemoryManager:
    """统一记忆管理器，协调各层记忆"""

    def __init__(self):
        self.short_term = ShortTermMemory()
        self.session = SessionMemory()
        self.long_term = LongTermMemory()
        self.episodic = EpisodicMemory()

    def remember(self, key: str, value: Any, importance: float = 0.5):
        """存储记忆"""
        if importance >= 0.7:
            self.long_term.store(key, value)
        else:
            self.short_term.store(key, value)

    def recall(self, key: str) -> Optional[Any]:
        """召回记忆 - 按层级顺序查询"""
        # 短期 → 会话 → 长期
        if value := self.short_term.get(key):
            return value
        if value := self.session.get(key):
            return value
        return self.long_term.get(key)

    async def recall_with_decay(self, query: str, top_k: int = 3) -> List[MemoryEntry]:
        """带遗忘曲线的时间衰减召回"""
        memories = await self.long_term.search(query, top_k=top_k*2)
        current_time = time.time()

        scored = []
        for mem in memories:
            retention = self._calculate_retention_score(mem, current_time)
            if retention >= 0.1:  # 阈值过滤
                scored.append((retention * mem.importance, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored[:top_k]]
```

### 5.2 short_term.py — 短期记忆

```python
class ShortTermMemory:
    """短期记忆，内存 LRU 缓存"""

    def __init__(self, max_items: int = 500):
        self.cache = OrderedDict()
        self.max_items = max_items

    def store(self, key: str, value: Any):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.max_items:
            self.cache.popitem(last=False)  # LRU 淘汰
```

### 5.3 session.py — 会话记忆

```python
class SessionMemory:
    """会话记忆，任务内跨 Agent 共享"""

    def __init__(self, storage_path: str = "data/memory/session.json"):
        self.storage_path = storage_path

    def store(self, key: str, value: Any):
        # 持久化到文件
        ...

    def get(self, key: str) -> Optional[Any]:
        # 从文件加载
        ...
```

### 5.4 long_term.py — 长期记忆

```python
class LongTermMemory:
    """长期记忆，跨任务持久化"""

    def __init__(self, db_path: str = "data/memory/long_term.db"):
        self.db_path = db_path
        self.embeddings = EmbeddingsService()

    def store(self, key: str, value: Any, vector: List[float] = None):
        # 存储到 SQLite + 向量索引
        ...

    def search(self, query: str, top_k: int = 5) -> List[Any]:
        # 向量相似度搜索
        ...
```

---

## 六、智能触发与上下文注入

### 6.1 智能上下文注入器 (IntelligentContextInjector)

```python
class IntelligentContextInjector:
    """智能上下文注入器 - 带遗忘曲线的记忆召回"""

    HISTORY_KEYWORDS = [
        "之前", "上次", "之前那个", "上次那个",
        "以前", "曾经", "之前你", "上次我",
        "还记得", "之前提到", "上次说的"
    ]

    def __init__(
        self,
        importance_threshold: float = 0.3,
        enable_time_decay: bool = True,
        system_token_reserve: int = 2000
    ):
        self.importance_threshold = importance_threshold
        self.enable_time_decay = enable_time_decay
        self.system_token_reserve = system_token_reserve

    def _should_recall_memories(self, task: str) -> bool:
        """判断是否需要召回记忆"""
        for keyword in self.HISTORY_KEYWORDS:
            if keyword in task:
                return True
        return False

    def _calculate_retention_score(self, mem: Any, current_time: float) -> float:
        """基于Ebbinghaus公式计算保留分数"""
        importance = self._get_memory_importance(mem)
        if not hasattr(mem, 'last_accessed') or mem.last_accessed == 0:
            return importance

        t = current_time - mem.last_accessed

        if importance >= 0.8:
            S = 86400 * 7   # 7天
        elif importance >= 0.6:
            S = 86400        # 1天
        elif importance >= 0.4:
            S = 3600 * 12    # 12小时
        else:
            S = 3600         # 1小时

        retention = importance * math.exp(-t / S) if S > 0 else importance
        return min(1.0, max(0.0, retention))

    def _prioritize_memories(self, memories: List[Any]) -> List[Any]:
        """优先级排序 - 集成时间衰减和重要性阈值过滤"""
        scored = []
        current_time = time.time()

        for mem in memories:
            importance = self._get_memory_importance(mem)
            if importance < self.importance_threshold:
                continue

            retention = self._calculate_retention_score(mem, current_time)
            final_score = (importance * 0.7 + 0.3) * retention
            scored.append((final_score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored]
```

---

## 七、Embeddings 服务

```python
class EmbeddingsService:
    """向量嵌入服务"""

    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = model

    def encode(self, text: str) -> List[float]:
        """文本向量化"""
        ...

    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """余弦相似度"""
        ...
```

---

## 八、在 Workflow 中的集成

```
路由节点:
  router → memory_recall → crawler → selector → ...

      ↑ (召回历史记忆 Top 3)
      │ 增强用户查询
      │ 提供上下文

  ...

记忆节点:
  ... → evaluator → memory_remember → END

      ↑ (存储 Top 5 论文)
      │ 记录任务结果
      │ 积累用户知识
```

### 8.1 MemoryNode 集成

```python
# src/agents_v2/langgraph_workflow/nodes/memory.py
from ...memory.unified import UnifiedMemoryManager, get_memory_manager
from ...memory.types import MemoryType, MemoryEntry

class MemoryNode:
    def __init__(self):
        self.memory_manager = get_memory_manager()

    def recall_before_search(self, state: State) -> State:
        """搜索前记忆召回 - 智能触发"""
        task = state.get("task", "")
        memory_state = state.get("memory_state")

        injector = IntelligentContextInjector()

        # 智能触发判断
        if not injector._should_recall_memories(task):
            return state  # 不触发召回

        # 检索并优先级排序
        memories = memory_manager.recall(task, top_k=3)
        prioritized = injector._prioritize_memories(memories)

        state["recalled_memories"] = prioritized
        return state
```

---

## 九、检索增强

```python
class EnhancedRetrievalEngine:
    """增强检索引擎"""

    async def recall(
        self,
        query: str,
        top_k: int = 3,
        user_id: str = None,
        enable_decay: bool = True
    ) -> List[MemoryEntry]:
        """
        1. 向量化查询
        2. 短期记忆检索
        3. 会话记忆检索
        4. 长期记忆向量搜索
        5. 重要性阈值过滤
        6. 时间衰减排序
        7. 合并排序
        """
        ...
```

---

## 十、压缩机制

```python
class CompressionService:
    """记忆压缩服务"""

    def compress(self, memories: List[MemoryEntry]) -> MemoryEntry:
        """
        使用 LLM 压缩多个记忆为单一记忆
        保留核心信息
        """
        prompt = f"压缩以下记忆，保留核心信息:\n{memories}"
        compressed = llm.invoke(prompt)
        return MemoryEntry(content=compressed, importance=0.8)
```

---

## 十一、配置

```python
@dataclass
class MemoryConfig:
    """记忆系统配置"""
    storage_path: str = ".memory"
    short_term_max_items: int = 100
    short_term_ttl_seconds: float = 3600
    session_max_entries: int = 500
    session_summary_trigger: int = 30
    long_term_persist_threshold: float = 0.7
    forgetting_threshold: float = 0.1
    importance_threshold: float = 0.3
```

> **注意**: v4.0 版本使用 SQLite 单一存储，无需 Docker Compose外部服务。

---

**版本**: v4.0
**更新日期**: 2026-05-03
**基于代码**: `src/agents_v2/memory/`
**调研文档**: `docs/research/07-记忆系统/`