# Paper Agent 诊断模块开发计划

> 规划日期：2026-05-03
> 版本：v1.0
> 基于：学术论文诊断阶段调研报告 + 当前项目现状

---

## 一、背景与目标

### 1.1 调研结论

根据调研报告《学术论文诊断阶段调研报告》，学术论文诊断应包含以下**5大核心维度**：

| 诊断维度 | 权重 | 核心评估内容 |
|----------|------|-------------|
| **学术规范性** | 20% | 引用格式、术语使用、结构规范 |
| **研究质量** | 25% | 创新性、严谨性、贡献度 |
| **内容完整性** | 20% | 文献覆盖、论证完整、局限承认 |
| **表达质量** | 15% | 清晰度、连贯性、语法风格 |
| **逻辑严谨性** | 20% | 因果推理、论据质量、结论推导 |

### 1.2 当前项目现状

当前 `problem_oriented/` 模块已实现：
- `TopicRefinerAgent` — 选题精炼（部分覆盖选题维度）
- `LiteratureMapperAgent` — 文献映射（部分覆盖文献维度）
- `MethodologyAdvisorAgent` — 方法论指导（部分覆盖方法维度）
- `ArgumentBuilderAgent` — 论据构建（部分覆盖论证维度）
- `SectionDifferentiatorAgent` — 章节区分
- `DiscussionDeepenerAgent` — 讨论深化
- `ChartFormatterAgent` — 图表格式化
- `LanguagePolisherAgent` — 语言润色
- `PlagiarismCheckerAgent` — 查重检查

**问题**：
1. 缺乏统一的**诊断标准框架**
2. 各 Agent 诊断维度**不完整**，缺少系统性覆盖
3. **评分标准不统一**，没有按权重计算综合分
4. 缺少**学科差异化**诊断支持
5. 诊断结果与后续修复**衔接不紧密**

### 1.3 开发目标

1. 建立**标准化的5维诊断体系**
2. 实现**完整覆盖**的诊断 Agent 矩阵
3. 统一**评分标准**，输出可比较的综合评分
4. 支持**学科差异化**配置
5. 诊断结果自动匹配**修复策略**

---

## 二、标准化诊断框架设计

### 2.1 诊断维度完整矩阵

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Paper Agent 诊断体系 (5维 × 多级指标)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 维度1: 学术规范性 (权重: 20%)                                        │    │
│  │                                                                      │    │
│  │   ├─ 引用格式 (8%)     — APA/MLA/GB/T 格式正确性                     │    │
│  │   ├─ 术语使用 (6%)     — 专业术语准确性、一致性                      │    │
│  │   └─ 结构规范 (6%)     — IMRAD 结构完整性                            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 维度2: 研究质量 (权重: 25%)                                        │    │
│  │                                                                      │    │
│  │   ├─ 创新性 (10%)     — 理论突破/方法创新/应用创新                   │    │
│  │   ├─ 严谨性 (8%)      — 研究设计合理性、实验严谨性                   │    │
│  │   └─ 贡献度 (7%)      — 理论贡献、实践价值                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 维度3: 内容完整性 (权重: 20%)                                       │    │
│  │                                                                      │    │
│  │   ├─ 文献覆盖 (7%)     — 全面性、批判性分析                          │    │
│  │   ├─ 论证完整 (8%)     — 论点-论据-结论 链条完整性                   │    │
│  │   └─ 局限承认 (5%)     — 诚实讨论研究限制                            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 维度4: 表达质量 (权重: 15%)                                         │    │
│  │                                                                      │    │
│  │   ├─ 清晰度 (5%)      — 表达明确、无歧义                            │    │
│  │   ├─ 简洁性 (5%)      — 避免冗余、精炼表达                          │    │
│  │   └─ 语法正确 (5%)    — 时态、主谓一致、学术风格                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 维度5: 逻辑严谨性 (权重: 20%)                                       │    │
│  │                                                                      │    │
│  │   ├─ 因果推理 (7%)     — 因果关系成立、无混淆                       │    │
│  │   ├─ 论据质量 (7%)     — 证据支持论点程度                           │    │
│  │   └─ 结论推导 (6%)     — 结论由证据必然得出                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 评分等级标准

