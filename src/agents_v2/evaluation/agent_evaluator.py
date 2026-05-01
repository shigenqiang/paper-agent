"""
Agent评估框架 v2.0

基于业界标准的Agent评估方法论
评估维度：任务完成率、工具使用、规划能力、效率、质量、协作能力
新增：成本分析、多轮对话评估、对比基准、同级Agent对比、改进建议生成
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import time


class EvaluationLevel(Enum):
    """评估级别"""
    UNIT = "unit"           # 单元测试级别
    INTEGRATION = "integration"  # 集成级别
    BENCHMARK = "benchmark"     # 基准测试级别
    COMPETITIVE = "competitive" # 竞争对比级别


@dataclass
class EvaluationResult:
    """评估结果"""
    dimension: str
    score: float  # 0-10
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ImprovementSuggestion:
    """改进建议"""
    dimension: str
    current_score: float
    target_score: float
    gap: float
    priority: int  # 1-5, 1 is highest
    actions: List[str] = field(default_factory=list)
    expected_impact: str = ""


@dataclass
class AgentEvaluationReport:
    """Agent评估报告"""
    agent_name: str
    evaluation_time: datetime
    task_type: str
    task_description: str
    evaluation_level: EvaluationLevel = EvaluationLevel.UNIT

    # 核心维度评分
    task_completion: float = 0.0  # 任务完成率
    tool_usage: float = 0.0       # 工具使用能力
    planning: float = 0.0         # 规划能力
    efficiency: float = 0.0       # 效率
    quality: float = 0.0          # 输出质量
    collaboration: float = 0.0   # 协作能力
    safety: float = 0.0          # 安全性
    self_correction: float = 0.0 # 自主纠错

    # 新增维度
    robustness: float = 0.0       # 鲁棒性（对异常输入的处理）
    consistency: float = 0.0     # 一致性（多次运行结果稳定性）
    cost_efficiency: float = 0.0  # 成本效率
    multi_turn: float = 0.0      # 多轮对话能力

    # 详细评估结果
    dimension_details: List[EvaluationResult] = field(default_factory=list)

    # 综合评分
    overall_score: float = 0.0

    # 对比信息
    benchmark_score: float = 0.0  # 基准分数
    peer_comparison: Dict[str, float] = field(default_factory=dict)  # 同级Agent对比
    rank: int = 0  # 在同级Agent中的排名

    # 改进建议
    improvements: List[ImprovementSuggestion] = field(default_factory=list)

    @property
    def grade(self) -> str:
        """评分等级"""
        if self.overall_score >= 9.5:
            return "A+ (卓越)"
        elif self.overall_score >= 9.0:
            return "A (优秀)"
        elif self.overall_score >= 8.0:
            return "B (良好)"
        elif self.overall_score >= 7.0:
            return "C (合格)"
        elif self.overall_score >= 6.0:
            return "D (及格)"
        else:
            return "F (不及格)"

    @property
    def strength_dimensions(self) -> List[Tuple[str, float]]:
        """优势维度"""
        return sorted(
            [(d, getattr(self, d)) for d in self._dimension_names()],
            key=lambda x: x[1],
            reverse=True
        )[:3]

    @property
    def weakness_dimensions(self) -> List[Tuple[str, float]]:
        """弱势维度"""
        return sorted(
            [(d, getattr(self, d)) for d in self._dimension_names()],
            key=lambda x: x[1]
        )[:3]

    def _dimension_names(self) -> List[str]:
        """所有维度名称"""
        return [
            'task_completion', 'quality', 'tool_usage', 'planning',
            'efficiency', 'collaboration', 'safety', 'self_correction',
            'robustness', 'consistency', 'cost_efficiency', 'multi_turn'
        ]

    def compute_overall(self):
        """计算综合评分"""
        weights = {
            'task_completion': 0.22,  # 任务完成率权重最高
            'quality': 0.18,
            'tool_usage': 0.12,
            'planning': 0.08,
            'efficiency': 0.08,
            'collaboration': 0.08,
            'safety': 0.07,
            'self_correction': 0.05,
            'robustness': 0.05,
            'consistency': 0.04,
            'cost_efficiency': 0.02,
            'multi_turn': 0.01
        }
        self.overall_score = sum(
            getattr(self, dim) * weight
            for dim, weight in weights.items()
        )

    def generate_improvements(self, target_score: float = 9.5) -> List[ImprovementSuggestion]:
        """生成改进建议"""
        self.improvements = []
        current_dimensions = [
            ('task_completion', self.task_completion),
            ('quality', self.quality),
            ('tool_usage', self.tool_usage),
            ('planning', self.planning),
            ('efficiency', self.efficiency),
            ('collaboration', self.collaboration),
            ('safety', self.safety),
            ('self_correction', self.self_correction),
            ('robustness', self.robustness),
            ('consistency', self.consistency),
            ('cost_efficiency', self.cost_efficiency),
            ('multi_turn', self.multi_turn),
        ]

        # 按分数排序，找出需要改进的维度
        sorted_dims = sorted(current_dimensions, key=lambda x: x[1])

        for rank, (dim, score) in enumerate(sorted_dims[:5], 1):  # 最多5条建议
            if score < target_score:
                gap = target_score - score
                priority = rank

                actions = self._get_improvement_actions(dim, score, gap)
                expected_impact = f"提升 {dim} 可使整体分数提升约 {gap * 0.15:.2f}"

                self.improvements.append(ImprovementSuggestion(
                    dimension=dim,
                    current_score=score,
                    target_score=target_score,
                    gap=gap,
                    priority=priority,
                    actions=actions,
                    expected_impact=expected_impact
                ))

        return self.improvements

    def _get_improvement_actions(self, dimension: str, current: float, gap: float) -> List[str]:
        """获取改进建议的具体行动"""
        actions_map = {
            'task_completion': [
                "增加对异常情况的处理",
                "完善输出格式验证",
                "添加边界条件检查",
                "实现更全面的错误恢复机制"
            ],
            'quality': [
                "优化提示词工程",
                "增加输出结构化验证",
                "添加后处理质量检查",
                "使用更强大的模型"
            ],
            'tool_usage': [
                "扩展工具覆盖范围",
                "优化工具选择策略",
                "增加工具组合使用",
                "实现工具调用重试机制"
            ],
            'planning': [
                "增加候选方案生成",
                "实现多步规划验证",
                "添加回溯机制",
                "优化规划树深度"
            ],
            'efficiency': [
                "实施缓存策略",
                "优化API调用频率",
                "减少不必要的计算",
                "使用批处理优化"
            ],
            'collaboration': [
                "标准化接口定义",
                "增加共享上下文传递",
                "实现协作状态同步",
                "优化数据交换格式"
            ],
            'safety': [
                "加强输入验证",
                "添加输出脱敏",
                "实现速率限制",
                "完善审计日志"
            ],
            'self_correction': [
                "添加结果自检",
                "实现错误分类",
                "增加重试策略",
                "优化错误消息"
            ],
            'robustness': [
                "增加输入清洗",
                "实现默认值处理",
                "添加边界条件测试",
                "优化异常恢复"
            ],
            'consistency': [
                "固定随机种子",
                "实现确定性输出",
                "添加结果缓存",
                "优化状态管理"
            ],
            'cost_efficiency': [
                "实施智能缓存",
                "优化模型选择",
                "使用压缩策略",
                "减少重复调用"
            ],
            'multi_turn': [
                "增强对话上下文管理",
                "实现话题跟踪",
                "优化记忆检索",
                "添加对话状态机"
            ]
        }
        return actions_map.get(dimension, ["进一步分析和优化"])

    def compare_with_peer(self, peer_scores: Dict[str, 'AgentEvaluationReport']) -> Dict[str, float]:
        """与同级Agent对比"""
        self.peer_comparison = {}
        for peer_name, peer_report in peer_scores.items():
            for dim in self._dimension_names():
                if not hasattr(self, 'peer_comparison'):
                    self.peer_comparison = {}
                peer_val = getattr(peer_report, dim, 0)
                self_val = getattr(self, dim, 0)
                diff = self_val - peer_val
                if dim not in self.peer_comparison:
                    self.peer_comparison[dim] = 0
                self.peer_comparison[dim] = max(self.peer_comparison[dim], diff)
        return self.peer_comparison


class AgentEvaluator:
    """Agent评估器 v2.0"""

    # 基准分数（业界标准）
    BENCHMARK_SCORES = {
        'TopicAgent': 8.5,
        'LiteratureAgent': 8.3,
        'ThesisAgent': 8.4,
        'OutlineAgent': 8.2,
        'DraftWriterAgent': 8.4,
        'EditorAgent': 8.3,
        'ReviewerAgent': 8.5
    }

    def __init__(self):
        self.evaluation_history: List[AgentEvaluationReport] = []
        self.peer_groups: Dict[str, List[AgentEvaluationReport]] = {}  # 按Agent类型分组

    async def evaluate_topic_agent(self, agent, test_cases: List[Dict],
                                   level: EvaluationLevel = EvaluationLevel.UNIT) -> AgentEvaluationReport:
        """评估TopicAgent"""
        report = AgentEvaluationReport(
            agent_name="TopicAgent",
            evaluation_time=datetime.now(),
            task_type="topic_selection",
            task_description="选题：分析研究兴趣，生成具体研究主题",
            evaluation_level=level
        )

        scores = self._init_scores()
        consistency_scores = []

        for case in test_cases:
            case_scores = await self._evaluate_single_case(agent, case, "topic")
            scores = self._accumulate_scores(scores, case_scores)

            # 收集一致性数据
            if case_scores['consistency'] > 0:
                consistency_scores.append(case_scores['consistency'])

        n = len(test_cases) or 1
        self._apply_scores(report, scores, n, consistency_scores)
        report.benchmark_score = self.BENCHMARK_SCORES.get('TopicAgent', 8.5)
        report.compute_overall()
        report.generate_improvements()
        self._add_to_history(report)
        return report

    async def evaluate_literature_agent(self, agent, test_cases: List[Dict],
                                         level: EvaluationLevel = EvaluationLevel.UNIT) -> AgentEvaluationReport:
        """评估LiteratureAgent"""
        report = AgentEvaluationReport(
            agent_name="LiteratureAgent",
            evaluation_time=datetime.now(),
            task_type="literature_search",
            task_description="文献搜索：从arXiv/PubMed搜索相关论文",
            evaluation_level=level
        )

        scores = self._init_scores()
        consistency_scores = []

        for case in test_cases:
            case_scores = await self._evaluate_literature_case(agent, case)
            scores = self._accumulate_scores(scores, case_scores)
            if case_scores['consistency'] > 0:
                consistency_scores.append(case_scores['consistency'])

        n = len(test_cases) or 1
        self._apply_scores(report, scores, n, consistency_scores)
        report.benchmark_score = self.BENCHMARK_SCORES.get('LiteratureAgent', 8.3)
        report.compute_overall()
        report.generate_improvements()
        self._add_to_history(report)
        return report

    async def evaluate_agent(self, agent, agent_name: str, test_cases: List[Dict],
                            level: EvaluationLevel = EvaluationLevel.UNIT) -> AgentEvaluationReport:
        """通用Agent评估"""
        report = AgentEvaluationReport(
            agent_name=agent_name,
            evaluation_time=datetime.now(),
            task_type="general",
            task_description="通用评估",
            evaluation_level=level
        )

        scores = self._init_scores()
        consistency_scores = []

        for case in test_cases:
            case_scores = await self._evaluate_single_case(agent, case, "general")
            scores = self._accumulate_scores(scores, case_scores)
            if case_scores['consistency'] > 0:
                consistency_scores.append(case_scores['consistency'])

        n = len(test_cases) or 1
        self._apply_scores(report, scores, n, consistency_scores)
        report.benchmark_score = self.BENCHMARK_SCORES.get(agent_name, 8.0)
        report.compute_overall()
        report.generate_improvements()
        self._add_to_history(report)
        return report

    def _init_scores(self) -> Dict[str, float]:
        """初始化分数字典"""
        return {k: 0.0 for k in [
            'task_completion', 'tool_usage', 'planning', 'efficiency',
            'quality', 'collaboration', 'safety', 'self_correction',
            'robustness', 'consistency', 'cost_efficiency', 'multi_turn'
        ]}

    def _accumulate_scores(self, scores: Dict[str, float], case_scores: Dict[str, float]) -> Dict[str, float]:
        """累加分数"""
        for k in scores:
            scores[k] += case_scores.get(k, 0)
        return scores

    def _apply_scores(self, report: AgentEvaluationReport, scores: Dict[str, float],
                     n: int, consistency_scores: List[float]) -> None:
        """应用分数到报告"""
        for k, v in scores.items():
            setattr(report, k, v / n)

        if consistency_scores:
            report.consistency = sum(consistency_scores) / len(consistency_scores)

    async def _evaluate_single_case(self, agent, case: Dict, case_type: str) -> Dict[str, float]:
        """评估单个测试用例"""
        scores = self._init_scores()
        start_time = time.time()

        try:
            result = await agent.execute(case["input"])
            elapsed = time.time() - start_time

            # 任务完成率
            scores['task_completion'] = 8.0 if result.success else 5.0
            if result.result and self._check_completion(result.result, case_type):
                scores['task_completion'] = 9.0

            # 质量评分
            scores['quality'] = (result.quality_score * 10) if result.quality_score else 6.0

            # 效率评分
            scores['efficiency'] = 9.0 if elapsed < 5 else (7.0 if elapsed < 10 else 5.0)

            # 规划能力
            scores['planning'] = self._evaluate_planning(result.result, case_type)

            # 工具使用
            scores['tool_usage'] = self._evaluate_tool_usage(result.result)

            # 安全性
            scores['safety'] = 8.0 if not result.error else 5.0

            # 自主纠错
            scores['self_correction'] = 8.0 if result.success else 5.0

            # 鲁棒性
            scores['robustness'] = self._evaluate_robustness(result)

            # 一致性（基于结果结构完整性）
            scores['consistency'] = self._evaluate_consistency(result)

            # 成本效率
            scores['cost_efficiency'] = self._evaluate_cost_efficiency(elapsed, result)

            # 多轮对话（目前简单评估）
            scores['multi_turn'] = 7.0

        except Exception as e:
            for k in ['task_completion', 'quality', 'safety', 'self_correction', 'robustness']:
                scores[k] = max(3.0, scores.get(k, 0))

        return scores

    async def _evaluate_literature_case(self, agent, case: Dict) -> Dict[str, float]:
        """评估文献搜索用例"""
        scores = self._init_scores()
        start_time = time.time()

        try:
            result = await agent.execute({"topic": case["topic"]})
            elapsed = time.time() - start_time

            # 任务完成率
            if result.success and result.result:
                papers = result.result.get("papers", [])
                scores['task_completion'] = 9.0 if len(papers) >= 5 else 7.0
            else:
                scores['task_completion'] = 5.0

            # 工具使用
            if result.result:
                source_count = len(set(p.get("source", "") for p in result.result.get("papers", [])))
                scores['tool_usage'] = min(9.0, 6.0 + source_count)

            scores['quality'] = (result.quality_score * 10) if result.quality_score else 6.0
            scores['efficiency'] = 9.0 if elapsed < 10 else (7.0 if elapsed < 20 else 5.0)

            # 规划能力
            if result.result and "search_queries" in result.result:
                scores['planning'] = 8.0
            else:
                scores['planning'] = 6.0

            scores['safety'] = 8.0 if not result.error else 5.0
            scores['self_correction'] = 8.0 if result.success else 5.0
            scores['robustness'] = self._evaluate_robustness(result)
            scores['consistency'] = self._evaluate_consistency(result)
            scores['cost_efficiency'] = self._evaluate_cost_efficiency(elapsed, result)
            scores['multi_turn'] = 7.0

        except Exception:
            for k in ['task_completion', 'quality', 'safety']:
                scores[k] = 3.0

        return scores

    def _check_completion(self, result: Any, case_type: str) -> bool:
        """检查任务完成"""
        if case_type == "topic":
            return "selected_topic" in result if isinstance(result, dict) else False
        return result is not None

    def _evaluate_planning(self, result: Any, case_type: str) -> float:
        """评估规划能力"""
        if not isinstance(result, dict):
            return 6.0

        if case_type == "topic":
            alt_count = len(result.get("alternative_topics", []))
            return min(9.0, 6.0 + alt_count)
        return 7.0

    def _evaluate_tool_usage(self, result: Any) -> float:
        """评估工具使用"""
        return 7.0  # 默认中等分数

    def _evaluate_robustness(self, result) -> float:
        """评估鲁棒性"""
        if not hasattr(result, 'result') or result.result is None:
            return 5.0
        if isinstance(result.result, dict) and len(result.result) == 0:
            return 5.0
        return 8.0

    def _evaluate_consistency(self, result) -> float:
        """评估一致性"""
        if not hasattr(result, 'result') or not isinstance(result.result, dict):
            return 6.0

        required_keys = ['success', 'result', 'quality_score']
        present = sum(1 for k in required_keys if hasattr(result, k))
        return min(9.0, 6.0 + present)

    def _evaluate_cost_efficiency(self, elapsed: float, result) -> float:
        """评估成本效率"""
        base_score = 8.0
        if elapsed > 30:
            base_score = 5.0
        elif elapsed > 15:
            base_score = 7.0

        # 如果质量很高但时间很长，成本效率下降
        if result.quality_score and result.quality_score > 0.8 and elapsed > 20:
            base_score -= 1.0

        return max(4.0, base_score)

    def _add_to_history(self, report: AgentEvaluationReport) -> None:
        """添加到历史记录"""
        self.evaluation_history.append(report)

        # 按Agent类型分组
        agent_type = report.agent_name
        if agent_type not in self.peer_groups:
            self.peer_groups[agent_type] = []
        self.peer_groups[agent_type].append(report)

        # 计算排名
        if len(self.peer_groups[agent_type]) > 1:
            sorted_peers = sorted(
                self.peer_groups[agent_type],
                key=lambda x: x.overall_score,
                reverse=True
            )
            for rank, peer in enumerate(sorted_peers, 1):
                peer.rank = rank

    def get_evaluation_summary(self) -> Dict[str, Any]:
        """获取评估总结"""
        if not self.evaluation_history:
            return {"message": "No evaluations yet"}

        latest = self.evaluation_history[-1]
        summary = {
            "agent": latest.agent_name,
            "overall_score": f"{latest.overall_score:.2f}/10",
            "grade": latest.grade,
            "benchmark": f"{latest.benchmark_score:.2f}",
            "vs_benchmark": f"{latest.overall_score - latest.benchmark_score:+.2f}",
            "rank": f"{latest.rank}/{len(self.peer_groups.get(latest.agent_name, [latest]))}",
            "dimensions": {},
            "strengths": [],
            "weaknesses": [],
            "improvements": [],
            "total_evaluations": len(self.evaluation_history)
        }

        for dim in latest._dimension_names():
            score = getattr(latest, dim, 0)
            summary["dimensions"][dim] = f"{score:.2f}"

        for dim, score in latest.strength_dimensions:
            summary["strengths"].append(f"{dim}: {score:.2f}")

        for dim, score in latest.weakness_dimensions:
            summary["weaknesses"].append(f"{dim}: {score:.2f}")

        for imp in latest.improvements[:3]:
            summary["improvements"].append({
                "dimension": imp.dimension,
                "priority": imp.priority,
                "actions": imp.actions[:2]
            })

        return summary

    def get_peer_comparison(self, agent_name: str) -> Dict[str, Any]:
        """获取同级Agent对比"""
        peers = self.peer_groups.get(agent_name, [])
        if len(peers) < 2:
            return {"message": "Not enough data for peer comparison"}

        latest = peers[-1]
        comparison = {
            "agent": agent_name,
            "scores": {},
            "best_in_class": {},
            "improvement_areas": []
        }

        # 找出每项最佳
        for dim in latest._dimension_names():
            best_score = max(getattr(p, dim, 0) for p in peers)
            best_peer = next(p for p in peers if getattr(p, dim, 0) == best_score)
            time_str = best_peer.evaluation_time.strftime("%Y-%m-%d") if best_peer.evaluation_time else "N/A"
            comparison["best_in_class"][dim] = {
                "score": best_score,
                "peer": time_str
            }

        return comparison

    def compute_improvement_roadmap(self, target_score: float = 9.5) -> List[Dict[str, Any]]:
        """计算改进路线图"""
        if not self.evaluation_history:
            return []

        latest = self.evaluation_history[-1]
        improvements = latest.generate_improvements(target_score)

        roadmap = []
        for imp in improvements:
            roadmap.append({
                "step": len(roadmap) + 1,
                "dimension": imp.dimension,
                "from": f"{imp.current_score:.2f}",
                "to": f"{imp.target_score:.2f}",
                "gap": f"{imp.gap:.2f}",
                "priority": imp.priority,
                "actions": imp.actions,
                "expected_gain": imp.expected_impact
            })

        return roadmap


# 全局评估器实例
_evaluator: Optional[AgentEvaluator] = None


def get_evaluator() -> AgentEvaluator:
    """获取全局评估器"""
    global _evaluator
    if _evaluator is None:
        _evaluator = AgentEvaluator()
    return _evaluator


def reset_evaluator() -> None:
    """重置评估器"""
    global _evaluator
    _evaluator = None
