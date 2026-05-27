"""
Agent评估运行器 v2.0

运行完整的Agent评估流程并生成报告
支持基准测试、同级对比、改进路线图
"""
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import os

from .agent_evaluator import AgentEvaluator, AgentEvaluationReport, EvaluationLevel, get_evaluator


@dataclass
class BenchmarkConfig:
    """基准测试配置"""
    name: str
    description: str
    test_cases: List[Dict[str, Any]]
    expected_min_score: float = 7.0
    level: EvaluationLevel = EvaluationLevel.BENCHMARK


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    benchmark_name: str
    passed: bool
    actual_score: float
    expected_score: float
    benchmark_score: float = 0.0
    vs_benchmark: float = 0.0
    rank: int = 0
    details: Dict[str, Any] = field(default_factory=dict)
    improvements: List[Dict[str, Any]] = field(default_factory=list)


class EvaluationRunner:
    """评估运行器 v2.0"""

    def __init__(self):
        self.evaluator = get_evaluator()
        self.benchmark_history: List[BenchmarkResult] = []

    async def run_topic_agent_benchmark(self) -> BenchmarkResult:
        """运行TopicAgent基准测试"""
        config = BenchmarkConfig(
            name="TopicAgent_Benchmark",
            description="TopicAgent核心功能基准测试",
            test_cases=[
                {"input": "深度学习在医学影像诊断中的应用"},
                {"input": "自然语言处理在客服系统中的应用"},
                {"input": "强化学习在游戏AI中的研究"},
                {"input": "计算机视觉在自动驾驶中的技术"},
                {"input": "图神经网络在推荐系统中的应用"}
            ],
            expected_min_score=8.0,
            level=EvaluationLevel.BENCHMARK
        )

        from .paper_agents import TopicAgent
        from .paper_agents.base_paper_agent import LLMConfig

        agent = TopicAgent(LLMConfig(provider="openai", model_name="gpt-4"))

        report = await self.evaluator.evaluate_topic_agent(agent, config.test_cases, config.level)

        result = BenchmarkResult(
            benchmark_name=config.name,
            passed=report.overall_score >= config.expected_min_score,
            actual_score=report.overall_score,
            expected_score=config.expected_min_score,
            benchmark_score=report.benchmark_score,
            vs_benchmark=report.overall_score - report.benchmark_score,
            rank=report.rank,
            details={
                "task_completion": report.task_completion,
                "quality": report.quality,
                "tool_usage": report.tool_usage,
                "planning": report.planning,
                "efficiency": report.efficiency,
                "collaboration": report.collaboration,
                "safety": report.safety,
                "self_correction": report.self_correction,
                "robustness": report.robustness,
                "consistency": report.consistency,
                "cost_efficiency": report.cost_efficiency,
                "multi_turn": report.multi_turn
            },
            improvements=[{
                "dimension": imp.dimension,
                "priority": imp.priority,
                "gap": imp.gap,
                "actions": imp.actions
            } for imp in report.improvements[:3]]
        )

        self.benchmark_history.append(result)
        return result

    async def run_literature_agent_benchmark(self) -> BenchmarkResult:
        """运行LiteratureAgent基准测试"""
        config = BenchmarkConfig(
            name="LiteratureAgent_Benchmark",
            description="LiteratureAgent文献搜索基准测试",
            test_cases=[
                {"topic": "深度学习医学影像诊断"},
                {"topic": "自然语言处理"},
                {"topic": "强化学习算法"}
            ],
            expected_min_score=7.5,
            level=EvaluationLevel.BENCHMARK
        )

        from .paper_agents import LiteratureAgent
        from .paper_agents.base_paper_agent import LLMConfig

        agent = LiteratureAgent(LLMConfig(provider="openai", model_name="gpt-4"))

        report = await self.evaluator.evaluate_literature_agent(agent, config.test_cases, config.level)

        result = BenchmarkResult(
            benchmark_name=config.name,
            passed=report.overall_score >= config.expected_min_score,
            actual_score=report.overall_score,
            expected_score=config.expected_min_score,
            benchmark_score=report.benchmark_score,
            vs_benchmark=report.overall_score - report.benchmark_score,
            rank=report.rank,
            details={
                "task_completion": report.task_completion,
                "tool_usage": report.tool_usage,
                "quality": report.quality,
                "planning": report.planning,
                "efficiency": report.efficiency
            },
            improvements=[{
                "dimension": imp.dimension,
                "priority": imp.priority,
                "gap": imp.gap,
                "actions": imp.actions
            } for imp in report.improvements[:3]]
        )

        self.benchmark_history.append(result)
        return result

    async def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """运行所有基准测试"""
        results = []

        print("Running TopicAgent Benchmark...")
        try:
            result = await self.run_topic_agent_benchmark()
            results.append(result)
            status = "PASSED" if result.passed else "FAILED"
            print(f"  Result: [{status}] {result.actual_score:.2f} (expected: {result.expected_score:.2f})")
            print(f"  vs Benchmark: {result.vs_benchmark:+.2f}, Rank: {result.rank}")
        except Exception as e:
            print(f"  Error: {e}")

        print("\nRunning LiteratureAgent Benchmark...")
        try:
            result = await self.run_literature_agent_benchmark()
            results.append(result)
            status = "PASSED" if result.passed else "FAILED"
            print(f"  Result: [{status}] {result.actual_score:.2f} (expected: {result.expected_score:.2f})")
            print(f"  vs Benchmark: {result.vs_benchmark:+.2f}, Rank: {result.rank}")
        except Exception as e:
            print(f"  Error: {e}")

        return results

    def generate_report(self) -> Dict[str, Any]:
        """生成评估报告"""
        summary = self.evaluator.get_evaluation_summary()

        total_benchmarks = len(self.benchmark_history)
        passed = sum(1 for r in self.benchmark_history if r.passed)
        failed = total_benchmarks - passed

        # 计算改进路线图
        roadmap = self.evaluator.compute_improvement_roadmap(target_score=9.5)

        report = {
            "evaluation_summary": summary,
            "benchmark_summary": {
                "total": total_benchmarks,
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{(passed/total_benchmarks*100):.1f}%" if total_benchmarks > 0 else "N/A"
            },
            "benchmarks": [
                {
                    "name": r.benchmark_name,
                    "passed": r.passed,
                    "actual_score": r.actual_score,
                    "expected_score": r.expected_score,
                    "benchmark_score": r.benchmark_score,
                    "vs_benchmark": r.vs_benchmark,
                    "rank": r.rank,
                    "details": r.details,
                    "improvements": r.improvements
                }
                for r in self.benchmark_history
            ],
            "improvement_roadmap": roadmap,
            "generated_at": datetime.now().isoformat()
        }

        return report

    def save_report(self, filepath: str) -> None:
        """保存评估报告到文件"""
        report = self.generate_report()
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    def print_report(self) -> None:
        """打印评估报告"""
        report = self.generate_report()

        print("\n" + "="*70)
        print("Agent Evaluation Report v2.0")
        print("="*70)

        print("\nEvaluation Summary:")
        summary = report["evaluation_summary"]
        if "message" in summary:
            print(f"  {summary['message']}")
        else:
            print(f"  Agent: {summary['agent']}")
            print(f"  Overall Score: {summary['overall_score']}")
            print(f"  Grade: {summary['grade']}")
            print(f"  Benchmark: {summary['benchmark']} (vs: {summary['vs_benchmark']})")
            print(f"  Rank: {summary['rank']}")

            print("\n  Top Strengths:")
            for s in summary.get("strengths", [])[:3]:
                print(f"    - {s}")

            print("\n  Areas for Improvement:")
            for imp in summary.get("improvements", [])[:3]:
                print(f"    - {imp['dimension']} (priority: {imp['priority']})")

        print("\nBenchmark Summary:")
        bm = report["benchmark_summary"]
        print(f"  Total: {bm['total']}")
        print(f"  Passed: {bm['passed']}")
        print(f"  Failed: {bm['failed']}")
        print(f"  Pass Rate: {bm['pass_rate']}")

        print("\nBenchmarks:")
        for bm in report["benchmarks"]:
            status = "PASSED" if bm["passed"] else "FAILED"
            print(f"  [{status}] {bm['name']}")
            print(f"        Score: {bm['actual_score']:.2f} (expected: {bm['expected_score']:.2f})")
            print(f"        vs Benchmark: {bm['vs_benchmark']:+.2f}, Rank: {bm['rank']}")

        print("\nImprovement Roadmap (target: 9.5):")
        for step in report.get("improvement_roadmap", [])[:5]:
            print(f"  Step {step['step']}: {step['dimension']}")
            print(f"        {step['from']} -> {step['to']} (gap: {step['gap']})")
            print(f"        Priority: {step['priority']}, Actions: {', '.join(step['actions'][:2])}")

        print("\n" + "="*70)
        print(f"Generated at: {report['generated_at']}")
        print("="*70)


async def run_full_evaluation():
    """运行完整评估流程"""
    runner = EvaluationRunner()

    print("Starting Full Agent Evaluation v2.0...")
    print("="*70)

    # 运行所有基准测试
    results = await runner.run_all_benchmarks()

    # 生成并打印报告
    runner.print_report()

    # 保存报告
    report_path = ".reports/evaluation_report.json"
    runner.save_report(report_path)
    print(f"\nReport saved to: {report_path}")

    return runner.benchmark_history


if __name__ == "__main__":
    asyncio.run(run_full_evaluation())
