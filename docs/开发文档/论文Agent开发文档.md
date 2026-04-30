# 论文Agent开发文档

> 智能论文调研与写作系统 - 完整技术文档（融合需求 + 架构 + 实现）

版本: 6.2
更新日期: 2026-05-01
状态: ✅ 迭代完成（协议生态 + 最新模型 已更新）

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

---

## 附录C：Agent开发最佳实践


### 1.1 简单性优先 (from Anthropic)

> "最成功的 LLM Agent 实现不使用复杂框架，而是构建简单、可组合的模式。"

**实践建议**：
- 优先选择简单的单Agent方案
- 仅在必要时增加多Agent复杂性
- 直接使用LLM API，避免不必要的抽象层

### 1.2 Workflow vs Agent

| 类型 | 定义 | 适用场景 |
|------|------|----------|
| **Workflow** | 预定义代码路径协调LLM和工具 | 任务明确、需要可预测性 |
| **Agent** | LLM动态指导流程和工具使用 | 复杂开放、需要灵活性 |

### 1.3 何时使用Agent

需要Agent的场景：
- 复杂开放问题，步骤不可预测
- 需要模型驱动决策
- 需要自主性和扩展性

考虑因素：
- **延迟成本**：Agent通常增加延迟
- **错误传播**：Agent灵活性带来的错误风险

---

## 二、设计模式

### 2.1 五大Workflow模式

#### 1. Prompt Chaining (提示链)
```
Task → LLM1 → LLM2 → LLM3 → Output
```
将任务分解为多步骤，每步依赖前一步输出。

**适用**：需要高准确性的任务
**注意**：避免过长链，保持简洁

#### 2. Routing (路由)
```
Input → Classifier → Expert1/Expert2/Expert3 → Output
```
根据输入类型分流到不同专家Agent。

**适用**：任务类型明确的场景

#### 3. Parallelization (并行化)
```
Task → [Agent1] [Agent2] [Agent3] → Aggregator → Output
```
多个Agent并行处理，结果聚合。

**适用**：子任务独立、结果可合并

#### 4. Orchestrator-Workers (编排器-工作者)
```
Orchestrator → Dynamic Task Assignment → Workers → Synthesize
```
编排器动态分解任务，分配给Worker，结果汇总。

**适用**：复杂不可预测任务

#### 5. Evaluator-Optimizer (评估-优化循环)
```
Draft → Evaluator → [Optimizer] → Draft' → ... → Output
```
循环评估和改进，直到达标。

**适用**：有明确质量标准的任务

### 2.2 Agent架构组件

```
Agent = LLM + Memory + Planning + Tools + Protocol

增强型LLM (Augmented LLM)：
├── 检索 (Retrieval): GraphRAG 2.0 + 混合检索 + Self-RAG
├── 工具 (Tools): MCP 协议标准化工具调用
├── 记忆 (Memory): Mem0/Letta 风格多层记忆
├── 协议 (Protocol): MCP(工具) + A2A(Agent间通信) + Skills(能力模块)
└── 协作 (Collaboration): Subagents + Agent-to-Agent
```

### 2.3 2026 年 LLM 模型选择矩阵

| 任务类型 | 推荐模型 | 备选模型 | 选择理由 |
|---------|---------|---------|---------|
| 问题路由/分类 | DeepSeek-V3 / Haiku 4.5 | GPT-4o-mini | 低成本、低延迟 |
| 论文搜索/查询 | Claude Sonnet 4.6 | Gemini 3.1 Flash | 平衡质量与成本 |
| 论文深度分析 | Claude Opus 4.7 | DeepSeek-R1 | 最强推理，200K上下文 |
| 论文初稿写作 | Claude Opus 4.7 | DeepSeek-V3 | 长文本质量最高 |
| 数学推理 | DeepSeek-R1 | Qwen 3.5-Math | R1 强化推理，AIME 79.8% |
| 中文内容处理 | Qwen 3.5-Max | DeepSeek-V3 | 中文能力顶级 |
| 图表/图像理解 | Gemini 3.1 Pro | Claude Opus 4.7 | 原生多模态 |
| 论文润色/格式检查 | DeepSeek-V3 / Haiku 4.5 | GPT-4o | 简单任务低成本 |

