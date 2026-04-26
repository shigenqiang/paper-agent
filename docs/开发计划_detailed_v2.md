# Paper Agent 详细开发计划 - 迭代版本
**项目**: Paper Agent
**版本**: v0.2 (迭代版)
**目标**: 达到 9.5 → 10.0 评分
**迭代次数**: 20次以上
**最后更新**: 2026-04-27

---

## 一、现有系统分析

### 1.1 已实现的核心模块

| 模块 | 实现状态 | 代码文件 | 功能完整性 |
|------|---------|----------|-----------|
| IntentRouter | ✅ 完整 | intent_router.py | 意图识别 + LLM辅助 |
| MasterSupervisor | ✅ 完整 | master_supervisor.py | 6阶段流程编排 |
| UnifiedMemoryManager | ✅ 完整 | unified.py | 6层记忆整合 |
| KnowledgeGraphService | ✅ 完整 | kg_service.py | 混合检索+GraphRAG |
| SELF-RAGController | ✅ 完整 | self_rag_controller.py | 反思型RAG |
| ChainOfThoughtReasoner | ✅ 完整 | chain_of_thought.py | CoT/ToT/ReAct |
| MultiAgentDebate | ⚠️ 基础 | debate.py | 辩论框架存在 |
| SkillAcquisitionEngine | ⚠️ 基础 | skill_engine.py | 技能库存在 |
| PreferenceLearner | ⚠️ 基础 | preference_learner.py | 5维偏好学习 |
| DynamicRetrievalPlanner | ✅ 完整 | dynamic_planner.py | 5种查询类型 |
| ToolRegistry | ✅ 完整 | registry.py | 工具注册执行 |

### 1.2 现有流程概览

```
用户输入
    │
    ▼
IntentRouter ──── 意图识别 ────▶ IntentType
    │
    ▼
MasterSupervisor ──── 全局协调 ────▶ PhaseSupervisor
    │
    ├── Diagnostic Phase (3个Agent并行诊断)
    ├── Topic Phase (Pipeline Agent)
    ├── Literature Phase (Pipeline Agent)
    ├── Methodology Phase (Problem-Oriented Agent)
    ├── Writing Phase (Pipeline Agent)
    └── Polish Phase (Problem-Oriented Agent)
    │
    ▼
UnifiedMemoryManager ──── 多层记忆 ────▶ 各层存储
```

---

## 二、差距分析（基于现代Agent框架研究）

### 2.1 与AutoGen/CrewAI/LangGraph的对比

| 功能维度 | AutoGen | CrewAI | LangGraph | Paper Agent | 差距 |
|---------|---------|--------|-----------|-------------|------|
| **Agent通信协议** | 共享消息池 | Hierarchical | 状态机流转 | 直接调用 | 缺少协议层 |
| **状态管理** | 组会话状态 | 角色定义 | 检查点机制 | PaperState | 需增强持久化 |
| **工具调用** | function_call | 工具注册 | Tool节点 | Registry | 需版本管理 |
| **错误恢复** | 容错会话 | 无 | 错误边界 | FallbackHandler | 需分类分级 |
| **人机交互** | HumanInput | 无 | 打断机制 | 无 | 需引入HIL |
| **流式输出** | streaming | 无 | streaming | 无 | 需流式支持 |
| **成本控制** | BudgetAgent | 无 | 无 | CostOptimizer | 需实时追踪 |
| **上下文管理** | context_max | 无 | summarizer | 有限制 | 需智能压缩 |

### 2.2 论文对标分析（来自Agent论文研究）

| 论文/框架 | 核心特性 | Paper Agent现状 | 差距 |
|-----------|---------|-----------------|------|
| **Voyager** | 技能库+迭代改进 | SkillAcquisitionEngine存在 | 需完善技能发现和演化 |
| **MetaGPT** | SOP驱动多Agent | MasterSupervisor存在 | 需SOP标准化 |
| **AutoGen** | 人机协作+代码执行 | 部分实现 | 需HIL机制 |
| **Reflexion** | 语言反馈自我反思 | CoT存在 | 需反思闭环 |
| **SWE-bench** | 真实软件任务评估 | 无 | 需领域基准 |
| **WebArena** | 网站导航任务 | 无 | 需环境交互 |

---

## 三、详细迭代计划（20+次迭代）

### 第1次迭代：Agent通信协议设计

**目标**: 建立标准化的Agent间通信协议

#### 1.1 设计消息格式

```python
@dataclass
class AgentMessage:
    """Agent通信消息格式"""
    id: str                           # 消息唯一ID (UUID)
    sender: str                      # 发送者Agent ID
    receiver: Optional[str]           # 接收者 (None=广播)
    message_type: MessageType        # 消息类型
    content: str                      # 消息内容
    metadata: Dict[str, Any]         # 元数据
    timestamp: float                  # 时间戳
    reply_to: Optional[str]           # 回复目标消息ID
    conversation_id: str              # 对话ID
    priority: MessagePriority = MessagePriority.NORMAL  # 优先级
    attachments: List[Attachment] = field(default_factory=list)  # 附件

class MessageType(Enum):
    REQUEST = "request"              # 请求
    RESPONSE = "response"             # 响应
    QUERY = "query"                   # 查询
    NOTIFY = "notify"                 # 通知
    ERROR = "error"                   # 错误
    HANDOFF = "handoff"               # 交接
    FEEDBACK = "feedback"             # 反馈

class MessagePriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3
```

#### 1.2 实现通信中间件

```python
class AgentCommunicationBus:
    """Agent通信总线"""

    def __init__(self):
        self._subscribers: Dict[str, List[Agent]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._message_history: List[AgentMessage] = []
        self._routing_rules: Dict[MessageType, Callable] = {}

    async def publish(self, message: AgentMessage) -> None:
        """发布消息"""
        self._message_history.append(message)
        if message.receiver:
            # 单播
            await self._deliver_to_agent(message.receiver, message)
        else:
            # 广播
            await self._broadcast(message)

    async def subscribe(self, agent: Agent, message_types: List[MessageType]) -> None:
        """订阅消息类型"""
        for msg_type in message_types:
            if msg_type not in self._subscribers:
                self._subscribers[msg_type] = []
            self._subscribers[msg_type].append(agent)

    async def _route_message(self, message: AgentMessage) -> None:
        """消息路由"""
        handler = self._routing_rules.get(message.message_type)
        if handler:
            await handler(message)
```

#### 1.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| AgentMessage格式 | 支持单播/广播/优先级 | ⏳ |
| 通信中间件 | 消息队列+历史 | ⏳ |
| 订阅机制 | 按消息类型订阅 | ⏳ |
| 消息追踪 | conversation_id追踪 | ⏳ |

---

### 第2次迭代：状态持久化与检查点机制

**目标**: 实现任务状态持久化和断点恢复

#### 2.1 检查点数据模型

```python
@dataclass
class Checkpoint:
    """任务检查点"""
    task_id: str
    phase: str
    checkpoint_id: str
    state_snapshot: PaperState        # 完整状态快照
    agent_states: Dict[str, AgentState]  # 各Agent状态
    memory_snapshot: MemorySnapshot   # 记忆快照
    timestamp: float
    parent_checkpoint_id: Optional[str]  # 父检查点（用于回溯）
    metadata: Dict[str, Any]

@dataclass
class AgentState:
    """Agent执行状态"""
    agent_id: str
    status: AgentStatus              # running/waiting/completed/failed
    current_action: str
    context: Dict[str, Any]
    local_memory: Dict[str, Any]
    checkpoints: List[str]           # 子检查点列表
```

#### 2.2 CheckpointManager实现

```python
class CheckpointManager:
    """检查点管理器"""

    def __init__(self, storage_path: str = ".checkpoints"):
        self.storage_path = storage_path
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._max_checkpoints_per_task = 10

    async def save_checkpoint(self, task_id: str, checkpoint: Checkpoint) -> str:
        """保存检查点"""
        checkpoint_id = f"{task_id}_{checkpoint.phase}_{int(time.time()*1000)}"
        checkpoint.checkpoint_id = checkpoint_id

        # 持久化到磁盘
        path = f"{self.storage_path}/{task_id}/{checkpoint_id}.json"
        await self._persist_to_disk(path, checkpoint)

        # 更新内存索引
        self._checkpoints[checkpoint_id] = checkpoint

        # 清理旧检查点
        await self._cleanup_old_checkpoints(task_id)

        return checkpoint_id

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """加载检查点"""
        if checkpoint_id in self._checkpoints:
            return self._checkpoints[checkpoint_id]

        # 从磁盘加载
        path = f"{self.storage_path}/**/{checkpoint_id}.json"
        # ... 实现磁盘加载逻辑
        return None

    async def recover_from_checkpoint(self, checkpoint_id: str) -> RecoveryResult:
        """从检查点恢复"""
        checkpoint = await self.load_checkpoint(checkpoint_id)
        if not checkpoint:
            return RecoveryResult(success=False, error="Checkpoint not found")

        # 恢复Agent状态
        for agent_id, agent_state in checkpoint.agent_states.items():
            await self._restore_agent_state(agent_id, agent_state)

        # 恢复记忆
        await self._restore_memory_snapshot(checkpoint.memory_snapshot)

        # 恢复PaperState
        self.state = checkpoint.state_snapshot

        return RecoveryResult(success=True, recovered_phase=checkpoint.phase)
```

#### 2.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| Checkpoint格式 | 完整状态快照 | ⏳ |
| 自动保存 | 每阶段自动创建 | ⏳ |
| 恢复机制 | 任意检查点恢复 | ⏳ |
| 清理策略 | 保留最近N个 | ⏳ |

---

### 第3次迭代：Token与成本实时追踪

**目标**: 实现精确的Token消耗和成本控制

#### 3.1 追踪数据模型

```python
@dataclass
class TokenUsage:
    """Token使用记录"""
    agent_id: str
    operation: str
    input_tokens: int
    output_tokens: int
    model: str
    timestamp: float
    cost_usd: float
    latency_ms: float

@dataclass
class BudgetTracker:
    """预算追踪器"""
    total_budget_usd: float
    spent_usd: float
    remaining_usd: float
    token_usage: List[TokenUsage]
    warning_threshold: float = 0.8  # 80%警告

    def can_afford(self, estimated_cost: float) -> bool:
        """检查是否能负担"""
        return self.remaining_usd >= estimated_cost

    def record_usage(self, usage: TokenUsage) -> None:
        """记录使用量"""
        self.token_usage.append(usage)
        self.spent_usd += usage.cost_usd
        self.remaining_usd = self.total_budget_usd - self.spent_usd

        if self.spent_usd / self.total_budget_usd >= self.warning_threshold:
            self._trigger_warning()
```

#### 3.2 实时成本追踪器

```python
class CostTracker:
    """实时成本追踪器"""

    MODEL_PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},  # per 1K tokens
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "claude-3": {"input": 0.015, "output": 0.075},
    }

    def __init__(self, total_budget: float = 10.0):
        self.total_budget = total_budget
        self.reset()

    def reset(self):
        self.total_spent = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.operation_costs: Dict[str, float] = {}
        self.agent_costs: Dict[str, float] = {}

    async def track_operation(
        self,
        agent_id: str,
        operation: str,
        input_text: str,
        output_text: str,
        model: str
    ) -> TokenUsage:
        """追踪单个操作的成本"""
        input_tokens = self._estimate_tokens(input_text)
        output_tokens = self._estimate_tokens(output_text)

        pricing = self.MODEL_PRICING.get(model, {"input": 0.01, "output": 0.03})
        cost = (input_tokens / 1000 * pricing["input"]) + (output_tokens / 1000 * pricing["output"])

        usage = TokenUsage(
            agent_id=agent_id,
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            timestamp=time.time(),
            cost_usd=cost,
            latency_ms=0  # 由调用者填充
        )

        self._record_usage(usage)
        return usage

    def _record_usage(self, usage: TokenUsage) -> None:
        """内部记录使用"""
        self.total_spent += usage.cost_usd
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens

        if usage.operation not in self.operation_costs:
            self.operation_costs[usage.operation] = 0
        self.operation_costs[usage.operation] += usage.cost_usd

        if usage.agent_id not in self.agent_costs:
            self.agent_costs[usage.agent_id] = 0
        self.agent_costs[usage.agent_id] += usage.cost_usd

    def get_report(self) -> CostReport:
        """获取成本报告"""
        return CostReport(
            total_budget=self.total_budget,
            total_spent=self.total_spent,
            remaining=self.total_budget - self.total_spent,
            input_tokens=self.total_input_tokens,
            output_tokens=self.total_output_tokens,
            operation_breakdown=self.operation_costs,
            agent_breakdown=self.agent_costs,
            utilization_percent=(self.total_spent / self.total_budget * 100) if self.total_budget > 0 else 0
        )
```

#### 3.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| TokenUsage记录 | 每次LLM调用记录 | ⏳ |
| 成本计算 | 实时计算USD | ⏳ |
| 预算警告 | 80%阈值触发 | ⏳ |
| 成本报告 | 详细分组统计 | ⏳ |
| 超出处理 | 自动降级/停止 | ⏳ |

---

### 第4次迭代：流式输出支持

**目标**: 实现LLM响应的流式输出，提升用户体验

#### 4.1 流式响应接口

