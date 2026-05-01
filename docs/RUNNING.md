# Paper Agent - 运行指南

## 系统架构

Paper Agent 是一个基于 LangGraph 的智能论文调研与写作系统，支持 6 大核心功能：

1. **论文搜索** - 多源搜索（arXiv, PubMed, Semantic Scholar, OpenAlex）
2. **定时报告** - 每日/周/月学术资讯自动生成
3. **论文写作** - AI 辅助大纲生成、内容写作、多轮审查
4. **论文修改** - 智能改稿、精炼、语言润色
5. **对话问答** - 基于论文的智能问答、比较分析
6. **记忆系统** - 用户偏好学习、跨会话知识管理

## 快速开始

### 1. 启动后端 API 服务器

```bash
# 方式 1: 直接运行
python -m src.agents_v2.api_server

# 方式 2: 使用 Docker
docker-compose up -d paper-agent

# 验证服务
curl http://localhost:8000/health
```

后端地址: `http://localhost:8000`

### 2. 启动前端界面

#### 方式 A: 使用 Docker（推荐）

```bash
# 确保 Docker Desktop 正在运行
docker-compose up -d frontend

# 访问前端
# http://localhost:3000
```

#### 方式 B: 本地开发模式

```bash
# 1. 安装 Node.js (https://nodejs.org)

# 2. 安装依赖
cd frontend
npm install

# 3. 启动开发服务器
npm run dev

# 访问前端
# http://localhost:3000
```

### 3. 配置环境变量

创建 `.env` 文件：

```bash
# API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key  # 可选
MINIMAX_API_KEY=your_minimax_key      # 可选

# API 服务器
API_KEY=dev-api-key

# 数据库（可选）
POSTGRES_URI=postgresql://paper:paper@localhost:5432/paperagent
REDIS_URL=redis://localhost:6379
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=paperagent
```

## API 使用示例

### 搜索论文

```bash
curl -H "X-API-Key: dev-api-key" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/api/literature/search \
     -d '{
       "query": "deep learning",
       "source": "arxiv",
       "max_results": 10
     }'
```

### 创建论文项目

```bash
curl -H "X-API-Key: dev-api-key" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/api/papers \
     -d '{
       "title": "深度学习综述",
       "topic": "deep learning"
     }'
```

### 生成大纲

```bash
curl -H "X-API-Key: dev-api-key" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/api/papers/{paper_id}/outline/generate \
     -d '{
       "topic": "深度学习在医学影像中的应用"
     }'
```

### AI 对话

```bash
curl -H "X-API-Key: dev-api-key" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/api/papers/{paper_id}/chat \
     -d '{
       "message": "什么是 Transformer 架构？",
       "user_id": "user1",
       "session_id": "session1"
     }'
```

### 生成学术资讯

```bash
curl -H "X-API-Key: dev-api-key" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/api/reports \
     -d '{
       "type": "daily",
       "topic": "深度学习最新进展"
     }'
```

## 使用统一工作流

### Python API

```python
from src.agents_v2.langgraph_workflow import create_unified_workflow

# 创建工作流
workflow = create_unified_workflow(
    llm=your_llm,
    enable_memory=True,
    enable_multimodal=True,
    enable_kg=True,
)

# 编译工作流
app = workflow.compile()

# 运行查询（自动路由）
result = await workflow.run(
    query="帮我写一篇关于因果推断的综述",
    user_id="user1",
    session_id="session1",
)

# 获取追踪信息
trace = workflow.get_trace_summary()
```

### 工作流路径

系统会根据查询意图自动路由到不同工作流：

1. **搜索工作流**: "搜索深度学习论文" → crawler → selector
2. **写作工作流**: "写一篇综述" → memory → crawler → selector → multimodal → kg → outline → write → review → evaluator
3. **报告工作流**: "生成本周资讯" → report_crawl → report_analyze → report_gen
4. **问答工作流**: "什么是 Transformer" → qa_search → qa_synthesize → qa_answer
5. **修改工作流**: "润色这段文字" → revise → refine → polish

