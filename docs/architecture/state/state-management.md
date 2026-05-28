# State Management 状态管理详解

> 位置: `src/agents_v2/state/`

## 一、架构概览

```
state/
├── __init__.py
├── state_model.py          # 状态模型定义 (7KB)
├── state_persistence.py   # 状态持久化 (9KB)
├── state_validator.py     # 状态验证 (8KB)
└── checkpoint_manager.py  # 检查点管理 (17KB)
```

## 二、状态模型

### 2.1 PaperAgentState

```python
class PaperAgentState(TypedDict):
    """LangGraph状态"""

    # 用户信息
    user_id: str
    session_id: str

    # 查询
    user_query: str
    intent: str

    # 论文数据
    papers: List[dict]              # 原始论文列表
    selected_papers: List[dict]     # 筛选后的论文

    # 写作数据
    outline: dict                   # 大纲
    draft: str                      # 初稿
    revised_draft: str              # 修订稿

    # 反馈
    feedback: str                   # 评审反馈
    quality_score: float            # 质量评分

    # 迭代控制
    iteration: int                  # 当前迭代
    max_iterations: int             # 最大迭代
    evaluation_passed: bool         # 是否通过评估

    # 阶段控制
    current_phase: str              # 当前阶段
    phases_completed: List[str]     # 已完成阶段

    # 元数据
    timestamp: str
    errors: List[str]
    trace_id: str
    metadata: dict
```

### 2.2 PhaseState 阶段状态

```python
class PhaseState(Enum):
    """阶段状态枚举"""
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 执行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"         # 失败
    SKIPPED = "skipped"       # 跳过
    WAITING_HITL = "waiting_hitl"  # 等待人工审核
```

## 三、检查点管理

### 3.1 CheckpointManager

```python
class CheckpointManager:
    """检查点管理器 - 支持暂停/恢复/时间旅行"""

    def __init__(self, backend: str = "memory"):
        self.backend = backend  # memory/sqlite/postgres
        self._checkpointer = self._create_checkpointer(backend)

    def _create_checkpointer(self, backend):
        if backend == "memory":
            return MemorySaver()
        elif backend == "sqlite":
            return SqliteSaver("data/checkpoints.db")
        elif backend == "postgres":
            return PostgresSaver(connection_string)

    async def save_checkpoint(
        self,
        session_id: str,
        state: PaperAgentState,
        phase: str
    ):
        """保存检查点"""
        config = {"configurable": {"thread_id": session_id}}
        await self._checkpointer.asave(
            state,
            config=config,
            metadata={"phase": phase}
        )

    async def load_checkpoint(
        self,
        session_id: str
    ) -> Optional[PaperAgentState]:
        """加载检查点"""
        config = {"configurable": {"thread_id": session_id}}
        return await self._checkpointer.aload(config=config)

    async def list_checkpoints(
        self,
        session_id: str
    ) -> List[CheckpointInfo]:
        """列出所有检查点"""
        ...

    async def time_travel(
        self,
        session_id: str,
        checkpoint_id: str
    ) -> PaperAgentState:
        """时间旅行到指定检查点"""
        ...
```

### 3.2 状态持久化

```python
class StatePersistence:
    """状态持久化"""

    def save_session(
        self,
        session_id: str,
        state: PaperAgentState
    ):
        """保存会话状态到持久化存储"""
        session_data = {
            "session_id": session_id,
            "state": state,
            "updated_at": datetime.now().isoformat()
        }

        if self.use_database:
            self.db.save_session(session_data)
        else:
            self.file_store.save(session_id, session_data)

    def load_session(
        self,
        session_id: str
    ) -> Optional[PaperAgentState]:
        """加载会话状态"""
        ...

    def delete_session(self, session_id: str):
        """删除会话"""
        ...
```

## 四、状态验证

### 4.1 StateValidator

```python
class StateValidator:
    """状态验证器"""

    def validate(self, state: PaperAgentState) -> ValidationResult:
        """验证状态完整性"""
        errors = []

        # 必需字段检查
        required_fields = ["user_id", "session_id", "user_query"]
        for field in required_fields:
            if field not in state or not state[field]:
                errors.append(f"Missing required field: {field}")

        # 类型检查
        if "papers" in state and not isinstance(state["papers"], list):
            errors.append("Field 'papers' must be a list")

        # 值范围检查
        if "iteration" in state and state["iteration"] < 0:
            errors.append("Iteration cannot be negative")

        if "quality_score" in state:
            if not 0 <= state["quality_score"] <= 10:
                errors.append("Quality score must be between 0 and 10")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )
```

### 4.2 TransitionValidator 状态转换验证

```python
class TransitionValidator:
    """状态转换验证"""

    ALLOWED_TRANSITIONS = {
        PhaseState.PENDING: [PhaseState.RUNNING],
        PhaseState.RUNNING: [PhaseState.COMPLETED, PhaseState.FAILED],
        PhaseState.FAILED: [PhaseState.RUNNING],  # 可重试
        PhaseState.COMPLETED: [PhaseState.WAITING_HITL, PhaseState.SKIPPED],
        PhaseState.WAITING_HITL: [PhaseState.COMPLETED, PhaseState.SKIPPED],
    }

    def validate_transition(
        self,
        from_state: PhaseState,
        to_state: PhaseState
    ) -> bool:
        """验证状态转换是否合法"""
        allowed = self.ALLOWED_TRANSITIONS.get(from_state, [])
        return to_state in allowed
```

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/state/`
