# Agent 协议生态调研报告 — MCP、A2A、Skills、AG-UI

> 调研时间: 2026-05-01
> 状态: 2025-2026 年 AI Agent 协议生态全景
> 项目: Paper Agent — 协议层基础设施选型

---

## 一、生态全景

2025-2026 年是 AI Agent 协议爆发的两年。Anthropic、Google、CopilotKit 等组织相继发布了 MCP、A2A、Skills、AG-UI 等开放协议，共同构成了 AI Agent 开发的四大基础设施标准。

### 1.1 四层协议体系

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI Agent 协议生态全景 (2026)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│   │   MCP 协议    │    │  A2A 协议    │    │  AG-UI 协议   │          │
│   │  (Anthropic)  │    │   (Google)   │    │ (CopilotKit)  │          │
│   │              │    │              │    │              │          │
│   │ Agent ↔ Tool │    │ Agent ↔ Agent│    │ Agent ↔ User  │          │
│   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘          │
│          │                   │                   │                   │
│          │      ┌────────────┴────────────┐      │                   │
│          └──────┤    Agent Skills 标准     ├──────┘                   │
│                 │      (Anthropic)         │                          │
│                 │   能力模块化封装与复用     │                          │
│                 └─────────────────────────┘                          │
│                                                                     │
│   ─────────────────────────────────────────────────────────────     │
│                        底层传输标准                                    │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│   │ stdio    │  │ HTTP+SSE │  │ WebSocket│  │ JSON-RPC │           │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 协议速览

| 协议/标准 | 发布时间 | 主导方 | 解决的通信 | 类比 |
|-----------|----------|--------|-----------|------|
| **MCP** | 2024-11-25 | Anthropic | Agent ↔ 工具/数据源 | USB-C 接口 |
| **A2A** | 2025-04-09 | Google | Agent ↔ Agent | HTTP 协议 |
| **Skills** | 2025-12-18 | Anthropic | Agent ↔ 能力模块 | npm 包 |
| **AG-UI** | 2025-05 | CopilotKit | Agent ↔ 用户界面 | WebSocket API |

**核心关系**: 互补，不是竞争。MCP 是"手"(操作工具)，A2A 是"口"(相互通信)，Skills 是"脑"(专业知识)，AG-UI 是"脸"(用户交互)。

---

## 二、A2A 协议 (Agent-to-Agent Protocol)

### 2.1 协议概述

A2A 由 Google 于 2025 年 4 月 9 日在 Google Cloud Next 25 大会上开源发布，2025 年 6 月 24 日捐赠给 Linux 基金会。旨在为不同框架、不同供应商开发的 AI Agent 提供标准化的通信方式。

**关键里程碑**:
| 时间 | 事件 |
|------|------|
| 2025-04-09 | Google Cloud Next 25 发布 A2A |
| 2025-06-24 | 捐赠给 Linux 基金会 |
| 2025-12 | 超过 50+ 技术合作伙伴 |
| 2026-04 | Spring AI、tRPC 等框架原生集成 |

### 2.2 核心设计原则

1. **拥抱智能体能力** — 不将 Agent 降级为简单 API，支持非结构化交互
2. **基于现有标准** — HTTP/1.1、HTTP/2、JSON-RPC 2.0、SSE (Server-Sent Events)
3. **默认安全** — 企业级认证和授权机制
4. **支持长时间任务** — 异步任务+流式状态更新
5. **模态无关** — 文本、结构化数据、文件等多模态通信

### 2.3 核心概念

#### AgentCard (Agent 名片)

每个 Agent 通过 `/.well-known/agent.json` 暴露自身能力描述：

```json
{
  "name": "PaperAgent-Search",
  "description": "学术论文搜索智能体，支持多数据源检索",
  "url": "https://paper-agent.example.com",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "arxiv_search",
      "name": "arXiv 搜索",
      "description": "在 arXiv 数据库中搜索预印本论文",
      "tags": ["academic", "preprint", "physics", "cs"],
      "examples": ["搜索机器学习最新论文", "查找量子计算综述"]
    },
    {
      "id": "pubmed_search",
      "name": "PubMed 搜索",
      "description": "在 PubMed 数据库中搜索生物医学论文",
      "tags": ["biomedical", "clinical", "medicine"]
    }
  ],
  "authentication": {
    "schemes": ["bearer_token", "oauth2"]
  },
  "defaultInputModes": ["text", "text/plain"],
  "defaultOutputModes": ["text", "text/plain"]
}
```

