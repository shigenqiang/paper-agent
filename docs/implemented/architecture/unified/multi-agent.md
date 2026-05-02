# Multi-Agent Collaboration 多Agent协作详解

> 位置: `src/agents_v2/unified/` (agent_loop, phase_supervisor, hitl_manager)

## 一、架构概览

```
unified/
├── master_supervisor.py     # 全局协调器 (6阶段流水线)
├── phase_supervisor.py     # 阶段监督器
├── agent_loop.py          # Agent循环抽象
├── circuit_breaker.py     # 熔断保护
├── intent_router.py        # 意图路由 (11种意图)
├── hitl_manager.py        # Human-in-the-Loop管理器
├── error_handler.py        # 错误处理
├── error_recovery.py      # 错误恢复
├── state_model.py          # 状态模型
├── cache.py               # 结果缓存
├── monitoring.py          # 指标收集
├── execution_replay.py    # 执行回放
├── flow_monitoring.py      # 流程监控
├── input_security.py       # 输入安全
├── output_manager.py       # 输出管理
├── pydantic_validator.py   # Pydantic验证
└── translation.py          # 翻译包装器
```

## 二、MasterSupervisor 全局协调器

```python
class MasterSupervisor:
    """全局协调器 - 6阶段流水线"""

    PHASES = [
        "diagnostic",   # 诊断
        "topic",        # 选题
        "literature",   # 文献
        "methodology",  # 方法论
        "writing",      # 写作
        "polish"        # 润色
    ]

    QUALITY_THRESHOLDS = {
        "diagnostic": 0.6,
        "topic": 0.7,
        "literature": 0.7,
        "methodology": 0.7,
        "writing": 0.7,
        "polish": 0.8
    }

    async def run(self, intent: str, user_input: dict) -> PhaseResult:
        """运行流水线"""
        state = self._init_state(user_input)

        for phase in self.PHASES:
            # 检查熔断
            if self.circuit_breaker.is_open(phase):
                return self._handle_circuit_open(phase)

            # 执行阶段
            result = await self._run_phase(phase, state)

            # 质量评估
            if result.score < self.QUALITY_THRESHOLDS[phase]:
                result = await self._retry_phase(phase, state)

            # 更新状态
            state.update(result)

        return state
```

## 三、PhaseSupervisor 阶段监督器

```python
class PhaseSupervisor:
    """阶段监督器 - 管理单阶段内的多个Agent"""

    def __init__(self, phase_name: str):
        self.phase_name = phase_name
        self.agents: Dict[str, BaseAgent] = {}
        self.circuit_breaker = CircuitBreaker(phase_name)

    async def run_phase(
        self,
        agents: List[BaseAgent],
        input_data: dict
    ) -> PhaseResult:
        """执行阶段内的Agent循环"""
        results = []

        for agent in agents:
            try:
                result = await self.circuit_breaker.call(
                    agent.execute,
                    input_data
                )
                results.append(result)
            except CircuitBreakerOpenError:
                self._handle_agent_failure(agent)
                continue

        # 合并结果
        return self._merge_results(results)
```

## 四、AgentLoop Agent循环抽象

```python
class AgentLoop:
    """Agent执行循环"""

    def __init__(
        self,
        agents: List[BaseAgent],
        max_iterations: int = 3
    ):
        self.agents = agents
        self.max_iterations = max_iterations

    async def execute(
        self,
        task: str,
        context: dict = None
    ) -> ExecutionResult:
        """
        1. 按顺序执行Agent
        2. 结果传递给下一个Agent
        3. 支持循环迭代
        """
        state = context or {}
        iteration = 0

        while iteration < self.max_iterations:
            for agent in self.agents:
                result = await agent.execute(task, state)
                state[agent.name] = result

                # 检查是否需要停止
                if self._should_terminate(result):
                    return ExecutionResult(
                        success=True,
                        final_state=state,
                        iterations=iteration
                    )

            iteration += 1

        return ExecutionResult(
            success=False,
            final_state=state,
            iterations=iteration,
            error="Max iterations reached"
        )
```

