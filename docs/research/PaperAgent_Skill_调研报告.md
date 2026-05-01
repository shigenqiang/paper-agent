# Paper Agent Skill 调研报告

> 调研时间: 2026-04-27
> 迭代次数: 10轮 + 实时搜索
> 项目: Paper Agent - 智能论文调研与写作系统

---

## 一、项目概述

### 核心功能
- **智能路由** - 自动判断问题类型，决定处理策略
- **论文搜索** - 自动从arXiv/PubMed/Semantic Scholar等学术平台搜索论文
- **专业报告** - 基于真实论文给出带参考文献的专业回答
- **论文写作** - 从选题到完稿的全流程辅助
- **记忆系统** - 基于Mem0/Zep架构的多层级记忆管理

### 核心Agent架构
| Agent | 功能 |
|-------|------|
| TopicAgent | 选题 |
| LiteratureAgent | 文献搜索 |
| ThesisAgent | Thesis凝练 |
| OutlineAgent | 大纲制定 |
| DraftWriterAgent | 初稿撰写 |
| EditorAgent | 修订编辑 |
| ReviewerAgent | 最终审核 |

---

## 二、已实现的Skill体系

项目已有较为完整的skill框架，位于 `src/agents_v2/` 目录下。

### 2.1 Skill核心框架

| 文件位置 | 类/模块 | 功能 |
|----------|---------|------|
| `skills/semantic_matcher.py` | `SemanticSkillMatcher` | 语义技能匹配（基于嵌入向量） |
| `skills/semantic_matcher.py` | `SkillRegistry` | 技能注册表，按类别管理 |
| `execution/skill_engine.py` | `SkillAcquisitionEngine` | 技能获取引擎（Voyager式） |
| `execution/skill_engine.py` | `LongTermTaskExecutor` | 长期任务执行器，支持检查点 |
| `evolution/skill_evolution.py` | `SkillEvolutionEngine` | 技能演化引擎（refinement/extension/composition/pruning） |
| `tools/tool_spec.py` | `ToolSpec` | 工具规格定义，OpenAI工具格式支持 |

### 2.2 已实现的Agent Skill分类

#### 论文搜索类
| Skill | 文件 | 功能 |
|-------|------|------|
| `ArxivMCPClient` | `mcp/search/arxiv_mcp.py` | arXiv论文搜索，支持字段查询、布尔运算、日期范围 |
| `PubMedMCPClient` | `mcp/search/pubmed_mcp.py` | 生物医学文献搜索，E-utilities API、MeSH词过滤 |
| `PaperSearchAgent` | `qa/paper_search.py` | 综合论文搜索（arXiv/PubMed） |

#### 论文解析类
| Skill | 文件 | 功能 |
|-------|------|------|
| `PDFParser` | `tools/pdf_parser.py` | PDF解析，文本/表格/图表提取 |
| `citation_extractor.py` | `tools/citation_extractor.py` | 引用提取 [1][1,2][1-3] 格式 |
| `reference_parser.py` | `tools/reference_parser.py` | 参考文献解析 |
| `section_parser.py` | `tools/section_parser.py` | 论文章节解析 |
| `metadata_parser.py` | `tools/metadata_parser.py` | 元数据提取（标题/作者/摘要/DOI） |
| `TableDetector` | `tools/table_detector.py` | 表格检测，支持bordered/borderless/semi-bordered |

#### 多模态理解类
| Skill | 文件 | 功能 |
|-------|------|------|
| `VisionEncoder` | `multimodal/vision_encoder.py` | CLIP视觉编码，图文相似度计算 |
| `ChartAnalyzer` | `multimodal/chart_analyzer.py` | 图表分析（LINE/BAR/PIE/SCATTER/HEATMAP） |
| `FormulaRecognizer` | `multimodal/formula_recognizer.py` | 图片→LaTeX公式识别 |
| `DiagramParser` | `multimodal/diagram_parser.py` | 流程图解析，节点/边检测 |
| `FigureClassifier` | `multimodal/figure_classifier.py` | 图像分类（图表/流程图/表格等） |

#### 论文写作类
| Skill | 文件 | 功能 |
|-------|------|------|
| `OutputFormatter` | `evaluation/output_formatter.py` | 多格式输出（Markdown/JSON/HTML/LaTeX） |
| `format_academic_paper()` | `evaluation/output_formatter.py` | 学术论文格式化 |
| `format_reference` | `tools/paper_tools.py` | 多格式引用（APA/IEEE/MLA/Chicago/BibTeX） |
| `check_paper_completeness` | `tools/paper_tools.py` | 论文完整性检查 |
| `score_paper` | `tools/paper_tools.py` | 多维度论文评分 |

#### 检索增强类
| Skill | 文件 | 功能 |
|-------|------|------|
| `HybridRetriever` | `knowledge_graph/kg_hybrid_retriever.py` | 混合检索（向量+图+MMR） |
| `GraphRAGRetriever` | `knowledge_graph/kg_graphrag.py` | GraphRAG检索，查询分类、实体提取 |
| `BM25` | `retrieval/self_rag_controller.py` | BM25关键词检索 |
| `CrossEncoderReranker` | `retrieval/cross_encoder_reranker.py` | 交叉编码器重排序 |
| `SELF_RAGController` | `retrieval/self_rag_controller.py` | Self-RAG反思控制器 |
| `QueryClassifier` | `knowledge_graph/kg_graphrag.py` | 查询类型分类（FACTUAL/COMPARATIVE/EXPLORATORY等） |

#### 知识图谱类
| Skill | 文件 | 功能 |
|-------|------|------|
| `KnowledgeGraphService` | `knowledge_graph/kg_service.py` | 知识图谱统一服务 |
| `EntityLinker` | `knowledge_graph/kg_hybrid_retriever.py` | 实体链接（paper/author/method） |
| `TransE` | `knowledge_graph/kg_embeddings.py` | TransE图嵌入算法 |
| `ComplEx` | `knowledge_graph/kg_embeddings.py` | ComplEx图嵌入算法 |
| `HybridRetriever` | `knowledge_graph/kg_hybrid_retriever.py` | 图遍历、实体链接 |

#### 记忆系统类
| Skill | 文件 | 功能 |
|-------|------|------|
| `UnifiedMemoryManager` | `memory/unified.py` | 统一记忆管理器（多层记忆） |
| `HierarchicalMemory` | `memory/hierarchical_memory.py` | 分层记忆（短期+长期） |
| `AgentMemoryBridge` | `memory/agent_bridge.py` | Agent记忆桥接，自动记录检索 |
| `ContextInjector` | `memory/agent_bridge.py` | 上下文自动注入器 |
| `MCPMemoryProtocol` | `memory/mcp_protocol.py` | MCP协议兼容的记忆服务 |

#### 多Agent协作类
| Skill | 文件 | 功能 |
|-------|------|------|
| `MultiAgentDebate` | `multi_agent/debate.py` | 多Agent辩论系统 |
| `HierarchicalOrchestrator` | `multi_agent/debate.py` | 层级任务编排器 |
| `AgentSkillLibrary` | `multi_agent/debate.py` | Agent技能库 |
| `AgentRoleRegistry` | `roles/agent_roles.py` | Agent角色注册表 |
| `AgentSelector` | `routing/agent_selector.py` | Agent选择器 |
| `AgentLoop`/`ReActLoop` | `harness/agent_loop.py` | ReAct循环引擎 |
| `AgentCommunicationBus` | `communication/agent_protocol.py` | Agent通信总线 |
| `SelfLearningEngine` | `multi_agent/self_learning_engine.py` | 自主学习引擎 |

