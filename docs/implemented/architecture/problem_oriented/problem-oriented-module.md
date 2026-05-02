# Problem Oriented 模块

> 版本：v1.0
> 更新日期：2026-05-03
> 基于：`src/agents_v2/problem_oriented/`

## 模块概述

problem_oriented 模块提供专业领域的问题导向 Agent，包含 11 个专业 Agent：

- **topic_refiner.py**：主题精炼
- **literature_mapper.py**：文献映射
- **research_gap.py**：研究空白分析
- **methodology_advisor.py**：方法论建议
- **argument_builder.py**：论点构建
- **discussion_deepener.py**：讨论深化
- **language_polisher.py**：语言润色
- **chart_formatter.py**：图表格式化
- **section_differentiator.py**：章节区分
- **plagiarism_checker.py**：查重检测
- **supervisor.py**：主管 Agent

## 目录结构

```
problem_oriented/
├── __init__.py
├── argument_builder.py       # 论点构建 (9KB)
├── base_problem_agent.py    # 基础类 (6KB)
├── chart_formatter.py        # 图表格式化 (5KB)
├── discussion_deepener.py   # 讨论深化 (10KB)
├── language_polisher.py     # 语言润色 (11KB)
├── literature_mapper.py     # 文献映射 (16KB)
├── methodology_advisor.py   # 方法论建议 (16KB)
├── plagiarism_checker.py    # 查重检测 (8KB)
├── research_gap.py          # 研究空白 (24KB)
├── research_gap_integration.py # 整合 (15KB)
├── section_differentiator.py # 章节区分 (10KB)
├── supervisor.py            # 主管 (12KB)
└── topic_refiner.py          # 主题精炼 (17KB)
```

## 核心组件

### topic_refiner.py

主题精炼 Agent：
- 研究问题提取
- 关键词扩展
- 研究边界明确

### literature_mapper.py

文献映射 Agent：
- 文献关联分析
- 研究脉络梳理
- 知识结构构建

### research_gap.py

研究空白分析：
- 现有研究不足识别
- 研究机会发现
- 创新点提炼

### methodology_advisor.py

方法论建议：
- 方法选择建议
- 统计方法指导
- 实验设计审查

### language_polisher.py

语言润色：
- 学术语言优化
- 句式结构调整
- 用词准确性检查

## Agent 协作关系

```
supervisor/
    │
    ├─► topic_refiner ──────► 研究问题定义
    ├─► literature_mapper ──► 文献综述
    ├─► research_gap ───────► 研究空白识别
    ├─► methodology_advisor ─► 方法论设计
    │
    ├─► argument_builder ────► 论点构建
    ├─► discussion_deepener ─► 讨论深化
    ├─► section_differentiator ─► 章节区分
    │
    ├─► language_polisher ──► 语言润色
    ├─► chart_formatter ────► 图表格式化
    └─► plagiarism_checker ─► 查重检测
```

## 与其他模块关系

```
paper_agents/
        │
        ▼
    problem_oriented/
        │
        ├─► unified/IntentRouter    # 意图识别
        ├─► unified/HITLManager     # 人机协作
        ├─► tools/                  # 工具调用
        └─► memory/                # 记忆系统
```

---

**版本**：v1.0
**更新日期**：2026-05-03