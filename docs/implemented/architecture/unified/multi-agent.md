# Multi-Agent Collaboration 多Agent协作详解

> 位置: `src/agents_v2/unified/` (master_supervisor, phase_supervisor, intent_router)

## 一、架构概览

```
unified/
├── __init__.py              # 入口与导出
├── master_supervisor.py     # 全局协调器 (6阶段流水线)
├── phase_supervisor.py      # 阶段监督器
├── circuit_breaker.py       # 熔断保护
├── intent_router.py         # 意图路由 (17种意图)
├── state_model.py           # 状态模型
├── phase_models.py          # 阶段输入模型
├── pydantic_validator.py    # Pydantic验证
├── translation.py           # 翻译包装器
├── error_handler.py         # 错误处理
├── error_recovery.py        # 错误恢复
├── hitl_manager.py          # HITL人工介入管理
├── monitoring.py           # 监控指标
├── cache.py                # 结果缓存
├── agent_loop.py           # Agent循环
├── execution_replay.py     # 执行回放
├── flow_monitoring.py      # 流程监控
├── input_security.py       # 输入安全
└── output_manager.py       # 输出管理
```

## 二、MasterSupervisor 全局协调器

```python
class MasterSupervisor:
    """全局协调器 - 6阶段流水线"""

    PHASES = [
        "diagnostic",   # 诊断
        "topic",        # 选题
        "literature",   # 文献
        "methodology",  # 方法论
        "writing",      # 写作
        "polish"        # 润色
    ]

    # 质量阈值 (0-1 scale)
    QUALITY_THRESHOLDS = {
        "diagnostic": 0.6,
        "topic": 0.7,
        "literature": 0.7,
        "methodology": 0.7,
        "writing": 0.7,
        "polish": 0.8
    }

    async def run(self, task_type: str, input_data: dict) -> PhaseResult:
        """运行流水线"""
        state = self._init_state(input_data)

        for phase in self.PHASES:
            # 执行阶段
            result = await self._run_phase(phase, state)

            # 质量评估
            if result.score < self.QUALITY_THRESHOLDS[phase]:
                result = await self._retry_phase(phase, state)

            # 更新状态
            state.update(result)

        return self._compile_final_result()
```

## 三、阶段流程

```
diagnostic → topic → literature → methodology → writing → polish
    │           │          │            │           │        │
    ▼           ▼          ▼            ▼           ▼        ▼
 问题导向    Pipeline    Pipeline    问题导向    Pipeline  问题导向
  并行诊断    选题        文献综述     指导        写作      修复
```

| 阶段 | 执行模式 | Agent | 质量阈值 |
|------|---------|-------|----------|
| diagnostic | parallel | topic_refiner, literature_mapper, methodology_advisor | 0.6 |
| topic | sequential | topic | 0.7 |
| literature | sequential | literature | 0.7 |
| methodology | adaptive | methodology_advisor, argument_builder | 0.7 |
| writing | adaptive | thesis, outline, draft | 0.7 |
| polish | adaptive | language_polisher, smart_reviser, report_refiner | 0.8 |

## 四、PhaseSupervisor 阶段监督器

```python
class PhaseSupervisor:
    """阶段监督器 - 管理单阶段内的多个Agent"""

    def __init__(self, phase_name: str, execution_mode: str, quality_threshold: float):
        self.phase_name = phase_name
        self.execution_mode = execution_mode  # parallel/sequential/adaptive
        self.quality_threshold = quality_threshold
        self.agents: Dict[str, BaseAgent] = {}
        self.circuit_breaker = CircuitBreaker(phase_name)

    async def run_agents(
        self,
        agents: List[Callable],
        input_data: dict,
        context: dict
    ) -> PhaseResult:
```

## 五、HITL 人工介入管理

