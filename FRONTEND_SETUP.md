# 前端启动指南

## 问题诊断

前端显示空白的原因：**Node.js 未安装**

## 解决方案

### 方案 1: 手动安装 Node.js（推荐）

1. **下载 Node.js**
   - 访问：https://nodejs.org/zh-cn/
   - 下载 LTS 版本（推荐 v18.x 或 v20.x）
   - 或直接下载：https://nodejs.org/dist/v18.20.2/node-v18.20.2-x64.msi

2. **安装 Node.js**
   - 双击下载的 `.msi` 文件
   - 按照安装向导操作（全部使用默认选项即可）
   - 安装完成后，重启命令行窗口

3. **验证安装**
   ```bash
   node --version
   npm --version
   ```

4. **启动前端**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **访问前端**
   - 打开浏览器访问：http://localhost:3000

### 方案 2: 使用 Docker（如果 Docker Desktop 已安装）

1. **启动 Docker Desktop**
   - 确保 Docker 引擎正在运行

2. **启动前端容器**
   ```bash
   docker-compose up -d frontend
   ```

3. **访问前端**
   - 打开浏览器访问：http://localhost:3000

### 方案 3: 直接使用后端 API（无需前端）

后端 API 已经完全可用，可以直接通过 API 测试所有功能：

#### 1. 搜索论文
```bash
curl -H "X-API-Key: dev-api-key" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/api/literature/search \
     -d "{\"query\":\"deep learning\",\"source\":\"arxiv\",\"max_results\":5}"
```

#### 2. 创建论文项目
```bash
curl -H "X-API-Key: dev-api-key" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/api/papers \
     -d "{\"title\":\"测试论文\",\"topic\":\"深度学习\"}"
```

#### 3. 生成大纲
```bash
curl -H "X-API-Key: dev-api-key" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/api/papers/{paper_id}/outline/generate \
     -d "{\"topic\":\"深度学习在医学影像中的应用\"}"
```

#### 4. AI 对话
```bash
curl -H "X-API-Key: dev-api-key" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/api/papers/{paper_id}/chat \
     -d "{\"message\":\"什么是Transformer架构？\",\"user_id\":\"user1\",\"session_id\":\"session1\"}"
```

#### 5. 生成学术资讯
```bash
curl -H "X-API-Key: dev-api-key" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/api/reports \
     -d "{\"type\":\"daily\",\"topic\":\"深度学习最新进展\"}"
```

## 当前系统状态

### ✅ 后端 API
- **状态**: 运行中
- **地址**: http://localhost:8000
- **健康检查**: http://localhost:8000/health
- **API Key**: dev-api-key

### ⚠️ 前端界面
- **状态**: 需要安装 Node.js
- **代码**: 完整（7 个页面）
- **配置**: Docker 配置已完成

## 安装后的下一步

安装 Node.js 后，按以下步骤启动前端：

```bash
# 1. 进入前端目录
cd C:\Users\sgqsg\paper-agent\frontend

# 2. 安装依赖（首次运行需要，大约需要 2-3 分钟）
npm install

# 3. 启动开发服务器
npm run dev

# 4. 看到以下输出表示成功：
#   VITE v5.0.8  ready in xxx ms
#   ➜  Local:   http://localhost:3000/
#   ➜  Network: use --host to expose

# 5. 打开浏览器访问
# http://localhost:3000
```

## 故障排除

### 问题 1: npm install 失败
```bash
# 清除缓存后重试
npm cache clean --force
npm install
```

### 问题 2: 端口 3000 被占用
```bash
# 方法 1: 使用其他端口
npm run dev -- --port 3001

# 方法 2: 查找并关闭占用端口的进程
netstat -ano | findstr :3000
taskkill /PID <进程ID> /F
```

### 问题 3: 前端页面空白
1. 打开浏览器开发者工具（F12）
2. 查看 Console 标签页的错误信息
3. 查看 Network 标签页，确认 API 请求是否成功

### 问题 4: API 连接失败
```bash
# 检查后端是否运行
curl http://localhost:8000/health

# 如果后端未运行，启动后端
python -m src.agents_v2.api_server
```

## 系统功能

安装完成后，你可以使用以下功能：

1. **论文搜索** - 多源搜索（arXiv, PubMed, Semantic Scholar, OpenAlex）
2. **定时报告** - 每日/周/月学术资讯自动生成
3. **论文写作** - AI 辅助大纲生成、内容写作、多轮审查
4. **论文修改** - 智能改稿、精炼、语言润色
5. **对话问答** - 基于论文的智能问答、比较分析
6. **记忆系统** - 用户偏好学习、跨会话知识管理

## 需要帮助？

- 查看完整文档：RUNNING.md
- 运行测试：`pytest tests/test_unified_workflow.py -v`
- 查看 API 文档：http://localhost:8000/docs（启动后端后访问）
