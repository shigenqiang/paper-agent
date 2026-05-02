"""
ReportRefinerAgent - 报告精炼Agent

职责：
- 多轮迭代优化
- 评审-修改-精炼循环
- 质量评估与改进
- 针对性问题修复
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

import json

from .base_writing_agent import WritingAgentBase, WritingOutput, LLMConfig

logger = get_logging_logger(__name__)


class ReportRefinerAgent(WritingAgentBase):
    """
    ReportRefinerAgent - 报告精炼（多轮迭代）

    职责：
    - 多轮迭代优化
    - 评审-修改-精炼循环
    - 质量评估与改进
    - 针对性问题修复
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个专业的学术论文评审和精炼专家。
你的职责是：
1. 多轮迭代优化论文质量
2. 评审论文问题
3. 针对性修改
4. 精炼语言和逻辑

请确保：
- 每次迭代都有实质性改进
- 问题修复准确
- 保持论文整体一致性"""
        super().__init__(
            name="report_refiner",
            llm_config=llm_config,
            description="报告精炼（多轮迭代）",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> WritingOutput:
        """
        执行报告精炼

        Args:
            input_data: 包含以下字段的字典：
                - draft: 初稿内容
                - focus_areas: 重点改进领域 (可选)
                - max_iterations: 最大迭代次数 (默认3)
                - quality_threshold: 质量阈值 (默认0.7)
            context: 执行上下文
        """
        draft = input_data.get("draft", "")
        focus_areas = input_data.get("focus_areas", [])
        max_iterations = input_data.get("max_iterations", 3)
        quality_threshold = input_data.get("quality_threshold", 0.7)

        if not draft:
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Empty draft"
            )

        try:
            # 1. 初始化评审
            current_draft = draft
            iteration_history = []
            quality_scores = []

            # 2. 多轮迭代精炼
            for iteration in range(max_iterations):
                # 评审当前版本
                review_result = await self._review_draft(
                    current_draft, iteration + 1, focus_areas
                )
                iteration_history.append(review_result)

                # 评估质量
                quality = review_result.get("quality_score", 0)
                quality_scores.append(quality)

                logger.info(f"Iteration {iteration + 1}: quality = {quality}")

                # 达到阈值则停止
                if quality >= quality_threshold:
                    logger.info(f"Quality threshold {quality_threshold} reached at iteration {iteration + 1}")
                    break

                # 如果问题严重，修复
                if review_result.get("issues"):
                    refined = await self._refine_draft(
                        current_draft, review_result, iteration + 1
                    )
                    current_draft = refined

            # 3. 最终精炼
            final_draft = await self._final_polish(current_draft)

            # 4. 生成改进报告
            improvement_report = self._generate_improvement_report(
                draft, final_draft, iteration_history, quality_scores
            )

            return WritingOutput(
                success=True,
                result={
                    "original_draft": draft,
                    "final_draft": final_draft,
                    "improvement_report": improvement_report,
                    "iterations_completed": len(iteration_history),
                    "final_quality_score": quality_scores[-1] if quality_scores else 0,
                    "quality_improvement": quality_scores[-1] - quality_scores[0] if len(quality_scores) > 1 else 0,
                    "iteration_details": iteration_history
                },
                agent_name=self.name,
                reasoning=f"Completed {len(iteration_history)} iterations, final quality: {quality_scores[-1] if quality_scores else 0}",
                quality_score=quality_scores[-1] if quality_scores else 0.5
            )

        except Exception as e:
            self.logger.error(f"ReportRefinerAgent execution failed: {e}")
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _review_draft(
        self,
        draft: str,
        iteration: int,
        focus_areas: List[str]
    ) -> Dict[str, Any]:
        """评审初稿"""
        focus_str = ", ".join(focus_areas) if focus_areas else "全面评审"

        prompt = f"""
评审论文初稿（第{iteration}轮）：

重点关注领域：{focus_str}

论文内容：
{draft[:2000]}{'...' if len(draft) > 2000 else ''}

评审维度：
1. 结构完整性
2. 逻辑连贯性
3. 论证充分性
4. 引用准确性
5. 语言表达
6. 格式规范性

