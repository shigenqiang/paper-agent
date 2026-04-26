# Paper Agent 超详细开发计划 - 迭代版 (Iteration 21-25)

**项目**: Paper Agent
**版本**: v0.3 (细节打磨版)
**目标**: 达到 10.0/10.0 评分
**新增迭代**: 5次 (Iteration 21-25)
**最后更新**: 2026-04-27

---

## 文档目的

本计划专注于Agent处理流程中的**每个细节步骤**，对照最新Agent框架论文和最佳实践，找出当前实现中的缺失，并给出可执行的具体任务。

---

## 一、当前Agent处理流程详解与差距分析

### 1.1 完整处理流程图（当前实现）

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INTENT ROUTING 阶段                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │ 关键词匹配   │ -> │ LLM辅助识别  │ -> │ 意图类型确认 │                   │
│  │ (快速路径)   │    │ (复杂情况)   │    │              │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MASTER SUPERVISOR 协调阶段                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │ 状态初始化   │ -> │ PhaseSupervisor │ -> │ 质量检查    │                   │
│  │ (PaperState) │    │ (按阶段执行)  │    │              │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT 执行阶段                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │ 输入验证     │ -> │ LLM调用      │ -> │ 输出解析     │                   │
│  │             │    │              │    │              │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│         │                                       │                           │
│         v                                       v                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │ 上下文准备   │    │ 工具调用     │    │ 结果验证     │                   │
│  │             │    │              │    │              │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY 记忆阶段                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │ 短期记忆     │ -> │ 会话记忆     │ -> │ 长期记忆     │                   │
│  │ (ShortTerm)  │    │ (Session)   │    │ (LongTerm)   │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
用户输出
```

---

## 二、Iteration 21: Intent Routing 细节打磨

### 2.1 当前实现问题

**文件**: `src/agents_v2/unified/intent_router.py`

**当前问题**:
1. 关键词匹配是简单的子串搜索，没有考虑同义词、变体
2. LLM辅助识别只做简单的意图分类，没有置信度校准
3. 没有意图消歧机制（用户表达模糊时）
4. 没有意图澄清对话机制
5. 协作意图识别简单，没有分析子任务依赖

### 2.2 详细改进任务

#### Task 21.1: 关键词语义扩展

```python
# src/agents_v2/unified/intent_router.py 新增

class SemanticKeywordExpander:
    """
    语义关键词扩展器

    将用户输入的关键词扩展为同义词、上下位词、相关词

    扩展策略:
    1. 同义词扩展 (深度学习 -> 机器学习、神经网络)
    2. 上下位词 (AI -> 人工智能)
    3. 常见变体 (论文 -> 文章、学术论文)
    4. 英文缩写 (NLP -> Natural Language Processing)
    """

    def __init__(self):
        # 领域知识库 - 应从配置或知识图谱加载
        self._synonym_map = {
            "论文": ["文章", "学术论文", "研究论文", "paper"],
            "搜索": ["查找", "检索", "寻找", "search", "find"],
            "文献": ["论文", "参考", "参考资料", "literature", "references"],
            "选题": ["主题", "研究方向", "课题", "topic", "research topic"],
            "润色": ["修改", "完善", "优化", "polish", "refine"],
            "综述": ["总结", "概述", "survey", "review"],
        }

        self._hyponym_map = {
            "AI": ["人工智能", "Artificial Intelligence"],
            "ML": ["机器学习", "Machine Learning"],
            "DL": ["深度学习", "Deep Learning"],
            "NLP": ["自然语言处理", "Natural Language Processing"],
            "CV": ["计算机视觉", "Computer Vision"],
        }

    def expand(self, keyword: str) -> List[str]:
        """扩展关键词"""
        expanded = [keyword]

        # 同义词扩展
        if keyword in self._synonym_map:
            expanded.extend(self._synonym_map[keyword])

        # 上下位词扩展
        for hyper, hypos in self._hyponym_map.items():
            if keyword.lower() in hypos or keyword in hypos:
                expanded.append(hyper)
                expanded.extend([h for h in hypos if h != keyword])

        # 变体扩展
        expanded.extend(self._generate_variants(keyword))

        # 去重
        return list(dict.fromkeys(expanded))

    def _generate_variants(self, keyword: str) -> List[str]:
        """生成变体"""
        variants = []

        # 中文变体
        if keyword.endswith("论文"):
            variants.append(keyword.replace("论文", "文章"))
        if keyword.endswith("研究"):
            variants.append(keyword.replace("研究", "分析"))

        # 英文大小写变体
        if keyword.islower():
            variants.append(keyword.capitalize())
        if keyword.isupper():
            variants.append(keyword.lower())

        return variants
```

#### Task 21.2: 多意图检测与消歧

```python
# src/agents_v2/unified/intent_router.py 新增

@dataclass
class IntentCandidate:
    """意图候选"""
    intent_type: IntentType
    confidence: float
    reasoning: str
    required_slots: List[str]           # 需要填充的槽位
    missing_info: List[str]            # 缺失信息

class IntentDisambiguator:
    """
    意图消歧器

    当用户输入可能匹配多个意图时，启动消歧对话

    场景:
    1. "搜索深度学习" -> 可能是literature_search或topic_select
    2. "润色论文" -> 可能是language_polish或full_paper的局部修改
    """

    def __init__(self, llm: Any = None):
        self.llm = llm

    async def detect_multiple_intents(
        self,
        user_request: str
    ) -> List[IntentCandidate]:
        """检测多意图"""

        prompt = f"""
分析以下用户请求，可能存在多个意图：

用户请求：{user_request}

请分析：
1. 主要意图是什么？
2. 是否存在次要意图？
3. 这些意图之间的关系（并行/顺序/依赖）？

返回JSON格式：
{{
    "intents": [
        {{
            "type": "意图类型",
            "confidence": 0.0-1.0,
            "reasoning": "判断理由",
            "required_slots": ["需要的槽位"],
            "missing_info": ["缺失的信息"]
        }}
    ],
    "intent_relationships": "intents间的关系描述"
}}
"""
        # 解析LLM响应
        # 返回意图候选列表

    async def generate_clarification_question(
        self,
        ambiguous_request: str,
        candidates: List[IntentCandidate]
    ) -> str:
        """生成澄清问题"""
        # 当意图置信度接近时，生成澄清问题
        pass

    async def fill_slots_from_context(
        self,
        intent: IntentCandidate,
        context: Dict[str, Any]
    ) -> IntentCandidate:
        """从上下文填充槽位"""
        # 尝试从对话历史、用户画像等填充缺失信息
        pass
```

#### Task 21.3: 协作意图分解

```python
# src/agents_v2/unified/intent_router.py 新增

class CollaborationIntentDecomposer:
    """
    协作意图分解器

    将复杂意图分解为多个子任务的协作流程

    示例:
    输入: "帮我写一篇关于深度学习在医学影像诊断的论文"
    分解:
    1. topic_select: 选题确认
    2. literature_search: 文献搜索
    3. literature_review: 文献综述
    4. outline_generate: 大纲生成
    5. draft_write: 初稿撰写

    协作模式:
    - 顺序依赖: 1 -> 2 -> 3 -> 4 -> 5
    - 并行执行: [2, 3] 可并行（文献搜索和综述可同时进行）
    - 数据依赖: 2的输出作为3的输入
    """

    def __init__(self):
        # 意图依赖图
        self._intent_dependencies = {
            IntentType.LITERATURE_REVIEW: [IntentType.LITERATURE_SEARCH],
            IntentType.OUTLINE_GENERATE: [IntentType.LITERATURE_REVIEW],
            IntentType.DRAFT_WRITE: [IntentType.OUTLINE_GENERATE],
            IntentType.FULL_PAPER: [
                IntentType.TOPIC_SELECT,
                IntentType.LITERATURE_SEARCH,
                IntentType.LITERATURE_REVIEW,
                IntentType.OUTLINE_GENERATE,
                IntentType.DRAFT_WRITE
            ]
        }

        # 可并行的意图组
        self._parallel_groups = [
            [IntentType.LITERATURE_SEARCH, IntentType.LITERATURE_TRACKING],
            [IntentType.LANGUAGE_POLISH, IntentType.REFERENCE_FORMAT],
        ]

    def decompose(
        self,
        intent: IntentType,
        context: Dict[str, Any]
    ) -> List[SubTask]:
        """
        分解协作意图

        Returns:
            子任务列表，包含:
            - sub_task_id
            - intent_type
            - dependencies (依赖的sub_task_id)
            - can_parallel_with (可并行的sub_task_id)
            - input_slots
            - output_slots
        """
        pass

    def build_execution_plan(
        self,
        sub_tasks: List[SubTask]
    ) -> ExecutionPlan:
        """
        构建执行计划

        生成:
        1. 执行顺序（拓扑排序）
        2. 可并行的任务组
        3. 数据流动图
        """
        pass
```

#### Task 21.4: 意图置信度校准

```python
# src/agents_v2/unified/intent_router.py 新增

