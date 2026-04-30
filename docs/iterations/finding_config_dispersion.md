# 发现：配置分散问题

**日期**：2026-04-30
**类型**：工程问题

---

## 1. 问题描述

项目配置分散在多个位置，存在重复定义和硬编码问题。

---

## 2. 配置分布现状

| 配置 | 位置 | 问题 |
|------|------|------|
| LLMConfig | `config.py`, `base_agent.py`, `pipeline/base_*.py` | 重复定义 |
| PHASES | `master_supervisor.py` | 硬编码 |
| QUALITY_THRESHOLDS | `master_supervisor.py` | 硬编码 |
| 熔断器配置 | `circuit_breaker.py` | 硬编码 |

---

## 3. 代码证据

```python
# config.py
class LLMConfig:
    model: str = "gpt-4"
    temperature: float = 0.7

# base_agent.py (重复)
class LLMConfig:
    def __init__(self, model="gpt-4", temperature=0.7, api_key=None):
        self.model = model
        self.temperature = temperature

# master_supervisor.py (硬编码)
PHASES = ["diagnostic", "topic", "literature", "methodology", "writing", "polish"]
QUALITY_THRESHOLDS = {"diagnostic": 6.0, "polish": 8.0, ...}

# circuit_breaker.py (硬编码)
FAILURE_THRESHOLD = 5
RECOVERY_TIMEOUT = 60
```

---

## 4. 问题影响

1. **维护困难**：修改需要同步多处
2. **不一致风险**：不同定义可能冲突
3. **测试困难**：硬编码难以覆盖边界情况
4. **部署限制**：无法适应多环境

---

## 5. 改进方案

```python
# config/unified.py
class UnifiedConfig:
    _instance = None

    def __init__(self):
        self.llm = LLMConfig.from_env()
        self.phases = self._load_phases()
        self.quality_thresholds = self._load_thresholds()
        self.circuit_breaker = self._load_circuit_breaker()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
```

---

## 6. 参考

- [12-Factor App 配置](https://12factor.net/config)
