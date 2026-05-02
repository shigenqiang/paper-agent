# Paper Agent API 完整参考文档

**文档版本**: v2.2
**更新日期**: 2026-05-03
**综合评分**: 9.2/10

---

## 一、系统概述

### 1.1 项目目标

Paper Agent 是一个多Agent协作系统，旨在辅助学术论文研究、选题、写作全流程。

### 1.2 核心架构

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

---

## 二、快速开始

### 2.1 安装依赖

```bash
pip install -r requirements.txt

# 记忆系统依赖 (可选)
pip install psycopg2-binary pgvector redis neo4j

# 向量嵌入 (可选)
pip install openai  # OpenAI嵌入
pip install sentence-transformers  # 本地嵌入
```

### 2.2 环境变量配置

```bash
# LLM配置
export OPENAI_API_KEY=your_api_key_here
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4

# 代理配置 (可选)
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890

# 数据库配置 (可选)
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export REDIS_HOST=localhost
export REDIS_PORT=6379

# 学术搜索API (可选)
export SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_key  # https://api.semanticscholar.org/
export TRINKA_API_KEY=your_trinka_key                        # https://www.trinka.ai/ (学术语法检查)

# Zotero引用管理 (可选)
export ZOTERO_API_KEY=your_zotero_api_key                  # https://www.zotero.org/settings/keys
export ZOTERO_USER_ID=your_zotero_user_id                   # https://api.zotero.org/keys/self
```

### 2.3 基本使用

```python
import asyncio
from src.agents_v2.paper_agents import TopicAgent
from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

# 配置LLM
llm_config = LLMConfig(
    provider="openai",
    model_name="minimax",
    temperature=0.7
)

# 创建Agent并执行
async def main():
    agent = TopicAgent(llm_config)
    result = await agent.execute({
        "user_request": "机器学习在医疗诊断中的应用"
    })
    print(f"Success: {result.success}")
    print(f"Quality: {result.quality_score}")

asyncio.run(main())
```

---

## 三、Agent类型

### 3.1 PaperAgent (Pipeline型)

用于从零写完整论文，串起完整流程。

```python
from src.agents_v2.paper_agents.base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig
```

**核心方法**:
- `execute(input_data, context) -> AgentOutput`: 执行Agent任务
- `add_tool(tool)`: 添加工具
- `get_tool_schemas() -> List[Dict]`: 获取工具schema

### 3.2 ProblemAgent (问题导向型)

用于修复论文局部缺陷。

```python
from src.agents_v2.problem_oriented.base_problem_agent import ProblemAgentBase
```

**核心方法**:
- `diagnose(input_data, context) -> AgentOutput`: 诊断问题
- `fix(input_data, context) -> AgentOutput`: 修复问题

### 3.3 WritingAgent (写作型)

用于论文写作全流程。

```python
from src.agents_v2.writing.base_writing_agent import BaseWritingAgent
```

---

## 四、核心Agent API

### 4.1 TopicAgent

主题选择与研究问题凝练。

```python
from src.agents_v2.paper_agents import TopicAgent

agent = TopicAgent(llm_config=None)

result = await agent.execute({
    "user_request": "你的研究兴趣或方向"
})
```

**输入**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_request | string | 是 | 用户的研究请求 |

**输出** (AgentOutput):
```python
{
    "success": True,
    "result": {
        "selected_topic": {
            "title": "...",
            "description": "...",
            "scope": "...",
            "potential_methods": [...],
            "expected_contribution": "...",
            "scores": {...},
            "overall_score": 0.8,
            "risk_factors": [...]
        },
        "alternative_topics": [...],
        "domain_analysis": {...}
    },
    "quality_score": 0.8
}
```

### 4.2 LiteratureAgent

文献搜索、筛选与综述。

```python
from src.agents_v2.paper_agents import LiteratureAgent

agent = LiteratureAgent(llm_config)
result = await agent.execute({
    "topic": "研究主题"
}, context={"research_question": "具体问题"})
```