### 2.4 Agent 协议生态系统

Paper Agent 基于 2026 年四大开放协议标准构建：

| 协议 | 解决的问题 | Paper Agent 中的应用 |
|------|-----------|-------------------|
| **MCP** (Anthropic) | Agent ↔ 工具/数据源 标准化连接 | Arxiv/PubMed/Semantic Scholar MCP Server |
| **A2A** (Google/Linux基金会) | Agent ↔ Agent 标准通信 | 搜索Agent→分析Agent→写作Agent 任务分发 |
| **Agent Skills** (Anthropic) | 能力模块化封装与复用 | paper-search/paper-analysis/report-generation |
| **AG-UI** (CopilotKit) | Agent ↔ 前端 实时交互 | 流式展示搜索进度、生成进度 |

---

## 三、关键实践

### 3.1 工具设计 (Tool Design)

**核心原则**：像为团队初级开发者编写文档一样投入精力

工具设计检查清单：
- [ ] 清晰的函数名和描述
- [ ] 明确的输入/输出类型
- [ ] 详细的参数说明
- [ ] 错误处理和边界情况
- [ ] 使用示例

### 3.2 状态管理

**LangGraph状态管理模式**：
```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    current_phase: str
    context: dict
```

关键点：
- 显式状态转移
- 中间状态隔离异常
- 可视化状态流

### 3.3 错误处理

#### 熔断器模式 (Circuit Breaker)
```
CLOSED → (失败阈值) → OPEN
OPEN → (超时恢复) → HALF_OPEN
HALF_OPEN → (成功) → CLOSED
HALF_OPEN → (失败) → OPEN
```

#### 降级策略 (Fallback)
- 使用默认/缓存结果
- 跳过可选阶段
- 返回最小可用输出

#### 重试策略 (Retry)
```python
RetryPolicy(
    max_retries=3,
    initial_delay=1.0,
    exponential_base=2.0,
    max_delay=60.0
)
```

---

## 四、Multi-Agent系统挑战

### 4.1 常见失败原因 (from "Why Do Multi-Agent LLM Systems Fail")

1. **任务分配不当**
   - Agent能力与任务不匹配
   - 依赖关系不明确

2. **通信失败**
   - 信息传递丢失
   - 上下文理解偏差

3. **协调问题**
   - 冲突解决机制缺失
   - 全局状态不一致

### 4.2 解决方案

| 问题 | 解决策略 |
|------|---------|
| 任务分配 | 清晰的Agent能力定义 + 路由机制 |
| 通信失败 | 结构化消息格式 + 确认机制 |
| 协调问题 | 全局状态管理 + 冲突解决策略 |

---

## 五、质量保证

### 5.1 Validation Gate

每个阶段的质量门控：
```python
PHASE_GATES = {
    "research": {"min_papers": 10, "min_relevance": 0.6},
    "analysis": {"min_themes": 3, "min_gaps": 1},
    "writing": {"min_sections": 5, "min_coherence": 0.7}
}
```

### 5.2 迭代改进机制

```
Phase Output → Reflection → Quality Check → Pass/Fail
                              ↓
                    Fail → Improve → Re-check
```

### 5.3 评估指标

| 维度 | 指标 |
|------|------|
| 准确性 | 任务完成率、错误率 |
| 效率 | 延迟、token消耗 |
| 稳定性 | 失败率、恢复时间 |
| 一致性 | 输出质量方差 |

---

## 六、反模式 (避免)

1. **过度工程化**
   - 不必要的抽象层
   - 过复杂的状态机

2. **框架依赖**
   - 用框架掩盖底层问题
   - 不理解框架内部机制

3. **缺乏监控**
   - 不知道Agent在做什么
   - 错误难以追踪

