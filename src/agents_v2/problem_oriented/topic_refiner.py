"""
TopicRefinerAgent - 选题精炼Agent

针对问题：选题困难、选题太大/太偏/缺乏创新性

职责：
- 分析用户初步想法
- 评估选题可行性
- 帮助缩小/优化选题
- 检查创新性
"""
from typing import Any, Dict, List, Optional
import json
import logging

from .base_problem_agent import ProblemAgentBase, AgentOutput, LLMConfig

logger = logging.getLogger(__name__)


class TopicRefinerAgent(ProblemAgentBase):
    """
    TopicRefinerAgent - 选题精炼

    针对问题：
    - 选题太大或太偏
    - 缺乏创新性/跟风
    - 超出研究能力
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个学术研究选题专家。
你的职责是帮助用户优化研究选题，确保：
1. 选题具体、可执行
2. 具有创新性
3. 在用户能力范围内
4. 有研究价值

请分析用户输入，诊断问题，并提供具体改进建议。"""
        super().__init__(
            name="topic_refiner",
            target_problem="选题困难/缺乏创新性",
            llm_config=llm_config,
            description="选题精炼与创新性评估",
            system_prompt=system_prompt
        )

    async def diagnose(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        诊断选题问题

        输入：
        - user_idea: 用户的研究想法/初步主题
        - user_level: 用户研究水平（本科/硕士/博士）
        - available_time: 可用时间
        - available_resources: 可用资源
        """
        user_idea = input_data.get("user_idea", input_data.get("topic", ""))
        user_level = input_data.get("user_level", "硕士")
        available_time = input_data.get("available_time", "6个月")
        available_resources = input_data.get("available_resources", "一般")

        if not user_idea:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["研究主题为空"],
                recommendations=["请提供具体的研究兴趣或初步想法"],
                quality_score=0.0,
                error="Empty topic"
            )

        try:
            # 1. 分析选题问题
            issues = await self._analyze_topic_issues(user_idea, user_level)

            # 2. 评估可行性
            feasibility = await self._evaluate_feasibility(
                user_idea, user_level, available_time, available_resources
            )

            # 3. 评估创新性
            novelty = await self._evaluate_novelty(user_idea)

            # 4. 生成优化建议
            recommendations = await self._generate_recommendations(
                issues, feasibility, novelty
            )

            # 5. 生成优化后的选题
            refined_topic = await self._refine_topic(user_idea, recommendations)

            # 计算质量分数
            quality_score = self._calculate_quality_score(feasibility, novelty)

            return AgentOutput(
                success=True,
                result={
                    "original_topic": user_idea,
                    "refined_topic": refined_topic,
                    "feasibility": feasibility,
                    "novelty": novelty,
                    "scope_assessment": issues
                },
                agent_name=self.name,
                diagnosed_issues=issues,
                recommendations=recommendations,
                quality_score=quality_score
            )

        except Exception as e:
            self.logger.error(f"Topic refinement failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["选题分析失败"],
                recommendations=["请提供更详细的研究想法"],
                quality_score=0.0,
                error=str(e)
            )

    async def _analyze_topic_issues(self, topic: str, user_level: str) -> List[str]:
        """分析选题问题"""
        prompt = f"""
分析以下研究选题的问题：

选题：{topic}
研究者水平：{user_level}

请诊断以下常见问题：
1. 选题是否过于宽泛？
2. 选题是否过于狭窄？
3. 选题是否缺乏创新性？
4. 选题是否符合学术规范？
5. 选题是否适合研究者水平？

输出JSON格式：
{{
    "issues": ["问题1", "问题2", ...],
    "scope_assessment": {{
        "too_broad": true/false,
        "too_narrow": true/false,
        "main_issue": "主要问题描述"
    }}
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("issues", [])
        except Exception as e:
            logger.error(f"Topic analysis failed: {e}")
            return ["选题需要进一步明确"]

    async def _evaluate_feasibility(
        self,
        topic: str,
        user_level: str,
        available_time: str,
        available_resources: str
    ) -> Dict[str, Any]:
        """评估可行性"""
        prompt = f"""
评估以下研究选题的可行性：

选题：{topic}
研究者水平：{user_level}
可用时间：{available_time}
可用资源：{available_resources}

请评估：
1. 时间可行性
2. 资源可行性
3. 能力匹配度
4. 总体可行性评分(1-10)

输出JSON格式：
{{
    "feasible": true/false,
    "time_feasibility": "评估",
    "resource_feasibility": "评估",
    "skill_match": "评估",
    "overall_score": 7.5,
    "concerns": ["担忧1", "担忧2"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"Feasibility evaluation failed: {e}")
            return {"feasible": True, "overall_score": 5.0, "concerns": []}

    async def _evaluate_novelty(self, topic: str) -> Dict[str, Any]:
        """评估创新性"""
        prompt = f"""
评估以下研究选题的创新性：

选题：{topic}

请分析：
1. 是否有新颖的研究角度？
2. 是否填补研究空白？
3. 是否有独特贡献？
4. 创新性评分(1-10)

输出JSON格式：
{{
    "novel": true/false,
    "novelty_aspects": ["创新点1", "创新点2"],
    "potential_gaps": ["gap1", "gap2"],
    "novelty_score": 6.5
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"Novelty evaluation failed: {e}")
            return {"novel": False, "novelty_score": 5.0}

    async def _generate_recommendations(
        self,
        issues: List[str],
        feasibility: Dict[str, Any],
        novelty: Dict[str, Any]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于问题生成建议
        if any("宽泛" in issue or "too broad" in issue.lower() for issue in issues):
            recommendations.append("缩小研究范围，聚焦于具体问题")

        if any("狭窄" in issue or "too narrow" in issue.lower() for issue in issues):
            recommendations.append("拓宽研究角度，考虑相关领域")

        if not novelty.get("novel", True):
            recommendations.append("寻找独特的研究视角或方法创新")

        if not feasibility.get("feasible", True):
            for concern in feasibility.get("concerns", []):
                recommendations.append(f"解决可行性问题: {concern}")

        if not recommendations:
            recommendations.append("选题基本可行，可进一步细化")

        return recommendations[:5]  # 限制建议数量

    async def _refine_topic(self, original: str, recommendations: List[str]) -> str:
        """生成优化后的选题"""
        prompt = f"""
基于以下建议，优化研究选题：

原始选题：{original}
改进建议：{json.dumps(recommendations, ensure_ascii=False)}

请生成3个优化后的选题建议，每个都要：
1. 具体明确
2. 具有可执行性
3. 体现创新性

输出JSON格式：
{{
    "refined_topics": [
        {{"title": "优化选题1", "description": "描述"}},
        {{"title": "优化选题2", "description": "描述"}},
        {{"title": "优化选题3", "description": "描述"}}
    ],
    "best_choice": "最佳选题标题"
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("best_choice", original)
        except Exception as e:
            logger.error(f"Topic refinement failed: {e}")
            return original

    def _calculate_quality_score(self, feasibility: Dict, novelty: Dict) -> float:
        """计算综合质量分数"""
        fea_score = feasibility.get("overall_score", 5.0) / 10.0
        nov_score = novelty.get("novelty_score", 5.0) / 10.0

        # 综合评分：可行性60%，创新性40%
        return round(fea_score * 0.6 + nov_score * 0.4, 2)
