"""
AgentBench适配器 - 多领域Agent评估适配器

覆盖领域:
- knowledge_graph: 知识图谱查询 (Neo4j/Cypher)
- database: 数据库操作 (SQL)
- code: 代码生成与修复
- web: Web导航与交互
"""
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Domain(Enum):
    """评估领域枚举"""
    KNOWLEDGE_GRAPH = "knowledge_graph"
    DATABASE = "database"
    CODE = "code"
    WEB = "web"


@dataclass
class DomainTask:
    """领域任务定义"""
    task_id: str
    domain: Domain
    description: str
    expected_output: Any
    evaluation_fn: Optional[Callable] = None
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DomainResult:
    """领域评估结果"""
    domain: str
    accuracy: float
    total_tasks: int
    passed_tasks: int
    avg_latency: float
    results: List[Dict[str, Any]]


@dataclass
class BenchmarkReport:
    """完整Benchmark报告"""
    overall_score: float
    domain_scores: Dict[str, DomainResult]
    industry_standards: Dict[str, float]
    gap_analysis: Dict[str, float]
    recommendations: List[str]


class AgentBenchAdapter:
    """AgentBench适配器 - 适配Paper Agent场景"""

    # 行业标准分数（来自AgentBench论文）
    INDUSTRY_STANDARDS = {
        "knowledge_graph": 0.75,
        "database": 0.72,
        "code": 0.68,
        "web": 0.65
    }

    def __init__(self):
        self.tasks: Dict[Domain, List[DomainTask]] = {
            Domain.KNOWLEDGE_GRAPH: [],
            Domain.DATABASE: [],
            Domain.CODE: [],
            Domain.WEB: []
        }
        self._register_default_tasks()

    def _register_default_tasks(self):
        """注册默认任务"""
        # Knowledge Graph 任务
        self.tasks[Domain.KNOWLEDGE_GRAPH] = [
            DomainTask(
                task_id="kg_001",
                domain=Domain.KNOWLEDGE_GRAPH,
                description="查询论文'Attention is All You You Need'的作者",
                expected_output=["Ashish Vaswani", "Noam Shazeer"],
                evaluation_fn=self._eval_list_overlap
            ),
            DomainTask(
                task_id="kg_002",
                domain=Domain.KNOWLEDGE_GRAPH,
                description="查找所有引用了'BERT'的论文",
                expected_output=["RoBERTa", "ALBERT", "ELECTRA"],
                evaluation_fn=self._eval_list_overlap
            ),
            DomainTask(
                task_id="kg_003",
                domain=Domain.KNOWLEDGE_GRAPH,
                description="找出论文之间的引用关系路径",
                expected_output=["transformer -> BERT -> RoBERTa"],
                evaluation_fn=self._eval_path
            ),
        ]

        # Database 任务
        self.tasks[Domain.DATABASE] = [
            DomainTask(
                task_id="db_001",
                domain=Domain.DATABASE,
                description="查询过去一年被引用最多的10篇论文",
                expected_output=["paper_ids with high citations"],
                evaluation_fn=self._eval_result_exists
            ),
            DomainTask(
                task_id="db_002",
                domain=Domain.DATABASE,
                description="统计每个研究领域的论文数量",
                expected_output={"NLP": 100, "CV": 80, "RL": 50},
                evaluation_fn=self._eval_dict_similarity
            ),
        ]

        # Code 任务
        self.tasks[Domain.CODE] = [
            DomainTask(
                task_id="code_001",
                domain=Domain.CODE,
                description="生成一个Transformer模型的PyTorch实现",
                expected_output="class Transformer",
                evaluation_fn=self._eval_code_contains
            ),
            DomainTask(
                task_id="code_002",
                domain=Domain.CODE,
                description="编写一个论文数据抓取函数",
                expected_output="def scrape_paper",
                evaluation_fn=self._eval_code_contains
            ),
        ]

        # Web 任务 (模拟)
        self.tasks[Domain.WEB] = [
            DomainTask(
                task_id="web_001",
                domain=Domain.WEB,
                description="从arXiv获取最新论文列表",
                expected_output=["list of papers"],
                evaluation_fn=self._eval_result_exists
            ),
        ]

    def add_task(self, task: DomainTask):
        """添加任务"""
        if task.domain not in self.tasks:
            self.tasks[task.domain] = []
        self.tasks[task.domain].append(task)

    async def evaluate_domain(self, agent, domain: Domain) -> DomainResult:
        """评估指定领域

        Args:
            agent: 待评估的Agent
            domain: 要评估的领域

        Returns:
            DomainResult: 领域评估结果
        """
        tasks = self.tasks.get(domain, [])
        if not tasks:
            logger.warning(f"No tasks registered for domain {domain}")
            return DomainResult(
                domain=domain.value,
                accuracy=0.0,
                total_tasks=0,
                passed_tasks=0,
                avg_latency=0.0,
                results=[]
            )

        results = []
        passed = 0
        latencies = []

        logger.info(f"开始 {domain.value} 领域评估，共 {len(tasks)} 个任务")

        for task in tasks:
            start_time = time.time()
            try:
                # 执行任务
                response = await agent.run(task.description)

                # 评估结果
                if task.evaluation_fn:
                    success = task.evaluation_fn(response, task.expected_output)
                else:
                    success = self._default_eval(response, task.expected_output)

                result = {
                    "task_id": task.task_id,
                    "success": success,
                    "latency": time.time() - start_time,
                    "response": response
                }

                if success:
                    passed += 1
                    logger.info(f"  ✓ {task.task_id}: 通过")
                else:
                    logger.warning(f"  ✗ {task.task_id}: 失败")

            except Exception as e:
                result = {
                    "task_id": task.task_id,
                    "success": False,
                    "error": str(e),
                    "latency": time.time() - start_time
                }
                logger.error(f"  ✗ {task.task_id}: 错误 - {e}")

            results.append(result)
            latencies.append(result.get("latency", 0))

        accuracy = passed / len(tasks) if tasks else 0
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        return DomainResult(
            domain=domain.value,
            accuracy=accuracy,
            total_tasks=len(tasks),
            passed_tasks=passed,
            avg_latency=avg_latency,
            results=results
        )

    async def evaluate_all(self, agent) -> BenchmarkReport:
        """评估Agent在所有领域的表现

        Args:
            agent: 待评估的Agent

        Returns:
            BenchmarkReport: 完整评估报告
        """
        domain_scores = {}

        for domain in Domain:
            result = await self.evaluate_domain(agent, domain)
            domain_scores[domain.value] = result

        # 计算整体分数
        overall_score = sum(d.accuracy for d in domain_scores.values()) / len(domain_scores)

        # 分析差距
        gap_analysis = {}
        for domain_name, result in domain_scores.items():
            industry_std = self.INDUSTRY_STANDARDS.get(domain_name, 0.7)
            gap_analysis[domain_name] = result.accuracy - industry_std

        # 生成建议
        recommendations = self._generate_recommendations(domain_scores, gap_analysis)

        return BenchmarkReport(
            overall_score=overall_score,
            domain_scores=domain_scores,
            industry_standards=self.INDUSTRY_STANDARDS,
            gap_analysis=gap_analysis,
            recommendations=recommendations
        )

    def _generate_recommendations(self, domain_scores: Dict, gap_analysis: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []

        for domain_name, gap in gap_analysis.items():
            if gap < -0.1:
                recommendations.append(
                    f"{domain_name}: 需要重点改进，当前低于行业标准 {abs(gap):.1%}"
                )
            elif gap < 0:
                recommendations.append(
                    f"{domain_name}: 接近行业标准，还需小幅提升"
                )
            else:
                recommendations.append(
                    f"{domain_name}: 已超过行业标准 {gap:.1%}"
                )

        return recommendations

    # ========== 评估函数 ==========

    def _eval_list_overlap(self, response: Any, expected: List) -> bool:
        """评估列表重叠度"""
        if isinstance(response, list):
            response_set = set(str(item).lower() for item in response)
        else:
            response_set = set(str(response).lower().split())

        expected_set = set(str(item).lower() for item in expected)

        overlap = len(response_set & expected_set)
        return overlap >= len(expected_set) * 0.3

    def _eval_path(self, response: Any, expected: str) -> bool:
        """评估路径是否正确"""
        response_str = str(response).lower()
        expected_lower = expected.lower()

        # 检查路径中的关键节点
        expected_nodes = expected_lower.replace("->", ",").split(",")
        found_nodes = sum(1 for node in expected_nodes if node.strip() in response_str)

        return found_nodes >= len(expected_nodes) * 0.5

    def _eval_result_exists(self, response: Any, expected: Any) -> bool:
        """评估结果是否存在"""
        if response is None:
            return False
        if isinstance(response, (list, dict)) and len(response) == 0:
            return False
        return True

    def _eval_dict_similarity(self, response: Any, expected: Dict) -> bool:
        """评估字典相似度"""
        if not isinstance(response, dict):
            return False

        # 计算key重叠度
        response_keys = set(response.keys())
        expected_keys = set(expected.keys())

        if not expected_keys:
            return True

        overlap = len(response_keys & expected_keys) / len(expected_keys)
        return overlap >= 0.5

    def _eval_code_contains(self, response: Any, expected: str) -> bool:
        """评估代码是否包含关键片段"""
        response_str = str(response)
        expected_lower = expected.lower()

        return expected_lower in response_str.lower()

    def _default_eval(self, response: Any, expected: Any) -> bool:
        """默认评估函数"""
        if isinstance(expected, str):
            return expected in str(response)
        return response == expected

    def generate_report(self, report: BenchmarkReport) -> str:
        """生成评估报告

        Args:
            report: 评估报告

        Returns:
            str: 格式化报告
        """
        lines = [
            "=" * 60,
            "AgentBench 评估报告",
            "=" * 60,
            f"\n整体分数: {report.overall_score:.2%}",
            "\n各领域评分:",
        ]

        for domain_name, result in report.domain_scores.items():
            industry_std = report.industry_standards.get(domain_name, 0.7)
            gap = result.accuracy - industry_std

            status = "✓" if gap >= 0 else "✗"
            lines.append(
                f"  {status} {domain_name}: {result.accuracy:.2%} "
                f"(行业标准: {industry_std:.2%}, 差距: {gap:+.1%})"
            )

        lines.extend([
            "\n差距分析:",
        ])

        for domain_name, gap in report.gap_analysis.items():
            lines.append(f"  - {domain_name}: {gap:+.1%}")

        if report.recommendations:
            lines.append("\n改进建议:")
            for rec in report.recommendations:
                lines.append(f"  - {rec}")

        lines.append("=" * 60)

        return "\n".join(lines)


# 便捷函数
async def run_agent_bench_evaluation(agent) -> BenchmarkReport:
    """运行AgentBench评估的便捷函数

    Args:
        agent: 待评估的Agent

    Returns:
        BenchmarkReport: 评估报告
    """
    adapter = AgentBenchAdapter()
    report = await adapter.evaluate_all(agent)
    print(adapter.generate_report(report))
    return report
