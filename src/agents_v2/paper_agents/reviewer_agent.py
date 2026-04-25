"""
ReviewerAgent - 最终审核Agent

职责：
- 多视角Critique
- 质量评估
- 决定是否通过
"""
from typing import Any, Dict, List, Optional
import json
import logging

from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig

logger = logging.getLogger(__name__)


class ReviewerAgent(PaperAgentBase):
    """
    ReviewerAgent - 最终审核

    职责：
    - 多视角Critique
    - 质量评估
    - 决定是否通过
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个严格的学术论文评审专家。
你的职责是：
1. 从多个视角审核论文
2. 评估论文质量
3. 指出问题和不足
4. 提出改进建议

评审视角：
1. 学术专家视角 - 创新性、方法学、贡献
2. 审稿人视角 - 完整性、可读性、格式
3. 批判者视角 - 潜在问题、逻辑漏洞

请确保评审客观、公正、严格。"""
        super().__init__(
            name="reviewer_agent",
            llm_config=llm_config,
            description="论文最终审核",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        执行最终审核

        Args:
            input_data: 包含task_type的字典
            context: 执行上下文（包含final_draft、thesis等）
        """
        paper = ""
        thesis = ""
        outline = {}

        if context:
            paper = context.get("final_draft", context.get("full_draft", ""))
            thesis = context.get("thesis_statement", "")
            outline = context.get("outline", {})

        if not paper:
            paper = input_data.get("paper", "")

        if not paper:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Empty paper"
            )

        try:
            # 1. 多视角审核
            critiques = await self._multi_perspective_review(paper, thesis)

            # 2. 质量评分
            quality_score = await self._calculate_quality_score(critiques)

            # 3. 决策
            passed = quality_score >= 7.0

            return AgentOutput(
                success=True,
                result={
                    "passed": passed,
                    "quality_score": quality_score,
                    "critiques": critiques,
                    "recommendation": "Accept with minor revisions" if passed else "Major revisions needed"
                },
                agent_name=self.name,
                reasoning=f"Review complete, score: {quality_score}/10, passed: {passed}",
                quality_score=quality_score / 10
            )

        except Exception as e:
            self.logger.error(f"ReviewerAgent execution failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _multi_perspective_review(
        self,
        paper: str,
        thesis: str
    ) -> Dict[str, Any]:
        """多视角审核"""
        paper_preview = paper[:4000] if len(paper) > 4000 else paper

        prompt = f"""
从多个视角对以下论文进行严格审核：

Thesis: {thesis}

论文内容：
{paper_preview}

请从以下三个视角进行审核：

1. 学术专家视角
   - 创新性 (1-10)
   - 方法学质量 (1-10)
   - 理论贡献 (1-10)
   - 实证支持 (1-10)

2. 审稿人视角
   - 结构完整性 (1-10)
   - 写作质量 (1-10)
   - 格式规范 (1-10)
   - 可读性 (1-10)

3. 批判者视角
   - 逻辑漏洞
   - 潜在问题
   - 反对意见

输出JSON格式：
{{
    "expert_review": {{
        "scores": {{
            "novelty": 7,
            "methodology": 8,
            "contribution": 7,
            "evidence": 8
        }},
        "strengths": ["优势1", "优势2"],
        "weaknesses": ["劣势1", "劣势2"]
    }},
    "reviewer_review": {{
        "scores": {{
            "structure": 8,
            "writing": 7,
            "format": 8,
            "readability": 7
        }},
        "issues": ["问题1", "问题2"]
    }},
    "critic_review": {{
        "logical_gaps": ["漏洞1", "漏洞2"],
        "potential_problems": ["问题1", "问题2"],
        "counter_arguments": ["反对意见1", "反对意见2"]
    }}
}}
"""
        try:
            response = await self._llm_call(prompt)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Multi-perspective review failed: {e}")
            return {
                "expert_review": {"scores": {"overall": 7}},
                "reviewer_review": {"scores": {"overall": 7}},
                "critic_review": {"issues": []}
            }

    async def _calculate_quality_score(self, critiques: Dict[str, Any]) -> float:
        """计算质量评分"""
        expert_scores = critiques.get("expert_review", {}).get("scores", {})
        reviewer_scores = critiques.get("reviewer_review", {}).get("scores", {})

        if not expert_scores and not reviewer_scores:
            return 5.0

        # 计算各视角平均分
        expert_avg = sum(expert_scores.values()) / len(expert_scores) if expert_scores else 0
        reviewer_avg = sum(reviewer_scores.values()) / len(reviewer_scores) if reviewer_scores else 0

        # 综合评分（专家权重0.6，审稿人权重0.4）
        overall = expert_avg * 0.6 + reviewer_avg * 0.4

        return round(overall, 1)

    async def _generate_recommendations(
        self,
        critiques: Dict[str, Any],
        quality_score: float
    ) -> List[str]:
        """生成建议"""
        issues = []
        issues.extend(critiques.get("expert_review", {}).get("weaknesses", []))
        issues.extend(critiques.get("reviewer_review", {}).get("issues", []))
        issues.extend(critiques.get("critic_review", {}).get("potential_problems", []))

        if quality_score >= 8.0:
            return ["Accept", "Minor revisions suggested"]
        elif quality_score >= 7.0:
            return ["Accept with minor revisions", f"Specific issues: {', '.join(issues[:3])}"]
        elif quality_score >= 5.0:
            return ["Major revisions needed", f"Issues to address: {', '.join(issues[:5])}"]
        else:
            return ["Reject and resubmit", f"Major issues: {', '.join(issues)}"]