#### Task 对象生命周期

```
submitted → processing → working → completed
                ↓                       ↓
             failed                  canceled

完整状态机:
  submitted   — 任务已提交，等待处理
  processing  — Agent 正在分析任务
  working     — Agent 正在执行任务
  completed   — 任务成功完成
  failed      — 任务执行失败
  canceled    — 任务被取消
```

Task 对象结构:

```json
{
  "id": "task-abc-123",
  "status": "working",
  "title": "搜索深度学习优化论文",
  "message": {
    "role": "user",
    "parts": [
      {"type": "text", "text": "搜索2024-2025年深度学习优化的最新论文"}
    ]
  },
  "artifacts": [
    {
      "parts": [
        {"type": "text", "text": "已找到 15 篇相关论文..."},
        {"type": "data", "data": {"papers": [...]}}
      ]
    }
  ],
  "metadata": {
    "created_at": "2026-05-01T10:00:00Z",
    "updated_at": "2026-05-01T10:00:30Z"
  }
}
```

### 2.4 API 方法

| 方法 | 描述 | 模式 |
|------|------|------|
| `tasks/send` | 发送任务（同步等待结果） | 请求-响应 |
| `tasks/sendSubscribe` | 发送任务并订阅 SSE 流 | 流式 |
| `tasks/get` | 查询任务状态 | 请求-响应 |
| `tasks/cancel` | 取消正在执行的任务 | 请求-响应 |
| `tasks/list` | 列出任务列表（可选） | 请求-响应 |

**JSON-RPC 调用示例**:

```json
// 请求: tasks/sendSubscribe
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tasks/sendSubscribe",
  "params": {
    "id": "task-001",
    "message": {
      "role": "user",
      "parts": [
        {"type": "text", "text": "请为我的AI教育论文搜索相关文献"}
      ]
    }
  }
}

// 响应: SSE 事件流
event: status
data: {"state": "submitted", "timestamp": "2026-05-01T10:00:00Z"}

event: status
data: {"state": "working", "timestamp": "2026-05-01T10:00:05Z"}

event: artifact
data: {"artifacts": [{"parts": [{"type": "text", "text": "已找到 23 篇论文..."}]}]}

event: status
data: {"state": "completed", "timestamp": "2026-05-01T10:00:15Z"}
```

### 2.5 传输与安全

| 层级 | 技术 | 说明 |
|------|------|------|
| 传输层 | HTTP/1.1、HTTP/2 | 使用标准 Web 栈 |
| RPC 格式 | JSON-RPC 2.0 | 轻量级，开发者熟悉 |
| 流式通信 | SSE (Server-Sent Events) | 单向推送任务状态 |
| 认证 | API Key、Bearer Token、OAuth 2.0 | 企业级安全 |
| 服务发现 | `/.well-known/agent.json` | 标准化 Agent 发现 |

### 2.6 生态系统

| 框架/SDK | 语言 | 状态 |
|----------|------|------|
| Google ADK | Python | 官方支持 |
| Spring AI A2A | Java | 原生集成 |
| tRPC-A2A-Go | Go | 社区实现 |
| LangChain A2A | Python | 社区集成 |
| CrewAI A2A | Python | 社区集成 |
| AutoGen A2A | Python | 社区集成 |

### 2.7 MCP vs A2A 关系

| 维度 | MCP | A2A |
|------|-----|-----|
| 通信对象 | Agent ↔ 工具/数据 | Agent ↔ Agent |
| 通信模式 | 客户端-服务器 (C/S) | 对等通信 (P2P) |
| 核心原语 | Tools、Resources、Prompts | Task、AgentCard |
| 流式 | 可选 | 核心特性 (SSE) |
| 状态管理 | 无状态 | 有状态 (Task 生命周期) |
| RPC 协议 | 自定义 JSON | JSON-RPC 2.0 |
| 主导方 | Anthropic | Google (Linux 基金会) |
| 类比 | USB-C 接口 | HTTP 协议 |

**一句话总结**: MCP 让 Agent 能"使用什么"，A2A 让 Agent 能"和谁协作"。

---

## 三、Agent Skills 标准

### 3.1 标准概述