**输入**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| topic | string | 是 | 研究主题 |
| research_question | string | 否 | 具体研究问题 |

### 4.3 ThesisAgent

研究Thesis的凝练与优化。

```python
from src.agents_v2.paper_agents import ThesisAgent

agent = ThesisAgent(llm_config)
result = await agent.execute({
    "topic": "研究主题",
    "literature_result": {...}
})
```

### 4.4 OutlineAgent

论文大纲制定。

```python
from src.agents_v2.paper_agents import OutlineAgent

agent = OutlineAgent(llm_config)
result = await agent.execute({
    "topic": "研究主题",
    "thesis_statement": "Thesis陈述",
    "literature_summary": {...}
})
```

### 4.5 DraftWriterAgent

分节撰写论文初稿。

```python
from src.agents_v2.paper_agents import DraftWriterAgent

agent = DraftWriterAgent(llm_config)
result = await agent.execute({
    "topic": "研究主题",
    "outline": {...},
    "literature_summary": {...}
})
```

---

## 五、问题导向Agent API

### 5.1 TopicRefinerAgent

选题精炼与可行性评估。

```python
from src.agents_v2.problem_oriented import TopicRefinerAgent

agent = TopicRefinerAgent(llm_config)
result = await agent.diagnose({
    "topic_idea": "初步想法",
    "research_field": "研究领域"
})
```

### 5.2 DiscussionDeepenerAgent

深化讨论部分。

```python
from src.agents_v2.problem_oriented import DiscussionDeepenerAgent

agent = DiscussionDeepenerAgent(llm_config)
result = await agent.fix({
    "current_discussion": "当前讨论内容",
    "literature_context": {...}
})
```

### 5.3 LanguagePolisherAgent

语言润色。

```python
from src.agents_v2.problem_oriented import LanguagePolisherAgent

agent = LanguagePolisherAgent(llm_config)
result = await agent.fix({
    "text": "需要润色的文本",
    "language": "en"
})
```

---

## 六、Writing Agent API

### 6.1 DraftGeneratorAgent

生成完整论文初稿。

```python
from src.agents_v2.writing import DraftGeneratorAgent

agent = DraftGeneratorAgent(llm_config)
result = await agent.execute({
    "title": "论文标题",
    "outline": {...},
    "requirements": ["创新性", "实用性"]
})
```

### 6.2 ProposalGeneratorAgent

生成开题报告。

```python
from src.agents_v2.writing import ProposalGeneratorAgent

agent = ProposalGeneratorAgent(llm_config)
result = await agent.execute({
    "research_topic": "研究主题",
    "background": "研究背景"
})
```

---

## 七、配置参数

### 7.1 LLMConfig

```python
from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

config = LLMConfig(
    provider="openai",        # openai 或 anthropic
    model_name="minimax",     # 模型名称
    temperature=0.7,          # 温度参数
    max_tokens=4096,         # 最大token数
    api_key=None,            # API密钥
    base_url=None            # API基础URL
)
```

### 7.2 质量阈值

```python
QUALITY_THRESHOLDS = {
    "diagnostic": 6.0,
    "topic": 7.0,
    "literature": 7.0,
    "methodology": 7.0,
    "writing": 7.0,
    "polish": 8.0
}
```

---

## 八、HTTP API

### 8.1 API版本

| 项目 | 值 |
|------|---|
| 当前版本 | v1 |
| 基础URL | `http://localhost:8000` |
| 协议 | HTTP |
| 格式 | JSON |

### 8.2 认证

API使用API密钥认证：

```
X-API-Key: your_api_key_here
```

### 8.3 速率限制

| 等级 | 限制 |
|------|------|
| 默认 | 100请求/分钟 |
| 已认证 | 500请求/分钟 |

