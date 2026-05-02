"""
ReviewerAgent - 最终审核Agent

职责：
- 多视角Critique
- 7维度质量评估（与QualityEvaluator对齐）
- 结构化评审报告
- 决定是否通过
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

import json

from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig

logger = get_logging_logger(__name__)

# 7维度定义（与QualityEvaluator一致）
REVIEW_DIMENSIONS = {
    "structure": {"weight": 0.20, "label": "结构完整性", "description": "章节结构、标题层次、段落组织"},
    "logic": {"weight": 0.20, "label": "逻辑连贯性", "description": "论证逻辑、段落衔接、因果关系"},
    "originality": {"weight": 0.15, "label": "原创性", "description": "独立见解、创新方法、新颖观点"},
    "language": {"weight": 0.15, "label": "语言质量", "description": "学术用语、表述清晰、语法规范"},
    "citation": {"weight": 0.15, "label": "引用规范", "description": "引用数量、格式一致、来源权威"},
    "completeness": {"weight": 0.10, "label": "内容完整", "description": "覆盖全面、分析深入、无重大遗漏"},
    "format": {"weight": 0.05, "label": "格式规范", "description": "Markdown语法、排版美观、图表规范"},
}


class ReviewerAgent(PaperAgentBase):
    """
    ReviewerAgent - 结构化评审

    输出7维度评分 + 多视角Critique，与QualityEvaluator体系对齐。
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个严格的学术论文评审专家。
你的职责是：
1. 从7个维度对论文进行结构化评分
2. 从多个视角进行深度审核
3. 指出问题和不足，提出改进建议