class IntentConfidenceCalibrator:
    """
    意图置信度校准器

    基于历史数据校准意图识别的置信度
    防止模型过度自信或过度不自信
    """

    def __init__(self):
        self._calibration_data: Dict[IntentType, List[CalibrationPoint]] = {}
        self._default_temperature = 1.0

    def calibrate(
        self,
        raw_confidence: float,
        intent_type: IntentType,
        context_features: Dict[str, Any]
    ) -> float:
        """
        校准置信度

        输入:
        - raw_confidence: LLM返回的原始置信度
        - intent_type: 意图类型
        - context_features: 上下文特征（输入长度、关键词匹配数等）

        输出:
        - 校准后的置信度
        """
        # 1. 基于意图类型调整
        base_adjustment = self._get_intent_type_adjustment(intent_type)

        # 2. 基于上下文特征调整
        context_adjustment = self._get_context_adjustment(context_features)

        # 3. 基于历史校准数据
        historical_adjustment = self._get_historical_adjustment(
            intent_type, raw_confidence
        )

        # 综合调整
        calibrated = raw_confidence * base_adjustment * context_adjustment * historical_adjustment

        return max(0.0, min(1.0, calibrated))

    def _get_intent_type_adjustment(self, intent_type: IntentType) -> float:
        """根据意图类型获取调整系数"""
        # 某些意图更容易误识别，需要更大校准
        adjustment_map = {
            IntentType.UNKNOWN: 0.8,       # 未知意图降低置信度
            IntentType.FULL_PAPER: 0.9,     # 复杂意图略微降低
            IntentType.LITERATURE_SEARCH: 1.1,  # 简单意图可略微提高
        }
        return adjustment_map.get(intent_type, 1.0)

    def update_calibration(
        self,
        intent_type: IntentType,
        predicted_confidence: float,
        actual_correct: bool
    ) -> None:
        """更新校准数据"""
        # 记录预测结果，用于后续校准
        self._calibration_data[intent_type].append(
            CalibrationPoint(
                predicted=predicted_confidence,
                actual_correct=actual_correct,
                timestamp=time.time()
            )
        )
```

### 2.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 语义关键词扩展 | 同义词覆盖>90% | 测试"论文"扩展出"文章、学术论文"等 |
| 多意图检测 | 识别出>80%的多意图 | "搜索深度学习论文并润色"检测到2个意图 |
| 意图消歧 | 澄清对话自然流畅 | 用户模糊输入触发合适的问题 |
| 协作分解 | 分解出正确的依赖关系 | full_paper分解出5个以上子任务 |
| 置信度校准 | 校准后准确率提升10% | 对比校准前后的实际准确率 |

---

## 三、Iteration 22: MasterSupervisor 协调细节打磨

### 3.1 当前实现问题

**文件**: `src/agents_v2/unified/master_supervisor.py`

**当前问题**:
1. 阶段流转是硬编码的，没有灵活的重试机制
2. 质量评估只有最终分数，没有过程质量追踪
3. 错误恢复是简单的fallback，没有细粒度策略
4. 没有执行回放功能（当Agent执行慢时）
5. 阶段间的数据传递没有版本控制

### 3.2 详细改进任务

#### Task 22.1: 阶段执行状态机

```python
# src/agents_v2/unified/phase_supervisor.py 增强

class PhaseExecutionStateMachine:
    """
    阶段执行状态机

    每个阶段有详细的状态转换：

    状态:
    PENDING -> RUNNING -> WAITING_INPUT -> COMPLETED
                      -> RETRYING -> RUNNING
                      -> FAILED

    转换规则:
    1. PENDING -> RUNNING: 开始执行
    2. RUNNING -> WAITING_INPUT: 等待外部输入（如人类确认）
    3. RUNNING -> RETRYING: 质量不达标，准备重试
    4. RETRYING -> RUNNING: 执行重试
    5. RUNNING -> COMPLETED: 质量达标
    6. RUNNING -> FAILED: 不可恢复错误
    7. WAITING_INPUT -> RUNNING: 输入到达
    8. WAITING_INPUT -> FAILED: 超时
    """

    def __init__(self, phase_name: str):
        self.phase_name = phase_name
        self._state = PhaseExecutionState.PENDING
        self._state_history: List[StateTransition] = []
        self._retry_count = 0
        self._max_retries = 3

    def transition(self, new_state: PhaseExecutionState, reason: str) -> bool:
        """执行状态转换"""
        # 验证转换合法性
        if not self._can_transition(self._state, new_state):
            return False

        # 记录转换
        self._state_history.append(StateTransition(
            from_state=self._state,
            to_state=new_state,
            reason=reason,
            timestamp=time.time()
        ))

        self._state = new_state
        return True

    def _can_transition(
        self,
        from_state: PhaseExecutionState,
        to_state: PhaseExecutionState
    ) -> bool:
        """检查状态转换是否合法"""
        # 定义合法的状态转换
        valid_transitions = {
            PhaseExecutionState.PENDING: [PhaseExecutionState.RUNNING],
            PhaseExecutionState.RUNNING: [
                PhaseExecutionState.COMPLETED,
                PhaseExecutionState.RETRYING,
                PhaseExecutionState.FAILED,
                PhaseExecutionState.WAITING_INPUT
            ],
            PhaseExecutionState.RETRYING: [PhaseExecutionState.RUNNING],
            PhaseExecutionState.WAITING_INPUT: [
                PhaseExecutionState.RUNNING,
                PhaseExecutionState.FAILED
            ],
        }

        return to_state in valid_transitions.get(from_state, [])

    def get_state(self) -> PhaseExecutionState:
        """获取当前状态"""
        return self._state

    def get_retry_decision(self, quality_score: float) -> RetryDecision:
        """
        根据质量分数做出重试决策

        Returns:
            RetryDecision: 包含是否重试、重试策略等信息
        """
        if self._retry_count >= self._max_retries:
            return RetryDecision(action=RetryAction.ABORT, reason="Max retries exceeded")

        if quality_score >= 0.8:
            return RetryDecision(action=RetryAction.COMPLETE, reason="Quality acceptable")

        if quality_score >= 0.5:
            # 质量一般，可以重试
            self._retry_count += 1
            return RetryDecision(
                action=RetryAction.RETRY,
                strategy=self._suggest_retry_strategy(),
                remaining_retries=self._max_retries - self._retry_count
            )

        if quality_score >= 0.3:
            # 质量较差，需要大幅改进
            self._retry_count += 1
            return RetryDecision(
                action=RetryAction.RETRY,
                strategy=RetryStrategy.FUNDAMENTAL_CHANGE,
                remaining_retries=self._max_retries - self._retry_count
            )

        # 质量太差
        return RetryDecision(action=RetryAction.ABORT, reason="Quality too low")
```

#### Task 22.2: 过程质量追踪

```python
# src/agents_v2/unified/phase_supervisor.py 新增

@dataclass
class QualityCheckpoint:
    """质量检查点"""
    checkpoint_id: str
    phase_name: str
    sub_step: str                    # 子步骤名称
    timestamp: float

    # 质量维度
    completeness: float = 0.0        # 完整性 (0-1)
    correctness: float = 0.0       # 正确性 (0-1)
    coherence: float = 0.0          # 连贯性 (0-1)
    relevance: float = 0.0          # 相关性 (0-1)

    # 元数据
    input_quality: float = 0.0      # 输入质量
    processing_time_ms: float = 0.0
    tokens_used: int = 0

    # 问题标记
    issues_detected: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class ProcessQualityTracker:
    """
    过程质量追踪器

    在Agent执行的每个关键节点记录质量数据
    形成完整的质量变化曲线
    """

    def __init__(self, phase_name: str):
        self.phase_name = phase_name
        self._checkpoints: List[QualityCheckpoint] = []
        self._quality_thresholds = {
            "completeness": 0.7,
            "correctness": 0.75,
            "coherence": 0.7,
            "relevance": 0.8
        }

    def record_checkpoint(
        self,
        sub_step: str,
        quality_metrics: Dict[str, float],
        metadata: Dict[str, Any]
    ) -> QualityCheckpoint:
        """记录质量检查点"""
        checkpoint = QualityCheckpoint(
            checkpoint_id=f"{self.phase_name}_{sub_step}_{int(time.time()*1000)}",
            phase_name=self.phase_name,
            sub_step=sub_step,
            timestamp=time.time(),
            completeness=quality_metrics.get("completeness", 0.0),
            correctness=quality_metrics.get("correctness", 0.0),
            coherence=quality_metrics.get("coherence", 0.0),
            relevance=quality_metrics.get("relevance", 0.0),
            input_quality=metadata.get("input_quality", 0.0),
            processing_time_ms=metadata.get("processing_time_ms", 0.0),
            tokens_used=metadata.get("tokens_used", 0),
            issues_detected=metadata.get("issues", []),
            suggestions=metadata.get("suggestions", [])
        )

        self._checkpoints.append(checkpoint)

        # 检查是否需要预警
        self._check_quality_alerts(checkpoint)

        return checkpoint

    def _check_quality_alerts(self, checkpoint: QualityCheckpoint) -> None:
        """检查质量告警"""
        for dimension, threshold in self._quality_thresholds.items():
            value = getattr(checkpoint, dimension, 0.0)
            if value < threshold:
                logger.warning(
                    f"Quality alert: {self.phase_name}.{checkpoint.sub_step}.{dimension} "
                    f"= {value:.2f} < {threshold}"
                )

    def get_quality_trend(self) -> QualityTrend:
        """获取质量趋势"""
        if not self._checkpoints:
            return QualityTrend(status="no_data")

        # 计算各维度的趋势
        completeness_trend = self._calculate_trend("completeness")
        correctness_trend = self._calculate_trend("correctness")

        overall_score = sum(
            getattr(c, dim, 0.0)
            for c in self._checkpoints
            for dim in ["completeness", "correctness", "coherence", "relevance"]
        ) / (len(self._checkpoints) * 4)

        return QualityTrend(
            phase_name=self.phase_name,
            checkpoint_count=len(self._checkpoints),
            overall_score=overall_score,
            completeness_trend=completeness_trend,
            correctness_trend=correctness_trend,
            issues_count=sum(len(c.issues_detected) for c in self._checkpoints),
            average_processing_time=sum(c.processing_time_ms for c in self._checkpoints) / len(self._checkpoints)
        )

    def get_bottlenecks(self) -> List[str]:
        """获取瓶颈分析"""
        bottlenecks = []

        # 检查处理时间异常
        avg_time = sum(c.processing_time_ms for c in self._checkpoints) / len(self._checkpoints)
        slow_checkpoints = [c for c in self._checkpoints if c.processing_time_ms > avg_time * 2]
        if slow_checkpoints:
            bottlenecks.append(f"Slow processing: {[c.sub_step for c in slow_checkpoints]}")

        # 检查质量问题
        low_quality = [c for c in self._checkpoints if c.correctness < 0.6]
        if low_quality:
            bottlenecks.append(f"Low correctness: {[c.sub_step for c in low_quality]}")

        return bottlenecks