```python
class StreamResponse:
    """流式响应对象"""

    def __init__(self):
        self._chunks: List[str] = []
        self._queue: asyncio.Queue = asyncio.Queue()

    async def write(self, chunk: str) -> None:
        """写入chunk"""
        self._chunks.append(chunk)
        await self._queue.put(chunk)

    async def read(self) -> str:
        """读取下一个chunk"""
        return await self._queue.get()

    def get_full_content(self) -> str:
        """获取完整内容"""
        return "".join(self._chunks)

class StreamingHandler:
    """流式处理器"""

    def __init__(self):
        self._active_streams: Dict[str, StreamResponse] = {}

    async def create_stream(self, task_id: str) -> StreamResponse:
        """创建流"""
        stream = StreamResponse()
        self._active_streams[task_id] = stream
        return stream

    async def stream_llm_response(self, prompt: str, task_id: str) -> StreamResponse:
        """流式获取LLM响应"""
        stream = await self.create_stream(task_id)

        async def generate():
            # 模拟流式生成（实际使用SDK的streaming）
            import openai
            client = openai.AsyncOpenAI()

            async with client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                stream=True
            ) as response:
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        await stream.write(chunk.choices[0].delta.content)

        # 后台运行生成
        asyncio.create_task(generate())
        return stream
```

#### 4.2 MasterSupervisor流式集成

```python
class MasterSupervisor:
    # ... 现有代码 ...

    async def run_streaming(
        self,
        task_type: str,
        input_data: Dict[str, Any]
    ) -> StreamResponse:
        """流式运行主流程"""
        stream = StreamingHandler().create_stream(f"{task_type}_{int(time.time())}")

        # 在每个阶段完成后立即输出
        for phase in self.PHASES:
            # 执行阶段
            result = await self._execute_phase_streaming(phase, input_data, stream)

            # 流式输出阶段结果
            if result.quality_score:
                await stream.write(f"\n[Phase {phase}] Quality: {result.quality_score.score}\n")

        await stream.write("\n[COMPLETE]")
        return stream
```

#### 4.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| StreamResponse | chunk队列管理 | ⏳ |
| LLM流式 | 实时token输出 | ⏳ |
| 阶段流式 | 阶段完成即输出 | ⏳ |
| SSE支持 | Server-Sent Events | ⏳ |
| WebSocket | 实时推送 | ⏳ |

---

### 第5次迭代：Agent角色系统与能力定义

**目标**: 建立标准化的Agent角色和能力定义体系

#### 5.1 角色定义模型

```python
@dataclass
class AgentRole:
    """Agent角色定义"""
    role_id: str
    name: str                         # 如 "文献搜索专家"
    description: str
    capabilities: List[Capability]   # 能力列表
    constraints: List[Constraint]     # 约束条件
    preferred_tools: List[str]        # 偏好的工具
    max_concurrent_tasks: int = 3     # 最大并发任务数
    timeout_seconds: float = 300      # 超时时间
    retry_policy: RetryPolicy         # 重试策略

@dataclass
class Capability:
    """能力定义"""
    name: str
    description: str
    input_types: List[str]           # 支持的输入类型
    output_types: List[str]          # 输出的类型
    quality_metrics: List[str]       # 质量指标
    examples: List[str]              # 示例场景

@dataclass
class Constraint:
    """约束条件"""
    type: ConstraintType              # TIME/COST/QUALITY/RESOURCE
    value: Any
    soft: bool = False               # 软约束可突破，硬约束不行

class ConstraintType(Enum):
    TIME = "time"                    # 时间约束
    COST = "cost"                    # 成本约束
    QUALITY = "quality"              # 质量约束
    RESOURCE = "resource"            # 资源约束
```

#### 5.2 角色注册表

```python
class AgentRoleRegistry:
    """Agent角色注册表"""

    def __init__(self):
        self._roles: Dict[str, AgentRole] = {}
        self._agent_role_mapping: Dict[str, str] = {}  # agent_id -> role_id

    def register_role(self, role: AgentRole) -> None:
        """注册角色"""
        self._roles[role.role_id] = role
        logger.info(f"Registered role: {role.name}")

    def assign_role_to_agent(self, agent_id: str, role_id: str) -> None:
        """为Agent分配角色"""
        self._agent_role_mapping[agent_id] = role_id
        role = self._roles.get(role_id)
        logger.info(f"Assigned {agent_id} -> role {role.name if role else 'unknown'}")

    def get_role_for_agent(self, agent_id: str) -> Optional[AgentRole]:
        """获取Agent的角色"""
        role_id = self._agent_role_mapping.get(agent_id)
        return self._roles.get(role_id)

    def find_best_role(self, task_requirements: Dict[str, Any]) -> Optional[AgentRole]:
        """根据任务需求找到最佳角色"""
        best_role = None
        best_score = 0

        for role in self._roles.values():
            score = self._calculate_role_match_score(role, task_requirements)
            if score > best_score:
                best_score = score
                best_role = role

        return best_role

    def _calculate_role_match_score(self, role: AgentRole, requirements: Dict) -> float:
        """计算机角色匹配分数"""
        # 简单实现：检查capabilities覆盖
        score = 0.0
        required_caps = requirements.get("required_capabilities", [])

        for cap in required_caps:
            for role_cap in role.capabilities:
                if cap in role_cap.name:
                    score += 1.0

        return score / max(len(required_caps), 1)
```

#### 5.3 预定义角色

```python
# 预定义的Paper Agent角色

RESEARCH_ANALYST = AgentRole(
    role_id="research_analyst",
    name="研究分析师",
    description="深入分析研究主题，识别研究空白和机会",
    capabilities=[
        Capability(
            name="literature_analysis",
            description="文献分析与综合",
            input_types=["topic", "papers"],
            output_types=["analysis_report", "research_gaps"]
        ),
        Capability(
            name="trend_identification",
            description="研究趋势识别",
            input_types=["field", "papers"],
            output_types=["trends", "forecasts"]
        )
    ],
    constraints=[
        Constraint(ConstraintType.QUALITY, 0.8, soft=True),
        Constraint(ConstraintType.TIME, 120, soft=True)
    ],
    preferred_tools=["arxiv_searcher", "pubmed_searcher"],
    max_concurrent_tasks=2
)

WRITING_SPECIALIST = AgentRole(
    role_id="writing_specialist",
    name="写作专家",
    description="专业学术写作，结构清晰论证严密",
    capabilities=[
        Capability(
            name="academic_writing",
            description="学术论文写作",
            input_types=["outline", "content"],
            output_types=["paper_draft", "sections"]
        ),
        Capability(
            name="revision",
            description="论文修订润色",
            input_types=["draft", "feedback"],
            output_types=["revised_draft"]
        )
    ],
    constraints=[
        Constraint(ConstraintType.QUALITY, 0.85, soft=False),
        Constraint(ConstraintType.TIME, 180, soft=True)
    ],
    preferred_tools=["draft_generator", "language_polisher"],
    max_concurrent_tasks=1
)
```

#### 5.4 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| AgentRole定义 | 完整角色模型 | ⏳ |
| Capability定义 | 能力标准化 | ⏳ |
| Constraint定义 | 约束分类 | ⏳ |
| 角色注册表 | 注册/查询/匹配 | ⏳ |
| 预定义角色 | 3+角色 | ⏳ |

---

### 第6次迭代：执行监控与决策追踪

**目标**: 实现完整的执行过程监控和决策追溯

#### 6.1 执行追踪数据模型

```python
@dataclass
class ExecutionTrace:
    """执行追踪记录"""
    trace_id: str
    task_id: str
    start_time: float
    end_time: Optional[float]
    phases: List[PhaseExecution]
    decisions: List[DecisionPoint]     # 关键决策点
    agent_executions: List[AgentExecution]
    errors: List[ErrorRecord]
    metadata: Dict[str, Any]

@dataclass
class DecisionPoint:
    """决策点"""
    decision_id: str
    timestamp: float
    context: str                       # 决策上下文
    options_considered: List[str]      # 考虑的选项
    selected_option: str               # 选择的选项
    reasoning: str                     # 决策理由
    agent_id: str                      # 做出决策的Agent

@dataclass
class AgentExecution:
    """Agent执行记录"""
    agent_id: str
    agent_role: str
    start_time: float
    end_time: Optional[float]
    action: str                        # 执行的动作
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    tokens_used: int
    cost_usd: float
    success: bool
    error_message: Optional[str]
```

#### 6.2 执行监控器

```python
class ExecutionMonitor:
    """执行监控器"""

    def __init__(self):
        self._active_traces: Dict[str, ExecutionTrace] = {}
        self._completed_traces: List[ExecutionTrace] = []
        self._decision_log: List[DecisionPoint] = []

    async def start_trace(self, task_id: str) -> str:
        """开始追踪"""
        trace_id = f"trace_{task_id}_{int(time.time()*1000)}"
        trace = ExecutionTrace(
            trace_id=trace_id,
            task_id=task_id,
            start_time=time.time(),
            phases=[],
            decisions=[],
            agent_executions=[],
            errors=[]
        )
        self._active_traces[task_id] = trace
        return trace_id

    async def record_decision(self, task_id: str, decision: DecisionPoint) -> None:
        """记录决策"""
        if task_id in self._active_traces:
            self._active_traces[task_id].decisions.append(decision)
        self._decision_log.append(decision)

        logger.info(f"Decision recorded: {decision.decision_id} - {decision.selected_option}")

    async def record_agent_execution(self, task_id: str, execution: AgentExecution) -> None:
        """记录Agent执行"""
        if task_id in self._active_traces:
            self._active_traces[task_id].agent_executions.append(execution)

    def get_trace_summary(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取追踪摘要"""
        trace = self._active_traces.get(task_id)
        if not trace:
            return None

        total_time = (trace.end_time or time.time()) - trace.start_time
        total_tokens = sum(e.tokens_used for e in trace.agent_executions)
        total_cost = sum(e.cost_usd for e in trace.agent_executions)

        return {
            "trace_id": trace.trace_id,
            "task_id": trace.task_id,
            "total_time": total_time,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "decision_count": len(trace.decisions),
            "agent_count": len(trace.agent_executions),
            "error_count": len(trace.errors),
            "phase_count": len(trace.phases)
        }

    def get_decision_insights(self, task_id: str) -> List[Dict[str, Any]]:
        """获取决策洞察"""
        trace = self._active_traces.get(task_id)
        if not trace:
            return []

        return [
            {
                "decision_id": d.decision_id,
                "context": d.context,
                "selected": d.selected_option,
                "reasoning": d.reasoning
            }
            for d in trace.decisions
        ]
```

#### 6.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| ExecutionTrace | 完整执行记录 | ⏳ |
| DecisionPoint | 决策追溯 | ⏳ |
| AgentExecution | 执行明细 | ⏳ |
| 监控仪表板 | 实时监控 | ⏳ |
| 决策洞察 | 分析建议 | ⏳ |

---

### 第7次迭代：工具版本管理与迁移

**目标**: 实现工具的版本管理和平滑迁移

#### 7.1 工具版本模型

```python
@dataclass
class ToolVersion:
    """工具版本"""
    version_id: str                   # 如 "search_papers_v2.1.0"
    tool_name: str
    version: str                      # 语义版本 "2.1.0"
    major: int                        # 主版本
    minor: int                        # 次版本
    patch: int                        # 补丁版本

    changelog: str                    # 变更日志
    created_at: float
    deprecated_at: Optional[float]    # 弃用时间
    sunset_at: Optional[float]        # 停用时间

    # 兼容性
    deprecated_args: List[str]        # 弃用的参数
    new_args: List[str]               # 新增参数
    migration_guide: str              # 迁移指南

    # 质量指标
    usage_count: int = 0
    success_rate: float = 1.0
    avg_latency_ms: float = 0

class ToolVersionRegistry:
    """工具版本注册表"""

    def __init__(self):
        self._tools: Dict[str, ToolVersion] = {}  # version_id -> version
        self._current_versions: Dict[str, str] = {}  # tool_name -> current_version_id
        self._version_history: Dict[str, List[str]] = {}  # tool_name -> [version_ids]

    def register_version(self, version: ToolVersion) -> None:
        """注册新版本"""
        # 检查版本冲突
        existing = self._current_versions.get(version.tool_name)
        if existing:
            current = self._tools.get(existing)
            if current and self._compare_versions(version.version, current.version) <= 0:
                raise ValueError(f"Version {version.version} is not newer than current {current.version}")

        self._tools[version.version_id] = version
        self._current_versions[version.tool_name] = version.version_id

        if version.tool_name not in self._version_history:
            self._version_history[version.tool_name] = []
        self._version_history[version.tool_name].append(version.version_id)

        logger.info(f"Registered tool version: {version.version_id}")

    def deprecate_version(self, version_id: str, deprecation_msg: str) -> None:
        """弃用版本"""
        version = self._tools.get(version_id)
        if version:
            version.deprecated_at = time.time()
            logger.warning(f"Tool version deprecated: {version_id} - {deprecation_msg}")

    def migrate_to_version(self, tool_name: str, target_version: str) -> MigrationPlan:
        """生成迁移计划"""
        current_version_id = self._current_versions.get(tool_name)
        if not current_version_id:
            raise ValueError(f"Tool {tool_name} not found")

        current = self._tools.get(current_version_id)
        target = self._tools.get(f"{tool_name}_{target_version}")

        return MigrationPlan(
            from_version=current.version,
            to_version=target.version,
            breaking_changes=self._find_breaking_changes(current, target),
            migration_steps=self._generate_migration_steps(current, target),
            rollback_plan=self._generate_rollback_plan(current)
        )
```

#### 7.2 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| ToolVersion模型 | 语义版本+兼容性 | ⏳ |
| 版本注册 | 注册/查询/历史 | ⏳ |
| 弃用管理 | 弃用通知+迁移 | ⏳ |
| 迁移计划 | 自动生成步骤 | ⏳ |
| 版本统计 | 使用率+成功率 | ⏳ |

---

### 第8次迭代：错误分类与智能恢复

**目标**: 建立标准化的错误分类体系和智能恢复策略

#### 8.1 错误分类模型

