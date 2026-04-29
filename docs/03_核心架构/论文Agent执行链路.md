# 论文Agent执行链路

本文档描述论文Agent系统的完整执行链路，包括请求入口、路由决策、论文搜索、报告生成、定时订阅等核心流程。

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户请求                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     IntentRouter                             │
│                     (意图识别)                               │
│  ┌─────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────┐  │
│  │BASIC查询│ │PROFESSIONAL│ │ FRONTIER │ │ APPLICATION  │  │
│  └─────────┘ └───────────┘ └──────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     ┌────────────┐   ┌────────────┐   ┌────────────┐
     │  知识库    │   │ 论文搜索    │   │  案例搜索   │
     └────────────┘   └────────────┘   └────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    MasterSupervisor                          │
│                    (全局协调器)                               │
│  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────┐  │
│  │问题诊断 │→│ 选题阶段  │→│ 文献阶段  │→│ 方法论指导   │  │
│  └─────────┘ └──────────┘ └───────────┘ └──────────────┘  │
│       ↓                                                    │
│  ┌──────────┐ ┌───────────┐ ┌──────────────────────────┐   │
│  │ 写作阶段 │→│ 完善阶段  │→│ 质量评估(不达标则迭代)    │   │
│  └──────────┘ └───────────┘ └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、核心组件

### 2.1 IntentRouter (意图路由)

负责识别用户问题类型并决定处理策略。

| 问题类型 | 特征关键词 | 处理路径 |
|---------|-----------|---------|
| BASIC_QUERY | 什么是、定义、概念、公式 | knowledge_base |
| PROFESSIONAL | 方法、理论、证明、推导 | paper_search |
| FRONTIER | 最新、前沿、趋势、2024/2025/2026 | arXiv_search |
| APPLICATION | 应用、临床、医学、数据 | pubmed_search |

**执行流程:**

```
用户问题 → 关键词匹配/LLM判断 → QuestionType分类 → RoutingDecision
                                                      ↓
                                           {path, confidence, filters}
```

### 2.2 MasterSupervisor (全局协调器)

管理论文写作全流程的全局状态和阶段协调。

**阶段流程:**

```
diagnostic → topic → literature → methodology → writing → polish
    │           │          │            │          │         │
    ▼           ▼          ▼            ▼          ▼         ▼
  并行诊断   选题凝练    文献综述     方法指导    初稿撰写   完善润色
```

**质量阈值:**

| 阶段 | 阈值 | 说明 |
|-----|------|-----|
| diagnostic | 6.0 | 诊断阶段不需要太高 |
| topic | 7.0 | 选题阶段 |
| literature | 7.0 | 文献综述 |
| methodology | 7.0 | 方法论 |
| writing | 7.0 | 写作阶段 |
| polish | 8.0 | 最终润色需要更高 |

### 2.3 PaperSearchAgent (论文搜索)

支持多平台论文搜索。

| 平台 | 特点 | 适用场景 |
|-----|------|---------|
| arXiv | 最新论文、预印本 | 前沿探索 |
| PubMed | 医学、生物文献 | 应用咨询 |
| Semantic Scholar | 学术图谱、引用分析 | 深度调研 |
| DBLP | 计算机会议/期刊 | CS领域 |
| OpenAlex | 跨学科、元数据 | 综合搜索 |

**搜索链路:**

```
查询请求 → QueryRouter路由 → PaperSearchAgent
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
           arXiv                   PubMed              Semantic Scholar
              │                        │                        │
              └────────────────────────┼────────────────────────┘
                                       ▼
                              SearchResultCache (缓存)
                                       │
                                       ▼
                              ReportGenerator (报告生成)
```

---

## 三、论文搜索详细链路

### 3.1 搜索入口

```python
# 代码位置: src/agents_v2/qa/paper_search.py
search_agent = PaperSearchAgent()
result = await search_agent.execute(
    query="deep learning optimization",
    options={"source": "arxiv", "max_results": 10}
)
```

### 3.2 搜索流程