Agent Skills 由 Anthropic 于 2025 年 12 月 18 日以开放标准形式在 agentskills.io 发布，Microsoft、GitHub、Atlassian、Figma 等首批宣布采用。Agent Skills 是将专业知识、流程、工具使用方式打包为可复用模块的标准。

### 3.2 核心价值

1. **上下文按需加载** — 不再把所有指令塞进 System Prompt，Agent 按需激活 Skills，节省 90%+ Token
2. **能力模块化** — 团队经验固化为数字资产，跨项目、跨平台复用
3. **稳定可预测** — 固化执行流程，减少 LLM 随机性带来的输出不一致
4. **开放标准** — 与 MCP、A2A 互补，不依赖特定模型或框架

### 3.3 标准目录结构

```
my-skill/                         # Skill 名称 (自定义)
├── SKILL.md                      # 必需: YAML 元数据 + Markdown 指令
├── scripts/                      # 可选: 可执行脚本 (Python/Shell/JS)
│   ├── helper.py
│   └── setup.sh
├── references/                   # 可选: 参考文档 (按需加载)
│   ├── api-docs.md
│   ├── conventions.md
│   └── examples.md
└── assets/                       # 可选: 模板/资源文件
    ├── report-template.md
    └── diagram-template.mmd
```

**SKILL.md 文件格式**:

```markdown
---
name: paper-analysis
description: >
  分析学术论文，提取核心贡献、方法论、实验结果和局限性。
  当用户需要理解、比较或评估研究论文时使用此技能。
supported_tools: [arxiv_search, pubmed_search, pdf_reader]
---

# 论文分析技能

## 工作流程

1. **获取论文**: 使用 search 工具检索目标论文
2. **提取核心信息**:
   - 研究问题
   - 方法论/算法
   - 实验设计与数据集
   - 主要结果
   - 局限性
3. **结构化输出**: 按模板 `assets/analysis-template.md` 输出

## 分析维度

### 方法评估
- 将方法与最相关的基线对比
- 评估实验设计的合理性
- 检查消融实验是否充分

### 创新性评估
- 与现有工作的本质差异
- 技术贡献的增量价值

## 常见模式

### 单篇论文深度分析
加载 `references/deep-analysis.md` 获取完整指南

### 多篇论文对比
加载 `references/comparison-guide.md` 获取对比框架
```

### 3.4 渐进式披露 (Progressive Disclosure)

三层加载机制，核心优势是 **上下文窗口的高效利用**:

```
第一层: Metadata 触发层 (常驻上下文)
  └── 所有 Skill 的 name + description 加载到 System Prompt
  └── Agent 根据用户意图判断需要激活哪些 Skill
  └── Token 占用: 极低 (~50 token/skill)

第二层: Core Instructions 核心指令层 (激活时加载)
  └── 当 Agent 确认 Skill 相关时才读取 SKILL.md
  └── 包含 80% 常见场景的处理逻辑
  └── Token 占用: 中等 (500-2000 token/skill)

第三层: Reference Materials 参考资源层 (深度需要时加载)
  └── references/ 中的详细文档
  └── assets/ 中的模板
  └── Token 占用: 按需 (不限制，用完即释放)
```

**实际效果对比**:

| 场景 | 传统 System Prompt | 使用 Skills 后 |
|------|-------------------|---------------|
| 10 个能力模块 | 一次性加载 20K+ Token | 仅加载 ~500 Token 元数据 |
| 触发 1 个能力 | 仍然占用 20K+ Token | ~2K Token (元数据+核心指令) |
| 上下文剩余 | 已被严重压缩 | 充足，留给任务本身 |

### 3.5 五大标准设计模式

Google 在 ADK 实践中总结的五种 Skill 设计模式:

| 模式 | 核心思想 | 适用场景 | Paper Agent 示例 |
|------|---------|---------|-----------------|
| **Tool Wrapper** (工具包装器) | SKILL.md 加载 references/ 规范，Agent 应用规则 | 将领域知识注入工具使用 | "搜索论文时优先返回高引文献" |
| **Generator** (生成器) | 模板+流程控制，确保输出结构和质量 | 文档生成、报告写作 | 论文大纲生成、文献综述 |
| **Reviewer** (审查器) | 加载检查清单，逐条验证输出 | 代码审查、质量检查 | 论文格式审查、引用完整性检查 |
| **Inversion** (反转) | Agent 不直接做，而是引导用户自己完成 | 教育、培训、引导式交互 | 学术写作指导、选题辅导 |
| **Pipeline** (管道) | 多个 Skill 串联，形成完整的处理链 | 复杂多步骤流程 | 搜索→筛选→分析→报告 全流程 |