```python
class ErrorCategory(Enum):
    """错误分类"""
    # 输入相关
    INVALID_INPUT = "invalid_input"           # 输入无效
    MISSING_FIELD = "missing_field"           # 缺少必需字段
    FORMAT_ERROR = "format_error"              # 格式错误

    # 执行相关
    TIMEOUT = "timeout"                        # 执行超时
    RESOURCE_EXHAUSTED = "resource_exhausted"  # 资源耗尽
    EXTERNAL_SERVICE_ERROR = "external_service"  # 外部服务错误

    # LLM相关
    LLM_RATE_LIMIT = "llm_rate_limit"          # LLM限流
    LLM_INVALID_RESPONSE = "llm_invalid_response"  # LLM无效响应
    LLM_CONTEXT_OVERFLOW = "llm_context_overflow"  # 上下文溢出

    # 系统相关
    SYSTEM_ERROR = "system_error"              # 系统错误
    UNKNOWN = "unknown"                        # 未知错误

@dataclass
class ErrorRecord:
    """错误记录"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    stack_trace: Optional[str]
    context: Dict[str, Any]
    timestamp: float
    agent_id: Optional[str]
    task_id: Optional[str]
    recovery_attempted: bool = False
    recovery_successful: bool = False

class ErrorSeverity(Enum):
    LOW = 0.2         # 轻微问题，可忽略
    MEDIUM = 0.5      # 中等问题，需要处理
    HIGH = 0.8       # 严重问题，必须处理
    CRITICAL = 1.0    # 致命问题，系统级
```

#### 8.2 智能错误恢复器

```python
class IntelligentErrorRecovery:
    """智能错误恢复器"""

    RECOVERY_STRATEGIES = {
        ErrorCategory.INVALID_INPUT: ["validate_and_retry", "use_defaults"],
        ErrorCategory.TIMEOUT: ["retry_with_backoff", "reduce_scope"],
        ErrorCategory.LLM_RATE_LIMIT: ["rate_limit_backoff", "switch_model"],
        ErrorCategory.LLM_CONTEXT_OVERFLOW: ["truncate_context", "summarize_history"],
        ErrorCategory.EXTERNAL_SERVICE_ERROR: ["retry", "fallback_to_cache", "skip_step"],
        ErrorCategory.RESOURCE_EXHAUSTED: ["wait_for_resources", "reduce_batch_size"],
    }

    def __init__(self, llm: Any = None):
        self.llm = llm
        self._recovery_history: List[Dict] = []
        self._max_retries = 3

    async def handle_error(self, error: ErrorRecord) -> RecoveryResult:
        """处理错误"""
        category = error.category
        strategies = self.RECOVERY_STRATEGIES.get(category, ["log_and_continue"])

        for strategy in strategies:
            if self._can_apply_strategy(strategy, error):
                result = await self._apply_recovery_strategy(strategy, error)
                if result.success:
                    self._record_recovery(error, strategy, result)
                    return result

        # 所有策略都失败
        return RecoveryResult(
            success=False,
            strategy_attempted=strategies,
            error="All recovery strategies failed",
            fallback_action=self._get_fallback_action(error)
        )

    async def _apply_recovery_strategy(self, strategy: str, error: ErrorRecord) -> RecoveryResult:
        """应用恢复策略"""
        if strategy == "retry_with_backoff":
            return await self._retry_with_backoff(error)
        elif strategy == "reduce_scope":
            return await self._reduce_scope(error)
        elif strategy == "truncate_context":
            return await self._truncate_context(error)
        elif strategy == "switch_model":
            return await self._switch_model(error)
        # ... 更多策略

    async def _retry_with_backoff(self, error: ErrorRecord) -> RecoveryResult:
        """指数退避重试"""
        for attempt in range(self._max_retries):
            delay = 2 ** attempt  # 1, 2, 4, 8秒
            await asyncio.sleep(delay)

            try:
                # 重试原操作
                result = await self._retry_original_operation(error)
                if result.success:
                    return result
            except Exception as e:
                logger.warning(f"Retry attempt {attempt + 1} failed: {e}")
                continue

        return RecoveryResult(success=False, error="Max retries exceeded")
```

#### 8.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| ErrorCategory分类 | 12+错误类型 | ⏳ |
| ErrorSeverity | 4级严重程度 | ⏳ |
| RecoveryStrategy | 10+恢复策略 | ⏳ |
| 智能恢复 | 自动选择策略 | ⏳ |
| 恢复历史 | 策略效果追踪 | ⏳ |

---

### 第9次迭代：人机交互机制 (Human-in-the-loop)

**目标**: 引入人类介入机制，实现关键节点的审批和打断

#### 9.1 HIL接口定义

```python
class HumanInterventionType(Enum):
    """人类介入类型"""
    APPROVAL = "approval"             # 审批请求
    CORRECTION = "correction"         # 修正请求
    CONFIRMATION = "confirmation"     # 确认请求
    ABORT = "abort"                   # 中止请求

@dataclass
class InterventionRequest:
    """介入请求"""
    request_id: str
    intervention_type: HumanInterventionType
    agent_id: str
    task_id: str
    message: str                      # 向人类展示的消息
    options: List[str]                # 可选的操作
    context: Dict[str, Any]           # 上下文信息
    timeout_seconds: float = 300      # 等待超时
    timestamp: float
    status: InterventionStatus = InterventionStatus.PENDING

class HumanInTheLoopManager:
    """人机交互管理器"""

    def __init__(self):
        self._pending_requests: Dict[str, InterventionRequest] = {}
        self._approval_history: List[InterventionRequest] = []
        self._auto_approve_threshold: float = 0.9  # 高置信度自动批准

    async def request_approval(
        self,
        agent_id: str,
        task_id: str,
        message: str,
        options: List[str],
        context: Dict[str, Any]
    ) -> InterventionRequest:
        """请求人类审批"""
        request = InterventionRequest(
            request_id=f"hil_{int(time.time()*1000)}",
            intervention_type=HumanInterventionType.APPROVAL,
            agent_id=agent_id,
            task_id=task_id,
            message=message,
            options=options,
            context=context,
            timestamp=time.time()
        )

        self._pending_requests[request.request_id] = request

        # 检查是否可自动批准
        if self._should_auto_approve(context):
            await self._auto_approve(request)
        else:
            # 等待人工审批
            result = await self._wait_for_human_decision(request)

        return request

    async def request_correction(
        self,
        agent_id: str,
        task_id: str,
        current_output: str,
        expected_output: str,
        context: Dict[str, Any]
    ) -> InterventionRequest:
        """请求人类修正"""
        request = InterventionRequest(
            request_id=f"hil_{int(time.time()*1000)}",
            intervention_type=HumanInterventionType.CORRECTION,
            agent_id=agent_id,
            task_id=task_id,
            message=f"输出需要修正。当前: {current_output[:100]}... 期望: {expected_output[:100]}...",
            options=["accept_suggestion", "provide_alternative", "abort"],
            context=context,
            timestamp=time.time()
        )

        self._pending_requests[request.request_id] = request
        return request
```

#### 9.2 MasterSupervisor HIL集成

```python
class MasterSupervisor:
    # ... 现有代码 ...

    def __init__(self, llm_config: Optional[Any] = None):
        # ... 现有初始化 ...
        self.hil_manager = HumanInTheLoopManager()
        self.enable_hil = True

    async def run_with_hil(
        self,
        task_type: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """带人机交互的运行"""
        # 在关键节点检查是否需要HIL
        for phase in self.PHASES:
            # 检查置信度
            confidence = await self._estimate_phase_confidence(phase)

            if confidence < self.hil_manager._auto_approve_threshold and self.enable_hil:
                # 请求人类确认
                await self.hil_manager.request_approval(
                    agent_id="master_supervisor",
                    task_id=self.state.task_id,
                    message=f"Phase {phase} confidence is {confidence:.2f}",
                    options=["continue", "modify", "abort"],
                    context={"phase": phase, "state": self.state}
                )

            # 执行阶段
            result = await self._execute_phase(phase, input_data)

            # 检查是否需要人工审核最终结果
            if phase == "polish" and self.enable_hil:
                await self.hil_manager.request_confirmation(
                    agent_id="reviewer",
                    task_id=self.state.task_id,
                    message="论文润色完成，请确认是否满意",
                    final_output=result.output
                )
```

#### 9.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| InterventionRequest | 标准化请求 | ⏳ |
| HILManager | 审批/修正/确认 | ⏳ |
| 自动批准 | 高置信度跳过 | ⏳ |
| 超时处理 | 等待+超时 | ⏳ |
| 审批历史 | 完整记录 | ⏳ |

---

### 第10次迭代：上下文窗口智能管理

**目标**: 实现智能的上下文压缩和摘要策略

#### 10.1 上下文管理模型

```python
@dataclass
class ContextWindow:
    """上下文窗口"""
    max_tokens: int                   # 最大token数
    current_tokens: int               # 当前token数
    sections: List[ContextSection]    # 上下文分段

    def can_fit(self, additional_tokens: int) -> bool:
        """检查是否能容纳更多内容"""
        return self.current_tokens + additional_tokens <= self.max_tokens

    def add_section(self, section: ContextSection) -> bool:
        """添加分段"""
        if not self.can_fit(section.token_count):
            return False
        self.sections.append(section)
        self.current_tokens += section.token_count
        return True

@dataclass
class ContextSection:
    """上下文分段"""
    section_id: str
    content_type: ContentType         # SYSTEM/USER/HISTORY/RESULT/METADATA
    content: str
    token_count: int
    importance: float                 # 0-1 重要性
    is_summarizable: bool             # 是否可摘要
    compression_candidates: List[str]  # 可压缩的部分

class ContentType(Enum):
    SYSTEM = "system"                 # 系统指令
    USER = "user"                    # 用户输入
    HISTORY = "history"               # 对话历史
    RESULT = "result"                 # 中间结果
    METADATA = "metadata"             # 元数据

class ContextCompressionStrategy(Enum):
    NONE = "none"                    # 不压缩
    TRUNCATE = "truncate"            # 截断
    SUMMARIZE = "summarize"          # 摘要
    SELECTIVE = "selective"          # 选择性保留
    HIERARCHICAL = "hierarchical"    # 分层压缩
```

#### 10.2 智能上下文管理器

```python
class IntelligentContextManager:
    """智能上下文管理器"""

    # 保留优先级（从高到低）
    PRESERVE_PRIORITY = [
        ContentType.SYSTEM,      # 系统指令必须保留
        ContentType.USER,        # 用户输入保留
        ContentType.RESULT,      # 中间结果优先保留
        ContentType.HISTORY,     # 对话历史可压缩
        ContentType.METADATA,    # 元数据可丢弃
    ]

    def __init__(self, max_tokens: int = 128000):
        self.max_tokens = max_tokens
        self._compression_history: List[Dict] = []

    async def compress(
        self,
        context_window: ContextWindow,
        target_tokens: int
    ) -> ContextWindow:
        """压缩上下文到目标token数"""
        compressed = ContextWindow(
            max_tokens=self.max_tokens,
            current_tokens=0,
            sections=[]
        )

        # 计算需要删除的token
        tokens_to_remove = context_window.current_tokens - target_tokens

        # 按优先级处理
        for content_type in self.PRESERVE_PRIORITY:
            type_sections = [s for s in context_window.sections if s.content_type == content_type]

            for section in type_sections:
                if tokens_to_remove <= 0:
                    compressed.add_section(section)
                    continue

                # 检查是否可压缩
                if not section.is_summarizable:
                    if section.token_count <= tokens_to_remove:
                        tokens_to_remove -= section.token_count
                        continue
                    else:
                        # 无法压缩但空间不够，跳过
                        continue

                # 应用压缩策略
                if section.importance < 0.3:
                    # 低重要性：完全丢弃或大幅摘要
                    tokens_to_remove -= section.token_count
                elif section.importance < 0.7:
                    # 中等重要性：摘要
                    summarized = await self._summarize_section(section)
                    if summarized.token_count < section.token_count:
                        compressed.add_section(summarized)
                        tokens_to_remove -= (section.token_count - summarized.token_count)
                else:
                    # 高重要性：保留全部或精简
                    compressed.add_section(section)

        self._compression_history.append({
            "original_tokens": context_window.current_tokens,
            "target_tokens": target_tokens,
            "result_tokens": compressed.current_tokens,
            "sections_removed": len(context_window.sections) - len(compressed.sections)
        })

        return compressed

    async def _summarize_section(self, section: ContextSection) -> ContextSection:
        """摘要分段"""
        # 使用LLM进行摘要
        summary_prompt = f"""请将以下内容摘要到20%的长度，保留关键信息：

内容类型：{section.content_type.value}
内容：{section.content[:2000]}...

摘要："""

        # 简化实现，实际应调用LLM
        return ContextSection(
            section_id=f"{section.section_id}_summarized",
            content_type=section.content_type,
            content=f"[摘要] {section.content[:len(section.content)//5]}",
            token_count=section.token_count // 5,
            importance=section.importance,
            is_summarizable=False
        )

    def get_context_stats(self, context_window: ContextWindow) -> Dict[str, Any]:
        """获取上下文统计"""
        by_type = {}
        for section in context_window.sections:
            type_name = section.content_type.value
            if type_name not in by_type:
                by_type[type_name] = {"count": 0, "tokens": 0}
            by_type[type_name]["count"] += 1
            by_type[type_name]["tokens"] += section.token_count

        return {
            "total_tokens": context_window.current_tokens,
            "max_tokens": context_window.max_tokens,
            "utilization": context_window.current_tokens / context_window.max_tokens,
            "section_count": len(context_window.sections),
            "by_type": by_type
        }
```

