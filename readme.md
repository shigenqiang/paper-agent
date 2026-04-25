 # 论文Agent - 智能论文调研与知识图谱系统

> 基于多Agent协作的学术论文自动调研与综述生成系统

## 一、项目简介

面向统计领域文献爆发式增长、知识抽取难结构化、人工综述周期长等问题，设计两大核心系统：

### 系统一：智能统计学问答系统
- **智能路由**：自动判断问题类型，决定是否调用大模型
- **论文搜索**：自动从arXiv/PubMed等搜索相关统计学论文
- **专业报告**：基于真实论文给出带参考文献的专业回答
- **每日推送**：自动订阅并总结最新统计学论文，生成报告

### 系统二：论文写作助手
- **多Agent协作**：基于LangGraph构建五智能体协作流水线
- **知识图谱**：CDC-BERTopic主题检测 + Graph-First RAG
- **记忆管理**：短期/长期/情景记忆，支持语义检索
- **质量保证**：Validation Gate + 迭代改进机制

---

## 二、核心系统详解

### 2.1 智能统计学问答系统

```
用户提问
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│                    QueryRouter (问题路由)                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │ 简单统计   │  │ 专业问题   │  │ 概念解释   │              │
│  │ 直接回答   │  │ 搜索论文   │  │ LLM回答    │              │
│  └────────────┘  └────────────┘  └────────────┘              │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│              PaperSearchAgent (论文搜索Agent)                   │
│  ├── arXiv搜索        - 机器学习、统计理论论文                  │
│  ├── PubMed搜索       - 生物统计、医学应用论文                   │
│  └── 语义排序         - 基于问题相关性排序                      │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│              ReportGenerator (报告生成Agent)                   │
│  ├── 摘要提取       - 提炼每篇论文核心贡献                      │
│  ├── 对比分析       - 比较不同论文的方法和结论                   │
│  └── 专业报告       - 生成结构化报告，含参考文献                 │
└────────────────────────────────────────────────────────────────┘
```

#### 路由决策规则

| 问题类型 | 特征 | 处理方式 |
|----------|------|----------|
| **基础查询** | 定义、公式、概念 | 直接从知识库回答 |
| **专业问题** | 方法论、理论证明 | 搜索论文后回答 |
| **前沿探索** | 最新技术、发展趋势 | 搜索arXiv最新论文 |
| **应用咨询** | 实际数据分析 | 搜索PubMed案例 |

#### 每日论文订阅

```python
# 每日自动执行
DailyPaperWatcher:
    - 搜索关键词: ["statistical learning", "causal inference", "Bayesian"]
    - 筛选条件: 发表时间<30天, 引用>5
    - 生成摘要报告: 新方法总结 + 研究趋势
```

### 2.2 论文写作助手

#### 双层Supervisor架构

```
MasterSupervisor
    │
    ├── Diagnostic Phase (并行诊断)
    │   ├── TopicRefinerAgent
    │   ├── LiteratureMapperAgent
    │   └── MethodologyAdvisorAgent
    │
    ├── Pipeline Phase (顺序执行)
    │   ├── TopicAgent → LiteratureAgent → ThesisAgent
    │   └── OutlineAgent → DraftWriterAgent → EditorAgent
    │
    └── Polish Phase (针对性修复)
        ├── ChartFormatterAgent
        ├── LanguagePolisherAgent
        └── PlagiarismCheckerAgent
```

---

## 三、核心Agent详解

### 3.1 统计学问答相关Agent

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| `QueryRouter` | 判断问题类型，决定处理策略 | 用户问题 | 路由决策 + 处理路径 |
| `PaperSearchAgent` | 搜索统计学论文 | 查询关键词 | 相关论文列表 |
| `ReportGenerator` | 生成专业报告 | 论文列表 | 结构化报告 |
| `DailyWatcher` | 每日论文监控 | 订阅关键词 | 每日摘要报告 |
| `CitationManager` | 管理参考文献 | 论文列表 | 格式化引用 |

### 3.2 论文写作Agent

#### 问题导向型 (Problem-Oriented)

