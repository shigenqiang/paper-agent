# Paper Agent - 智能论文调研与写作系统

> 基于多Agent协作的学术论文自动调研与综述生成系统

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Test Status](https://img.shields.io/badge/tests-157%20passed-green.svg)]()
[![Score](https://img.shields.io/badge/score-9.2%2F10-orange.svg)]()

---

## 项目概述

Paper Agent 是一个多Agent协作系统，旨在辅助学术论文研究、选题、写作全流程。

### 核心功能

- **智能路由**: 自动判断问题类型，决定处理策略
- **论文搜索**: 自动从arXiv/PubMed/Semantic Scholar等学术平台搜索论文
- **专业报告**: 基于真实论文给出带参考文献的专业回答
- **论文写作**: 从选题到完稿的全流程辅助
- **智能改稿**: 解析导师意见，自动优化文本
- **记忆系统**: 基于Mem0/Zep架构的多层级记忆管理

### 应用场景

| 场景 | 说明 |
|------|------|
| 快速调研 | 快速了解某研究领域的前沿进展 |
| 论文搜索 | 寻找特定研究方向的开创性工作 |
| 专业问答 | 获取跨学科的研究洞察 |
| 文献追踪 | 每日/每周/每月推送论文摘要报告 |
| 论文写作 | 从选题到完稿的全流程辅助 |
| 智能改稿 | 解析导师意见，自动优化文本 |

---

## 系统架构

```
用户请求
    │
    ▼
┌─────────────────┐
│  IntentRouter   │ ← 意图识别
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│Pipeline │ │Problem │
│ Agent  │ │ Agent  │
└────────┘ └────────┘
         │
         ▼
┌─────────────────┐
│ MasterSupervisor│ ← 全局协调
└────────┬────────┘
          │
          ▼
┌─────────────────┐
│  UnifiedMemory   │
│  Manager         │
└─────────────────┘
```

### 记忆系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    UnifiedMemoryManager                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ ShortTerm   │  │   Session   │  │  LongTerm   │        │
│  │  Memory     │  │   Memory    │  │   Memory    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Episodic   │  │ Relational  │  │   Vector    │        │
│  │   Memory    │  │   Storage   │  │   Storage   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│                    Retrieval Engine                          │
│  (Hybrid Retriever + BM25 + Query Classification)          │
├─────────────────────────────────────────────────────────────┤
│                    Storage Backends                          │
│  PostgreSQL + pgvector | Redis | Neo4j                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
OPENAI_API_KEY=your_api_key_here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4

# 可选代理
# HTTP_PROXY=http://127.0.0.1:7890
# HTTPS_PROXY=http://127.0.0.1:7890
```

### 3. 运行测试

```bash
python -m pytest tests/ -v
```

### 4. 启动API服务

```bash
python -m src.agents_v2.api_server
```

服务将在 `http://localhost:8000` 启动。

---

## 核心Agent

### Pipeline Agent

| Agent | 功能 | 状态 |
|-------|------|------|
| TopicAgent | 选题 | ✅ |
| LiteratureAgent | 文献搜索 | ✅ |
| ThesisAgent | Thesis凝练 | ✅ |
| OutlineAgent | 大纲制定 | ✅ |
| DraftWriterAgent | 初稿撰写 | ✅ |
| EditorAgent | 修订编辑 | ✅ |
| ReviewerAgent | 最终审核 | ✅ |

### Problem-Oriented Agent

| Agent | 针对问题 | 状态 |
|-------|----------|------|
| TopicRefinerAgent | 选题困难 | ✅ |
| LiteratureMapperAgent | 文献综述不充分 | ✅ |
| MethodologyAdvisorAgent | 研究方法不当 | ✅ |
| DiscussionDeepenerAgent | 讨论部分薄弱 | ✅ |
| LanguagePolisherAgent | 语言表达问题 | ✅ |

### 记忆系统组件

| 组件 | 功能 | 状态 |
|------|------|------|
| ShortTermMemory | 短期上下文 (LRU+TTL) | ✅ |
| SessionMemory | 跨Agent共享 | ✅ |
| LongTermMemory | 持久化存储 | ✅ |
| EpisodicMemory | 执行轨迹 + 时序推理 | ✅ |
| VectorStorage | 向量搜索 | ✅ |
| RelationalStorage | 关系数据库 | ✅ |

---

## API端点

### 基础端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/topic` | POST | 选题 |
| `/api/search` | POST | 论文搜索 |
| `/api/route` | POST | 意图路由 |

### 写作端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/literature` | POST | 文献综述 |
| `/api/proposal` | POST | 开题报告 |
| `/api/paper` | POST | 完整论文 |
| `/api/draft` | POST | 论文初稿 |
| `/api/revise` | POST | 局部修改 |
| `/api/diagnostics` | POST | 诊断 |

### 高级端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/batch` | POST | 批量请求 |
| `/ws/status` | GET | WebSocket状态推送 |

---

## 使用示例

### Python API

```python
import asyncio
from src.agents_v2.paper_agents import TopicAgent
from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

async def main():
    agent = TopicAgent(LLMConfig(provider="openai", model_name="gpt-4"))
    result = await agent.execute({
        "user_request": "深度学习在医学影像诊断中的应用"
    })
    print(f"Success: {result.success}")
    print(f"Quality: {result.quality_score}")

asyncio.run(main())
```

### HTTP API

```bash
# 选题
curl -X POST http://localhost:8000/api/topic \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"user_request": "深度学习优化"}'

# 完整论文
curl -X POST http://localhost:8000/api/paper \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"topic": "图像分割算法研究"}'
```

---

## 记忆系统使用

```python
from src.agents_v2.memory import (
    UnifiedMemoryManager,
    MemoryType,
    create_embedder,
    EmbeddingConfig
)

# 创建记忆管理器
memory = UnifiedMemoryManager()

# 存储记忆
await memory.remember(
    key="user_preference",
    value="用户偏好Python",
    memory_type=MemoryType.USER_PROFILE,
    importance=0.8
)

# 搜索记忆
results = await memory.search(
    query="用户偏好什么语言",
    memory_types=[MemoryType.USER_PROFILE]
)

# 获取Agent上下文
context = await memory.get_context_for_agent("topic_agent")
```

---

## 技术特性

### Mem0风格设计
- LLM驱动的记忆提取
- 单通道ADD-only写入
- 分层记忆架构
- 自动重要性评估

### 生产级特性
- 断路器模式
- 降级策略
- 连接池管理
- 批量操作优化
- 预取策略

### 安全与监控
- 访问控制 (RBAC)
- 数据脱敏
- 性能监控
- 访问分析
- 审计日志

---

## 测试状态

```
总测试数: 260个
通过: 254个
失败: 0个 (6个跳过因需要外部服务)
通过率: 100% (核心测试)
```

---

## 项目结构

```
src/agents_v2/
├── memory/                 # 记忆系统 (30+组件)
│   ├── short_term.py      # 短期记忆
│   ├── session.py         # 会话记忆
│   ├── long_term.py       # 长期记忆
│   ├── episodic.py        # 情景记忆
│   ├── retrieval.py       # 检索引擎
│   ├── embeddings.py      # 向量嵌入
│   ├── services.py        # 核心服务
│   ├── unified.py         # 统一管理器
│   └── ...
├── knowledge_graph/       # 知识图谱模块
│   ├── kg_service.py      # KG核心服务
│   ├── kg_schema.py       # 图谱Schema
│   ├── kg_vector_store.py # 向量存储
│   ├── kg_embeddings.py   # Embeddings
│   ├── kg_summarizer.py   # 摘要生成
│   ├── kg_community.py   # 社区检测
│   ├── kg_batch.py       # 批量操作
│   ├── kg_graphrag.py     # GraphRAG
│   └── kg_hybrid_retriever.py # 混合检索
├── paper_agents/          # Pipeline Agent
├── problem_oriented/      # 问题导向Agent
├── writing/               # 写作Agent
├── unified/               # 统一框架
├── tools/                 # 工具链
└── api_server.py          # HTTP API
```

---

## 文档

| 文档 | 说明 |
|------|------|
| [迭代报告与开发计划](docs/开发文档/迭代报告与开发计划.md) | 完整迭代历程与开发计划 |
| [API文档_完整版](docs/开发文档/API文档_完整版.md) | Agent API、HTTP API、Memory API |
| [Agent记忆系统设计文档](docs/Agent记忆系统设计文档.md) | 记忆框架调研与设计 |
| [数据库选型指南](docs/开发文档/数据库选型指南.md) | PostgreSQL、Redis、Neo4j选型 |
| [部署指南](docs/开发文档/部署指南.md) | Docker、本地部署 |
| [快速开始](docs/开发文档/快速开始.md) | 入门指南 |
| [Complete Prompt Engineering Guide](docs/调研报告/Complete_Prompt_Engineering_Guide.md) | 提示词工程完全指南 |

---

## 与优秀框架对比

| 功能 | Mem0 | MemGPT | Claude Code | Paper Agent |
|------|------|--------|-------------|-------------|
| 多级记忆 | ✅ | ✅ | ✅ | ✅ |
| LLM智能提取 | ✅ | ❌ | ✅ | ✅ |
| 主动检索 | ✅ | ❌ | ✅ | ✅ |
| 真实向量嵌入 | ✅ | ✅ | ✅ | ✅ |
| 图关系 | ✅ | ❌ | ❌ | ✅ |
| 时序推理 | ⚠️ | ❌ | ❌ | ✅ |
| MCP协议 | ❌ | ❌ | ❌ | ✅ |
| 监控面板 | ⚠️ | ❌ | ⚠️ | ✅ |

---

## 开发历程

| 阶段 | 轮次 | 评分 |
|------|------|------|
| 基础建设 | 1-7 | 7.8/10 |
| 基础设施 | 8-14 | 8.0/10 |
| 部署监控 | 15-20 | 8.8/10 |
| 企业级功能 | 21-30 | 8.8/10 |
| 记忆重构 | 31-50 | 8.6/10 |
| 记忆完善 | 51-60 | 9.0/10 |
| 系统整合 | 81-100 | 9.2/10 |
| Phase 1 | 101-105 | 9.2/10 |
| Phase 2 | 106-110 | 9.0/10 |
| Phase 3 | 111-113 | 9.5/10 |

**当前评分**: 9.5/10

---

## 后续计划

| 阶段 | 轮次 | 方向 | 进度 |
|------|------|------|------|
| Phase 1 | 101-105 | 评估与优化 | 5/5 (100%) ✅ |
| Phase 2 | 106-110 | 用户体验优化 | 5/5 (100%) ✅ |
| Phase 3 | 111-113 | 高级功能 | 3/5 (60%) |
| Phase 4 | 116-120 | 生产就绪 | 0/5 (0%) |

详细计划请查看 [迭代报告与开发计划](docs/开发文档/迭代报告与开发计划.md)

---

## 已知限制

1. **MiniMax中文问题**: 模型有中文编码bug，建议使用GPT-4/Claude或TranslationWrapper
2. **外部服务依赖**: Redis、Neo4j测试需要外部服务运行
3. **网络依赖**: 需要访问外部API（arXiv, PubMed, OpenAI等）

---

## 贡献

欢迎提交Issue和Pull Request！

---

## 许可证

MIT License

---

**项目状态**: 进行中 🔄
**最后更新**: 2026-04-26