#### 10.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| ContextWindow | 分段管理 | ⏳ |
| 保留优先级 | 5级优先级 | ⏳ |
| 压缩策略 | 5种策略 | ⏳ |
| 智能摘要 | LLM辅助 | ⏳ |
| 统计面板 | 使用率可视化 | ⏳ |

---

### 第11次迭代：Agent协作标记语言 (ACML)

**目标**: 设计并实现一种Agent协作标记语言，用于结构化多Agent任务分配

#### 11.1 ACML语言规范

```python
"""
ACML (Agent Collaboration Markup Language)

用于结构化描述多Agent协作任务的领域特定语言
"""

# 任务定义
TASK_TEMPLATE = """
<task id="{task_id}" name="{task_name}" priority="{priority}">
    <description>{description}</description>

    <roles>
        <role id="{role_id}" name="{role_name}" capabilities="{capabilities}"/>
    </roles>

    <steps>
        <step id="{step_id}" agent="{agent_id}" action="{action}">
            <input>{input_spec}</input>
            <output>{output_spec}</output>
            <timeout>{timeout_seconds}</timeout>
            <retry>{max_retries}</retry>
        </step>
    </steps>

    <dependencies>
        <depends on="{step_id}" when="{condition}"/>
    </dependencies>

    <quality_gate>
        <metric name="{metric_name}" threshold="{threshold}"/>
    </quality_gate>
</task>
"""

# 消息格式
MESSAGE_TEMPLATE = """
<message id="{msg_id}" type="{msg_type}" from="{sender}" to="{receiver}">
    <content>{content}</content>
    <conversation>{conversation_id}</conversation>
    <reply_to>{reply_to_msg_id}</reply_to>
    <metadata>
        <priority>{priority}</priority>
        <attachments>{attachment_list}</attachments>
    </metadata>
</message>
"""
```

#### 11.2 ACML解析器

```python
class ACMLParser:
    """ACML解析器"""

    def parse_task(self, acml_string: str) -> TaskDefinition:
        """解析任务定义"""
        # 提取task元素
        task_match = re.search(r'<task[^>]*>(.*?)</task>', acml_string, re.DOTALL)
        if not task_match:
            raise ValueError("Invalid ACML: missing task element")

        task_content = task_match.group(1)

        return TaskDefinition(
            id=self._extract_attribute(acml_string, 'task', 'id'),
            name=self._extract_attribute(acml_string, 'task', 'name'),
            description=self._extract_text(task_content, 'description'),
            steps=self._parse_steps(task_content),
            dependencies=self._parse_dependencies(task_content),
            quality_gates=self._parse_quality_gates(task_content)
        )

    def _parse_steps(self, task_content: str) -> List[StepDefinition]:
        """解析步骤"""
        steps = []
        step_matches = re.findall(r'<step[^>]*>(.*?)</step>', task_content, re.DOTALL)

        for match in step_matches:
            steps.append(StepDefinition(
                id=self._extract_attribute(match, 'step', 'id'),
                agent=self._extract_attribute(match, 'step', 'agent'),
                action=self._extract_attribute(match, 'step', 'action'),
                input_spec=self._extract_text(match, 'input'),
                output_spec=self._extract_text(match, 'output'),
                timeout=float(self._extract_attribute(match, 'step', 'timeout') or 300),
                max_retries=int(self._extract_attribute(match, 'step', 'retry') or 3)
            ))

        return steps

    def serialize_result(self, result: TaskResult) -> str:
        """序列化任务结果为ACML"""
        return f"""
<result task_id="{result.task_id}" success="{result.success}">
    <execution_time>{result.execution_time}</execution_time>
    <outputs>
        {"".join(f'<output step="{s.step_id}">{s.output}</output>' for s in result.step_results)}
    </outputs>
    <quality_metrics>
        {"".join(f'<metric name="{m.name}" value="{m.value}" passed="{m.passed}"/>' for m in result.quality_metrics)}
    </quality_metrics>
</result>
"""
```

#### 11.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| ACML规范 | 任务/消息模板 | ⏳ |
| 任务解析器 | 完整解析 | ⏳ |
| 依赖解析 | 条件依赖 | ⏳ |
| 结果序列化 | ACML输出 | ⏳ |
| 可视化编辑器 | 图形界面 | ⏳ |

---

### 第12次迭代：依赖自动解析与执行调度

**目标**: 实现基于依赖图的自动任务调度

#### 12.1 依赖图模型

```python
@dataclass
class TaskNode:
    """任务节点"""
    node_id: str
    task_definition: TaskDefinition
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)  # 依赖的node_id列表
    dependents: List[str] = field(default_factory=list)    # 依赖该节点的node_id列表

    # 执行信息
    assigned_agent: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Any] = None

    # 优先级
    priority: int = 0
    estimated_duration: float = 0

class TaskDependencyGraph:
    """任务依赖图"""

    def __init__(self):
        self._nodes: Dict[str, TaskNode] = {}
        self._adjacency_list: Dict[str, List[str]] = {}  # node_id -> [dependent_node_ids]

    def add_node(self, node: TaskNode) -> None:
        """添加节点"""
        self._nodes[node.node_id] = node
        if node.node_id not in self._adjacency_list:
            self._adjacency_list[node.node_id] = []

        # 更新依赖关系
        for dep_id in node.dependencies:
            if dep_id in self._nodes:
                self._nodes[dep_id].dependents.append(node.node_id)

    def get_executable_nodes(self, completed_ids: Set[str]) -> List[TaskNode]:
        """获取可执行的节点（所有依赖都已完成）"""
        executable = []

        for node_id, node in self._nodes.items():
            if node.status != TaskStatus.PENDING:
                continue

            # 检查所有依赖是否已完成
            if all(dep_id in completed_ids for dep_id in node.dependencies):
                executable.append(node)

        # 按优先级排序
        executable.sort(key=lambda n: n.priority, reverse=True)
        return executable
```

#### 12.2 自动调度器

```python
class AutomaticScheduler:
    """自动任务调度器"""

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self._running_tasks: Dict[str, TaskNode] = {}
        self._completed_tasks: Set[str] = set()

    async def schedule(self, graph: TaskDependencyGraph) -> SchedulingResult:
        """调度任务执行"""
        schedule_log = []

        while True:
            # 检查是否还有任务可执行
            executable = graph.get_executable_nodes(self._completed_tasks)

            if not executable and not self._running_tasks:
                # 所有任务完成或无法继续
                break

            # 如果运行中的任务数已达到上限，等待
            if len(self._running_tasks) >= self.max_concurrent:
                completed_id = await self._wait_for_any_completion()
                self._completed_tasks.add(completed_id)
                del self._running_tasks[completed_id]

            # 启动可执行的任务
            for node in executable[:self.max_concurrent - len(self._running_tasks)]:
                task = asyncio.create_task(self._execute_node(node))
                self._running_tasks[node.node_id] = node
                schedule_log.append(f"Started {node.node_id}")

        return SchedulingResult(
            scheduled_tasks=len(graph._nodes),
            completed_tasks=len(self._completed_tasks),
            execution_order=schedule_log
        )

    async def _execute_node(self, node: TaskNode) -> Any:
        """执行单个节点"""
        node.status = TaskStatus.RUNNING
        node.start_time = time.time()

        try:
            # 创建Agent执行
            result = await self._run_task(node.task_definition)

            node.status = TaskStatus.COMPLETED
            node.result = result
            node.end_time = time.time()

            return result

        except Exception as e:
            node.status = TaskStatus.FAILED
            logger.error(f"Task {node.node_id} failed: {e}")
            raise

    async def _wait_for_any_completion(self) -> str:
        """等待任意任务完成"""
        done, pending = await asyncio.wait(
            self._running_tasks.values(),
            return_when=asyncio.FIRST_COMPLETED
        )

        # 返回完成的task_id
        for node in self._running_tasks:
            if any(n.node_id == node for n in done):
                return node

        raise TimeoutError("No task completed")
```

#### 12.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| TaskDependencyGraph | 依赖图管理 | ⏳ |
| 拓扑排序 | 执行顺序 | ⏳ |
| 并发控制 | max_concurrent | ⏳ |
| 失败处理 | 跳过/中止 | ⏳ |
| 调度日志 | 完整记录 | ⏳ |

---

### 第13次迭代：反馈信号采集与信任更新

**目标**: 建立多维反馈信号采集和Agent信任度更新机制

#### 13.1 反馈信号模型

```python
@dataclass
class FeedbackSignal:
    """反馈信号"""
    signal_id: str
    source: FeedbackSource           # 信号来源
    target_agent: str               # 目标Agent
    signal_type: SignalType         # 信号类型

    # 数值
    value: float                    # 信号值 (-1 to 1 或 0 to 1)
    confidence: float               # 信号置信度

    # 上下文
    context: str                    # 反馈上下文
    task_id: Optional[str]
    timestamp: float

    # 用于信任计算
    weight: float = 1.0             # 信号权重

class FeedbackSource(Enum):
    USER = "user"                   # 用户直接反馈
    AUTOMATIC = "automatic"          # 自动评估
    PEER = "peer"                   # peer Agent评估
    SYSTEM = "system"               # 系统评估

class SignalType(Enum):
    QUALITY = "quality"             # 质量信号
    TIMELINESS = "timeliness"      # 时效信号
    COOPERATION = "cooperation"     # 协作信号
    RELIABILITY = "reliability"     # 可靠性信号
    ACCURACY = "accuracy"          # 准确性信号

@dataclass
class AgentTrustScore:
    """Agent信任分数"""
    agent_id: str
    overall_trust: float            # 综合信任度 (0-1)

    # 各维度信任
    quality_trust: float = 0.5
    timeliness_trust: float = 0.5
    cooperation_trust: float = 0.5
    reliability_trust: float = 0.5
    accuracy_trust: float = 0.5

    # 统计
    total_feedbacks: int = 0
    positive_feedbacks: int = 0
    last_updated: float

    # 趋势
    trend: TrustTrend = TrustTrend.STABLE  # UP/DOWN/STABLE
    recent_delta: float = 0
```

#### 13.2 信任更新引擎

```python
class TrustUpdateEngine:
    """信任更新引擎"""

    # 信号权重配置
    SIGNAL_WEIGHTS = {
        FeedbackSource.USER: 0.4,        # 用户反馈权重最高
        FeedbackSource.AUTOMATIC: 0.2,
        FeedbackSource.PEER: 0.2,
        FeedbackSource.SYSTEM: 0.2,
    }

    # 维度映射
    DIMENSION_MAP = {
        SignalType.QUALITY: "quality_trust",
        SignalType.TIMELINESS: "timeliness_trust",
        SignalType.COOPERATION: "cooperation_trust",
        SignalType.RELIABILITY: "reliability_trust",
        SignalType.ACCURACY: "accuracy_trust",
    }

    def __init__(self):
        self._trust_scores: Dict[str, AgentTrustScore] = {}
        self._feedback_history: Dict[str, List[FeedbackSignal]] = {}

    async def record_feedback(self, signal: FeedbackSignal) -> None:
        """记录反馈信号"""
        if signal.target_agent not in self._feedback_history:
            self._feedback_history[signal.target_agent] = []

        self._feedback_history[signal.target_agent].append(signal)

        # 更新信任
        await self.update_trust(signal)

    async def update_trust(self, signal: FeedbackSignal) -> AgentTrustScore:
        """根据反馈更新信任"""
        if signal.target_agent not in self._trust_scores:
            self._trust_scores[signal.target_agent] = AgentTrustScore(
                agent_id=signal.target_agent,
                overall_trust=0.5,
                last_updated=time.time()
            )

        trust = self._trust_scores[signal.target_agent]
        dimension = self.DIMENSION_MAP.get(signal.signal_type, "quality_trust")

        # 置信度加权更新
        current_value = getattr(trust, dimension, 0.5)
        weight = signal.weight * signal.confidence * self.SIGNAL_WEIGHTS.get(signal.source, 0.2)

        # 指数移动平均
        new_value = current_value * (1 - weight) + signal.value * weight
        setattr(trust, dimension, new_value)

        # 更新综合信任
        trust.overall_trust = (
            trust.quality_trust * 0.3 +
            trust.timeliness_trust * 0.2 +
            trust.cooperation_trust * 0.2 +
            trust.reliability_trust * 0.15 +
            trust.accuracy_trust * 0.15
        )

        trust.total_feedbacks += 1
        if signal.value > 0.5:
            trust.positive_feedbacks += 1

        trust.last_updated = time.time()

        # 更新趋势
        self._update_trend(trust, signal)

        return trust

    def _update_trend(self, trust: AgentTrustScore, signal: FeedbackSignal) -> None:
        """更新信任趋势"""
        recent_signals = self._feedback_history.get(trust.agent_id, [])[-10:]
        if len(recent_signals) < 3:
            trust.trend = TrustTrend.STABLE
            return

        avg_recent = sum(s.value for s in recent_signals) / len(recent_signals)
        older_signals = self._feedback_history.get(trust.agent_id, [])[-20:-10]
        avg_older = sum(s.value for s in older_signals) / len(older_signals) if older_signals else avg_recent

        trust.recent_delta = avg_recent - avg_older

        if trust.recent_delta > 0.1:
            trust.trend = TrustTrend.UP
        elif trust.recent_delta < -0.1:
            trust.trend = TrustTrend.DOWN
        else:
            trust.trend = TrustTrend.STABLE
```

#### 13.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| FeedbackSignal | 完整反馈模型 | ⏳ |
| 4+反馈来源 | User/Auto/Peer/System | ⏳ |
| 5维信任分数 | 细分维度 | ⏳ |
| 信任更新引擎 | 置信度加权 | ⏳ |
| 趋势分析 | UP/DOWN/STABLE | ⏳ |

