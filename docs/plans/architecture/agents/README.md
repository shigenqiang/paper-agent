# agents 模块开发计划

> 状态：待规划
> 与未来框架设计 v2.1 对齐

## 模块定位

agents 模块是 Agent 核心框架，提供：
- BaseAgent 基类（Pydantic 模型）
- ReActLoop 执行器
- 角色化 Agent（Searcher/Writer/Reviewer/Polisher）
- 工具能力管理

## 与已实现架构对应

| 已实现文件 | 功能 |
|-----------|------|
| `src/agents_v2/agents/base/base_agent.py` | BaseAgent + LLMConfig + AgentCapability |
| `src/agents_v2/agents/loops/react_loop.py` | ReActExecutor (546行) |
| `src/agents_v2/agents/roles/` | 角色化 Agent |

## 与未来框架设计对应

| 未来框架设计 | 本模块任务 |
|-------------|-----------|
| Agent Skills | SKILL.md 三层渐进式披露 |
| A2A 协议 | Agent 间标准化通信 |
| Generator-Critic | Writer + Reviewer 配对 |
| 多专家对话 | STORM 式模拟辩论 |

## 详细计划

见 `agents模块开发计划.md`

## 进度追踪

- [ ] BaseAgent 增强（ToolCapability）
- [ ] ReActLoop 多样化（Plan-Execute-Reflect）
- [ ] 角色化 Agent 完善
- [ ] Skill 封装支持
- [ ] A2A 协议集成

---

**版本**：v1.0
**更新日期**：2026-05-03