```

#### Task 22.3: 细粒度错误恢复策略

```python
# src/agents_v2/unified/error_handler.py 增强

class GranularErrorRecovery:
    """
    细粒度错误恢复策略

    根据错误类型、上下文、严重程度选择最优恢复策略
    """

    # 错误类型 -> 恢复策略映射
    ERROR_RECOVERY_STRATEGY_MAP = {
        ErrorCategory.INVALID_INPUT: [
            {"strategy": "validate_and_retry", "timeout": 5, "max_attempts": 2},
            {"strategy": "use_defaults", "timeout": 1, "max_attempts": 1},
        ],
        ErrorCategory.TIMEOUT: [
            {"strategy": "retry_with_backoff", "timeout": 30, "max_attempts": 3},
            {"strategy": "reduce_scope", "timeout": 15, "max_attempts": 1},
        ],
        ErrorCategory.LLM_RATE_LIMIT: [
            {"strategy": "rate_limit_backoff", "timeout": 60, "max_attempts": 5},
            {"strategy": "switch_to_cache", "timeout": 5, "max_attempts": 1},
        ],
        ErrorCategory.LLM_CONTEXT_OVERFLOW: [
            {"strategy": "truncate_context", "timeout": 10, "max_attempts": 1},
            {"strategy": "summarize_history", "timeout": 30, "max_attempts": 2},
            {"strategy": "split_task", "timeout": 60, "max_attempts": 1},
        ],
        ErrorCategory.EXTERNAL_SERVICE_ERROR: [
            {"strategy": "retry", "timeout": 15, "max_attempts": 3},
            {"strategy": "fallback_to_cache", "timeout": 5, "max_attempts": 1},
            {"strategy": "skip_with_warning", "timeout": 1, "max_attempts": 1},
        ],
    }

    def __init__(self):
        self._recovery_history: List[RecoveryRecord] = []
        self._strategy_success_rates: Dict[str, float] = {}

    def get_recovery_plan(
        self,
        error: ErrorRecord,
        context: RecoveryContext
    ) -> RecoveryPlan:
        """
        生成恢复计划

        Args:
            error: 错误记录
            context: 恢复上下文（包含当前状态、可用的fallback等）

        Returns:
            RecoveryPlan: 包含具体的恢复步骤
        """
        strategies = self.ERROR_RECOVERY_STRATEGY_MAP.get(
            error.category,
            [{"strategy": "log_and_continue", "timeout": 5, "max_attempts": 1}]
        )

        # 选择最佳策略（基于历史成功率）
        best_strategy = self._select_best_strategy(strategies)

        # 生成具体的恢复步骤
        plan = self._generate_recovery_steps(
            best_strategy,
            error,
            context
        )

        return plan

    def _select_best_strategy(
        self,
        strategies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """选择最佳策略（基于历史成功率）"""
        for strategy in strategies:
            strategy_name = strategy["strategy"]
            success_rate = self._strategy_success_rates.get(strategy_name, 0.5)

            if success_rate >= 0.7:
                return strategy

        # 如果没有高成功率策略，返回第一个
        return strategies[0]

    def _generate_recovery_steps(
        self,
        strategy: Dict[str, Any],
        error: ErrorRecord,
        context: RecoveryContext
    ) -> RecoveryPlan:
        """生成具体的恢复步骤"""
        strategy_name = strategy["strategy"]

        if strategy_name == "retry_with_backoff":
            return RecoveryPlan(
                steps=[
                    RecoveryStep(
                        action="wait",
                        duration=self._calculate_backoff(context.attempt_count),
                        description=f"等待{self._calculate_backoff(context.attempt_count)}秒后重试"
                    ),
                    RecoveryStep(
                        action="retry",
                        target=context.failed_operation,
                        parameters=self._prepare_retry_params(context),
                        description=f"重试操作 {context.failed_operation}"
                    )
                ],
                estimated_time=sum(s.duration for s in [
                    RecoveryStep(action="wait", duration=self._calculate_backoff(context.attempt_count)),
                    RecoveryStep(action="retry", duration=10)
                ])
            )

        elif strategy_name == "truncate_context":
            return RecoveryPlan(
                steps=[
                    RecoveryStep(
                        action="analyze_context",
                        target="context_window",
                        description="分析上下文哪些部分可以截断"
                    ),
                    RecoveryStep(
                        action="truncate",
                        target="oldest_messages",
                        parameters={"keep_recent": context.max_tokens // 2},
                        description="截断历史消息，保留最近一半"
                    ),
                    RecoveryStep(
                        action="retry",
                        target=context.failed_operation,
                        description="重试操作"
                    )
                ]
            )

        elif strategy_name == "switch_to_cache":
            return RecoveryPlan(
                steps=[
                    RecoveryStep(
                        action="check_cache",
                        target=context.failed_operation,
                        description="检查是否有缓存的可用结果"
                    ),
                    RecoveryStep(
                        action="use_cached_result",
                        condition="cache_hit",
                        description="使用缓存结果"
                    )
                ],
                fallback=self._get_fallback_plan(context)
            )

    def record_recovery_result(
        self,
        strategy_name: str,
        success: bool,
        duration: float
    ) -> None:
        """记录恢复结果用于学习"""
        # 更新成功率统计
        if strategy_name not in self._strategy_success_rates:
            self._strategy_success_rates[strategy_name] = 0.5

        current = self._strategy_success_rates[strategy_name]
        # 指数移动平均
        self._strategy_success_rates[strategy_name] = current * 0.9 + (1.0 if success else 0.0) * 0.1

        self._recovery_history.append(RecoveryRecord(
            strategy=strategy_name,
            success=success,
            duration=duration,
            timestamp=time.time()
        ))
```

#### Task 22.4: 执行回放功能

```python
# src/agents_v2/unified/master_supervisor.py 新增

class ExecutionReplay:
    """
    执行回放功能

    当Agent执行时间过长时，可以回放之前的执行状态
    支持:
    1. 慢查询检测与警告
    2. 执行过程回放
    3. 部分结果提前返回
    """

    def __init__(self):
        self._replay_buffer: Dict[str, List[ReplayEntry]] = {}
        self._slow_threshold_ms = 30000  # 30秒

    def start_recording(
        self,
        task_id: str,
        agent_id: str,
        operation: str
    ) -> str:
        """开始记录执行"""
        recording_id = f"{task_id}_{agent_id}_{int(time.time()*1000)}"

        self._replay_buffer[recording_id] = [
            ReplayEntry(
                event_type="start",
                timestamp=time.time(),
                data={"operation": operation}
            )
        ]

        return recording_id

    def record_progress(
        self,
        recording_id: str,
        progress: float,
        partial_result: Any = None
    ) -> None:
        """记录进度"""
        if recording_id not in self._replay_buffer:
            return

        entry = ReplayEntry(
            event_type="progress",
            timestamp=time.time(),
            data={
                "progress": progress,
                "partial_result": partial_result
            }
        )

        self._replay_buffer[recording_id].append(entry)

    def check_slow_execution(
        self,
        recording_id: str,
        expected_duration_ms: float
    ) -> SlowExecutionWarning:
        """检查是否执行过慢"""
        if recording_id not in self._replay_buffer:
            return None

        entries = self._replay_buffer[recording_id]
        start_time = entries[0].timestamp if entries else time.time()
        elapsed = (time.time() - start_time) * 1000

        if elapsed > self._slow_threshold_ms:
            return SlowExecutionWarning(
                recording_id=recording_id,
                elapsed_ms=elapsed,
                expected_ms=expected_duration_ms,
                slowdown_factor=elapsed / expected_duration_ms if expected_duration_ms > 0 else 0,
                progress=entries[-1].data.get("progress", 0) if entries else 0,
                partial_result=entries[-1].data.get("partial_result")
            )

        return None

    def generate_early_result(
        self,
        recording_id: str,
        quality_threshold: float = 0.6
    ) -> Optional[EarlyResult]:
        """生成提前结果"""
        if recording_id not in self._replay_buffer:
            return None

        entries = self._replay_buffer[recording_id]

        # 找到最新的部分结果
        for entry in reversed(entries):
            if entry.event_type == "progress" and entry.data.get("partial_result"):
                partial = entry.data["partial_result"]

                # 检查部分结果的质量
                if self._estimate_quality(partial) >= quality_threshold:
                    return EarlyResult(
                        partial_result=partial,
                        completeness=entry.data.get("progress", 0),
                        is_final=False,
                        estimated_remaining_time=self._estimate_remaining_time(
                            entry.data.get("progress", 0),
                            entry.timestamp - entries[0].timestamp
                        )
                    )

        return None

    def replay(
        self,
        recording_id: str
    ) -> List[ReplayEntry]:
        """回放执行过程"""
        return self._replay_buffer.get(recording_id, [])
```

### 3.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 状态机 | 6种状态正确转换 | 测试所有合法/非法转换 |
| 过程质量追踪 | 每阶段5+检查点 | 验证质量曲线生成 |
| 错误恢复 | 6种错误类型×3种策略 | 测试每种组合 |
| 执行回放 | 慢查询检测<100ms | 检测30秒+的执行 |
| 回放内容 | 完整恢复执行状态 | 回放结果与原结果一致 |

---

## 四、Iteration 23: Agent执行细节打磨

### 4.1 当前实现问题

**文件**: `src/agents_v2/base_agent.py`, `src/agents_v2/problem_oriented/topic_refiner.py`

**当前问题**:
1. Agent执行没有详细的步骤拆解（Thought -> Action -> Observation）
2. LLM调用没有重试机制和降级策略
3. 工具调用结果没有验证和后处理
4. 输出解析是简单的JSON解析，没有容错
5. 上下文注入是简单的拼接，没有智能压缩

### 4.2 详细改进任务

#### Task 23.1: ReAct执行循环细粒度控制

```python
# src/agents_v2/base_agent.py 增强

class ReActExecutor:
    """
    ReAct执行器

    实现详细的思考-行动-观察循环

    每轮执行:
    1. Thought: 分析当前状态，决定下一步
    2. Action: 执行行动（工具调用或LLM生成）
    3. Observation: 观察结果，更新状态
    4. 判断是否继续或结束
    """

    def __init__(self, agent: BaseAgent):
        self.agent = agent
        self.max_iterations = 10
        self.max_tool_calls = 5

    async def execute(
        self,
        task: str,
        context: AgentContext,
        callbacks: Optional[ExecutionCallbacks] = None
    ) -> ReActResult:
        """
        执行ReAct循环

        Returns:
            ReActResult: 包含完整的执行轨迹
        """
        trace = []
        current_state = {"task": task, "observations": [], "next_action": None}

        for iteration in range(self.max_iterations):
            # 1. Thought阶段
            thought = await self._think(current_state, context)
            trace.append(ThoughtStep(
                iteration=iteration,
                thought=thought.reasoning,
                confidence=thought.confidence
            ))

            # 2. 决定行动
            if thought.next_action.type == "tool_call":
                # 工具调用
                result = await self._execute_tool(
                    thought.next_action.tool_name,
                    thought.next_action.parameters
                )
                trace.append(ActionStep(
                    iteration=iteration,
                    action_type="tool",
                    tool_name=thought.next_action.tool_name,
                    result=result
                ))

                # 3. Observation
                observation = self._process_observation(result)
                current_state["observations"].append(observation)

            elif thought.next_action.type == "final_answer":
                # 完成
                trace.append(FinishStep(
                    iteration=iteration,
                    final_answer=thought.next_action.answer
                ))
                return ReActResult(
                    success=True,
                    final_answer=thought.next_action.answer,
                    trace=trace,
                    iterations=iteration + 1
                )

            # 检查是否超时或达到最大调用次数
            if len(trace) >= self.max_tool_calls:
                break

        # 达到最大迭代
        return ReActResult(
            success=False,
            final_answer=current_state["observations"][-1] if current_state["observations"] else None,
            trace=trace,
            iterations=self.max_iterations,
            error="Max iterations exceeded"
        )

    async def _think(
        self,
        state: Dict[str, Any],
        context: AgentContext
    ) -> Thought:
        """
        思考下一步行动

        使用专门的小模型进行快速决策
        大模型只在关键节点使用
        """
        prompt = self._build_thinking_prompt(state, context)

        # 使用小模型快速决策（成本考虑）
        response = await self.agent._llm_call(prompt, model="gpt-3.5-turbo")

        return self._parse_thought(response)

    def _build_thinking_prompt(
        self,
        state: Dict[str, Any],
        context: AgentContext
    ) -> str:
        """构建思考提示"""
        recent_observations = state["observations"][-3:] if state["observations"] else []

        return f"""
当前任务: {state['task']}

最近的观察结果:
{chr(10).join([f"- {obs}" for obs in recent_observations])}

可用工具:
{self._format_available_tools()}

请决定下一步行动。考虑：
1. 当前最需要什么信息？
2. 是否有足够的信息生成答案？
3. 应该使用哪个工具？

输出JSON格式：
{{
    "reasoning": "你的思考过程",
    "confidence": 0.0-1.0,
    "next_action": {{
        "type": "tool_call" | "final_answer",
        "tool_name": "工具名称（如果是tool_call）",
        "parameters": {{...}}（如果是tool_call）,
        "answer": "最终答案（如果是final_answer）"
    }}
}}
"""
```

#### Task 23.2: LLM调用多层降级策略

```python
# src/agents_v2/base_agent.py 新增

class LLMCallWithFallback:
    """
    带降级策略的LLM调用

    层级降级:
    1. 主模型 (gpt-4)
    2. 次级模型 (gpt-3.5-turbo)
    3. 本地模型 (llama3:70b)
    4. 缓存结果
    5. 默认回复
    """

    def __init__(self):
        self._model_configs = {
            "primary": {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2048,
                "timeout": 30
            },
            "secondary": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.5,
                "max_tokens": 1024,
                "timeout": 15
            },
            "local": {
                "model": "llama3:70b",
                "temperature": 0.6,
                "max_tokens": 1024,
                "timeout": 60
            }
        }

        self._cache = LRUCache(max_size=1000)

    async def call_with_fallback(
        self,
        prompt: str,
        required_quality: float = 0.7,
        context: Dict[str, Any] = None
    ) -> LLMResponse:
        """
        带降级的LLM调用

        Args:
            prompt: 提示词
            required_quality: 最低质量要求
            context: 上下文（用于缓存键生成）

        Returns:
            LLMResponse: 包含结果和质量信息
        """

        # 1. 检查缓存
        cache_key = self._generate_cache_key(prompt, context)
        cached = self._cache.get(cache_key)
        if cached:
            cached.from_cache = True
            return cached

        # 2. 尝试主模型
        try:
            response = await self._call_model("primary", prompt)
            if response.quality >= required_quality:
                self._cache.set(cache_key, response)
                return response
        except Exception as e:
            logger.warning(f"Primary model failed: {e}")

        # 3. 尝试次级模型
        try:
            response = await self._call_model("secondary", prompt)
            if response.quality >= required_quality * 0.9:  # 略微降低要求
                self._cache.set(cache_key, response)
                return response
        except Exception as e:
            logger.warning(f"Secondary model failed: {e}")

        # 4. 尝试本地模型
        try:
            response = await self._call_model("local", prompt)
            if response.quality >= required_quality * 0.8:
                return response
        except Exception as e:
            logger.warning(f"Local model failed: {e}")

        # 5. 返回默认回复
        return LLMResponse(
            content=self._get_fallback_content(context),
            quality=0.3,
            model="none",
            from_cache=False,
            error="All models failed, using fallback"
        )

    async def _call_model(
        self,
        model_level: str,
        prompt: str
    ) -> LLMResponse:
        """调用指定层级的模型"""
        config = self._model_configs[model_level]

        start_time = time.time()

        try:
            response = await self.agent.llm.ainvoke(prompt)

            latency = time.time() - start_time

            return LLMResponse(
                content=response.content,
                quality=self._estimate_quality(response.content, prompt),
                model=config["model"],
                latency=latency,
                from_cache=False
            )

        except Exception as e:
            raise LLMCallError(f"{model_level} model failed: {e}")

    def _estimate_quality(
        self,
        content: str,
        prompt: str
    ) -> float:
        """估计内容质量"""
        # 基础检查
        if not content or len(content) < 10:
            return 0.0

        # 与prompt的相关性
        prompt_keywords = set(prompt.lower().split()[:20])
        content_keywords = set(content.lower().split()[:100])
        overlap = len(prompt_keywords & content_keywords) / len(prompt_keywords) if prompt_keywords else 0

        # 结构完整性
        has_structure = any(marker in content for marker in ["##", "###", "1.", "2.", "- "])

        # 格式正确性
        try:
            json.loads(content)
            is_json_valid = True
        except:
            is_json_valid = False

        return min(1.0, overlap * 0.4 + (0.3 if has_structure else 0) + (0.3 if is_json_valid else 0))
```

#### Task 23.3: 工具结果验证与后处理

```python
# src/agents_v2/tools/tool_spec.py 增强

class ToolResultValidator:
    """
    工具结果验证器

    对工具执行结果进行:
    1. 格式验证
    2. 语义验证
    3. 后处理
    """

    def __init__(self):
        self._validators: Dict[str, Callable] = {}

    def register_validator(
        self,
        tool_name: str,
        validator: Callable[[ToolResult], ValidationResult]
    ) -> None:
        """注册验证器"""
        self._validators[tool_name] = validator

    async def validate(
        self,
        tool_result: ToolResult,
        tool_spec: ToolSpec
    ) -> ValidatedResult:
        """
        验证工具结果

        1. 检查返回格式是否符合spec
        2. 检查值是否在有效范围内
        3. 必要时进行后处理（如截断、转换）
        """
        # 1. 格式验证
        if not tool_result.success:
            return ValidatedResult(
                is_valid=False,
                errors=["Tool execution failed"],
                warnings=[],
                processed_result=None
            )

        # 2. 获取验证器
        validator = self._validators.get(tool_spec.name)

        if validator:
            return await validator(tool_result)
        else:
            return self._default_validation(tool_result, tool_spec)

    async def _default_validation(
        self,
        tool_result: ToolResult,
        tool_spec: ToolSpec
    ) -> ValidatedResult:
        """默认验证逻辑"""
        errors = []
        warnings = []

        result = tool_result.result

        # 检查类型
        if not isinstance(result, dict):
            errors.append(f"Expected dict, got {type(result)}")
            return ValidatedResult(False, errors, warnings, None)

        # 检查必需字段
        for param in tool_spec.parameters:
            if param.required and param.name not in result:
                errors.append(f"Missing required field: {param.name}")

        # 检查字段类型
        for param in tool_spec.parameters:
            if param.name in result:
                value = result[param.name]
                expected_type = param.type.value if isinstance(param.type, ParameterType) else param.type

                if not self._check_type(value, expected_type):
                    errors.append(
                        f"Field {param.name}: expected {expected_type}, got {type(value).__name__}"
                    )

        # 后处理
        processed = self._post_process(result, tool_spec)

        return ValidatedResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            processed_result=processed if len(errors) == 0 else None
        )

    def _post_process(
        self,
        result: Dict[str, Any],
        tool_spec: ToolSpec
    ) -> Dict[str, Any]:
        """后处理结果"""
        processed = result.copy()

        for param in tool_spec.parameters:
            if param.name not in processed:
                continue

            value = processed[param.name]

            # 截断过长的字符串
            if isinstance(value, str) and param.max_value:
                if len(value) > param.max_value:
                    processed[param.name] = value[:param.max_value] + "..."

            # 类型转换
            if param.type == ParameterType.INTEGER:
                try:
                    processed[param.name] = int(value)
                except:
                    pass

        return processed


