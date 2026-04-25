# 统一Agent框架 - 融合Pipeline与问题导向

## 一、框架概述

本框架融合了两种Agent设计范式：

1. **Pipeline型Agent** (原paper_agents)
   - 优点：流程清晰、顺序执行、质量稳定
   - 适用：选题、文献、大纲、撰写等线性流程

2. **问题导向型Agent** (原problem_oriented)
   - 优点：针对性强、精准解决问题
   - 适用：诊断、修复、润色等非确定性任务

融合后的框架：
- **诊断阶段**：问题导向Agent并行诊断
- **执行阶段**：Pipeline型Agent顺序执行
- **完善阶段**：问题导向Agent针对性修复

## 二、架构图

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
    MethodologyAdvisor        ThesisAgent             DiscussionDeepener
                               OutlineAgent            ChartFormatter
                               DraftWriterAgent        LanguagePolisher
                               EditorAgent             PlagiarismChecker
                               ReviewerAgent
```

## 三、核心组件

### 3.1 MasterSupervisor

全局协调器，负责：
- 管理全局状态 (PaperState)
- 路由到正确的PhaseSupervisor
- 处理阶段间的流转
- 协调诊断-执行-完善流程

```python
supervisor = MasterSupervisor(llm_config)
result = await supervisor.run("full_paper", {"topic": "深度学习..."})
```

### 3.2 PhaseSupervisor

单阶段协调器，负责：
- 调度阶段内的多个Agent
- 聚合Agent结果
- 评估阶段质量
- 决定是否需要诊断修复

支持三种执行模式：
- **parallel**: 并行执行（诊断阶段）
- **sequential**: 顺序执行（选题、文献阶段）
- **adaptive**: 自适应执行（根据结果动态决定）

### 3.3 PaperState

全局状态管理，包含：
- 当前阶段和阶段历史
- 各阶段的结果
- 诊断发现的问题
- 质量追踪
- 迭代控制

### 3.4 CircuitBreaker

熔断器，防止级联失败：
- CLOSED → OPEN: 失败次数超过阈值
- OPEN → HALF_OPEN: 超过恢复超时
- HALF_OPEN → CLOSED: 请求成功

### 3.5 FallbackHandler

降级处理，当Agent失败时：
- 使用默认/缓存结果
- 跳过可选阶段
- 返回最小可用输出

## 四、工作流程

### 4.1 完整论文流程 (full_paper)

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

### 4.2 诊断-治疗模式

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

### 4.3 迭代改进

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

## 五、问题类型映射

| ProblemType | 对应Agent | 修复策略 |
|------------|----------|---------|
| TOPIC_VAGUE | TopicRefinerAgent | 明确研究范围 |
| TOPIC_TOO_BROAD | TopicRefinerAgent | 缩小选题 |
| LITERATURE_INSUFFICIENT | LiteratureMapperAgent | 扩大文献搜索 |
| ARGUMENT_WEAK | ArgumentBuilderAgent | 重构论证框架 |
| DISCUSSION_SHALLOW | DiscussionDeepenerAgent | 深化讨论 |
| LANGUAGE_POOR | LanguagePolisherAgent | 语言润色 |
| PLAGIARISM_RISK | PlagiarismCheckerAgent | 改写建议 |

## 六、状态模型

```python
@dataclass
class PaperState:
    user_request: str           # 用户输入
    current_phase: str         # 当前阶段
    phase_sequence: List[str]   # 阶段序列
    phase_results: Dict[str, PhaseResult]  # 各阶段结果
    problems: List[ProblemType]            # 发现的问题
    problem_severity: Dict[ProblemType, float]  # 问题严重程度
    iteration: int             # 当前迭代
    quality_history: List[QualityScore]  # 质量历史
```

## 七、错误处理

### 7.1 熔断器状态

```
正常(CLOSED) ──失败阈值突破──> 断开(OPEN)
    ▲                           │
    │                     超时恢复
    │                           │
    └──成功阈值突破────────────┘
              半开(HALF_OPEN)
```

### 7.2 降级策略

每个阶段都有降级输出：
- topic: 默认选题
- literature: 空文献列表
- writing: 基本大纲
- polish: 保持原样

## 八、使用示例

### 8.1 完整流程

```python
from src.agents_v2.unified import MasterSupervisor, LLMConfig

config = LLMConfig(provider="openai", model_name="gpt-4")
supervisor = MasterSupervisor(config)

# 注册所有Agent
supervisor.register_problem_agents()
supervisor.register_pipeline_agents()

# 运行完整流程
result = await supervisor.run("full_paper", {
    "user_request": "深度学习在医学影像诊断中的应用"
})

print(result["final_paper"])
print(f"Quality: {result['final_quality']}")
```

### 8.2 只诊断

```python
result = await supervisor.run("diagnostic_only", {
    "user_request": "深度学习在医学影像诊断中的应用"
})

print(result["problems"])  # 发现的问题列表
print(result["recommendations"])  # 建议
```

### 8.3 问题聚焦修复

```python
result = await supervisor.run("problem_focused", {
    "problems": [ProblemType.ARGUMENT_WEAK, ProblemType.LANGUAGE_POOR],
    "content": {
        "text": "论文内容...",
        "thesis": "研究论点..."
    }
})
```

## 九、与旧框架的关系

| 旧模块 | 新框架中的位置 | 说明 |
|--------|---------------|------|
| paper_agent.py | Pipeline Phase | 单一Agent模式，重组为PhaseSupervisor |
| paper_agents/ | Pipeline Agents | TopicAgent, LiteratureAgent等 |
| problem_oriented/ | Problem-Solving Agents | 9个针对性Agent |
| supervisor/ | PhaseSupervisor + MasterSupervisor | 协调机制融合 |

## 十、扩展点

1. **新增Agent类型**: 在对应模块实现后注册到MasterSupervisor
2. **自定义流程**: 通过_run_custom_flow扩展
3. **自定义质量评估**: 继承PhaseSupervisor重写_evaluate_quality
4. **自定义路由**: 继承MasterSupervisor重写RoutingPolicy