---

### 第14次迭代：增量学习与技能演化

**目标**: 实现技能库的增量学习和自动演化机制

#### 14.1 技能演化模型

```python
@dataclass
class SkillEvolution:
    """技能演化记录"""
    skill_id: str
    evolution_type: EvolutionType   # IMPROVE/ADAPT/SPECIALIZE/GENERALIZE/MERGE/SPLIT

    # 变化前
    before_state: Dict[str, Any]

    # 变化后
    after_state: Dict[str, Any]

    # 触发原因
    trigger: EvolutionTrigger
    trigger_context: Dict[str, Any]

    # 效果评估
    improvement_score: float         # 改进分数
    feedback_impact: float           # 反馈影响

    timestamp: float

class EvolutionType(Enum):
    IMPROVE = "improve"             # 改进现有技能
    ADAPT = "adapt"                 # 适应新场景
    SPECIALIZE = "specialize"       # 特化技能
    GENERALIZE = "generalize"       # 泛化技能
    MERGE = "merge"                 # 合并技能
    SPLIT = "split"                 # 拆分技能

class EvolutionTrigger(Enum):
    SUCCESS_PATTERN = "success_pattern"     # 成功模式重复
    FAILURE_PATTERN = "failure_pattern"     # 失败模式重复
    FEEDBACK_SIGNAL = "feedback_signal"     # 反馈信号触发
    CONTEXT_CHANGE = "context_change"       # 上下文变化
    USER_REQUEST = "user_request"           # 用户请求

@dataclass
class SkillGenome:
    """技能基因组 - 用于技能演化和匹配"""
    skill_id: str
    genes: Dict[str, GeneValue]      # 基因名称 -> 基因值

    # 基因类别
    functional_genes: List[str]       # 功能基因
    behavioral_genes: List[str]       # 行为基因
    quality_genes: List[str]          # 质量基因

@dataclass
class GeneValue:
    """基因值"""
    value: Any
    mutation_rate: float              # 突变率
    dominance: float                 # 显性度 (0-1)
    expression: str                  # 表达形式
```

#### 14.2 技能演化引擎

```python
class SkillEvolutionEngine:
    """技能演化引擎"""

    def __init__(self, llm: Any = None):
        self.llm = llm
        self._evolution_history: List[SkillEvolution] = []
        self._skill_genomes: Dict[str, SkillGenome] = {}

    async def analyze_evolution_needed(self, skill: Skill) -> List[EvolutionTrigger]:
        """分析是否需要演化"""
        triggers = []

        # 分析成功率趋势
        recent_success_rate = self._calculate_recent_success_rate(skill)
        if recent_success_rate < 0.6:
            triggers.append(EvolutionTrigger.FAILURE_PATTERN)

        # 分析反馈信号
        feedback_trend = await self._get_feedback_trend(skill.id)
        if feedback_trend == "declining":
            triggers.append(EvolutionTrigger.FEEDBACK_SIGNAL)

        # 分析使用模式变化
        usage_change = self._detect_usage_pattern_change(skill)
        if usage_change:
            triggers.append(EvolutionTrigger.CONTEXT_CHANGE)

        return triggers

    async def evolve_skill(
        self,
        skill: Skill,
        trigger: EvolutionTrigger,
        context: Dict[str, Any]
    ) -> Skill:
        """执行技能演化"""
        if trigger == EvolutionTrigger.FAILURE_PATTERN:
            return await self._improve_skill(skill, context)
        elif trigger == EvolutionTrigger.CONTEXT_CHANGE:
            return await self._adapt_skill(skill, context)
        elif trigger == EvolutionTrigger.SUCCESS_PATTERN:
            return await self._specialize_skill(skill, context)

    async def _improve_skill(self, skill: Skill, context: Dict[str, Any]) -> Skill:
        """改进技能"""
        # 分析失败案例
        failed_cases = context.get("failed_cases", [])

        if self.llm and failed_cases:
            # 使用LLM分析改进方向
            prompt = f"""
分析以下失败案例，生成技能改进建议：

失败案例：
{chr(10).join(failed_cases[:5])}

请提供：
1. 失败原因分析
2. 技能代码改进建议
3. 新的适用场景
"""
            result = await self.llm.agenerate([prompt])
            improvement = self._parse_improvement(result.generations[0][0].text)

            # 创建新版本技能
            new_skill = Skill(
                id=f"{skill.id}_evolved_{int(time.time())}",
                name=skill.name,
                description=skill.description,
                code=improvement.get("new_code", skill.code),
                success_rate=max(skill.success_rate, improvement.get("expected_rate", 0.7)),
                usage_count=0,
                metadata={
                    "evolved_from": skill.id,
                    "evolution_type": EvolutionType.IMPROVE.value,
                    "improvement": improvement
                }
            )

            # 记录演化
            self._record_evolution(
                skill.id,
                EvolutionType.IMPROVE,
                {"code": skill.code},
                {"code": new_skill.code},
                trigger,
                context
            )

            return new_skill

        return skill

    async def merge_skills(self, skill_ids: List[str]) -> Optional[Skill]:
        """合并技能"""
        if len(skill_ids) < 2:
            return None

        skills = [self._skill_library[sid] for sid in skill_ids if sid in self._skill_library]
        if len(skills) < 2:
            return None

        # 分析技能相似性和互补性
        merged_description = self._generate_merged_description(skills)
        merged_code = self._generate_merged_code(skills)

        return Skill(
            id=f"merged_{int(time.time())}",
            name=f"Merged Skill ({len(skills)})",
            description=merged_description,
            code=merged_code,
            success_rate=max(s.success_rate for s in skills),
            metadata={"merged_from": skill_ids, "skill_count": len(skills)}
        )
```

#### 14.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| SkillEvolution | 完整演化记录 | ⏳ |
| 6种演化类型 | Improve/Adapt/Specialize等 | ⏳ |
| 5种触发器 | 失败模式/反馈/上下文等 | ⏳ |
| 演化引擎 | 自动分析+执行 | ⏳ |
| 技能合并/拆分 | 基因组操作 | ⏳ |

---

### 第15次迭代：多模态理解深度增强

**目标**: 深化图表、公式、流程图的多模态理解能力

#### 15.1 多模态理解模型

```python
@dataclass
class MultimodalContent:
    """多模态内容"""
    content_id: str
    content_type: MultimodalType     # IMAGE/TABLE/FORMULA/DIAGRAM/CHART

    # 原始数据
    raw_data: Any                    # 原始数据（base64/LaTeX/SVG等）

    # 解析结果
    parsed_content: Dict[str, Any]   # 解析后的内容
    semantic_annotation: Dict[str, Any]  # 语义标注

    # 质量指标
    parsing_confidence: float        # 解析置信度
    semantic_quality: float          # 语义质量

    # 关联信息
    references: List[str]           # 关联的引用
    context_dependencies: List[str]  # 上下文依赖

class MultimodalType(Enum):
    IMAGE = "image"
    TABLE = "table"
    FORMULA = "formula"
    DIAGRAM = "diagram"
    CHART = "chart"
    FLOWCHART = "flowchart"
    TIMING_DIAGRAM = "timing_diagram"
    STATE_DIAGRAM = "state_diagram"

@dataclass
class FigureAnalysis:
    """图表分析结果"""
    figure_type: str                  # 图表子类型
    components: List[FigureComponent]  # 组件列表
    relationships: List[ComponentRelation]  # 组件关系
    data_extraction: Dict[str, Any]  # 提取的数据
    description: str                 # 自然语言描述
    key_insights: List[str]          # 关键洞察
```

#### 15.2 深度理解处理器

```python
class MultimodalDeepUnderstander:
    """多模态深度理解处理器"""

    def __init__(self, vision_encoder: Any = None, llm: Any = None):
        self.vision_encoder = vision_encoder
        self.llm = llm

    async def deep_analyze(self, content: MultimodalContent) -> DeepAnalysisResult:
        """深度分析多模态内容"""
        if content.content_type == MultimodalType.CHART:
            return await self._analyze_chart(content)
        elif content.content_type == MultimodalType.FORMULA:
            return await self._analyze_formula(content)
        elif content.content_type == MultimodalType.DIAGRAM:
            return await self._analyze_diagram(content)
        elif content.content_type == MultimodalType.TABLE:
            return await self._analyze_table(content)

    async def _analyze_chart(self, content: MultimodalContent) -> DeepAnalysisResult:
        """深度分析图表"""
        # 1. 识别图表类型（折线/柱状/散点/热力/饼图等）
        chart_type = await self._classify_chart_type(content)

        # 2. 提取数据系列
        data_series = await self._extract_data_series(content, chart_type)

        # 3. 分析趋势和模式
        trend_analysis = await self._analyze_trends(data_series)

        # 4. 检测异常点
        anomalies = await self._detect_anomalies(data_series)

        # 5. 生成描述性分析
        description = await self._generate_chart_description(
            chart_type, data_series, trend_analysis
        )

        # 6. 提取关键洞察
        insights = await self._extract_key_insights(
            chart_type, data_series, trend_analysis, anomalies
        )

        return DeepAnalysisResult(
            primary_type=chart_type,
            extracted_data=data_series,
            trend_analysis=trend_analysis,
            anomalies=anomalies,
            description=description,
            insights=insights,
            confidence=self._calculate_confidence(content)
        )
```

#### 15.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| MultimodalContent | 标准化多模态 | ⏳ |
| 图表深度分析 | 7+图表类型 | ⏳ |
| 公式结构解析 | LaTeX AST | ⏳ |
| 流程图解析 | 时序图/状态图 | ⏳ |
| 跨模态推理 | 图文联合 | ⏳ |

---

### 第16次迭代：实时性能优化

**目标**: 实现系统级的实时性能监控和自动优化

#### 16.1 性能指标模型

```python
@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: float

    # 延迟指标
    latency_p50: float               # P50延迟
    latency_p95: float               # P95延迟
    latency_p99: float               # P99延迟
    latency_max: float               # 最大延迟

    # 吞吐量指标
    throughput_rps: float           # 每秒请求数
    concurrent_requests: int         # 并发请求数

    # 资源指标
    cpu_usage: float                 # CPU使用率
    memory_usage: float              # 内存使用率
    gpu_usage: float = 0.0          # GPU使用率

    # 质量指标
    quality_score_avg: float         # 平均质量分数
    error_rate: float                # 错误率

    # 成本指标
    cost_per_request: float          # 单次请求成本
    total_cost_hourly: float          # 小时总成本

class PerformanceProfile:
    """性能画像"""
    agent_id: str
    operation: str
    avg_latency: float
    p95_latency: float
    throughput: float
    success_rate: float
    common_failures: List[str]
    optimization_hints: List[str]
```

#### 16.2 实时性能监控器

```python
class RealTimePerformanceMonitor:
    """实时性能监控器"""

    def __init__(self):
        self._metrics_buffer: List[PerformanceMetrics] = []
        self._agent_profiles: Dict[str, PerformanceProfile] = {}
        self._alerts: List[PerformanceAlert] = []
        self._optimization_enabled = True

    async def record_metric(self, metric: PerformanceMetrics) -> None:
        """记录性能指标"""
        self._metrics_buffer.append(metric)

        # 检查是否触发告警
        await self._check_alerts(metric)

        # 更新Agent画像
        await self._update_profiles(metric)

        # 触发自动优化
        if self._optimization_enabled:
            await self._check_optimization_opportunities(metric)

    async def _check_optimization_opportunities(self, metric: PerformanceMetrics) -> None:
        """检查优化机会"""
        if metric.latency_p95 > 5000:  # P95 > 5s
            await self._suggest_latency_optimization(metric)

        if metric.cpu_usage > 0.8:  # CPU > 80%
            await self._suggest_scaling_optimization(metric)

        if metric.error_rate > 0.05:  # 错误率 > 5%
            await self._suggest_reliability_optimization(metric)

    async def _suggest_latency_optimization(self, metric: PerformanceMetrics) -> None:
        """建议延迟优化"""
        suggestions = []

        # 分析慢查询
        slow_operations = await self._find_slow_operations(metric)
        for op in slow_operations:
            if op["type"] == "llm_inference":
                suggestions.append(
                    OptimizationSuggestion(
                        type=OptimizationType.LLM_CACHING,
                        target=op["agent_id"],
                        expected_improvement=0.3,
                        implementation="Add result caching for repeated queries"
                    )
                )
            elif op["type"] == "retrieval":
                suggestions.append(
                    OptimizationSuggestion(
                        type=OptimizationType.RETRIEVAL_INDEXING,
                        target=op["agent_id"],
                        expected_improvement=0.4,
                        implementation="Optimize index structure or add pre-filtering"
                    )
                )

        # 应用高置信度建议
        for suggestion in suggestions:
            if suggestion.expected_improvement > 0.25:
                await self._apply_optimization(suggestion)
```

#### 16.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| PerformanceMetrics | 完整指标 | ⏳ |
| 延迟追踪 | P50/P95/P99/Max | ⏳ |
| 吞吐量监控 | RPS+并发 | ⏳ |
| 资源监控 | CPU/Memory/GPU | ⏳ |
| 自动优化 | 缓存/索引/调度 | ⏳ |

---

### 第17次迭代：安全与权限强化

**目标**: 实现细粒度的安全控制和审计机制

#### 17.1 安全模型