| 等级 | 分数范围 | 描述 | 特征 |
|------|----------|------|------|
| **优秀** | 9-10 | 达到顶级期刊发表标准 | 显著创新贡献、方法论严谨、论证无懈可击 |
| **良好** | 7-9 | 达到良好期刊发表标准 | 有一定创新性、方法设计合理、论证基本完整 |
| **合格** | 5-7 | 达到一般期刊发表标准 | 创新性有限、方法无明显缺陷、论证基本合理 |
| **不合格** | 0-5 | 未达到发表标准 | 缺乏创新性、方法存在明显问题、论证不完整 |

### 2.3 学科差异化配置

| 学科类型 | 侧重点 | 权重调整 |
|----------|--------|----------|
| **自然科学** | 实验设计、数据可靠性、可重复性 | 方法论权重 +5% |
| **社会科学** | 理论框架、论证逻辑、社会意义 | 逻辑严谨性权重 +5% |
| **医学** | 研究规范、伦理性、临床价值 | 严谨性权重 +5%，创新性权重 -5% |
| **工程** | 实用性、技术实现、性能评估 | 实用性权重 +5% |

---

## 三、诊断 Agent 矩阵设计

### 3.1 完整 Agent 矩阵

| Agent | 负责维度 | 评估指标 | 修复 Agent |
|-------|----------|----------|------------|
| `TopicDiagnostician` | 选题 | novelty, feasibility, value, specificity | TopicRefinerAgent |
| `LiteratureDiagnostician` | 文献综述 | coverage, balance, critical_analysis, gap_id | LiteratureMapperAgent |
| `MethodologyDiagnostician` | 方法论 | appropriateness, rigor, reproducibility, validity | MethodologyAdvisorAgent |
| `ArgumentDiagnostician` | 论证逻辑 | logic_coherence, evidence_quality, causal_reasoning | ArgumentBuilderAgent |
| `ExpressionDiagnostician` | 表达规范 | clarity, conciseness, grammar, terminology | LanguagePolisherAgent |
| `StructureDiagnostician` | 结构规范 | citation_format, section_coherence, format_compliance | CitationFormatterAgent |
| `DiscussionDiagnostician` | 讨论深度 | limitation_acknowledgment, significance, future_direction | DiscussionDeepenerAgent |

### 3.2 诊断输入/输出标准

```python
# 诊断输入
class DiagnosticInput(BaseModel):
    paper_content: str              # 论文全文或部分
    paper_metadata: Dict[str, Any]  # 元数据 (title, authors, abstract)
    user_level: str = "硕士"        # 研究者水平
    discipline: str = "通用"        # 学科领域
    diagnostic_scope: List[str]    # 诊断范围，如 ["topic", "literature", ...]

# 诊断输出
class DiagnosticOutput(BaseModel):
    agent_name: str
    dimension: str                  # 诊断维度
    overall_score: float           # 0-10 分
    grade: str                     # excellent/good/acceptable/poor
    sub_scores: Dict[str, float]    # 各子指标分数
    issues: List[Issue]            # 发现的问题
    severity: Dict[str, float]     # 问题严重程度 0-1
    recommendations: List[str]     # 修复建议
    grade_description: str         # 等级描述

# 问题描述
class Issue(BaseModel):
    type: str                      # 问题类型 (topic_vague, literature_insufficient, ...)
    description: str               # 问题描述
    location: str                  # 位置 (introduction/method/result/...)
    severity: float                # 0-1
    suggestion: str                # 修复建议
```

---

## 四、实施计划

### Phase 1: 诊断框架基础 (1周)

**目标**: 建立统一的诊断框架和接口

**任务清单**:

| 任务 | 说明 | 文件 |
|------|------|------|
| DiagnosticFramework 基类 | 统一诊断接口 | `src/agents_v2/problem_oriented/diagnostic_framework.py` |
| DiagnosticInput/Output 定义 | Pydantic 模型 | `src/agents_v2/problem_oriented/models.py` |
| 评分标准配置 | 5维度权重配置 | `src/agents_v2/problem_oriented/scoring_config.py` |
| 学科差异化配置 | 各学科权重调整 | `src/agents_v2/problem_oriented/discipline_config.py` |
| ProblemSupervisor 重构 | 集成新框架 | `src/agents_v2/problem_oriented/supervisor.py` |

### Phase 2: 诊断 Agent 开发 (2周)

**目标**: 实现 7 个诊断 Agent

**任务清单**:

| 任务 | 说明 | 文件 |
|------|------|------|
| TopicDiagnostician | 选题诊断 | `src/agents_v2/problem_oriented/topic_diagnostician.py` |
| LiteratureDiagnostician | 文献诊断 | `src/agents_v2/problem_oriented/literature_diagnostician.py` |
| MethodologyDiagnostician | 方法论诊断 | `src/agents_v2/problem_oriented/methodology_diagnostician.py` |
| ArgumentDiagnostician | 论证诊断 | `src/agents_v2/problem_oriented/argument_diagnostician.py` |
| ExpressionDiagnostician | 表达诊断 | `src/agents_v2/problem_oriented/expression_diagnostician.py` |
| StructureDiagnostician | 结构诊断 | `src/agents_v2/problem_oriented/structure_diagnostician.py` |
| DiscussionDiagnostician | 讨论诊断 | `src/agents_v2/problem_oriented/discussion_diagnostician.py` |

### Phase 3: 评分体系集成 (1周)

**目标**: 统一评分计算和结果输出

**任务清单**:

| 任务 | 说明 | 文件 |
|------|------|------|
| WeightedScoreCalculator | 加权评分计算 | `src/agents_v2/problem_oriented/score_calculator.py` |
| 综合报告生成器 | 输出统一报告 | `src/agents_v2/problem_oriented/report_generator.py` |
| 问题优先级排序 | severity 排序 | `src/agents_v2/problem_oriented/issue_sorter.py` |
| 诊断历史存储 | SQLite 存储 | `src/agents_v2/problem_oriented/diagnostic_history.py` |

### Phase 4: 诊断-修复衔接 (1周)

**目标**: 诊断结果自动匹配修复 Agent

**任务清单**:

| 任务 | 说明 | 文件 |
|------|------|------|
| IssueToAgentMapper | 问题→修复Agent映射 | `src/agents_v2/problem_oriented/issue_mapper.py` |
| 修复策略配置 | 问题类型→修复策略 | `src/agents_v2/problem_oriented/repair_strategies.py` |
| 自动修复调度 | 根据诊断结果调度 | `src/agents_v2/problem_oriented/repair_scheduler.py` |

---

## 五、核心代码设计

### 5.1 DiagnosticFramework 基类