class ToolResultCache:
    """
    工具结果缓存

    基于输入参数缓存工具执行结果
    """

    def __init__(self, ttl_seconds: float = 3600):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._ttl = ttl_seconds

    def get_cache_key(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> str:
        """生成缓存键"""
        # 使用参数的有序表示
        param_str = json.dumps(parameters, sort_keys=True)
        return f"{tool_name}:{hashlib.md5(param_str.encode()).hexdigest()}"

    def get(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Optional[Any]:
        """获取缓存结果"""
        key = self.get_cache_key(tool_name, parameters)

        if key in self._cache:
            result, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return result
            else:
                del self._cache[key]

        return None

    def set(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Any
    ) -> None:
        """设置缓存"""
        key = self.get_cache_key(tool_name, parameters)
        self._cache[key] = (result, time.time())
```

#### Task 23.4: 智能上下文注入

```python
# src/agents_v2/base_agent.py 新增

class IntelligentContextInjector:
    """
    智能上下文注入器

    根据当前任务动态决定上下文中应包含什么
    """

    def __init__(self, max_context_tokens: int = 128000):
        self.max_context_tokens = max_context_tokens
        self._token_counter = TokenCounter()

    def build_context(
        self,
        task: str,
        agent_capabilities: AgentCapability,
        memory_state: MemoryState,
        session_history: List[Message],
        user_profile: UserProfile
    ) -> str:
        """
        构建智能上下文

        优先级:
        1. 系统指令 (必须保留)
        2. 用户输入 (必须保留)
        3. 相关记忆 (高优先级)
        4. 最近对话 (根据token限制)
        5. 用户偏好 (低优先级)
        """

        context_parts = []
        remaining_tokens = self.max_context_tokens - self._reserve_system_tokens()

        # 1. 用户输入（完整保留）
        context_parts.append(self._format_user_input(task))
        remaining_tokens -= self._token_counter.count(context_parts[-1])

        # 2. 相关记忆（智能检索）
        relevant_memories = self._retrieve_relevant_memories(task, memory_state, limit=5000)
        if relevant_memories:
            context_parts.append(f"## 相关记忆\n{relevant_memories}")
            remaining_tokens -= self._token_counter.count(relevant_memories)

        # 3. 会话历史（最近优先，智能截断）
        session_context = self._build_session_context(session_history, remaining_tokens)
        if session_context:
            context_parts.append(f"## 对话历史\n{session_context}")
            remaining_tokens -= self._token_counter.count(session_context)

        # 4. 用户偏好（简短总结）
        if remaining_tokens > 1000:
            preference_summary = self._summarize_preferences(user_profile)
            context_parts.append(f"## 用户偏好\n{preference_summary}")

        return "\n\n".join(context_parts)

    def _retrieve_relevant_memories(
        self,
        task: str,
        memory_state: MemoryState,
        limit: int
    ) -> str:
        """检索相关记忆"""
        # 1. 任务相关记忆
        task_memories = memory_state.search_by_task(task)

        # 2. 偏好相关记忆
        preference_memories = memory_state.search_by_preferences(task)

        # 3. 优先级排序
        combined = self._prioritize_memories(task_memories, preference_memories)

        # 4. 截断到限制
        result = self._truncate_to_limit(combined, limit)

        return result

    def _prioritize_memories(
        self,
        task_memories: List[Memory],
        preference_memories: List[Memory]
    ) -> List[Memory]:
        """优先级排序"""
        scored = []

        for mem in task_memories:
            score = mem.importance * 0.7 + mem.recency * 0.3
            scored.append((score, mem))

        for mem in preference_memories:
            if mem not in [m for _, m in scored]:
                score = mem.importance * 0.5 + mem.recency * 0.5
                scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored]

    def _truncate_to_limit(self, memories: List[Memory], limit: int) -> str:
        """截断到token限制"""
        result_parts = []
        current_tokens = 0

        for mem in memories:
            mem_text = f"- [{mem.type.value}] {mem.content}"
            mem_tokens = self._token_counter.count(mem_text)

            if current_tokens + mem_tokens > limit:
                break

            result_parts.append(mem_text)
            current_tokens += mem_tokens

        return "\n".join(result_parts)


class TokenCounter:
    """Token计数器（估算）"""

    def count(self, text: str) -> int:
        """估算token数量"""
        # 简单估算：中文2token/字，英文1.5token/词
        chinese_chars = len([c for c in text if '一' <= c <= '鿿'])
        english_words = len(text.split()) - chinese_chars

        return int(chinese_chars * 2 + english_words * 1.5)
```

### 4.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| ReAct执行 | 5轮内收敛>80% | 测试复杂任务执行 |
| 多层降级 | 4种模型正确切换 | 模拟模型失败场景 |
| 工具验证 | 6种错误类型检测 | 测试各种边界情况 |
| 上下文注入 | 128K token正确管理 | 测试长文本场景 |
| 结果缓存 | 命中率>30% | 统计重复调用 |

---

## 五、Iteration 24: 记忆系统细节打磨

### 5.1 当前实现问题

**文件**: `src/agents_v2/memory/unified.py`, `src/agents_v2/memory/short_term.py`

**当前问题**:
1. 记忆检索只是简单的相似度匹配，没有考虑时间衰减
2. 记忆重要性评估是静态的，没有根据使用情况动态调整
3. 情景记忆记录是简单的日志，没有结构化的执行追踪
4. 记忆之间没有建立关联图谱
5. 跨会话知识迁移没有系统化

### 5.2 详细改进任务

#### Task 24.1: 时间衰减记忆检索

```python
# src/agents_v2/memory/retrieval.py 增强

class TemporalAwareRetriever:
    """
    时间感知检索器

    记忆的 relevance = 基础相似度 × 时间衰减因子 × 使用频率因子
    """

    def __init__(self, base_retriever: EnhancedRetrievalEngine):
        self.base_retriever = base_retriever

        # 时间衰减参数
        self.decay_rate = 0.1  # 每天衰减10%
        self.half_life_days = 7  # 7天后重要性减半

        # 使用频率参数
        self.frequency_weight = 0.2  # 使用频率权重

    async def retrieve(
        self,
        query: str,
        memory_state: MemoryState,
        context: Dict[str, Any],
        limit: int = 10
    ) -> List[RetrievedMemory]:
        """
        时间感知检索

        考虑:
        1. 语义相似度（基础分数）
        2. 时间衰减（越老越不重要）
        3. 使用频率（常用记忆更易检索）
        4. 上下文相关性（当前任务相关）
        """

        # 1. 获取基础检索结果
        base_results = await self.base_retriever.retrieve(
            query=query,
            limit=limit * 2  # 多取一些，后面过滤
        )

        # 2. 计算综合分数
        scored_results = []
        for result in base_results:
            memory = result.entry

            # 时间衰减分数
            time_score = self._calculate_temporal_score(memory)

            # 使用频率分数
            frequency_score = self._calculate_frequency_score(memory)

            # 上下文相关分数
            context_score = self._calculate_context_score(memory, context)

            # 综合分数
            final_score = (
                result.score * 0.4 +           # 基础相似度权重
                time_score * 0.25 +            # 时间权重
                frequency_score * 0.15 +      # 频率权重
                context_score * 0.2            # 上下文权重
            )

            scored_results.append(RetrievedMemory(
                entry=memory,
                score=final_score,
                score_breakdown={
                    "semantic": result.score,
                    "temporal": time_score,
                    "frequency": frequency_score,
                    "context": context_score
                }
            ))

        # 3. 排序并返回
        scored_results.sort(key=lambda x: x.score, reverse=True)

        return scored_results[:limit]

    def _calculate_temporal_score(self, memory: MemoryEntry) -> float:
        """计算时间衰减分数"""
        if not memory.metadata or "last_accessed" not in memory.metadata:
            # 没有时间信息，使用created_at
            age_days = (time.time() - memory.created_at) / 86400
        else:
            last_accessed = memory.metadata["last_accessed"]
            age_days = (time.time() - last_accessed) / 86400

        # 指数衰减: score = e^(-t/half_life)
        return math.exp(-age_days / self.half_life_days)

    def _calculate_frequency_score(self, memory: MemoryEntry) -> float:
        """计算使用频率分数"""
        access_count = memory.metadata.get("access_count", 0)

        # 对数衰减：当访问次数超过10次后，增长变慢
        return min(1.0, math.log(1 + access_count) / math.log(11))

    def _calculate_context_score(
        self,
        memory: MemoryEntry,
        context: Dict[str, Any]
    ) -> float:
        """计算上下文相关分数"""
        current_task = context.get("task", "")
        current_topic = context.get("topic", "")

        if not current_task:
            return 0.5  # 无上下文时返回中性

        memory_tags = set(memory.metadata.get("tags", []))
        context_tags = set(context.get("tags", []))

        # 计算标签重叠
        if not memory_tags or not context_tags:
            return 0.5

        overlap = len(memory_tags & context_tags)
        union = len(memory_tags | context_tags)

        # Jaccard相似度
        return overlap / union if union > 0 else 0.5
```

#### Task 24.2: 动态重要性评估

```python
# src/agents_v2/memory/services.py 增强

class DynamicImportanceEvaluator:
    """
    动态重要性评估器

    根据记忆的使用情况动态调整重要性
    """

    def __init__(self):
        # 历史评估数据
        self._evaluation_history: Dict[str, List[ImportanceRecord]] = {}

        # 调整参数
        self.incremental_weight = 0.15    # 使用时增量
        self.decremental_weight = 0.05     # 未使用时减量
        self.max_importance = 1.0
        self.min_importance = 0.1

    def record_access(self, memory_id: str, context: Dict[str, Any]) -> float:
        """
        记录记忆访问

        返回更新后的重要性
        """
        if memory_id not in self._evaluation_history:
            self._evaluation_history[memory_id] = []

        record = ImportanceRecord(
            timestamp=time.time(),
            access_type="read",
            context=context,
            result_usefulness=self._estimate_usefulness(context)
        )

        self._evaluation_history[memory_id].append(record)

        # 计算新的重要性
        new_importance = self._calculate_importance(memory_id)

        return new_importance

    def record_result(
        self,
        memory_id: str,
        result_quality: float,
        context: Dict[str, Any]
    ) -> float:
        """
        记录记忆使用的效果

        用于反馈驱动的调整
        """
        if memory_id not in self._evaluation_history:
            self._evaluation_history[memory_id] = []

        record = ImportanceRecord(
            timestamp=time.time(),
            access_type="use",
            context=context,
            result_usefulness=result_quality
        )

        self._evaluation_history[memory_id].append(record)

        return self._calculate_importance(memory_id)

    def _calculate_importance(self, memory_id: str) -> float:
        """
        计算重要性

        公式: importance = base × (1 + increment)^pos × (1 - decrement)^neg
        """
        records = self._evaluation_history.get(memory_id, [])

        if not records:
            return 0.5  # 默认重要性

        # 计算正负信号
        positive_signals = sum(r.result_usefulness for r in records[-10:])
        negative_signals = len(records) - sum(1 for r in records[-10:] if r.result_usefulness > 0.5)

        # 指数移动平均
        base = 0.5
        adjustment = positive_signals * self.incremental_weight - negative_signals * self.decremental_weight

        importance = base + adjustment

        # 限制范围
        return max(self.min_importance, min(self.max_importance, importance))

    def suggest_importance(
        self,
        memory_type: MemoryType,
        content: str,
        context: Dict[str, Any]
    ) -> float:
        """
        预测新记忆的重要性

        基于记忆类型和内容特征
        """
        # 基础分数
        base_scores = {
            MemoryType.USER_PROFILE: 0.8,     # 用户画像重要
            MemoryType.LONG_TERM: 0.7,        # 长期记忆重要
            MemoryType.SESSION: 0.5,          # 会话记忆中等
            MemoryType.SHORT_TERM: 0.3,      # 短期记忆较低
            MemoryType.EPISODIC: 0.6         # 情景记忆中等
        }

        base = base_scores.get(memory_type, 0.5)

        # 内容特征调整
        content_length = len(content)
        if content_length > 500:
            base += 0.1  # 长内容可能更重要

        # 关键词调整
        important_keywords = ["关键", "重要", "核心", "主要"]
        if any(kw in content for kw in important_keywords):
            base += 0.15

        # 上下文匹配调整
        topic_keywords = context.get("topic_keywords", [])
        if any(kw in content for kw in topic_keywords):
            base += 0.1

        return max(self.min_importance, min(self.max_importance, base))
```

#### Task 24.3: 结构化情景记忆

```python
# src/agents_v2/memory/episodic.py 增强

@dataclass
class StructuredEpisode:
    """结构化情节"""
    episode_id: str
    task_id: str
    agent_id: str

    # 时间信息
    start_time: float
    end_time: Optional[float]
    duration_ms: float

    # 执行信息
    goal: str                           # 执行目标
    actions: List[EpisodeAction]         # 执行的动作序列
    decisions: List[EpisodeDecision]    # 关键决策点

    # 结果
    outcome: EpisodeOutcome             # 执行结果
    lessons_learned: List[str]         # 经验教训

    # 关联
    related_episodes: List[str]         # 关联的情节
    referenced_memories: List[str]     # 引用的记忆

    # 元数据
    success: bool
    quality_score: float
    efficiency_score: float             # 效率分数（实际/预期时间）


@dataclass
class EpisodeAction:
    """情节中的动作"""
    action_id: str
    timestamp: float
    action_type: ActionType              # thought/tool/llm/handoff

    # 动作详情
    description: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]

    # 性能
    duration_ms: float
    tokens_used: int

    # 质量
    confidence: float
    issues: List[str] = field(default_factory=list)