## 测试

### 运行单元测试

```bash
# 测试 LangGraph 工作流
pytest tests/test_langgraph_workflow.py -v

# 测试端到端
pytest tests/test_e2e_langgraph.py -v

# 测试统一工作流
python test_unified_workflow.py
```

### 运行演示

```bash
# LangGraph 工作流演示
python demo_langgraph_workflow.py

# 完整系统演示
python demo_stage1.py
```

## 故障排除

### 前端显示空白

1. **检查前端服务是否启动**
   ```bash
   curl http://localhost:3000
   ```

2. **检查浏览器控制台**
   - 打开浏览器开发者工具（F12）
   - 查看 Console 标签页的错误信息
   - 查看 Network 标签页的请求状态

3. **检查 API 连接**
   ```bash
   # 前端应该能访问后端 API
   curl http://localhost:8000/health
   ```

4. **重新构建前端**
   ```bash
   cd frontend
   npm install
   npm run build
   npm run dev
   ```

### 后端 API 错误

1. **检查日志**
   ```bash
   # 查看 API 服务器日志
   tail -f api_server.log
   ```

2. **检查依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **检查环境变量**
   ```bash
   # 确保 .env 文件存在
   cat .env
   ```

### Docker 问题

1. **Docker Desktop 未运行**
   - 启动 Docker Desktop
   - 等待 Docker 引擎启动完成

2. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -ano | findstr :3000
   netstat -ano | findstr :8000
   ```

3. **重新构建容器**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

## 项目结构

```
paper-agent/
├── src/agents_v2/
│   ├── langgraph_workflow/      # LangGraph 工作流
│   │   ├── nodes/               # 工作流节点
│   │   │   ├── router.py        # 路由节点
│   │   │   ├── crawler.py       # 爬虫节点
│   │   │   ├── selector.py      # 选择节点
│   │   │   ├── outline.py       # 大纲节点
│   │   │   ├── writer.py        # 写作节点
│   │   │   ├── reviewer.py      # 审查节点
│   │   │   ├── evaluator.py     # 评估节点
│   │   │   ├── memory.py        # 记忆节点
│   │   │   ├── multimodal.py    # 多模态节点
│   │   │   ├── knowledge_graph.py # 知识图谱节点
│   │   │   ├── report_*.py      # 报告工作流节点
│   │   │   ├── qa_*.py          # 问答工作流节点
│   │   │   └── revise/refine/polish.py # 修改工作流节点
│   │   ├── unified_workflow.py  # 统一工作流
│   │   ├── workflow.py          # 基础工作流
│   │   ├── state.py             # 状态定义
│   │   └── edges.py             # 边和路由
│   ├── api/                     # API 层
│   │   ├── paper_api.py         # 论文 API
│   │   └── reports_api.py       # 报告 API
│   ├── api_server.py            # API 服务器
│   ├── search/                  # 搜索模块
│   ├── qa/                      # 问答模块
│   ├── writing/                 # 写作模块
│   ├── paper_agents/            # 论文 Agent
│   ├── routing/                 # 路由模块
│   └── memory/                  # 记忆模块
├── frontend/                    # React 前端
│   ├── src/
│   │   ├── pages/               # 页面组件
│   │   ├── components/          # UI 组件
│   │   ├── services/            # API 服务
│   │   └── store/               # 状态管理
│   ├── Dockerfile               # 前端 Docker 配置
│   └── nginx.conf               # Nginx 配置
├── tests/                       # 测试文件
├── docs/                        # 文档
├── docker-compose.yml           # Docker Compose 配置
└── requirements.txt             # Python 依赖
```

## 开发文档

详细开发文档请参考：
- [统一开发计划 v12.0](docs/开发文档/统一开发计划_v12.0_融合版.md)
- [LangGraph 工作流开发总结](docs/开发文档/LangGraph工作流开发总结.md)

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
