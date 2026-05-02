# evaluation 模块开发计划

> 规划日期：2026-05-02
> 基于：`docs/implemented/architecture/evaluation/evaluation-system.md` + `docs/research/COMPLETE_AGENT_EVALUATION_GUIDE.md`
> 现状：QualityEvaluator 7维度/AgentEvaluator/Benchmark 已实现

---

## 一、模块概述

### 1.1 现有架构

```
evaluation/
├── agent_evaluator.py        # Agent级别评估器 ✅
├── module_evaluator.py       # 模块级别评估器 ✅
├── quality_evaluator.py      # 质量评估器 (7维度) ✅
├── rag_evaluator.py         # RAG检索评估器 ✅
├── evaluation_runner.py     # 评估运行器 ✅
├── benchmark.py             # 基准测试 ✅
├── feedback_collector.py    # 反馈收集 ✅
├── output_formatter.py      # 输出格式化 ✅
├── output_validator.py      # 输出验证 ✅
├── report_generator.py      # 报告生成 ✅
├── chain_integrator.py      # 链式集成 ✅
├── chaos_tester.py          # 混沌测试 ✅
├── e2e_test_suite.py       # 端到端测试 ✅
├── performance_benchmark.py # 性能基准 ✅
├── release_checker.py       # 发布检查 ✅
└── benchmarks/             # 基准测试套件
    ├── ab_testing.py        # A/B测试 ✅
    ├── agent_bench.py       # AgentBench ✅
    ├── gaia.py             # GAIA基准 ✅
    └── paper_writing.py    # 论文写作基准 ✅
```

### 1.2 提升目标

| 组件 | 当前 | 目标 |
|------|------|------|
| **QualityEvaluator** | 7维度 | 5维度（学术规范/研究质量/内容完整/表达质量/逻辑严谨） |
| **权重配置** | 无 | 20%/25%/20%/15%/20% |
| **LLM-as-Judge** | 基础 | Instructor结构化输出 |
| **评估基准** | 基础 | AgentBench/SWE-bench/PaperBench |
| **实时评估** | 批处理 | 流式评估 |

---

## 二、任务清单

### 2.1 QualityEvaluator 5维度重构（P0）

**目标**：按 COMPLETE_AGENT_EVALUATION_GUIDE.md 实现标准5维度

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 学术规范性评估 | P0 | 引用格式/术语使用/结构规范 | `src/agents_v2/evaluation/dimensions/academic_norm.py` |
| 研究质量评估 | P0 | 创新性/严谨性/贡献度 | `src/agents_v2/evaluation/dimensions/research_quality.py` |
| 内容完整性评估 | P0 | 文献覆盖/论证完整/局限承认 | `src/agents_v2/evaluation/dimensions/completeness.py` |
| 表达质量评估 | P1 | 清晰度/连贯性/语法风格 | `src/agents_v2/evaluation/dimensions/expression.py` |
| 逻辑严谨性评估 | P1 | 因果推理/论据质量/结论推导 | `src/agents_v2/evaluation/dimensions/logic.py` |

### 2.2 权重配置系统（P0）

**目标**：可配置的维度权重

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 权重配置定义 | P0 | 各维度权重定义 | `src/agents_v2/evaluation/weights.py` |
| 权重校准 | P1 | 基于反馈的权重调整 | `src/agents_v2/evaluation/weight_calibrator.py` |
| 综合评分计算 | P0 | 加权平均 | `src/agents_v2/evaluation/score_calculator.py` |

**权重配置**：

```python
# src/agents_v2/evaluation/weights.py
from dataclasses import dataclass

@dataclass
class EvaluationWeights:
    """评估维度权重配置"""

    # 五维度权重（总和100%）
    academic_norm: float = 0.20   # 学术规范性 20%
    research_quality: float = 0.25  # 研究质量 25%
    completeness: float = 0.20   # 内容完整性 20%
    expression: float = 0.15    # 表达质量 15%
    logic: float = 0.20          # 逻辑严谨性 20%

    @classmethod
    def default(cls) -> "EvaluationWeights":
        return cls()

    @classmethod
    def strict(cls) -> "EvaluationWeights":
        """严格模式"""
        return cls(
            academic_norm=0.25,
            research_quality=0.30,
            completeness=0.20,
            expression=0.10,
            logic=0.15
        )
```

