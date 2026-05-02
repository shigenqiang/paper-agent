# Harness 层

> 版本：v1.0
> 更新日期：2026-05-03
> 基于：`src/agents_v2/harness/`

## 模块概述

harness 模块是质量保障的兼容层，从 `unified/` 导出核心组件：

- **CircuitBreaker**：熔断器，防止级联失败
- **HITLManager**：人机协作管理
- **ExecutionReplay**：执行回放
- **ErrorHandler**：错误处理

## 目录结构

```
harness/
└── __init__.py              # 兼容层，从 unified 导出
    import warnings
    warnings.warn("src.agents_v2.harness 是新的模块路径...")
    from src.agents_v2.unified import (
        CircuitBreaker,
        MultiCircuitBreaker,
        FallbackHandler,
        RetryPolicy,
        HITLManager,
        InterventionType,
        InterventionRequest,
        InterventionResponse,
        ExecutionReplay,
        ResultCache,
        ...
    )
```

## 核心组件

### CircuitBreaker

熔断器状态机：
- **CLOSED**：正常状态
- **OPEN**：熔断状态
- **HALF_OPEN**：半开状态

触发条件：
- 错误率 > 30%
- 连续失败 5 次
- 单步超时 > 5 分钟

### HITLManager

人机协作管理器，提供干预点：

| 介入点 | 说明 |
|--------|------|
| `after_outline` | 大纲完成后人工确认 |
| `after_literature` | 文献综述完成后审核 |
| `after_section` | 每章节完成后可选审核 |
| `before_final` | 终稿前全面审核 |
| `on_low_quality` | 质量评分低于阈值时强制中断 |

### ExecutionReplay

执行回放，支持：
- 记录执行轨迹
- 重放历史执行
- 调试问题

### ErrorAccumulator

错误累积器：
- 错误类型统计
- 错误趋势分析
- 自动告警

## 与其他模块关系

```
agents/BaseAgent
        │
        ▼
    harness/
        │
        ├─► CircuitBreaker    # 熔断保护
        ├─► HITLManager       # 人机协作
        ├─► ExecutionReplay   # 执行回放
        └─► ErrorAccumulator  # 错误追踪
                │
                ▼
            unified/           # 核心错误处理
```

---

**版本**：v1.0
**更新日期**：2026-05-03