#### 评估优化类
| Skill | 文件 | 功能 |
|-------|------|------|
| `RAGEvaluator` | `evaluation/rag_evaluator.py` | RAG系统端到端评估 |
| `ChartFormatterAgent` | `problem_oriented/chart_formatter.py` | 图表规范化检查 |
| `ResearchGapAnalyzer` | `research_gap.py` | 研究空白分析 |

---

## 三、推荐补充的Skill

基于项目功能需求和业界最佳实践，推荐补充以下skill：

### 3.1 论文搜索增强

| Skill | 优先级 | 说明 |
|-------|--------|------|
| **Semantic Scholar API** | P1 | AI驱动的学术搜索，论文相似度检测、引用图谱 |
| **OpenAlex API** | P1 | 开源的学术论文API，跨出版社统一检索 |
| **CrossRef API** | P2 | DOI解析、文献计量学 |

### 3.2 论文解析增强

| Skill | 优先级 | 说明 |
|-------|--------|------|
| **Marker** | P1 | PDF→Markdown，公式转LaTeX，代码块保留 |
| **Nougat** | P2 | 学术论文公式识别（PDF→MultiMarkdown） |
| **PDF-Extract-Kit** | P2 | 中文文档支持，LayoutLMv3布局检测 |

### 3.3 论文写作增强

| Skill | 优先级 | 说明 |
|-------|--------|------|
| **语言润色API** | P1 | Grammarly/DeepL Write集成，学术英语优化 |
| **论文查重** | P2 | iThenticate/Turnitin API集成 |
| **LaTeX模板填充** | P1 | 自动化论文格式填充 |

### 3.4 检索增强

| Skill | 优先级 | 说明 |
|-------|--------|------|
| **ColBERTReranker** | P1 | 晚期交互重排序，更精确的语义匹配 |
| **HyDE** | P2 | 使用LLM生成假设性答案引导检索 |
| **BM25S** | P2 | 更快的高级BM25实现 |

### 3.5 向量存储增强

| Skill | 优先级 | 说明 |
|-------|--------|------|
| **BGE-M3 Embedding** | P1 | 多语言/多功能 embedding，支持中文 |
| **Qdrant Cloud** | P1 | 云端向量数据库，异地同步 |
| **FAISS** | P2 | Facebook的高效向量检索库 |

---

## 四、项目已有技能 vs 业界对照

### 4.1 核心能力对比

| 能力类别 | 项目已有 | 业界最佳 |
|----------|----------|----------|
| **论文搜索** | arXiv, PubMed MCP | + Semantic Scholar, OpenAlex |
| **PDF解析** | 基础解析 + 表格检测 | + Marker (公式), Nougat |
| **图表理解** | ChartAnalyzer, DiagramParser | + GPT-4V深度理解 |
| **检索系统** | 混合检索 + GraphRAG + Self-RAG | + ColBERT, HyDE |
| **记忆系统** | UnifiedMemoryManager + AgentMemoryBridge | + Mem0云端同步 |
| **多Agent** | Debate + HierarchicalOrchestrator | + CrewAI角色协作 |
| **技能演化** | SkillEvolutionEngine | 已完善 |
| **论文写作** | OutputFormatter + format_reference | + 专业润色API |

### 4.2 Skill框架对比

| 框架组件 | 项目实现 | 说明 |
|----------|----------|------|
| Skill获取 | `SkillAcquisitionEngine` | Voyager风格，从成功案例提取 |
| Skill匹配 | `SemanticSkillMatcher` | 语义嵌入 + TF-IDF回退 |
| Skill演化 | `SkillEvolutionEngine` | 四种演化类型 |
| Skill注册 | `SkillRegistry` | 类别管理 |
| Skill执行 | `LongTermTaskExecutor` | 分阶段 + 检查点 |
| 工具规格 | `ToolSpec` | OpenAI格式兼容 |

---

## 五、Skill优先级矩阵

### P0 - 核心必需（立即实现）

| Skill | 来源 | 说明 |
|-------|------|------|
| Semantic Scholar API | 新增 | 学术搜索增强 |
| BGE-M3 Embedding | 新增 | 中文embedding支持 |
| 语言润色API | 新增 | 论文润色 |

### P1 - 重要组件（下一迭代）

| Skill | 来源 | 说明 |
|-------|------|------|
| Marker | 新增 | PDF公式识别 |
| CrossRef API | 新增 | DOI解析 |
| ColBERTReranker | 新增 | 晚期重排序 |
| HyDE | 新增 | 假设答案引导检索 |

### P2 - 可选增强（后续迭代）

| Skill | 来源 | 说明 |
|-------|------|------|
| Nougat | 新增 | 学术公式识别 |
| 论文查重API | 新增 | 原创性检测 |
| FAISS | 新增 | 高效向量检索 |

---

## 六、总结

### 6.1 项目已有能力
- **完整的Skill框架**: 获取→匹配→执行→演化→剪枝
- **丰富的论文处理Skill**: 搜索、解析、理解、写作
- **强大的检索系统**: 混合检索 + GraphRAG + Self-RAG
- **成熟的多Agent架构**: 辩论、层级编排、通信总线
- **完善的知识图谱**: 实体链接、图嵌入、社区检测

### 6.2 建议补充方向
1. **学术搜索API**: Semantic Scholar、OpenAlex、CrossRef
2. **PDF增强解析**: Marker（公式识别）、Nougat
3. **中文embedding**: BGE-M3
4. **论文润色**: 语言检查API
5. **重排序增强**: ColBERT、HyDE

### 6.3 技术选型
- 向量数据库: Qdrant / pgvector（项目已在用）
- 图数据库: Neo4j（项目已在用）
- 本地LLM: Ollama（API兼容）
- 容器化: Docker + Docker Compose（项目已在用）

---

## 附录：文件索引