| Agent | 针对问题 | 职责 |
|-------|----------|------|
| `TopicRefinerAgent` | 选题困难 | 分析想法、评估可行性、优化选题 |
| `LiteratureMapperAgent` | 文献综述不充分 | 全面搜索、分类整理、识别空白 |
| `MethodologyAdvisorAgent` | 研究方法不当 | 推荐方法、检查严谨性 |
| `ArgumentBuilderAgent` | 论证逻辑不严密 | 构建框架、检查连贯性 |
| `SectionDifferentiatorAgent` | 摘要与结论重复 | 检查差异、指导差异化 |
| `DiscussionDeepenerAgent` | 讨论部分薄弱 | 深化讨论、对比已有研究 |
| `ChartFormatterAgent` | 图表制作粗糙 | 检查规范、优化呈现 |
| `LanguagePolisherAgent` | 语言表达问题 | 语法检查、规范术语 |
| `PlagiarismCheckerAgent` | 查重问题 | 识别高复制、提供改写 |

#### Pipeline型 (Pipeline)

| Agent | 阶段 | 职责 |
|-------|------|------|
| `TopicAgent` | 选题 | 确定研究主题和范围 |
| `LiteratureAgent` | 文献 | 检索和分析相关文献 |
| `ThesisAgent` | 论点 | 提炼研究论点和假设 |
| `OutlineAgent` | 大纲 | 制定论文结构和大纲 |
| `DraftWriterAgent` | 撰写 | 分章节撰写论文内容 |
| `EditorAgent` | 编辑 | 修订和完善论文 |
| `ReviewerAgent` | 审核 | 最终审核和质量把控 |

---

## 四、关键机制

### 4.1 路由决策机制

```python
class QueryRouter:
    """
    问题路由决策

    决策流程:
    1. 解析问题类型 (基础/专业/前沿/应用)
    2. 评估复杂度 (简单/中等/复杂)
    3. 决定处理路径 (直接回答/搜索论文/LLM增强)
    """

    ROUTING_RULES = {
        "基础概念": {"path": "knowledge_base", "priority": 1},
        "统计方法": {"path": "paper_search", "priority": 2},
        "前沿研究": {"path": "arxiv_search", "priority": 3},
        "实际应用": {"path": "pubmed_search", "priority": 2}
    }
```

### 4.2 论文搜索机制

```python
class PaperSearchAgent:
    """
    论文搜索Agent

    支持的数据源:
    - arXiv: 机器学习、统计理论
    - PubMed: 生物统计、医学应用
    - Google Scholar: 通用学术搜索

    搜索策略:
    1. 多关键词组合
    2. 时间范围筛选
    3. 相关性排序
    4. 去重和过滤
    """
```

### 4.3 报告生成机制

```python
class ReportGenerator:
    """
    报告生成Agent

    输出格式:
    {
        "summary": "综合摘要",
        "papers": [
            {
                "title": "论文标题",
                "authors": "作者",
                "year": 年份,
                "key_contributions": ["贡献1", "贡献2"],
                "method": "方法概述",
                "results": "主要结果"
            }
        ],
        "comparisons": "对比分析",
        "references": ["参考文献列表"]
    }
    """
```

### 4.4 错误处理机制

#### 熔断器 (CircuitBreaker)

```
CLOSED → (失败阈值) → OPEN → (超时) → HALF_OPEN → (成功) → CLOSED
```

#### 降级处理 (FallbackHandler)

- 直接回答：使用缓存的知识库
- 论文搜索：使用备用数据源
- 报告生成：返回基础摘要

---

## 五、设计模式

### 5.1 五大Workflow模式

| 模式 | 描述 | 适用场景 |
|------|------|----------|
| **Prompt Chaining** | Task → LLM1 → LLM2 → LLM3 → Output | 需要高准确性的任务 |
| **Routing** | Input → Classifier → Expert1/Expert2/Expert3 | 任务类型明确的场景 |
| **Parallelization** | Task → [Agent1] [Agent2] [Agent3] → Aggregator | 子任务独立、结果可合并 |
| **Orchestrator-Workers** | Orchestrator → Workers → Synthesize | 复杂不可预测任务 |
| **Evaluator-Optimizer** | Draft → Evaluator → Optimizer → Draft' | 有明确质量标准的任务 |

### 5.2 Multi-Agent协作模式

| 协作形式 | 说明 |
|----------|------|
| **顺序交接** | Agent A完成 → 传递给Agent B |
| **并行处理** | 多个Agent同时处理不同子任务 |
| **辩论与共识** | 多Agent讨论，达成共识 |
| **层级结构** | Supervisor管理多个Worker |

---

## 六、评估指标

### 6.1 核心指标

| 维度 | 指标 | 说明 |
|------|------|------|
| **准确性** | 任务完成率、错误率 | Agent能否成功完成目标 |
| **效率** | 延迟、token消耗 | 响应时间和资源消耗 |
| **稳定性** | 失败率、恢复时间 | 容错能力和自愈能力 |
| **相关性** | 搜索召回率、精确率 | 论文搜索质量 |