输出JSON格式：
{{
    "quality_score": 0-1,
    "issues": [
        {{"type": "问题类型", "location": "位置", "description": "描述", "severity": "high/medium/low"}}
    ],
    "strengths": ["优点1", "优点2"],
    "suggestions": ["建议1", "建议2"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"Draft review failed: {e}")
            return {
                "quality_score": 0.5,
                "issues": [],
                "suggestions": ["评审服务暂时不可用"]
            }

    async def _refine_draft(
        self,
        draft: str,
        review_result: Dict[str, Any],
        iteration: int
    ) -> str:
        """精炼初稿"""
        issues = review_result.get("issues", [])
        suggestions = review_result.get("suggestions", [])

        if not issues:
            return draft

        prompt = f"""
根据评审意见精炼论文（第{iteration}轮）：

原始论文：
{draft}

评审发现的问题：
{json.dumps(issues, ensure_ascii=False)}

改进建议：
{json.dumps(suggestions, ensure_ascii=False)}

请根据评审意见修改论文：
1. 修复发现的问题
2. 采纳改进建议
3. 保持论文整体结构
4. 确保修改后逻辑连贯

输出修改后的完整论文。
"""
        try:
            response = await self._llm_call(prompt)
            return response
        except Exception as e:
            logger.error(f"Draft refinement failed: {e}")
            return draft

    async def _final_polish(self, draft: str) -> str:
        """最终润色"""
        prompt = f"""
对论文进行最终润色：

{draft}

润色要求：
1. 语言表达更流畅
2. 消除冗余表达
3. 统一术语使用
4. 优化段落衔接
5. 检查格式一致性

请输出润色后的完整论文。
"""
        try:
            response = await self._llm_call(prompt)
            return response
        except Exception as e:
            logger.error(f"Final polish failed: {e}")
            return draft

    def _generate_improvement_report(
        self,
        original: str,
        refined: str,
        iteration_history: List[Dict[str, Any]],
        quality_scores: List[float]
    ) -> str:
        """生成改进报告"""
        # 统计改进
        total_issues = sum(len(r.get("issues", [])) for r in iteration_history)
        resolved_issues = len(iteration_history[-1].get("issues", [])) if iteration_history else 0

        # 构建报告
        lines = [
            "# 论文改进报告\n",
            f"## 迭代统计",
            f"- 迭代次数: {len(iteration_history)}",
            f"- 初始质量: {quality_scores[0] if quality_scores else 'N/A'}",
            f"- 最终质量: {quality_scores[-1] if quality_scores else 'N/A'}",
            f"- 质量提升: {quality_scores[-1] - quality_scores[0] if len(quality_scores) > 1 else 0:.2f}",
            "",
            f"## 问题修复",
            f"- 发现问题总数: {total_issues}",
            f"- 修复问题数: {total_issues - resolved_issues}",
            f"- 剩余问题数: {resolved_issues}",
            ""
        ]

        # 各轮详情
        if len(iteration_history) > 1:
            lines.append("## 各轮改进详情\n")
            for i, result in enumerate(iteration_history):
                lines.append(f"### 第{i+1}轮")
                lines.append(f"- 质量评分: {result.get('quality_score', 'N/A')}")
                issues = result.get("issues", [])
                if issues:
                    lines.append(f"- 问题: {len(issues)}个")
                    for issue in issues[:3]:
                        lines.append(f"  - {issue.get('type')}: {issue.get('description')}")
                lines.append("")

        return "\n".join(lines)


class ReviewerAgent(WritingAgentBase):
    """
    ReviewerAgent - 评审Agent（单次评审）

    与ReportRefinerAgent不同，ReviewerAgent只执行单次评审，不进行迭代修改
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个专业的学术论文评审专家。
你的职责是：
1. 评估论文质量
2. 识别问题
3. 提供改进建议

请确保评审客观公正，建议具体可行。"""
        super().__init__(
            name="reviewer",
            llm_config=llm_config,
            description="论文质量评审",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> WritingOutput:
        """
        执行评审

        Args:
            input_data: 包含以下字段的字典：
                - draft: 要评审的论文
                - criteria: 评审标准 (可选)
        """
        draft = input_data.get("draft", "")
        criteria = input_data.get("criteria", [])

        if not draft:
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Empty draft"
            )

        try:
            # 执行评审
            review_result = await self._perform_review(draft, criteria)

            return WritingOutput(
                success=True,
                result=review_result,
                agent_name=self.name,
                reasoning=f"Quality score: {review_result.get('quality_score', 0)}",
                quality_score=review_result.get("quality_score", 0)
            )

        except Exception as e:
            self.logger.error(f"ReviewerAgent execution failed: {e}")
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _perform_review(
        self,
        draft: str,
        criteria: List[str]
    ) -> Dict[str, Any]:
        """执行评审"""
        criteria_str = ", ".join(criteria) if criteria else "结构、逻辑、论证、引用、语言"

        prompt = f"""
评审以下学术论文：

评审标准：{criteria_str}

论文内容：
{draft[:3000]}{'...' if len(draft) > 3000 else ''}

请进行全面评审，输出JSON格式：
{{
    "quality_score": 0-1,
    "dimension_scores": {{
        "structure": 0-10,
        "logic": 0-10,
        "argumentation": 0-10,
        "citation": 0-10,
        "language": 0-10
    }},
    "issues": [
        {{"dimension": "维度", "description": "问题描述", "severity": "high/medium/low"}}
    ],
    "strengths": ["优点"],
    "improvement_suggestions": ["建议"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"Review failed: {e}")
            return {"quality_score": 0.5, "issues": [], "improvement_suggestions": []}
