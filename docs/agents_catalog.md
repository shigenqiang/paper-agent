# Agent 目录

本文档列出 `src/agents_v2` 目录下所有 Agent 的职责和能力。

> 更新时间：2026-05-02 | Agent 总数：40+
> 状态：✅ 与代码库一致

---

## Agent 架构体系

### 基类层级

```
BaseAgent (core/base_agent.py)
├── PaperAgentBase (paper_agents/base_paper_agent.py)
│   ├── TopicAgent
│   ├── LiteratureAgent
│   ├── ThesisAgent
│   ├── OutlineAgent
│   ├── DraftWriterAgent
│   ├── EditorAgent
│   ├── ReviewerAgent
│   └── DigestAgent
├── ProblemAgentBase (problem_oriented/base_problem_agent.py)
│   ├── TopicRefinerAgent
│   ├── LiteratureMapperAgent
│   ├── MethodologyAdvisorAgent
│   ├── ArgumentBuilderAgent
│   ├── SectionDifferentiatorAgent
│   ├── DiscussionDeepenerAgent
│   ├── ChartFormatterAgent
│   ├── PlagiarismCheckerAgent
│   ├── LanguagePolisherAgent
│   └── ResearchGapAgent (新增)
├── WritingAgentBase (writing/base_writing_agent.py)
│   ├── OutlineGeneratorAgent
│   ├── ProposalGeneratorAgent
│   ├── ReferenceProcessorAgent
│   ├── LiteratureReviewAgent
│   ├── DraftGeneratorAgent
│   ├── ReportRefinerAgent
│   ├── SmartReviserAgent
│   └── GenerationOptimizerAgent (新增)
└── BaseQAAgent (paper_search/base_qa_agent.py)
    └── PaperSearchAgent
```

---

## 1. PaperAgentBase 体系

继承自 `paper_agents/base_paper_agent.py`。所有论文写作流程 Agent 的基类。

### 1.1 OutlineAgent

**文件**: `paper_agents/outline_agent.py`

**职责**: 设计论文结构、规划各章节内容、确定关键论点

**主要方法**:
- `_design_structure()` - 设计章节结构
- `_plan_chapters()` - 规划各章节内容
- `_identify_key_arguments()` - 确定关键论点

**输入**: `topic`, `thesis`, `literature`
**输出**: 结构化大纲 JSON

---

### 1.2 ThesisAgent

**文件**: `paper_agents/thesis_agent.py`

**职责**: 分析文献综述、凝练研究动机、明确研究目标、定义研究范围、形成 Thesis Statement

**主要方法**:
- `_analyze_existing_research()` - 分析现有研究
- `_refine_motivation()` - 凝练研究动机
- `_define_objectives()` - 明确研究目标
- `_define_scope()` - 定义研究范围
- `_formulate_thesis()` - 形成 Thesis Statement
- `_formulate_hypotheses()` - 形成研究假设

**输入**: `topic`, `literature_result`
**输出**: `thesis_statement`, `research_motivation`, `research_objectives`, `scope`, `hypotheses`

---

### 1.3 DraftWriterAgent

**文件**: `paper_agents/draft_writer.py`

**职责**: 按大纲撰写各章节、保持内容连贯性、添加引用和参考文献

**主要方法**:
- `_write_introduction()` - 撰写引言
- `_write_literature_review()` - 撰写文献综述
- `_write_methodology()` - 撰写方法论
- `_write_results()` - 撰写结果
- `_write_discussion()` - 撰写讨论
- `_write_conclusion()` - 撰写结论
- `_compile_draft()` - 整合初稿

**特性**: 独立章节并行撰写，依赖章节顺序撰写

---

### 1.4 ReviewerAgent

**文件**: `paper_agents/reviewer_agent.py`

**职责**: 多视角 Critique、质量评估、决定是否通过

**评审视角**:
1. 学术专家视角 - 创新性、方法学、贡献
2. 审稿人视角 - 完整性、可读性、格式
3. 批判者视角 - 潜在问题、逻辑漏洞

**主要方法**:
- `_multi_perspective_review()` - 多视角审核
- `_calculate_quality_score()` - 计算质量评分
- `_generate_recommendations()` - 生成建议