```python
@dataclass
class SecurityContext:
    """安全上下文"""
    user_id: str
    session_id: str
    permissions: Set[Permission]
    ip_address: Optional[str]
    user_agent: Optional[str]
    risk_level: RiskLevel = RiskLevel.LOW

class Permission(Enum):
    # 数据权限
    READ_PAPER = "read_paper"
    WRITE_PAPER = "write_paper"
    DELETE_PAPER = "delete_paper"
    SHARE_PAPER = "share_paper"

    # Agent权限
    EXECUTE_AGENT = "execute_agent"
    CONFIGURE_AGENT = "configure_agent"
    VIEW_AGENT_LOGS = "view_agent_logs"

    # 系统权限
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    CONFIGURE_SYSTEM = "configure_system"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class DataClassification:
    """数据分类"""
    classification: DataLevel
    sensitivity: float                # 0-1 敏感度
    encryption_required: bool
    retention_period: int            # 保留天数

class DataLevel(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
```

#### 17.2 安全执行引擎

```python
class SecurityEngine:
    """安全执行引擎"""

    def __init__(self):
        self._policy_engine = PolicyEngine()
        self._threat_detector = ThreatDetector()
        self._audit_logger = AuditLogger()

    async def authorize_action(
        self,
        context: SecurityContext,
        action: str,
        resource: str
    ) -> AuthorizationResult:
        """授权操作"""
        # 1. 权限检查
        permission = self._get_required_permission(action, resource)
        if permission not in context.permissions:
            self._audit_logger.log_denied_access(context, action, resource)
            return AuthorizationResult(
                authorized=False,
                reason=f"Missing permission: {permission.value}"
            )

        # 2. 风险评估
        risk_score = await self._threat_detector.assess_risk(context, action, resource)
        if risk_score > 0.7:
            self._audit_logger.log_high_risk_action(context, action, resource, risk_score)

        # 3. 额外验证（高风险操作）
        if risk_score > 0.5:
            verified = await self._verify_high_risk_action(context, action, resource)
            if not verified:
                return AuthorizationResult(
                    authorized=False,
                    reason="High-risk action verification failed"
                )

        self._audit_logger.log_authorized_access(context, action, resource)
        return AuthorizationResult(authorized=True)

    async def _verify_high_risk_action(
        self,
        context: SecurityContext,
        action: str,
        resource: str
    ) -> bool:
        """验证高风险操作"""
        # 可能需要多因素认证或其他验证
        if context.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            # 需要额外验证
            return await self._require_additional_verification(context)
        return True
```

#### 17.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| SecurityContext | 完整安全上下文 | ⏳ |
| Permission枚举 | 15+权限定义 | ⏳ |
| RiskLevel | 4级风险评估 | ⏳ |
| DataClassification | 4级数据分类 | ⏳ |
| 审计日志 | 完整操作记录 | ⏳ |

---

### 第18次迭代：端到端测试与质量保证

**目标**: 建立完整的端到端测试框架和质量管理流程

#### 18.1 测试框架模型

```python
@dataclass
class TestScenario:
    """测试场景"""
    scenario_id: str
    name: str
    description: str
    test_type: TestType             # UNIT/INTEGRATION/E2E/PERFORMANCE

    # 测试数据
    input_data: Dict[str, Any]
    expected_output: Any
    validation_rules: List[ValidationRule]

    # 执行配置
    timeout_seconds: float = 300
    retry_count: int = 3
    dependencies: List[str] = []     # 前置测试

class ValidationRule:
    """验证规则"""
    rule_type: ValidationType        # EQUAL/CONTAIN/REGEX/SCHEMA/QUALITY
    expected: Any
    tolerance: float = 0.0          # 容差
    weight: float = 1.0             # 权重

class TestResult:
    """测试结果"""
    scenario_id: str
    status: TestStatus               # PASS/FAIL/ERROR/SKIP
    duration_ms: float
    output: Any
    validation_results: List[ValidationResult]
    error_message: Optional[str]
    screenshots: List[str] = []     # 截图（用于UI测试）
```

#### 18.2 E2E测试运行器

```python
class E2ETestRunner:
    """端到端测试运行器"""

    def __init__(self):
        self._scenarios: Dict[str, TestScenario] = {}
        self._results: List[TestResult] = []
        self._coverage_tracker = CoverageTracker()

    async def run_test_suite(
        self,
        suite_name: str,
        test_filter: Optional[str] = None,
        parallel: bool = True
    ) -> TestSuiteResult:
        """运行测试套件"""
        scenarios = self._get_scenarios(suite_name, test_filter)

        if parallel:
            results = await self._run_parallel(scenarios)
        else:
            results = await self._run_sequential(scenarios)

        # 生成报告
        return self._generate_suite_report(results)

    async def _run_parallel(self, scenarios: List[TestScenario]) -> List[TestResult]:
        """并行运行测试"""
        tasks = []
        for scenario in scenarios:
            # 检查依赖
            if await self._check_dependencies(scenario):
                task = self._execute_scenario(scenario)
                tasks.append(task)
            else:
                tasks.append(asyncio.create_task(self._skip_scenario(scenario, "Dependencies not met")))

        return await asyncio.gather(*tasks)

    async def _execute_scenario(self, scenario: TestScenario) -> TestResult:
        """执行单个测试场景"""
        start_time = time.time()

        try:
            # 设置测试环境
            await self._setup_test_env(scenario)

            # 执行测试
            output = await self._execute_test_logic(scenario)

            # 验证结果
            validation_results = await self._validate_output(scenario, output)

            # 计算总体状态
            all_passed = all(v.passed for v in validation_results)
            status = TestStatus.PASS if all_passed else TestStatus.FAIL

            return TestResult(
                scenario_id=scenario.scenario_id,
                status=status,
                duration_ms=(time.time() - start_time) * 1000,
                output=output,
                validation_results=validation_results
            )

        except Exception as e:
            return TestResult(
                scenario_id=scenario.scenario_id,
                status=TestStatus.ERROR,
                duration_ms=(time.time() - start_time) * 1000,
                output=None,
                validation_results=[],
                error_message=str(e)
            )
```

#### 18.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| TestScenario | 完整测试场景 | ⏳ |
| 4种测试类型 | Unit/Int/E2E/Perf | ⏳ |
| ValidationRule | 5种验证类型 | ⏳ |
| 并行执行 | 多进程/多线程 | ⏳ |
| 覆盖率追踪 | 分支/函数覆盖 | ⏳ |
| 测试报告 | HTML/JSON报告 | ⏳ |

---

### 第19次迭代：文档与示例完善

**目标**: 完善所有模块的API文档和使用示例

#### 19.1 文档生成规范

```python
"""
API Documentation Template

每个公共类和方法必须包含:

1. 类/方法描述
2. 参数说明 (Args/Parameters)
3. 返回值说明 (Returns)
4. 异常说明 (Raises)
5. 使用示例 (Example)
6. 注意事项 (Note)
"""

class Example:
    """
    类名 - 简短描述

    详细描述类的功能和用途。

    Args:
        param1: 参数1的描述，类型，默认值
        param2: 参数2的描述，类型，默认值

    Returns:
        返回值描述，类型

    Raises:
        ValueError: 当xxx时
        TimeoutError: 当xxx时

    Example:
        >>> from module import Example
        >>> example = Example(param1="value")
        >>> result = await example.execute()
        >>> print(result)

    Note:
        - 注意事项1
        - 注意事项2
    """
```

#### 19.2 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| 所有公共API文档 | 完整docstring | ⏳ |
| 使用示例 | 3+示例每个类 | ⏳ |
| 错误处理文档 | 所有异常类型 | ⏳ |
| 类型注解 | 完整类型提示 | ⏳ |
| 更新日志 | CHANGELOG.md | ⏳ |

---

### 第20次迭代：集成测试与性能基准

**目标**: 建立完整的集成测试和性能基准体系

#### 20.1 性能基准模型

```python
@dataclass
class PerformanceBenchmark:
    """性能基准"""
    benchmark_id: str
    name: str
    description: str
    test_category: BenchmarkCategory  # LATENCY/THROUGHPUT/ACCURACY/SCALABILITY

    # 配置
    workload: WorkloadConfig
    constraints: BenchmarkConstraints

    # 预期结果
    target_metrics: Dict[str, float]

    # 实际结果
    actual_metrics: Optional[Dict[str, float]] = None

class BenchmarkCategory(Enum):
    LATENCY = "latency"              # 延迟基准
    THROUGHPUT = "throughput"        # 吞吐量基准
    ACCURACY = "accuracy"            # 准确性基准
    SCALABILITY = "scalability"      # 可扩展性基准

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    benchmark_id: str
    passed: bool
    execution_time: float

    # 指标对比
    target_vs_actual: Dict[str, Tuple[float, float]]

    # 性能得分
    score: float                     # 0-100

    # 详细报告
    details: Dict[str, Any]

    recommendations: List[str]      # 优化建议
```

#### 20.2 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| 性能基准套件 | 20+基准测试 | ⏳ |
| 延迟基准 | P50/P95/P99 | ⏳ |
| 吞吐量基准 | RPS测试 | ⏳ |
| 准确性基准 | 质量评估 | ⏳ |
| 扩展性基准 | 规模测试 | ⏳ |
| 自动化CI/CD | 集成到CI | ⏳ |

---

### 第20次迭代：端到端测试与性能基准

**目标**: 建立完整的集成测试和性能基准体系

#### 20.1 性能基准模型

```python
@dataclass
class PerformanceBenchmark:
    """性能基准"""
    benchmark_id: str
    name: str
    description: str
    test_category: BenchmarkCategory  # LATENCY/THROUGHPUT/ACCURACY/SCALABILITY

    # 配置
    workload: WorkloadConfig
    constraints: BenchmarkConstraints

    # 预期结果
    target_metrics: Dict[str, float]

    # 实际结果
    actual_metrics: Optional[Dict[str, float]] = None

class BenchmarkCategory(Enum):
    LATENCY = "latency"              # 延迟基准
    THROUGHPUT = "throughput"        # 吞吐量基准
    ACCURACY = "accuracy"            # 准确性基准
    SCALABILITY = "scalability"      # 可扩展性基准

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    benchmark_id: str
    passed: bool
    execution_time: float

    # 指标对比
    target_vs_actual: Dict[str, Tuple[float, float]]

    # 性能得分
    score: float                     # 0-100

    # 详细报告
    details: Dict[str, Any]

    recommendations: List[str]      # 优化建议
```

#### 20.2 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| 性能基准套件 | 20+基准测试 | ⏳ |
| 延迟基准 | P50/P95/P99 | ⏳ |
| 吞吐量基准 | RPS测试 | ⏳ |
| 准确性基准 | 质量评估 | ⏳ |
| 扩展性基准 | 规模测试 | ⏳ |
| 自动化CI/CD | 集成到CI | ⏳ |

---

## 第21次迭代：本地模型部署支持

**目标**: 实现本地小模型部署支持，支持Ollama/vLLM/LM Studio等

### 21.1 本地模型架构

```python
@dataclass
class LocalModelConfig:
    """本地模型配置"""
    provider: LocalModelProvider     # ollama/vllm/lm_studio
    model_name: str                 # 模型名称
    base_url: str                  # 服务地址
    api_key: Optional[str] = None  # API密钥（可选）

    # 模型参数
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

    # 特定提供商配置
    ollama_options: Optional[Dict] = None  # num_ctx, num_gpu等
    vllm_options: Optional[Dict] = None     # tensor_parallel, gpu_memory等

class LocalModelProvider(Enum):
    OLLAMA = "ollama"              # Ollama本地服务
    VLLM = "vllm"                  # vLLM推理服务器
    LM_STUDIO = "lm_studio"        # LM Studio
    APILOCAL = "api_local"         # 通用的本地API
    TEXTGEN = "textgen"           # Text Generation WebUI
    OOBABOOGA = "oobabooga"       # Oobabooga

@dataclass
class ModelEndpoint:
    """模型端点"""
    name: str
    provider: LocalModelProvider
    url: str
    capabilities: List[str]        # 能力列表
    max_context_length: int        # 最大上下文长度
    supports_streaming: bool       # 是否支持流式
    is_available: bool             # 是否可用
    load_time_ms: float = 0        # 加载时间
```

### 21.2 本地模型管理器

```python
class LocalModelManager:
    """本地模型管理器"""

    def __init__(self):
        self._endpoints: Dict[str, ModelEndpoint] = {}
        self._active_model: Optional[str] = None
        self._model_cache: Dict[str, Any] = {}
        self._health_check_interval = 60  # 秒

    async def register_endpoint(self, endpoint: ModelEndpoint) -> None:
        """注册模型端点"""
        self._endpoints[endpoint.name] = endpoint
        logger.info(f"Registered endpoint: {endpoint.name} ({endpoint.provider.value})")

    async def discover_ollama_models(self, base_url: str = "http://localhost:11434") -> List[str]:
        """自动发现Ollama可用模型"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Ollama discovery failed: {e}")
        return []

    async def health_check(self, endpoint_name: str) -> bool:
        """检查端点健康状态"""
        endpoint = self._endpoints.get(endpoint_name)
        if not endpoint:
            return False

        try:
            # 发送测试请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{endpoint.url}/chat/completions",
                    json={"model": endpoint.name, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    endpoint.is_available = resp.status == 200
        except Exception:
            endpoint.is_available = False

        return endpoint.is_available

    async def generate(
        self,
        model_name: str,
        prompt: str,
        stream: bool = False,
        options: Optional[Dict] = None
    ) -> Union[str, AsyncIterator[str]]:
        """生成文本"""
        endpoint = self._endpoints.get(model_name)
        if not endpoint or not endpoint.is_available:
            raise ValueError(f"Model {model_name} not available")

        if endpoint.provider == LocalModelProvider.OLLAMA:
            return await self._ollama_generate(endpoint, prompt, stream, options)
        elif endpoint.provider == LocalModelProvider.VLLM:
            return await self._vllm_generate(endpoint, prompt, stream, options)
        # ... 其他提供商
```

### 21.3 智能模型路由