```python
# src/agents_v2/problem_oriented/diagnostic_framework.py

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from .models import DiagnosticInput, DiagnosticOutput, Issue
from .scoring_config import SCORING_WEIGHTS

class DiagnosticFramework(ABC):
    """诊断框架基类"""

    # 诊断维度名称
    DIMENSION_NAME: str = ""
    # 维度权重
    DIMENSION_WEIGHT: float = 0.0
    # 子指标定义 (name, weight)
    SUB_DIMENSIONS: List[tuple] = []

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        self.llm_config = llm_config or LLMConfig()

    async def diagnose(self, input_data: DiagnosticInput) -> DiagnosticOutput:
        """执行诊断"""
        # 1. 收集各子指标评分
        sub_scores = await self._evaluate_sub_dimensions(input_data)

        # 2. 计算加权总分
        overall_score = self._calculate_weighted_score(sub_scores)

        # 3. 识别问题
        issues = await self._identify_issues(input_data, sub_scores)

        # 4. 生成建议
        recommendations = await self._generate_recommendations(
            issues, sub_scores
        )

        # 5. 确定等级
        grade = self._determine_grade(overall_score)

        return DiagnosticOutput(
            agent_name=self.__class__.__name__,
            dimension=self.DIMENSION_NAME,
            overall_score=overall_score,
            grade=grade,
            sub_scores=sub_scores,
            issues=issues,
            severity={issue.type: issue.severity for issue in issues},
            recommendations=recommendations,
            grade_description=self._get_grade_description(grade)
        )

    @abstractmethod
    async def _evaluate_sub_dimensions(
        self, input_data: DiagnosticInput
    ) -> Dict[str, float]:
        """评估各子维度 - 子类实现"""
        pass

    @abstractmethod
    async def _identify_issues(
        self, input_data: DiagnosticInput, sub_scores: Dict[str, float]
    ) -> List[Issue]:
        """识别问题 - 子类实现"""
        pass

    def _calculate_weighted_score(self, sub_scores: Dict[str, float]) -> float:
        """计算加权总分"""
        total_score = 0.0
        total_weight = 0.0

        for sub_name, weight in self.SUB_DIMENSIONS:
            if sub_name in sub_scores:
                total_score += sub_scores[sub_name] * weight
                total_weight += weight

        if total_weight == 0:
            return 5.0  # 默认分数

        return round(total_score / total_weight, 2)

    def _determine_grade(self, score: float) -> str:
        """确定等级"""
        if score >= 9.0:
            return "excellent"
        elif score >= 7.0:
            return "good"
        elif score >= 5.0:
            return "acceptable"
        else:
            return "poor"
```

### 5.2 TopicDiagnostician 实现

```python
# src/agents_v2/problem_oriented/topic_diagnostician.py

class TopicDiagnostician(DiagnosticFramework):
    """选题诊断 Agent"""

    DIMENSION_NAME = "topic"
    DIMENSION_WEIGHT = 0.25  # 研究质量维度的一部分
    SUB_DIMENSIONS = [
        ("novelty", 0.35),      # 创新性
        ("feasibility", 0.30),  # 可行性
        ("value", 0.20),        # 学术价值
        ("specificity", 0.15),  # 具体性
    ]

    async def _evaluate_sub_dimensions(
        self, input_data: DiagnosticInput
    ) -> Dict[str, float]:
        """评估选题各子维度"""
        topic = input_data.paper_metadata.get("topic", "")

        # 使用 LLM 评估
        prompt = f"""评估以下研究选题的各维度分数 (0-10):

        选题: {topic}

        评估以下维度并给出分数:
        1. 创新性: 是否具有独特的研究角度或突破性
        2. 可行性: 在给定条件下是否可完成
        3. 学术价值: 对学科发展的推动作用
        4. 具体性: 是否有明确的研究问题

        输出JSON格式:
        {{
            "novelty": 分数,
            "feasibility": 分数,
            "value": 分数,
            "specificity": 分数
        }}
        """

        response = await self._llm_call(prompt)
        return json.loads(response)

    async def _identify_issues(
        self, input_data: DiagnosticInput, sub_scores: Dict[str, float]
    ) -> List[Issue]:
        """识别选题问题"""
        issues = []

        if sub_scores.get("novelty", 10) < 6:
            issues.append(Issue(
                type="topic_lack_novelty",
                description="选题缺乏创新性",
                location="introduction",
                severity=0.8,
                suggestion="考虑引入新的研究视角或方法"
            ))

        if sub_scores.get("specificity", 10) < 6:
            issues.append(Issue(
                type="topic_vague",
                description="选题不够具体明确",
                location="introduction",
                severity=0.7,
                suggestion="聚焦于具体的研究问题"
            ))

        if sub_scores.get("feasibility", 10) < 5:
            issues.append(Issue(
                type="topic_infeasible",
                description="选题可行性存疑",
                location="methodology",
                severity=0.6,
                suggestion="评估是否具备完成研究所需的资源"
            ))

        return issues

    async def _generate_recommendations(
        self, issues: List[Issue], sub_scores: Dict[str, float]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        for issue in issues:
            if issue.type == "topic_lack_novelty":
                recommendations.append("寻找独特的研究视角或创新点")
            elif issue.type == "topic_vague":
                recommendations.append("将选题聚焦到具体的研究问题")
            elif issue.type == "topic_infeasible":
                recommendations.append("调整研究范围或补充研究条件")

        if not recommendations:
            recommendations.append("选题基本可行，可进入下一阶段")

        return recommendations[:5]
```