**输入**: `paper`, `thesis`, `outline`
**输出**: `passed`, `quality_score`, `critiques`, `recommendation`

---

### 1.5 EditorAgent

**文件**: `paper_agents/editor_agent.py`

**职责**: 内容修订、语言润色、格式调整

**主要方法**:
- `_revise_content()` - 修订内容
- `_polish_language()` - 语言润色
- `_adjust_format()` - 格式调整
- `_summarize_revisions()` - 总结修订内容

---

### 1.6 TopicAgent

**文件**: `paper_agents/topic_agent.py`

**职责**: 分析研究领域、生成候选主题、评估可行性、凝练具体研究问题

**主要方法**:
- `_analyze_domain()` - 分析研究领域
- `_generate_topic_candidates()` - 生成候选主题
- `_evaluate_feasibility()` - 评估可行性
- `_select_best_topic()` - 选择最佳主题

**输出**: 包含 `selected_topic`, `alternative_topics`, `domain_analysis`, `feasibility_scores`

---

### 1.7 LiteratureAgent

**文件**: `paper_agents/literature_agent.py`

**职责**: 多源文献搜索、质量筛选、PDF 阅读与信息提取、识别研究空白

**主要方法**:
- `_generate_search_queries()` - 生成多角度搜索查询
- `_multi_engine_search()` - 多引擎并行搜索（使用真实 API）
- `_rank_papers()` - 排序论文
- `_deep_read()` - 深度阅读论文
- `_extract_paper_info()` - 提取论文关键信息
- `_identify_gaps()` - 识别研究空白

**搜索数据源**: arXiv, PubMed（通过 `PaperSearchAgent`）

---

### 1.8 DigestReportAgent

**文件**: `paper_agents/digest_agent.py`

**职责**: 生成学术资讯快报（日报/周报/月报）

**报告类型**:

| 类型 | 论文数 | 长度 | 结构 |
|------|--------|------|------|
| 日报 (daily) | 10-20 | 500-800字 | 今日热点 + 代表性论文 |
| 周报 (weekly) | 20-40 | 1000-1500字 | 本周概览 + 主题聚类 + 趋势分析 |
| 月报 (monthly) | 40-60 | 2000-3000字 | 月度概览 + 主题深度分析 + 前沿展望 |

**主要方法**:
- `_preprocess_papers()` - 预处理论文数据
- `_cluster_papers()` - 按研究主题聚类
- `_rank_papers()` - 排序论文
- `_generate_daily_report()` - 生成日报
- `_generate_weekly_report()` - 生成周报
- `_generate_monthly_report()` - 生成月报
- `_generate_fallback_report()` - 模板方式生成报告（LLM 失败时备选）

---

## 2. ProblemAgentBase 体系

继承自 `problem_oriented/base_problem_agent.py`。每个 Agent 针对论文写作中的一个具体困难：诊断问题、分析原因、提供改进建议。

### 2.1 TopicRefinerAgent

**文件**: `problem_oriented/topic_refiner.py`

**针对问题**: 选题太宽泛/缺乏创新/可行性低

**职责**: 分析初步想法、评估可行性、帮助优化选题、检查创新性

**主要方法**:
- `_analyze_initial_topic()` - 分析初步选题
- `_evaluate_feasibility()` - 评估可行性
- `_narrow_topic()` - 缩小选题范围
- `_check_originality()` - 检查创新性
- `_generate_refined_topic()` - 生成优化后的选题

---

### 2.2 ResearchGapAgent

**文件**: `problem_oriented/research_gap.py`

**针对问题**: 无法识别研究空白、文献综述不充分

**职责**: 全面搜索相关文献、分类整理现有研究、识别研究空白、生成文献地图

**主要方法**:
- `_search_literature()` - 搜索文献
- `_categorize_papers()` - 分类整理论文
- `_identify_gaps()` - 识别研究空白
- `_analyze_trends()` - 分析研究趋势
- `_generate_gap_report()` - 生成空白报告

---

### 2.3 MethodologyAdvisorAgent

**文件**: `problem_oriented/methodology_advisor.py`

**针对问题**: 研究方法不当、数据处理不严谨

**职责**: 推荐适合的研究方法、检查方法论严谨性、辅助统计/数据分析、识别方法漏洞

