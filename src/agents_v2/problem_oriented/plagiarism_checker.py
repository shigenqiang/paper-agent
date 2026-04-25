"""
PlagiarismCheckerAgent - 查重检测Agent

针对问题：查重/原创性问题

职责：
- 识别高复制段落
- 提供改写建议
- 强化原创观点
"""
from typing import Any, Dict, List, Optional
import json
import logging

from .base_problem_agent import ProblemAgentBase, AgentOutput, LLMConfig

logger = logging.getLogger(__name__)


class PlagiarismCheckerAgent(ProblemAgentBase):
    """
    PlagiarismCheckerAgent - 查重检测

    针对问题：
    - 复制比率高
    - 缺乏原创观点
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个学术诚信专家。
你的职责是：
1. 识别高复制风险段落
2. 提供改写建议
3. 强化原创观点

请确保论文原创性，避免学术不端。"""
        super().__init__(
            name="plagiarism_checker",
            target_problem="查重问题/缺乏原创性",
            llm_config=llm_config,
            description="原创性检查与改写建议",
            system_prompt=system_prompt
        )

    async def diagnose(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        检查原创性

        输入：
        - text: 需要检查的文本
        - cited_sources: 已引用的文献（可选）
        - similarity_threshold: 相似度阈值（默认30%）
        """
        text = input_data.get("text", "")
        cited_sources = input_data.get("cited_sources", [])
        similarity_threshold = input_data.get("similarity_threshold", 30)

        if not text:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["文本为空"],
                recommendations=["请提供需要检查的文本"],
                quality_score=0.0,
                error="Empty text"
            )

        try:
            # 1. 识别高风险段落
            high_risk = await self._identify_high_risk(text, cited_sources)

            # 2. 评估整体原创性
            originality = await self._assess_originality(text, high_risk)

            # 3. 识别可改进之处
            improvement_points = await self._identify_improvement_points(text, cited_sources)

            # 4. 生成改写建议
            rewrite_suggestions = await self._generate_rewrite_suggestions(high_risk)

            # 5. 强化原创建议
            originality_suggestions = await self._suggest_originality_improvements(text, originality)

            # 质量评分
            quality_score = originality.get("originality_score", 0.7)

            return AgentOutput(
                success=True,
                result={
                    "high_risk_segments": high_risk,
                    "originality_assessment": originality,
                    "improvement_points": improvement_points,
                    "rewrite_suggestions": rewrite_suggestions,
                    "similarity_threshold": similarity_threshold
                },
                agent_name=self.name,
                diagnosed_issues=[seg.get("segment", "")[:50] + "..." for seg in high_risk[:3]],
                recommendations=rewrite_suggestions[:3] + originality_suggestions[:2],
                quality_score=quality_score
            )

        except Exception as e:
            self.logger.error(f"Plagiarism check failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["原创性检查失败"],
                recommendations=["请提供完整文本"],
                quality_score=0.0,
                error=str(e)
            )

    async def _identify_high_risk(
        self,
        text: str,
        cited_sources: List[str]
    ) -> List[Dict[str, Any]]:
        """识别高风险段落"""
        prompt = f"""
识别以下文本中可能存在高复制风险的段落：

文本：
{self._truncate(text, 2000)}

已引用文献：{json.dumps(cited_sources[:5], ensure_ascii=False)}

请识别：
1. 直接复制但未引用的内容
2. 与已有文献高度相似的段落
3. 常见短语和陈词滥调
4. 可以更强掉原创性的地方

输出JSON格式：
{{
    "high_risk": [
        {{
            "segment": "高风险段落原文",
            "risk_type": "未引用/高度相似/陈词滥调",
            "risk_level": "high/medium/low",
            "source_hint": "可能的来源提示"
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("high_risk", [])
        except Exception as e:
            logger.error(f"High risk identification failed: {e}")
            return []

    async def _assess_originality(self, text: str, high_risk: List[Dict]) -> Dict[str, Any]:
        """评估整体原创性"""
        total_length = len(text)
        high_risk_length = sum(len(seg.get("segment", "")) for seg in high_risk)
        risk_ratio = high_risk_length / total_length if total_length > 0 else 0

        originality_score = 1.0 - min(1.0, risk_ratio * 2)  # 风险越高，原创性越低

        return {
            "originality_score": round(originality_score, 2),
            "risk_ratio": round(risk_ratio, 2),
            "assessment": "高原创性" if originality_score > 0.8 else "需改进" if originality_score > 0.5 else "存在风险"
        }

    async def _identify_improvement_points(
        self,
        text: str,
        cited_sources: List[str]
    ) -> List[str]:
        """识别可改进之处"""
        prompt = f"""
识别以下文本中可以更强掉原创性的地方：

文本：
{self._truncate(text, 1500)}

请识别：
1. 缺乏自己观点的描述性段落
2. 可以加入批判性分析的地方
3. 可以提出新见解的地方
4. 需要加强个人贡献的地方

输出JSON格式：
{{
    "points": [
        {{
            "location": "位置描述",
            "current": "当前内容",
            "improvement": "改进建议"
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return [p.get("improvement", "") for p in data.get("points", [])]
        except Exception as e:
            logger.error(f"Improvement points identification failed: {e}")
            return []

    async def _generate_rewrite_suggestions(self, high_risk: List[Dict]) -> List[str]:
        """生成改写建议"""
        suggestions = []

        for seg in high_risk[:5]:
            risk_type = seg.get("risk_type", "")
            segment = seg.get("segment", "")[:50]

            if "未引用" in risk_type:
                suggestions.append(f"添加引用或改写: \"{segment}...\"")
            elif "高度相似" in risk_type:
                suggestions.append(f"重新表述以避免相似: \"{segment}...\"")
            elif "陈词滥调" in risk_type:
                suggestions.append(f"更新为更具体的表达: \"{segment}...\"")

        if not suggestions:
            suggestions.append("文本原创性良好")

        return suggestions

    async def _suggest_originality_improvements(
        self,
        text: str,
        originality: Dict
    ) -> List[str]:
        """强化原创建议"""
        score = originality.get("originality_score", 0.5)

        if score > 0.8:
            return ["保持现有原创性，可以进一步深化分析"]

        prompt = f"""
为以下文本提供强化原创性的建议：

文本：
{self._truncate(text, 1000)}

当前原创性评分：{score}

请提供：
1. 如何增加原创贡献
2. 如何提出独特见解
3. 如何强化批判性分析

输出JSON格式：
{{
    "suggestions": ["建议1", "建议2", "建议3"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("suggestions", [])
        except Exception as e:
            logger.error(f"Originality suggestions failed: {e}")
            return []

    def _truncate(self, text: str, max_length: int) -> str:
        if not text:
            return ""
        return text[:max_length] + "..." if len(text) > max_length else text
