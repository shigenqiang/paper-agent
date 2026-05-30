# Paper Agent - 运行指南

## 快速启动

```bash
# 1. 安装依赖
pip install -e .

# 2. 配置 .env（按需，含 PARALLEL_WORKERS 控制并行下载/解析数）
cp .env.example .env

# 3. 启动服务
make service
# 或
python -m src.service --port 8000
```

服务启动后：
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- 健康检查: `http://localhost:8000/api/health`

## CLI 命令

除了 HTTP API，还可以用 CLI：

```bash
# 创建项目
python -m src.agents_v3.cli create-project "我的研究"

# 列出项目
python -m src.agents_v3.cli list-projects

# 添加论文
python -m src.agents_v3.cli add-paper <project_id> "论文标题"

# 解析论文
python -m src.agents_v3.cli parse --project-id <project_id>

# 生成卡片
python -m src.agents_v3.cli build-cards <project_id>

# 构建证据表
python -m src.agents_v3.cli build-evidence <project_id>

# 构建知识图谱
python -m src.agents_v3.cli build-graph <project_id>

# QA
python -m src.agents_v3.cli qa <project_id> "What are the main methods?"

# 生成文献综述
python -m src.agents_v3.cli generate-review <project_id>

# 生成创新点报告
python -m src.agents_v3.cli generate-innovation <project_id>

# 项目统计
python -m src.agents_v3.cli stats <project_id>
```

## Docker 部署

```bash
# 构建镜像
make docker-build

# 或使用 docker-compose
docker-compose up -d
```

## 故障排除

### 端口被占用

```bash
netstat -ano | findstr :8000
make service PORT=9000
```

### 依赖缺失

```bash
pip install fastapi uvicorn pydantic loguru pdfplumber
```

### 查看日志

日志文件在 `logs/` 目录。