**主要方法**:
- `_recommend_methods()` - 推荐适合的方法
- `_evaluate_method()` - 评估提议方法
- `_check_rigor()` - 检查严谨性
- `_identify_problems()` - 识别潜在问题

---

### 2.4 ArgumentBuilderAgent

**文件**: `problem_oriented/argument_builder.py`

**针对问题**: 论证逻辑不严密、结构不清晰

**职责**: 帮助构建论证框架、检查逻辑连贯性、识别逻辑漏洞、强化论点支撑

**主要方法**:
- `_build_argument_framework()` - 构建论证框架
- `_check_coherence()` - 检查逻辑连贯性
- `_identify_logical_gaps()` - 识别逻辑漏洞
- `_evaluate_support()` - 评估论据支撑

---

### 2.5 SectionDifferentiatorAgent

**文件**: `problem_oriented/section_differentiator.py`

**针对问题**: 摘要与结论重复、内容缺乏差异化

**职责**: 检查摘要与结论差异、指导各章节差异化写作、确保内容不重复

**主要方法**:
- `_check_abstract_vs_conclusion()` - 检查摘要与结论差异
- `_check_section_differentiation()` - 检查各章节差异化
- `_identify_duplications()` - 识别重复内容
- `_define_section_purposes()` - 定义各章节定位

---

### 2.4 DiscussionDeepenerAgent

**文件**: `problem_oriented/discussion_deepener.py`

**针对问题**: 讨论部分薄弱、缺乏深度

**职责**: 指导深入讨论、帮助对比已有研究、识别局限性、提出未来方向

**主要方法**:
- `_assess_depth()` - 评估讨论深度
- `_guide_comparisons()` - 指导与已有研究对比
- `_identify_discussion_points()` - 识别需要讨论的要点
- `_guide_limitation_analysis()` - 指导局限性分析
- `_guide_future_directions()` - 指导未来方向

---

### 2.6 ChartFormatterAgent

**文件**: `problem_oriented/chart_formatter.py`

**针对问题**: 图表制作粗糙、格式不规范

**职责**: 检查图表规范性、优化信息呈现、标准化格式

**主要方法**:
- `_check_single_chart()` - 检查单个图表
- `_generate_recommendations()` - 生成规范化建议

---

### 2.7 PlagiarismCheckerAgent

**文件**: `problem_oriented/plagiarism_checker.py`

**针对问题**: 查重/原创性问题

**职责**: 识别高复制段落、提供改写建议、强化原创观点

**主要方法**:
- `_identify_high_risk()` - 识别高风险段落
- `_assess_originality()` - 评估整体原创性
- `_identify_improvement_points()` - 识别可改进之处
- `_generate_rewrite_suggestions()` - 生成改写建议

---

### 2.8 LanguagePolisherAgent

**文件**: `problem_oriented/language_polisher.py`

**针对问题**: 语言表达问题、语法错误

**职责**: 语法检查、学术语言规范、术语一致性

**诊断维度**:
- GRAMMAR_ERROR - 语法错误
- SPELLING_ERROR - 拼写错误
- PUNCTUATION_ERROR - 标点错误
- COLLOQUIALISM - 口语化表达
- SUBJECTIVITY - 主观性过强
- VERBOSITY - 冗余表达
- INCONSISTENCY - 术语不一致
- LOGIC_BREAK - 逻辑断裂

**严重程度**: HIGH (0.8-1.0), MEDIUM (0.4-0.7), LOW (0.1-0.3)

---

### 2.9 LiteratureMapperAgent

**文件**: `problem_oriented/literature_mapper.py`

**针对问题**: 文献综述不充分、无法识别研究空白

**职责**: 全面搜索相关文献、分类整理现有研究、识别研究空白、生成文献地图

**主要方法**:
- `_generate_search_queries()` - 生成多角度搜索查询
- `_search_papers()` - 搜索文献（使用 `PaperSearchAgent`）
- `_categorize_papers()` - 分类整理文献
- `_identify_gaps()` - 识别研究空白
- `_generate_literature_map()` - 生成文献地图

---

## 3. WritingAgentBase 体系

继承自 `writing/base_writing_agent.py`。

