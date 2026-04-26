"""
自动化评估报告生成器

功能:
1. 从评估结果生成Markdown报告
2. 趋势分析
3. 对比分析
4. 导出功能
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import os


@dataclass
class EvaluationDimension:
    """评估维度"""
    name: str
    weight: float
    score: float
    description: str
    details: str = ""


class ReportGenerator:
    """
    评估报告生成器

    生成格式:
    - Markdown格式报告
    - JSON格式数据
    - HTML格式（可选）
    """

    def __init__(self, output_dir: str = "docs/evaluation"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_markdown_report(
        self,
        agent_name: str,
        dimensions: List[EvaluationDimension],
        overall_score: float,
        test_summary: Dict[str, Any],
        recommendations: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成Markdown格式评估报告

        Args:
            agent_name: Agent名称
            dimensions: 评估维度列表
            overall_score: 综合评分
            test_summary: 测试摘要
            recommendations: 改进建议
            metadata: 额外元数据

        Returns:
            Markdown格式报告内容
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""# Agent评估报告

## 基本信息

| 项目 | 内容 |
|------|------|
| Agent名称 | {agent_name} |
| 评估时间 | {timestamp} |
| 评估版本 | {metadata.get('version', 'N/A') if metadata else 'N/A'} |
| 测试用例数 | {test_summary.get('total_cases', 0)} |

## 综合评分

**Overall Score: {overall_score:.2f}/10** ({self._get_grade(overall_score)})

{dimensions_to_table(dimensions)}

## 测试摘要

| 指标 | 值 |
|------|-----|
| 通过用例 | {test_summary.get('passed', 0)} |
| 失败用例 | {test_summary.get('failed', 0)} |
| 通过率 | {test_summary.get('pass_rate', 0):.1%} |
| 平均执行时间 | {test_summary.get('avg_duration_ms', 0):.2f}ms |

## 维度分析

"""

        for dim in dimensions:
            report += f"""### {dim.name} (权重: {dim.weight:.0%})

**评分: {dim.score:.2f}/10**

{dim.description}

{dim.details}

"""

        report += """## 改进建议

"""

        for i, rec in enumerate(recommendations, 1):
            report += f"{i}. {rec}\n"

        if metadata:
            report += """

## 附加信息

"""
            for key, value in metadata.items():
                report += f"- **{key}**: {value}\n"

        report += f"""

---
*报告生成时间: {timestamp}*
"""

        return report

    def generate_trend_report(
        self,
        history: List[Dict[str, Any]],
        agent_name: str
    ) -> str:
        """
        生成趋势分析报告

        Args:
            history: 评估历史列表
            agent_name: Agent名称

        Returns:
            Markdown格式趋势报告
        """
        if not history:
            return f"# {agent_name} - 暂无趋势数据\n\n评估历史为空，请先运行评估。\n"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""# {agent_name} - 趋势分析报告

**生成时间**: {timestamp}
**数据点数**: {len(history)}

---

## 评分趋势

| 日期 | 综合评分 | 任务完成 | 质量 | 工具使用 | 规划 | 效率 | 协作 | 安全 | 纠错 |
|------|----------|----------|------|----------|------|------|------|------|------|
"""

        for entry in history:
            date = entry.get("evaluation_time", "N/A")
            if isinstance(date, datetime):
                date = date.strftime("%Y-%m-%d")
            report += f"| {date} | {entry.get('overall_score', 0):.2f} | "
            report += f"{entry.get('task_completion', 0):.2f} | "
            report += f"{entry.get('quality', 0):.2f} | "
            report += f"{entry.get('tool_usage', 0):.2f} | "
            report += f"{entry.get('planning', 0):.2f} | "
            report += f"{entry.get('efficiency', 0):.2f} | "
            report += f"{entry.get('collaboration', 0):.2f} | "
            report += f"{entry.get('safety', 0):.2f} | "
            report += f"{entry.get('self_correction', 0):.2f} |\n"

        # 计算趋势
        report += "\n## 趋势分析\n\n"

        if len(history) >= 2:
            latest = history[-1]
            previous = history[-2]

            score_diff = latest.get('overall_score', 0) - previous.get('overall_score', 0)
            trend = "↑ 上升" if score_diff > 0 else ("↓ 下降" if score_diff < 0 else "→ 持平")
            report += f"- **综合评分趋势**: {trend} ({score_diff:+.2f})\n"

            for dim in ['task_completion', 'quality', 'tool_usage', 'planning',
                       'efficiency', 'collaboration', 'safety', 'self_correction']:
                curr = latest.get(dim, 0)
                prev = previous.get(dim, 0)
                diff = curr - prev
                if abs(diff) > 0.1:
                    direction = "↑" if diff > 0 else "↓"
                    report += f"- **{dim}**: {direction} ({diff:+.2f})\n"

        # 计算平均值和峰值
        report += "\n## 统计摘要\n\n"

        avg_scores = {}
        for dim in ['overall_score', 'task_completion', 'quality', 'tool_usage',
                   'planning', 'efficiency', 'collaboration', 'safety', 'self_correction']:
            values = [h.get(dim, 0) for h in history if h.get(dim) is not None]
            if values:
                avg_scores[dim] = sum(values) / len(values)

        report += "| 维度 | 平均值 | 峰值 |\n|------|--------|------|\n"
        for dim, avg in avg_scores.items():
            peak = max(h.get(dim, 0) for h in history)
            report += f"| {dim} | {avg:.2f} | {peak:.2f} |\n"

        report += f"\n---\n*趋势报告生成时间: {timestamp}*\n"

        return report

    def generate_comparison_report(
        self,
        evaluations: Dict[str, Dict[str, Any]],
        metrics: List[str]
    ) -> str:
        """
        生成对比分析报告

        Args:
            evaluations: Agent名称 -> 评估数据
            metrics: 要对比的指标列表

        Returns:
            Markdown格式对比报告
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""# Agent对比分析报告