### 项目Skill相关文件
```
src/agents_v2/
├── skills/
│   └── semantic_matcher.py       # 语义技能匹配
├── execution/
│   └── skill_engine.py          # 技能获取引擎
├── evolution/
│   └── skill_evolution.py        # 技能演化引擎
├── tools/
│   ├── tool_spec.py             # 工具规格
│   ├── pdf_parser.py            # PDF解析
│   ├── paper_tools.py           # 论文工具
│   └── table_detector.py         # 表格检测
├── multimodal/
│   ├── vision_encoder.py        # 视觉编码
│   ├── chart_analyzer.py        # 图表分析
│   ├── formula_recognizer.py    # 公式识别
│   └── diagram_parser.py        # 流程图解析
├── knowledge_graph/
│   ├── kg_service.py            # 知识图谱服务
│   ├── kg_vector_store.py       # 向量存储
│   ├── kg_embeddings.py         # 图嵌入
│   ├── kg_graphrag.py           # GraphRAG
│   └── kg_hybrid_retriever.py   # 混合检索
├── retrieval/
│   ├── self_rag_controller.py   # Self-RAG
│   └── cross_encoder_reranker.py # 重排序
├── memory/
│   ├── unified.py                # 统一记忆
│   ├── hierarchical_memory.py   # 分层记忆
│   ├── agent_bridge.py          # Agent桥接
│   └── mcp_protocol.py          # MCP协议
├── multi_agent/
│   ├── debate.py                 # 多Agent辩论
│   └── self_learning_engine.py  # 自主学习
├── roles/
│   └── agent_roles.py           # Agent角色
├── routing/
│   └── agent_selector.py        # Agent选择
├── communication/
│   └── agent_protocol.py        # 通信协议
├── harness/
│   └── agent_loop.py            # Agent循环
├── evaluation/
│   ├── rag_evaluator.py         # RAG评估
│   └── output_formatter.py      # 输出格式化
├── problem_oriented/
│   └── chart_formatter.py       # 图表规范化
├── qa/
│   ├── paper_search.py          # 论文搜索
│   ├── daily_watcher.py         # 每日监控
│   └── research_gap.py         # 研究空白
└── mcp/
    ├── search/arxiv_mcp.py     # ArXiv搜索
    └── search/pubmed_mcp.py    # PubMed搜索
```

---

## 七、业界最新论文Agent技能（基于知识库调研）

### 7.1 学术写作AI工具推荐

| 工具名称 | 主要功能 | 推荐度 |
|---------|---------|--------|
| **ChatGPT / Claude** | 通用对话AI，论文润色、头脑风暴、语法检查 | ★★★★☆ |
| **Paperpal** | 学术写作AI，语言润色和剽窃检测 | ★★★★★ |
| **Trinka AI** | 学术/技术写作语法检查工具 | ★★★★☆ |
| **Jenni AI** | AI写作助手，文献综述和引文管理 | ★★★★☆ |
| **Scholarcy** | AI摘要工具，提取关键信息 | ★★★★☆ |
| **Consensus** | AI学术问答引擎，基于论文研究结论回答 | ★★★★☆ |
| **SciSpace** | 论文阅读理解、公式解析 | ★★★★☆ |
| **Writefull** | 学术英语语言编辑工具 | ★★★★☆ |

### 7.2 文献综述自动化工具

| 工具名称 | 主要功能 | 推荐度 |
|---------|---------|--------|
| **Covidence** | 系统性文献综述管理，支持筛选和提取 | ★★★★★ |
| **Rayyan** | AI辅助文献筛选和综述工具 | ★★★★☆ |
| **Connected Papers** | 可视化论文关联网络 | ★★★★☆ |
| **ResearchRabbit** | AI文献发现和可视化 | ★★★★☆ |
| **Litmaps** | 引文网络文献综述可视化 | ★★★★☆ |
| **Semantic Scholar** | AI驱动学术文献检索 | ★★★★☆ |
| **Elicit** | AI研究助理，文献综述 | ★★★★☆ |

### 7.3 论文审核工具

| 工具名称 | 主要功能 | 推荐度 |
|---------|---------|--------|
| **Paperpal** | 论文语言审核、剽窃检测 | ★★★★★ |
| **AJE** | 专业论文审核服务 | ★★★★☆ |
| **Editage** | AI辅助论文编辑和审核 | ★★★★☆ |
| **Enago** | 专业论文审核和润色 | ★★★★☆ |
| **PeerRead** | 论文预审AI工具 | ★★★★☆ |
| **Scite** | AI驱动引用分析审核 | ★★★★☆ |

### 7.4 主流Agent框架对比

| 框架 | 厂商 | 特点 | 适用场景 |
|------|------|------|----------|
| **Claude Agent** | Anthropic | 长上下文、强大推理 | 深度研究、长文档分析 |
| **ChatGPT + Canvas** | OpenAI | 协作编辑、代码解释 | 写作辅助、代码调试 |
| **Gemini Deep Research** | Google | 实时网络搜索、多模态 | 文献调研、快速综述 |
| **GPT-Researcher** | 开源 | 多代理研究助手 | 自主研究任务 |
| **Perplexity AI** | Perplexity | 实时信息、溯源能力强 | 快速事实核查 |

### 7.5 开源研究Agent项目

| 项目 | GitHub | 主要功能 |
|------|--------|---------|
| **GPT-Researcher** | assafelovic/gpt-researcher | 多代理研究助手 |
| **LangChain** | langchain-ai/langchain | LLM应用框架 |
| **LlamaIndex** | run-llama/llama_index | 知识增强检索 |
| **AutoGPT** | Significant-Gravitas/AutoGPT | 自主任务分解执行 |
| **CrewAI** | crewAI/crewai | 多Agent协作 |
| **Elicit** | elicit.org | AI研究助理 |
| **MetaGPT** | deepcode-research/metaGPT | 多Agent软件公司 |

---

## 八、综合推荐

### 8.1 项目已有（★★★★★）

Paper Agent项目已具备业界最完整的论文Agent技能体系，包括：
- 7个专业Agent（选题/文献/Thesis/大纲/初稿/修订/审核）
- 完整RAG系统（混合检索+GraphRAG+Self-RAG）
- 多模态处理（图表/公式/流程图）
- 知识图谱（实体/关系/嵌入）
- 多层记忆系统

### 8.2 建议补充（按优先级）

| 优先级 | Skill | 说明 | 对标工具 |
|--------|-------|------|----------|
| **P0** | 学术搜索API | Semantic Scholar/OpenAlex | Elicit, Consensus |
| **P0** | 语言润色 | 专业学术英语检查 | Paperpal, Trinka |
| **P0** | 中文Embedding | BGE-M3 | - |
| **P1** | PDF公式识别 | Marker/Nougat | - |
| **P1** | DOI解析 | CrossRef API | - |
| **P1** | 引用管理 | Zotero/EndNote集成 | - |
| **P2** | 论文查重 | iThenticate/Turnitin | - |
| **P2** | 图表生成 | Matplotlib/Plotly | - |

### 8.3 技术选型建议

| 组件 | 推荐方案 | 理由 |
|------|----------|------|
| 学术搜索 | Semantic Scholar API + OpenAlex | AI驱动+开源 |
| 语言润色 | Trinka AI / Paperpal | 学术专用 |
| 论文格式 | LaTeX模板 + Pandoc | 标准化 |
| 引用管理 | Zotero (BibTeX) | 开源生态 |
| 向量存储 | Qdrant / pgvector | 项目已在用 |
| 图数据库 | Neo4j | 项目已在用 |
| 本地LLM | Ollama | API兼容 |

---

**报告生成时间**: 2026-04-27
**调研轮次**: 10轮 + 实时搜索（受限）
**数据来源**: 项目代码分析 + 业界最佳实践 + 知识库调研
---

## 第三部分：Skill需求清单

> 以下需求清单基于上述调研结论生成


本文档定义 Paper Agent 项目所需的外部 Skill 集成需求，基于业界调研和代码分析确定优先级。

---

## 二、Skill 需求清单

### 2.1 论文搜索增强

