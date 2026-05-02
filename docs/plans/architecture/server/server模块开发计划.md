# server 模块开发计划

> 规划日期：2026-05-03
> 基于：`docs/implemented/architecture/server/` + 未来框架设计 v2.1
> 现状：api_server.py 已实现

---

## 一、模块概述

### 1.1 现有架构

```
server/
└── api_server.py    # aiohttp API Server ✅
    - 请求日志中间件
    - API Key 认证
    - REST 端点
    - SSE 流式响应
```

### 1.2 提升目标

| 组件 | 当前 | 目标 |
|------|------|------|
| **HTTP 服务** | aiohttp 基础 | 高性能 + 连接池 |
| **AG-UI** | REST 轮询 | SSE + 16种事件 |
| **A2A 路由** | 无 | Agent 任务分发 |
| **限流** | 基础 | 令牌桶 + 自适应 |

---

## 二、任务清单

### 2.1 AG-UI 协议集成（P0）

**目标**：支持 Agent 协议标准

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| AG-UI 事件定义 | P0 | 16种事件类型 | `src/agents_v2/server/events.py` |
| SSE 事件推送 | P0 | 实时流式推送 | `src/agents_v2/server/sse_handler.py` |
| 状态快照 | P1 | STEP_STARTED/COMPLETED | `src/agents_v2/server/state_snapshots.py` |
| 工具调用事件 | P1 | TOOL_CALL/TOOL_RESULT | `src/agents_v2/server/tool_events.py` |

### 2.2 A2A 任务路由（P1）

**目标**：Agent 间任务分发

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| AgentCard 注册 | P1 | /.well-known/agent.json | `src/agents_v2/server/agent_registry.py` |
| 任务发送 | P1 | tasks/sendSubscribe | `src/agents_v2/server/task_client.py` |
| 任务接收 | P1 | tasks/sendReceive | `src/agents_v2/server/task_server.py` |
| 流式任务 | P2 | 任务状态实时推送 | `src/agents_v2/server/stream_task.py` |

### 2.3 性能优化（P1）

**目标**：企业级性能

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 连接池管理 | P1 | 连接复用 | `src/agents_v2/server/connection_pool.py` |
| 限流策略 | P1 | 令牌桶 + 自适应 | `src/agents_v2/server/rate_limiter.py` |
| 缓存层 | P2 | Redis 缓存 | `src/agents_v2/server/response_cache.py` |
| 负载均衡 | P2 | 多实例部署 | `src/agents_v2/server/load_balancer.py` |

### 2.4 安全增强（P0）

**目标**：企业级安全

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| OAuth 2.0 | P0 | 第三方认证 | `src/agents_v2/server/oauth.py` |
| CORS 配置 | P0 | 跨域支持 | `src/agents_v2/server/cors.py` |
| 输入验证 | P1 | 请求体校验 | `src/agents_v2/server/validation.py` |
| 审计日志 | P1 | 操作记录 | `src/agents_v2/server/audit.py` |

---

## 三、AG-UI 事件类型

| 事件类型 | 说明 |
|----------|------|
| TEXT_MESSAGE | 文本消息 |
| TOOL_CALL | 工具调用 |
| TOOL_RESULT | 工具结果 |
| STATE_SNAPSHOT | 状态快照 |
| STEP_STARTED | 步骤开始 |
| STEP_COMPLETED | 步骤完成 |
| ERROR | 错误 |
| ... | 其他事件 |

---

## 四、实施计划

### Phase 1：AG-UI 协议（2周）

```
Week 1:
  - AG-UI 事件定义
  - SSE 事件推送

Week 2:
  - 状态快照
  - 工具调用事件
```

### Phase 2：A2A 路由（2周）

```
Week 3:
  - AgentCard 注册
  - 任务发送/接收

Week 4:
  - 流式任务
  - 任务状态推送
```

### Phase 3：性能与安全（1周）

```
Week 5:
  - 连接池管理
  - 限流策略
  - OAuth 2.0
```

---

## 五、验收标准

- [ ] AG-UI 16种事件类型完整支持
- [ ] SSE 实时推送稳定
- [ ] A2A 任务路由正常
- [ ] 限流策略有效
- [ ] OAuth 2.0 认证可用

---

**版本**：v1.0
**规划日期**：2026-05-03