### 6.2 质量等级

| 等级 | 分数范围 | 说明 |
|------|----------|------|
| **EXCELLENT** | >= 9.0 | 超出预期 |
| **GOOD** | >= 7.0 | 达到要求 |
| **ACCEPTABLE** | >= 5.0 | 基本可用 |
| **POOR** | < 5.0 | 需要改进 |

---

## 七、项目结构

```
d:\pycharmprojects\pythonProject1\
├── src/
│   ├── agents_v2/                    # 多智能体系统 (v2)
│   │   ├── unified/                  # 统一Agent框架
│   │   │   ├── state_model.py       # 状态模型
│   │   │   ├── circuit_breaker.py   # 熔断器
│   │   │   ├── error_handler.py     # 错误处理
│   │   │   ├── phase_supervisor.py # 阶段协调
│   │   │   └── master_supervisor.py # 全局协调
│   │   ├── qa/                       # 统计学问答系统
│   │   │   ├── query_router.py     # 问题路由
│   │   │   ├── paper_search.py      # 论文搜索
│   │   │   ├── report_generator.py  # 报告生成
│   │   │   ├── daily_watcher.py     # 每日监控
│   │   │   └── citation_manager.py  # 引用管理
│   │   ├── problem_oriented/        # 问题导向Agent
│   │   │   ├── topic_refiner.py
│   │   │   ├── literature_mapper.py
│   │   │   └── ...
│   │   └── paper_agents/            # Pipeline型Agent
│   │
│   ├── knowledge/                    # 知识图谱系统
│   ├── memory/                       # 记忆管理
│   └── workflows/                    # 工作流定义
│
└── README.md                          # 本文档
```

---

## 八、快速开始

### 8.1 安装依赖

```bash
pip install -r requirements.txt
```

### 8.2 配置环境变量

```env
OPEN_API_KEY=your_api_key
MILVUS_URI=your_milvus_uri
NEO4J_PASSWORD=your_neo4j_password
```

### 8.3 使用示例

#### 统计学问答

```python
from src.agents_v2.qa import QueryRouter, PaperSearchAgent, ReportGenerator

# 用户提问
question = "什么是贝叶斯分层模型？它在医学研究中的应用有哪些？"

# 路由决策
router = QueryRouter()
decision = router.decide(question)
print(f"路由决策: {decision['path']}")  # -> paper_search

# 搜索论文
searcher = PaperSearchAgent()
papers = searcher.search(question, source="arxiv")
print(f"找到 {len(papers)} 篇相关论文")

# 生成报告
generator = ReportGenerator()
report = generator.generate(papers, question)
print(report["summary"])
```

#### 每日论文订阅

```python
from src.agents_v2.qa import DailyWatcher

watcher = DailyWatcher(
    keywords=["statistical learning", "causal inference"],
    frequency="daily"
)

# 启动每日监控
await watcher.start()

# 手动触发
report = await watcher.run()
print(report["daily_summary"])
```

#### 论文写作流程

```python
from src.agents_v2.unified import MasterSupervisor, LLMConfig

# 初始化
config = LLMConfig(provider="openai", model_name="gpt-4")
supervisor = MasterSupervisor(config)

# 注册Agent
supervisor.register_problem_agents()
supervisor.register_pipeline_agents()

# 运行完整流程
result = await supervisor.run("full_paper", {
    "user_request": "深度学习在医学影像诊断中的应用"
})

print(result["final_paper"])
print(f"Quality: {result['final_quality']}")
```

---

## 九、扩展指南

### 9.1 新增问答场景

1. 在 `qa/` 目录实现新的Agent
2. 继承 `BaseQAAgent`
3. 注册到 `QueryRouter`

### 9.2 自定义路由规则

继承 `QueryRouter` 重写 `_classify_question`

### 9.3 新增论文数据源

继承 `PaperSearchAgent` 实现 `_search_source`

---

## 十、参考资源

| 资源 | 说明 |
|------|------|
| [Anthropic: Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) | 核心设计原则 |
| [arXiv API](https://arxiv.org/help/api) | 论文搜索API |
| [PubMed E-utilities](https://www.ncbi.nlm.nih.gov/home/develop/api/) | 生物医学文献API |
| [LangGraph Documentation](https://langchain.dev/langgraph) | 工作流编排 |

---

## 许可证

MIT License