### 5.3 评分计算器

```python
# src/agents_v2/problem_oriented/score_calculator.py

class WeightedScoreCalculator:
    """加权评分计算器"""

    def __init__(self, discipline: str = "通用"):
        self.discipline = discipline
        self.weights = self._load_discipline_weights(discipline)

    def calculate_overall_score(
        self, diagnostic_results: Dict[str, DiagnosticOutput]
    ) -> float:
        """计算综合评分"""
        total_score = 0.0
        total_weight = 0.0

        for dimension, result in diagnostic_results.items():
            weight = self.weights.get(dimension, 0.2)
            total_score += result.overall_score * weight
            total_weight += weight

        if total_weight == 0:
            return 5.0

        return round(total_score / total_weight, 2)

    def _load_discipline_weights(self, discipline: str) -> Dict[str, float]:
        """加载学科差异化权重"""
        base_weights = {
            "学术规范性": 0.20,
            "研究质量": 0.25,
            "内容完整性": 0.20,
            "表达质量": 0.15,
            "逻辑严谨性": 0.20,
        }

        # 学科差异化调整
        if discipline == "自然科学":
            adjustments = {"研究质量": 0.05}
        elif discipline == "社会科学":
            adjustments = {"逻辑严谨性": 0.05}
        elif discipline == "医学":
            adjustments = {"研究质量": 0.05, "研究质量": -0.05}
        elif discipline == "工程":
            adjustments = {"内容完整性": 0.05}
        else:
            adjustments = {}

        # 应用调整
        for dim, adj in adjustments.items():
            base_weights[dim] = min(1.0, base_weights.get(dim, 0) + adj)

        return base_weights
```

---

## 六、验收标准

### 6.1 功能验收

| 任务 | 验收标准 |
|------|----------|
| 诊断框架基础 | DiagnosticFramework 基类可正常使用 |
| 7个诊断Agent | 每个 Agent 正确实现 diagnose() 方法 |
| 评分体系 | 加权评分计算正确，输出 0-10 分 |
| 学科差异化 | 不同学科权重配置生效 |
| 诊断-修复衔接 | 诊断结果自动匹配修复 Agent |

### 6.2 质量标准

| 标准 | 目标值 |
|------|--------|
| 诊断覆盖率 | 每个维度 ≥ 90% 覆盖 |
| 评分一致性 | 与专家评分偏差 ≤ 15% |
| 诊断延迟 | P95 < 2s/维度 |
| 问题识别召回率 | ≥ 80% |

---

## 七、依赖关系

```
Phase 1 (诊断框架基础)
      │
      ▼
Phase 2 (诊断Agent开发)
      │
      ▼
Phase 3 (评分体系集成)
      │
      ▼
Phase 4 (诊断-修复衔接)
```

---

## 八、相关文档

| 文档 | 说明 |
|------|------|
| [学术论文诊断阶段调研报告](../../research/学术论文诊断阶段调研报告.md) | 调研结论 |
| [各模块开发计划](../各模块开发计划.md) | 总体开发计划 |
| [problem_oriented 模块现状](../architecture/problem_oriented/) | 当前实现 |

---

**版本**：v1.0
**规划日期**：2026-05-03
**基于**：学术论文诊断阶段调研报告