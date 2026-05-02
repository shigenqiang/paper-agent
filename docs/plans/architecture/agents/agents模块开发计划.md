# agents 模块开发计划

> 规划日期：2026-05-03
> 基于：`docs/implemented/architecture/agents/` + 未来框架设计 v2.1
> 现状：BaseAgent + ReActLoop 已实现

---

## 一、模块概述

### 1.1 现有架构

```
agents/
├── base/
│   └── base_agent.py    # BaseAgent + LLMConfig + AgentCapability ✅ (361行)
├── loops/
│   └── react_loop.py    # ReActExecutor ✅ (546行)
└── roles/              # 角色化 Agent
    ├── __init__.py
    └── *.py
```

### 1.2 提升目标

| 组件 | 当前 | 目标 |
|------|------|------|
| **BaseAgent** | 基础 Pydantic 模型 | Skill 封装 + ToolWrapper |
| **ReActLoop** | 基础 ReAct | Plan-Execute-Reflect + Generator-Critic |
| **角色 Agent** | 基础实现 | 专业能力 + 反思机制 |
| **工具系统** | 直接调用 | MCP 标准化 + Skill 封装 |

---

## 二、任务清单

### 2.1 BaseAgent 增强（P0）

**目标**：Skill 封装 + 工具能力标准化

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| ToolCapability 扩展 | P0 | 工具能力描述标准化 | `src/agents_v2/agents/base/tool_capability.py` |
| SKILL.md 集成 | P0 | 渐进式披露机制 | `src/agents_v2/agents/base/skill_loader.py` |
| AgentCard 支持 | P1 | A2A Agent 发现 | `src/agents_v2/agents/base/agent_card.py` |
| 多模型支持 | P1 | LLMConfig 扩展 | `src/agents_v2/agents/base/multi_model.py` |

### 2.2 ReActLoop 多样化（P1）

**目标**：支持多种 Agent Loop 模式

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| Plan-Execute-Reflect | P1 | 复杂任务分解 | `src/agents_v2/agents/loops/plan_execute.py` |
| Generator-Critic | P1 | 质量敏感生成 | `src/agents_v2/agents/loops/generator_critic.py` |
| 多层 Reflector | P2 | SciSage 式层次反思 | `src/agents_v2/agents/loops/multi_reflector.py` |
| Tree-of-Research | P2 | 树状检索探索 | `src/agents_v2/agents/loops/tree_search.py` |

### 2.3 角色 Agent 完善（P0）

**目标**：专业分工 + 能力增强

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| Searcher Agent | P0 | 多源 MCP 搜索 | `src/agents_v2/agents/roles/searcher.py` |
| Writer Agent | P0 | 上下文感知写作 | `src/agents_v2/agents/roles/writer.py` |
| Reviewer Agent | P0 | 结构化评审 | `src/agents_v2/agents/roles/reviewer.py` |
| Polisher Agent | P1 | 语言润色 | `src/agents_v2/agents/roles/polisher.py` |
| Planner Agent | P1 | 大纲生成 | `src/agents_v2/agents/roles/planner.py` |

### 2.4 Skill 封装（P1）

**目标**：按 Agent Skills 标准重构

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| SKILL.md 解析器 | P1 | 三层渐进式披露 | `src/agents_v2/agents/skills/skill_parser.py` |
| Tool Wrapper | P1 | 工具标准化封装 | `src/agents_v2/agents/skills/tool_wrapper.py` |
| Skill Registry | P1 | 技能注册发现 | `src/agents_v2/agents/skills/registry.py` |
| Skill Generator | P2 | 自动 Skill 生成 | `src/agents_v2/agents/skills/generator.py` |

---

## 三、Agent Loop 模式设计

### 3.1 ReAct（当前实现）

```
Thought → Action → Observation → Thought → ...
```

### 3.2 Plan-Execute-Reflect（目标）

```
Plan → Execute → Reflect → Plan → ...
```

### 3.3 Generator-Critic（目标）

```
Generate → Critic → Revise → Generate → ...
```

---

## 四、实施计划

### Phase 1：基础增强（2周）

```
Week 1:
  - ToolCapability 扩展
  - SKILL.md 解析器

Week 2:
  - Searcher/Writer Agent 完善
  - A2A AgentCard 支持
```

### Phase 2：Loop 多样化（2周）

```
Week 3:
  - Plan-Execute-Reflect Loop
  - Generator-Critic Loop

Week 4:
  - Reviewer/Polisher Agent
  - 多层 Reflector
```

### Phase 3：Skill 封装（1周）

```
Week 5:
  - Tool Wrapper
  - Skill Registry
  - Skill Generator
```

---

## 五、验收标准

- [ ] BaseAgent 支持 Skill 渐进式加载
- [ ] ReActLoop 支持多种 Loop 模式
- [ ] 角色 Agent 达到专业分工要求
- [ ] Skill 可通过 SKILL.md 配置
- [ ] AgentCard 支持 A2A 协议发现

---

**版本**：v1.0
**规划日期**：2026-05-03