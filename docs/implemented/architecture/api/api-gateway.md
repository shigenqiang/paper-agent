# API 网关层

> 版本：v1.0
> 更新日期：2026-05-03
> 基于：`src/agents_v2/api/`

## 模块概述

api 模块是业务 API 的聚合层，提供统一的 API 入口：

- **gateway.py**：请求分发与路由
- **paper_api.py**：论文相关 API
- **knowledge_graph_api.py**：知识图谱 API
- **reports_api.py**：报告生成 API
- **workflow_api.py**：工作流 API
- **sse_helper.py**：SSE 辅助函数

## 目录结构

```
api/
├── __init__.py
├── gateway.py               # 请求网关 (12KB)
├── knowledge_graph_api.py   # 知识图谱 API (37KB)
├── paper_api.py             # 论文 API (67KB)
├── reports_api.py           # 报告 API (28KB)
├── sse_helper.py            # SSE 辅助 (5KB)
└── workflow_api.py          # 工作流 API (11KB)
```

## 核心组件

### gateway.py

请求分发中心，根据路径将请求路由到对应的业务处理器：

```python
async def handle_request(request):
    path = request.path
    if path.startswith('/api/paper'):
        return paper_api_handler(request)
    elif path.startswith('/api/kg'):
        return knowledge_graph_api_handler(request)
    # ...
```

### paper_api.py

论文相关业务接口：
- 论文搜索
- 论文详情
- 论文元数据
- 引用分析

### knowledge_graph_api.py

知识图谱相关接口：
- 实体查询
- 关系探索
- 社区检测
- 图谱可视化数据

### reports_api.py

报告生成接口：
- 创建报告任务
- 查询报告状态
- 获取报告内容

### workflow_api.py

工作流控制接口：
- 启动工作流
- 暂停/恢复
- 查看进度

## 与其他模块关系

```
server/api_server.py
        │
        ▼
    gateway.py
        │
        ├─► paper_api.py ─────────► paper_agents/
        ├─► knowledge_graph_api.py ► knowledge_graph/
        ├─► reports_api.py ───────► writing/
        ├─► workflow_api.py ──────► langgraph_workflow/
        └─► sse_helper.py ─────────► server/SSE
```

---

**版本**：v1.0
**更新日期**：2026-05-03