```python
class SmartModelRouter:
    """智能模型路由"""

    # 模型能力分类
    CAPABILITY_LEVELS = {
        "reasoning": ["gpt-4", "claude-3", "llama-3-70b"],
        "fast_simple": ["gpt-3.5-turbo", "llama-3-8b", "mistral-7b"],
        "embedding": ["text-embedding-3-large", "bge-large", "e5-mistral"],
        "code": ["gpt-4-code", "claude-3-code", "codellama"]
    }

    def __init__(self):
        self._local_models: Dict[str, ModelEndpoint] = {}
        self._cloud_models: Dict[str, str] = {}  # name -> config
        self._routing_rules: List[RoutingRule] = []

    def add_local_model(self, endpoint: ModelEndpoint) -> None:
        """添加本地模型"""
        self._local_models[endpoint.name] = endpoint

        # 自动分类
        if "embedding" in endpoint.capabilities:
            self._assign_to_capability(endpoint, "embedding")
        elif "70b" in endpoint.name or "Llama" in endpoint.name:
            self._assign_to_capability(endpoint, "reasoning")
        else:
            self._assign_to_capability(endpoint, "fast_simple")

    def select_model(self, task_type: str, prefer_local: bool = True) -> str:
        """选择最佳模型"""
        # 1. 确定需要的模型类型
        capability = self._get_capability_for_task(task_type)

        # 2. 优先使用本地模型
        if prefer_local:
            local_candidates = self._get_local_models_by_capability(capability)
            if local_candidates:
                # 选择最合适的本地模型
                return self._select_best_local(local_candidates)

        # 3. 回退到云端模型
        return self._get_cloud_fallback(capability)

    def _select_best_local(self, candidates: List[ModelEndpoint]) -> str:
        """选择最佳本地模型"""
        # 考虑因素：上下文长度、可用性、速度
        for candidate in candidates:
            if candidate.is_available and candidate.max_context_length >= 4096:
                return candidate.name
        return candidates[0].name if candidates else ""
```

### 21.4 本地Embedding支持

```python
class LocalEmbeddingManager:
    """本地Embedding管理器"""

    SUPPORTED_MODELS = {
        "bge-large": {"dim": 1024, "max_length": 512},
        "bge-base": {"dim": 768, "max_length": 512},
        "e5-mistral": {"dim": 1024, "max_length": 4096},
        "nomic-embed": {"dim": 768, "max_length": 2048},
        "all-MiniLM": {"dim": 384, "max_length": 256}
    }

    def __init__(self):
        self._models: Dict[str, Any] = {}
        self._active_model: Optional[str] = None

    async def load_model(self, model_name: str, device: str = "auto") -> bool:
        """加载Embedding模型"""
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(model_name, device=device)
            self._models[model_name] = model
            self._active_model = model_name

            logger.info(f"Loaded embedding model: {model_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load {model_name}: {e}")
            return False

    async def embed(self, texts: Union[str, List[str]], model: Optional[str] = None) -> List[List[float]]:
        """生成Embedding向量"""
        model_name = model or self._active_model
        if model_name not in self._models:
            raise ValueError(f"Model {model_name} not loaded")

        model_obj = self._models[model_name]

        if isinstance(texts, str):
            texts = [texts]

        embeddings = model_obj.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
```

### 21.5 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| LocalModelProvider | 6种提供商 | ⏳ |
| Ollama集成 | 自动发现模型 | ⏳ |
| vLLM集成 | Tensor并行 | ⏳ |
| LM Studio集成 | API兼容 | ⏳ |
| SmartModelRouter | 智能路由 | ⏳ |
| LocalEmbedding | 本地向量化 | ⏳ |
| 健康检查 | 自动检测 | ⏳ |
| 模型切换 | 热切换 | ⏳ |

---

## 第22次迭代：本地向量数据库集成

**目标**: 支持本地向量数据库（Chroma/Qdrant/Faiss）

### 22.1 本地向量存储架构

```python
class LocalVectorStore:
    """本地向量存储"""

    SUPPORTED_BACKENDS = {
        "chroma": ChromaClient,
        "qdrant": QdrantClient,
        "faiss": FaissIndex,
        "milvus": MilvusClient
    }

    def __init__(self, backend: str = "chroma"):
        self.backend = backend
        self._client = None
        self._collection = None

    async def connect(self, persist_directory: str, collection_name: str = "default") -> None:
        """连接到本地向量数据库"""
        if self.backend == "chroma":
            import chromadb
            self._client = chromadb.PersistentClient(path=persist_directory)
            self._collection = self._client.get_or_create_collection(collection_name)
        elif self.backend == "qdrant":
            from qdrant_client import QdrantClient
            self._client = QdrantClient(path=persist_directory)
        # ... 其他后端

    async def add_vectors(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadata: List[Dict]
    ) -> None:
        """添加向量"""
        if self.backend == "chroma":
            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadata
            )
        elif self.backend == "faiss":
            import faiss
            index = faiss.IndexFlatIP(len(embeddings[0]))
            index.add(np.array(embeddings).astype('float32'))
            # 保存到磁盘
```

### 22.2 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| Chroma集成 | 持久化存储 | ⏳ |
| Qdrant集成 | 高性能 | ⏳ |
| Faiss集成 | 内存索引 | ⏳ |
| 向量搜索 | 高效检索 | ⏳ |
| 增量更新 | 支持增量 | ⏳ |

---

## 第23次迭代：混合云-本地部署架构

**目标**: 实现混合部署架构，平衡成本和性能

### 23.1 混合部署策略

```python
class HybridDeploymentStrategy:
    """混合部署策略"""

    def __init__(self):
        self._cloud_preference = 0.3  # 云端使用偏好
        self._local_preference = 0.7  # 本地使用偏好

    async def decide_deployment(
        self,
        task_type: str,
        complexity: float,          # 0-1 复杂度
        latency_requirement: float,  # 秒
        budget_constraint: float    # USD
    ) -> DeploymentDecision:
        """决定部署策略"""
        # 1. 延迟敏感任务 -> 本地
        if latency_requirement < 2.0:
            return DeploymentDecision(
                target="local",
                model=self._select_local_model(task_type),
                reason="Low latency requirement"
            )

        # 2. 成本敏感任务 -> 本地
        if budget_constraint < 0.01:
            return DeploymentDecision(
                target="local",
                model=self._select_local_model(task_type),
                reason="Cost constraint"
            )

        # 3. 高复杂度 -> 云端
        if complexity > 0.8:
            return DeploymentDecision(
                target="cloud",
                model=self._select_cloud_model(task_type),
                reason="High complexity requires powerful model"
            )

        # 4. 简单任务 -> 本地小模型
        if complexity < 0.3:
            return DeploymentDecision(
                target="local",
                model=self._select_small_local_model(),
                reason="Simple task, local is sufficient"
            )

        # 5. 默认 -> 混合
        return await self._evaluate_hybrid(task_type, complexity)
```

### 23.2 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| 延迟决策 | <2s使用本地 | ⏳ |
| 成本决策 | 预算<0.01本地 | ⏳ |
| 复杂度决策 | >0.8复杂度云端 | ⏳ |
| 自动切换 | 按策略切换 | ⏳ |
| 成本统计 | 云/本地分别统计 | ⏳ |

---

## 第24次迭代：本地模型量化与优化

**目标**: 支持模型量化以降低本地部署资源需求

### 24.1 模型量化配置

```python
class QuantizationConfig:
    """量化配置"""
    quantization_type: QuantizationType  # INT8/INT4/FP16/FP8
    bits: int = 4                         # 量化位数
    use_flash_attention: bool = True     # 使用Flash Attention
    tensor_parallel: int = 1             # 张量并行数

class QuantizationType(Enum):
    INT8 = "int8"                       # 8位整数量化
    INT4 = "int4"                       # 4位整数量化
    FP16 = "fp16"                       # 半精度浮点
    FP8 = "fp8"                         # 8位浮点
    AWQ = "awq"                         # Activation-Aware Quantization
    GGUF = "gguf"                        # GGUF格式（用于Ollama）

@dataclass
class LocalModelOptimization:
    """本地模型优化配置"""
    model_name: str
    quantization: QuantizationConfig
    recommended_gpu_memory: float       # GB
    expected_performance: float         # 相对FP16的性能
```

### 24.2 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| INT8量化 | 50%内存节省 | ⏳ |
| INT4量化 | 75%内存节省 | ⏳ |
| GGUF格式 | Ollama兼容 | ⏳ |
| 性能基准 | 量化vs原始 | ⏳ |
| 内存估算 | 自动估算 | ⏳ |

---

## 第25次迭代：离线模式支持

**目标**: 支持完全离线运行，不依赖任何外部服务

### 25.1 离线模式架构

```python
class OfflineModeManager:
    """离线模式管理器"""

    def __init__(self):
        self._is_offline = False
        self._offline_capabilities: Dict[str, bool] = {}
        self._downloaded_models: List[str] = []

    def enable_offline_mode(self) -> None:
        """启用离线模式"""
        self._is_offline = True
        self._check_offline_capabilities()

    def _check_offline_capabilities(self) -> None:
        """检查离线能力"""
        self._offline_capabilities = {
            "local_llm": len(self._downloaded_models) > 0,
            "local_embeddings": self._has_local_embedding_model(),
            "local_vector_store": self._has_local_vector_db(),
            "cached_data": self._has_sufficient_cache()
        }

    async def download_model_for_offline(
        self,
        model_name: str,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """下载模型以供离线使用"""
        # 使用Ollama拉取模型
        if self._is_ollama_available():
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self._downloaded_models.append(model_name)
                return True
        return False

    def get_offline_status(self) -> OfflineStatus:
        """获取离线状态"""
        return OfflineStatus(
            is_offline=self._is_offline,
            capabilities=self._offline_capabilities,
            downloaded_models=self._downloaded_models,
            all_capabilities_available=all(self._offline_capabilities.values())
        )
```

### 25.2 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| 离线检测 | 自动检测网络 | ⏳ |
| 离线模式 | 完全不依赖外网 | ⏳ |
| 模型下载 | 下载到本地 | ⏳ |
| 离线向量库 | 本地Chroma | ⏳ |
| 缓存预热 | 提前缓存数据 | ⏳ |

---

## 第26次迭代：资源监控与自动调度

**目标**: 实现本地资源监控和自动调度

### 26.1 本地资源监控

```python
class LocalResourceMonitor:
    """本地资源监控器"""

    def __init__(self):
        self._gpu_available = self._check_gpu()

    def _check_gpu(self) -> bool:
        """检查GPU可用性"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    async def get_system_resources(self) -> SystemResources:
        """获取系统资源"""
        import psutil

        resources = SystemResources(
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_percent=psutil.virtual_memory().percent,
            memory_available_gb=psutil.virtual_memory().available / (1024**3)
        )

        if self._gpu_available:
            import torch
            resources.gpu_memory_total_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            resources.gpu_memory_used_gb = (torch.cuda.memory_allocated() / (1024**3))
            resources.gpu_percent = (resources.gpu_memory_used_gb / resources.gpu_memory_total_gb) * 100

        return resources

    def can_load_model(self, model_name: str, model_size_gb: float) -> bool:
        """检查是否可以加载模型"""
        resources = asyncio.run(self.get_system_resources())

        # 检查内存
        if resources.memory_available_gb < model_size_gb * 1.2:  # 留20%缓冲
            return False

        # 检查GPU（如果需要）
        if self._model_requires_gpu(model_name):
            if resources.gpu_memory_total_gb < model_size_gb:
                return False

        return True
```

### 26.2 自动调度器

```python
class AutomaticResourceScheduler:
    """自动资源调度器"""

    def __init__(self, monitor: LocalResourceMonitor):
        self.monitor = monitor
        self._loaded_models: Dict[str, datetime] = {}
        self._max_concurrent_models = 2

    async def schedule_model_loading(
        self,
        model_name: str,
        priority: int = 0
    ) -> bool:
        """调度模型加载"""
        resources = await self.monitor.get_system_resources()

        # 检查是否可以加载
        model_size = self._estimate_model_size(model_name)
        if not self.monitor.can_load_model(model_name, model_size):
            # 尝试卸载低优先级模型
            await self._unload_low_priority_models()
            resources = await self.monitor.get_system_resources()

        # 再次检查
        if self.monitor.can_load_model(model_name, model_size):
            await self._load_model(model_name)
            return True

        return False
```

### 26.3 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| CPU监控 | 使用率实时 | ⏳ |
| 内存监控 | 可用内存 | ⏳ |
| GPU监控 | CUDA监控 | ⏳ |
| 模型大小估算 | 自动估算 | ⏳ |
| 自动卸载 | 低优先级释放 | ⏳ |
| 调度日志 | 完整记录 | ⏳ |

---

## 四、迭代依赖关系图（更新版）

