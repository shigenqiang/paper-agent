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