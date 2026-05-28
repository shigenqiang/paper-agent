# Paper Search 模块

> 版本：v1.0
> 更新日期：2026-05-03
> 基于：`src/agents_v2/paper_search/`

## 模块概述

paper_search 模块提供论文搜索相关功能：

- **paper_search.py**：主搜索模块
- **paper_flash.py**：快速论文搜索
- **citation_manager.py**：引用管理
- **query_router.py**：查询路由
- **report_generator.py**：报告生成
- **daily_watcher.py**：每日监控
- **weekly_report.py**：周报生成

## 目录结构

```
paper_search/
├── __init__.py
├── base_qa_agent.py         # 基础问答 Agent
├── citation_manager.py      # 引用管理器 (9KB)
├── daily_watcher.py        # 每日监控 (9KB)
├── monthly_report.py       # 月度报告 (11KB)
├── paper_flash.py          # 快速搜索 (14KB)
├── paper_search.py         # 主搜索模块 (23KB)
├── query_router.py         # 查询路由 (9KB)
├── report_generator.py     # 报告生成 (8KB)
└── weekly_report.py        # 周报生成 (10KB)
```

## 核心组件

### paper_search.py

主搜索模块，提供：
- 多源论文搜索
- 结果去重与排序
- 元数据提取

### paper_flash.py

快速搜索，提供：
- 轻量级搜索接口
- 缓存加速
- 结果摘要

### citation_manager.py

引用管理器：
- DOI 解析
- 引用格式转换
- 参考文献校验

### query_router.py

查询路由：
- 查询意图识别
- 搜索策略选择
- 结果重排序

## 与其他模块关系

```
paper_agents/LiteratureAgent
        │
        ▼
    paper_search/
        │
        ├─► search/              # 底层搜索
        ├─► storage/             # 结果存储
        └─► knowledge_graph/     # 图谱增强
```

---

**版本**：v1.0
**更新日期**：2026-05-03