### 3.6 安装与加载路径

```
项目级别 (优先级最高):
  .claude/skills/<skill-name>/SKILL.md
  .cursor/skills/<skill-name>/SKILL.md
  .github/skills/<skill-name>/SKILL.md

用户级别 (所有项目可见):
  ~/.claude/skills/<skill-name>/SKILL.md
  ~/.cursor/skills/<skill-name>/SKILL.md
```

### 3.7 支持平台 (截至 2026-05)

| 平台 | 支持状态 |
|------|---------|
| Claude Desktop / Claude Code | 原生支持 |
| GitHub Copilot | 项目级 + 个人级 |
| Cursor | 项目级 + 全局，支持 GitHub 安装 |
| Vercel Skills.sh | 开源实现 |
| Spring AI | Java 生态支持 |
| OpenAI Codex CLI | 兼容架构 |

---

## 四、AG-UI 协议 (Agent-User Interaction Protocol)

### 4.1 协议概述

AG-UI 由 CopilotKit 团队于 2025 年 5 月开源发布，是一个轻量级、基于事件的协议，用于标准化 AI Agent 后端与前端的实时交互。

**核心价值**: 不同 Agent 框架（LangGraph, CrewAI, AutoGen 等）输出格式各异，前端需要为每种框架写适配层。AG-UI 统一了这个交互标准。

### 4.2 16 种标准事件

| 事件类型 | 描述 |
|----------|------|
| `TEXT_MESSAGE_START` | 文本消息开始 |
| `TEXT_MESSAGE_CONTENT` | 文本消息内容 (流式) |
| `TEXT_MESSAGE_END` | 文本消息结束 |
| `TOOL_CALL_START` | 工具调用开始 |
| `TOOL_CALL_ARGS` | 工具调用参数 |
| `TOOL_CALL_END` | 工具调用结束 |
| `TOOL_CALL_RESULT` | 工具调用结果 |
| `STATE_SNAPSHOT` | 完整状态快照 |
| `STATE_DELTA` | 增量状态变更 |
| `STEP_STARTED` | 步骤开始 |
| `STEP_FINISHED` | 步骤结束 |
| `MESSAGES_SNAPSHOT` | 消息历史快照 |
| `RUN_STARTED` | 运行开始 |
| `RUN_FINISHED` | 运行结束 |
| `RUN_ERROR` | 运行错误 |
| `CUSTOM` | 自定义事件 |

### 4.3 传输方式

| 传输 | 使用场景 |
|------|---------|
| SSE (Server-Sent Events) | 单向流式推送（推荐） |
| WebSocket | 双向实时通信 |
| Webhook | 异步回调通知 |

### 4.4 与 Paper Agent 的关系

AG-UI 与项目前端直接相关。Paper Agent 的前端 (React + Antd) 如果能接入 AG-UI，将获得：
- 统一的流式 Agent 消息渲染
- 工具调用的实时可视化（如展示检索进度）
- 多步骤执行的状态跟踪
- 跨 Agent 框架的前端适配能力

---

## 五、协议关系与协同

### 5.1 分工矩阵

