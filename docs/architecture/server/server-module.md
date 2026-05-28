# Server 模块

> 版本：v1.0
> 更新日期：2026-05-03
> 基于：`src/agents_v2/server/`

## 模块概述

server 模块提供 HTTP API 服务，是系统的入口层：

- **aiohttp Web 服务**：高性能异步 HTTP 服务
- **请求中间件**：日志、认证、限流
- **SSE 流式响应**：实时推送事件
- **AG-UI 协议支持**：16种事件类型

## 目录结构

```
server/
└── api_server.py           # 主服务器文件
    ├── 请求日志中间件
    ├── API Key 认证
    ├── 限流中间件
    └── SSE 事件推送
```

## 核心功能

### 请求日志中间件

为每个请求添加唯一的 `request_id`，记录：
- 请求方法、路径
- 响应状态
- 执行时长

```python
@web.middleware
async def request_logging_middleware(request, handler):
    request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())[:8]
    start_time = time.time()
    req_logger = logger.bind(request_id=request_id, path=request.path)
    request['logger'] = req_logger
    request['request_id'] = request_id
```

### API Key 认证

公开端点：
- `/` - 首页
- `/health` - 健康检查
- `/docs` - API 文档
- `/openapi.json` - OpenAPI 规范

其他端点需要 `X-API-Key` 请求头。

### SSE 流式响应

支持 Server-Sent Events 实时推送：
- 写作进度
- 搜索结果
- 执行状态

## 端点定义

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/v1/*` | * | 业务 API |
| `/sse/*` | GET | SSE 流式端点 |

## 与其他模块关系

```
HTTP 请求
    │
    ▼
api_server.py
    │
    ├─► api/gateway.py       # API 分发
    ├─► unified/             # 编排逻辑
    ├─► agents/              # Agent 执行
    └─► memory/              # 记忆系统
```

---

**版本**：v1.0
**更新日期**：2026-05-03