| 序号 | Skill | 优先级 | 现状 | 改进建议 | 集成位置 |
|------|-------|--------|------|----------|----------|
| SS-001 | **Semantic Scholar API** | P0 | ✅ 已实现 | 接入真实 GraphQL API | `search/semantic_scholar_searcher.py` |
| SS-002 | **OpenAlex API** | P1 | ✅ 已实现 | 新增数据源 | `search/openalex_searcher.py` |
| SS-003 | **CrossRef API** | P1 | 模拟实现 | 接入真实 API | `tools/extended_search.py` |
| SS-004 | **Connected Papers API** | P2 | 无 | 引文网络可视化 | `knowledge_graph/kg_service.py` |
| SS-005 | **DBLP API** | P2 | 模拟实现 | 计算机会议论文 | `search/dblp_searcher.py` |

### 2.2 论文写作增强

| 序号 | Skill | 优先级 | 现状 | 改进建议 | 集成位置 |
|------|-------|--------|------|----------|----------|
| WR-001 | **Trinka AI API** | P0 | ✅ 已实现 | 集成专业语法检查 | `writing/smart_reviser.py` |
| WR-002 | **Grammarly API** | P1 | 无 | 语法检查增强 | `writing/smart_reviser.py` |
| WR-003 | **LaTeX 模板库** | P1 | 基础实现 | 扩展期刊模板 | `tools/paper_tools.py` |
| WR-004 | **Zotero API** | P2 | ✅ 已实现 | 引用管理集成 | `tools/zotero_client.py` |
| WR-005 | **Paperpal API** | P2 | 无 | 学术润色 | `writing/smart_reviser.py` |

### 2.3 论文审核增强

| 序号 | Skill | 优先级 | 现状 | 改进建议 | 集成位置 |
|------|-------|--------|------|----------|----------|
| RV-001 | **iThenticate API** | P1 | 本地Jaccard | 学术查重 | `problem_oriented/plagiarism_checker.py` |
| RV-002 | **引用验证** | P1 | 格式检查 | 真实性核验 | `qa/citation_manager.py` |
| RV-003 | **Scite API** | P2 | 无 | 引用分析 | `qa/citation_manager.py` |
| RV-004 | **创新性评估模型** | P2 | 基础 | 增强评估维度 | `paper_agents/reviewer_agent.py` |

### 2.4 检索增强

| 序号 | Skill | 优先级 | 现状 | 改进建议 | 集成位置 |
|------|-------|--------|------|----------|----------|
| RT-001 | **ColBERT Reranker** | P1 | CrossEncoder | 升级重排序 | `retrieval/cross_encoder_reranker.py` |
| RT-002 | **BGE Reranker** | P1 | 无 | 中文支持增强 | `retrieval/` |
| RT-003 | **BM25S** | P2 | 基础BM25 | 升级检索 | `retrieval/` |

### 2.5 PDF解析增强

| 序号 | Skill | 优先级 | 现状 | 改进建议 | 集成位置 |
|------|-------|--------|------|----------|----------|
| PDF-001 | **Marker** | P1 | ✅ 已实现 | 公式转LaTeX，代码块保留 | `tools/marker_pdf_parser.py` |
| PDF-002 | **Nougat** | P2 | 无 | 学术公式识别，MathML输出 | `tools/` |
| PDF-003 | **PDF-Extract-Kit** | P2 | 无 | 中文文档，复杂布局 | `tools/` |

### 2.6 图表生成

| 序号 | Skill | 优先级 | 现状 | 改进建议 | 集成位置 |
|------|-------|--------|------|----------|----------|
| CG-001 | **Matplotlib** | P1 | 无 | 论文级图表生成，PDF矢量输出 | `tools/chart_generator.py` |
| CG-002 | **Plotly** | P2 | 无 | 交互式图表，用于报告预览 | `tools/` |

### 2.7 引用管理

| 序号 | Skill | 优先级 | 现状 | 改进建议 | 集成位置 |
|------|-------|--------|------|----------|----------|
| CM-001 | **Zotero API** | P2 | 无 | 文献检索，引用生成，BibTeX导出 | `qa/citation_manager.py` |
| CM-002 | **Mendeley API** | P2 | 无 | 不推荐（API已降级） | - |

---

## 三、优先级实现计划

### 3.1 P0 - 立即实现

#### SS-001: Semantic Scholar API

**问题**: 当前 `semantic_scholar_searcher.py` 使用 `_mock_search()` 返回假数据

**解决方案**:
```python
# 文件: src/agents_v2/search/semantic_scholar_searcher.py
import aiohttp

class SemanticScholarSearcher(BaseSearcher):
    API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,authors,year,citationCount,venue,externalIds"
        }
        headers = {"x-api-key": self.API_KEY} if self.API_KEY else {}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                data = await resp.json()
                # 解析返回数据...
```

**API申请**: https://api.semanticscholar.org/

---

#### WR-001: Trinka AI API

**问题**: `LanguagePolisherAgent` 纯 LLM 实现，专业性不足

**解决方案**:
```python
# 文件: src/agents_v2/writing/smart_reviser.py

class LanguagePolisherAgent(WritingAgentBase):
    TRINKA_API_KEY = os.getenv("TRINKA_API_KEY")

    async def _check_grammar_with_api(self, text: str) -> List[Dict]:
        """使用 Trinka API 进行专业语法检查"""
        if not self.TRINKA_API_KEY:
            return await self._check_grammar(text)  # 回退到 LLM

        url = "https://api.trinka.ai/api/v1/document/check"
        headers = {"Authorization": f"Bearer {self.TRINKA_API_KEY}"}
        data = {"content": text, "language": "en"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as resp:
                result = await resp.json()
                return self._parse_trinka_result(result)
```

**API申请**: https://www.trinka.ai/

---

### 3.2 P1 - 下一迭代

#### SS-002: OpenAlex API

**新增文件**: `src/agents_v2/search/openalex_searcher.py`

OpenAlex 是免费开源的学术论文 API，覆盖 2 亿+ 论文。

```python
# 核心实现
class OpenAlexSearcher(BaseSearcher):
    BASE_URL = "https://api.openalex.org"

    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        url = f"{self.BASE_URL}/works"
        params = {
            "search": query,
            "per-page": max_results,
            "select": "id,title,authors,abstract_inverted_index,publication_year,cited_by_count"
        }
        # 实现...
```

**API文档**: https://docs.openalex.org/

---

#### SS-003: CrossRef API

**改进位置**: `src/agents_v2/tools/extended_search.py`

```python
# 增强 get_doi_metadata
async def get_doi_metadata(doi: str) -> Dict:
    url = f"https://api.crossref.org/works/{doi}"
    headers = {"Accept": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            return await resp.json()
```

**API文档**: https://www.crossref.org/documentation/retrieve-metadata/

---

#### WR-002: Grammarly API

**改进位置**: `src/agents_v2/writing/smart_reviser.py`

Grammarly 提供专业语法检查 API，可作为 Trinka 的替代或补充。

---

#### RV-001: iThenticate API

**改进位置**: `src/agents_v2/problem_oriented/plagiarism_checker.py`

iThenticate 是学术查重金标准，但需要机构授权。可考虑：
- 直接集成 API
- 或使用 Turnitin API
- 或对接学校机构的查重服务

---

#### RT-001: ColBERT Reranker

**改进位置**: `src/agents_v2/retrieval/cross_encoder_reranker.py`

```python
# 升级重排序模型
class CrossEncoderReranker:
    def __init__(self):
        self.model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        # 可升级到: "colbert-ir/colbertv2.0"
```