### 2.3 LLM-as-Judge 增强（P1）

**目标**：Instructor 结构化输出评分

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| Instructor 集成 | P1 | 结构化输出 | `src/agents_v2/evaluation/instructor_judge.py` |
| Prompt 模板 | P1 | 标准化评估 Prompt | `src/agents_v2/evaluation/prompts.py` |
| 批量评估 | P2 | 并行评估 | `src/agents_v2/evaluation/batch_judge.py` |

### 2.4 评估基准集成（P1）

**目标**：集成标准评估基准

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| AgentBench 接口 | P1 | 8环境评估 | `src/agents_v2/evaluation/benchmarks/agent_bench.py` |
| PaperBench 接口 | P1 | 论文复现评估 | `src/agents_v2/evaluation/benchmarks/paper_bench.py` |
| SWE-bench 接口 | P2 | 代码评估 | `src/agents_v2/evaluation/benchmarks/swe_bench.py` |
| 基准报告生成 | P1 | JSON格式评估结果 | `src/agents_v2/evaluation/benchmark_reporter.py` |

### 2.5 规则引擎（P2）

**目标**：格式/引用规则校验

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 引用格式规则 | P2 | BibTeX/APA/GB/T 格式 | `src/agents_v2/evaluation/rules/citation_rules.py` |
| 结构规范规则 | P2 | IMRAD 结构检查 | `src/agents_v2/evaluation/rules/structure_rules.py` |
| 语言规范规则 | P2 | 术语/缩写检查 | `src/agents_v2/evaluation/rules/language_rules.py` |

---

## 三、5维度评估详解

### 3.1 评估维度定义

| 维度 | 权重 | 核心指标 | 评分范围 |
|------|------|---------|----------|
| **学术规范性** | 20% | 引用格式、术语使用、结构规范 | 0-10 |
| **研究质量** | 25% | 创新性、严谨性、贡献度 | 0-10 |
| **内容完整性** | 20% | 文献覆盖、论证完整、局限承认 | 0-10 |
| **表达质量** | 15% | 清晰度、连贯性、语法风格 | 0-10 |
| **逻辑严谨性** | 20% | 因果推理、论据质量、结论推导 | 0-10 |

### 3.2 评分计算

```python
class QualityScore:
    """综合质量评分"""

    def __init__(
        self,
        academic_norm: float,
        research_quality: float,
        completeness: float,
        expression: float,
        logic: float,
        weights: EvaluationWeights = None
    ):
        self.academic_norm = academic_norm
        self.research_quality = research_quality
        self.completeness = completeness
        self.expression = expression
        self.logic = logic
        self.weights = weights or EvaluationWeights()

    @property
    def overall(self) -> float:
        """加权综合评分"""
        return (
            self.academic_norm * self.weights.academic_norm +
            self.research_quality * self.weights.research_quality +
            self.completeness * self.weights.completeness +
            self.expression * self.weights.expression +
            self.logic * self.weights.logic
        )

    @property
    def passed(self) -> bool:
        """是否通过（≥7.0通过）"""
        return self.overall >= 7.0
```

---

## 四、实施计划

### Phase 1：5维度重构（1-2周）

```
Week 1:
  - 学术规范性评估实现
  - 研究质量评估实现
  - 权重配置系统

Week 2:
  - 内容完整性评估实现
  - 表达质量评估实现
  - 逻辑严谨性评估实现
```

### Phase 2：LLM-as-Judge + 基准（1-2周）

```
Week 3:
  - Instructor 集成
  - Prompt 模板标准化
  - 批量评估实现

Week 4:
  - AgentBench 接口
  - PaperBench 接口
  - 基准报告生成
```

### Phase 3：规则引擎（1周）

```
Week 5:
  - 引用格式规则
  - 结构规范规则
  - 语言规范规则
```

---

## 五、验收标准

- [ ] 5维度 QualityEvaluator 正常工作
- [ ] 权重可配置（default/strict 模式）
- [ ] Instructor 结构化输出评分正常
- [ ] AgentBench/PaperBench 接口可调用
- [ ] 综合评分 ≥ 7.0 通过

---

**版本**：v1.0
**规划日期**：2026-05-02