4. **忽视成本**
   - 无限循环调用
   - 不必要的Agent调用

---

## 七、实施检查清单

### 开始前
- [ ] 明确是否真的需要Multi-Agent
- [ ] 定义清晰的Agent能力边界
- [ ] 设计消息传递协议

### 开发中
- [ ] 从简单模式开始
- [ ] 每个工具都有完整文档
- [ ] 实现错误处理和降级
- [ ] 保持状态可观测

### 完成后
- [ ] 测试各种失败场景
- [ ] 测量延迟和成本
- [ ] 验证输出质量
- [ ] 文档化Agent行为

---

## 八、特定领域Agent指南

### 8.0 框架概述

本框架融合两种Agent设计范式：

| 范式 | 特点 | 适用场景 |
|------|------|---------|
| **Pipeline型** | 流程清晰、顺序执行、质量稳定 | 选题、文献、大纲、撰写等线性流程 |
| **问题导向型** | 针对性强、精准解决问题 | 诊断、修复、润色等非确定性任务 |

**融合后的三阶段流程**：
```
诊断阶段 → 问题导向Agent并行诊断
    ↓
执行阶段 → Pipeline型Agent顺序执行
    ↓
完善阶段 → 问题导向Agent针对性修复
```

---

### 8.1 论文写作Agent体系架构

#### 论文Agent Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                        论文写作Agent Pipeline                        │
└─────────────────────────────────────────────────────────────────────┘

┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐
│   Topic   │───▶│Literature │───▶│  Thesis   │───▶│  Outline  │
│   Agent   │    │   Agent   │    │   Agent   │    │   Agent   │
└───────────┘    └───────────┘    └───────────┘    └───────────┘
      │                                      │
      │    ┌───────────┐    ┌───────────┐    │
      └───▶│  Writer   │───▶│  Review   │───┘
           │   Agent   │    │   Agent   │
           └───────────┘    └───────────┘
                  │
           ┌───────────┐
           │  Editor   │
           │   Agent   │
           └───────────┘
```

#### Agent职责定义

| Agent | 核心职责 | 输出 |
|-------|---------|------|
| **TopicAgent** | 主题选择与研究问题凝练 | 候选主题、研究问题 |
| **LiteratureAgent** | 文献搜索、筛选、深度分析 | 论文列表、研究空白 |
| **ThesisAgent** | 研究动机、目标、假设凝练 | Thesis Statement |
| **OutlineAgent** | 论文结构设计 | 大纲、章节规划 |
| **WriterAgent** | 各章节撰写 | 初稿内容 |
| **ReviewerAgent** | 质量审查与反馈 | 评审意见 |
| **EditorAgent** | 整合修改、最终润色 | 定稿 |

---

### 8.2 论文Agent设计原则

#### 学术严谨性原则

论文Agent必须遵循：
- **引用准确性**：确保所有引用可溯源
- **逻辑严密性**：论点推导有据可依
- **方法科学性**：研究方法符合学术规范
- **格式规范性**：符合目标期刊/会议要求

#### 领域适配原则

不同的研究领域有不同的写作范式：

```python
DOMAIN_CONFIGS = {
    "cs": {
        "structure": ["Abstract", "Introduction", "Related Work", "Method", "Experiment", "Conclusion"],
        "citation_style": "ACM/IEEE",
        "emphasis": ["性能指标", "算法创新", "实验验证"]
    },
    "medical": {
        "structure": ["Abstract", "Background", "Methods", "Results", "Discussion"],
        "citation_style": "Vancouver",
        "emphasis": ["统计显著性", "样本量", "伦理审批"]
    },
    "social_science": {
        "structure": ["Abstract", "Introduction", "Literature Review", "Methodology", "Findings", "Discussion"],
        "citation_style": "APA",
        "emphasis": ["理论框架", "质性分析", "研究伦理"]
    }
}
```

#### 迭代优化原则

论文写作是迭代过程，每个阶段都应有反馈机制：

```
Phase Output → Self-Review → Quality Gate → Pass/Revise
                    ↓
              Revise → Re-review → ...