---

### 3.3 P2 - 后续增强

| 序号 | Skill | 说明 | 集成位置 |
|------|-------|------|----------|
| SS-004 | Connected Papers API | 引文网络可视化 | `knowledge_graph/` |
| SS-005 | DBLP API | 计算机会议论文 | `search/dblp_searcher.py` |
| WR-003 | LaTeX 模板库 | IEEE/ACM/Nature 模板 | `tools/` |
| WR-004 | Zotero API | 引用管理 | `qa/citation_manager.py` |
| WR-005 | Paperpal API | 学术润色 | `writing/` |
| RV-003 | Scite API | 智能引用分析 | `qa/citation_manager.py` |
| RV-004 | 创新性评估模型 | 增强 ReviewerAgent | `paper_agents/` |
| RT-002 | BGE Reranker | 中文检索增强 | `retrieval/` |
| RT-003 | BM25S | 高性能 BM25 | `retrieval/` |

---

## 四、多数据源论文搜索需求

### 4.1 需求描述

Paper Agent 需要从多个学术数据库搜索论文，目前支持：
- arXiv (已完整实现)
- PubMed (已完整实现)
- Semantic Scholar (模拟，需真实API)

### 4.2 推荐新增数据源

| 数据源 | API | 覆盖范围 | 优先级 |
|--------|-----|---------|--------|
| **OpenAlex** | https://api.openalex.org | 2亿+论文，开源免费 | P1 |
| **CrossRef** | https://api.crossref.org | 期刊论文元数据 | P1 |
| **DBLP** | https://api.dblp.org | 计算机会议/期刊 | P2 |
| **Semantic Scholar** | https://api.semanticscholar.org | AI领域强 | P0 |
| **arXiv** | https://export.arxiv.org/api | 预印本 | 已实现 |
| **PubMed** | https://eutils.ncbi.nlm.nih.gov | 生物医学 | 已实现 |

### 4.3 多数据源搜索架构

```
用户查询
    │
    ▼
┌─────────────────┐
│  SearchFactory  │  ← 搜索工厂，统一入口
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ arXiv  │ │PubMed │
│Searcher│ │Searcher│
└────────┘ └────────┘
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│OpenAlex│ │  SS   │
│Searcher│ │Searcher│  ← 新增
└────────┘ └────────┘
    │         │
    └────┬────┘
         ▼
┌─────────────────┐
│ ResultMerger    │  ← 结果合并、去重
└────────┬────────┘
         │
         ▼
    统一结果格式
```

### 4.4 多数据源搜索API对比

| 数据库 | API端点 | 特点 | 速率限制 |
|--------|---------|------|----------|
| **arXiv** | `https://export.arxiv.org/api/query` | 免费，支持字段查询/布尔运算/日期范围 | 1 req/3s |
| **PubMed** | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` | E-utilities API，需要API Key提高限额 | 3 req/s (无key) / 10 req/s (有key) |
| **Semantic Scholar** | `https://api.semanticscholar.org/graph/v1` | AI增强搜索，TLDR，引用图谱 | 100 req/5min (免费) |
| **OpenAlex** | `https://api.openalex.org` | 开源，跨学科，统一的Paper/Author/Institution数据 | 10 req/s |
| **CrossRef** | `https://api.crossref.org` | DOI元数据，期刊文章 | 50 req/s |
| **DBLP** | `https://api.dblp.org` | 计算机会议/期刊论文 | 公开访问 |

### 4.5 多数据源搜索实现代码

#### OpenAlex Searcher（建议新增）

```python
# 文件: src/agents_v2/search/openalex_searcher.py
import aiohttp

class OpenAlexSearcher(BaseSearcher):
    """OpenAlex学术搜索器 - 跨学科免费API"""

    BASE_URL = "https://api.openalex.org"

    async def search(
        self,
        query: str,
        max_results: int = 10,
        year_filter: str = None
    ) -> SearchResponse:
        url = f"{self.BASE_URL}/works"
        params = {
            "search": query,
            "per-page": min(max_results, 200),
            "select": "id,title,authorships,abstract_inverted_index,publication_year,cited_by_count,concepts,open_access"
        }

        if year_filter:
            params["filter"] = f"publication_year:{year_filter}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                papers = [self._parse_work(w) for w in data.get("results", [])]
                return self._create_response(query, papers, self.name)

    def _parse_work(self, work: dict) -> SearchResult:
        """解析OpenAlex论文格式"""
        return SearchResult(
            paper_id=work["id"].split("/")[-1],
            title=work.get("title", ""),
            abstract=self._reconstruct_abstract(work.get("abstract_inverted_index")),
            authors=[a["author"]["display_name"] for a in work.get("authorships", [])[:5]],
            year=work.get("publication_year", 2024),
            venue=work.get("primary_location", {}).get("source", {}).get("display_name", ""),
            url=work.get("doi", ""),
            citations=work.get("cited_by_count", 0)
        )
```

#### Semantic Scholar Searcher 真实API（当前模拟）

```python
# 文件: src/agents_v2/search/semantic_scholar_searcher.py

class SemanticScholarSearcher(BaseSearcher):
    """Semantic Scholar搜索器 - AI增强学术搜索"""

    API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        url = f"{self.BASE_URL}/paper/search"
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,authors,year,citationCount,venue,externalIds"
        }
        headers = {"x-api-key": self.API_KEY} if self.API_KEY else {}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                data = await resp.json()
                papers = [self._parse_paper(p) for p in data.get("data", [])]
                return self._create_response(query, papers, self.name)
```

### 4.6 项目已有搜索组件

| 文件路径 | 类/模块 | 功能 |
|---------|--------|------|
| `search/search_factory.py` | `SearchFactory` | 搜索器工厂，统一管理多个搜索器 |
| `search/arxiv_searcher.py` | `ArxivSearcher` | arXiv论文搜索 |
| `search/pubmed_searcher.py` | `PubmedSearcher` | PubMed生物医学文献搜索 |
| `search/semantic_scholar_searcher.py` | `SemanticScholarSearcher` | Semantic Scholar搜索 |
| `mcp/search/arxiv_mcp.py` | `ArxivMCPClient` | ArXiv MCP协议实现 |
| `mcp/search/pubmed_mcp.py` | `PubmedMCPClient` | PubMed MCP实现 |
| `qa/paper_search.py` | `PaperSearchAgent` | 综合论文搜索Agent |

### 4.7 实现计划

#### Phase 1: Semantic Scholar 真实 API (P0)
- 申请 API Key: https://api.semanticscholar.org/
- 修改 `semantic_scholar_searcher.py`
- 测试搜索功能

#### Phase 2: OpenAlex 新数据源 (P1)
- 新建 `openalex_searcher.py`
- 实现 SearchFactory 支持
- 实现结果合并

#### Phase 3: CrossRef DOI 解析 (P1)
- 增强 `extended_search.py`
- 实现 DOI 元数据获取

#### Phase 4: DBLP 计算机文献 (P2)
- 新建 `dblp_searcher.py`
- 覆盖计算机领域

---

### 4.8 PDF解析工具对比