@dataclass
class EpisodeDecision:
    """关键决策点"""
    decision_id: str
    timestamp: float

    # 决策上下文
    context: str                          # 决策时的状态描述
    options_considered: List[str]        # 考虑的选项

    # 决策结果
    selected_option: str
    reasoning: str                       # 决策理由

    # 效果评估
    outcome_score: float                  # 这个决策的效果
    alternative_outcome: Optional[str]   # 如果选另一个会怎样


@dataclass
class EpisodeOutcome:
    """执行结果"""
    final_state: Dict[str, Any]           # 最终状态
    output: Any                           # 输出内容

    # 质量评估
    completeness: float                   # 完成度
    correctness: float                    # 正确性
    efficiency: float                     # 效率

    # 问题记录
    problems_encountered: List[str] = field(default_factory=list)
    recovery_actions: List[str] = field(default_factory=list)


class StructuredEpisodicRecorder:
    """
    结构化情景记忆记录器

    记录Agent执行过程中的详细信息
    """

    def __init__(self):
        self._active_episodes: Dict[str, StructuredEpisode] = {}
        self._completed_episodes: List[StructuredEpisode] = []

    def start_episode(
        self,
        task_id: str,
        agent_id: str,
        goal: str
    ) -> str:
        """开始记录新情节"""
        episode_id = f"episode_{task_id}_{agent_id}_{int(time.time()*1000)}"

        episode = StructuredEpisode(
            episode_id=episode_id,
            task_id=task_id,
            agent_id=agent_id,
            start_time=time.time(),
            goal=goal,
            actions=[],
            decisions=[],
            outcome=EpisodeOutcome(
                final_state={},
                output=None,
                completeness=0.0,
                correctness=0.0,
                efficiency=0.0
            ),
            lessons_learned=[],
            related_episodes=[],
            referenced_memories=[],
            success=False,
            quality_score=0.0,
            efficiency_score=0.0
        )

        self._active_episodes[episode_id] = episode
        return episode_id

    def record_action(
        self,
        episode_id: str,
        action: EpisodeAction
    ) -> None:
        """记录动作"""
        if episode_id in self._active_episodes:
            self._active_episodes[episode_id].actions.append(action)

    def record_decision(
        self,
        episode_id: str,
        decision: EpisodeDecision
    ) -> None:
        """记录决策"""
        if episode_id in self._active_episodes:
            self._active_episodes[episode_id].decisions.append(decision)

    def end_episode(
        self,
        episode_id: str,
        outcome: EpisodeOutcome
    ) -> StructuredEpisode:
        """结束情节记录"""
        if episode_id not in self._active_episodes:
            raise ValueError(f"Episode {episode_id} not found")

        episode = self._active_episodes[episode_id]
        episode.end_time = time.time()
        episode.duration_ms = (episode.end_time - episode.start_time) * 1000
        episode.outcome = outcome

        # 计算效率分数
        expected_duration = self._estimate_expected_duration(episode)
        episode.efficiency_score = expected_duration / episode.duration_ms if episode.duration_ms > 0 else 1.0

        # 判断成功
        episode.success = outcome.completeness >= 0.8 and outcome.correctness >= 0.7

        # 提取经验教训
        episode.lessons_learned = self._extract_lessons(episode)

        # 移动到已完成
        self._completed_episodes.append(episode)
        del self._active_episodes[episode_id]

        return episode

    def _extract_lessons(self, episode: StructuredEpisode) -> List[str]:
        """提取经验教训"""
        lessons = []

        # 从失败中学习
        if not episode.success:
            for action in episode.actions:
                if action.issues:
                    lessons.append(f"Issue to avoid: {action.description} - {', '.join(action.issues)}")

        # 从决策中学习
        for decision in episode.decisions:
            if decision.outcome_score < 0.5:
                lessons.append(f"Poor decision: {decision.selected_option} - {decision.reasoning}")

        # 从效率中学习
        if episode.efficiency_score < 0.5:
            lessons.append(f"Slow process: consider optimizing {episode.goal}")

        return lessons[:5]  # 最多5条

    def get_episode_by_task(self, task_id: str) -> List[StructuredEpisode]:
        """获取任务相关的所有情节"""
        return [
            ep for ep in self._completed_episodes
            if ep.task_id == task_id
        ]