```
1. 接收查询关键词和搜索选项
2. 根据source参数选择搜索平台
3. 构建搜索Query
4. 调用各平台API获取结果
5. 结果缓存 (TTL_MEDIUM: 30min)
6. 排序和去重
7. 返回Paper列表
```

### 3.3 多平台搜索

```python
# 并行搜索多个平台
sources = ["arxiv", "pubmed", "semantic_scholar"]
tasks = [search(source, query) for source in sources]
results = await asyncio.gather(*tasks)
```

---

## 四、报告生成链路

### 4.1 流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    ReportGenerator                           │
│                    (报告生成Agent)                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    构建Prompt                                │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐  │
│  │论文摘要    │ │用户问题    │ │报告格式要求│ │引用格式规范 │  │
│  └───────────┘ └───────────┘ └───────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    LLM (GPT-4/Claude)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    解析输出                                  │
│  ┌─────────┐ ┌───────────┐ ┌──────────┐ ┌─────────────┐  │
│  │ JSON解析 │ │ 降级处理   │ │ 格式验证  │ │ 参考文献生成│  │
│  └─────────┘ └───────────┘ └──────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    PaperReport (结构化报告)
```

### 4.2 报告结构

```json
{
    "summary": "综合摘要 (200字以内)",
    "paper_details": [
        {
            "title": "论文标题",
            "core_contribution": "核心贡献",
            "method": "方法",
            "conclusion": "结论"
        }
    ],
    "comparisons": "方法对比分析",
    "trends": "研究趋势",
    "limitations": "局限性",
    "future_directions": "未来方向",
    "references": ["引用1", "引用2"]
}
```

### 4.3 代码调用

```python
# 代码位置: src/agents_v2/qa/report_generator.py
report_gen = ReportGenerator()
result = await report_gen.execute(
    papers=[paper_dicts],
    question="该领域的研究趋势是什么？"
)
```

---

## 五、定时订阅链路

### 5.1 订阅类型

| 类型 | 调度策略 | 说明 |
|-----|---------|-----|
| daily | `0 9 * * *` | 每天早上9点 |
| weekly | `0 9 * * 1` | 每周一早上9点 |
| monthly | `0 9 1 * *` | 每月1号早上9点 |
| flash | `0 */4 * * *` | 每4小时热点推送 |

### 5.2 订阅链路

```
┌─────────────────────────────────────────────────────────────┐
│              ReportScheduler (定时调度器)                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐ │
│  │ DailyCron  │ │ WeeklyCron │ │ MonthlyCron│ │FlashCron│ │
│  └────────────┘ └────────────┘ └────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           SubscriptionManager (订阅管理)                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ReportSubscription                                    │   │
│  │  - subscription_id, user_id                          │   │
│  │  - subscription_type: daily/weekly/monthly/flash   │   │
│  │  - keywords: 关键词列表                              │   │
│  │  - sources: [arxiv, pubmed, semantic_scholar]       │   │
│  │  - channels: [email, slack, feishu]                 │   │
│  │  - output_format: markdown/json/html                 │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        PaperFlash       PaperSearch      ReportGen
              │               │               │
              └───────────────┼───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                PushService (多渠道推送)                       │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌───────────┐ ┌─────────┐ │
│  │ Email  │ │ Slack  │ │ Feishu │ │ DingTalk  │ │ Webhook │ │
│  └────────┘ └────────┘ └────────┘ └───────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 代码调用

```python
# 创建订阅
subscription = subscription_manager.create_subscription(
    user_id="user_001",
    subscription_type="daily",
    keywords=["machine learning", "deep learning"],
    sources=["arxiv", "pubmed"],
    channels=["email", "slack"]
)

# 创建定时任务
scheduler.create_task(
    task_id="daily_report",
    task_func=generate_daily_report,
    schedule_type="cron",
    cron_expr="0 9 * * *"
)
```

---

## 六、论文快讯链路 (PaperFlash)

### 6.1 快讯类型