```
场景: Paper Agent 用户说"帮我搜索深度学习优化最新论文并写综述"

┌─────────────────────────────────────────────────────────────┐
│                      用户 (User)                             │
│                         │                                    │
│                    AG-UI 协议                                │
│                    (流式展示搜索进度、生成进度)               │
│                         │                                    │
│                    ┌─────┴──────┐                            │
│                    │ Paper Agent │ ← Skills 标准              │
│                    │  (Orchestrator)│ ← 加载 paper-search     │
│                    └─────┬──────┘     paper-analysis          │
│                          │            report-generation       │
│              ┌───────────┼───────────┐                       │
│              │           │           │                       │
│         A2A 协议     A2A 协议    A2A 协议                    │
│              │           │           │                       │
│      ┌───────┴──┐ ┌─────┴───┐ ┌────┴──────┐                │
│      │ Search   │ │ Analyze │ │ Write     │                │
│      │ Agent    │ │ Agent   │ │ Agent     │                │
│      └────┬─────┘ └────┬────┘ └─────┬─────┘                │
│           │            │            │                        │
│      MCP 协议      MCP 协议     MCP 协议                     │
│           │            │            │                        │
│    ┌──────┴──────┐ ┌──┴───┐  ┌────┴─────┐                  │
│    │Arxiv MCP    │ │PDF   │  │FileSystem│                  │
│    │PubMed MCP   │ │MCP   │  │MCP        │                  │
│    │Semantic Sch │ │      │  │           │                  │
│    └─────────────┘ └──────┘  └───────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 技术栈层次

| 层 | 协议/标准 | Paper Agent 对应 |
|----|----------|-----------------|
| **能力层** | Skills | `skills/` 目录下的 paper-search、paper-analysis 等 |
| **协作层** | A2A | 多个 Agent 子模块间任务分发与结果同步 |
| **工具层** | MCP | Arxiv、PubMed、Semantic Scholar 等 MCP Server |
| **交互层** | AG-UI | 前端实时流式展示 Agent 执行过程 |

---

## 六、Paper Agent 集成路线图

### 6.1 现状

| 协议/标准 | Paper Agent 现状 | 差距 |
|-----------|-----------------|------|
| MCP | `src/agents_v2/mcp/` 已实现基础版 | 需标准化为完整 MCP Server |
| A2A | 未实现 | 需设计 Agent 间通信机制 |
| Skills | 未实现 | 需按标准重构 Agent 提示词 |
| AG-UI | 未实现 | 前端接入流式状态 |

### 6.2 实施路线图

```
Phase 1 (立即 — 1-2周): 协议基础上线
├── 将 arxiv_mcp.py / pubmed_mcp.py 升级为完整 MCP Server
├── 创建 Semantic Scholar MCP Server
├── 按 Skills 标准重构现有 Agent 提示词为 SKILL.md
└── 设计 AgentCard 描述文件

Phase 2 (短期 — 3-4周): 多 Agent 协作
├── 实现 A2A 协议的 tasks/sendSubscribe (多 Agent 任务分发)
├── 创建 paper-analysis、report-generation Skills
├── 实现 AG-UI 事件流，前端支持实时进度展示
└── 实现 Skills 的动态注册与发现

Phase 3 (中期 — 1-2月): 生态完善
├── 实现完整的 AgentCard 服务发现
├── 创建 Skills 市场/注册表
├── A2A 认证与安全机制
└── 性能压测与优化

Phase 4 (长期 — 3-6月): 开放生态
├── Paper Agent MCP Server 发布到 mcp.so
├── Paper Agent Skills 发布到 agentskills.io
├── 支持第三方 Agent 通过 A2A 接入
└── 贡献开源社区
```

### 6.3 推荐优先级

| 优先级 | 内容 | 理由 |
|--------|------|------|
| **P0** | MCP Server 标准化 | 现有代码基础，改动最小，收益最直接 |
| **P0** | Skills 标准化 | 直接提升 Agent 输出质量和一致性 |
| **P1** | AG-UI 集成 | 用户体验提升明显，前端可展示执行过程 |
| **P1** | A2A 基础实现 | 为多 Agent 协作打基础 |
| **P2** | 完整 A2A 生态 | 需要多 Agent 场景成熟后再深入 |

---

## 七、参考资源

### 官方资源
- [MCP 官方文档](https://modelcontextprotocol.io/)
- [A2A GitHub](https://github.com/google/A2A)
- [Agent Skills 标准](https://agentskills.io/)
- [AG-UI GitHub](https://github.com/CopilotKit/ag-ui)
- [Agent Skills 开源仓库](https://github.com/agentskills/agentskills)

### 社区资源
- [mcp.so](https://mcp.so/) — MCP Server 发现平台
- [smithery.ai](https://smithery.ai/) — MCP Server 托管
- [Skills.sh](https://skills.sh/) — Vercel 开源的 Skills 注册表
- [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers)

### 协议规范
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [A2A JSON Schema](https://github.com/google/A2A/blob/main/specification/json/a2a.json)
- [AG-UI 协议文档](https://docs.ag-ui.com/)

---

**报告生成时间**: 2026-05-01
**调研方法**: 官方文档 + 社区分析 + 行业新闻
**关联报告**: [MCP协议深度调研报告](MCP协议深度调研报告.md) | [PaperAgent Skill 调研报告](PaperAgent_Skill_调研报告.md)
