# 改进建议：Reflexion 机制

**日期**：2026-04-30
**优先级**：高

---

## 1. 背景

当前 Agent 完成任务即终止，不评估输出质量。Reflexion 机制通过"生成→评估→反馈→优化"循环提升 Agent 能力。

---

## 2. Reflexion 架构

### 2.1 三组件模型

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│   Actor     │────▶│  Evaluator  │────▶│  Self-Reflection │
│  (生成器)    │     │  (评估器)    │     │    (反思器)      │
└─────────────┘     └─────────────┘     └──────────────────┘
       ↑                                    │
       └────────────────────────────────────┘
                     反馈循环
```

### 2.2 组件职责

| 组件 | 职责 | 输入 | 输出 |
|------|------|------|------|
| Actor | 生成响应 | 任务 + 反思反馈 | 初步结果 |
| Evaluator | 评估质量 | 结果 + 标准 | 质量分数 + 问题 |
| Self-Reflection | 生成反馈 | 问题列表 | 改进建议 |

---

## 3. 实现方案

### 3.1 核心类

```python
# agents_v2/reflexion_agent.py
from dataclasses import dataclass
from typing import Protocol, Optional, List
from enum import Enum

class QualityLevel(Enum):
    GOOD = "good"
    NEEDS_IMPROVEMENT = "needs_improvement"
    POOR = "poor"

@dataclass
class EvaluationResult:
    quality: float
    level: QualityLevel
    issues: List[str]
    suggestions: List[str]

@dataclass
class ReflectionFeedback:
    original_issues: List[str]
    improvement_hints: List[str]
    retry_context: dict

class Actor:
    """生成器"""
    async def generate(self, task: dict, context: dict) -> AgentOutput:
        raise NotImplementedError

class Evaluator:
    """评估器"""
    async def evaluate(self, output: AgentOutput, criteria: dict) -> EvaluationResult:
        raise NotImplementedError

    async def reflect(self, evaluation: EvaluationResult) -> ReflectionFeedback:
        """生成反思反馈"""
        raise NotImplementedError

class ReflexionAgent:
    """具备 Reflexion 机制的 Agent"""

    def __init__(
        self,
        generator: Actor,
        evaluator: Evaluator,
        max_iterations: int = 3,
        quality_threshold: float = 0.8
    ):
        self.generator = generator
        self.evaluator = evaluator
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold
        self.execution_history: List[dict] = []

    async def execute(self, task: dict, context: Optional[dict] = None) -> AgentOutput:
        context = context or {}
        current_task = task.copy()

        for iteration in range(self.max_iterations):
            # 1. Actor 生成
            result = await self.generator.generate(current_task, context)

            # 2. Evaluator 评估
            evaluation = await self.evaluator.evaluate(result, context)

            # 记录历史
            self.execution_history.append({
                "iteration": iteration,
                "result": result,
                "evaluation": evaluation
            })

            # 3. 质量检查
            if evaluation.level == QualityLevel.GOOD:
                result.metadata["iterations"] = iteration + 1
                result.metadata["history"] = self.execution_history
                return result

            # 4. Self-Reflection 生成反馈
            feedback = await self.evaluator.reflect(evaluation)

            # 5. 基于反馈调整输入
            current_task = self._apply_feedback(current_task, feedback)

        # 达到最大迭代次数
        result.metadata["iterations"] = self.max_iterations
        result.metadata["history"] = self.execution_history
        result.metadata["final_evaluation"] = evaluation
        return result

    def _apply_feedback(self, task: dict, feedback: ReflectionFeedback) -> dict:
        """应用反馈到任务"""
        task["_reflection_feedback"] = feedback.improvement_hints
        task["_retry_context"] = feedback.retry_context
        return task
```

### 3.2 LLM 评估器实现

```python
# agents_v2/evaluators/llm_evaluator.py
class LLMEvaluator:
    """基于 LLM 的评估器"""

    def __init__(self, llm_client, quality_threshold: float = 0.8):
        self.llm = llm_client
        self.quality_threshold = quality_threshold

    async def evaluate(self, output: AgentOutput, criteria: dict) -> EvaluationResult:
        prompt = f"""
        评估以下输出质量：

        输出：{output.data}
        标准：{criteria}

        返回 JSON：
        {{
            "quality": 0.0-1.0,
            "level": "good/needs_improvement/poor",
            "issues": ["问题1", "问题2"],
            "suggestions": ["建议1", "建议2"]
        }}
        """
        response = await self.llm.generate(prompt)
        return EvaluationResult(**json.loads(response))

    async def reflect(self, evaluation: EvaluationResult) -> ReflectionFeedback:
        prompt = f"""
        基于以下评估问题，生成改进建议：

        问题：{evaluation.issues}

        返回 JSON：
        {{
            "original_issues": [...],
            "improvement_hints": ["提示1", "提示2"],
            "retry_context": {{}}
        }}
        """
        response = await self.llm.generate(prompt)
        return ReflectionFeedback(**json.loads(response))
```

---

## 4. 集成方案

### 4.1 替换现有 Agent

```python
# 旧代码
agent = TopicAgent(config)

# 新代码
base_generator = TopicAgent(config)
evaluator = LLMEvaluator(llm_client, quality_threshold=0.8)
agent = ReflexionAgent(
    generator=base_generator,
    evaluator=evaluator,
    max_iterations=3
)
```

### 4.2 配置

```python
# reflexion 默认配置
REFLEXION_CONFIG = {
    "max_iterations": 3,
    "quality_threshold": 0.8,
    "enable_history": True
}
```

---

## 5. 效果评估

| 指标 | 无 Reflexion | 有 Reflexion |
|------|--------------|--------------|
| 输出质量 | 基准 | +15-20% |
| 幻觉率 | 基准 | -30% |
| 迭代次数 | 1 | 1-3 |
| Token 消耗 | 基准 | +20-40% |

---

## 6. 参考

- [Reflexion 论文 (arXiv:2303.11366)](https://arxiv.org/abs/2303.11366)
- [Self-Reflective Language Agents](https://arxiv.org/abs/2303.11366)
