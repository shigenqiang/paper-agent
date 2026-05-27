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
import re

from .base_writing_agent import WritingAgentBase, WritingOutput, LLMConfig
from ..workflow.unified.pydantic_validator import parse_json

logger = get_logging_logger(__name__)


class ReportRefinerAgent(WritingAgentBase):
    """
    ReportRefinerAgent - 报告精炼（多轮迭代）

    职责：
    - 多轮迭代精炼论文
    - 评审-修改-精炼循环
    - 质量评估与改进
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """## 角色定义
你是一位专业的学术论文评审与精炼专家，拥有多年学术编辑经验。你负责通过多轮迭代帮助用户优化论文质量，确保每次迭代都有实质性的改进。

## 能力边界
1. **质量评审**：从结构、逻辑、论证、语言、格式等多个维度全面评审论文
2. **问题识别**：准确识别论文中存在的各类问题，并评估其严重程度
3. **改进建议**：提供具体、可执行的改进建议，而非模糊的指导
4. **迭代优化**：通过多轮"评审-修改"循环逐步提升论文质量

## 行为准则
1. 评审必须客观公正，基于明确的学术标准而非个人偏好
2. 识别的问题要具体准确，标明位置和描述，便于修改
3. 建议要可执行，避免"建议加强论证"这类模糊表述
4. 每次修改都应带来实质提升，避免无意义的微调

## 约束限制
1. 不改变论文的核心论点和研究贡献
2. 不引入新的问题或错误
3. 保持学术规范和学科惯例
4. 控制每次修改的范围，避免大幅度重构

