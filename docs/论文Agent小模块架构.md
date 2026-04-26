# 论文Agent小模块架构

> 从论文搜索到写作完成的完整流程模块划分

---

## 一、论文搜索模块 (Paper Search) ⭐ 已实现

### 1.1 已实现的小模块

```
src/agents_v2/search/
├── __init__.py
├── base_searcher.py              # 搜索基类和数据结构 [已测试]
├── arxiv_searcher.py             # ArXiv搜索 [已测试]
├── pubmed_searcher.py            # PubMed搜索 [已测试]
├── semantic_scholar_searcher.py  # SS搜索+引用 [已测试]
└── search_factory.py            # 搜索器工厂 [已测试]
```

| 小模块 | 功能 | 测试 |
|--------|------|------|
| `base_searcher.py` | SearchResult, SearchResponse, BaseSearcher | ✅ |
| `arxiv_searcher.py` | ArXiv搜索 | ✅ |
| `pubmed_searcher.py` | PubMed搜索 | ✅ |
| `semantic_scholar_searcher.py` | SS搜索 + 引用分析 | ✅ |
| `search_factory.py` | 统一搜索接口 | ✅ |

**测试数**: 14

### 1.2 待实现的小模块

```
MCPSearch/
├── mcp_client.py         # MCP协议客户端
├── arxiv_mcp.py          # arXiv MCP
├── pubmed_mcp.py         # PubMed MCP
└── paper_mcp.py         # 通用论文MCP
```

### 1.3 待实现的搜索策略

```
SearchStrategy/
├── query_parser.py       # 查询解析
├── query_rewriter.py     # 查询改写
├── query_expander.py      # 查询扩展
└── deduplicator.py       # 去重
```

---

## 二、PDF解析模块 (PDF Parsing)

### 2.1 已实现的小模块 ⭐

```
src/agents_v2/tools/
├── citation_extractor.py   # 引用提取 [已测试]
├── reference_parser.py     # 参考文献解析 [已测试]
├── section_parser.py       # 章节解析 [已测试]
├── metadata_parser.py      # 元数据解析 [已测试]
└── pdf_parser.py          # PDF解析器（组合以上组件）
```

| 小模块 | 功能 | 测试 |
|--------|------|------|
| `citation_extractor.py` | 提取[1][1,2][1-3]格式引用 | ✅ 12 tests |
| `reference_parser.py` | 解析参考文献条目 | ✅ 6 tests |
| `section_parser.py` | 解析论文章节 | ✅ 7 tests |
| `metadata_parser.py` | 提取标题/作者/摘要/DOI | ✅ 6 tests |

### 2.2 待实现的子模块

#### 文本提取
```
TextExtraction/
├── pdf_text_extractor.py # PDF文本提取
├── text_cleaner.py       # 文本清洗
├── text_segmenter.py     # 文本分段
└── sentence_splitter.py  # 句子分割
```

#### 表格提取
```
TableExtraction/
├── table_detector.py     # 表格检测
├── table_parser.py       # 表格解析
├── table_structurer.py   # 表格结构化
└── table_normalizer.py   # 表格标准化
```

#### 图表提取
```
FigureExtraction/
├── figure_detector.py    # 图表检测
├── figure_classifier.py  # 图表分类
├── figure_caption_extractor.py
└── figure_description.py
```

#### 公式提取
```
FormulaExtraction/
├── formula_detector.py
├── latex_parser.py
├── mathml_converter.py
└── formula_renderer.py
```

---

## 三、论文理解模块 (Paper Understanding)

### 3.1 信息抽取

```
InformationExtraction/
├── title_extractor.py     # 标题提取
├── abstract_extractor.py  # 摘要提取
├── author_extractor.py    # 作者提取
├── keyword_extractor.py   # 关键词提取
├── metadata_extractor.py  # 元数据提取
└── section_classifier.py  # 章节分类
```

| 小模块 | 功能 | 可深究方向 |
|--------|------|-----------|
| `title_extractor.py` | 论文标题提取 | 首行检测、大字体识别 |
| `abstract_extractor.py` | 摘要提取 | Abstract标记识别 |
| `author_extractor.py` | 作者信息提取 |  affiliation匹配 |
| `keyword_extractor.py` | 关键词提取 | 自动关键词/MeSH |
| `metadata_extractor.py` | DOI/期刊/年份 | 多格式解析 |
| `section_classifier.py` | 章节分类 | Introduction/Method等 |

### 3.2 全文结构化

```
StructuredPaper/
├── paper_schema.py       # 论文Schema定义
├── section_extractor.py   # 章节提取
├── paragraph_analyzer.py  # 段落分析
├── citation_linker.py     # 引用链接
└── paper_summarizer.py   # 论文摘要
```

| 小模块 | 功能 | 可深究方向 |
|--------|------|-----------|
| `paper_schema.py` | 数据结构定义 | JSON Schema/Protobuf |
| `section_extractor.py` | 提取各章节 | 层级结构恢复 |
| `paragraph_analyzer.py` | 分析段落功能 | 主题句、支撑句 |
| `citation_linker.py` | 链接引用 | 参考文献映射 |
| `paper_summarizer.py` | 生成摘要 | Extractive/Abstractive |

---

## 四、论文写作模块 (Paper Writing)

### 4.1 Pipeline Agents