**生成时间**: {timestamp}
**对比Agent数**: {len(evaluations)}

---

## 评分对比

| Agent | 综合评分 | """ + " | ".join(m.title() for m in metrics) + """ |
|-------|----------|""" + "------|" * (len(metrics) + 1) + "\n"

        for agent_name, data in evaluations.items():
            report += f"| {agent_name} | {data.get('overall_score', 0):.2f} | "
            report += " | ".join(f"{data.get(m, 0):.2f}" for m in metrics) + " |\n"

        # 找出最佳
        report += "\n## 最佳表现\n\n"

        for metric in ['overall_score'] + metrics:
            best_agent = max(evaluations.items(), key=lambda x: x[1].get(metric, 0))
            best_score = best_agent[1].get(metric, 0)
            report += f"- **{metric}**: {best_agent[0]} ({best_score:.2f})\n"

        # 优劣势分析
        report += "\n## 优劣势分析\n\n"

        for agent_name, data in evaluations.items():
            report += f"### {agent_name}\n\n"

            sorted_dims = sorted(data.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0)
            strengths = [(k, v) for k, v in sorted_dims[-3:] if isinstance(v, (int, float))]
            weaknesses = [(k, v) for k, v in sorted_dims[:3] if isinstance(v, (int, float))]

            report += "**优势**: " + ", ".join(f"{k}({v:.2f})" for k, v in strengths) + "\n\n"
            report += "**劣势**: " + ", ".join(f"{k}({v:.2f})" for k, v in weaknesses) + "\\n\n"

        report += f"\n---\n*对比报告生成时间: {timestamp}*\n"

        return report

    def save_report(
        self,
        content: str,
        filename: str,
        format_type: str = "md"
    ) -> str:
        """
        保存报告到文件

        Args:
            content: 报告内容
            filename: 文件名（不含扩展名）
            format_type: 格式类型 (md/json)

        Returns:
            保存的文件路径
        """
        if format_type == "json":
            filepath = os.path.join(self.output_dir, f"{filename}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2, default=str)
        else:
            filepath = os.path.join(self.output_dir, f"{filename}.md")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

        return filepath

    def _get_grade(self, score: float) -> str:
        """获取评分等级"""
        if score >= 9.0:
            return "A (优秀)"
        elif score >= 8.0:
            return "B (良好)"
        elif score >= 7.0:
            return "C (合格)"
        elif score >= 6.0:
            return "D (及格)"
        else:
            return "F (不及格)"


def dimensions_to_table(dimensions: List[EvaluationDimension]) -> str:
    """将维度列表转换为Markdown表格"""
    table = "| 维度 | 权重 | 评分 | 说明 |\n|------|------|------|------|\n"
    for dim in dimensions:
        table += f"| {dim.name} | {dim.weight:.0%} | {dim.score:.2f}/10 | {dim.description[:50]}... |\n"
    return table


# 全局报告生成器
_report_generator: Optional[ReportGenerator] = None


def get_report_generator(output_dir: str = "docs/evaluation") -> ReportGenerator:
    """获取报告生成器单例"""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator(output_dir=output_dir)
    return _report_generator
