 # 论文Agent - 智能论文调研与知识图谱系统

## 项目简介

面向统计领域文献爆发式增长、知识抽取难结构化、人工综述周期长等问题，设计"概念知识图谱系统 + 多智能体论文调研系统"双引擎架构，实现高精度知识构建与自动综述生成。

## 核心功能

### 1. 知识抽取 ✓
- **智能路由**：DeBERTa-v3轻量分类器作为过滤路由，根据文本复杂度自动选择抽取方法
  - 简单文本 → 小模型规则抽取
  - 中等复杂度 → 大模型抽取
  - 高复杂度 → 大模型 + Self-Consistency Decoding
- **结构化抽取**：按概念图谱结构化抽取实体和关系
- **Self-Consistency优化**：通过多次独立抽取投票聚合，提升核心实体/关系纯净度

### 2. 图谱更新 ✓
- **CDC-BERTopic**：主题级检测策略，滑动窗口检测主题演化
- **增量更新**：仅对新主题触发局部重抽，避免全量重计算
- **变化检测**：识别新主题、消失主题和主题漂移

### 3. 多智能体论文调研框架 ✓
基于LangGraph构建五智能体协作流水线：
- **搜索Agent**：论文检索，支持查询澄清和重写
- **阅读Agent**：PDF解析和内容提取
- **分析Agent**：聚类分析、深度分析、全局分析
- **写作Agent**：大纲生成、资料检索、章节撰写
- **报告Agent**：生成最终Markdown报告

### 4. 查询澄清与重写 ✓
- **查询澄清**：
  - 口语术语映射到学术表达
  - 预定义领域术语库（学术、医学等）
  - 识别查询中的歧义并生成澄清建议
- **查询重写**：
  - 同义词替换扩大检索范围
  - 查询扩展添加相关关键词
  - 学术表达转换提高专业性
  - 多维度LLM智能重写

### 5. 记忆管理模块 ✓
- **短期记忆**：存储当前对话的上下文，支持会话管理
- **长期记忆**：结构化存储事实、概念、经验等知识
- **情景记忆**：记录具体的事件和经历
- **对话总结**：自动提炼对话历史中的关键信息
- **记忆检索**：基于语义检索和加权算法

### 6. Graph-First检索增强
- **"先图后向量"的并行RAG策略**
- 先抽取图谱1-hop子图缩小语义空间
- 再扩召向量库上下文
- 答案附来源ID支持可溯源

## 项目结构

