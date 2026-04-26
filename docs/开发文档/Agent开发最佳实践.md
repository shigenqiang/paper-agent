# Agent开发最佳实践指南

## 一、核心原则

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
Agent = LLM + Memory + Planning + Tools

增强型LLM (Augmented LLM)：
├── 检索 (Retrieval)
├── 工具 (Tools)
└── 记忆 (Memory)
```

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
- Microsoft: [AI Agents for Beginners](https://github.com/microsoft/ai-agents-for-beginners)
- LangGraph Documentation: [LangGraph](https://langchain.dev/langgraph)
- CrewAI: [Multi-Agent Architecture](https://github.com/crewAI/crewAI)
- 论文写作范式：各学科顶会/顶刊 guidelines (CVPR, NeurIPS, ACL, Nature, etc.)