### 3.1 OutlineGeneratorAgent

**文件**: `writing/outline_generator.py`

**职责**: 根据题目和研究目标生成完整论文大纲、设计章节结构、规划内容分配、确保逻辑连贯性

**主要方法**:
- `_analyze_requirements()` - 分析研究要求
- `_generate_outline_structure()` - 生成大纲结构
- `_plan_chapter_details()` - 详细规划每个章节
- `_evaluate_outline_quality()` - 评估大纲质量
- `format_outline_markdown()` - 格式化为 Markdown

**输入**: `topic`, `thesis_statement`, `literature_review`, `target_venue`, `academic_level`
**输出**: 大纲 JSON（包含 chapters, chapter_details, estimated_words）

---

### 3.2 ProposalGeneratorAgent

**文件**: `writing/proposal_generator.py`

**职责**: 生成任务书、生成开题报告、整合文献综述

**主要方法**:
- `_generate_task_book()` - 生成任务书
- `_generate_proposal()` - 生成开题报告

**输出**: 任务书 + 开题报告（Markdown 格式）

---

### 3.3 ReferenceProcessorAgent

**文件**: `writing/reference_processor.py`

**职责**: 格式化引用、交叉引用、引用验证、统一引用风格

**主要方法**:
- `_format_references()` - 格式化参考文献
- `_validate_citations()` - 验证引用
- `_check_completeness()` - 检查引用完整性
- `_generate_reference_list()` - 生成参考文献列表

**支持的引用风格**: APA, IEEE, MLA 等

---

### 3.4 LiteratureReviewAgent

**文件**: `writing/literature_review.py`

**职责**: 自动搜索相关论文、分类整理文献、识别研究空白、生成结构化综述报告

**三种执行模式**:

| 模式 | 描述 | 用途 |
|------|------|------|
| `full_review` | 完整文献综述（默认） | 系统性文献调研 |
| `tracking` | 文献追踪模式 | 追踪特定主题最新进展 |
| `summary` | 文献总结模式 | 多篇论文对比分析，优缺点总结 |

**主要方法**:
- `_execute_full_review()` - 执行完整文献综述
- `_execute_tracking()` - 执行文献追踪
- `_execute_summary()` - 执行文献总结
- `_multi_source_search()` - 多源并行搜索（arXiv + PubMed）
- `_quality_rank()` - 基于质量排序
- `_categorize_papers()` - 分类整理论文
- `_identify_research_gaps()` - 识别研究空白
- `_compare_papers()` - 多论文对比分析
- `_summarize_pros_cons()` - 总结优缺点

---

### 3.5 DraftGeneratorAgent

**文件**: `writing/draft_generator.py`

**职责**: 根据大纲生成完整的论文初稿、各章节内容撰写、引用融入、保持风格一致性

**主要方法**:
- `_generate_chapters()` - 生成各章节内容
- `_write_chapter()` - 撰写单个章节
- `_generate_abstract()` - 生成摘要
- `_integrate_draft()` - 整合全文
- `_evaluate_draft_quality()` - 评估初稿质量

**逻辑一致性检查**: 集成 `LogicCoherenceChecker` 和 `SelfReviseManager`

---

### 3.6 ReportRefinerAgent

**文件**: `writing/report_refiner.py`

**职责**: 多轮迭代优化、评审-修改-精炼循环、质量评估与改进、针对性问题修复

**主要方法**:
- `_review_draft()` - 评审初稿
- `_refine_draft()` - 精炼初稿
- `_final_polish()` - 最终润色
- `_generate_improvement_report()` - 生成改进报告

**迭代控制**: `max_iterations`, `quality_threshold`

---

### 3.7 SmartReviserAgent

**文件**: `writing/smart_reviser.py`

**职责**: 解析导师/审稿人意见、针对性修改文本、保持修改前后一致性

**主要方法**:
- `_parse_feedback()` - 解析意见
- `_categorize_feedback()` - 分类意见
- `_apply_revisions()` - 执行修改
- `_generate_revision_report()` - 生成修改报告

**集成**: Trinka AI 语法检查 API（可选）

---

### 3.8 LanguagePolisherAgent

**文件**: `writing/smart_reviser.py` (同 `problem_oriented/language_polisher.py`)