### 8.4 端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/topic` | POST | 选题 |
| `/api/search` | POST | 论文搜索 |
| `/api/route` | POST | 意图路由 |
| `/api/literature` | POST | 文献综述 |
| `/api/proposal` | POST | 开题报告 |
| `/api/paper` | POST | 完整论文 |
| `/api/draft` | POST | 论文初稿 |
| `/api/revise` | POST | 局部修改 |
| `/api/diagnostics` | POST | 诊断 |
| `/api/batch` | POST | 批量请求 |
| `/ws/status` | GET | WebSocket状态推送 |

### 8.5 端点详情

#### 健康检查

```
GET /health
```

**响应**:
```json
{
    "status": "healthy"
}
```

#### 选题

```
POST /api/topic
```

**请求体**:
```json
{
    "user_request": "深度学习在医学影像诊断中的应用"
}
```

**响应**:
```json
{
    "success": true,
    "result": {
        "selected_topic": {
            "title": "基于深度学习的医学影像诊断算法研究",
            "description": "研究利用深度学习技术自动诊断医学影像的算法...",
            "scope": "图像分割、病变检测、诊断准确率提升",
            "potential_methods": ["U-Net", "Transformer", "CNN"],
            "expected_contribution": "提高诊断准确率，减少漏诊",
            "scores": {
                "novelty": 8.0,
                "feasibility": 8.5,
                "impact": 9.0
            },
            "overall_score": 8.5,
            "risk_factors": ["数据获取难度", "标注成本"]
        }
    },
    "quality_score": 8.5,
    "execution_time": 12.5,
    "timestamp": "2026-04-26T10:00:00"
}
```

#### 论文搜索

```
POST /api/search
```

