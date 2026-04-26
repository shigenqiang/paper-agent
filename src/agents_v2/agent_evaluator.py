"""
Agent评估框架

基于业界标准的Agent评估方法论
评估维度：任务完成率、工具使用、规划能力、效率、质量、协作能力
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time


@dataclass
class EvaluationResult:
    """评估结果"""
    dimension: str
    score: float  # 0-10
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class AgentEvaluationReport:
    """Agent评估报告"""
    agent_name: str
    evaluation_time: datetime
    task_type: str
    task_description: str

    # 核心维度评分
    task_completion: float = 0.0  # 任务完成率
    tool_usage: float = 0.0       # 工具使用能力
    planning: float = 0.0         # 规划能力
    efficiency: float = 0.0      # 效率
    quality: float = 0.0          # 输出质量
    collaboration: float = 0.0    # 协作能力
    safety: float = 0.0          # 安全性
    self_correction: float = 0.0  # 自主纠错

    # 详细评估结果
    dimension_details: List[EvaluationResult] = field(default_factory=list)

    # 综合评分
    overall_score: float = 0.0

    @property
    def grade(self) -> str:
        """评分等级"""
        if self.overall_score >= 9.0:
            return "A (优秀)"
        elif self.overall_score >= 8.0:
            return "B (良好)"
        elif self.overall_score >= 7.0:
            return "C (合格)"
        elif self.overall_score >= 6.0:
            return "D (及格)"
        else:
            return "F (不及格)"

    def compute_overall(self):
        """计算综合评分"""
        weights = {
            'task_completion': 0.25,  # 任务完成率权重最高
            'quality': 0.20,
            'tool_usage': 0.15,
            'planning': 0.10,
            'efficiency': 0.10,
            'collaboration': 0.08,
            'safety': 0.07,
            'self_correction': 0.05
        }
        self.overall_score = (
            self.task_completion * weights['task_completion'] +
            self.quality * weights['quality'] +
            self.tool_usage * weights['tool_usage'] +
            self.planning * weights['planning'] +
            self.efficiency * weights['efficiency'] +
            self.collaboration * weights['collaboration'] +
            self.safety * weights['safety'] +
            self.self_correction * weights['self_correction']
        )


class AgentEvaluator:
    """Agent评估器"""

    def __init__(self):
        self.evaluation_history: List[AgentEvaluationReport] = []

    async def evaluate_topic_agent(self, agent, test_cases: List[Dict]) -> AgentEvaluationReport:
        """评估TopicAgent"""
        report = AgentEvaluationReport(
            agent_name="TopicAgent",
            evaluation_time=datetime.now(),
            task_type="topic_selection",
            task_description="选题：分析研究兴趣，生成具体研究主题"
        )

        total_scores = {k: 0.0 for k in [
            'task_completion', 'tool_usage', 'planning', 'efficiency',
            'quality', 'collaboration', 'safety', 'self_correction'
        ]}

        for case in test_cases:
            start_time = time.time()
            try:
                result = await agent.execute({"user_request": case["input"]})
                elapsed = time.time() - start_time

                # 任务完成率
                task_score = 8.0 if result.success else 5.0
                if result.result and "selected_topic" in result.result:
                    task_score = 9.0
                total_scores['task_completion'] += task_score

                # 质量评分
                quality_score = result.quality_score * 10 if result.quality_score else 6.0
                total_scores['quality'] += quality_score

                # 效率评分 (响应时间)
                if elapsed < 5:
                    total_scores['efficiency'] += 9.0
                elif elapsed < 10:
                    total_scores['efficiency'] += 7.0
                else:
                    total_scores['efficiency'] += 5.0

                # 规划能力（是否生成多个候选主题）
                if result.result and "alternative_topics" in result.result:
                    alt_count = len(result.result.get("alternative_topics", []))
                    total_scores['planning'] += min(9.0, 6.0 + alt_count)
                else:
                    total_scores['planning'] += 6.0

                # 工具使用（通常TopicAgent不依赖外部工具）
                total_scores['tool_usage'] += 7.0

                # 安全性（错误处理）
                if result.error:
                    total_scores['safety'] += 5.0
                else:
                    total_scores['safety'] += 8.0

                # 协作能力（与后续Agent的衔接）
                if result.result and "selected_topic" in result.result:
                    total_scores['collaboration'] += 8.0

                # 自主纠错
                if result.success:
                    total_scores['self_correction'] += 8.0
                else:
                    total_scores['self_correction'] += 5.0

            except Exception as e:
                total_scores['task_completion'] += 3.0
                total_scores['quality'] += 2.0
                total_scores['safety'] += 3.0
                total_scores['self_correction'] += 3.0

        n = len(test_cases) or 1
        report.task_completion = total_scores['task_completion'] / n
        report.quality = total_scores['quality'] / n
        report.efficiency = total_scores['efficiency'] / n
        report.planning = total_scores['planning'] / n
        report.tool_usage = total_scores['tool_usage'] / n
        report.safety = total_scores['safety'] / n
        report.collaboration = total_scores['collaboration'] / n
        report.self_correction = total_scores['self_correction'] / n

        report.compute_overall()
        self.evaluation_history.append(report)
        return report

    async def evaluate_literature_agent(self, agent, test_cases: List[Dict]) -> AgentEvaluationReport:
        """评估LiteratureAgent"""
        report = AgentEvaluationReport(
            agent_name="LiteratureAgent",
            evaluation_time=datetime.now(),
            task_type="literature_search",
            task_description="文献搜索：从arXiv/PubMed搜索相关论文"
        )

        total_scores = {k: 0.0 for k in [
            'task_completion', 'tool_usage', 'planning', 'efficiency',
            'quality', 'collaboration', 'safety', 'self_correction'
        ]}

        for case in test_cases:
            start_time = time.time()
            try:
                result = await agent.execute({"topic": case["topic"]})
                elapsed = time.time() - start_time

                # 任务完成率
                if result.success and result.result:
                    papers = result.result.get("papers", [])
                    total_scores['task_completion'] += 9.0 if len(papers) >= 5 else 7.0
                else:
                    total_scores['task_completion'] += 5.0

                # 工具使用（论文搜索能力）
                tool_score = 8.0
                if result.result:
                    source_count = len(set(p.get("source", "") for p in result.result.get("papers", [])))
                    tool_score = min(9.0, 6.0 + source_count)
                total_scores['tool_usage'] += tool_score

                # 质量评分
                quality_score = result.quality_score * 10 if result.quality_score else 6.0
                total_scores['quality'] += quality_score

                # 效率评分
                if elapsed < 10:
                    total_scores['efficiency'] += 9.0
                elif elapsed < 20:
                    total_scores['efficiency'] += 7.0
                else:
                    total_scores['efficiency'] += 5.0

                # 规划能力
                if result.result and "search_queries" in result.result:
                    total_scores['planning'] += 8.0
                else:
                    total_scores['planning'] += 6.0

                # 协作能力
                if result.result and "paper_analyses" in result.result:
                    total_scores['collaboration'] += 8.0

                # 安全性
                if result.error:
                    total_scores['safety'] += 5.0
                else:
                    total_scores['safety'] += 8.0

                # 自主纠错
                total_scores['self_correction'] += 8.0 if result.success else 5.0

            except Exception as e:
                total_scores['task_completion'] += 3.0
                total_scores['tool_usage'] += 3.0
                total_scores['safety'] += 3.0

        n = len(test_cases) or 1
        for k in total_scores:
            setattr(report, k, total_scores[k] / n)

        report.compute_overall()
        self.evaluation_history.append(report)
        return report

    async def evaluate_agent(self, agent, agent_name: str, test_cases: List[Dict]) -> AgentEvaluationReport:
        """通用Agent评估"""
        report = AgentEvaluationReport(
            agent_name=agent_name,
            evaluation_time=datetime.now(),
            task_type="general",
            task_description="通用评估"
        )

        total_scores = {k: 0.0 for k in [
            'task_completion', 'tool_usage', 'planning', 'efficiency',
            'quality', 'collaboration', 'safety', 'self_correction'
        ]}

        for case in test_cases:
            start_time = time.time()
            try:
                result = await agent.execute(case["input"])
                elapsed = time.time() - start_time

                total_scores['task_completion'] += 8.0 if result.success else 5.0
                total_scores['quality'] += (result.quality_score * 10) if result.quality_score else 6.0
                total_scores['efficiency'] += 9.0 if elapsed < 10 else (7.0 if elapsed < 20 else 5.0)
                total_scores['safety'] += 8.0 if not result.error else 5.0
                total_scores['self_correction'] += 8.0 if result.success else 5.0
                total_scores['tool_usage'] += 7.0
                total_scores['planning'] += 7.0
                total_scores['collaboration'] += 7.0

            except Exception:
                total_scores['task_completion'] += 3.0
                total_scores['quality'] += 3.0
                total_scores['safety'] += 3.0

        n = len(test_cases) or 1
        for k in total_scores:
            setattr(report, k, total_scores[k] / n)

        report.compute_overall()
        self.evaluation_history.append(report)
        return report

    def get_evaluation_summary(self) -> Dict[str, Any]:
        """获取评估总结"""
        if not self.evaluation_history:
            return {"message": "No evaluations yet"}

        latest = self.evaluation_history[-1]
        return {
            "agent": latest.agent_name,
            "overall_score": f"{latest.overall_score:.2f}/10",
            "grade": latest.grade,
            "dimensions": {
                "task_completion": f"{latest.task_completion:.2f}",
                "quality": f"{latest.quality:.2f}",
                "tool_usage": f"{latest.tool_usage:.2f}",
                "planning": f"{latest.planning:.2f}",
                "efficiency": f"{latest.efficiency:.2f}",
                "collaboration": f"{latest.collaboration:.2f}",
                "safety": f"{latest.safety:.2f}",
                "self_correction": f"{latest.self_correction:.2f}"
            },
            "total_evaluations": len(self.evaluation_history)
        }


# 全局评估器实例
_evaluator: Optional[AgentEvaluator] = None


def get_evaluator() -> AgentEvaluator:
    """获取全局评估器"""
    global _evaluator
    if _evaluator is None:
        _evaluator = AgentEvaluator()
    return _evaluator
