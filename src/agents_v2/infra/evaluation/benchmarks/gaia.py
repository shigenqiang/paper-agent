"""
GAIA基准评估器 - General AI Assistants Benchmark

GAIA基准包含3个难度等级:
- Level 1: 简单问题，单一工具
- Level 2: 多步骤推理，需要信息整合
- Level 3: 复杂任务，需要规划与工具组合
"""
from src.agents_v2.logging_config import get_logging_logger

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json

logger = get_logging_logger(__name__)


@dataclass
class GAIATask:
    """GAIA任务定义"""
    task_id: str
    question: str
    expected_answer: str
    level: int  # 1, 2, or 3
    tools_allowed: List[str] = field(default_factory=list)
    requires_web: bool = False
    requires_calculation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GAIAResult:
    """GAIA评估结果"""
    level: int
    accuracy: float
    avg_latency: float
    total_tasks: int
    passed_tasks: int
    failed_tasks: int
    results: List[Dict[str, Any]]
    score_breakdown: Dict[str, float]


class GAIABenchmark:
    """GAIA (General AI Assistants) 基准评估器"""

    # GAIA预定义任务（示例，实际使用时从数据文件加载）
    TASKS = {
        1: [
            GAIATask(
                task_id="gaia_1_001",
                question="什么是机器学习？",
                expected_answer="机器学习是...",
                level=1,
                tools_allowed=["search"]
            ),
            GAIATask(
                task_id="gaia_1_002",
                question="请查找2024年关于Transformer的论文",
                expected_answer="Attention is All You Need",
                level=1,
                tools_allowed=["search_arxiv"],
                requires_web=True
            ),
        ],
        2: [
            GAIATask(
                task_id="gaia_2_001",
                question="对比BERT和GPT的技术架构差异，并总结各自优势",
                expected_answer="架构对比总结",
                level=2,
                tools_allowed=["search_arxiv", "analyze"],
                requires_web=True
            ),
            GAIATask(
                task_id="gaia_2_002",
                question="从arXiv获取最新10篇强化学习论文，分析研究趋势",
                expected_answer="趋势分析报告",
                level=2,
                tools_allowed=["search_arxiv", "analyze"],
                requires_web=True
            ),
        ],
        3: [
            GAIATask(
                task_id="gaia_3_001",
                question="为一个关于'大模型在医学诊断中的应用'的研究课题设计完整研究方案，包括文献综述、方法论和预期成果",
                expected_answer="完整研究方案",
                level=3,
                tools_allowed=["search_arxiv", "search_pubmed", "analyze", "write"],
                requires_web=True
            ),
        ]
    }

    def __init__(self, level: int = 1):
        """初始化GAIA评估器

        Args:
            level: 评估难度等级 (1, 2, 或 3)
        """
        if level not in [1, 2, 3]:
            raise ValueError(f"Invalid level {level}. Must be 1, 2, or 3")
        self.level = level
        self.tasks = self._load_tasks(level)

    def _load_tasks(self, level: int) -> List[GAIATask]:
        """加载指定等级的任务"""
        return self.TASKS.get(level, [])

    def load_tasks_from_file(self, file_path: str) -> None:
        """从JSON文件加载任务

        Args:
            file_path: 任务文件路径
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.tasks = [GAIATask(**task) for task in data]

    async def evaluate(self, agent) -> GAIAResult:
        """评估Agent在GAIA基准上的表现

        Args:
            agent: 待评估的Agent实例，需要实现run(question)方法

        Returns:
            GAIAResult: 评估结果
        """
        results = []
        passed = 0
        latencies = []

        logger.info(f"开始GAIA Level {self.level} 评估，共 {len(self.tasks)} 个任务")

        for task in self.tasks:
            start_time = time.time()
            try:
                # 执行任务
                response = await agent.run(task.question)

                # 检查答案正确性
                success = self._check_answer(response, task.expected_answer)

                result = {
                    "task_id": task.task_id,
                    "success": success,
                    "latency": time.time() - start_time,
                    "question": task.question,
                    "response": response if isinstance(response, str) else str(response)
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

        # 计算统计
        accuracy = passed / len(self.tasks) if self.tasks else 0
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        # 分项评分
        breakdown = self._calculate_breakdown(results)

        return GAIAResult(
            level=self.level,
            accuracy=accuracy,
            avg_latency=avg_latency,
            total_tasks=len(self.tasks),
            passed_tasks=passed,
            failed_tasks=len(self.tasks) - passed,
            results=results,
            score_breakdown=breakdown
        )

    def _check_answer(self, response: Any, expected: str) -> bool:
        """检查答案是否正确

        Args:
            response: Agent响应
            expected: 期望答案

        Returns:
            bool: 是否正确
        """
        if isinstance(response, dict):
            response_text = response.get("answer", str(response))
        else:
            response_text = str(response)

        # 简化的匹配逻辑（实际使用需要更复杂的评估）
        response_lower = response_text.lower()
        expected_lower = expected.lower()

        # 检查关键词重叠
        expected_keywords = set(expected_lower.split())
        response_keywords = set(response_lower.split())

        overlap = len(expected_keywords & response_keywords)
        if overlap >= len(expected_keywords) * 0.5:
            return True

        # 检查是否包含关键答案片段
        if expected_lower[:20] in response_lower:
            return True

        return False

    def _calculate_breakdown(self, results: List[Dict]) -> Dict[str, float]:
        """计算分项评分

        Args:
            results: 所有任务结果

        Returns:
            Dict: 分项评分
        """
        total = len(results)
        if total == 0:
            return {"overall": 0.0}

        passed = sum(1 for r in results if r.get("success", False))

        return {
            "overall": passed / total,
            "pass_rate": passed / total,
            "avg_latency": sum(r.get("latency", 0) for r in results) / total
        }

    def generate_report(self, result: GAIAResult) -> str:
        """生成评估报告

        Args:
            result: 评估结果

        Returns:
            str: 格式化报告
        """
        report = f"""
{'='*60}
GAIA Benchmark 评估报告
{'='*60}

难度等级: Level {result.level}
总任务数: {result.total_tasks}
通过任务: {result.passed_tasks}
失败任务: {result.failed_tasks}
正确率:   {result.accuracy:.2%}
平均延迟: {result.avg_latency:.2f}s

分项评分:
"""
        for key, value in result.score_breakdown.items():
            report += f"  - {key}: {value:.2f}\n"

        report += f"""
{'='*60}
"""
        return report


# 便捷函数
async def run_gaia_evaluation(agent, level: int = 1) -> GAIAResult:
    """运行GAIA评估的便捷函数

    Args:
        agent: 待评估的Agent
        level: 难度等级

    Returns:
        GAIAResult: 评估结果
    """
    benchmark = GAIABenchmark(level=level)
    result = await benchmark.evaluate(agent)
    print(benchmark.generate_report(result))
    return result