| 工具 | GitHub | 公式支持 | 表格支持 | 速度 | 推荐度 |
|------|--------|----------|----------|------|--------|
| **Marker** | VikParuchuri/marker | ⭐⭐⭐⭐⭐ LaTeX输出 | ⭐⭐⭐⭐ | 快 | ⭐⭐⭐⭐⭐ |
| **Nougat** | facebookresearch/nougat | ⭐⭐⭐⭐⭐ MathML | ⭐⭐⭐ | 慢 | ⭐⭐⭐⭐ |
| **PDF-Extract-Kit** | UFAL/pdf-extract-kit | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 中 | ⭐⭐⭐⭐ |

**推荐选择**:
- 通用学术论文: **Marker** (安装简单，速度快)
- 公式为主论文: **Nougat** (Meta出品，公式最准)
- 复杂布局中文: **PDF-Extract-Kit**

### 4.9 图表生成工具对比

| 工具 | 输出格式 | 论文适用性 | 学习曲线 | 推荐度 |
|------|----------|------------|----------|--------|
| **Matplotlib** | PDF/SVG/PNG | ⭐⭐⭐⭐⭐ | 陡 | ⭐⭐⭐⭐⭐ |
| **Plotly** | HTML/PNG | ⭐⭐⭐ (仅预览) | 缓 | ⭐⭐⭐ |
| **ECharts** | HTML | ⭐ (不推荐) | 中 | ⭐ |

**推荐方案**:
- 论文正式图表: **Matplotlib + PDF/EPS**
- 交互式报告: **Plotly (HTML导出)**
- 不推荐 ECharts 用于学术论文

### 4.10 引用管理API对比

| 工具 | API完整性 | 免费可用 | 推荐度 |
|------|-----------|----------|--------|
| **Zotero** | ⭐⭐⭐⭐⭐ 完整REST | ⭐⭐⭐⭐⭐ 完全免费 | ⭐⭐⭐⭐⭐ |
| **Mendeley** | ⭐⭐ 严重降级 | ⭐⭐ 受限 | ⭐ |
| **EndNote** | ⭐ 无公共API | - | - |

**Zotero API核心endpoints**:
```
GET /users/{userID}/items          # 获取文献
POST /users/{userID}/items         # 创建条目
GET /users/{userID}/collections    # 获取收藏夹
```

---

## 五、Skill 优先级汇总

| 优先级 | Skill | 工作量 | 价值 |
|--------|-------|--------|------|
| **P0** | Semantic Scholar API | 中 | 高 |
| **P0** | Trinka AI 语法检查 | 中 | 高 |
| **P1** | OpenAlex API | 中 | 高 |
| **P1** | CrossRef API | 低 | 中 |
| **P1** | iThenticate 查重 | 高 | 高 |
| **P1** | ColBERT Reranker | 中 | 中 |
| **P1** | Marker PDF解析 | 中 | 高 |
| **P1** | Matplotlib 图表生成 | 中 | 高 |
| **P2** | DBLP API | 低 | 中 |
| **P2** | Zotero 集成 | 中 | 中 |
| **P2** | BGE Reranker | 中 | 中 |
| **P2** | Nougat PDF解析 | 中 | 中 |
| **P2** | 本地LLM部署 (Ollama) | 中 | 中 |
| **P2** | GraphRAG | 高 | 高 |

---

## 六、多Agent协作框架对比

### 6.1 框架对比

| 维度 | CrewAI | LangChain/LangGraph | AutoGen |
|------|--------|---------------------|---------|
| **抽象层次** | 高层 | 中低层 | 中层 |
| **学习曲线** | 平缓 | 陡峭 | 中等 |
| **多Agent原生** | 是 | 需LangGraph | 是 |
| **人机协作** | 一般 | 一般 | 强 |
| **代码执行** | 需自集成 | 需自集成 | 内置 |
| **社区生态** | 增长中 | 成熟 | 活跃 |
| **维护方** | CrewAI Inc. | LangChain AI | Microsoft |

### 6.2 框架选择建议

| 场景 | 推荐框架 |
|------|----------|
| 快速构建多角色工作流 | **CrewAI** |
| 深度定制复杂工作流 | **LangGraph** |
| 人机协作+代码执行 | **AutoGen** |

### 6.3 本地LLM部署对比

| 工具 | 特点 | 推荐度 |
|------|------|--------|
| **Ollama** | 命令行优先，API兼容OpenAI | ⭐⭐⭐⭐⭐ |
| **LM Studio** | 桌面GUI，快速原型 | ⭐⭐⭐⭐ |
| **LocalAI** | 企业级，Kubernetes友好 | ⭐⭐⭐⭐ |

---

## 七、知识图谱相关Skill

### 7.1 核心组件

| 组件 | 工具 | 说明 |
|------|------|------|
| **实体识别** | spaCy / LLM-based | 从文本提取实体 |
| **关系抽取** | Stanford NLP / LLM-based | 提取实体关系 |
| **图数据库** | Neo4j / JanusGraph | 存储知识图谱 |
| **GraphRAG** | Microsoft GraphRAG | 图增强检索 |

### 7.2 项目已有实现

| 组件 | 文件 | 状态 |
|------|------|------|
| 实体链接 | `knowledge_graph/kg_hybrid_retriever.py` | ✅ 已有 |
| 图嵌入 | `knowledge_graph/kg_embeddings.py` | ✅ 已有 (TransE/ComplEx) |
| 社区检测 | `knowledge_graph/kg_community.py` | ✅ 已有 (Louvain/Leiden) |
| GraphRAG | `knowledge_graph/kg_graphrag.py` | ✅ 已有 |

---

## 八、附录

### A. API 申请链接

| API | 申请地址 | 费用 |
|-----|----------|------|
| Semantic Scholar | https://api.semanticscholar.org/ | 免费/付费 |
| OpenAlex | https://docs.openalex.org/ | 免费 |
| CrossRef | https://www.crossref.org/ | 免费 |
| Trinka AI | https://www.trinka.ai/ | 付费 |
| iThenticate | https://www.ithenticate.com/ | 机构付费 |
| Grammarly | https://www.grammarly.com/ | 付费 |

### B. GitHub 开源参考项目

#### 多源学术搜索开源项目

| 项目 | GitHub | Stars | 功能 | 技术栈 |
|------|--------|-------|------|--------|
| **GPT-Researcher** | assafelovic/gpt-researcher | 26,739+ | 多Agent研究助手，自动搜索/比较/总结 | Python, LangChain, Tavily |
| **PaperQA** | fairybio/paperqa | 8,422+ | 科学文献RAG，支持PubMed/arxiv/其他 | Python, LangChain, Anthropic |
| **Haystack** | deepset-ai/haystack | 14,800+ | 多源RAG框架，支持40+数据源 | Python, Elasticsearch, FAISS |
| **cite/seek** | atw1028/cite-seek | 1,500+ | 学术搜索聚合器 | Python |
| **Multi-Searcher** | - | - | 多数据源学术搜索原型 | Python |

#### 核心项目分析