**请求体**:
```json
{
    "query": "transformer image segmentation",
    "source": "arxiv",
    "max_results": 10
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 搜索关键词 |
| source | string | 否 | arxiv/pubmed/all |
| max_results | integer | 否 | 最大结果数（默认10） |

#### 意图路由

```
POST /api/route
```

**请求体**:
```json
{
    "user_request": "我想写一篇关于深度学习优化的论文"
}
```

**响应**:
```json
{
    "intent": "full_paper",
    "suggested_agents": ["TopicAgent", "LiteratureAgent", "ThesisAgent"],
    "mode": "sequential",
    "execution_time": 0.5
}
```

#### 文献综述

```
POST /api/literature
```

**请求体**:
```json
{
    "topic": "深度学习图像分割"
}
```

#### 开题报告

```
POST /api/proposal
```

**请求体**:
```json
{
    "topic": "基于深度学习的医学影像诊断研究",
    "research_background": "医学影像诊断是临床诊断的重要组成部分...",
    "research_significance": "提高诊断准确率，减少漏诊和误诊..."
}
```

#### 完整论文

```
POST /api/paper
```

**请求体**:
```json
{
    "topic": "图像分割算法研究"
}
```

**响应**:
```json
{
    "success": true,
    "result": {
        "phases_completed": ["diagnostic", "topic", "literature", "methodology", "writing", "polish"],
        "final_paper": "# 论文标题\n\n## 摘要\n...",
        "final_quality": 8.5,
        "quality_level": "excellent",
        "iterations": 1
    },
    "quality_score": 8.5,
    "execution_time": 120.0
}
```

#### 论文初稿

```
POST /api/draft
```

**请求体**:
```json
{
    "topic": "图像分割算法研究",
    "outline": {
        "sections": ["引言", "方法", "实验", "结论"]
    }
}
```

#### 局部修改

```
POST /api/revise
```

**请求体**:
```json
{
    "content": "需要修改的论文内容...",
    "revision_type": "general"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | string | 是 | 需要修改的内容 |
| revision_type | string | 否 | 修改类型（general/deep/language） |

#### 诊断

```
POST /api/diagnostics
```

**请求体**:
```json
{
    "content": {
        "abstract": "摘要内容...",
        "introduction": "引言内容..."
    },
    "phase": "writing"
}
```

#### 批量请求

```
POST /api/batch
```

**请求体**:
```json
{
    "requests": [
        {
            "type": "topic",
            "data": {"user_request": "深度学习优化"}
        },
        {
            "type": "search",
            "data": {"query": "transformer", "max_results": 5}
        }
    ]
}
```

#### WebSocket状态推送

```
GET /ws/status
```

每5秒推送一次系统指标。

```json
{
    "type": "metrics",
    "data": {
        "total_requests": 1000,
        "success_rate": 0.95,
        "avg_response_time": 0.2,
        "cache_hit_rate": 0.8,
        "timestamp": "2026-04-26T10:00:00"
    }
}
```

### 8.6 统一响应格式

```json
{
    "success": true,
    "result": {...},
    "quality_score": 8.5,
    "execution_time": 12.5,
    "timestamp": "2026-04-26T10:00:00",
    "error": null
}
```

错误响应：
```json
{
    "success": false,
    "error": "错误描述",
    "execution_time": 0.5,
    "timestamp": "2026-04-26T10:00:00"
}
```

### 8.7 错误码

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 401 | 认证失败 |
| 404 | 端点不存在 |
| 429 | 请求过多（限流） |
| 500 | 服务器内部错误 |

---

## 九、Memory API

### 9.1 快速开始

```python
from src.agents_v2.memory import (
    UnifiedMemoryManager,
    MemorySystemConfig,
    MemoryType
)

# 创建记忆管理器
memory = UnifiedMemoryManager()

# 初始化会话
memory.init_session(task_id="task_001")

# 存储记忆
await memory.remember(
    key="user_prefers_python",
    value="用户偏好Python编程",
    memory_type=MemoryType.LONG_TERM,
    importance=0.8,
    tags=["preference", "language"]
)

# 搜索记忆
results = await memory.search(
    query="用户偏好什么语言",
    memory_types=[MemoryType.LONG_TERM]
)
```

### 9.2 UnifiedMemoryManager API

```python
from src.agents_v2.memory import UnifiedMemoryManager, MemoryType

# 初始化
memory = UnifiedMemoryManager(config: Optional[MemorySystemConfig] = None)

# 初始化会话
session = memory.init_session(task_id: str, session_id: Optional[str] = None)

# 存储记忆
await memory.remember(
    key: str,
    value: Any,
    memory_type: MemoryType = MemoryType.SHORT_TERM,
    persist: bool = False,
    importance: float = 0.5,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
)

# 检索记忆
results = await memory.recall(
    query: str,
    memory_types: Optional[List[MemoryType]] = None,
    limit: int = 10
)

# 搜索记忆
results = await memory.search(
    query: str,
    memory_types: Optional[List[MemoryType]] = None,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 10
)

# 记录执行情节
episode_id = await memory.record_episode(
    agent_id: str,
    action: str,
    result: Any,
    context_snapshot: Optional[Dict[str, Any]] = None,
    duration_ms: float = 0.0,
    success: bool = True
)

# 获取Agent上下文
context = await memory.get_context_for_agent(
    agent_id: str,
    max_tokens: int = 4096,
    force_retrieve: bool = False
)

# 用户画像
profile = await memory.get_user_profile(user_id: str)
```

### 9.3 MemoryType 枚举

```python
from src.agents_v2.memory import MemoryType

MemoryType.SHORT_TERM      # 短期记忆 (内存, LRU+TTL)
MemoryType.SESSION         # 会话记忆 (跨Agent共享)
MemoryType.LONG_TERM      # 长期记忆 (持久化)
MemoryType.EPISODIC       # 情景记忆 (执行轨迹)
MemoryType.USER_PROFILE   # 用户画像 (关系数据库)
MemoryType.PROCEDURAL      # 程序记忆 (流程)
```

### 9.4 检索引擎 API

```python
from src.agents_v2.memory.retrieval import (
    EnhancedRetrievalEngine,
    RetrievalQuery,
    QueryType,
    RetrievalStrategy
)

# 创建检索引擎
engine = EnhancedRetrievalEngine(
    long_term_memory: LongTermMemory,
    relational_store: Optional[RelationalStorage] = None
)

# 执行检索
query = RetrievalQuery(
    text: str,
    query_type: Optional[QueryType],
    limit: int = 10,
    memory_types: Optional[List[MemoryType]] = None,
    strategy: Optional[RetrievalStrategy] = None,
    filters: Optional[Dict[str, Any]] = None
)

results = await engine.retrieve(query, context=None)
```

#### QueryType 查询类型

```python
QueryType.FACTUAL      # 事实查询 "谁/什么/何时"
QueryType.PROCEDURAL   # 流程查询 "如何做"
QueryType.EXPLANATORY  # 解释查询 "为什么"
QueryType.TEMPORAL     # 时序查询 "之前发生了什么"
QueryType.ENTITY       # 实体查询 "关于X的所有信息"
```

#### RetrievalStrategy 检索策略

```python
RetrievalStrategy.SEMANTIC   # 语义向量搜索
RetrievalStrategy.KEYWORD    # BM25关键词搜索
RetrievalStrategy.HYBRID     # 混合搜索
RetrievalStrategy.GRAPH      # 图关系搜索
RetrievalStrategy.TEMPORAL   # 时序搜索
RetrievalStrategy.DIRECT     # 直接键查找
```

### 9.5 向量嵌入 API

```python
from src.agents_v2.memory import (
    create_embedder,
    OpenAIEmbedder,
    LocalEmbedder,
    EmbeddingConfig
)

# OpenAI嵌入器
embedder = create_embedder(EmbeddingConfig(
    provider="openai",
    model="text-embedding-3-small",
    api_key="your-api-key"
))

# 本地嵌入器
embedder = create_embedder(EmbeddingConfig(
    provider="local",
    model="all-MiniLM-L6-v2"
))

# 生成嵌入
result = await embedder.embed_single("Hello world")
print(f"Dimension: {result.dimension}")
```

### 9.6 数据库存储 API

#### PostgreSQL向量存储

```python
from src.agents_v2.memory import (
    PostgresConnection,
    VectorStorage,
    initialize_postgres_memory
)

# 初始化
vector_storage, relational_storage = await initialize_postgres_memory()

# 添加向量
await vector_storage.add(
    memory_id="key1",
    content="test content",
    embedding=[0.1] * 1536,
    memory_type="test",
    importance=0.8
)

# 搜索相似向量
results = await vector_storage.search(
    query_vector=[0.1] * 1536,
    limit=10,
    min_importance=0.5
)
```

#### Redis缓存

```python
from src.agents_v2.memory import RedisCache

cache = RedisCache(host="localhost", port=6379, db=0)

await cache.set("key1", {"data": "value"}, ttl=3600)
value = await cache.get("key1")

stats = await cache.get_stats()
```

#### Neo4j图存储

```python
from src.agents_v2.memory import Neo4jGraphStore

store = Neo4jGraphStore(uri="bolt://localhost:7687", user="neo4j", password="password")

await store.add_entity(
    entity_id="agent_1",
    entity_type="agent",
    properties={"name": "Topic Agent"}
)

await store.add_relation(
    source_id="agent_1",
    target_id="task_1",
    relation_type="executing"
)

related = await store.find_related_entities("agent_1", depth=2)
```

### 9.7 配置API

```python
from src.agents_v2.memory import MemorySystemConfig, get_memory_config

config = get_memory_config()
config = MemorySystemConfig.from_env()

from src.agents_v2.memory import validate_config
errors = validate_config(config)
```

---

## 十、错误处理

### 10.1 错误类型

```python
from src.agents_v2.unified.error_handler import ErrorType

ErrorType.LLM_FAILURE           # LLM调用失败
ErrorType.PARSING_FAILURE       # JSON解析失败
ErrorType.EXTERNAL_API_FAILURE  # 外部API失败
ErrorType.VALIDATION_FAILURE   # 验证失败
ErrorType.SYSTEM_ERROR         # 系统错误
```

### 10.2 降级处理

```python
from src.agents_v2.unified.error_handler import FallbackHandler

handler = FallbackHandler()
fallback = handler.get_fallback("topic", context, error)
```

---

## 十一、MiniMax中文问题解决方案

### 11.1 问题说明

MiniMax-M2.7模型存在中文编码问题：
- 输入中文 → 模型收到乱码
- 模型生成中文 → 输出乱码
- 英文处理正常

### 11.2 TranslationWrapper

```python
from src.agents_v2.unified import TranslationWrapper

translator = TranslationWrapper()

result = await translator.process_english_first(
    chinese_input="我想写一篇关于深度学习的论文",
    agent=topic_agent,
    translate_output=True
)
```

---

## 十二、测试

### 12.1 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_error_handler.py -v
```

### 12.2 测试覆盖

| 模块 | 测试数 |
|------|--------|
| test_agents.py | 12 |
| test_error_handler.py | 12 |
| test_writing_and_problem_agents.py | 24 |
| test_integration.py | 9 |
| test_cache.py | 14 |
| test_monitoring.py | 17 |
| test_exceptions.py | 11 |
| test_validators.py | 12 |
| test_security_config_alerts.py | 22 |
| test_performance.py | 9 |
| test_memory_extended.py | 23 |
| **总计** | **165** |

---

## 十三、外部API服务集成

### 13.1 Semantic Scholar API

论文搜索增强，支持AI驱动的学术搜索、TLDR摘要、引用图谱。

**申请地址**: https://api.semanticscholar.org/

**环境变量**:
```bash
export SEMANTIC_SCHOLAR_API_KEY=your_api_key
```

**功能**:
- 论文搜索 (`/paper/search`)
- 论文详情 (`/paper/{paperId}`)
- 引用列表 (`/paper/{paperId}/citations`)
- 参考文献 (`/paper/{paperId}/references`)
- 相似论文 (`/paper/{paperId}/similar`)

**速率限制**:
| 级别 | 限制 |
|------|------|
| 免费 | 100请求/5分钟 |
| 付费 | 10000请求/5分钟 |

**使用示例**:
```python
from src.agents_v2.search import SemanticScholarSearcher

searcher = SemanticScholarSearcher()
result = await searcher.search("machine learning", max_results=10)
```

---

### 13.2 OpenAlex API

免费开源的跨学科学术论文API，覆盖2亿+论文。

**申请地址**: https://docs.openalex.org/ (无需API Key)

**环境变量**: 无需配置

**功能**:
- 论文搜索 (`/works`)
- 作者论文 (`/authors/{author_id}/works`)
- 期刊论文 (`/venues`)
- 机构论文 (`/institutions`)

**速率限制**: 10请求/秒

**使用示例**:
```python
from src.agents_v2.search import OpenAlexSearcher

searcher = OpenAlexSearcher()
result = await searcher.search("causal inference", year_filter="2024")
```

---

### 13.3 Trinka AI API

专业学术语法检查API，适用于英文论文润色。

**申请地址**: https://www.trinka.ai/

**环境变量**:
```bash
export TRINKA_API_KEY=your_api_key
```

**功能**:
- 学术语法检查
- 技术术语校验
- 学术写作规范检查
- 多种错误类型识别

**使用示例**:
```python
from src.agents_v2.writing import LanguagePolisherAgent

agent = LanguagePolisherAgent()
result = await agent.execute({
    "text": "Your paper abstract here...",
    "language": "en",
    "polish_level": "medium"
})
```

---

### 13.4 API Key配置汇总

| 服务 | 环境变量 | 必填 | 说明 |
|------|---------|------|------|
| OpenAI | `OPENAI_API_KEY` | 是 | LLM调用 |
| MiniMax | `MINIMAX_API_KEY` | 否 | 备选LLM |
| Semantic Scholar | `SEMANTIC_SCHOLAR_API_KEY` | 否 | 学术搜索增强 |
| Trinka AI | `TRINKA_API_KEY` | 否 | 学术语法检查 |
| arXiv | 无 | 否 | 直接调用 |
| PubMed | 无 | 否 | 直接调用 |
| OpenAlex | 无 | 否 | 免费直接调用 |

**文档版本**: v2.0
**创建日期**: 2026-04-26
**最后更新**: 2026-04-28

---

## 附录：前后端接口对照表


本项目采用 React + Vite 前端与 Python aiohttp 后端架构，通过 RESTful API 进行通信。前端使用 axios 封装请求，后端采用 API Key 认证。

---

## 论文相关接口 (Paper API)

| 前端方法 | 请求方式 | 后端路由 | 功能说明 |
|---------|---------|---------|---------|
| `paperAPI.createPaper` | POST | `/api/papers` | 创建新论文 |
| `paperAPI.uploadPaper` | POST | `/api/papers/upload` | 上传论文文件 (FormData) |
| `paperAPI.getPapers` | GET | `/api/papers` | 获取论文列表 |
| `paperAPI.getPaper` | GET | `/api/papers/{id}` | 获取论文详情 |
| `paperAPI.updatePaper` | PUT | `/api/papers/{id}` | 更新论文 |
| `paperAPI.deletePaper` | DELETE | `/api/papers/{id}` | 删除论文 |
| `paperAPI.getOutline` | GET | `/api/papers/{id}/outline` | 获取论文大纲 |
| `paperAPI.generateOutline` | POST | `/api/papers/{id}/outline/generate` | AI 生成大纲 |
| `paperAPI.generateContent` | POST | `/api/papers/{id}/sections/{sectionId}/generate` | AI 生成章节内容 |

---

## 文献相关接口 (Literature API)

| 前端方法 | 请求方式 | 后端路由 | 功能说明 |
|---------|---------|---------|---------|
| `literatureAPI.search` | POST | `/api/literature/search` | 搜索文献 |
| `literatureAPI.getDetail` | GET | `/api/literature/{id}` | 获取文献详情 |
| `literatureAPI.addToLibrary` | POST | `/api/papers/{paperId}/literature` | 添加到文献库 |
| `literatureAPI.getCitation` | GET | `/api/literature/{id}/citation` | 获取引用格式 |
| `literatureAPI.uploadFile` | POST | `/api/literature/upload` | 上传文献文件 (FormData) |

---

## AI 助手接口 (AI Chat API)

| 前端方法 | 请求方式 | 后端路由 | 功能说明 |
|---------|---------|---------|---------|
| `aiAPI.sendMessage` | POST | `/api/papers/{paperId}/chat` | 发送消息 (非流式) |
| `aiAPI.streamMessage` | GET | `/api/papers/{paperId}/chat/stream` | 流式响应 (SSE) |
| `aiAPI.getChatHistory` | GET | `/api/papers/{paperId}/chat/history` | 获取聊天历史 |

---

## 学术资讯接口 (Reports API)

| 前端方法 | 请求方式 | 后端路由 | 功能说明 |
|---------|---------|---------|---------|
| `reportsAPI.getReports` | GET | `/api/reports` | 获取资讯列表 |
| `reportsAPI.getReport` | GET | `/api/reports/{id}` | 获取资讯详情 |
| `reportsAPI.createReport` | POST | `/api/reports` | 生成新资讯 |
| `reportsAPI.updateReport` | PUT | `/api/reports/{id}` | 更新资讯 |
| `reportsAPI.deleteReport` | DELETE | `/api/reports/{id}` | 删除资讯 |
| `reportsAPI.getDailyReports` | GET | `/api/reports/daily` | 获取日报列表 |
| `reportsAPI.getWeeklyReports` | GET | `/api/reports/weekly` | 获取周报列表 |
| `reportsAPI.getMonthlyReports` | GET | `/api/reports/monthly` | 获取月报列表 |

---

## 知识图谱接口 (Knowledge Graph API)

| 前端方法 | 请求方式 | 后端路由 | 功能说明 |
|---------|---------|---------|---------|
| `knowledgeGraphAPI.getLiteratureGraph` | POST/GET | `/api/knowledge-graph/generate` 或 `/api/knowledge-graph/literature` | 获取文献知识图谱 |
| `knowledgeGraphAPI.generateGraph` | POST | `/api/knowledge-graph/generate` | 显式生成图谱 |
| `knowledgeGraphAPI.getEntityRelations` | GET | `/api/knowledge-graph/entity/{entityId}` | 获取实体关联 |
| `knowledgeGraphAPI.detectCommunities` | GET | `/api/knowledge-graph/communities` | 社区检测 |
| `knowledgeGraphAPI.getCommunityPapers` | GET | `/api/knowledge-graph/communities/{communityId}/papers` | 获取社区内论文 |
| `knowledgeGraphAPI.getCentrality` | GET | `/api/knowledge-graph/centrality` | 节点中心性分析 |
| `knowledgeGraphAPI.findPaths` | GET | `/api/knowledge-graph/paths` | 路径查找 |
| `knowledgeGraphAPI.getNeighbors` | GET | `/api/knowledge-graph/entity/{entityId}/neighbors` | 邻居分析 |

---

## 系统设置接口 (Settings API)

| 前端方法 | 请求方式 | 后端路由 | 功能说明 |
|---------|---------|---------|---------|
| `settingsAPI.getSettings` | GET | `/api/settings` | 获取设置 |
| `settingsAPI.updateSettings` | PUT | `/api/settings` | 更新设置 |

---

## 认证方式

### API Key 认证

所有接口（除流式响应外）通过请求头传递 API Key：

```
x-api-key: {api_key}
```

前端存储于 `localStorage.getItem('api_key')`，默认值 `dev-api-key`

### 流式响应 (SSE)

`streamMessage` 由于 EventSource 限制，API Key 通过 URL query 参数传递：

```
/api/papers/{paperId}/chat/stream?message={message}&api_key={api_key}
```

---

## 请求示例

### 创建论文
```javascript
paperAPI.createPaper({
  title: '论文标题',
  abstract: '摘要内容'
})
```

### 上传论文文件
```javascript
const formData = new FormData()
formData.append('file', file)
paperAPI.uploadPaper(formData)
```

### 生成大纲
```javascript
paperAPI.generateOutline(paperId, '论文主题')
```

### 流式聊天
```javascript
const eventSource = aiAPI.streamMessage(paperId, '你好')
eventSource.onmessage = (event) => {
  console.log(event.data)
}
```

---

## 常见错误码

| HTTP 状态码 | 说明 |
|-------------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 401 | 未授权 (API Key 缺失或无效) |
| 500 | 服务器内部错误 |

---

## 前端 API 封装位置

- **文件**: `frontend/src/services/api.js`
- **导出对象**: `default { paperAPI, literatureAPI, aiAPI, settingsAPI, reportsAPI, knowledgeGraphAPI }`

### 使用示例

```javascript
import { paperAPI, literatureAPI, aiAPI } from '../services/api'

// 创建论文
const result = await paperAPI.createPaper({ title: '新论文' })

// 搜索文献
const results = await literatureAPI.search('深度学习')

// 流式聊天
const eventSource = aiAPI.streamMessage(paperId, message)
```