| 类型 | 说明 | 使用场景 |
|-----|------|---------|
| HOT | 热点论文 | 每日推送 |
| TRENDING | 上升趋势 | 趋势追踪 |
| CONFERENCE | 顶会论文 | NeurIPS/ICML/ICLR速报 |

### 6.2 快讯链路

```
┌─────────────────────────────────────────────────────────────┐
│                      PaperFlash                               │
│                      (论文快讯)                               │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        HOT搜索          TRENDING搜索      CONFERENCE搜索
              │               │               │
              ▼               ▼               ▼
        最新7天论文     30天内高引用      顶会年度论文
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                    _generate_flash_reports
                              │
                              ▼
              ┌───────────────────────────────────┐
              │          FlashReport               │
              │  - title: 论文标题                 │
              │  - core_finding: 3句话核心发现    │
              │  - key_points: 要点列表            │
              │  - significance: 研究意义          │
              │  - tldr: 一句话总结                │
              │  - reading_time: 预估阅读时间      │
              └───────────────────────────────────┘
```

### 6.3 代码调用

```python
# 代码位置: src/agents_v2/qa/paper_flash.py
flash = PaperFlash()

# 生成热点快讯
result = await flash.execute(
    flash_type=FlashType.HOT,
    topic="machine learning",
    limit=5
)

# 生成每日多主题快讯
daily = await flash.generate_daily_flash(
    topics=["ML", "DL", "NLP", "CV"],
    limit_per_topic=3
)

# 生成顶会速报
neurips = await flash.generate_conference_flash(
    conference="NeurIPS",
    topic="transformer",
    limit=10
)
```

---

## 七、Pipeline完整流程

### 7.1 流程阶段

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: DIAGNOSTIC (并行诊断)                               │
│  ├─ TopicRefinerAgent → 选题问题诊断                        │
│  ├─ LiteratureMapperAgent → 文献完整性诊断                   │
│  └─ MethodologyAdvisorAgent → 方法论诊断                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: TOPIC (选题阶段)                                    │
│  └─ TopicAgent → 凝练研究课题                               │
│      输入: user_request                                      │
│      输出: topic (课题定义)                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: LITERATURE (文献阶段)                              │
│  └─ LiteratureAgent → 文献综述                              │
│      输入: topic                                             │
│      输出: literature_result (文献总结)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: METHODOLOGY (方法论阶段)                           │
│  ├─ MethodologyAdvisorAgent → 方法指导                      │
│  └─ ArgumentBuilderAgent → 论点构建                         │
│      输入: topic, literature_result                          │
│      输出: methodology_guide (方法指南)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 5: WRITING (写作阶段)                                  │
│  ├─ ThesisAgent → Thesis凝练                                │
│  ├─ OutlineAgent → 大纲生成                                 │
│  └─ DraftWriterAgent → 初稿撰写                             │
│      输入: topic, literature_result, thesis_statement        │
│      输出: draft (论文初稿)                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 6: POLISH (完善阶段)                                   │
│  ├─ ChartFormatterAgent → 图表优化                          │
│  ├─ LanguagePolisherAgent → 语言润色                        │
│  └─ PlagiarismCheckerAgent → 查重检测                       │
│      输入: draft                                             │
│      输出: polished_paper (最终论文)                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    QualityScore ≥ 8.0?
                          /          \
                       否             是
                        /              \
                   迭代阶段          输出最终论文
```

### 7.2 代码调用

```python
# 代码位置: src/agents_v2/unified/master_supervisor.py
supervisor = MasterSupervisor()
supervisor.register_problem_agents()
supervisor.register_pipeline_agents()
supervisor.register_writing_agents()

result = await supervisor.run(
    "full_paper",
    {"topic": "基于深度学习的图像超分辨率算法研究"}
)

