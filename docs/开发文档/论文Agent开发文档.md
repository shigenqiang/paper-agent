# 论文Agent开发文档

> 智能论文调研与写作系统 - 完整技术文档

版本: 6.0
更新日期: 2026-04-28
状态: ✅ 迭代完成

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [小模块架构](#3-小模块架构)
4. [论文搜索](#4-论文搜索)
5. [定时报告](#5-定时报告)
6. [论文写作](#6-论文写作)
7. [论文修改](#7-论文修改)
8. [对话问答](#8-对话问答)
9. [订阅管理](#9-订阅管理)
10. [知识图谱](#10-知识图谱)
11. [系统集成](#11-系统集成)
12. [企业功能](#12-企业功能)
13. [迭代计划](#13-迭代计划)
14. [测试覆盖](#14-测试覆盖)

---

## 1. 项目概述

### 1.1 目标

构建一个智能论文调研与写作系统，实现：

- **多源搜索** - 从多个学术平台搜索论文
- **定时报告** - 每日/每周/每月论文报告自动生成
- **论文写作** - 从选题到大纲到初稿的全流程辅助
- **论文修改** - 智能改稿、润色、评审多轮迭代
- **对话问答** - 基于论文的智能问答与比较分析
- **订阅推送** - 多渠道论文推送服务
- **知识图谱** - 论文关系网络可视化
- **企业支持** - 多用户、团队协作

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| 模块化架构 | 每个功能独立Agent，便于扩展 |
| 精细化拆分 | 小模块边界清晰，可独立测试 |
| 异步优先 | 使用async/await处理IO密集任务 |
| 降级策略 | JSON解析失败时提供降级输出 |
| 可配置性 | 关键词、频率、输出格式均可配置 |
| 可追溯性 | 所有输出包含参考文献 |

### 1.3 核心Agent列表

| Agent类型 | Agent名称 | 文件 | 优先级 |
|-----------|-----------|------|--------|
| **报告** | DailyWatcher | `qa/daily_watcher.py` | P0 |
| | WeeklyReportGenerator | `qa/weekly_report.py` | P0 |
| | MonthlyReportGenerator | `qa/monthly_report.py` | P0 |
| | PaperFlash | `qa/paper_flash.py` | P1 ✅ |
| **写作** | TopicAgent | `paper_agents/thesis_agent.py` | P0 |
| | OutlineGeneratorAgent | `writing/outline_generator.py` | P0 |
| | DraftGeneratorAgent | `writing/draft_generator.py` | P0 |
| | LiteratureReviewAgent | `writing/literature_review.py` | P1 |
| | ProposalGeneratorAgent | `writing/proposal_generator.py` | P1 |
| **修改** | SmartReviserAgent | `writing/smart_reviser.py` | P0 |
| | ReportRefinerAgent | `writing/report_refiner.py` | P0 |
| | LanguagePolisherAgent | `writing/smart_reviser.py` | P1 |
| | ReviewerAgent | `writing/report_refiner.py` | P1 |
| **搜索** | PaperSearchAgent | `qa/paper_search.py` | P0 |
| | QueryRouter | `qa/query_router.py` | P0 |
| **调度** | SubscriptionManager | `scheduler/subscription_manager.py` | P1 ✅ |
| | ReportScheduler | `scheduler/report_scheduler.py` | P1 ✅ |

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         用户层                                        │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────┐ │
│   │ 对话问答 │  │报告订阅 │  │ 写作任务 │  │论文追踪 │  │推送通知│ │
│   └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └───┬───┘ │
├────────┴───────────┴───────────┴───────────┴───────────┴──────────┤
│                         服务层                                        │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│   │  定时调度   │  │  订阅管理   │  │  推送服务   │  │  API网关   │ │
│   └────────────┘  └────────────┘  └────────────┘  └────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                         Agent层                                      │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│   │  报告Agent │  │  写作Agent │  │  搜索Agent │  │  路由Agent │        │
│   │Daily/Week │  │大纲/初稿  │  │多源并行   │  │问题分类   │        │
│   │/Month/Flash│  │/修订/润色 │  │去重排序   │  │意图识别   │        │
│   └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └────┬─────┘        │
│         └───────────────┼───────────────┼──────────────┘              │
├─────────────────────────────────────────────────────────────────────┤
│                       数据源层                                       │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ arXiv │ PubMed │ Semantic Scholar │ CrossRef │ DBLP │ OpenAlex │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 论文写作Pipeline

```
选题 ──▶ 大纲 ──▶ 初稿 ──▶ 修订 ──▶ 润色 ──▶ 评审
  │        │        │        │        │        │
  ▼        ▼        ▼        ▼        ▼        ▼
Topic   Outline  Draft   Refine  Polish  Review
Agent   Agent   Writer   Agent   Agent   Agent
```

### 2.3 模块依赖关系

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
                   └─────────────┘    │   PDF解析   │    │   初稿撰写   │
                          │           └─────────────┘    └─────────────┘
                          ▼                  │                   │
                   ┌─────────────┐          │                   ▼
                   │MCPSearch    │          ▼           ┌─────────────┐
                   │   MCP搜索   │    ┌─────────────┐   │  Editor    │
                   └─────────────┘    │Information  │───▶│  Agent     │
                                      │ Extraction  │    │   修订编辑   │
                                      │   信息抽取   │    └─────────────┘
                                      └─────────────┘
                                                              │
                                                              ▼
                                                       ┌─────────────┐
                                                       │  Reviewer   │
                                                       │  Agent      │
                                                       │   审核       │
                                                       └─────────────┘
```

---

## 3. 小模块架构

### 3.1 模块总览

本文档记录 Paper Agent 项目中已精细化的小模块。每个模块满足以下标准：
- **解耦性**：模块边界清晰，依赖最小化
- **可测试性**：每个模块有独立的测试文件
- **单一职责**：每个模块只做一件事

### 3.2 测试覆盖总汇

| 模块 | 小模块数 | 测试数 |
|------|----------|--------|
| Search (搜索) | 6 | 40 |
| Retrieval (检索) | 16 | 350+ |
| PDF解析 | 8 | 60+ |
| Personalization | 5 | 50 |
| Production | 3 | 43 |
| Multimodal | 6 | 38 |
| MultiAgent | 4 | 33 |
| Evaluation | 15 | 80+ |
| Routing | 7 | 40+ |
| Writing | 10 | 50+ |
| MCP | 4 | 25 |
| Tools | 5 | 35+ |
| **总计** | **89** | **840+** |

> 当前总计: 1880+ passing tests (99.0% pass rate)
> **开发状态**: Phase 1-6 全部30个迭代已完成 ✅

---

## 4. 论文搜索

### 4.1 支持的数据源

| 数据源 | API | 类型 | 说明 | 优先级 |
|--------|-----|------|------|--------|
| **arXiv** | export.arxiv.org | 预印本 | cs.LG, stat.ML, stat.ME, math.ST | P0 |
| **PubMed** | eutils.ncbi.nlm.nih.gov | 学术数据库 | 生物医学文献 | P0 |
| **Semantic Scholar** | api.semanticscholar.org | 学术搜索 | AI增强、TLDR、引用分析 | P1 |
| **CrossRef** | api.crossref.org | 元数据 | DOI元数据、期刊文章 | P1 |
| **DBLP** | api.dblp.org | 计算机文献 | 会议论文为主 | P1 |
| **OpenAlex** | api.openalex.org | 学术知识库 | 跨学科文献 | P1 |
| **Papers with Code** | paperswithcode.com | 论文+代码 | 代码关联 | P2 |
| **ACL Anthology** | aclweb.org/anthology | NLP文献 | 自然语言处理 | P2 |
| **IEEE Xplore** | ieeexplore.ieee.org | 工程应用 | 工程技术文献 | P2 |

### 4.2 搜索模块结构

```
src/agents_v2/search/
├── __init__.py
├── base_searcher.py              # 搜索基类、数据结构
├── arxiv_searcher.py             # ArXiv搜索
├── pubmed_searcher.py            # PubMed搜索
├── semantic_scholar_searcher.py  # Semantic Scholar搜索
├── search_factory.py             # 搜索器工厂
└── query_parser.py               # 查询解析器
```

### 4.3 核心类

| 类 | 功能 | 测试 |
|----|------|------|
| `SearchResult` | 搜索结果数据结构 | ✅ |
| `SearchResponse` | 搜索响应结构 | ✅ |
| `BaseSearcher` | 搜索器抽象基类 | ✅ |
| `ArxivSearcher` | ArXiv论文搜索 | ✅ |
| `PubmedSearcher` | PubMed生物医学搜索 | ✅ |
| `SemanticScholarSearcher` | SS搜索+引用分析 | ✅ |
| `SearchFactory` | 多搜索器统一管理 | ✅ |
| `QueryParser` | 查询意图识别、关键词提取 | ✅ |

### 4.4 QueryParser 详解

```python
class QueryIntent(Enum):
    FACTUAL = "factual"           # 事实性问题
    EXPLORATORY = "exploratory"  # 探索性问题
    COMPARATIVE = "comparative"   # 比较性问题
    EXPLANATORY = "explanatory"  # 解释性问题
    ACTION = "action"            # 动作请求

class ParsedQuery:
    original: str                # 原始查询
    intent: QueryIntent          # 查询意图
    keywords: List[str]         # 关键词
    entities: List[str]         # 实体
    modifiers: List[str]         # 修饰词
    is_temporal: bool           # 是否时间相关
    is_quantity: bool           # 是否数量相关
    language: str               # 语言检测
```

### 4.5 搜索输出格式

```json
{
    "success": true,
    "papers": [
        {
            "paper_id": "arxiv:2401.12345",
            "title": "论文标题",
            "authors": ["作者1", "作者2"],
            "year": 2024,
            "abstract": "摘要内容...",
            "url": "https://...",
            "source": "arxiv",
            "citations": 156,
            "keywords": ["machine learning"],
            "methodology": "方法描述",
            "tldr": "一句话总结",
            "has_code": true,
            "code_url": "https://github.com/..."
        }
    ],
    "total_count": 45,
    "search_time": 1.23,
    "sources_used": ["arxiv", "pubmed"]
}
```

### 4.6 扩展搜索功能

| 功能 | 方法 | 说明 |
|------|------|------|
| 趋势分析 | `analyze_paper_trend(topic, start_year, end_year)` | 分析论文发表趋势 |
| 论文比较 | `compare_papers(paper_ids, metrics)` | 比较论文指标 |
| 引用获取 | `get_citations(paper_id)` | 获取引用列表 |
| DOI元数据 | `get_doi_metadata(doi)` | 通过DOI获取信息 |

---

## 5. 定时报告

### 5.1 报告类型总览

| 类型 | Agent | 文件 | 时间范围 | 论文量 | 优先级 |
|------|-------|------|---------|--------|--------|
| **每日报告** | DailyWatcher | `qa/daily_watcher.py` | 30天 | 20-50篇 | P0 |
| **每周报告** | WeeklyReportGenerator | `qa/weekly_report.py` | 7天 | 50-200篇 | P0 |
| **每月报告** | MonthlyReportGenerator | `qa/monthly_report.py` | 30天 | 100-500篇 | P0 |
| **论文快讯** | PaperFlash | (待实现) | 实时 | 5-10篇 | P1 |

### 5.2 每日报告 (DailyWatcher)

```python
# 输入
{
    "keywords": ["statistical learning", "causal inference"],
    "days": 30,
    "max_papers": 10
}

# 输出
{
    "date": "2026-04-27",
    "topic": "统计学习、因果推断",
    "papers_found": 45,
    "summary": "本周新增45篇论文，主要集中在...",
    "new_methods": ["diffusion model", "state space model"],
    "trends": ["大模型微调", "因果表示学习"],
    "top_papers": [...],
    "references": [...]
}
```

### 5.3 每周报告 (WeeklyReportGenerator)

```python
# 输入
{
    "keywords": ["deep learning", "transformer"],
    "week_start": "2026-04-20",
    "week_end": "2026-04-26",
    "max_papers": 20
}

# 输出
{
    "week_start": "2026-04-20",
    "week_end": "2026-04-26",
    "papers_found": 156,
    "summary": "本周共156篇论文，较上周增长12%...",
    "method_breakdown": {...},
    "top_papers": [...],
    "emerging_trends": [...],
    "week_over_week_change": "+12%"
}
```

### 5.4 每月报告 (MonthlyReportGenerator)

```python
# 输入
{
    "keywords": ["statistical learning"],
    "year": 2026,
    "month": 4,
    "max_papers": 50
}

# 输出
{
    "month": "2026-04",
    "papers_found": 523,
    "summary": "本月共523篇论文，涵盖...",
    "method_distribution": {...},
    "weekly_breakdown": {...},
    "top_papers": [...],
    "influential_authors": [...],
    "key_themes": [...],
    "research_gaps": [...]
}
```

### 5.5 论文快讯 (PaperFlash) - P1

| 功能 | 说明 |
|------|------|
| 热点论文速读 | 5分钟内生成精炼解读（300字以内） |
| arXiv热门追踪 | 监控cs.LG, stat.ML等分类热门论文 |
| 顶会论文速报 | NeurIPS/ICML/ICLR等顶会期间每日专题 |

### 5.6 报告对比

| 特性 | 每日报告 | 每周报告 | 每月报告 | 论文快讯 |
|------|---------|---------|---------|---------|
| **时间范围** | 30天 | 7天 | 30天 | 当天/实时 |
| **论文处理量** | 20-50篇 | 50-200篇 | 100-500篇 | 5-10篇 |
| **分析深度** | 浅 | 中 | 深 | 浅 |
| **生成速度** | <60s | <180s | <300s | <30s |
| **核心输出** | 新论文列表 | 趋势变化 | 领域全景 | 热点速读 |

---

## 6. 论文写作

### 6.1 写作Pipeline Agents

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

### 6.2 选题 (TopicAgent)

```python
# 输入
{
    "domain": "机器学习",
    "interests": ["因果推断", "表示学习"],
    "exclude": ["强化学习"]
}

# 输出
{
    "topics": [
        {
            "title": "因果表示学习在医学诊断中的应用",
            "description": "探索如何从观测数据中学习因果表示...",
            "novelty": "将因果推断与深度表示学习结合...",
            "feasibility": "数据充足，已有baseline方法"
        }
    ]
}
```

### 6.3 大纲生成 (OutlineGeneratorAgent)

```python
# 输入
{
    "topic": "深度学习在医学影像中的应用",
    "type": "research_paper",
    "sections": ["introduction", "methods", "experiments", "conclusion"]
}

# 输出
{
    "outline": {
        "1. Introduction": {...},
        "2. Related Work": {...},
        "3. Method": {...},
        "4. Experiments": {...},
        "5. Conclusion": {...}
    },
    "estimated_length": "8-10页"
}
```

### 6.4 初稿撰写 (DraftGeneratorAgent)

```python
# 输入
{
    "outline": outline_data,
    "references": paper_list,
    "style": "academic"
}

# 输出
{
    "draft": "完整论文初稿...",
    "word_count": 5000,
    "sections_completed": ["1", "2", "3", "4", "5"]
}
```

### 6.5 写作工具

| 工具 | 文件 | 功能 | 优先级 |
|------|------|------|--------|
| ReflectionEngine | `reflection_engine.py` | 反思引擎，提升生成质量 | P1 |
| AnswerQualityChecker | `answer_quality_checker.py` | 答案质量检查 | P1 |
| StreamingGenerator | `streaming_generator.py` | 流式生成，打字机效果 | P1 |
| GenerationOptimizer | `generation_optimizer.py` | 批量生成优化 | P2 |
| CitationGenerator | `citation_generator.py` | 多格式引用生成 | P0 |

### 6.6 论文检查

```
PaperCheck/
├── completeness_checker.py  # 完整性检查
├── plagiarism_checker.py    # 查重检测
├── format_checker.py       # 格式检查
└── quality_scorer.py       # 质量评分
```

---

## 7. 论文修改

### 7.1 修改流程

```
原始论稿 ──▶ 智能改稿 ──▶ 多轮精炼 ──▶ 语言润色 ──▶ 最终评审
    │           │            │            │           │
    ▼           ▼            ▼            ▼           ▼
 原文      针对性修改     迭代优化     语法术语     质量评分
```

### 7.2 智能改稿 (SmartReviserAgent)

**功能：**
- 解析导师/审稿人意见
- 针对性修改文本
- 保持修改一致性
- 标记修改内容

```python
# 输入
{
    "original_text": "论文原文...",
    "feedback": "方法部分不够详细，需要补充实验细节...",
    "highlight_changes": True
}

# 输出
{
    "success": True,
    "result": {
        "original_text": "...",
        "revised_text": "修改后的文本...",
        "revision_report": "修改统计...",
        "feedback_categories": ["content", "language"],
        "total_revisions": 8
    }
}
```

### 7.3 多轮精炼 (ReportRefinerAgent)

**功能：**
- 多轮迭代优化
- 评审-修改-精炼循环
- 质量评估与改进
- 针对性问题修复

```python
# 输入
{
    "draft": "初稿内容...",
    "focus_areas": ["结构", "逻辑", "引用", "语言"],
    "max_iterations": 3,
    "quality_threshold": 0.8
}

# 输出
{
    "success": True,
    "result": {
        "original_draft": "...",
        "final_draft": "精炼后的文本...",
        "iterations_completed": 3,
        "final_quality_score": 0.85,
        "quality_improvement": 0.25
    }
}
```

### 7.4 语言润色 (LanguagePolisherAgent)

**功能：**
- 语法检查与纠正
- 术语规范化
- 句式优化
- 中英翻译润色

```python
# 输入
{
    "text": "要润色的文本...",
    "language": "zh",
    "polish_level": "medium"  # light, medium, heavy
}
```

### 7.5 质量评审 (ReviewerAgent)

**评审维度：**

| 维度 | 说明 | 权重 |
|------|------|------|
| structure | 结构完整性 | 20% |
| logic | 逻辑连贯性 | 25% |
| argumentation | 论证充分性 | 25% |
| citation | 引用准确性 | 15% |
| language | 语言表达 | 15% |

---

## 8. 对话问答

### 8.1 交互模式

| 模式 | 示例 | 处理流程 | 优先级 |
|------|------|---------|--------|
| **问答** | "transformer的最新论文有哪些？" | 搜索 → 摘要 → 回答 | P0 |
| **比较** | "对比贝叶斯方法和深度学习在时间序列上的应用" | 多论文 → 对比分析 | P1 |
| **探索** | "因果推断领域还有哪些未解决的问题？" | 搜索 → 趋势分析 → 研究空白 | P1 |
| **追踪** | "追踪X教授的最新论文" | 作者搜索 → 研究脉络 | P1 |

### 8.2 问题路由

```python
class QuestionType(Enum):
    BASIC_QUERY = "basic_query"        # 基础查询 → 知识库
    PROFESSIONAL = "professional"      # 专业问题 → 论文搜索
    FRONTIER = "frontier"              # 前沿探索 → 多源搜索
    APPLICATION = "application"        # 应用咨询 → 案例搜索
```

### 8.3 查询分类 (Retrieval模块)

#### 关键词集合

| 关键词集 | 示例 |
|----------|------|
| REASONING_KEYWORDS | 为什么, why, 分析 |
| COMPARISON_KEYWORDS | 对比, 比较, vs |
| DEFINITION_KEYWORDS | 什么是, what is |
| FACT_KEYWORDS | 谁, 哪一年, who |
| EXPLORATION_KEYWORDS | 探索, 最新, explore |

#### 分类器

```python
class QueryType(Enum):
    FACT_LOOKUP, COMPLEX_REASONING, EXPLORATION, COMPARISON, DEFINITION

class QueryTypeClassifier:
    def classify(query) -> QueryType
    def get_confidence(query) -> float
    def get_keyword_counts(query) -> dict
```

### 8.4 SELF-RAG 子模块

| 模块 | 功能 |
|------|------|
| `score_parser.py` | LLM分数解析器 |
| `document_evaluator.py` | 文档相关性/有用性评估 |
| `answer_generator.py` | 基于文档的答案生成 |
| `dynamic_planner.py` | 动态规划器 |
| `self_rag_controller.py` | SELF-RAG控制器 |
| `cross_encoder_reranker.py` | 交叉编码重排 |
| `iterative_retriever.py` | 迭代检索 |

---

## 9. 订阅管理 - P1

### 9.1 订阅配置

```python
class Subscription:
    user_id: str
    keywords: List[str]          # 订阅关键词
    sources: List[str]           # 数据源
    frequency: str               # daily, weekly, monthly
    channels: List[str]         # email, slack, feishu
    output_format: str           # json, markdown, html
    max_papers: int              # 每次推送最大论文数
    enabled: bool                # 是否启用
```

### 9.2 推送渠道

| 渠道 | 说明 | 优先级 |
|------|------|--------|
| Email | 邮件HTML模板 | P0 |
| Slack | Slack机器人 | P1 |
| 飞书 | 飞书机器人 | P1 |
| 钉钉 | 钉钉机器人 | P1 |
| Webhook | 自定义HTTP回调 | P1 |
| RSS | RSS订阅源 | P2 |

---

## 10. 知识图谱

### 10.1 论文关系网络

```
KnowledgeGraph/
├── kg_builder.py         # 图谱构建
├── entity_extractor.py   # 实体抽取(作者/方法/数据集)
├── relation_extractor.py # 关系抽取
├── kg_query.py          # 图谱查询
└── kg_visualizer.py     # 图谱可视化
```

### 10.2 引用分析

```
CitationAnalysis/
├── citation_extractor.py # 引用提取
├── citation_ranker.py    # 引用重要性排序
├── citation_graph.py     # 引用网络
└── citation_recommender.py # 引用推荐
```

### 10.3 功能

| 功能 | 说明 |
|------|------|
| 引用关系图 | 论文A引用B / A被B引用 |
| 方法演进图 | 方法A→方法B→方法C演进 |
| 作者合作网络 | 共同署名关系、机构合作 |

---

## 11. 系统集成 - P1

### 11.1 API端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/search` | POST | 论文搜索 |
| `/api/reports/daily` | POST | 每日报告 |
| `/api/reports/weekly` | POST | 每周报告 |
| `/api/reports/monthly` | POST | 每月报告 |
| `/api/outline` | POST | 大纲生成 |
| `/api/draft` | POST | 初稿撰写 |
| `/api/revise` | POST | 论文修改 |
| `/api/polish` | POST | 语言润色 |
| `/api/review` | POST | 质量评审 |
| `/api/subscriptions` | GET/POST | 订阅管理 |

### 11.2 MCP模块

```
src/agents_v2/mcp/
├── __init__.py
└── client.py               # MCP客户端、连接池
```

| 类 | 功能 | 测试 |
|----|------|------|
| `MCPClient` | MCP协议客户端 | ✅ |
| `MCPClientPool` | MCP客户端池 | ✅ |
| `MCPConnectionState` | 连接状态枚举 | ✅ |
| `MCPMessage` | MCP消息结构 | ✅ |

### 11.3 前端集成 - P2

| 集成 | 说明 |
|------|------|
| Web Dashboard | 订阅管理、报告查看、搜索界面 |
| VS Code插件 | IDE中查看论文摘要 |
| 浏览器插件 | arXiv页面显示摘要，一键收藏 |

---

## 12. 企业功能 - P2

### 12.1 多用户支持

| 功能 | 说明 |
|------|------|
| 用户管理 | 用户组/团队功能 |
| 共享订阅 | 团队主题订阅 |
| 权限管理 | 管理员/普通用户 |

### 12.2 协作功能

| 功能 | 说明 |
|------|------|
| 论文讨论区 | 团队论文讨论 |
| 共享笔记 | 阅读笔记共享 |
| 报告分享 | 团队报告分享 |

### 12.3 部署选项

| 部署 | 说明 |
|------|------|
| SaaS | 云服务版本 |
| Docker | Docker镜像 |
| Kubernetes | K8s集群 |
| 单机版 | 个人使用 |

---

## 13. 迭代计划

### Iteration 1-3: 核心功能 ✅

| 功能 | 状态 | 文件 |
|------|------|------|
| DailyWatcher 每日监控 | ✅ 已实现 | `qa/daily_watcher.py` |
| WeeklyReportGenerator 周报 | ✅ 已实现 | `qa/weekly_report.py` |
| MonthlyReportGenerator 月报 | ✅ 已实现 | `qa/monthly_report.py` |
| PaperSearchAgent 多源搜索 | ✅ 已实现 | `qa/paper_search.py` |
| 统一报告输出格式 | ✅ 已实现 | 各报告Agent统一JSON输出 |
| 定时调度集成 | ✅ 已实现 | `scheduler/report_scheduler.py` |

### Iteration 4-6: 写作与修改

| 功能 | 状态 | 说明 |
|------|------|------|
| SmartReviserAgent 智能改稿 | ✅ 已实现 | `writing/smart_reviser.py` |
| ReportRefinerAgent 多轮精炼 | ✅ 已实现 | `writing/report_refiner.py` |
| LanguagePolisherAgent 润色 | ✅ 已实现 | `writing/smart_reviser.py` |
| 大纲生成完善 | ✅ 已实现 | `writing/outline_generator.py` |
| 初稿生成完善 | ✅ 已实现 | `writing/draft_generator.py` |
| 文献综述优化 | ✅ 已实现 | `writing/literature_review.py` |

### Iteration 7-8: 订阅与增强 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| 论文快讯 PaperFlash | ✅ 已实现 | `qa/paper_flash.py` |
| 多渠道推送 | ✅ 已实现 | `notification/push_service.py` |
| 用户订阅管理 | ✅ 已实现 | `scheduler/subscription_manager.py` |
| 定时调度器 | ✅ 已实现 | `scheduler/report_scheduler.py` |
| 搜索结果缓存 | ✅ 已实现 | `cache/report_cache.py` |

### Iteration 9-10: 企业与智能 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| 知识图谱 | 🚧 开发中 | 需基于现有knowledge_graph模块扩展 |
| 多用户支持 | ✅ 已实现 | `team/team_manager.py` |
| 推荐系统 | ✅ 已实现 | `recommendation/paper_recommender.py` |
| 趋势预测 | ✅ 已实现 | 推荐系统中的trending功能 |

---

## 14. 测试覆盖

### 14.1 测试覆盖总汇

| 模块 | 小模块数 | 测试数 |
|------|----------|--------|
| Search (搜索) | 6 | 40 |
| Retrieval (检索) | 16 | 350+ |
| PDF解析 | 8 | 60+ |
| Personalization | 5 | 50 |
| Production | 3 | 43 |
| Multimodal | 6 | 38 |
| MultiAgent | 4 | 33 |
| Evaluation | 15 | 80+ |
| Routing | 7 | 40+ |
| Writing | 10 | 50+ |
| MCP | 4 | 25 |
| Tools | 5 | 35+ |
| **总计** | **89** | **840+** |

### 14.2 Search模块测试

| 文件 | 测试数 |
|------|--------|
| `test_search.py` | 14 |
| `test_query_parser.py` | 26 |

### 14.3 Retrieval模块测试

| 文件 | 测试数 |
|------|--------|
| `test_keyword_sets.py` | 16 |
| `test_priority_matcher.py` | 14 |
| `test_confidence_calculator.py` | 14 |
| `test_query_classifier.py` | 51 |
| `test_score_parser.py` | 12 |
| `test_document_evaluator.py` | 15 |
| `test_answer_generator.py` | 13 |
| `test_dynamic_planner.py` | 21 |
| `test_self_rag_controller.py` | 19 |
| `test_cross_encoder_reranker.py` | 22 |
| `test_iterative_retriever.py` | 23 |
| `test_query_rewriter.py` | 14 |
| `test_query_expander.py` | 14 |

### 14.4 PDF解析模块测试

| 小模块 | 功能 | 测试 |
|--------|------|------|
| `citation_extractor.py` | 提取[1][1,2][1-3]格式引用 | 12 |
| `reference_parser.py` | 解析参考文献条目 | 6 |
| `section_parser.py` | 解析论文章节 | 7 |
| `metadata_parser.py` | 提取标题/作者/摘要/DOI | 6 |
| `pdf_parser.py` | PDF解析器 | 11 |

### 14.5 精细化原则

1. **数据与逻辑分离**: `keyword_sets.py` 只定义数据，`priority_matcher.py` 只处理匹配
2. **单一职责**: 每个文件只做一件事
3. **可独立测试**: 每个小模块都有对应的测试文件
4. **可组合使用**: 父模块组合子模块，子模块可独立使用
5. **工厂模式**: `SearchFactory` 统一管理多个搜索器

### 14.6 模块细化程度

| 层级 | 示例 | 说明 |
|------|------|------|
| L1 | `arxiv_searcher.py` | 整个arXiv搜索 |
| L2 | `arxiv_api.py`, `arxiv_parser.py` | API调用 + 结果解析分离 |
| L3 | `arxiv_api.py` → `request.py`, `retry.py`, `rate_limit.py` | 进一步拆分 |
| L4 | `request.py` → `http_client.py`, `headers.py` | 更细粒度 |

**当前细化程度**: 大部分模块在L1-L2，可继续深究到L3-L4

---

## 附录

### A. 搜索关键词示例

```python
# 统计学习
STAT_LEARNING_KEYWORDS = [
    "statistical learning",
    "causal inference",
    "bayesian methods",
    "machine learning",
    "time series analysis"
]

# 深度学习
DEEP_LEARNING_KEYWORDS = [
    "deep learning",
    "neural network",
    "transformer",
    "large language model",
    "computer vision"
]
```

### B. 方法关键词库

```python
METHOD_KEYWORDS = [
    "markov chain monte carlo", "mcmc",
    "bayesian inference",
    "neural network", "deep learning",
    "reinforcement learning",
    "supervised learning", "unsupervised learning",
    "semi-supervised learning",
    "transfer learning", "meta learning",
    "attention mechanism",
    "graph neural network",
    "diffusion model",
    "generative model",
    "variational inference"
]
```

### C. 性能要求

| 指标 | 日报 | 周报 | 月报 | 搜索 |
|------|------|------|------|------|
| 生成时间 | < 60秒 | < 180秒 | < 300秒 | < 5秒 |
| 论文处理量 | 50篇 | 200篇 | 500篇 | 10-50篇 |
| 并发搜索数 | - | - | - | 10个/秒 |

### D. 错误处理

| 场景 | 处理策略 |
|------|---------|
| LLM调用失败 | 返回降级报告（结构化但缺少分析） |
| JSON解析失败 | 返回原始文本+备用结构 |
| 搜索超时 | 跳过超时源，使用其他源 |
| 无论文结果 | 返回空报告+提示信息 |

### E. 参考系统

| 系统 | 参考点 |
|------|--------|
| arXiv Daily Digest | 论文精选逻辑 |
| Connected Papers | 关系图谱可视化 |
| Semantic Scholar | AI增强搜索、TLDR生成 |
| ResearchGate | 用户订阅、推荐系统 |
| Papers with Code | 论文+代码关联 |
| Jenni.ai | AI写作辅助 |
| SciSpace Copilot | 论文阅读助手 |

---

*最后更新: 2026-04-27*