```
d:\pycharmprojects\pythonProject1\
├── config/                            # 配置文件目录
│   ├── config.yaml                    # 主配置文件
│   ├── llm_config.yaml                # LLM配置
│   ├── storage_config.yaml            # 存储配置
│   └── agent_config.yaml              # Agent配置
│
├── src/
│   ├── agents/                        # 多智能体系统
│   │   ├── base/                      # Agent基类
│   │   │   └── base_agent.py
│   │   ├── search/                    # 搜索智能体
│   │   │   ├── search_agent.py        # 主搜索Agent
│   │   │   ├── query_clarifier.py     # 查询澄清Agent ✓
│   │   │   └── query_rewriter.py      # 查询重写Agent ✓
│   │   ├── reading/                   # 阅读智能体
│   │   │   └── reading_agent.py
│   │   ├── analysis/                  # 分析智能体
│   │   │   ├── analysis_agent.py
│   │   │   ├── cluster/
│   │   │   │   ├── cluster_agent.py
│   │   │   │   └── topic_modeler.py  # BERTopic主题建模 ✓
│   │   │   ├── deep/
│   │   │   │   └── deep_analysis_agent.py
│   │   │   └── global/
│   │   │       └── global_analysis_agent.py
│   │   ├── writing/                   # 写作智能体
│   │   │   ├── writing_agent.py
│   │   │   ├── director.py            # 导演Agent
│   │   │   ├── writer.py              # 写作Agent
│   │   │   ├── retriever.py           # 检索Agent
│   │   │   └── writing_state.py
│   │   ├── report/                    # 报告智能体
│   │   │   └── report_agent.py
│   │   └── orchestrator.py            # 工作流编排器
│   │
│   ├── knowledge/                     # 知识图谱系统
│   │   ├── extraction/                # 知识抽取模块 ✓
│   │   │   ├── router.py              # 智能路由器
│   │   │   ├── base_extractor.py      # 抽取器基类
│   │   │   ├── llm_extractor.py       # 大模型抽取器
│   │   │   ├── small_model_extractor.py  # 小模型抽取器
│   │   │   ├── self_consistency.py    # Self-Consistency Decoding
│   │   │   ├── entity_extractor.py    # 实体抽取器
│   │   │   └── relation_extractor.py  # 关系抽取器
│   │   ├── concept_graph/             # 概念图谱
│   │   │   ├── concept_graph.py       # 概念图谱主类
│   │   │   ├── concept_node.py        # 概念节点
│   │   │   └── hierarchy_builder.py   # 层次结构构建
│   │   ├── update/                    # 图谱更新模块
│   │   │   ├── topic_detector.py      # CDC-BERTopic主题检测
│   │   │   ├── change_detector.py     # 变更检测
│   │   │   ├── incremental_updater.py # 增量更新
│   │   │   └── graph_merger.py        # 图谱合并
│   │   └── retrieval/                 # 图谱检索模块
│   │       ├── graph_retriever.py     # 图谱检索器
│   │       ├── vector_retriever.py    # 向量检索器
│   │       ├── hybrid_retriever.py    # Graph-First RAG
│   │       ├── parallel_search.py     # 并行搜索
│   │       └── result_fusion.py       # 结果融合
│   │
│   ├── memory/                        # 记忆管理模块 ✓
│   │   ├── short_term_memory.py       # 短期记忆（工作记忆）
│   │   ├── semantic_memory.py         # 长期记忆（语义记忆）
│   │   ├── episodic_memory.py         # 情景记忆
│   │   ├── conversation_summarizer.py # 对话总结
│   │   ├── memory_storage.py          # 记忆持久化
│   │   ├── memory_retriever.py        # 记忆检索
│   │   └── memory_manager.py          # 统一记忆管理器
│   │
│   ├── core/                          # 核心组件
│   │   ├── state_model.py             # 状态模型
│   │   ├── model.py                   # LLM模型封装
│   │   ├── prompt.py                  # 提示词模板
│   │   ├── mcp_tool.py                # MCP工具封装
│   │   ├── config.py                  # 配置加载器
│   │   └── exceptions.py              # 异常定义
│   │
│   ├── services/                      # 服务层
│   │   ├── retrieval_tools.py         # 检索工具
│   │   ├── embedding_service.py       # 嵌入服务
│   │   ├── llm_service.py             # LLM服务
│   │   ├── cache_service.py           # 缓存服务
│   │   └── milvus.py                  # Milvus向量存储
│   │
│   ├── workflows/                     # 工作流定义
│   │   ├── base_workflow.py           # 工作流基类
│   │   ├── paper_workflow.py          # 论文调研工作流
│   │   ├── knowledge_workflow.py      # 知识构建工作流
│   │   ├── dual_engine_workflow.py    # 双引擎协调工作流
│   │   ├── fault_tolerance.py         # 容错机制（错误边界/Fallback/重试）
│   │   ├── multi_path_search.py       # 多路径冗余搜索
│   │   ├── checkpoint_rollback.py     # 状态快照与回滚
│   │   ├── subgraph_isolation.py       # 隔离子图（阅读/写作/搜索）
│   │   ├── research_graph.py          # 容错状态机（整合所有改进）
│   │   └── planner_orchestrator.py    # Planner中枢调度（非线性架构）
│   │
│   └── utils/                         # 工具函数
│       ├── log_utils.py
│       ├── env_utils.py
│       ├── mcp_utils.py
│       ├── text_utils.py
│       ├── date_utils.py
│       └── metrics.py
│
├── models/                            # 模型相关
│   ├── routers/                       # 路由模型
│   │   └── deberta_router.py          # DeBERTa-v3路由器
│   └── extractors/                    # 抽取模型
│
├── data/                              # 数据目录
│   ├── raw/                           # 原始数据
│   ├── processed/                     # 处理后数据
│   ├── graphs/                        # 图谱数据
│   └── memory/                        # 记忆数据
│
├── tests/                             # 测试目录
│   ├── unit/                          # 单元测试
│   ├── integration/                   # 集成测试
│   └── fixtures/                      # 测试夹具
│
├── examples/                          # 示例代码
│   └── memory_example.py
│
├── docs/                              # 文档目录
│   ├── architecture.md                # 架构文档
│   ├── api.md                         # API文档
│   ├── user_guide.md                  # 用户指南
│   ├── memory_usage.md                # 记忆系统使用指南
│   └── implementation_summary.md     # 实现总结
│
├── LightRAG/                          # LightRAG框架
├── paper_for_search/                  # MCP服务器
├── main.py                            # 主入口
├── api.py                             # API服务
├── test.py                            # 测试入口
├── requirements.txt                   # 项目依赖
└── readme.md                          # 项目文档
```

## 技术栈

### 核心框架
- `langgraph>=0.2.0` - 多智能体工作流编排
- `langchain>=0.3.0` - LLM应用框架
- `langchain-openai>=0.2.0` - OpenAI兼容接口
- `langchain-community>=0.3.0` - 社区集成
- `langchain-milvus>=0.1.0` - Milvus向量存储
- `langchain-mcp-adapters>=0.1.0` - MCP适配器

### 知识图谱
- `neo4j>=5.0.0` - 图数据库
- `pymilvus>=2.4.0` - Milvus向量数据库
- `networkx>=3.0` - 图算法

### 机器学习
- `transformers>=4.40.0` - Transformers模型（DeBERTa-v3）
- `torch>=2.3.0` - PyTorch
- `scikit-learn>=1.5.0` - 机器学习工具
- `bertopic>=0.16.0` - 主题建模
- `sentence-transformers>=2.7.0` - 句子嵌入

