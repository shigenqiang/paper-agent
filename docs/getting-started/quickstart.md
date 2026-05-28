# Paper Agent 运行指南

## 前置要求

- **Python 3.10+** - 后端运行环境
- **Node.js 18+** - 前端运行环境（已安装在 `C:\Users\sgqsg\nodejs`）

## 启动命令

### 1. 启动后端 (Python API Server)

```bash
cd C:\Users\sgqsg\paper-agent
python -m src.agents_v2.api_server
```

后端服务启动后监听 `http://0.0.0.0:8000`，默认 API Key 为 `dev-api-key`。

### 2. 启动前端 (Vite Dev Server)

```bash
cd C:\Users\sgqsg\paper-agent\frontend
C:\Users\sgqsg\nodejs\npm run dev
```

前端开发服务器默认运行在 `http://localhost:3000`，自动代理 API 请求到后端 `http://localhost:8000`。

## 快速启动（两个终端同时运行）

**终端 1 - 后端：**
```bash
cd C:\Users\sgqsg\paper-agent && python -m src.agents_v2.api_server
```

**终端 2 - 前端：**
```bash
cd C:\Users\sgqsg\paper-agent\frontend && C:\Users\sgqsg\nodejs\npm run dev
```

## 功能说明

| 功能 | 状态 | 说明 |
|------|------|------|
| 论文写作 | ✅ | 创建论文、生成大纲、AI续写 |
| 文献搜索 | ✅ | arXiv + PubMed 多源搜索，支持分页和批量添加 |
| 学术资讯 | ✅ | 根据关键词自动生成每日/每周/每月学术报告 |
| 报告下载 | ✅ | 支持下载为 Markdown 文件 |
| AI助手 | ✅ | 智能问答 |