```
Iteration 1: Agent通信协议
    │
    └──► Iteration 2: 状态持久化
            │
            └──► Iteration 3: Token追踪
                    │
                    └──► Iteration 4: 流式输出
                            │
                            └──► Iteration 5: Agent角色系统
                                    │
                                    └──► Iteration 6: 执行监控
                                            │
                                            └──► Iteration 7: 工具版本管理
                                                    │
                                                    └──► Iteration 8: 错误恢复
                                                            │
                                                            └──► Iteration 9: HIL人机交互
                                                                    │
                                                                    └──► Iteration 10: 上下文管理
                                                                            │
                                                                            └──► Iteration 11: ACML协作语言
                                                                                    │
                                                                                    └──► Iteration 12: 依赖调度
                                                                                            │
                                                                                            └──► Iteration 13: 反馈信任
                                                                                                    │
                                                                                                    └──► Iteration 14: 技能演化
                                                                                                            │
                                                                                                            └──► Iteration 15: 多模态增强
                                                                                                                    │
                                                                                                                    └──► Iteration 16: 性能优化
                                                                                                                            │
                                                                                                                            └──► Iteration 17: 安全强化
                                                                                                                                    │
                                                                                                                                    └──► Iteration 18: E2E测试
                                                                                                                                            │
                                                                                                                                            └──► Iteration 19: 文档完善
                                                                                                                                                    │
                                                                                                                                                    └──► Iteration 20: 集成测试
                                                                                                                                                            │
                                                                                                                                                            └──► Iteration 21: 本地模型部署 ← 新增
                                                                                                                                                                    │
                                                                                                                                                                    └──► Iteration 22: 本地向量库 ← 新增
                                                                                                                                                                            │
                                                                                                                                                                            └──► Iteration 23: 混合部署 ← 新增
                                                                                                                                                                                    │
                                                                                                                                                                                    └──► Iteration 24: 模型量化 ← 新增
                                                                                                                                                                                            │
                                                                                                                                                                                            └──► Iteration 25: 离线支持 ← 新增
                                                                                                                                                                                                    │
                                                                                                                                                                                                    └──► Iteration 26: 资源调度 ← 新增
```

---

## 五、迭代总览（更新版）

| 迭代 | 主题 | 核心产出 | 验收项数 | 优先级 |
|------|------|---------|---------|--------|
| 1 | Agent通信协议 | 消息格式+中间件 | 4 | P0 |
| 2 | 状态持久化 | CheckpointManager | 4 | P0 |
| 3 | Token追踪 | CostTracker | 5 | P0 |
| 4 | 流式输出 | StreamingHandler | 5 | P1 |
| 5 | Agent角色系统 | RoleRegistry | 5 | P0 |
| 6 | 执行监控 | ExecutionMonitor | 5 | P1 |
| 7 | 工具版本管理 | ToolVersionRegistry | 5 | P1 |
| 8 | 错误恢复 | ErrorRecovery | 5 | P0 |
| 9 | HIL人机交互 | HILManager | 5 | P1 |
| 10 | 上下文管理 | ContextManager | 5 | P1 |
| 11 | ACML协作语言 | ACMLParser | 5 | P2 |
| 12 | 依赖调度 | Scheduler | 5 | P1 |
| 13 | 反馈信任 | TrustEngine | 5 | P1 |
| 14 | 技能演化 | EvolutionEngine | 5 | P2 |
| 15 | 多模态增强 | MultimodalUnderstander | 5 | P1 |
| 16 | 性能优化 | PerformanceMonitor | 5 | P1 |
| 17 | 安全强化 | SecurityEngine | 5 | P1 |
| 18 | E2E测试 | TestRunner | 6 | P0 |
| 19 | 文档完善 | Documentation | 5 | P2 |
| 20 | 集成测试 | BenchmarkSuite | 6 | P0 |
| 21 | 本地模型部署 | LocalModelManager | 8 | P0 |
| 22 | 本地向量库 | LocalVectorStore | 5 | P1 |
| 23 | 混合部署 | HybridDeploymentStrategy | 5 | P1 |
| 24 | 模型量化 | QuantizationConfig | 5 | P2 |
| 25 | 离线支持 | OfflineModeManager | 5 | P1 |
| 26 | 资源调度 | AutomaticResourceScheduler | 6 | P1 |

**总计**: 26次迭代，120+验收项，130+代码模块

---

## 六、新增本地部署模块结构

```
src/agents_v2/
├── local_models/                 # 本地模型支持 (Iter 21-26)
│   ├── __init__.py
│   ├── providers/                # 模型提供商
│   │   ├── __init__.py
│   │   ├── ollama.py            # Ollama集成
│   │   ├── vllm.py             # vLLM集成
│   │   ├── lm_studio.py        # LM Studio
│   │   └── base.py             # 基类
│   ├── model_manager.py         # 模型管理器
│   ├── model_router.py          # 智能路由
│   ├── embedding_manager.py     # 本地Embedding
│   ├── vector_store.py          # 本地向量库
│   ├── quantization.py          # 量化支持
│   ├── offline_mode.py          # 离线模式
│   ├── resource_monitor.py      # 资源监控
│   └── auto_scheduler.py        # 自动调度

├── config/
│   └── local_models.yaml        # 本地模型配置
```

---

## 七、与原开发计划的关系

### 7.1 保持一致的部分

- **PhaseSupervisor多阶段流程**: 保持原有的diagnostic → topic → literature → methodology → writing → polish流程
- **UnifiedMemoryManager架构**: 保持6层记忆结构
- **IntentRouter意图识别**: 保持关键词+LLM的双层识别
- **Pipeline Agent和Problem-Oriented Agent分类**: 保持原有分类
- **评估基准**: GAIA/AgentBench/PaperWriting基准继续使用

### 7.2 本地部署增强部分

| 原模块 | 增强内容 |
|--------|---------|
| LLMConfig | 添加本地模型提供商配置 |
| CostOptimizer | 支持本地/云端成本分别统计 |
| ToolRegistry | 本地工具调用支持 |
| Retrieval | 本地向量检索 |
| Memory | 本地向量存储 |
| Monitoring | 资源监控 |

### 7.3 新增的模块

```
本地部署相关 (Iteration 21-26):
├── LocalModelProvider (6种提供商)
├── SmartModelRouter (智能路由)
├── LocalEmbeddingManager (本地向量化)
├── LocalVectorStore (Chroma/Qdrant/Faiss)
├── HybridDeploymentStrategy (混合部署)
├── QuantizationConfig (量化配置)
├── OfflineModeManager (离线支持)
└── AutomaticResourceScheduler (自动调度)
```

---

## 八、本地部署配置示例

### 8.1 config_local.yaml

```yaml
local_models:
  enabled: true

  providers:
    ollama:
      enabled: true
      base_url: "http://localhost:11434"
      auto_discover: true

    vllm:
      enabled: true
      base_url: "http://localhost:8000"
      tensor_parallel: 1

    lm_studio:
      enabled: true
      base_url: "http://localhost:1234"

  models:
    - name: "llama3:70b"
      provider: "ollama"
      type: "reasoning"
      max_context: 8192
      quantization: "int4"

    - name: "mistral:7b"
      provider: "ollama"
      type: "fast_simple"
      max_context: 4096
      quantization: "int8"

    - name: "nomic-embed-text"
      provider: "ollama"
      type: "embedding"
      max_context: 512

  embedding:
    model: "bge-large-zh"
    device: "cuda"  # auto/cpu/cuda
    normalize: true

  vector_store:
    backend: "chroma"
    persist_directory: ".vector_db"
    collection: "paper_agent"

  deployment_strategy:
    prefer_local: 0.7
    latency_threshold: 2.0  # 秒
    cost_threshold: 0.01   # USD

  offline:
    enabled: true
    models_to_download:
      - "llama3:70b"
      - "mistral:7b"
      - "nomic-embed-text"
```

---

**计划状态**: 26次迭代详细规划完成
**评分目标**: 9.5 → 10.0
**新增**: 本地部署支持（Iteration 21-26）
**执行状态**: 待开始

```
Iteration 1: Agent通信协议
    │
    └──► Iteration 2: 状态持久化
            │
            └──► Iteration 3: Token追踪
                    │
                    └──► Iteration 4: 流式输出
                            │
                            └──► Iteration 5: Agent角色系统
                                    │
                                    └──► Iteration 6: 执行监控
                                            │
                                            └──► Iteration 7: 工具版本管理
                                                    │
                                                    └──► Iteration 8: 错误恢复
                                                            │
                                                            └──► Iteration 9: HIL人机交互
                                                                    │
                                                                    └──► Iteration 10: 上下文管理
                                                                            │
                                                                            └──► Iteration 11: ACML协作语言
                                                                                    │
                                                                                    └──► Iteration 12: 依赖调度
                                                                                            │
                                                                                            └──► Iteration 13: 反馈信任
                                                                                                    │
                                                                                                    └──► Iteration 14: 技能演化
                                                                                                            │
                                                                                                            └──► Iteration 15: 多模态增强
                                                                                                                    │
                                                                                                                    └──► Iteration 16: 性能优化
                                                                                                                            │
                                                                                                                            └──► Iteration 17: 安全强化
                                                                                                                                    │
                                                                                                                                    └──► Iteration 18: E2E测试
                                                                                                                                            │
                                                                                                                                            └──► Iteration 19: 文档完善
                                                                                                                                                    │
                                                                                                                                                    └──► Iteration 20: 集成测试
```

---

## 五、验收总览

| 迭代 | 主题 | 核心产出 | 验收项数 | 优先级 |
|------|------|---------|---------|--------|
| 1 | Agent通信协议 | 消息格式+中间件 | 4 | P0 |
| 2 | 状态持久化 | CheckpointManager | 4 | P0 |
| 3 | Token追踪 | CostTracker | 5 | P0 |
| 4 | 流式输出 | StreamingHandler | 5 | P1 |
| 5 | Agent角色系统 | RoleRegistry | 5 | P0 |
| 6 | 执行监控 | ExecutionMonitor | 5 | P1 |
| 7 | 工具版本管理 | ToolVersionRegistry | 5 | P1 |
| 8 | 错误恢复 | ErrorRecovery | 5 | P0 |
| 9 | HIL人机交互 | HILManager | 5 | P1 |
| 10 | 上下文管理 | ContextManager | 5 | P1 |
| 11 | ACML协作语言 | ACMLParser | 5 | P2 |
| 12 | 依赖调度 | Scheduler | 5 | P1 |
| 13 | 反馈信任 | TrustEngine | 5 | P1 |
| 14 | 技能演化 | EvolutionEngine | 5 | P2 |
| 15 | 多模态增强 | MultimodalUnderstander | 5 | P1 |
| 16 | 性能优化 | PerformanceMonitor | 5 | P1 |
| 17 | 安全强化 | SecurityEngine | 5 | P1 |
| 18 | E2E测试 | TestRunner | 6 | P0 |
| 19 | 文档完善 | Documentation | 5 | P2 |
| 20 | 集成测试 | BenchmarkSuite | 6 | P0 |

**总计**: 20次迭代，95+验收项，100+代码模块

---

## 六、与原开发计划的关系

### 6.1 保持一致的部分

- **PhaseSupervisor多阶段流程**: 保持原有的diagnostic → topic → literature → methodology → writing → polish流程
- **UnifiedMemoryManager架构**: 保持6层记忆结构
- **IntentRouter意图识别**: 保持关键词+LLM的双层识别
- **Pipeline Agent和Problem-Oriented Agent分类**: 保持原有分类
- **评估基准**: GAIA/AgentBench/PaperWriting基准继续使用

### 6.2 增强的部分

| 原模块 | 增强内容 |
|--------|---------|
| MasterSupervisor | 添加HIL、流式输出、上下文管理 |
| Agent协作 | 添加通信协议、ACML语言、依赖调度 |
| 记忆系统 | 添加智能压缩、增量学习 |
| 检索系统 | 添加多模态理解、跨模态推理 |
| 工具系统 | 添加版本管理、错误恢复 |
| 评估系统 | 添加E2E测试、性能基准 |
| 安全系统 | 添加安全引擎、权限控制 |

### 6.3 新增的模块

```
src/agents_v2/
├── communication/              # Agent通信协议 (Iter 1)
│   ├── message.py             # AgentMessage定义
│   ├── bus.py                 # 通信中间件
│   └── protocol.py            # 通信协议
├── checkpoint/                # 状态持久化 (Iter 2)
│   ├── checkpoint_manager.py
│   └── recovery.py
├── cost_tracking/             # 成本追踪 (Iter 3)
│   ├── cost_tracker.py
│   └── budget_controller.py
├── streaming/                 # 流式输出 (Iter 4)
│   ├── stream_response.py
│   └── sse_handler.py
├── roles/                     # Agent角色系统 (Iter 5)
│   ├── agent_role.py
│   └── role_registry.py
├── monitoring/                # 执行监控 (Iter 6)
│   ├── execution_monitor.py
│   ├── decision_tracker.py
│   └── trace_manager.py
├── tool_version/              # 工具版本管理 (Iter 7)
│   ├── version_registry.py
│   └── migration.py
├── error_recovery/            # 错误恢复 (Iter 8)
│   ├── error_classifier.py
│   └── recovery_engine.py
├── hil/                       # 人机交互 (Iter 9)
│   ├── hil_manager.py
│   ├── approval_queue.py
│   └── intervention.py
├── context/                   # 上下文管理 (Iter 10)
│   ├── context_window.py
│   └── compression.py
├── acml/                      # ACML语言 (Iter 11)
│   ├── parser.py
│   ├── validator.py
│   └── executor.py
├── scheduler/                 # 任务调度 (Iter 12)
│   ├── dependency_graph.py
│   └── automatic_scheduler.py
├── trust/                     # 信任系统 (Iter 13)
│   ├── feedback_signal.py
│   └── trust_engine.py
├── evolution/                 # 技能演化 (Iter 14)
│   ├── skill_genome.py
│   └── evolution_engine.py
├── multimodal/                # 多模态增强 (Iter 15)
│   ├── deep_understander.py
│   └── cross_modal_reasoner.py
├── performance/               # 性能优化 (Iter 16)
│   ├── real_time_monitor.py
│   └── auto_optimizer.py
├── security/                  # 安全强化 (Iter 17)
│   ├── security_engine.py
│   └── permission.py
└── testing/                   # 测试框架 (Iter 18-20)
    ├── e2e_runner.py
    ├── benchmark_suite.py
    └── coverage_tracker.py
```

---

**计划状态**: 20次迭代详细规划完成
**评分目标**: 9.5 → 10.0
**执行状态**: 待开始