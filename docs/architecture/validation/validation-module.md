# Validation 模块

> 版本：v1.0
> 更新日期：2026-05-03
> 基于：`src/agents_v2/validation/`

## 模块概述

validation 模块提供数据验证功能：

- **__init__.py**：Pydantic 验证器
- 输入数据校验
- 输出数据校验
- 业务规则校验

## 目录结构

```
validation/
└── __init__.py              # PydanticValidator (10KB)
```

## 核心组件

### PydanticValidator

基于 Pydantic 的数据验证器：

```python
class PydanticValidator:
    @staticmethod
    def validate_user_input(data: dict) -> UserInput
    @staticmethod
    def validate_paper_data(data: dict) -> PaperData
    @staticmethod
    def validate_agent_config(data: dict) -> AgentConfig
```

### 内置验证器

| 验证器 | 说明 |
|--------|------|
| UserInputValidator | 用户输入验证 |
| PaperDataValidator | 论文数据验证 |
| AgentConfigValidator | Agent 配置验证 |
| QueryValidator | 查询参数验证 |

## 与其他模块关系

```
api/
        │
        ▼
    validation/
        │
        └─► PydanticValidator  # 请求数据验证
                │
                ▼
            unified/           # 业务处理
```

---

**版本**：v1.0
**更新日期**：2026-05-03