```

---

### 8.3 论文Agent实现规范

#### 基类继承结构

```python
# 标准论文Agent实现模板
from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig
from typing import Any, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)


class YourAgentName(PaperAgentBase):
    """
    [Agent名称] - [简短描述]

    职责：
    - [职责1]
    - [职责2]
    - [职责3]
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个[领域]专家。
你的职责是：
1. [具体职责1]
2. [具体职责2]
3. [具体职责3]

请确保：
- [质量要求1]
- [质量要求2]"""
        super().__init__(
            name="your_agent_name",
            llm_config=llm_config,
            description="Agent描述",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """执行主任务"""
        # 1. 输入验证
        # 2. 核心逻辑
        # 3. 结果组装
        # 4. 质量评估
        pass
```

#### 标准输入输出格式

**输入格式 (AgentInput)**：
```python
{
    "task_type": "literature_review",      # 任务类型
    "task_description": "关于XX的研究",    # 任务描述
    "input_data": {                         # 任务特定数据
        "topic": "机器学习优化",
        "keywords": ["深度学习", "优化算法"]
    },
    "context": {                            # 执行上下文（上游结果）
        "thesis_statement": "...",
        "literature_result": {...}
    },
    "requirements": [                       # 特殊需求
        "需要包含近3年文献",
        "优先顶级会议论文"
    ],
    "metadata": {                           # 元数据
        "academic_level": "硕士",
        "target_journal": "CVPR"
    }
}
```

**输出格式 (AgentOutput)**：
```python
{
    "success": True,
    "result": {                            # 执行结果
        "key_field": "value"
    },
    "agent_name": "your_agent",
    "reasoning": "为什么输出这个结果",       # 推理过程说明
    "next_actions": ["suggested_next"],    # 建议的后续操作
    "quality_score": 0.85,                 # 质量评分 (0-1)
    "metadata": {                          # 额外信息
        "papers_analyzed": 20,
        "time_spent": "30s"
    }
}
```

#### 论文Agent质量门控

```python
QUALITY_GATES = {
    "topic_agent": {
        "min_candidates": 3,
        "min_feasibility_score": 0.6,
        "required_fields": ["title", "description", "scope"]
    },
    "literature_agent": {
        "min_papers": 10,
        "min_relevance_threshold": 0.5,
        "required_gaps": 2
    },
    "thesis_agent": {
        "required_fields": ["thesis_statement", "research_objectives"],
        "min_objectives": 3,
        "coherence_score_threshold": 0.7
    },
    "outline_agent": {
        "min_chapters": 5,
        "required_sections": ["Introduction", "Method", "Conclusion"]
    },
    "writer_agent": {
        "min_word_count": 500,
        "required_citations": 3,
        "coherence_check": True
    }
}
```

---

### 8.4 核心论文Agent详细设计

#### TopicAgent (主题选择)

工作流程：`领域分析 → 候选主题生成 → 可行性评估 → 最佳选择`

**关键设计点**：
- 多候选原则：生成多个候选而非单一主题
- 可行性评估：文献充足性、方法可行性、创新性、时间合理性
- 风险提示：识别潜在风险因素

#### LiteratureAgent (文献工作)

工作流程：`多角度查询生成 → 多源搜索 → 质量排序 → 深度分析 → Gap识别`

**关键设计点**：
- 并行搜索：利用Semaphore控制并发
- 去重机制：基于title去重
- 深度分析：提取core_problem, methodology, findings, limitations

#### ThesisAgent (研究凝练)

工作流程：`文献分析 → 研究动机 → 研究目标 → 研究范围 → Thesis Statement`

#### OutlineAgent (大纲设计)

工作流程：`结构设计 → 章节规划 → 关键论点识别`

#### WriterAgent (章节撰写)

```python
class WriterAgent(PaperAgentBase):
    """
    各章节撰写

    职责：
    - 根据大纲撰写各章节
    - 融入文献引用
    - 保持风格一致性
    """

    async def execute_section(self, section_type, outline, context):
        """撰写单个章节"""
        templates = {
            "introduction": self._write_introduction,
            "related_work": self._write_related_work,
            "methodology": self._write_methodology,
            "experiment": self._write_experiment,
            "conclusion": self._write_conclusion
        }
        writer = templates.get(section_type, self._write_generic)
        return await writer(outline, context)
```

#### ReviewerAgent (质量审查)

审查维度：逻辑连贯性、论据充分性、引用准确性、格式规范性、创新性评估

#### EditorAgent (整合编辑)

职责：整合各章节、统一风格格式、语言润色、最终检查

---

### 8.5 论文Agent间协作规范

#### Context传递协议

```python
# Pipeline执行时的context流动
context = {
    # Stage 1: Topic
    "user_request": "用户的研究意向",
    "selected_topic": {...},

    # Stage 2: Literature (receives topic from context)
    "topic": context["selected_topic"]["title"],
    "literature_result": {...},

    # Stage 3: Thesis (receives topic + literature from context)
    "literature_result": context["literature_result"],
    "thesis_result": {...},

    # Stage 4: Outline (receives thesis + literature from context)
    "thesis_statement": context["thesis_result"]["thesis_statement"],
    "literature_result": context["literature_result"],
    "outline_result": {...}
}
```

#### 错误传播与恢复

```python
ERROR_STRATEGIES = {
    "topic_agent": {
        "fallback": "使用用户原始请求作为主题",
        "retry": True,
        "max_retries": 2
    },
    "literature_agent": {
        "fallback": "返回已有缓存文献或空列表",
        "retry": True,
        "max_retries": 3
    },
    "thesis_agent": {
        "fallback": "生成通用Thesis Statement",
        "retry": False  # 需要真实的文献分析
    }
}
```

#### 质量验收标准

| Agent | 最低质量分 | 必须满足的条件 |
|-------|----------|--------------|
| TopicAgent | 0.6 | 至少3个候选主题，主题可执行 |
| LiteratureAgent | 0.5 | 至少10篇论文，至少2个研究空白 |
| ThesisAgent | 0.7 | 有Thesis Statement，至少3个目标 |
| OutlineAgent | 0.7 | 至少5章，核心章节齐全 |

---

### 8.6 论文Agent开发检查清单

#### 新Agent开发
- [ ] 明确Agent职责（单一职责原则）
- [ ] 设计System Prompt（角色定义 + 质量要求）
- [ ] 定义输入输出格式
- [ ] 实现主execute方法
- [ ] 实现子步骤方法（私有方法）
- [ ] 添加错误处理和fallback
- [ ] 设置质量评分
- [ ] 编写单元测试

#### Pipeline集成
- [ ] 定义context传递结构
- [ ] 配置上游依赖
- [ ] 设置质量门控阈值
- [ ] 实现错误传播
- [ ] 添加日志记录

#### 质量保证
- [ ] 每个Agent有自检机制
- [ ] 输出包含quality_score
- [ ] 不满足质量标准时有明确反馈
- [ ] 支持迭代改进

---

### 8.7 统一框架架构

#### 架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MasterSupervisor                                │
│                    (全局状态管理 + 路由决策)                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
    ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
    │   Diagnostic   │     │   Pipeline    │     │   Problem     │
    │   Phase        │     │   Phase       │     │   Solving     │
    └───────────────┘     └───────────────┘     └───────────────┘
            │                       │                       │
            ▼                       ▼                       ▼
    TopicRefiner              TopicAgent              ArgumentBuilder
    LiteratureMapper          LiteratureAgent         SectionDiff
    MethodologyAdvisor        ThesisAgent            DiscussionDeepener
                               OutlineAgent           ChartFormatter
                               DraftWriterAgent      LanguagePolisher
                               EditorAgent            PlagiarismChecker
                               ReviewerAgent
```

#### 核心组件

**MasterSupervisor**：全局协调器
- 管理全局状态 (PaperState)
- 路由到正确的PhaseSupervisor
- 处理阶段间的流转
- 协调诊断-执行-完善流程

**PhaseSupervisor**：单阶段协调器
- 调度阶段内的多个Agent
- 聚合Agent结果
- 评估阶段质量
- 决定是否需要诊断修复

支持三种执行模式：
- **parallel**: 并行执行（诊断阶段）
- **sequential**: 顺序执行（选题、文献阶段）
- **adaptive**: 自适应执行（根据结果动态决定）

**PaperState**：全局状态管理
```python
@dataclass
class PaperState:
    user_request: str
    current_phase: str
    phase_sequence: List[str]
    phase_results: Dict[str, PhaseResult]
    problems: List[ProblemType]
    problem_severity: Dict[ProblemType, float]
    iteration: int
    quality_history: List[QualityScore]
```

#### 完整论文流程 (full_paper)

```
用户输入
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│                     1. 诊断阶段 (Diagnostic)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │TopicRefiner │  │LiteratureMap │  │Methodology   │         │
│  │  Agent      │  │   Agent      │  │  Advisor     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│              (并行)                                              │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│                     2. 选题阶段 (Topic)                        │
│                      TopicAgent                                 │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│                     3. 文献阶段 (Literature)                   │
│                    LiteratureAgent                              │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│                     4. 方法阶段 (Methodology)                   │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │Methodology   │  │  Argument    │                            │
│  │  Advisor     │  │  Builder     │                            │
│  └──────────────┘  └──────────────┘                            │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│                     5. 写作阶段 (Writing)                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │ Thesis  │→│ Outline │→│  Draft  │→│ Editor  │           │
│  │ Agent   │  │ Agent   │  │ Writer  │  │ Agent   │           │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘           │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│                     6. 完善阶段 (Polish)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ChartFormat  │  │  Language    │  │  Plagiarism  │         │
│  │   Agent     │  │  Polisher    │  │  Checker     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│                     最终输出                                    │
│              符合学术规范的论文                                  │
└────────────────────────────────────────────────────────────────┘
```

#### 诊断-治疗模式

```
发现问题 ──→ 诊断 ──→ 治疗 ──→ 验证

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Pipeline   │────▶│  Diagnostic │────▶│  Problem    │
│   执行      │     │    诊断     │     │   修复      │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                   ┌─────────────────┐
                   │  发现问题列表   │
                   │  ProblemType    │
                   └─────────────────┘
```

#### 迭代改进机制

```
┌──────────────────────────────────────────┐
│            质量检查                       │
│  quality_score < threshold?              │
└──────────────────────────────────────────┘
            │
    Yes     │     No
    ▼       │       ▼
┌───────────┐    ┌──────────┐
│  迭代     │    │  下一阶段 │
│  修复     │    └──────────┘
└───────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│     iteration < max_iterations?          │
└──────────────────────────────────────────┘
            │
    Yes     │     No
    ▼       │       ▼
┌───────────┐    ┌──────────┐
│  重试     │    │  降级/结束│
└───────────┘    └──────────┘
```

#### 问题类型映射

| ProblemType | 对应Agent | 修复策略 |
|------------|----------|---------|
| TOPIC_VAGUE | TopicRefinerAgent | 明确研究范围 |
| TOPIC_TOO_BROAD | TopicRefinerAgent | 缩小选题 |
| LITERATURE_INSUFFICIENT | LiteratureMapperAgent | 扩大文献搜索 |
| ARGUMENT_WEAK | ArgumentBuilderAgent | 重构论证框架 |
| DISCUSSION_SHALLOW | DiscussionDeepenerAgent | 深化讨论 |
| LANGUAGE_POOR | LanguagePolisherAgent | 语言润色 |
| PLAGIARISM_RISK | PlagiarismCheckerAgent | 改写建议 |

#### 与旧框架的关系

| 旧模块 | 新框架中的位置 | 说明 |
|--------|---------------|------|
| paper_agent.py | Pipeline Phase | 单一Agent模式，重组为PhaseSupervisor |
| paper_agents/ | Pipeline Agents | TopicAgent, LiteratureAgent等 |
| problem_oriented/ | Problem-Solving Agents | 9个针对性Agent |
| supervisor/ | PhaseSupervisor + MasterSupervisor | 协调机制融合 |

#### 扩展点

1. **新增Agent类型**: 在对应模块实现后注册到MasterSupervisor
2. **自定义流程**: 通过_run_custom_flow扩展
3. **自定义质量评估**: 继承PhaseSupervisor重写_evaluate_quality
4. **自定义路由**: 继承MasterSupervisor重写RoutingPolicy

---

## 九、参考资源

- Anthropic: [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- Anthropic: [Claude Agent SDK](https://docs.anthropic.com/en/docs/agent-sdk)
- Google: [A2A Protocol](https://github.com/google/A2A)
- Agent Skills: [agentskills.io](https://agentskills.io/)
- MCP: [Model Context Protocol](https://modelcontextprotocol.io/)
- Microsoft: [GraphRAG](https://github.com/microsoft/graphrag)
- DeepSeek: [DeepSeek-R1 API](https://api.deepseek.com/)
- Microsoft: [AI Agents for Beginners](https://github.com/microsoft/ai-agents-for-beginners)
- LangGraph Documentation: [LangGraph](https://langchain.dev/langgraph)
- CrewAI: [Multi-Agent Architecture](https://github.com/crewAI/crewAI)
- 论文写作范式：各学科顶会/顶刊 guidelines (CVPR, NeurIPS, ACL, Nature, etc.)

---

## 附录：LangGraph工作流开发总结


### Phase 1: LangGraph 基础架构 ✅

**核心文件**：
- `src/agents_v2/langgraph_workflow/state.py` - 状态定义（PaperAgentState, Paper）
- `src/agents_v2/langgraph_workflow/workflow.py` - 工作流构建器（PaperAgentWorkflow）
- `src/agents_v2/langgraph_workflow/edges.py` - 条件路由逻辑
- `src/agents_v2/langgraph_workflow/runner.py` - CLI 运行入口

**Agent 节点**：
- `nodes/crawler.py` - 多源论文搜索 + 引用网络扩展 + 增强检索集成
- `nodes/selector.py` - 相关性评分 + Cross-Encoder 重排序
- `nodes/outline.py` - LLM/规则双模式大纲生成
- `nodes/writer.py` - 逐章节写作 + 文献引用整合
- `nodes/reviewer.py` - LLM/规则双模式审查 + 迭代控制

**工作流结构**：
```
[crawler] → [selector] → [outline] → [writing] → [review]
                                                    ↓
                                            (条件路由)
                                    ┌──────→ [writing] (需要修改)
                                    └──────→ [END]     (完成)
```

### Phase 2: 混合记忆 + 偏好学习 ✅

**核心文件**：
- `nodes/memory.py` - 记忆管理节点

**功能**：
1. **检索前召回**：从历史记忆中召回相关知识，增强查询上下文
2. **筛选后存储**：将高质量论文存入记忆系统（遗忘曲线 + 跨会话知识）
3. **个性化输出**：基于用户偏好生成个性化响应

### Phase 3: 多模态 + 知识图谱 ✅

**核心文件**：
- `nodes/multimodal.py` - 多模态节点（图表/公式识别）
- `nodes/knowledge_graph.py` - 知识图谱节点（实体抽取/关系构建）

**多模态功能**：
- 图表类型检测（折线图、柱状图、散点图、热力图、饼图）
- 公式识别提示
- 图文联合检索

**知识图谱功能**：
- 实体抽取（方法/模型/作者）
- 关系构建（作者-论文、论文-引用）
- 跨论文关联发现（共同作者、相似方法）

## 测试覆盖

### 单元测试（22 个）
- `tests/test_langgraph_workflow.py`
  - 状态定义测试（4 个）
  - 条件路由测试（4 个）
  - Agent 节点测试（5 个）
  - 记忆节��测试（3 个）
  - 多模态节点测试（2 个）
  - 知识图谱节点测试（4 个）

### 端到端测试（8 个）
- `tests/test_e2e_langgraph.py`
  - 完整工作流测试（无 LLM）
  - 完整工作流测试（模拟 LLM）
  - 记忆系统集成测试
  - 图编译测试
  - 迭代控制测试
  - 状态持久化测试
  - 性能测试（筛选器、大纲生成）

**测试结果**：25/25 全部通过 ✅

## 关键集成

### 1. SELF-RAG 增强检索
- CrawlerAgent 可选使用 `EnhancedRetrievalPipeline`
- 支持 Query 改写、扩展、Cross-Encoder 重排序、SELF-RAG

### 2. 记忆系统
- 集成 `EnhancedMemorySystem`（遗忘曲线 + 偏好学习）
- 支持检索前召回、筛选后存储、个性化输出

### 3. 多模态理解
- 集成 `VisionEncoder`（CLIP）、`ChartAnalyzer`、`FormulaRecognizer`
- 支持图表类型检测、公式识别提示

### 4. 知识图谱
- 集成 `KnowledgeGraphService`（可选）
- 支持实体抽取、关系构建、图推理查询

## 使用示例

### 基础使用
```python
from agents_v2.langgraph_workflow import create_workflow

# 创建工作流（无 LLM，使用规则生成）
workflow = create_workflow(
    llm=None,
    sources=["arxiv", "semantic_scholar"],
    top_k=20,
    max_iterations=3,
)

# 运行工作流
result = workflow.run(
    query="deep learning in medical imaging",
    user_id="user123",
    session_id="session456",
)

# 访问结果
papers = result["papers"]              # 搜索到的论文
selected = result["selected_papers"]   # 筛选后的论文
outline = result["outline"]            # 生成的大纲
draft = result["draft"]                # 撰写的草稿
```

### 高级使用（LLM + 增强检索 + 记忆）
```python
from langchain_openai import ChatOpenAI
from agents_v2.langgraph_workflow import create_workflow

llm = ChatOpenAI(model="gpt-4")

workflow = create_workflow(
    llm=llm,
    sources=["arxiv", "semantic_scholar"],
    top_k=20,
    max_iterations=3,
    enable_enhanced_retrieval=True,  # 启用 SELF-RAG
    retriever=your_retriever,         # 提供检索器
)

result = workflow.run(
    query="transformer architecture",
    user_id="user123",
    session_id="session456",
)
```

### CLI 使用
```bash
python -m src.agents_v2.langgraph_workflow.runner "deep learning"
```

### 演示脚本
```bash
python demo_langgraph_workflow.py
```

## 性能指标

- **筛选器**：100 篇论文 < 2 秒
- **大纲生成**：20 篇论文 < 1 秒
- **端到端工作流**：10 篇论文 → 5 篇筛选 → 6 节大纲 → 2719 字符草稿 < 3 秒（无 LLM）

## 下一步计划

### Phase 4: 评估 + 可观测性（未开始）
- LangSmith 集成
- Prometheus 指标
- AgentBench/GAIA 评估

### Phase 5: 生态 + 自动化（未开始）
- DSPy 自动 Prompt 优化
- 成本优化
- 生产部署

## 文件统计

| 类别 | 文件数 | 代码行数 |
|------|--------|----------|
| 核心工作流 | 4 | ~600 |
| Agent 节点 | 8 | ~1400 |
| 测试 | 2 | ~700 |
| 演示 | 1 | ~190 |
| **总计** | **15** | **~2890** |

## 依赖项

```bash
pip install langgraph langchain langchain-openai
pip install sentence-transformers  # 可选，用于 Cross-Encoder
pip install transformers torch      # 可选，用于 CLIP
pip install neo4j                   # 可选，用于知识图谱
```

## 参考文档