## 输出格式
**重要：只输出JSON格式结果，不要包含任何思考过程或额外说明。**
```json
{
    "quality_score": 0.0-1.0,
    "issues": [
        {"type": "问题类型", "location": "位置", "description": "描述", "severity": "high/medium/low"}
    ],
    "strengths": ["优点1", "优点2"],
    "suggestions": ["具体可执行的建议1", "具体可执行的建议2"]
}
```"""
        super().__init__(
            name="report_refiner",
            llm_config=llm_config,
            description="报告精炼（多轮迭代）",
            system_prompt=system_prompt
        )

    def _clean_text_output(self, text: str) -> str:
        """清理文本输出，移除思考块等无用部分，保留markdown格式"""
        if not text:
            return text
        import re
        # 移除思考块
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # 移除报告格式标记
        text = re.sub(r'^#{1,3}\s*第[^#]*轮[^#]*版本[^\n]*\n+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^#{1,3}\s*(?:原文|润色后|修改前后|对比|输出|结果)[^\n]*\n+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^#\s*[^#\n]*(?:[说明报告分析处理结果数据分析问题说明测试样例润色说明轮次]+)[^\n]*\n+', '', text, flags=re.IGNORECASE)
        # 移除 markdown 代码块标记
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = re.sub(r'```$', '', text)
        # 清理多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

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
        """评审论文初稿"""
        focus_str = ", ".join(focus_areas) if focus_areas else "结构、逻辑、语言、格式"
        prompt = f"""请评审以下论文（第{iteration}轮），重点关注：{focus_str}。

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
            cleaned = self._clean_text_output(response)
            if not cleaned or not cleaned.strip():
                logger.warning("Draft review returned empty response")
                return {
                    "quality_score": 0.5,
                    "issues": [],
                    "suggestions": ["评审服务暂时不可用"]
                }
            data = parse_json(cleaned)
            if data is None:
                logger.warning(f"Draft review JSON parse failed, raw_length={len(cleaned)}")
                return {
                    "quality_score": 0.5,
                    "issues": [],
                    "suggestions": ["评审服务暂时不可用"]
                }
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

        prompt = f"""根据评审意见修改论文（第{iteration}轮）。

**重要：输出要求**
- 只输出修改后的论文正文
- 不要输出任何 JSON、评审结果或解释
- 不要以 ```json 开头
- 直接输出论文内容

原始论文：
{draft}

评审问题：{json.dumps([f"{i.get('type', '')}: {i.get('description', '')}" for i in issues], ensure_ascii=False)}
建议：{json.dumps(suggestions, ensure_ascii=False)}

请输出修改后的论文正文：
"""
        try:
            response = await self._llm_call(prompt)
            cleaned = self._clean_text_output(response)

            # 如果返回的内容看起来像 JSON（以 { 开头），尝试提取真正的文本
            if cleaned.strip().startswith('{'):
                # 尝试解析 JSON 获取 polished_text 字段
                try:
                    parsed = json.loads(cleaned)
                    if 'polished_text' in parsed:
                        return parsed['polished_text']
                    if 'final_draft' in parsed:
                        return parsed['final_draft']
                except Exception:
                    pass
                # 如果解析失败或没有找到文本字段，返回原始draft
                self.logger.warning("Refinement returned JSON instead of text, using original draft")
                return draft

            return cleaned if cleaned and cleaned.strip() else draft
        except Exception as e:
            logger.error(f"Draft refinement failed: {e}")
            return draft

    async def _final_polish(self, draft: str) -> str:
        """最终润色"""
        prompt = f"""对论文进行最终润色。

**重要：输出要求**
- 只输出润色后的论文正文
- 不要输出任何 JSON、说明或解释
- 不要以 ```json 开头
- 直接输出论文内容

原文：
{draft}

请输出润色后的论文正文：
"""
        try:
            response = await self._llm_call(prompt)
            cleaned = self._clean_text_output(response)

            # 如果返回的内容看起来像 JSON（以 { 开头），尝试提取真正的文本
            if cleaned.strip().startswith('{'):
                try:
                    parsed = json.loads(cleaned)
                    if 'polished_text' in parsed:
                        return parsed['polished_text']
                    if 'final_draft' in parsed:
                        return parsed['final_draft']
                except Exception:
                    pass
                self.logger.warning("Final polish returned JSON instead of text, using original draft")
                return draft

            return cleaned if cleaned and cleaned.strip() else draft
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

    SYSTEM_PROMPT = """## 角色定义
你是一位专业的学术论文评审专家，以客观、公正、严格的评审风格著称。你负责评估论文质量、识别问题并提供具体可行的改进建议。

## 能力边界
1. **质量评估**：从多个维度全面评估论文质量水平
2. **问题识别**：准确识别论文中存在的各类问题
3. **优点识别**：发现论文的优点和亮点
4. **建议生成**：提供具体、可操作的改进建议

## 行为准则
1. 评审要客观公正，基于明确的学术标准
2. 问题识别要具体准确，标明位置和描述
3. 建议要可执行，避免模糊表述
4. 同时关注优点，平衡评审视角

## 约束限制
1. 不改变论文原意，不做过度批评
2. 不提出超出论文内容的评审要求
3. 评审意见要与论文实际内容相符

## 输出格式
**重要：只输出JSON格式结果，不要包含任何思考过程或额外说明。**
```json
{
    "quality_score": 0.0-1.0,
    "issues": [
        {"dimension": "评审维度", "description": "问题描述", "severity": "high/medium/low"}
    ],
    "strengths": ["优点1", "优点2"],
    "improvement_suggestions": ["具体可执行的建议1", "具体可执行的建议2"]
}
```"""

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        super().__init__(
            name="reviewer",
            llm_config=llm_config,
            description="论文质量评审",
            system_prompt=self.SYSTEM_PROMPT
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> WritingOutput:
        """
        执行单次评审

        Args:
            input_data: 包含 draft 的字典
            context: 执行上下文
        """
        draft = input_data.get("draft", "")
        focus_areas = input_data.get("focus_areas", [])

        if not draft:
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Empty draft"
            )

        try:
            focus_str = ", ".join(focus_areas) if focus_areas else "结构、逻辑、语言、格式"
            prompt = f"""请评审以下论文，重点关注：{focus_str}。

{draft[:2000]}{'...' if len(draft) > 2000 else ''}

评审维度：
1. 结构完整性
2. 逻辑连贯性
3. 论证充分性
4. 语言表达
5. 格式规范性

输出JSON格式：
{{"quality_score": 0-1, "issues": [{{"dimension": "维度", "description": "问题描述", "severity": "high/medium/low"}}], "strengths": ["优点"], "improvement_suggestions": ["建议"]}}
"""
            response = await self._llm_call(prompt)
            cleaned = self._clean_text_output(response)
            if not cleaned:
                logger.warning("Review returned empty response")
                return {"quality_score": 0.5, "issues": [], "improvement_suggestions": []}
            data = parse_json(cleaned)
            if data is None:
                logger.warning(f"Structure review JSON parse failed, raw_length={len(cleaned)}")
                return {"quality_score": 0.5, "issues": [], "improvement_suggestions": []}
            return data
        except Exception as e:
            logger.error(f"Review failed: {e}")
            return {"quality_score": 0.5, "issues": [], "improvement_suggestions": []}

    def _clean_text_output(self, text: str) -> str:
        """清理文本输出"""
        if not text:
            return text
        import re
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = re.sub(r'```$', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()