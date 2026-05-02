# core 模块开发计划

> 规划日期：2026-05-02
> 基于：`docs/implemented/architecture/core/base-agent.md` + 调研报告
> 现状：BaseAgent 已实现，LLMConfig 16 模型注册已实现

---

## 一、模块概述

### 1.1 现有架构

```
core/
├── base_agent.py         # BaseAgent 基类 (12,218 字节) ✅
├── enhanced_base.py     # 增强版 Agent (18,518 字节) ✅
├── react_executor.py    # ReAct 执行器 (16,783 字节) ✅
├── config.py           # YAML 配置 + 16 模型注册表 ✅
├── config_manager.py   # 配置管理器 ✅
├── context_injector.py  # 上下文注入器 ✅
├── llm_fallback.py     # LLM 降级策略 ✅
├── streaming.py        # SSE 流式输出 ✅
├── agent_roles.py       # Agent 角色定义 ✅
├── builtin_plugins.py   # 内置插件 ✅
├── plugins.py          # 插件系统 ✅
├── security.py         # 安全加固 ✅
├── error_recovery.py   # 错误恢复 ✅
└── validators.py       # 输入验证 ✅
```

### 1.2 提升目标

| 维度 | 当前 | 目标 |
|------|------|------|
| Agent 协议 | 直接调用 | MCP + Agent Skills |
| LLM 路由 | 16 模型注册 | 三级级联智能路由 |
| 上下文管理 | 基础注入 | 智能压缩 + 重要性筛选 |
| 流式输出 | SSE 支持 | AG-UI 16 种事件类型 |

---

## 二、任务清单

### 2.1 MCP Client 集成（P0）

**目标**：将工具调用通过 MCP 协议标准化

**任务**：

| 任务 | 优先级 | 说明 |
|------|--------|------|
| MCP Client 基类 | P0 | `src/agents_v2/core/mcp_client.py` |
| MCP 工具调用封装 | P0 | 统一工具调用接口 |
| MCP 资源订阅 | P1 | 资源实时同步 |

**MCP Client 示例**：

```python
# src/agents_v2/core/mcp_client.py
from mcp import Client

class MCPClient:
    """MCP 客户端封装"""

    def __init__(self, server_url: str):
        self.client = Client(server_url)

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """通过 MCP 调用工具"""
        result = await self.client.call_tool(tool_name, arguments)
        return result

    async def list_resources(self) -> List[Resource]:
        """列出可用资源"""
        return await self.client.list_resources()
```

### 2.2 意图路由级联升级（P0）

**目标**：实现三级级联混合路由

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| Layer 1 优化 | P0 | 关键词快速匹配 | `src/agents_v2/core/keyword_matcher.py` |
| Layer 2 实现 | P0 | 语义向量路由 | `src/agents_v2/core/vector_router.py` |
| Layer 3 集成 | P0 | LLM 深度分类 | `src/agents_v2/core/llm_classifier.py` |
| 置信度校准 | P1 | 三层结果合并 | `src/agents_v2/core/confidence_calibrator.py` |

### 2.3 上下文智能压缩（P1）

**目标**：智能管理上下文，避免 token 溢出

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 重要性评估 | P1 | 消息重要性评分 | `src/agents_v2/core/importance_scorer.py` |
| 摘要生成 | P1 | LLM 驱动摘要 | `src/agents_v2/core/summary_generator.py` |
| 上下文窗口管理 | P1 | Token 预算控制 | `src/agents_v2/core/context_window.py` |
| 智能注入 | P2 | 相关性过滤 | `src/agents_v2/core/context_injector.py` |

### 2.4 流式输出增强（P1）

**目标**：支持 AG-UI 协议事件类型

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| AG-UI 事件封装 | P1 | 16 种事件类型 | `src/agents_v2/core/agui_events.py` |
| SSE 流式增强 | P1 | 状态快照推送 | `src/agents_v2/core/streaming.py` |
| 工具调用追踪 | P2 | TOOL_CALL 事件 | `src/agents_v2/core/tool_tracker.py` |

### 2.5 安全加固增强（P2）

**目标**：增强安全防护

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| Prompt 注入检测 | P2 | 恶意 Prompt 识别 | `src/agents_v2/core/security.py` |
| 速率限制增强 | P2 | 多维度限流 | `src/agents_v2/core/rate_limiter.py` |
| 审计日志 | P2 | 操作完整记录 | `src/agents_v2/core/audit_logger.py` |

---

## 三、实施计划

### Phase 1：MCP Client + 意图路由（2周）

```
Week 1:
  - MCP Client 基类实现
  - Layer 1 关键词匹配优化

Week 2:
  - Layer 2 语义向量路由实现
  - Layer 3 LLM 分类集成
```

### Phase 2：上下文管理（2周）

```
Week 3:
  - 重要性评估器实现
  - 摘要生成器实现

Week 4:
  - 上下文窗口管理
  - 智能注入逻辑优化
```

### Phase 3：流式输出 + 安全（1周）

```
Week 5:
  - AG-UI 事件封装
  - SSE 流式增强
  - 安全加固增强
```

---

## 四、验收标准

- [ ] MCP Client 可正常调用 ArXiv/PubMed MCP Server
- [ ] 三级级联意图路由正常工作（Layer 1/2/3）
- [ ] 上下文智能压缩后 token 减少 > 50%
- [ ] AG-UI 事件正常推送
- [ ] Prompt 注入检测准确率 > 90%

---

## 五、依赖关系

```
意图路由级联升级
  ├── Layer 2 依赖向量模型 (BAAI/bge-small-zh-v1.5)
  └── Layer 3 依赖 LLM API

上下文智能压缩
  ├── 重要性评估 → 依赖 LLM
  └── 摘要生成 → 依赖 LLM

MCP Client
  ├── 依赖 MCP SDK
  └── 依赖 MCP Server 运行
```

---

**版本**：v1.0
**规划日期**：2026-05-02