```
PipelineAgents/
├── topic_agent.py        # 选题Agent
├── literature_agent.py    # 文献调研Agent
├── thesis_agent.py        # Thesis凝练Agent
├── outline_agent.py       # 大纲制定Agent
├── draft_writer_agent.py  # 初稿撰写Agent
├── editor_agent.py        # 修订编辑Agent
└── reviewer_agent.py      # 最终审核Agent
```

| 小模块 | 功能 | 核心能力 |
|--------|------|----------|
| `topic_agent.py` | 选题方向 | 创新性评估、热点分析 |
| `literature_agent.py` | 文献调研 | 综述生成、研究gap发现 |
| `thesis_agent.py` | Thesis凝练 | 核心论点提炼 |
| `outline_agent.py` | 大纲制定 | 逻辑结构设计 |
| `draft_writer_agent.py` | 初稿撰写 | 多Section生成 |
| `editor_agent.py` | 修订编辑 | 逻辑优化、语言润色 |
| `reviewer_agent.py` | 最终审核 | 质量评估、格式检查 |

### 4.2 写作工具

```
WritingTools/
├── paper_tools.py        # 论文完整性检查
│   ├── check_completeness()  # 检查结构完整性
│   ├── score_paper()         # 多维度评分
│   └── format_reference()     # 多格式引用
├── outline_builder.py    # 大纲构建
├── section_writer.py     # 章节撰写
└── citation_manager.py   # 引用管理
```

### 4.3 论文检查

```
PaperCheck/
├── completeness_checker.py  # 完整性检查
├── plagiarism_checker.py   # 查重检测
├── format_checker.py       # 格式检查
└── quality_scorer.py      # 质量评分
```

| 小模块 | 功能 | 可深究方向 |
|--------|------|-----------|
| `completeness_checker.py` | 检查必要章节 | 缺失检测、建议生成 |
| `plagiarism_checker.py` | 文字相似度 | iThenticate API对接 |
| `format_checker.py` | 格式规范性 | APA/IEEE/ACM格式 |
| `quality_scorer.py` | 多维质量评估 | 创新性/完整性/可复现性 |

---

## 五、辅助模块

### 5.1 知识图谱

```
KnowledgeGraph/
├── kg_builder.py         # 图谱构建
├── entity_extractor.py   # 实体抽取(作者/方法/数据集)
├── relation_extractor.py # 关系抽取
├── kg_query.py          # 图谱查询
└── kg_visualizer.py    # 图谱可视化
```

### 5.2 引用分析

```
CitationAnalysis/
├── citation_extractor.py # 引用提取
├── citation_ranker.py    # 引用重要性排序
├── citation_graph.py     # 引用网络
└── citation_recommender.py # 引用推荐
```

### 5.3 记忆系统

```
Memory/
├── short_term.py        # 短期记忆
├── long_term.py         # 长期记忆
├── episodic.py          # 情景记忆
└── preference.py        # 偏好记忆
```

---

## 六、模块依赖关系

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    用户请求                              │
                    └─────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ TopicAgent  │───▶│Literature   │───▶│  Thesis     │───▶│  Outline    │
│   选题      │    │  Agent      │    │  Agent      │    │  Agent      │
└─────────────┘    │   文献调研   │    │   Thesis凝练 │    │   大纲制定   │
                   └─────────────┘    └─────────────┘    └─────────────┘
                          │                                       │
                          ▼                                       ▼
                   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
                   │Paper Search │    │   PDF       │    │  Draft     │
                   │  论文搜索    │───▶│  Parsing   │───▶│  Writer    │
                   └─────────────┘    │   PDF解析   │    │  Agent     │
                          │           └─────────────┘    │   初稿撰写   │
                          ▼                  │           └─────────────┘
                   ┌─────────────┐          │                   │
                   │MCPSearch    │          ▼                   ▼
                   │   MCP搜索   │    ┌─────────────┐    ┌─────────────┐
                   └─────────────┘    │Information  │    │  Editor    │
                                      │ Extraction  │───▶│  Agent     │
                                      │   信息抽取   │    │   修订编辑   │
                                      └─────────────┘    └─────────────┘
                                                              │
                                                              ▼
                                                       ┌─────────────┐
                                                       │  Reviewer   │
                                                       │  Agent      │
                                                       │   审核       │
                                                       └─────────────┘
```

---

## 七、模块细化程度

| 层级 | 示例 | 说明 |
|------|------|------|
| L1 | `arxiv_searcher.py` | 整个arXiv搜索 |
| L2 | `arxiv_api.py`, `arxiv_parser.py` | API调用 + 结果解析分离 |
| L3 | `arxiv_api.py` → `request.py`, `retry.py`, `rate_limit.py` | 进一步拆分 |
| L4 | `request.py` → `http_client.py`, `headers.py` | 更细粒度 |

**当前细化程度**: 大部分模块在L1-L2，可继续深究到L3-L4

---

## 八、测试覆盖目标

| 模块 | 当前测试 | 目标测试 | 细化方向 |
|------|----------|----------|----------|
| PaperSearch | 少 | 搜索器单元测试、集成测试 | Mock API、真实API测试 |
| PDF Parsing | 无 | 提取准确性测试 | 标准PDF测试集 |
| Text Extraction | 无 | 清洗效果测试 | 边界情况 |
| Table Extraction | 无 | 结构化准确性 | 多格式表格 |
| Reference Parser | 无 | 解析准确率 | 正则 vs LLM |

---

*最后更新: 2026-04-27*
