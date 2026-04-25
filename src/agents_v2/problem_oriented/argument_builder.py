"""
ArgumentBuilderAgent - 论证构建Agent

针对问题：论证逻辑不严密、结构不清晰

职责：
- 帮助构建论证框架
- 检查逻辑连贯性
- 识别逻辑漏洞
- 强化论点支撑
"""
from typing import Any, Dict, List, Optional
import json
import logging

from .base_problem_agent import ProblemAgentBase, AgentOutput, LLMConfig

logger = logging.getLogger(__name__)


class ArgumentBuilderAgent(ProblemAgentBase):
    """
    ArgumentBuilderAgent - 论证构建

    针对问题：
    - 逻辑混乱
    - 结构不清晰
    - 论点论据脱节
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个论证结构专家。
你的职责是：
1. 帮助构建清晰的论证框架
2. 检查逻辑连贯性
3. 识别论证漏洞
4. 强化论点支撑

请确保论证逻辑严密、结构清晰、论据充分。"""
        super().__init__(
            name="argument_builder",
            target_problem="论证逻辑不严密/结构不清晰",
            llm_config=llm_config,
            description="论证逻辑构建与检查",
            system_prompt=system_prompt
        )

    async def diagnose(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        诊断论证问题

        输入：
        - thesis: 论文论点
        - arguments: 论证结构
        - evidence: 支持证据
        """
        thesis = input_data.get("thesis", "")
        arguments = input_data.get("arguments", [])
        evidence = input_data.get("evidence", [])

        if not thesis:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["论点为空"],
                recommendations=["请提供明确的论文论点"],
                quality_score=0.0,
                error="Empty thesis"
            )

        try:
            # 1. 构建论证框架
            framework = await self._build_argument_framework(thesis, arguments)

            # 2. 检查逻辑连贯性
            coherence = await self._check_coherence(thesis, framework)

            # 3. 识别逻辑漏洞
            gaps = await self._identify_logical_gaps(thesis, framework, evidence)

            # 4. 评估论据支撑
            support = await self._evaluate_support(framework, evidence)

            # 5. 生成改进建议
            recommendations = await self._generate_recommendations(coherence, gaps, support)

            # 质量评分
            logic_score = coherence.get("score", 5) / 10.0
            support_score = support.get("overall", 5) / 10.0
            quality_score = round(logic_score * 0.6 + support_score * 0.4, 2)

            return AgentOutput(
                success=True,
                result={
                    "thesis": thesis,
                    "argument_framework": framework,
                    "coherence": coherence,
                    "logical_gaps": gaps,
                    "support_evaluation": support
                },
                agent_name=self.name,
                diagnosed_issues=[g.get("description", "") for g in gaps] + coherence.get("issues", []),
                recommendations=recommendations,
                quality_score=quality_score
            )

        except Exception as e:
            self.logger.error(f"Argument building failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["论证分析失败"],
                recommendations=["请提供完整的论证内容"],
                quality_score=0.0,
                error=str(e)
            )

    async def _build_argument_framework(
        self,
        thesis: str,
        arguments: List
    ) -> Dict[str, Any]:
        """构建论证框架"""
        prompt = f"""
为以下论点构建论证框架：

论点：{thesis}
已有论证：{json.dumps(arguments, ensure_ascii=False)}

请构建：
1. 主论点
2. 分论点（2-4个）
3. 每个分论点的子论点
4. 论点之间的关系

输出JSON格式：
{{
    "main_thesis": "主论点",
    "sub_theses": [
        {{
            "id": 1,
            "statement": "分论点1",
            "supporting_points": ["支撑点1", "支撑点2"],
            "relationship": "与主论点关系"
        }}
    ],
    "structure_type": "演绎/归纳/类比"
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"Framework building failed: {e}")
            return {"main_thesis": thesis, "sub_theses": [], "structure_type": "unknown"}

    async def _check_coherence(self, thesis: str, framework: Dict) -> Dict[str, Any]:
        """检查逻辑连贯性"""
        prompt = f"""
检查以下论证的逻辑连贯性：

论点：{thesis}
论证框架：{json.dumps(framework, ensure_ascii=False)}

请检查：
1. 论点与分论点是否一致？
2. 分论点之间是否协调？
3. 论证路径是否清晰？
4. 是否有逻辑跳跃？

输出JSON格式：
{{
    "score": 7.5,
    "issues": ["问题1", "问题2"],
    "coherent": true/false,
    "suggestions": ["改进建议1", "改进建议2"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"Coherence check failed: {e}")
            return {"score": 5.0, "issues": [], "coherent": True}

    async def _identify_logical_gaps(
        self,
        thesis: str,
        framework: Dict,
        evidence: List
    ) -> List[Dict[str, str]]:
        """识别逻辑漏洞"""
        prompt = f"""
识别以下论证的逻辑漏洞：

论点：{thesis}
论证框架：{json.dumps(framework, ensure_ascii=False)}
已有证据：{json.dumps(evidence, ensure_ascii=False)}

请识别：
1. 未证明的假设
2. 缺失的逻辑环节
3. 需要更多证据支撑的地方
4. 可能的反驳

输出JSON格式：
{{
    "gaps": [
        {{
            "type": "假设/逻辑跳跃/证据不足",
            "description": "漏洞描述",
            "importance": "high/medium/low"
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("gaps", [])
        except Exception as e:
            logger.error(f"Gap identification failed: {e}")
            return []

    async def _evaluate_support(self, framework: Dict, evidence: List) -> Dict[str, Any]:
        """评估论据支撑"""
        prompt = f"""
评估以下论证的论据支撑：

论证框架：{json.dumps(framework, ensure_ascii=False)}
已有证据：{json.dumps(evidence, ensure_ascii=False)}

请评估：
1. 各分论点的证据支撑度 (1-10)
2. 整体证据充分性 (1-10)
3. 证据质量
4. 证据与论点关联度

输出JSON格式：
{{
    "sub_thesis_support": [
        {{"id": 1, "support_score": 7.5, "evidence_quality": "评估"}}
    ],
    "overall": 7.0,
    "weakest_point": "最薄弱的环节",
    "suggestions": ["改进建议"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"Support evaluation failed: {e}")
            return {"overall": 5.0}

    async def _generate_recommendations(
        self,
        coherence: Dict,
        gaps: List[Dict],
        support: Dict
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于连贯性问题
        for issue in coherence.get("issues", []):
            recommendations.append(f"解决连贯性问题: {issue}")

        # 基于逻辑漏洞
        high_priority_gaps = [g for g in gaps if g.get("importance") == "high"]
        for gap in high_priority_gaps:
            gap_type = gap.get("type", "")
            if "假设" in gap_type:
                recommendations.append(f"证明假设: {gap.get('description', '')}")
            elif "证据" in gap_type:
                recommendations.append(f"补充证据: {gap.get('description', '')}")

        # 基于支撑评估
        weakest = support.get("weakest_point", "")
        if weakest:
            recommendations.append(f"强化最薄弱环节: {weakest}")

        if not recommendations:
            recommendations.append("论证逻辑基本完整，可继续完善")

        return recommendations[:5]