```

### 5.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 时间衰减检索 | 7天记忆权重降50% | 测试时间衰减曲线 |
| 动态重要性 | 使用后重要性提升10% | 跟踪重要性变化 |
| 情景记忆结构 | 5+字段完整记录 | 验证episode数据结构 |
| 经验提取 | 每情节提取1+条 | 检查lessons_learned |
| 记忆关联 | 建立跨episode关联 | 测试related_episodes |

---

## 六、Iteration 25: 多Agent协作细节打磨

### 6.1 当前实现问题

**文件**: `src/agents_v2/multi_agent/debate.py`, `src/agents_v2/execution/skill_engine.py`

**当前问题**:
1. Agent间消息传递没有确认机制
2. 协作没有超时控制和部分结果返回
3. 技能匹配是简单的关键词匹配，没有语义理解
4. 辩论收敛条件过于简单
5. 没有Agent能力预热机制

### 6.2 详细改进任务

#### Task 25.1: 可靠的消息传递机制

```python
# src/agents_v2/multi_agent/communication.py 新增

@dataclass
class ReliableMessage:
    """可靠消息"""
    message_id: str
    sender: str
    receiver: str
    content: Any
    timestamp: float

    # 传输信息
    priority: MessagePriority = MessagePriority.NORMAL
    ttl_seconds: float = 300

    # 确认信息
    acks_received: Set[str] = field(default_factory=set)  # 已确认的接收者
    requires_ack: bool = True
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING

    # 重试信息
    retry_count: int = 0
    max_retries: int = 3


