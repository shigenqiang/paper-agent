# paper_agents 模块开发计划

> 规划日期：2026-05-02
> 基于：`docs/implemented/architecture/paper_agents/paper-agents.md`
> 现状：TopicAgent/LiteratureAgent/OutlineAgent/DraftWriterAgent/DigestAgent 已实现

---

## 一、模块概述

### 1.1 现有架构

```
paper_agents/
├── topic_agent.py         # 选题 Agent (19,428字节) ✅
├── literature_agent.py   # 文献调研 Agent (12,937字节) ✅
├── outline_agent.py      # 大纲制定 Agent (11,983字节) ✅
├── draft_writer.py       # 初稿撰写 Agent (12,165字节) ✅
├── digest_agent.py      # 摘要生成 Agent (20,923字节) ✅
├── base_paper_agent.py  # PaperAgent 基类 ✅
└── edges.py             # 边定义 ✅
```

### 1.2 提升目标

| Agent | 当前 | 目标 |
|-------|------|------|
| **TopicAgent** | 基础选题 | 研究空白分析 + 可行性评估 |
| **LiteratureAgent** | 6源检索 | 深度探索 + 质量筛选 |
| **OutlineAgent** | 基础大纲 | 层级化 + 方法论匹配 |
| **DraftWriterAgent** | 逐章写作 | Generator-Critic 循环 |
| **ReviewerAgent** | 质量评审 | 5维度结构化评审 |

---

## 二、任务清单

### 2.1 TopicAgent 增强（P1）

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 研究空白分析 | P1 | 识别研究缺口 | `src/agents_v2/paper_agents/topic_gap_analyzer.py` |
| 可行性评估 | P1 | 资源/时间评估 | `src/agents_v2/paper_agents/feasibility_checker.py` |
| 趋势分析 | P2 | 热门方向追踪 | `src/agents_v2/paper_agents/trend_analyzer.py` |

### 2.2 LiteratureAgent 增强（P1）

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 深度探索 | P1 | GPT Researcher 树状检索 | `src/agents_v2/paper_agents/deep_explorer.py` |
| 质量筛选 | P1 | LLM 评分 Top 20 | `src/agents_v2/paper_agents/quality_filter.py` |
| 相关性追踪 | P2 | 引用关系追踪 | `src/agents_v2/paper_agents/citation_tracker.py` |

### 2.3 Generator-Critic 循环（P0）

**目标**：Writer + Reviewer 配对迭代

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| Writer 迭代 | P0 | 章节草稿生成 | `src/agents_v2/paper_agents/draft_writer.py` |
| Reviewer 评审 | P0 | 质量反馈 | `src/agents_v2/paper_agents/reviewer_agent.py` |
| 迭代控制 | P0 | 分数 < 阈值返修 | `src/agents_v2/paper_agents/iteration_controller.py` |
| Polisher 润色 | P1 | 语言一致性 | `src/agents_v2/paper_agents/polisher_agent.py` |

---

## 三、实施计划

```
Week 1:
  - Generator-Critic 循环实现
  - 迭代控制器

Week 2:
  - TopicAgent 增强
  - LiteratureAgent 增强

Week 3:
  - Reviewer 5维度评审
  - Polisher 润色
```

---

## 四、验收标准

- [ ] Generator-Critic 循环正常工作
- [ ] 迭代次数限制有效（max_iterations）
- [ ] 5维度 Reviewer 评审正常
- [ ] 质量评分 ≥ 7.0 通过

---

**版本**：v1.0
**规划日期**：2026-05-02