### 数据处理
- `pandas>=2.0.0` - 数据处理
- `numpy>=1.24.0` - 数值计算
- `pydantic>=2.0.0` - 数据验证

### 文档处理
- `unstructured>=0.15.0` - 文档解析
- `pymupdf>=1.24.0` - PDF处理

### 工具库
- `python-dotenv>=1.0.0` - 环境变量
- `aiohttp>=3.9.0` - 异步HTTP
- `httpx>=0.27.0` - HTTP客户端
- `tenacity>=8.0.0` - 重试机制
- `python-dateutil>=2.8.0` - 日期处理
- `pyyaml>=6.0` - YAML配置

### MCP
- `fastmcp>=0.1.0` - MCP框架
- `arxiv>=2.0.0` - arXiv搜索
- `pubmed-parser>=0.4.0` - PubMed解析
- `scholarly>=1.7.0` - Google Scholar

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建`.env`文件并配置以下变量：

```env
OPEN_API_KEY=your_api_key
MILVUS_URI=your_milvus_uri
COLLECTION_NAME=your_collection_name
NEO4J_PASSWORD=your_neo4j_password
```

### 3. 启动服务

**方式一：命令行模式**
```bash
python main.py
```

**方式二：API服务模式**
```bash
python api.py
```
API文档访问：http://localhost:8000/docs

**方式三：Web界面模式（推荐）**

1. 启动后端API服务：
```bash
python api.py
```

2. 启动Web界面（新开终端）：
```bash
# Windows
run_web.bat

# Linux/Mac
./run_web.sh

# 或直接运行
streamlit run app.py
```

Web界面将在浏览器自动打开：http://localhost:8501

详细使用说明请参考：[Web界面使用说明](docs/Web界面使用说明.md)

## 使用示例

### 论文调研工作流

```python
from src.workflows.paper_workflow import PaperWorkflow
from src.core.state_model import State, paperagentstate, SearchAgent
import asyncio

async def main():
    workflow = PaperWorkflow()

    initial_state = State(
        value=paperagentstate(
            current_step="initializing",
            search_state=SearchAgent(query="函数型数据分析")
        )
    )

    result = await workflow.run(initial_state)
    print(result["value"].report_markdown)

asyncio.run(main())
```

### 记忆系统使用

```python
from src.memory import UnifiedMemoryManager
import asyncio

async def main():
    # 初始化记忆管理器
    memory_manager = UnifiedMemoryManager()

    # 创建会话
    session_id = "user_session_001"
    memory_manager.create_session(session_id)

    # 添加对话
    memory_manager.add_message(
        session_id,
        "user",
        "我想学习深度学习"
    )

    # 添加长期记忆
    memory_manager.add_fact(
        "深度学习是机器学习的一个分支",
        importance=0.9
    )

    # 检索记忆
    results = await memory_manager.retrieve("深度学习", session_id=session_id)

    # 保存并关闭
    memory_manager.close_session(session_id, save=True)

asyncio.run(main())
```

更多示例请查看 [examples/](examples/) 和 [docs/](docs/)。

### API调用

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "函数型数据分析",
    "max_results": 20
  }'
```

## 开发计划

### 阶段1：基础重构 ✓
- [x] 创建新的目录结构
- [x] 重构Agent目录结构
- [x] 建立统一的配置系统
- [x] 添加基础测试框架

### 阶段2：知识图谱系统 ✓
- [x] 实现DeBERTa-v3路由器
- [x] 实现概念图谱构建
- [x] 实现知识抽取模块
- [x] 集成BERTopic主题建模

### 阶段3：检索增强
- [x] 实现Graph-First RAG框架
- [ ] 实现并行搜索
- [ ] 实现结果融合
- [ ] 集成到工作流

### 阶段4：查询澄清与记忆 ✓
- [x] 实现查询澄清Agent
- [x] 实现查询重写Agent
- [x] 实现记忆管理模块
- [ ] 集成到搜索Agent

### 阶段5：双引擎协调 ✓
- [x] 实现双引擎协调工作流框架
- [ ] 扩展状态模型
- [ ] 端到端测试
- [ ] 性能优化

### 阶段6：容错架构（新增）✓
- [x] 实现错误边界 + Fallback机制
- [x] 实现多路径冗余搜索
- [x] 实现状态快照 + 回滚机制
- [x] 实现隔离子图（阅读/写作）
- [x] 重构主状态机整合所有容错机制

## 文档

- [论文Agent计划书](docs/论文Agent计划书.md) - 项目完整计划与架构设计
- [Web界面使用说明](docs/Web界面使用说明.md) - Web界面使用指南
- [架构文档](docs/architecture.md) - 系统架构设计
- [容错架构改进记录](docs/容错架构改进记录.md) - 容错机制详细说明（新增）
- [API文档](docs/api.md) - API接口说明
- [用户指南](docs/user_guide.md) - 用户使用指南
- [记忆系统使用指南](docs/memory_usage.md) - 记忆模块详细说明
- [实现总结](docs/implementation_summary.md) - 实现进度总结

## 贡献指南

欢迎提交Issue和Pull Request！

### 开发流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

MIT License
