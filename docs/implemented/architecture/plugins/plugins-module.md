# Plugins 模块

> 版本：v1.0
> 更新日期：2026-05-03
> 基于：`src/agents_v2/plugins/`

## 模块概述

plugins 模块提供插件系统支持：

- **__init__.py**：插件注册与加载
- 插件发现机制
- 插件生命周期管理

## 目录结构

```
plugins/
└── __init__.py              # 插件系统 (20KB)
```

## 核心功能

### 插件注册

```python
class PluginRegistry:
    def register(self, name: str, plugin: Plugin)
    def get(self, name: str) -> Plugin | None
    def list_all(self) -> list[str]
```

### 插件生命周期

```
load() → initialize() → execute() → terminate()
```

### 内置插件

| 插件 | 说明 |
|------|------|
| SearchPlugin | 搜索插件 |
| AnalysisPlugin | 分析插件 |
| WritingPlugin | 写作插件 |
| ExportPlugin | 导出插件 |

## 与其他模块关系

```
agents/
        │
        ▼
    plugins/
        │
        ├─► ToolRegistry     # 工具注册
        └─► SkillRegistry    # 技能注册
```

---

**版本**：v1.0
**更新日期**：2026-05-03