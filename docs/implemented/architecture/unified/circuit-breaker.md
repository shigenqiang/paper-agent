# CircuitBreaker 熔断保护详解

> 位置: `src/agents_v2/unified/circuit_breaker.py`

## 一、核心概念

```
正常状态 (CLOSED)
    │
    │ 错误率 > 30% OR 连续失败 5 次 OR 超时 5min OR 费用 > $5
    ▼
熔断打开 (OPEN)
    │
    │ 冷却时间 60s 后
    ▼
半开状态 (HALF-OPEN)
    │
    │ 请求成功
    ▼
恢复正常 (CLOSED)  或  请求失败 → 继续熔断 (OPEN)
```

## 二、状态机

| 状态 | 说明 | 行为 |
|------|------|------|
| **CLOSED** | 正常状态 | 所有请求通过，统计错误率 |
| **OPEN** | 熔断打开 | 请求直接失败，快速返回 |
| **HALF_OPEN** | 半开状态 | 放行一个请求测试 |

## 三、配置参数

```python
class CircuitBreakerConfig:
    error_rate_threshold: float = 0.3      # 错误率阈值 30%
    consecutive_failure_threshold: int = 5  # 连续失败次数阈值
    timeout_duration: int = 300           # 超时阈值 5 分钟
    cost_threshold: float = 5.0           # 费用阈值 $5
    half_open_timeout: int = 60           # 半开状态超时 60s
    recovery_timeout: int = 60            # 恢复冷却时间 60s
```

## 四、核心实现

```python
class CircuitBreaker:
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.total_requests = 0
        self.failed_requests = 0

    async def call(self, func, *args, **kwargs):
        """执行请求，带熔断保护"""

        # 检查状态
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError(
                    f"CircuitBreaker '{self.name}' is OPEN"
                )

        # 执行请求
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """成功处理"""
        self.success_count += 1
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED

        if self.total_requests > 0:
            error_rate = self.failed_requests / self.total_requests
            if error_rate < self.config.error_rate_threshold:
                self.state = CircuitState.CLOSED

    def _on_failure(self):
        """失败处理"""
        self.failure_count += 1
        self.failed_requests += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.config.consecutive_failure_threshold:
            self.state = CircuitState.OPEN
```

## 五、触发条件

| 条件 | 阈值 | 说明 |
|------|------|------|
| 错误率 | > 30% | 失败请求 / 总请求 |
| 连续失败 | ≥ 5 次 | 不受总请求数影响 |
| 超时 | 5 分钟 | 单次请求超时累计 |
| 费用 | > $5 | 单次调用费用累计 |

## 六、多级熔断器 (MultiCircuitBreaker)

```python
class MultiCircuitBreaker:
    """多级熔断器，管理多个 Agent 的熔断"""

    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, agent_name: str) -> CircuitBreaker:
        if agent_name not in self.breakers:
            self.breakers[agent_name] = CircuitBreaker(agent_name)
        return self.breakers[agent_name]

    async def call(self, agent_name: str, func, *args, **kwargs):
        breaker = self.get_breaker(agent_name)
        return await breaker.call(func, *args, **kwargs)
```

## 七、触发后的行为

```python
class CircuitBreakerOpenError(Exception):
    """熔断打开异常"""

    def __init__(self, message: str, circuit_name: str = None):
        self.circuit_name = circuit_name
        super().__init__(message)

# 触发时的返回
{
    "success": False,
    "error": "Circuit breaker is OPEN for agent: TopicAgent",
    "retry_after": 60,  # 秒
    "circuit_state": "OPEN"
}
```

## 八、在 MasterSupervisor 中的使用

```python
class MasterSupervisor:
    def __init__(self, llm_config: LLMConfig):
        self.circuit_breaker = CircuitBreaker("master_supervisor")

    async def run_phase(self, phase: str, agents: List[BaseAgent]):
        for agent in agents:
            try:
                result = await self.circuit_breaker.call(
                    agent.execute,
                    user_input
                )
            except CircuitBreakerOpenError:
                # 降级处理或跳过
                self._handle_circuit_open(phase, agent)
```

## 九、监控指标

| 指标 | 说明 |
|------|------|
| `circuit.{name}.state` | 当前状态 (CLOSED/OPEN/HALF_OPEN) |
| `circuit.{name}.failure_rate` | 错误率 |
| `circuit.{name}.total_requests` | 总请求数 |
| `circuit.{name}.failed_requests` | 失败请求数 |
| `circuit.{name}.success_rate` | 成功率 |

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/unified/circuit_breaker.py`