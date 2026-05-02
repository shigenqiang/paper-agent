"""
DiscussionDeepenerAgent - 讨论深化Agent

针对问题：讨论部分薄弱、缺乏深度

职责：
- 指导深入讨论
- 帮助对比已有研究
- 识别局限性
- 提出未来方向
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

import json

from .base_problem_agent import ProblemAgentBase, AgentOutput, LLMConfig

logger = get_logging_logger(__name__)


class DiscussionDeepenerAgent(ProblemAgentBase):
    """
    DiscussionDeepenerAgent - 讨论深化

    针对问题：
    - 讨论空洞
    - 缺乏深度分析
    - 不能与已有研究对比
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个学术讨论写作专家。
你的职责是：
1. 深化讨论内容
2. 指导与已有研究对比
3. 识别研究局限性
4. 提出未来研究方向

请确保讨论深入、有洞察力、与已有研究建立联系。"""
        super().__init__(
            name="discussion_deepener",
            target_problem="讨论部分薄弱/缺乏深度",
            llm_config=llm_config,
            description="讨论章节深化",
            system_prompt=system_prompt
        )

    async def diagnose(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        深化讨论内容

        输入：
        - results: 研究结果
        - discussion: 现有讨论内容
        - literature: 相关文献摘要
        """
        results = input_data.get("results", "")
        discussion = input_data.get("discussion", "")
        literature = input_data.get("literature", [])

        if not results:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["研究结果为空"],
                recommendations=["请提供研究结果"],
                quality_score=0.0,
                error="Empty results"
            )

        try:
            # 1. 评估现有讨论深度
            depth_assessment = await self._assess_depth(discussion, results)

            # 2. 指导与已有研究对比
            comparisons = await self._guide_comparisons(results, literature)

            # 3. 识别需要讨论的要点
            discussion_points = await self._identify_discussion_points(results)

            # 4. 指导局限性分析
            limitations = await self._guide_limitation_analysis(results)

            # 5. 指导未来方向
            future_directions = await self._guide_future_directions(results, limitations)

            # 6. 生成改进建议
            recommendations = await self._generate_recommendations(
                depth_assessment, comparisons, discussion_points
            )

            # 质量评分
            depth_score = depth_assessment.get("depth_score", 5) / 10.0
            quality_score = round(depth_score * 0.5 + comparisons.get("comparison_depth", 0.5) * 0.5, 2)

            return AgentOutput(
                success=True,
                result={
                    "depth_assessment": depth_assessment,
                    "comparisons": comparisons,
                    "discussion_points": discussion_points,
                    "limitations": limitations,
                    "future_directions": future_directions
                },
                agent_name=self.name,
                diagnosed_issues=depth_assessment.get("issues", []),
                recommendations=recommendations,
                quality_score=quality_score
            )

        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:117] Discussion deepening failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["讨论深化失败"],
                recommendations=["请提供完整的研究结果和讨论"],
                quality_score=0.0,
                error=str(e)
            )

    async def _assess_depth(self, discussion: str, results: str) -> Dict[str, Any]:
        """评估讨论深度"""
        prompt = f"""
评估以下讨论内容的深度：

研究结果：
{self._truncate(results, 500)}

现有讨论：
{self._truncate(discussion, 500)}

请检查：
1. 是否深入解释了结果意义？
2. 是否与已有研究对比？
3. 是否识别了局限性？
4. 是否提出了未来方向？
5. 讨论深度评分 (1-10)

输出JSON格式：
{{
    "depth_score": 6.5,
    "issues": ["问题1", "问题2"],
    "strengths": ["优点1", "优点2"],
    "missing_elements": ["缺失要素1", "缺失要素2"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:159] Depth assessment failed: {e}")
            return {"depth_score": 5.0, "issues": [], "missing_elements": []}

    async def _guide_comparisons(
        self,
        results: str,
        literature: List[Dict]
    ) -> Dict[str, Any]:
        """指导与已有研究对比"""
        prompt = f"""
基于以下研究结果，生成与已有研究对比的指导：

研究结果：
{self._truncate(results, 500)}

相关文献：{json.dumps(literature[:5], ensure_ascii=False)}

请提供：
1. 应该对比的已有研究
2. 对比维度（方法/结果/结论）
3. 如何展现差异和贡献

输出JSON格式：
{{
    "comparisons_to_make": [
        {{
            "paper": "文献标题",
            "dimension": "对比维度",
            "your_finding": "你的发现",
            "their_finding": "他们的发现",
            "significance": "差异意义"
        }}
    ],
    "comparison_depth": 0.75,
    "guidance": "对比写作指导"
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:201] Comparison guidance failed: {e}")
            return {"comparisons_to_make": [], "comparison_depth": 0.5}

    async def _identify_discussion_points(self, results: str) -> List[str]:
        """识别需要讨论的要点"""
        prompt = f"""
基于以下研究结果，识别需要深入讨论的要点：

研究结果：
{self._truncate(results, 800)}

请识别6-10个需要讨论的要点，涵盖：
1. 结果解释
2. 理论意义
3. 实践意义
4. 与预期的差异
5. 意外发现

输出JSON格式：
{{
    "points": [
        {{
            "point": "讨论要点",
            "type": "解释/意义/差异",
            "depth_guidance": "如何深入讨论"
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("points", [])
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:235] Discussion points identification failed: {e}")
            return []

    async def _guide_limitation_analysis(self, results: str) -> Dict[str, Any]:
        """指导局限性分析"""
        prompt = f"""
为以下研究提供局限性分析指导：

研究结果：
{self._truncate(results, 500)}

请识别：
1. 方法论局限
2. 样本局限
3. 测量局限
4. 外部效度局限
5. 其他局限

输出JSON格式：
{{
    "limitations": [
        {{
            "type": "局限类型",
            "description": "具体描述",
            "impact": "对结论的影响",
            "mitigation": "如何缓解或承认"
        }}
    ],
    "writing_guidance": "如何撰写局限性"
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:271] Limitation analysis guidance failed: {e}")
            return {"limitations": []}

    async def _guide_future_directions(self, results: str, limitations: Dict) -> List[str]:
        """指导未来研究方向"""
        prompt = f"""
基于以下研究和局限性，提出未来研究方向：

研究结果：{self._truncate(results, 400)}
局限性：{json.dumps(limitations, ensure_ascii=False)}

请提出3-5个具体、可行的未来研究方向：

输出JSON格式：
{{
    "future_directions": [
        {{
            "direction": "研究方向",
            "rationale": "理由",
            "feasibility": "可行性评估"
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("future_directions", [])
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:300] Future direction guidance failed: {e}")
            return []

    async def _generate_recommendations(
        self,
        depth_assessment: Dict,
        comparisons: Dict,
        discussion_points: List
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于深度评估
        for missing in depth_assessment.get("missing_elements", []):
            recommendations.append(f"补充讨论: {missing}")

        # 基于对比指导
        comparisons_to_make = comparisons.get("comparisons_to_make", [])
        if comparisons_to_make:
            recommendations.append(f"添加与{len(comparisons_to_make)}篇文献的对比分析")

        # 基于讨论要点
        if len(discussion_points) > 0:
            recommendations.append(f"深入探讨{len(discussion_points)}个关键要点")

        if not recommendations:
            recommendations.append("讨论深度基本合格，可进一步完善")

        return recommendations[:5]

    def _truncate(self, text: str, max_length: int) -> str:
        if not text:
            return ""
        return text[:max_length] + "..." if len(text) > max_length else text