```python
class HITLManager:
    """HITL 人工介入管理器"""

    def __init__(self):
        self.enabled = False
        self.intervention_queue: List[InterventionRequest] = []

    async def request_intervention(
        self,
        intervention_type: InterventionType,
        priority: InterventionPriority,
        context: dict
    ) -> InterventionResponse:
        """请求人工介入"""

    def should_interrupt(self, phase: str) -> bool:
        """判断是否应该在某阶段中断等待人工介入"""
        return self.enabled and phase in self.INTERVENTION_POINTS
```

### 5.1 干预类型

| 类型 | 说明 | 优先级 |
|------|------|--------|
| `content_review` | 内容审查 | HIGH |
| `direction_change` | 方向调整 | CRITICAL |
| `quality_escalation` | 质量升级 | MEDIUM |

### 5.2 干预点

```python
INTERVENTION_POINTS = {
    "after_diagnostic": "diagnostic",
    "after_outline": "outline",
    "after_draft": "writing",
    "after_review": "review",
}
```

## 六、监控指标

```python
class MetricsCollector:
    """指标收集器"""

    async def record_phase_duration(self, phase: str, duration: float):
        """记录阶段耗时"""

    async def record_quality_score(self, phase: str, score: float):
        """记录质量分数"""

    def get_phase_stats(self, phase: str) -> Dict[str, Any]:
        """获取阶段统计"""
```

## 七、执行回放

```python
class ExecutionReplay:
    """执行回放 - 用于调试和复现"""

    async def replay(self, execution_id: str):
        """回放指定执行"""

    def save_checkpoint(self, state: dict):
        """保存检查点"""

    def restore_checkpoint(self, checkpoint_id: str) -> dict:
        """恢复检查点"""
```
        """执行阶段内的Agent循环"""
```

## 五、IntentRouter 意图路由

```python
class IntentType(str, Enum):
    # 文献相关 (4种)
    LITERATURE_SEARCH = "literature_search"      # 搜索论文
    LITERATURE_REVIEW = "literature_review"    # 文献综述
    LITERATURE_TRACKING = "literature_tracking" # 文献追踪
    LITERATURE_SUMMARY = "literature_summary"   # 论文总结对比

    # 论文写作相关 (6种)
    TOPIC_SELECT = "topic_select"               # 选题
    THESIS_FORMULATE = "thesis_formulate"       # Thesis凝练
    OUTLINE_GENERATE = "outline_generate"       # 大纲生成
    DRAFT_WRITE = "draft_write"                 # 初稿撰写
    REPORT_REFINE = "report_refine"             # 报告精炼
    PAPER_REVISION = "paper_revision"           # 智能改稿

    # 开题相关 (1种)
    PROPOSAL_GENERATE = "proposal_generate"      # 开题报告

    # 完善相关 (2种)
    LANGUAGE_POLISH = "language_polish"         # 语言润色
    REFERENCE_FORMAT = "reference_format"       # 参考文献处理

    # Pipeline (2种)
    FULL_PAPER = "full_paper"                  # 完整论文流程
    DIAGNOSTIC = "diagnostic"                  # 诊断

    # 未知
    UNKNOWN = "unknown"

