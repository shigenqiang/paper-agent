# 快速开始

## 前置要求

- **Python 3.11+**（推荐 anaconda）
- **fastapi, uvicorn, pydantic, loguru** 等依赖

## 安装

```bash
cd D:\pycharmprojects\pythonProject1
pip install -e .
```

## 配置

在 `.env` 中配置 LLM：

```bash
# LLM 服务配置（按需）
LOG_LEVEL=INFO
```

## 启动服务

```bash
# 方式 1: Makefile（推荐）
make service

# 方式 2: 直接启动
python -m src.service --port 8000

# 指定端口
make service PORT=9000

# 开发模式（自动重载）
python -m src.service --reload
```

服务启动后：
- API: `http://localhost:8000`
- Swagger 文档: `http://localhost:8000/docs`
- 健康检查: `http://localhost:8000/api/health`

## Makefile 命令

| 命令 | 说明 |
|------|------|
| `make service` | 启动服务 |
| `make install` | 安装依赖 |
| `make test` | 运行测试 |
| `make lint` | 代码检查 |
| `make clean` | 清理缓存 |
| `make migrate` | 迁移平铺 JSON 到项目目录隔离 |
| `make docker-build` | 构建 Docker 镜像 |
| `make help` | 查看所有命令 |

## 典型使用流程

```bash
# 1. 创建项目
curl -X POST http://localhost:8000/api/rw/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "my research"}'

# 2. 搜索论文
curl -X POST http://localhost:8000/api/rw/projects/{ref}/papers/search \
  -H "Content-Type: application/json" \
  -d '{"query": "sparse functional data", "limit": 10}'

# 3. 确认入库
curl -X POST http://localhost:8000/api/rw/projects/{ref}/papers/search/commit \
  -H "Content-Type: application/json" \
  -d '{"session_id": "...", "selected_result_ids": ["id1", "id2"]}'

# 4. 解析 → 卡片 → 证据 → 图谱
curl -X POST http://localhost:8000/api/rw/projects/{ref}/papers/parse
curl -X POST http://localhost:8000/api/rw/projects/{ref}/cards
curl -X POST http://localhost:8000/api/rw/projects/{ref}/evidence/build
curl -X POST http://localhost:8000/api/rw/projects/{ref}/kg/build

# 5. QA
curl -X POST http://localhost:8000/api/rw/projects/{ref}/qa \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main methods?", "scope": {"type": "all_project"}}'

# 6. 文献综述
curl -X POST http://localhost:8000/api/rw/projects/{ref}/reports/literature-review \
  -H "Content-Type: application/json" \
  -d '{"scope": {"type": "all_project"}}'

# 7. 创新点报告
curl -X POST http://localhost:8000/api/rw/projects/{ref}/reports/innovation \
  -H "Content-Type: application/json" \
  -d '{"scope": {"type": "all_project"}}'
```

## API 端点一览

完整 API 请访问 `http://localhost:8000/docs` 查看 Swagger 文档。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/rw/projects` | 创建项目 |
| `GET` | `/api/rw/projects` | 项目列表 |
| `POST` | `/api/rw/projects/{ref}/papers/search` | 搜索论文 |
| `POST` | `/api/rw/projects/{ref}/papers/search/commit` | 确认入库 |
| `POST` | `/api/rw/projects/{ref}/papers/parse` | 解析论文 |
| `POST` | `/api/rw/projects/{ref}/cards` | 生成卡片 |
| `POST` | `/api/rw/projects/{ref}/evidence/build` | 构建证据 |
| `POST` | `/api/rw/projects/{ref}/kg/build` | 构建图谱 |
| `POST` | `/api/rw/projects/{ref}/qa` | Scope QA |
| `POST` | `/api/rw/projects/{ref}/reports/literature-review` | 文献综述 |
| `POST` | `/api/rw/projects/{ref}/reports/innovation` | 创新点报告 |