请确保评审客观、公正、严格，评分有理有据。"""
        super().__init__(
            name="reviewer_agent",
            llm_config=llm_config,
            description="论文结构化评审（7维度 + 多视角）",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        执行结构化评审

        Args:
            input_data: {"paper": str, "rubric": str (optional)}
            context: {"final_draft", "thesis_statement", "outline"}
        """
        paper = ""
        thesis = ""
        rubric = input_data.get("rubric", "")

        if context:
            paper = context.get("final_draft", context.get("full_draft", ""))
            thesis = context.get("thesis_statement", "")

        if not paper:
            paper = input_data.get("paper", "")

        if not paper:
            return AgentOutput(
                success=False, result=None, agent_name=self.name,
                error="Empty paper"
            )

        try:
            # 1. 规则引擎预检
            rule_scores = self._rule_engine_check(paper)

            # 2. LLM多维度评审
            llm_review = await self._llm_structured_review(paper, thesis, rubric)

            # 3. 合并规则+LLM分数
            dimension_scores = self._merge_scores(rule_scores, llm_review)

            # 4. 多视角Critique
            critiques = llm_review.get("critiques", {})

            # 5. 计算加权总分
            overall_score = sum(
                dimension_scores[dim] * REVIEW_DIMENSIONS[dim]["weight"]
                for dim in REVIEW_DIMENSIONS
            )

            # 6. 决策
            passed = overall_score >= 0.7

            # 7. 生成结构化报告
            report = self._build_review_report(
                dimension_scores, critiques, overall_score, passed
            )

            return AgentOutput(
                success=True,
                result=report,
                agent_name=self.name,
                reasoning=f"Structured review: {overall_score:.2f}/1.0, passed={passed}",
                quality_score=overall_score,
            )

        except Exception as e:
            self.logger.error(f"ReviewerAgent execution failed: {e}")
            return AgentOutput(
                success=False, result=None, agent_name=self.name,
                error=str(e)
            )

    def _rule_engine_check(self, paper: str) -> Dict[str, float]:
        """规则引擎快速评分"""
        import re
        scores: Dict[str, float] = {}

        # structure
        headings = re.findall(r'^#{1,6}\s+.+', paper, re.MULTILINE)
        paragraphs = [p.strip() for p in paper.split('\n\n') if p.strip()]
        s = 1.0
        if len(headings) < 2:
            s -= 0.3
        if len(paragraphs) < 3:
            s -= 0.2
        scores["structure"] = max(0.0, s)

        # logic
        connectors = ['因此', '然而', '此外', '同时', '首先', '其次', 'however', 'therefore']
        c_count = sum(1 for c in connectors if c.lower() in paper.lower())
        scores["logic"] = min(1.0, 0.5 + c_count * 0.1)

        # originality
        opinion = ['本文认为', '我们认为', '笔者', 'we argue', 'we propose']
        o_count = sum(1 for m in opinion if m.lower() in paper.lower())
        scores["originality"] = min(1.0, 0.6 + o_count * 0.15)

        # language
        scores["language"] = 0.8  # default, needs LLM

        # citation
        citations = re.findall(r'\[[\d,\s\-]+\]|\([^)]*\d{4}[^)]*\)', paper)
        has_refs = bool(re.search(r'(?i)#+\s*(参考文献|references)', paper))
        c_score = 0.5
        if len(citations) >= 3:
            c_score += 0.3
        if has_refs:
            c_score += 0.2
        scores["citation"] = min(1.0, c_score)

        # completeness
        char_count = len(paper)
        scores["completeness"] = 1.0 if char_count > 3000 else (0.6 if char_count > 1000 else 0.3)

        # format
        unclosed = paper.count('```') % 2
        scores["format"] = 0.8 if not unclosed else 0.6

        return scores

    async def _llm_structured_review(
        self, paper: str, thesis: str, rubric: str
    ) -> Dict[str, Any]:
        """LLM结构化评审"""
        paper_preview = paper[:4000] if len(paper) > 4000 else paper
        rubric_str = f"\n额外评审标准：{rubric}" if rubric else ""

        prompt = f"""对以下论文进行严格的结构化评审。

Thesis: {thesis}{rubric_str}

论文内容：
{paper_preview}

请输出JSON格式，包含：

1. 7维度评分（每个0-10分）：
   - structure: 结构完整性（章节结构、标题层次）
   - logic: 逻辑连贯性（论证逻辑、段落衔接）
   - originality: 原创性（独立见解、创新方法）
   - language: 语言质量（学术用语、表述清晰）
   - citation: 引用规范（引用数量、格式一致）
   - completeness: 内容完整（覆盖全面、分析深入）
   - format: 格式规范（排版美观、图表规范）

2. 多视角Critique：
   - expert_view: 学术专家视角（创新性、方法学、贡献）
   - reviewer_view: 审稿人视角（完整性、可读性）
   - critic_view: 批判者视角（逻辑漏洞、反面论点）

3. 整体建议

JSON格式：
{{
    "dimension_scores": {{
        "structure": 8,
        "logic": 7,
        "originality": 6,
        "language": 8,
        "citation": 7,
        "completeness": 7,
        "format": 8
    }},
    "critiques": {{
        "expert_view": {{
            "strengths": ["..."],
            "weaknesses": ["..."],
            "scores": {{"novelty": 7, "methodology": 8, "contribution": 7}}
        }},
        "reviewer_view": {{
            "issues": ["..."],
            "readability_score": 7
        }},
        "critic_view": {{
            "logical_gaps": ["..."],
            "counter_arguments": ["..."]
        }}
    }},
    "recommendation": "Accept with minor revisions",
    "suggestions": ["建议1", "建议2"]
}}"""

        try:
            response = await self._llm_call(prompt)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"LLM structured review failed: {e}")
            return {
                "dimension_scores": {dim: 6 for dim in REVIEW_DIMENSIONS},
                "critiques": {},
                "suggestions": ["评审服务暂时不可用"],
            }

    def _merge_scores(
        self, rule_scores: Dict[str, float], llm_review: Dict[str, Any]
    ) -> Dict[str, float]:
        """合并规则引擎和LLM评分（各占50%）"""
        llm_raw = llm_review.get("dimension_scores", {})
        merged = {}

        for dim in REVIEW_DIMENSIONS:
            rule_val = rule_scores.get(dim, 0.6)
            # LLM输出是0-10分，归一化到0-1
            llm_val = llm_raw.get(dim, 6) / 10.0
            # 取平均
            merged[dim] = round((rule_val + llm_val) / 2, 4)

        return merged

    def _build_review_report(
        self,
        dimension_scores: Dict[str, float],
        critiques: Dict[str, Any],
        overall_score: float,
        passed: bool,
    ) -> Dict[str, Any]:
        """构建结构化评审报告"""
        # 薄弱维度
        weak_dims = [
            dim for dim, score in dimension_scores.items()
            if score < 0.6
        ]

        # 收集所有issues
        all_issues = []
        expert = critiques.get("expert_view", {})
        reviewer = critiques.get("reviewer_view", {})
        critic = critiques.get("critic_view", {})

        for w in expert.get("weaknesses", []):
            all_issues.append({"source": "expert", "issue": w})
        for i in reviewer.get("issues", []):
            all_issues.append({"source": "reviewer", "issue": i})
        for g in critic.get("logical_gaps", []):
            all_issues.append({"source": "critic", "issue": g})

        # 决策
        if overall_score >= 0.85:
            recommendation = "Accept"
        elif overall_score >= 0.7:
            recommendation = "Accept with minor revisions"
        elif overall_score >= 0.5:
            recommendation = "Major revisions needed"
        else:
            recommendation = "Reject and resubmit"

        return {
            "passed": passed,
            "overall_score": round(overall_score, 4),
            "dimension_scores": {k: round(v, 4) for k, v in dimension_scores.items()},
            "dimension_details": {
                dim: {
                    "score": round(dimension_scores[dim], 4),
                    "weight": REVIEW_DIMENSIONS[dim]["weight"],
                    "weighted": round(dimension_scores[dim] * REVIEW_DIMENSIONS[dim]["weight"], 4),
                    "label": REVIEW_DIMENSIONS[dim]["label"],
                }
                for dim in REVIEW_DIMENSIONS
            },
            "weak_dimensions": weak_dims,
            "critiques": critiques,
            "issues": all_issues,
            "issue_count": len(all_issues),
            "recommendation": recommendation,
            "suggestions": critiques.get("suggestions", []),
        }

    async def _generate_recommendations(
        self, critiques: Dict[str, Any], quality_score: float
    ) -> List[str]:
        """生成建议"""
        issues = []
        issues.extend(critiques.get("expert_view", {}).get("weaknesses", []))
        issues.extend(critiques.get("reviewer_view", {}).get("issues", []))
        issues.extend(critiques.get("critic_view", {}).get("logical_gaps", []))

        if quality_score >= 0.85:
            return ["Accept", "Minor revisions suggested"]
        elif quality_score >= 0.7:
            return ["Accept with minor revisions", f"Issues: {', '.join(issues[:3])}"]
        elif quality_score >= 0.5:
            return ["Major revisions needed", f"Issues: {', '.join(issues[:5])}"]
        else:
            return ["Reject and resubmit", f"Major issues: {', '.join(issues)}"]