# 结果
{
    "success": True,
    "phases_completed": ["diagnostic", "topic", "literature", ...],
    "final_paper": "...",
    "final_quality": 8.5,
    "quality_level": "excellent",
    "iterations": 1
}
```

---

## 八、辅助系统链路

### 8.1 缓存系统

```
┌─────────────────────────────────────────────────────────────┐
│                       MemoryCache                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │TTL_SHORT    │ │TTL_MEDIUM   │ │TTL_LONG     │           │
│  │5分钟        │ │30分钟       │ │1小时        │           │
│  │搜索结果缓存  │ │报告缓存      │ │论文数据缓存  │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 记忆系统

```
┌─────────────────────────────────────────────────────────────┐
│                    HierarchicalMemory                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ ShortTerm   │ │ LongTerm    │ │ Episodic    │           │
│  │ 短期记忆     │ │ 长期记忆     │ │ 情节记忆     │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    UnifiedMemoryService                      │
│  - context_persistence (上下文持久化)                         │
│  - relational (关系存储)                                     │
│  - retrieval (记忆检索)                                     │
└─────────────────────────────────────────────────────────────┘
```

### 8.3 推荐系统

```
┌─────────────────────────────────────────────────────────────┐
│                  RecommendationEngine                       │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐     │
│  │ContentBased   │ │Collaborative  │ │ Hybrid        │     │
│  │基于内容推荐    │ │协同过滤推荐    │ │混合推荐       │     │
│  └───────────────┘ └───────────────┘ └───────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    recommend_for_user   recommend_hot      recommend_trending
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                    个性化论文推荐列表
```

---

## 九、团队协作链路

```
┌─────────────────────────────────────────────────────────────┐
│                      TeamManager                             │
│                      (团队管理)                               │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      核心功能                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ User管理    │ │ Team管理    │ │ 成员管理    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│  ┌─────────────┐ ┌─────────────┐                           │
│  │ SharedSub   │ │ Discussion  │                           │
│  │ 共享订阅    │ │ 团队讨论    │                           │
│  └─────────────┘ └─────────────┘                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      权限控制                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ is_team_    │ │ is_team_    │ │ can_manage  │           │
│  │ member      │ │ owner       │ │ _team       │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## 十、错误处理与熔断

### 10.1 熔断器链路

```
┌─────────────────────────────────────────────────────────────┐
│                 MultiCircuitBreaker                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │SearchCircuit│ │ ReportCircuit│ │FlashCircuit│           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│                                                              │
│  状态: CLOSED → OPEN → HALF_OPEN → CLOSED                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              外部API失败时快速返回，不阻塞用户
```

### 10.2 降级策略

```
异常发生
    │
    ▼
┌─────────────────┐
│ FallbackHandler │
└─────────────────┘
    │
    ├── 记录错误日志
    ├── 返回降级响应
    └── 累计错误计数
```

---

## 十一、执行入口汇总

| 场景 | 代码位置 | 调用方式 |
|-----|---------|---------|
| 意图识别 | `unified/intent_router.py` | `IntentRouter().route(query)` |
| 论文搜索 | `qa/paper_search.py` | `PaperSearchAgent().execute(query, options)` |
| 报告生成 | `qa/report_generator.py` | `ReportGenerator().execute(papers, question)` |
| 论文快讯 | `qa/paper_flash.py` | `PaperFlash().execute(flash_type, topic)` |
| 定时调度 | `scheduler/report_scheduler.py` | `ReportScheduler().run_scheduler()` |
| 订阅管理 | `scheduler/subscription_manager.py` | `SubscriptionManager().create_subscription()` |
| 完整流程 | `unified/master_supervisor.py` | `MasterSupervisor().run("full_paper", input)` |
| 推送通知 | `notification/push_service.py` | `PushService().push(content, channels)` |

---

## 十二、总结

论文Agent系统的执行链路遵循以下原则：

1. **问题导向**: 先诊断后治疗，通过IntentRouter识别问题类型
2. **质量驱动**: 每阶段设置质量阈值，不达标则迭代
3. **模块化设计**: 各Agent职责单一，可独立调用
4. **可扩展性**: 支持新增搜索平台、推送渠道、订阅类型
5. **容错处理**: 熔断器保护，降级策略保证可用性

---

*文档版本: 1.0*
*更新时间: 2026-04-28*
