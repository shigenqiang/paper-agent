# 改进建议：统一配置管理

**日期**：2026-04-30
**优先级**：高

---

## 1. 背景

当前配置分散在多个文件，存在重复定义和硬编码问题。

---

## 2. 设计方案

### 2.1 配置类

```python
# config/unified.py
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import os

@dataclass
class LLMConfig:
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    timeout: int = 60

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            model=os.getenv("LLM_MODEL", "gpt-4"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            api_key=os.getenv("OPENAI_API_KEY"),
            api_base=os.getenv("LLM_API_BASE"),
        )

@dataclass
class PhaseConfig:
    name: str
    quality_threshold: float
    timeout_seconds: int = 300
    max_retries: int = 3

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: int = 60
    half_open_max_calls: int = 3

@dataclass
class UnifiedConfig:
    llm: LLMConfig = field(default_factory=LLMConfig.from_env)
    phases: Dict[str, PhaseConfig] = field(default_factory=dict)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    storage_path: str = ".memory"

    _instance: Optional["UnifiedConfig"] = None

    @classmethod
    def get_instance(cls) -> "UnifiedConfig":
        if cls._instance is None:
            cls._instance = cls._load()
        return cls._instance

    @classmethod
    def _load(cls) -> "UnifiedConfig":
        config = cls()
        config.phases = cls._load_phases()
        return config

    @classmethod
    def _load_phases(cls) -> Dict[str, PhaseConfig]:
        return {
            "diagnostic": PhaseConfig(name="diagnostic", quality_threshold=6.0),
            "topic": PhaseConfig(name="topic", quality_threshold=6.5),
            "literature": PhaseConfig(name="literature", quality_threshold=7.0),
            "methodology": PhaseConfig(name="methodology", quality_threshold=7.0),
            "writing": PhaseConfig(name="writing", quality_threshold=7.5),
            "polish": PhaseConfig(name="polish", quality_threshold=8.0),
        }
```

### 2.2 使用示例

```python
# 旧代码
from config import ConfigLoader
config = ConfigLoader().llm_config
agent = SomeAgent(config.llm_config)

# 新代码
from config.unified import UnifiedConfig
config = UnifiedConfig.get_instance()
agent = SomeAgent(config.llm)
```

---

## 3. 配置加载优先级

1. 环境变量（最高优先级）
2. 配置文件（`config.yaml`）
3. 默认值

---

## 4. 迁移计划

### Phase 1：创建统一配置类
- 新建 `config/unified.py`
- 保留现有配置作为兼容层

### Phase 2：迁移 LLMConfig
- 统一所有 LLMConfig 定义
- 更新所有引用

### Phase 3：移除硬编码
- 将硬编码的 PHASES、THRESHOLDS 迁移到配置
- 移除 `master_supervisor.py` 中的硬编码

---

## 5. 参考

- [12-Factor App 配置管理](https://12factor.net/config)
- [Python dataclass 配置](https://docs.python.org/3/library/dataclasses.html)
