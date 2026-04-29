# Paper Agent - 智能论文调研与写作系统

> 基于多Agent协作的学术论文自动调研与综述生成系统

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Test Status](https://img.shields.io/badge/tests-827+%20passed-green.svg)]()

---

## 核心功能

| 功能模块 | 说明 |
|---------|------|
| **论文搜索** | 多源学术平台搜索（arXiv/PubMed/Semantic Scholar等） |
| **定时报告** | 每日/每周/每月论文报告自动生成 |
| **论文写作** | 从选题到大纲到初稿的全流程辅助 |
| **论文修改** | 智能改稿、润色、评审多轮迭代 |
| **对话问答** | 基于论文的智能问答与比较分析 |
| **记忆系统** | 多层级记忆管理，记住用户偏好 |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         用户层                                        │
│   (对话问答 / 报告订阅 / 写作任务 / 论文追踪)                        │
├─────────────────────────────────────────────────────────────────────┤
│                         Agent层                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │  报告Agent   │  │  写作Agent   │  │  搜索Agent   │  │ 路由Agent │ │
│  │Daily/Weekly/│  │大纲/初稿/修订│  │多源并行搜索  │  │问题分类  │ │
│  │ Monthly     │  │润色/评审    │  │去重排序    │  │意图识别  │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────┬─────┘ │
│         └─────────────────┼─────────────────┼──────────────┘       │
├─────────────────────────────────────────────────────────────────────┤
│                       数据源层                                       │
│  arXiv │ PubMed │ Semantic Scholar │ CrossRef │ DBLP │ OpenAlex   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 一、论文搜索 (Paper Search)

### 支持的数据源

| 数据源 | 类型 | 说明 | 优先级 |
|--------|------|------|--------|
| **arXiv** | 预印本 | cs.LG, stat.ML, stat.ME, math.ST | P0 |
| **PubMed** | 学术数据库 | 生物医学文献 | P0 |
| **Semantic Scholar** | 学术搜索 | AI增强搜索、TLDR、引用分析 | P1 |
| **CrossRef** | 元数据 | DOI元数据、期刊文章 | P1 |
| **DBLP** | 计算机文献 | 会议论文为主 | P1 |
| **OpenAlex** | 学术知识库 | 跨学科文献 | P1 |

### 搜索功能

```python
# 多源并行搜索
from src.agents_v2.qa import PaperSearchAgent

searcher = PaperSearchAgent()
result = await searcher.execute(
    query="causal inference machine learning",
    context={
        "source": "all",        # all, arxiv, pubmed
        "time_range": 30,        # 最近30天
        "max_results": 10
    }
)
```

### 扩展搜索工具

```python
from src.agents_v2.tools.extended_search import (
    search_semantic_scholar,  # AI增强搜索
    search_crossref,           # DOI元数据
    search_dblp,              # 计算机会议论文
    search_openalex,          # 跨学科搜索
    analyze_paper_trend,       # 趋势分析
    compare_papers             # 论文比较
)
```

---

## 二、定时报告 (Scheduled Reports)

### 报告类型

| 类型 | Agent | 说明 | 生成方式 |
|------|-------|------|---------|
| **每日报告** | `DailyWatcher` | 监控最新30天论文 | 定时/按需 |
| **每周报告** | `WeeklyReportGenerator` | 一周论文汇总分析 | 定时/按需 |
| **每月报告** | `MonthlyReportGenerator` | 月度深度分析报告 | 定时/按需 |
| **论文快讯** | `PaperFlash` | 热点论文5分钟速读 | 实时/按需 |

### 报告内容对比

| 特性 | 每日报告 | 每周报告 | 每月报告 |
|------|---------|---------|---------|
| **时间范围** | 最近30天 | 7天 | 30天 |
| **论文处理量** | 20-50篇 | 50-200篇 | 100-500篇 |
| **分析深度** | 浅（快速概览） | 中（方法统计） | 深（全面分析） |
| **输出内容** | 新论文列表 | 趋势变化 | 领域全景 |
| **核心指标** | 新方法、趋势 | 方法分布、周对比 | 作者分析、研究空白 |

### 使用示例

```python
# 每日报告
from src.agents_v2.qa import DailyWatcher
watcher = DailyWatcher()
result = watcher.run_sync(keywords=['machine learning', 'causal inference'])

# 每周报告
from src.agents_v2.qa import WeeklyReportGenerator
weekly = WeeklyReportGenerator()
result = weekly.run_sync(keywords=['deep learning', 'transformer'])

# 每月报告
from src.agents_v2.qa import MonthlyReportGenerator
monthly = MonthlyReportGenerator()
result = monthly.run_sync(keywords=['statistical learning'])
```

### 报告输出格式

```json
{
    "success": true,
    "report": {
        "date/week/month": "2026-04-27",
        "topic": "机器学习、因果推断",
        "papers_found": 45,
        "summary": "本周共45篇论文，主要集中在...",
        "method_breakdown": {
            "neural network": 15,
            "bayesian methods": 8,
            "causal inference": 12
        },
        "top_papers": [...],
        "trends": ["大模型微调", "因果表示学习"],
        "references": [...]
    }
}
```

---

## 三、论文写作 (Paper Writing)

### 写作流程

```
选题 ──▶ 大纲 ──▶ 初稿 ──▶ 修订 ──▶ 润色 ──▶ 评审
  │        │        │        │        │        │
  ▼        ▼        ▼        ▼        ▼        ▼
Topic   Outline  Draft   Refine  Polish  Review
Agent   Agent   Writer   Agent   Agent   Agent
```

### 写作Agent列表

| Agent | 文件 | 职责 |
|-------|------|------|
| `TopicAgent` | `paper_agents/thesis_agent.py` | 选题与研究方向 |
| `OutlineGeneratorAgent` | `writing/outline_generator.py` | 大纲生成 |
| `DraftGeneratorAgent` | `writing/draft_generator.py` | 初稿撰写 |
| `LiteratureReviewAgent` | `writing/literature_review.py` | 文献综述 |
| `ProposalGeneratorAgent` | `writing/proposal_generator.py` | 开题报告 |
| `ReferenceProcessorAgent` | `writing/reference_processor.py` | 参考文献处理 |

### 写作工具

| 工具 | 文件 | 功能 |
|------|------|------|
| `ReflectionEngine` | `reflection_engine.py` | 反思引擎，提升生成质量 |
| `AnswerQualityChecker` | `answer_quality_checker.py` | 答案质量检查 |
| `StreamingGenerator` | `streaming_generator.py` | 流式生成，支持打字机效果 |
| `GenerationOptimizer` | `generation_optimizer.py` | 生成优化，批量生成 |
| `CitationGenerator` | `citation_generator.py` | 引用生成，多格式支持 |

---

## 四、论文修改 (Paper Revision)

### 修改流程

```
原始论稿 ──▶ 智能改稿 ──▶ 多轮精炼 ──▶ 语言润色 ──▶ 最终评审
    │           │            │            │           │
    ▼           ▼            ▼            ▼           ▼
 原文      针对性修改     迭代优化     语法术语     质量评分
```

### 修改Agent列表

| Agent | 文件 | 职责 |
|-------|------|------|
| `SmartReviserAgent` | `writing/smart_reviser.py` | 解析意见，针对性修改 |
| `ReportRefinerAgent` | `writing/report_refiner.py` | 多轮迭代精炼 |
| `LanguagePolisherAgent` | `writing/smart_reviser.py` | 语言润色、语法检查 |
| `ReviewerAgent` | `writing/report_refiner.py` | 单次评审、质量评估 |

### 使用示例

```python
# 智能改稿 - 解析导师/审稿人意见
from src.agents_v2.writing import SmartReviserAgent

reviser = SmartReviserAgent()
result = await reviser.execute({
    "original_text": paper_content,
    "feedback": "方法部分不够详细，需要补充实验细节...",
    "highlight_changes": True
})

# 多轮精炼 - 自动迭代优化
from src.agents_v2.writing import ReportRefinerAgent

refiner = ReportRefinerAgent()
result = await refiner.execute({
    "draft": paper_content,
    "focus_areas": ["结构", "逻辑", "引用"],
    "max_iterations": 3,
    "quality_threshold": 0.8
})

# 语言润色
from src.agents_v2.writing import LanguagePolisherAgent

polisher = LanguagePolisherAgent()
result = await polisher.execute({
    "text": paper_content,
    "language": "zh",
    "polish_level": "medium"  # light, medium, heavy
})
```

### 改稿输出

```json
{
    "success": true,
    "result": {
        "original_text": "...",
        "revised_text": "...",
        "revision_report": "修改统计：\n- content: 3处修改\n- language: 5处修改",
        "feedback_categories": ["content", "language"],
        "total_revisions": 8
    }
}
```

---

## 五、对话问答 (Q&A Chat)

### 交互模式

| 模式 | 示例 | 处理流程 |
|------|------|---------|
| **问答** | "transformer的最新论文有哪些？" | 搜索 → 摘要 → 回答 |
| **比较** | "对比贝叶斯方法和深度学习在时间序列上的应用" | 多论文 → 对比分析 |
| **探索** | "因果推断领域还有哪些未解决的问题？" | 搜索 → 趋势分析 → 研究空白 |
| **追踪** | "追踪X教授的最新论文" | 作者搜索 → 研究脉络 |

### 路由决策

```python
class QuestionType(Enum):
    BASIC_QUERY = "basic_query"        # 基础查询
    PROFESSIONAL = "professional"      # 专业问题 → 论文搜索
    FRONTIER = "frontier"              # 前沿探索 → 多源搜索
    APPLICATION = "application"        # 应用咨询 → 案例搜索
```

---

## 六、完整功能清单

### P0 - 核心功能

| 模块 | 功能 | 说明 |
|------|------|------|
| **搜索** | 多源搜索 | arXiv、PubMed |
| | 关键词搜索 | 多关键词并行 |
| | 时间筛选 | 按天/周/月 |
| **报告** | 每日报告 | 监控+摘要 |
| | 每周报告 | 汇总+趋势 |
| | 每月报告 | 深度分析 |
| **写作** | 大纲生成 | 结构化大纲 |
| | 初稿撰写 | 全文初稿 |
| | 文献综述 | 背景介绍 |
| **修改** | 智能改稿 | 意见→修改 |
| | 多轮精炼 | 迭代优化 |
| **对话** | 问答 | 论文搜索回答 |

### P1 - 重要功能

| 模块 | 功能 | 说明 |
|------|------|------|
| **搜索** | 扩展平台 | Semantic Scholar、DBLP、OpenAlex |
| | 智能摘要 | TLDR自动生成 |
| | 查询扩展 | 同义词扩展 |
| **报告** | 论文快讯 | 热点速读 |
| | 订阅推送 | Email/Slack/飞书 |
| **写作** | 开题报告 | 选题论证 |
| | 参考文献处理 | 格式化 |
| **修改** | 语言润色 | 语法/术语 |
| | 质量评审 | 多维评分 |
| **对话** | 多轮对话 | 上下文记忆 |
| | 论文比较 | 多论文对比 |

### P2 - 增强功能

| 模块 | 功能 | 说明 |
|------|------|------|
| **搜索** | Papers with Code | 论文+代码 |
| | ACL Anthology | NLP领域 |
| | IEEE Xplore | 工程应用 |
| **报告** | 跨期对比 | 周/月同比 |
| | 可视化图表 | 分布图/趋势图 |
| **知识图谱** | 引用网络 | 关系图谱 |
| | 作者合作 | 合作网络 |
| **系统** | REST API | 完整暴露 |
| | Webhook | 钉钉/企微 |
| **企业** | 多用户 | 团队协作 |
| | 私有部署 | Docker/K8s |

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
echo "OPENAI_API_KEY=your_api_key" > .env

# 3. 论文搜索
python -c "
from src.agents_v2.qa import PaperSearchAgent
import asyncio
async def main():
    searcher = PaperSearchAgent()
    result = await searcher.execute('machine learning', {'source': 'all', 'max_results': 10})
    print(result)
asyncio.run(main())
"

# 4. 生成报告
python -c "
from src.agents_v2.qa import DailyWatcher
watcher = DailyWatcher()
result = watcher.run_sync(keywords=['statistical learning'])
print(result)
"

# 5. 论文写作
python -c "
from src.agents_v2.writing import OutlineGeneratorAgent
agent = OutlineGeneratorAgent()
result = await agent.execute({'topic': '深度学习在医学影像中的应用'})
print(result)
"

# 6. 论文修改
python -c "
from src.agents_v2.writing import SmartReviserAgent
agent = SmartReviserAgent()
result = agent.run_sync({
    'original_text': '论文内容...',
    'feedback': '实验部分需要补充...'
})
print(result)
"

# 7. 启动API服务
python -m src.agents_v2.api_server
```

---

## 项目结构

```
src/agents_v2/
├── qa/                     # 问答与报告
│   ├── daily_watcher.py    # 每日监控
│   ├── weekly_report.py    # 周报生成
│   ├── monthly_report.py   # 月报生成
│   ├── report_generator.py # 通用报告
│   ├── paper_search.py     # 论文搜索
│   └── citation_manager.py  # 引用管理
├── writing/                # 写作
│   ├── outline_generator.py   # 大纲生成
│   ├── draft_generator.py      # 初稿撰写
│   ├── report_refiner.py       # 多轮精炼
│   ├── smart_reviser.py        # 智能改稿
│   └── literature_review.py    # 文献综述
├── paper_agents/           # 论文Agent
│   ├── thesis_agent.py        # 选题
│   ├── outline_agent.py        # 大纲
│   ├── draft_writer.py         # 初稿
│   ├── editor_agent.py         # 编辑
│   └── reviewer_agent.py       # 评审
├── tools/
│   └── extended_search.py   # 扩展搜索 (Semantic Scholar, DBLP, OpenAlex)
└── memory/                 # 记忆系统

frontend/                    # 前端界面
docs/                        # 文档
tests/                       # 测试
```

---

## API端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/search` | POST | 论文搜索 |
| `/api/reports/daily` | POST | 每日报告 |
| `/api/reports/weekly` | POST | 每周报告 |
| `/api/reports/monthly` | POST | 每月报告 |
| `/api/outline` | POST | 大纲生成 |
| `/api/draft` | POST | 初稿撰写 |
| `/api/revise` | POST | 论文修改 |
| `/api/polish` | POST | 语言润色 |
| `/api/review` | POST | 质量评审 |

认证方式: `X-API-Key` 请求头

---

## 七、Agent提示词规范 (Prompt Engineering)

> **重要参考**: 完整的提示词工程指南请查阅 [Agent提示词工程指南](docs/调研报告/Agent提示词工程指南.md)

### 7.1 标准提示词结构

每个Agent的提示词应包含五个部分：

```
┌─────────────────────────────────────────────────────────────┐
│                    SYSTEM PROMPT 结构                        │
├─────────────────────────────────────────────────────────────┤
│  1. 角色定义 (Role Definition)                              │
│     - Agent身份、专业背景                                   │
│     - 核心职责说明                                          │
│                                                             │
│  2. 能力边界 (Capabilities)                                 │
│     - 能做什么                                               │
│     - 具备哪些专业知识                                       │
│                                                             │
│  3. 行为准则 (Guidelines)                                  │
│     - 应该如何处理任务                                       │
│     - 质量标准                                               │
│                                                             │
│  4. 约束限制 (Constraints)                                 │
│     - 不能做什么                                             │
│     - 限制条件                                               │
│                                                             │
│  5. 输出格式 (Output Format)                               │
│     - JSON Schema定义                                        │
│     - 示例输出                                               │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Agent类型与提示词模板

| Agent类型 | 职责 | 核心要素 |
|-----------|------|----------|
| **路由Agent** | 识别意图，分类问题，决定处理路径 | 问题类型定义、多路径映射 |
| **搜索Agent** | 多源检索、查询优化、结果排序 | 多平台特点、查询扩展策略 |
| **诊断Agent** | 问题识别、根因分析、严重程度评估 | 诊断维度、严重程度判定 |
| **生成Agent** | 内容生成、结构化输出、引用规范 | 报告结构、质量标准 |
| **精炼Agent** | 多轮迭代、质量提升、问题修复 | 评审维度、质量阈值 |
| **PipelineAgent** | 流水线执行、阶段输出、流程协调 | 阶段目标、输入输出规范 |

### 7.3 路由类Agent提示词示例 (QueryRouter)

```python
self.system_prompt = """你是一个专业的问题分类专家，擅长判断用户问题的类型并决定最佳处理策略。

问题类型定义：
1. BASIC_QUERY（基础查询）：简单的事实性问题，可以直接回答
   - 例如：什么是贝叶斯定理？正态分布的定义是什么？
   - 处理方式：直接回答，不需要搜索论文

2. PROFESSIONAL（专业问题）：需要深入解释的方法论或理论问题
   - 例如：分层模型的MCMC估计方法有哪些？
   - 处理方式：搜索论文后给出专业回答

3. FRONTIER（前沿探索）：关于最新研究进展的问题
   - 例如：2024年统计学习有什么新突破？
   - 处理方式：搜索arXiv最新论文

4. APPLICATION（应用咨询）：关于在实际场景中应用的问题
   - 例如：如何在医学研究中应用倾向性评分？
   - 处理方式：搜索PubMed案例

输出格式（JSON）：
{
    "question_type": "professional",
    "confidence": 0.85,
    "reasoning": "判断理由",
    "suggested_path": "paper_search",
    "filters": {"domain": "statistics", "sort_by": "relevance"}
}
"""
```

### 7.4 生成类Agent提示词示例

```python
system_prompt = """你是一个专业的学术[报告/文献]生成专家。

职责：
1. 确保内容符合学术规范
2. 结构清晰，逻辑连贯
3. 引用规范，有据可查

生成要求：
- 结构：摘要 → 引言 → 方法 → 结果 → 讨论
- 长度：根据要求控制字数
- 格式：Markdown或指定格式
- 引用：使用标准引用格式

输出格式：
{
    "sections": {
        "abstract": "...",
        "introduction": "...",
        "methods": "...",
        "results": "...",
        "discussion": "..."
    },
    "references": [...],
    "quality_score": 0.0-1.0
}
"""
```

### 7.5 Few-Shot Examples写法

```python
FEW_SHOT_EXAMPLES = """
【示例1：专业问题】
输入：我想研究因果推断在医学中的应用
输出：
{
    "question_type": "application",
    "confidence": 0.82,
    "reasoning": "涉及医学领域的实际应用",
    "suggested_path": "pubmed_search",
    "filters": {"domain": "medicine", "time_range": 365}
}

【示例2：前沿探索】
输入：2024年大语言模型有什么新突破？
输出：
{
    "question_type": "frontier",
    "confidence": 0.91,
    "reasoning": "询问最新研究进展",
    "suggested_path": "arxiv_search",
    "filters": {"year": 2024, "sort_by": "recent"}
}
"""

system_prompt = """你是一个问题分类专家...""" + FEW_SHOT_EXAMPLES
```

### 7.6 Chain-of-Thought (CoT) 提示

```python
prompt = f"""
分析以下研究选题的问题：

选题：{topic}
研究者水平：{user_level}

请按以下步骤逐步分析：

步骤1：范围评估
- 判断选题是过于宽泛还是过于狭窄

步骤2：创新性评估
- 分析是否有新颖的研究角度

步骤3：可行性评估
- 评估技术可行性和资源可行性

步骤4：综合诊断
- 汇总上述分析，识别主要问题

输出JSON格式：
{{
    "issues": ["问题1", "问题2"],
    "scope_assessment": {{"too_broad": true/false, "main_issue": "..."}},
    "reasoning": "分析推理过程"
}}
"""
```

### 7.7 JSON输出处理

```python
# 严格Schema + 降级策略
async def _llm_call_with_fallback(self, prompt: str, schema: str) -> Dict:
    try:
        # 尝试严格Schema输出
        response = await self._llm_call(prompt + f"\n\n{schema}")
        return json.loads(response)
    except json.JSONDecodeError:
        # 降级处理：返回原始文本
        return {"raw_output": response, "parse_error": True}
```

### 7.8 质量阈值配置

```python
QUALITY_THRESHOLDS = {
    "diagnostic": 6.0,   # 诊断阶段不需要太高
    "topic": 7.0,
    "literature": 7.0,
    "methodology": 7.0,
    "writing": 7.0,
    "polish": 8.0        # 最终润色需要更高
}
```

### 7.9 提示词设计检查清单

- [ ] 角色定义清晰，避免模糊身份
- [ ] 职责边界明确，防止任务混乱
- [ ] 示例覆盖主要场景（2-3个）
- [ ] 输出格式严格定义（JSON Schema）
- [ ] 包含错误处理和降级策略
- [ ] 设置合理的质量阈值
- [ ] 定义明确的迭代终止条件

---

## 八、完整Agent列表

| Agent | 模块 | 类型 | 核心职责 |
|-------|------|------|----------|
| `QueryRouter` | qa | 路由 | 问题分类、多路径映射 |
| `PaperSearchAgent` | qa | 搜索 | 多源并行搜索 |
| `DailyWatcher` | qa | 报告 | 每日论文监控 |
| `WeeklyReportGenerator` | qa | 报告 | 周报告生成 |
| `MonthlyReportGenerator` | qa | 报告 | 月度报告生成 |
| `PaperFlash` | qa | 快讯 | 热点论文速读 |
| `TopicAgent` | paper_agents | 选题 | 研究方向选择 |
| `OutlineGeneratorAgent` | writing | 大纲 | 结构化大纲 |
| `DraftGeneratorAgent` | writing | 初稿 | 全文撰写 |
| `LiteratureReviewAgent` | writing | 综述 | 文献综述 |
| `SmartReviserAgent` | writing | 改稿 | 意见→修改 |
| `ReportRefinerAgent` | writing | 精炼 | 多轮迭代优化 |
| `LanguagePolisherAgent` | writing | 润色 | 语法术语检查 |
| `ReviewerAgent` | writing | 评审 | 质量评估 |

---

## 技术特性

- **模块化Agent** - 每个功能独立，便于扩展
- **异步优先** - async/await处理IO密集任务
- **降级策略** - JSON解析失败时提供降级输出
- **多源搜索** - 并行搜索多个学术平台
- **流式生成** - 支持打字机效果的流式输出
- **多轮迭代** - 自动迭代优化直到达标
- **全链路追踪** - ChainTracer监控每个阶段

---

## 测试状态

```
总测试数: 2063个 | 通过率: 98.9%
```

---

## 文档

| 文档 | 说明 |
|------|------|
| [论文Agent开发文档](docs/论文Agent开发文档.md) | 完整技术文档（融合需求+架构+小模块） |
| [使用指南](docs/开发文档/使用指南.md) | 完整使用教程 |
| [API文档](docs/开发文档/API文档_完整版.md) | 完整API |
| [迭代报告](docs/开发文档/迭代报告与开发计划.md) | 开发历程与计划 |
| [记忆系统设计](docs/调研报告/Agent记忆系统设计文档.md) | 记忆框架 |

---

## 许可证

MIT License

**最后更新**: 2026-04-27