**GPT-Researcher** (推荐参考)
```python
# 架构特点:
# - 多Agent协作：规划Agent + 搜索Agent + 写作Agent
# - 自动选择最佳数据源
# - 并行搜索 + 结果去重
# - 支持 Tavily, SerpAPI, Google Scholar 等搜索API

# 关键代码模式:
async def research(self, query):
    # 1. 规划阶段 - 确定搜索策略
    plan = await self.planner.create_plan(query)

    # 2. 并行搜索多个数据源
    results = await asyncio.gather(
        self.search_arxiv(query),
        self.search_pubmed(query),
        self.search_semantic_scholar(query),
        ...
    )

    # 3. 结果合并与去重
    unified = self.deduplicate(results)

    # 4. 生成报告
    return await self.writer.write(unified)
```

**PaperQA** (推荐参考)
```python
# 架构特点:
# - 专为科学论文设计的RAG
# - 内置PDF解析 + 引用提取
# - 支持"获取论文并提问"端到端流程

# 关键功能:
qa = PaperQA("papers/*.pdf")
answer = qa.query("What methods were used?")
```

**Haystack** (框架参考)
```python
# 架构特点:
# - 模块化设计：DocumentStore / Retriever / Reader
# - 支持 Elasticsearch, FAISS, Pinecone 等向量存储
# - 支持 DeepSet, HuggingFace, OpenAI 等LLM

from haystack import Pipeline
p = Pipeline()
p.add_node(component=retriever, name="Retriever", inputs=["Query"])
p.add_node(component=reader, name="Reader", inputs=["Retriever"])
```

#### 多源搜索技术方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **GPT-Researcher 模式** | Agent自主决策，易扩展 | 成本较高 | 深度研究任务 |
| **Haystack 模式** | 成熟稳定，组件丰富 | 学习曲线较陡 | 生产级RAG系统 |
| **PaperQA 模式** | 专为论文设计 | 定制化程度低 | 快速问答场景 |
| **自研多源搜索** | 完全可控，可定制 | 开发工作量大 | 深度定制需求 |

#### 建议集成方式

```python
# 在 PaperAgent 中集成多源搜索能力
# 文件: src/agents_v2/qa/paper_search.py

class MultiSourcePaperSearcher:
    """多源论文搜索器"""

    def __init__(self):
        self.searchers = {
            "arxiv": ArxivSearcher(),
            "pubmed": PubmedSearcher(),
            "semantic_scholar": SemanticScholarSearcher(),
            "openalex": OpenAlexSearcher(),  # 新增
        }

    async def search(self, query: str, sources: List[str] = None) -> SearchResponse:
        sources = sources or list(self.searchers.keys())

        # 并行搜索多个数据源
        tasks = [
            self.searchers[source].search(query)
            for source in sources
            if source in self.searchers
        ]
        results = await asyncio.gather(*tasks)

        # 合并结果
        return self._merge_results(results)
```

---

## 九、2026 年协议与模型新进展 (新增补充)

> 补充时间: 2026-05-01
> 基于最新调研补充 Claude Agent SDK、A2A 协议、DeepSeek 模型等

### 9.1 Claude Agent SDK

Anthropic 于 2025 年底发布 Claude Agent SDK，是构建 AI Agent 的最核心工具包，Claude Code 和 Claude Desktop 均基于此 SDK 构建。

**核心能力**:

| 能力 | 说明 |
|------|------|
| **18+ 内置工具** | 文件读写、Bash命令、Web搜索、SQL查询、Git操作、MCP工具等 |
| **Agent 生命周期钩子** | 支持 preToolUse / postToolUse / preMessage / postMessage 等事件拦截 |
| **自动上下文压缩** | LLM 对话过长时自动摘要压缩，保持上下文字段一致性 |
| **MCP 原生集成** | 直接通过 MCP 协议挂载外部工具/数据源 |
| **Subagents 支持** | 内置子 Agent 机制，自动或手动路由到子 Agent 执行 |
| **权限系统** | 细粒度工具权限控制，沙箱隔离 |
| **Agentskills 支持** | 原生集成 Agent Skills 标准，支持 SKILL.md 加载 |

**Paper Agent 参考架构 (基于 Claude Agent SDK)**:

```python
# Claude Agent SDK 的使用模式
from claude_agent_sdk import Agent, tool, Skill

# 1. 定义工具 (Tool)
@tool(name="search_papers", description="搜索学术论文")
async def search_papers(
    query: str,
    source: str = "semantic_scholar",
    max_results: int = 10,
) -> dict:
    """多源学术论文搜索"""
    searcher = SearchFactory.get(source)
    results = await searcher.search(query, max_results)
    return {"papers": results, "total": len(results)}

# 2. 定义 Skill
class PaperAnalysisSkill(Skill):
    name = "paper-analysis"
    description = "深度分析学术论文"

    async def execute(self, paper: dict) -> dict:
        return await self.analyze(paper)

# 3. 定义 Agent
paper_agent = Agent(
    name="PaperAgent",
    instructions="你是一个学术论文研究助手...",
    tools=[search_papers, read_pdf, format_reference],
    skills=[PaperAnalysisSkill()],
    mcp_servers=["arxiv-mcp", "pubmed-mcp", "semantic-scholar-mcp"],
    subagents={
        "searcher": SearchSubAgent(),
        "analyst": AnalysisSubAgent(),
        "writer": WritingSubAgent(),
    },
)

# 4. 运行
result = await paper_agent.run("搜索深度学习优化最新论文并写综述")
```

**对比项目现有 AgentLoop**:

| 维度 | 项目现有 AgentLoop | Claude Agent SDK |
|------|-------------------|-----------------|
| 工具注册 | `ToolSpec` 手动注册 | `@tool` 装饰器自动注册 |
| 循环控制 | `ReActLoop` 手动实现 | SDK 内置 ReAct + Plan + 自定义 |
| 上下文管理 | 手动截断 | 自动压缩+摘要 |
| MCP 集成 | 基础 `MCPMemoryProtocol` | 原生 MCP Host，自动发现 |
| 子 Agent | `HierarchicalOrchestrator` | SDK 内置 Subagents |
| 权限 | 手动检查 | 内置细粒度权限系统 |

### 9.2 A2A 协议集成

Google A2A (Agent-to-Agent) 协议于 2025 年 4 月 9 日发布，解决多 Agent 间的标准化通信问题，与 MCP 互补。

**Paper Agent A2A 场景**:

```
用户请求: "搜索深度学习优化论文并写综述"
              │
    ┌─────────┴──────────┐
    │ Orchestrator Agent  │ ← 接收任务，分派子任务
    └─────────┬──────────┘
              │ A2A tasks/sendSubscribe
    ┌─────────┼──────────┐
    │         │          │
    ▼         ▼          ▼
  Search   Analyze    Writing
  Agent    Agent      Agent
    │         │          │
    │ A2A     │ A2A      │ A2A
    ▼         ▼          ▼
  返回论文   返回分析   返回初稿
```

**A2A AgentCard 示例**:

```json
{
  "name": "PaperAgent-Search",
  "description": "学术论文搜索Agent，支持多数据源检索",
  "url": "https://paper-agent.example.com",
  "capabilities": { "streaming": true },
  "skills": [
    {
      "id": "arxiv_search",
      "name": "arXiv 搜索",
      "description": "在 arXiv 数据库中搜索预印本论文",
      "tags": ["academic", "preprint"]
    }
  ],
  "authentication": { "schemes": ["bearer_token"] }
}
```

**与 MCP 的关系**: MCP 让 Agent 能"使用工具"（手），A2A 让 Agent 能"相互对话"（口），Skills 让 Agent 能"学习技能"（脑）。三者是互补关系，共同构成完整的 Agent 技术栈。