# 共17种意图
```

### 路由优先级

```python
intent_priority = {
    IntentType.FULL_PAPER: 100,
    IntentType.DIAGNOSTIC: 90,
    IntentType.DRAFT_WRITE: 80,
    IntentType.PROPOSAL_GENERATE: 70,
    IntentType.LITERATURE_SEARCH: 60,
    IntentType.LITERATURE_REVIEW: 60,
    IntentType.TOPIC_SELECT: 50,
    IntentType.OUTLINE_GENERATE: 40,
    IntentType.LANGUAGE_POLISH: 30,
}
```

## 六、Agent注册表

```python
class MasterSupervisor:
    def register_problem_agents(self):
        """问题导向Agent"""
        self.agents["topic_refiner"] = TopicRefinerAgent()
        self.agents["literature_mapper"] = LiteratureMapperAgent()
        self.agents["methodology_advisor"] = MethodologyAdvisorAgent()
        self.agents["argument_builder"] = ArgumentBuilderAgent()
        self.agents["section_diff"] = SectionDifferentiatorAgent()
        self.agents["discussion_deepener"] = DiscussionDeepenerAgent()
        self.agents["chart_formatter"] = ChartFormatterAgent()
        self.agents["language_polisher"] = LanguagePolisherAgent()
        self.agents["plagiarism_checker"] = PlagiarismCheckerAgent()

    def register_pipeline_agents(self):
        """Pipeline型Agent"""
        self.agents["topic"] = TopicAgent()
        self.agents["literature"] = LiteratureAgent()
        self.agents["outline"] = OutlineAgent()
        self.agents["draft"] = DraftWriterAgent()

    def register_writing_agents(self):
        """写作Agent"""
        self.agents["literature_review"] = LiteratureReviewAgent()
        self.agents["outline_generator"] = OutlineGeneratorAgent()
        self.agents["draft_generator"] = DraftGeneratorAgent()
        self.agents["report_refiner"] = ReportRefinerAgent()
        self.agents["proposal_generator"] = ProposalGeneratorAgent()
        self.agents["reference_processor"] = ReferenceProcessorAgent()
        self.agents["smart_reviser"] = SmartReviserAgent()
        self.agents["language_polisher_writing"] = LanguagePolisherAgent()
```

## 七、意图 → Agent 映射表

| IntentType | Agent 键名 | 说明 |
|------------|-----------|------|
| LITERATURE_SEARCH | `literature` | 多源聚合搜索 |
| LITERATURE_REVIEW | `literature_review` | 检索+筛选+综述 |
| LITERATURE_TRACKING | `literature_review` | 增量监控 |
| LITERATURE_SUMMARY | `literature_review` | 多论文对比 |
| TOPIC_SELECT | `topic` | 候选课题生成 |
| THESIS_FORMULATE | `thesis` | 论点提取 |
| OUTLINE_GENERATE | `outline_generator` | 层级化大纲 |
| DRAFT_WRITE | `draft_generator` | 逐节生成 |
| REPORT_REFINE | `report_refiner` | 多轮精炼 |
| PAPER_REVISION | `smart_reviser` | 迭代修订 |
| PROPOSAL_GENERATE | `proposal_generator` | 开题报告 |
| LANGUAGE_POLISH | `language_polisher_writing` | 语言润色 |
| REFERENCE_FORMAT | `reference_processor` | 参考文献处理 |
| FULL_PAPER | `full_pipeline` | 6阶段流水线 |
| DIAGNOSTIC | `diagnostic_phase` | 问题诊断 |

## 八、状态模型

```python
class PaperState:
    user_request: str
    current_phase: str = "init"
    phase_results: Dict[str, PhaseResult] = {}
    context: Dict[str, Any] = {}
    iteration: int = 0
    max_iterations: int = 3

    def get_quality_level(self) -> QualityLevel:
        """获取质量等级"""

class PhaseStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class QualityLevel(str, Enum):
    EXCELLENT = "excellent"  # ≥0.9
    GOOD = "good"            # ≥0.8
    ACCEPTABLE = "acceptable" # ≥0.7
    MARGINAL = "marginal"    # ≥0.6
    FAILURE = "failure"      # <0.6
```

## 九、熔断保护

```python
class CircuitBreaker:
    def __init__(
        self,
        name: str = "circuit_breaker",
        failure_threshold: int = 5,       # 连续失败次数阈值
        recovery_timeout: float = 60.0,  # 恢复超时时间（秒）
        half_open_max_calls: int = 3      # 半开状态允许的测试调用次数
    ):

class MultiCircuitBreaker:
    """多熔断器管理"""
    def get_circuit(self, name: str) -> CircuitBreaker:
    async def call(self, circuit_name: str, func: Callable, *args, **kwargs) -> Any:
```

---

**更新日期**: 2026-05-03
**基于代码**: `src/agents_v2/unified/`