同 ProblemAgentBase 体系中的 `LanguagePolisherAgent`。

---

## 4. QA Agent 体系

### 4.1 PaperSearchAgent

**文件**: `paper_search/paper_search.py`

**职责**: 从多个学术数据源搜索论文（arXiv / PubMed / Semantic Scholar / OpenAlex / CrossRef）

**支持的数据源**:
- arXiv - 机器学习、统计理论
- PubMed - 生物统计、医学应用
- Semantic Scholar - 学术引用网络
- OpenAlex - 开放学术图谱
- CrossRef - 参考文献元数据

**搜索策略**:
1. 多关键词组合
2. 时间范围筛选
3. 相关性排序
4. 去重和过滤

**主要方法**:
- `_search_arxiv()` - 搜索 arXiv
- `_search_pubmed()` - 搜索 PubMed
- `_search_semantic_scholar()` - 搜索 Semantic Scholar
- `_deduplicate_papers()` - 去除重复论文
- `_rank_papers()` - 根据相关性排序

---

### 4.2 QueryRouterAgent

**文件**: `paper_search/query_router.py`

**职责**: 分析用户查询类型，路由到合适的搜索策略

**支持的问题类型**:
- BASIC_QUERY - 基础问题
- PROFESSIONAL - 专业问题
- FRONTIER - 前沿问题
- APPLICATION - 应用问题

---

### 4.3 DailyWatcherAgent

**文件**: `paper_search/daily_watcher.py`

**职责**: 每日论文监控、关键词跟踪、趋势识别

---

### 4.4 WeeklyReportAgent

**文件**: `paper_search/weekly_report.py`

**职责**: 周报生成、多关键词聚合、方法分类

---

### 4.5 MonthlyReportAgent

**文件**: `paper_search/monthly_report.py`

**职责**: 月报生成、周度分解、作者统计、研究gap分析

---

## 5. 其他 Agent

### 5.1 SupervisorAgent

**文件**: `unified/supervisor.py`

**职责**: 协调多个子 Agent 的工作，作为主控 Agent

---

### 5.2 IntentRouterAgent

**文件**: `unified/intent_router.py`

**职责**: 用户意图检测，多意图支持，路由到合适 Agent

---

### 5.3 MasterSupervisorAgent

**文件**: `unified/master_supervisor.py`

**职责**: 全文流水线全局编排，阶段协调，质量阈值管理

### 5.2 ResearchPlannerAgent

**文件**: `base/enhanced_base.py`

**职责**: 研究规划

---

## 6. 辅助类

### TrinkaGrammarChecker

**文件**: `writing/smart_reviser.py`

集成 Trinka AI API 进行专业学术语法检查。

**方法**:
- `check()` - 使用 Trinka API 检查语法
- `_parse_trinka_result()` - 解析 API 返回结果
- `format_issues()` - 格式化错误列表

---

## 7. 输入输出格式

### AgentInput

```python
{
    "task_type": str,          # 任务类型
    "task_description": str,   # 任务描述
    "input_data": Dict,        # 任务输入数据
    "context": Dict,           # 上下文信息
    "requirements": List[str], # 需求列表
    "metadata": Dict            # 元数据
}
```

### AgentOutput

```python
{
    "success": bool,           # 是否成功
    "result": Any,             # 执行结果
    "agent_name": str,         # 执行 Agent 名称
    "reasoning": str,          # 推理过程
    "next_actions": List[str], # 建议的后续操作
    "error": str,              # 错误信息
    "metadata": Dict,          # 元数据
    "quality_score": float     # 质量评分
}
```

### WritingOutput

继承自 `AgentOutput`，额外包含:
- `quality_score`: 质量评分 (0-1)
- `metadata`: 包含 `coherence_score`, `coherence_issues` 等

---

## 8. LLM 配置

所有 Agent 通过 `LLMConfig` 配置:

```python
{
    "provider": str,      # LLM 提供商 (openai/anthropic)
    "model_name": str,   # 模型名称
    "temperature": float, # 温度参数
    "max_tokens": int,   # 最大 token 数
    "api_key": str,      # API 密钥
    "base_url": str,     # API 基础 URL
    "timeout": int       # 超时时间(秒)
}
```