### 9.3 DeepSeek 模型家族

DeepSeek 以极高的性价比和领先的推理能力，成为 2025-2026 年最重要的开源 LLM 之一。

| 模型 | 发布时间 | 核心特点 | 适用 Paper Agent 场景 |
|------|----------|---------|---------------------|
| **DeepSeek-V3** | 2024-12 | 671B MoE (37B活跃)，训练成本仅 557.6 万美元 | 论文写作、内容生成 |
| **DeepSeek-R1** | 2025-01-20 | 强化学习推理，纯RL无SFT，数学/代码推理领先 | 论文数据分析、逻辑推理 |
| **DeepSeek-R1-Distill** | 2025-01 | 基于 Qwen/Llama 蒸馏，小模型高性能 | 本地部署、低成本推理 |
| **DeepSeek-V4 Preview** | 2026-04-24 | 最新旗舰，推理+生成一体 | 全部 Paper Agent 场景 |

**成本优势**:

| 模型 | 输入价格 ($/1M tokens) | 输出价格 ($/1M tokens) | 相比 GPT-4o |
|------|----------------------|----------------------|------------|
| DeepSeek-V3 | $0.27 | $1.10 | ~1/18 |
| DeepSeek-R1 | $0.55 | $2.19 | ~1/9 |
| GPT-4o | $2.50 | $10.00 | 基准 |
| Claude Opus 4 | $15.00 | $75.00 | ~6x 基准 |

**Paper Agent 集成建议**:

```python
# 配置示例: 按任务类型选择模型
MODEL_ROUTING = {
    "paper_search": "deepseek-v3",        # 搜索: 低成本高吞吐
    "paper_analysis": "deepseek-r1",       # 分析: 强推理能力
    "paper_writing": "claude-opus-4",      # 写作: 长文本质量最高
    "math_reasoning": "deepseek-r1",       # 数学: R1 推理最强
    "code_generation": "deepseek-v4",      # 代码: V4 最新
    "topic_refinement": "deepseek-r1",     # 选题: 需要深度推理
}
```

### 9.4 Claude 模型家族最新进展

| 模型 | 发布时间 | 核心特点 | Paper Agent 适用 |
|------|----------|---------|-----------------|
| **Claude Opus 4.7** | 2026-04-16 | 编码能力提升 13%，200K 上下文 | 论文数据分析、复杂推理 |
| **Claude Sonnet 4.6** | 2026-Q1 | 性价比最佳，编码/工具使用强 | 论文搜索、大纲生成 |
| **Claude Haiku 4.5** | 2025-10 | 最快速度，最低成本 | 问题分类、简单问答 |

### 9.5 Qwen 模型家族

| 模型 | 发布时间 | 参数 | 核心特点 |
|------|----------|------|---------|
| **Qwen3.5-Max** | 2026-02 | MoE | 阿里旗舰，中文能力顶级 |
| **Qwen3.6-Max-Preview** | 2026-04 | MoE | 最新预览版，推理增强 |
| **Qwen3.5-Coder** | 2026-02 | 7B-32B | 代码生成专用 |
| **Qwen3.5-Math** | 2026-02 | 7B-72B | 数学推理专用 |

**Paper Agent 使用**: Qwen 系列是中文论文场景的首选，适合中文选题、中文文献解读、中文写作辅助。

### 9.6 Google Gemini 3.1 模型家族

Google 于 2026 年 Cloud Next 大会发布 Gemini 3.1 模型家族:

| 模型 | 核心特点 | Paper Agent 适用 |
|------|---------|-----------------|
| **Gemini 3.1 Pro** | 原生多模态，可调节推理深度，ARC-AGI-2 得分 77.1% | 图表理解、论文图像分析 |
| **Gemini 3.1 Flash** | 低延迟，高吞吐 | 快速问答、检索排序 |
| **Gemini 3.1 Ultra** | 最强推理，多跳逻辑推理，长篇自主编程 | 复杂论文分析、综述生成 |

**关键创新**: 可调节的推理深度 (adjustable reasoning depth) — 用户可根据任务复杂度选择浅推理或深推理，在成本和质量间灵活权衡。

### 9.7 模型选择策略

```
Paper Agent 任务 → 模型路由规则:

1. 问题分类/路由 → Haiku 4.5 / DeepSeek-V3 (低成本)
2. 论文搜索/查询 → Sonnet 4.6 / Gemini 3.1 Flash (平衡)
3. 论文深度分析 → Opus 4.7 / DeepSeek-R1 (强推理)
4. 论文初稿写作 → Opus 4.7 / DeepSeek-V3 (长文本)
5. 中文内容处理 → Qwen 3.5-Max / DeepSeek-V3 (中文优先)
6. 数学推理 → DeepSeek-R1 / Qwen 3.5-Math (数学专用)
7. 图表/图像理解 → Gemini 3.1 Pro / Claude Opus (多模态)
8. 引用格式检查 → Haiku 4.5 / DeepSeek-V3 (简单任务)
9. 论文润色 → Opus 4.7 / Claude Sonnet (质量优先)
```

### 9.8 Agent Skills 标准与 SKILL.md

Anthropic 于 2025 年 12 月 18 日发布 Agent Skills 开放标准，目前已有 5 大标准设计模式和 `agentskills.io` 注册平台。

**Paper Agent 当前 vs Agent Skills 标准对比**:

| 维度 | Paper Agent 当前 | Agent Skills 标准 | 差距 |
|------|-----------------|-------------------|------|
| 技能定义 | Python 类 + 注册表 | SKILL.md + 文件夹 | 需适配 |
| 加载机制 | 启动时全部加载 | 渐进式披露（三层） | 需改进 |
| 可移植性 | 仅本项目可用 | 跨平台、跨框架 | 需标准化 |
| 社区共享 | 无 | agentskills.io 注册表 | 可贡献 |

**建议**: 将项目 Skill 按 Agent Skills 标准重构为 SKILL.md 格式，受益于渐进式加载以节省 Token，同时获得跨平台复用能力。

### 9.9 Vercel Skills.sh

Vercel 于 2026 年初发布 Skills.sh，定位为"AI Agent 界的 npm"——通过命令行执行各种可复用的 Skill 操作。与 Anthropic Agent Skills 互补，更偏向 CLI 工具和 Shell 脚本封装。

### 9.10 行业趋势总结

| 趋势 | 描述 | Paper Agent 影响 |
|------|------|-----------------|
| **推理模型兴起** | DeepSeek-R1、o3、Gemini 3.1 深度推理 | 论文分析质量大幅提升 |
| **模型成本暴跌** | 开源模型成本仅为闭源 1/20 | 可大规模并行搜索 |
| **协议标准化** | MCP/A2A/Skills/AG-UI 形成完整栈 | 架构更清晰、可扩展 |
| **Agent SDK 成熟** | Claude Agent SDK、Google ADK | 开发效率大幅提升 |
| **Skills 生态起飞** | 2026 为"Agent Skills 元年" | 社区 Skills 可直接复用 |

---

**最后更新**: 2026-05-01 (补充 Claude Agent SDK、A2A、DeepSeek、Gemini 3.1、Agent Skills 标准等)