## 五、HITL Manager 人机协作

```python
class HITLManager:
    """Human-in-the-Loop 管理器"""

    INTERRUPT_POINTS = {
        "after_outline": "大纲生成后、写作前",
        "after_literature": "文献综述后需审核",
        "after_section": "每章节完成后可选审核",
        "before_final": "终稿前需全面审核",
        "on_low_quality": "质量评分<阈值时强制中断"
    }

    def __init__(self):
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self.approved: Dict[str, bool] = {}

    async def request_approval(
        self,
        point: str,
        content: Any,
        user_id: str
    ) -> ApprovalResult:
        """请求人工审批"""
        request = ApprovalRequest(
            id=str(uuid.uuid4()),
            point=point,
            content=content,
            user_id=user_id,
            timestamp=datetime.now()
        )

        self.pending_approvals[request.id] = request

        # 等待用户响应
        return await self._wait_for_approval(request)

    async def approve(self, request_id: str, approved: bool, comment: str = None):
        """审批通过/拒绝"""
        request = self.pending_approvals.pop(request_id)
        self.approved[request_id] = approved

        if not approved:
            # 记录拒绝原因，用于后续改进
            self._record_rejection(request, comment)
```

## 六、错误处理与恢复

```python
class FallbackHandler:
    """错误处理与回退"""

    def __init__(self):
        self.fallbacks: Dict[str, Callable] = {}

    def register_fallback(self, agent_name: str, fallback: Callable):
        """注册回退函数"""
        self.fallbacks[agent_name] = fallback

    async def handle_error(
        self,
        error: Exception,
        agent_name: str,
        context: dict
    ) -> Any:
        """处理错误，返回回退结果"""
        fallback = self.fallbacks.get(agent_name)

        if fallback:
            try:
                return await fallback(context)
            except Exception as e:
                return ErrorResult(
                    original_error=error,
                    fallback_error=e,
                    message="Fallback also failed"
                )

        return ErrorResult(
            error=error,
            message=f"No fallback for agent: {agent_name}"
        )
```

## 七、执行回放

```python
class ExecutionReplay:
    """执行回放 - 支持调试和复现"""

    def __init__(self):
        self.recordings: Dict[str, List[StepRecord]] = {}

    def record_step(
        self,
        session_id: str,
        agent_name: str,
        input_data: Any,
        output_data: Any,
        metadata: dict = None
    ):
        """记录执行步骤"""
        record = StepRecord(
            timestamp=datetime.now(),
            agent_name=agent_name,
            input=input_data,
            output=output_data,
            metadata=metadata or {}
        )

        if session_id not in self.recordings:
            self.recordings[session_id] = []

        self.recordings[session_id].append(record)

    def replay(self, session_id: str) -> Generator[StepRecord, None, None]:
        """回放执行过程"""
        for record in self.recordings.get(session_id, []):
            yield record

    def replay_step(self, session_id: str, step_index: int) -> StepRecord:
        """回放指定步骤"""
        return self.recordings[session_id][step_index]
```

## 八、流程监控

```python
class FlowMonitoring:
    """流程监控 - 实时追踪流水线执行"""

    def __init__(self):
        self.metrics = FlowMetrics()

    async def track_phase(
        self,
        phase_name: str,
        duration_ms: float,
        status: str,
        agent_count: int
    ):
        """追踪阶段执行指标"""
        self.metrics.record_phase(
            name=phase_name,
            duration_ms=duration_ms,
            status=status,
            agent_count=agent_count
        )

    def get_metrics(self) -> FlowMetricsSummary:
        """获取监控指标汇总"""
        return FlowMetricsSummary(
            total_phases=self.metrics.phase_count,
            total_duration_ms=self.metrics.total_duration,
            avg_phase_duration=self.metrics.avg_duration,
            failure_count=self.metrics.failure_count,
            success_rate=self.metrics.success_rate
        )
```

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/unified/`