class ReliableMessageBus:
    """
    可靠消息总线

    特性:
    1. 消息持久化（即使重启也不丢失）
    2. 确认机制（知道对方是否收到）
    3. 重试机制（失败自动重试）
    4. 超时处理
    """

    def __init__(self, persistence_path: str = ".messages"):
        self._persistence_path = persistence_path
        self._pending_messages: Dict[str, ReliableMessage] = {}
        self._message_handlers: Dict[str, Callable] = {}
        self._acknowledgement_callbacks: Dict[str, Callable] = {}

    async def send(
        self,
        sender: str,
        receiver: str,
        content: Any,
        requires_ack: bool = True,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> str:
        """发送消息"""
        message_id = f"msg_{sender}_{int(time.time()*1000)}"

        message = ReliableMessage(
            message_id=message_id,
            sender=sender,
            receiver=receiver,
            content=content,
            timestamp=time.time(),
            priority=priority,
            requires_ack=requires_ack
        )

        # 持久化
        await self._persist_message(message)

        # 加入待确认队列
        if requires_ack:
            self._pending_messages[message_id] = message

        # 尝试传递
        success = await self._deliver_message(message)

        if not success and message.retry_count < message.max_retries:
            # 异步重试
            asyncio.create_task(self._retry_delivery(message_id))

        return message_id

    async def _deliver_message(self, message: ReliableMessage) -> bool:
        """传递消息"""
        try:
            handler = self._message_handlers.get(message.receiver)
            if handler:
                result = await handler(message)

                if result.success:
                    message.delivery_status = DeliveryStatus.DELIVERED
                    if message.requires_ack:
                        await self._send_ack(message)
                    return True

            message.delivery_status = DeliveryStatus.FAILED
            return False

        except Exception as e:
            logger.error(f"Message delivery failed: {e}")
            message.delivery_status = DeliveryStatus.FAILED
            return False

    async def _send_ack(self, original_message: ReliableMessage) -> None:
        """发送确认"""
        ack = ReliableMessage(
            message_id=f"ack_{original_message.message_id}",
            sender=original_message.receiver,
            receiver=original_message.sender,
            content={"original_id": original_message.message_id, "status": "delivered"},
            timestamp=time.time(),
            requires_ack=False
        )

        handler = self._message_handlers.get(original_message.sender)
        if handler:
            await handler(ack)

    async def wait_for_ack(
        self,
        message_id: str,
        timeout_seconds: float = 30
    ) -> bool:
        """等待确认"""
        start = time.time()

        while time.time() - start < timeout_seconds:
            if message_id not in self._pending_messages:
                return True  # 消息已被确认并移除

            await asyncio.sleep(0.1)

        return False  # 超时

    async def _retry_delivery(self, message_id: str) -> None:
        """重试传递"""
        if message_id not in self._pending_messages:
            return

        message = self._pending_messages[message_id]
        message.retry_count += 1

        # 指数退避
        await asyncio.sleep(2 ** message.retry_count)

        success = await self._deliver_message(message)

        if not success and message.retry_count < message.max_retries:
            asyncio.create_task(self._retry_delivery(message_id))
        elif message.retry_count >= message.max_retries:
            # 放弃，通知发送者
            await self._notify_delivery_failure(message)
            del self._pending_messages[message_id]
```

#### Task 25.2: 协作超时与部分结果

```python
# src/agents_v2/multi_agent/collaboration.py 新增

@dataclass
class CollaborationTask:
    """协作任务"""
    task_id: str
    task_type: str
    deadline: Optional[float]           # 截止时间
    timeout_seconds: float = 300         # 超时时间

    # 参与者
    participants: List[str]             # 参与的agent
    role_assignments: Dict[str, str]    # agent -> role

    # 进度追踪
    progress: float = 0.0               # 0-1
    partial_results: Dict[str, Any] = {}  # 部分结果
    completed_participants: Set[str] = set()

    # 结果
    final_result: Optional[Any] = None
    success: bool = False


class CollaborationTimeoutHandler:
    """
    协作超时处理器

    处理多Agent协作中的超时问题
    支持部分结果返回
    """

    def __init__(self):
        self._active_tasks: Dict[str, CollaborationTask] = {}
        self._timeout_callbacks: Dict[str, Callable] = {}

    async def create_task(
        self,
        task_id: str,
        participants: List[str],
        timeout_seconds: float = 300
    ) -> CollaborationTask:
        """创建协作任务"""
        task = CollaborationTask(
            task_id=task_id,
            task_type="collaboration",
            timeout_seconds=timeout_seconds,
            deadline=time.time() + timeout_seconds,
            participants=participants
        )

        self._active_tasks[task_id] = task

        # 设置超时回调
        asyncio.create_task(self._schedule_timeout(task_id, timeout_seconds))

        return task

    async def update_progress(
        self,
        task_id: str,
        participant_id: str,
        partial_result: Any,
        progress_delta: float
    ) -> None:
        """更新任务进度"""
        if task_id not in self._active_tasks:
            return

        task = self._active_tasks[task_id]
        task.partial_results[participant_id] = partial_result
        task.progress += progress_delta
        task.completed_participants.add(participant_id)

        # 检查是否达到完成条件
        if task.progress >= 1.0:
            await self._finalize_task(task_id)

    def get_partial_result(
        self,
        task_id: str,
        min_progress: float = 0.5
    ) -> Optional[Any]:
        """
        获取部分结果

        当任务超时但已有足够进展时，返回部分结果
        """
        if task_id not in self._active_tasks:
            return None

        task = self._active_tasks[task_id]

        if task.progress >= min_progress:
            return self._merge_partial_results(task)

        return None

    def _merge_partial_results(self, task: CollaborationTask) -> Any:
        """合并部分结果"""
        results = task.partial_results

        if not results:
            return None

        # 简单的合并策略：按贡献者比例混合
        # 实际实现应该更复杂，考虑结果类型和质量

        merged = {
            "partial": True,
            "progress": task.progress,
            "contributors": list(results.keys()),
            "data": results
        }

        return merged

    async def _schedule_timeout(
        self,
        task_id: str,
        timeout_seconds: float
    ) -> None:
        """调度超时处理"""
        await asyncio.sleep(timeout_seconds)

        if task_id not in self._active_tasks:
            return

        task = self._active_tasks[task_id]

        # 检查是否已完成
        if task.final_result:
            return

        # 超时，获取部分结果
        partial = self.get_partial_result(task_id, min_progress=0.3)

        if partial:
            callback = self._timeout_callbacks.get(task_id)
            if callback:
                await callback(task_id, partial, is_partial=True)

        # 清理
        del self._active_tasks[task_id]
```

#### Task 25.3: 语义技能匹配

```python
# src/agents_v2/execution/skill_engine.py 增强

class SemanticSkillMatcher:
    """
    语义技能匹配器

    基于语义理解而非关键词匹配技能
    """

    def __init__(self, embedding_model: Any = None):
        self.embedding_model = embedding_model
        self._skill_embeddings: Dict[str, List[float]] = {}

    async def register_skill(
        self,
        skill: Skill,
        description_embedding: List[float] = None
    ) -> None:
        """注册技能并计算嵌入"""
        if description_embedding:
            self._skill_embeddings[skill.id] = description_embedding
        else:
            # 使用LLM生成描述嵌入
            embedding = await self._generate_embedding(skill.description)
            self._skill_embeddings[skill.id] = embedding

    async def match_skills(
        self,
        task_description: str,
        top_k: int = 5,
        min_score: float = 0.5
    ) -> List[Tuple[Skill, float]]:
        """
        匹配技能

        1. 将任务描述转为嵌入
        2. 计算与各技能嵌入的相似度
        3. 结合技能质量分数
        """
        # 生成任务嵌入
        task_embedding = await self._generate_embedding(task_description)

        # 计算相似度
        scores = []
        for skill_id, skill_emb in self._skill_embeddings.items():
            similarity = self._cosine_similarity(task_embedding, skill_emb)

            # 结合技能质量（使用率、成功率）
            quality_factor = skill.success_rate * 0.3 + min(skill.usage_count / 100, 1.0) * 0.2

            # 综合分数
            final_score = similarity * 0.7 + quality_factor * 0.3

            if final_score >= min_score:
                scores.append((skill_id, final_score))

        # 排序返回
        scores.sort(key=lambda x: x[1], reverse=True)

        return [(self._skill_library[sid], score) for sid, score in scores[:top_k]]

    async def _generate_embedding(self, text: str) -> List[float]:
        """生成文本嵌入"""
        if self.embedding_model:
            return self.embedding_model.encode(text)
        else:
            # 回退：使用TF-IDF或简单词袋
            return self._simple_embedding(text)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        return dot / (norm1 * norm2) if norm1 and norm2 else 0.0

    def _simple_embedding(self, text: str) -> List[float]:
        """简单嵌入（词袋）"""
        words = text.lower().split()
        vec = [0.0] * 1000

        for i, word in enumerate(words[:100]):
            vec[hash(word) % 1000] += 1

        # 归一化
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec
```

#### Task 25.4: 辩论收敛条件增强

```python
# src/agents_v2/multi_agent/debate.py 增强

class EnhancedDebateConvergence:
    """
    增强的辩论收敛检测

    多种收敛条件:
    1. 立场一致收敛
    2. 论点重复检测
    3. 置信度稳定
    4. 时间限制
    """

    def __init__(self):
        self._position_history: Dict[str, List[str]] = {}
        self._argument_history: Dict[str, List[str]] = {}

    def check_convergence(
        self,
        debate: MultiAgentDebate,
        statements: List[DebateStatement],
        max_rounds: int
    ) -> ConvergenceResult:
        """
        检查辩论是否收敛

        Returns:
            ConvergenceResult: 包含是否收敛、收敛原因等信息
        """

        # 条件1: 立场一致
        position_converged = self._check_position_convergence(statements)

        # 条件2: 论点重复
        argument_stable = self._check_argument_stability(statements)

        # 条件3: 置信度稳定
        confidence_stable = self._check_confidence_stability(statements)

        # 条件4: 时间限制
        time_expired = len(statements) // len(debate._agents) >= max_rounds

        # 综合判断
        if position_converged and confidence_stable:
            return ConvergenceResult(
                converged=True,
                reason="Position and confidence converged",
                consensus_strength=self._calculate_consensus_strength(statements)
            )

        if argument_stable and len(statements) >= max_rounds * len(debate._agents):
            return ConvergenceResult(
                converged=True,
                reason="Arguments stabilized after max rounds",
                consensus_strength=self._calculate_consensus_strength(statements)
            )

        if time_expired:
            return ConvergenceResult(
                converged=True,
                reason="Maximum rounds reached",
                consensus_strength=self._calculate_consensus_strength(statements),
                is_partial=True
            )

        return ConvergenceResult(
            converged=False,
            reason="Debate still ongoing",
            consensus_strength=0.0
        )

    def _check_position_convergence(
        self,
        statements: List[DebateStatement]
    ) -> bool:
        """检查立场是否收敛"""
        if len(statements) < 3:
            return False

        # 取最近的声明
        recent = statements[-3:]

        # 提取关键词作为位置表示
        positions = [self._extract_key_position(s) for s in recent]

        # 检查是否所有立场都相似
        first_pos = positions[0]
        return all(self._positions_similar(first_pos, p) for p in positions[1:])

    def _check_argument_stability(
        self,
        statements: List[DebateStatement]
    ) -> bool:
        """检查论点是否稳定（开始重复）"""
        if len(statements) < 6:
            return False

        recent_arguments = [s.content for s in statements[-3:]]

        # 检查是否有重复
        for i in range(len(recent_arguments)):
            for j in range(i + 1, len(recent_arguments)):
                if self._content_similarity(recent_arguments[i], recent_arguments[j]) > 0.8:
                    return True

        return False

    def _check_confidence_stability(
        self,
        statements: List[DebateStatement]
    ) -> bool:
        """检查置信度是否稳定"""
        if len(statements) < 4:
            return False

        recent_confidences = [s.quality_score for s in statements[-4:]]

        # 检查方差是否小
        mean = sum(recent_confidences) / len(recent_confidences)
        variance = sum((c - mean) ** 2 for c in recent_confidences) / len(recent_confidences)

        return variance < 0.02  # 小方差表示稳定
```

#### Task 25.5: Agent能力预热

```python
# src/agents_v2/multi_agent/collaboration.py 新增

class AgentWarmupper:
    """
    Agent能力预热器

    在需要时提前激活相关Agent
    减少冷启动延迟
    """

    def __init__(self):
        self._warm_agents: Dict[str, AgentWarmthState] = {}
        self._warmup_policies: Dict[str, WarmupPolicy] = {}

    def register_policy(
        self,
        agent_id: str,
        policy: WarmupPolicy
    ) -> None:
        """注册预热策略"""
        self._warmup_policies[agent_id] = policy

    async def warm_up(
        self,
        agent_id: str,
        trigger_context: Dict[str, Any]
    ) -> None:
        """预热Agent"""
        policy = self._warmup_policies.get(agent_id)
        if not policy:
            return

        # 检查是否需要预热
        if not policy.should_warmup(trigger_context):
            return

        # 执行预热
        warm_state = self._warm_agents.get(agent_id, AgentWarmthState())
        warm_state.last_warmed = time.time()
        warm_state.warmth_level = 1.0

        # 预加载模型
        if policy.preload_model:
            await self._preload_model(agent_id)

        # 预加载记忆
        if policy.preload_memory:
            await self._preload_memory(agent_id, trigger_context)

        # 预热工具
        if policy.preload_tools:
            await self._preload_tools(agent_id, policy.tools_to_preload)

        self._warm_agents[agent_id] = warm_state

    def should_use_warm(
        self,
        agent_id: str,
        task_urgency: float
    ) -> bool:
        """
        判断是否应该使用已预热的Agent

        Args:
            agent_id: Agent ID
            task_urgency: 任务紧急程度 (0-1, 越高越紧急)

        Returns:
            是否使用预热的Agent
        """
        if agent_id not in self._warm_agents:
            return False

        warm_state = self._warm_agents[agent_id]
        age = time.time() - warm_state.last_warmed

        # 预热状态过期
        if age > warm_state.cooldown_seconds:
            return False

        # 高紧急任务优先使用已预热Agent
        if task_urgency > 0.7 and warm_state.warmth_level > 0.5:
            return True

        # 中等紧急任务使用状态良好的预热Agent
        if task_urgency > 0.4 and warm_state.warmth_level > 0.8:
            return True

        return False


@dataclass
class WarmupPolicy:
    """预热策略"""
    trigger_conditions: List[Callable]    # 触发条件列表
    preload_model: bool = True
    preload_memory: bool = True
    preload_tools: bool = True
    tools_to_preload: List[str] = field(default_factory=list)
    cooldown_seconds: float = 300        # 预热状态持续时间


@dataclass
class AgentWarmthState:
    """Agent预热状态"""
    last_warmed: float = 0
    warmth_level: float = 0.0            # 0-1
    cooldown_seconds: float = 300
    loaded_model: Optional[str] = None
    loaded_tools: List[str] = field(default_factory=list)
```

### 6.3 验收标准

| 验收项 | 标准 | 检查点 |
|--------|------|--------|
| 消息确认 | 确认率>99% | 测试消息丢失场景 |
| 超时处理 | 部分结果返回>80% | 模拟超时场景 |
| 语义匹配 | 匹配准确率>85% | 对比关键词匹配 |
| 辩论收敛 | 3轮内收敛>70% | 测试多种话题 |
| 预热效果 | 启动延迟降低50% | 测量冷/热启动时间 |

---

## 七、Iteration 26 (最终): 系统集成与质量验证

### 7.1 端到端流程验证

#### Task 26.1: 完整流程集成测试

```python
# tests/integration/test_full_pipeline.py 新增

class FullPipelineIntegrationTest:
    """
    完整流程集成测试

    测试从用户请求到最终输出的完整流程
    """

    async def test_topic_to_paper_flow(self):
        """选题到论文完整流程"""
        pass

    async def test_diagnostic_flow(self):
        """诊断流程"""
        pass

    async def test_revision_flow(self):
        """修订流程"""
        pass

    async def test_multi_agent_collaboration(self):
        """多Agent协作流程"""
        pass

    async def test_offline_mode_flow(self):
        """离线模式流程"""
        pass
```

#### Task 26.2: 性能基准测试

```python
# tests/benchmark/test_performance.py 新增

class PerformanceBenchmark:
    """性能基准测试"""

    # 延迟基准 (ms)
    LATENCY_BENCHMARKS = {
        "intent_routing": {"target": 50, "threshold": 100},
        "llm_call_simple": {"target": 500, "threshold": 1000},
        "llm_call_complex": {"target": 2000, "threshold": 5000},
        "memory_retrieval": {"target": 30, "threshold": 100},
        "tool_execution": {"target": 200, "threshold": 500},
    }

    # 吞吐量基准 (rps)
    THROUGHPUT_BENCHMARKS = {
        "concurrent_requests": {"target": 10, "threshold": 5},
        "batch_processing": {"target": 50, "threshold": 20},
    }
```

### 7.2 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| 端到端测试 | 覆盖率>90% | ⏳ |
| 性能基准 | 全部达标 | ⏳ |
| 错误率 | <0.1% | ⏳ |
| 内存使用 | <2GB | ⏳ |
| 最终评分 | 10.0/10.0 | ⏳ |

---

## 八、总结：26次迭代完整列表

| 迭代 | 主题 | 核心文件 | 关键任务数 |
|------|------|---------|-----------|
| 1 | Agent通信协议 | communication/ | 4 |
| 2 | 状态持久化 | checkpoint/ | 4 |
| 3 | Token追踪 | cost_tracking/ | 5 |
| 4 | 流式输出 | streaming/ | 5 |
| 5 | Agent角色系统 | roles/ | 5 |
| 6 | 执行监控 | monitoring/ | 5 |
| 7 | 工具版本管理 | tool_version/ | 5 |
| 8 | 错误恢复 | error_recovery/ | 5 |
| 9 | HIL人机交互 | hil/ | 5 |
| 10 | 上下文管理 | context/ | 5 |
| 11 | ACML协作语言 | acml/ | 5 |
| 12 | 依赖调度 | scheduler/ | 5 |
| 13 | 反馈信任 | trust/ | 5 |
| 14 | 技能演化 | evolution/ | 5 |
| 15 | 多模态增强 | multimodal/ | 5 |
| 16 | 性能优化 | performance/ | 5 |
| 17 | 安全强化 | security/ | 5 |
| 18 | E2E测试 | testing/ | 6 |
| 19 | 文档完善 | docs/ | 5 |
| 20 | 集成测试 | benchmarks/ | 6 |
| 21 | Intent Routing细节 | unified/ | 5 |
| 22 | MasterSupervisor细节 | unified/ | 4 |
| 23 | Agent执行细节 | base_agent.py | 4 |
| 24 | 记忆系统细节 | memory/ | 3 |
| 25 | 多Agent协作细节 | multi_agent/ | 5 |
| 26 | 系统集成验证 | tests/ | 2 |

**总计**: 26次迭代，150+关键任务，500+验收点

---

**文档状态**: 完成
**版本**: v0.3
**最后更新**: 2026-04-27