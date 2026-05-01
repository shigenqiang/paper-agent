"""
ChartFormatterAgent - 图表规范化Agent

针对问题：图表制作粗糙

职责：
- 检查图表规范性
- 优化信息呈现
- 标准化格式
"""
from typing import Any, Dict, List, Optional
import json
import logging

from .base_problem_agent import ProblemAgentBase, AgentOutput, LLMConfig

logger = logging.getLogger(__name__)


class ChartFormatterAgent(ProblemAgentBase):
    """
    ChartFormatterAgent - 图表规范化

    针对问题：
    - 格式不规范
    - 信息呈现不清晰
    - 图表制作粗糙
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个学术图表制作专家。
你的职责是：
1. 检查图表规范性
2. 优化信息呈现
3. 提供标准化格式建议

请确保图表清晰、专业、符合学术规范。"""
        super().__init__(
            name="chart_formatter",
            target_problem="图表制作粗糙/格式不规范",
            llm_config=llm_config,
            description="图表规范化检查",
            system_prompt=system_prompt
        )

    async def diagnose(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        检查图表规范化

        输入：
        - charts: 图表列表，每个包含：
          {
            "type": "table/chart/graph",
            "title": "标题",
            "data": "数据描述",
            "description": "图表描述"
          }
        """
        charts = input_data.get("charts", [])

        if not charts:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["图表为空"],
                recommendations=["请提供需要检查的图表"],
                quality_score=0.0,
                error="Empty charts"
            )

        try:
            # 1. 逐个检查图表
            chart_checks = []
            for chart in charts:
                check = await self._check_single_chart(chart)
                chart_checks.append(check)

            # 2. 汇总问题
            all_issues = []
            for check in chart_checks:
                all_issues.extend(check.get("issues", []))

            # 3. 生成规范化建议
            recommendations = await self._generate_recommendations(chart_checks)

            # 4. 质量评分
            avg_score = sum(c.get("score", 5) for c in chart_checks) / len(chart_checks) / 10.0
            quality_score = round(avg_score, 2)

            return AgentOutput(
                success=True,
                result={
                    "chart_checks": chart_checks,
                    "total_charts": len(charts),
                    "issues_count": len(all_issues)
                },
                agent_name=self.name,
                diagnosed_issues=all_issues,
                recommendations=recommendations,
                quality_score=quality_score
            )

        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:109] Chart formatting check failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["图表检查失败"],
                recommendations=["请检查图表格式"],
                quality_score=0.0,
                error=str(e)
            )

    async def _check_single_chart(self, chart: Dict[str, Any]) -> Dict[str, Any]:
        """检查单个图表"""
        chart_type = chart.get("type", "unknown")
        title = chart.get("title", "")
        description = chart.get("description", "")

        prompt = f"""
检查以下学术图表的规范性：

图表类型：{chart_type}
标题：{title}
描述：{description}

请检查：
1. 标题是否清晰、准确？
2. 标注是否完整（坐标轴标签、图例、单位）？
3. 格式是否符合学术规范？
4. 信息呈现是否清晰？
5. 是否必要（是否有信息量）？

输出JSON格式：
{{
    "score": 7.5,
    "issues": ["问题1", "问题2"],
    "suggestions": ["改进建议1", "改进建议2"],
    "format_issues": ["格式问题1", "格式问题2"],
    "is_necessary": true/false
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"[ChartFormatterAgent:154] Single chart check failed: {e}")
            return {"score": 5.0, "issues": ["检查失败"], "suggestions": []}

    async def _generate_recommendations(self, chart_checks: List[Dict]) -> List[str]:
        """生成规范化建议"""
        recommendations = []

        # 汇总常见问题
        title_issues = sum(1 for c in chart_checks if any("title" in i.lower() for i in c.get("issues", [])))
        label_issues = sum(1 for c in chart_checks if any("label" in i.lower() or "axis" in i.lower() for i in c.get("issues", [])))
        format_issues = sum(1 for c in chart_checks if c.get("format_issues"))

        if title_issues > 0:
            recommendations.append(f"改进{title_issues}个图表的标题：使用描述性标题，明确图表主题")
        if label_issues > 0:
            recommendations.append(f"完善{label_issues}个图表的坐标轴标签和图例")
        if format_issues > 0:
            recommendations.append("统一图表格式：字体、字号、线条粗细保持一致")

        # 生成标准化模板
        recommendations.append("使用标准图表模板，确保学术期刊格式一致")

        return list(set(recommendations))[:5]
