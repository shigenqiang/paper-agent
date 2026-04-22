"""ReviewAgent - 质量评审Agent"""
import logging
from typing import List, Dict, Any, Optional
import json

from .base_agent import BaseAgent, AgentInput, AgentOutput, AgentCapability

logger = logging.getLogger(__name__)


class ReviewCriterion(BaseModel):
    """评审标准"""
    name: str
    description: str
    weight: float  # 权重 0-1
    score_range: tuple[float, float]  # 评分范围


class ReviewResult(BaseModel):
    """评审结果"""
    overall_score: float  # 综合评分 0-100
    passes_threshold: bool  # 是否通过阈值
    criterion_scores: Dict[str, float]  # 各维度评分
    suggestions: List[str]  # 改进建议
    strengths: List[str]  # 优点
    weaknesses: List[str]  # 不足


class ReviewAgent(BaseAgent):
    """
    评审Agent - 质量控制和评审

    功能:
    - 多维度质量评审
    - 自动评分和反馈
    - 改进建议生成
    - 质量趋势追踪
    """

    # 默认评审标准
    DEFAULT_CRITERIA = [
        ReviewCriterion(
            name="准确性",
            description="内容的准确性和事实正确性",
            weight=0.3,
            score_range=(0, 100)
        ),
        ReviewCriterion(
            name="完整性",
            description="内容的完整性和覆盖度",
            weight=0.25,
            score_range=(0, 100)
        ),
        ReviewCriterion(
            name="逻辑性",
            description="逻辑结构的清晰性和连贯性",
            weight=0.2,
            score_range=(0, 100)
        ),
        ReviewCriterion(
            name="可读性",
            description="语言表达的清晰性和可理解性",
            weight=0.15,
            score_range=(0, 100)
        ),
        ReviewCriterion(
            name="引用完整性",
            description="引用的完整性和规范性",
            weight=0.1,
            score_range=(0, 100)
        )
    ]

    def __init__(
        self,
        quality_threshold: float = 75.0,
        criteria: Optional[List[ReviewCriterion]] = None,
        llm_config=None
    ):
        """
        Args:
            quality_threshold: 质量阈值，低于此值需要改进
            criteria: 评审标准列表
            llm_config: LLM配置
        """
        self.quality_threshold = quality_threshold
        self.criteria = criteria or self.DEFAULT_CRITERIA
        self.review_history: List[Dict[str, Any]] = []

        super().__init__(
            name="ReviewAgent",
            llm_config=llm_config,
            description="质量评审Agent，负责多维度评审和改进建议",
            system_prompt="""你是ReviewAgent，一个专业的质量评审专家。

你的职责:
1. 从多个维度评估内容质量
2. 给出客观的评分和详细的反馈
3. 提供具体的改进建议
4. 识别内容的优点和不足

评审原则:
- 客观公正，基于事实
- 具体明确，避免空泛
- 建设性，帮助改进
- 一致性，保持评审标准统一

评分标准:
- 90-100分: 优秀
- 75-89分: 良好
- 60-74分: 及格
- 0-59分: 不及格
"""
        )

    def _get_capabilities(self) -> AgentCapability:
        return AgentCapability(
            task_types=["review", "quality_check", "validate", "audit"],
            description="质量评审、内容验证、改进建议"
        )

    async def execute(self, input_data: AgentInput) -> AgentOutput:
        """
        执行评审

        Args:
            input_data: 包含content（待评审内容）和requirements（需求）的输入

        Returns:
            评审结果
        """
        try:
            content = input_data.input_data.get("content", "")
            requirements = input_data.requirements
            agent_name = input_data.input_data.get("agent_name", "Unknown")

            logger.info(f"开始评审内容，来源Agent: {agent_name}")

            # 1. 多维度评分
            criterion_scores = {}
            for criterion in self.criteria:
                score, reasoning = await self._score_dimension(
                    content,
                    criterion,
                    requirements
                )
                criterion_scores[criterion.name] = {
                    "score": score,
                    "reasoning": reasoning
                }

            # 2. 计算综合评分
            overall_score = self._calculate_overall_score(criterion_scores)

            # 3. 生成评审结果
            review_result = await self._generate_review_result(
                criterion_scores,
                overall_score,
                content
            )

            # 4. 记录历史
            self._record_review(agent_name, review_result)

            # 5. 返回结果
            return AgentOutput(
                success=True,
                result=review_result.model_dump(),
                agent_name=self.name,
                reasoning=f"综合评分: {overall_score:.1f}/{100}, 通过阈值: {overall_score >= self.quality_threshold}",
                next_actions=self._get_next_actions(review_result)
            )

        except Exception as e:
            logger.error(f"评审失败: {e}")
            return AgentOutput(
                success=False,
                agent_name=self.name,
                error=str(e)
            )

    async def _score_dimension(
        self,
        content: str,
        criterion: ReviewCriterion,
        requirements: List[str]
    ) -> tuple[float, str]:
        """
        对单个维度进行评分

        使用LLM进行智能评分
        """
        prompt = f"""
请评审以下内容的{criterion.name}维度。

## 评审标准
{criterion.description}

## 评分范围
{criterion.score_range[0]}-{criterion.score_range[1]}分

## 用户需求
{json.dumps(requirements, ensure_ascii=False) if requirements else "无特殊需求"}

## 待评审内容
{content[:2000] if len(content) > 2000 else content}

请进行评审并给出评分（0-100），以JSON格式返回:
{{
  "score": 评分(0-100),
  "reasoning": "详细的评分理由，至少3点",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["不足1", "不足2"]
}}
"""

        try:
            response = await self._llm_call(prompt)
            result = json.loads(response)
            score = min(100, max(0, float(result.get("score", 50))))
            return score, result.get("reasoning", "未提供理由")
        except Exception as e:
            logger.error(f"维度评分失败: {e}")
            return 50.0, f"评分失败: {str(e)}"

    def _calculate_overall_score(self, criterion_scores: Dict[str, Dict]) -> float:
        """计算综合评分（加权平均）"""
        total_score = 0.0
        total_weight = 0.0

        for criterion in self.criteria:
            score_data = criterion_scores.get(criterion.name, {})
            score = score_data.get("score", 50.0)
            total_score += score * criterion.weight
            total_weight += criterion.weight

        return total_score / total_weight if total_weight > 0 else 0.0

    async def _generate_review_result(
        self,
        criterion_scores: Dict[str, Dict],
        overall_score: float,
        content: str
    ) -> ReviewResult:
        """生成完整的评审结果"""
        # 提取各维度评分
        scores_only = {
            name: data["score"]
            for name, data in criterion_scores.items()
        }

        # 生成建议和总结
        prompt = f"""
基于以下评审信息，生成一份完整的评审报告:

## 综合评分
{overall_score:.1f}/100

## 各维度评分
{json.dumps(scores_only, ensure_ascii=False, indent=2)}

## 详细评审
{json.dumps(criterion_scores, ensure_ascii=False, indent=2)}

请生成评审报告，以JSON格式返回:
{{
  "suggestions": ["具体改进建议1", "建议2"],
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["不足1", "不足2"],
  "summary": "总体评价"
}}
"""

        try:
            response = await self._llm_call(prompt)
            result = json.loads(response)
        except Exception as e:
            logger.error(f"生成评审报告失败: {e}")
            result = {
                "suggestions": [],
                "strengths": [],
                "weaknesses": [],
                "summary": "评审报告生成失败"
            }

        return ReviewResult(
            overall_score=overall_score,
            passes_threshold=overall_score >= self.quality_threshold,
            criterion_scores=scores_only,
            suggestions=result.get("suggestions", []),
            strengths=result.get("strengths", []),
            weaknesses=result.get("weaknesses", [])
        )

    def _get_next_actions(self, review_result: ReviewResult) -> List[str]:
        """根据评审结果生成后续操作建议"""
        actions = []

        if not review_result.passes_threshold:
            actions.append("根据评审建议改进内容")

        if any(score < 60 for score in review_result.criterion_scores.values()):
            actions.append("重点改进得分较低的维度")

        if review_result.suggestions:
            actions.append("实施改进建议")

        else:
            actions.append("内容已通过质量评审，可以继续下一步")

        return actions

    def _record_review(self, agent_name: str, review_result: ReviewResult):
        """记录评审历史"""
        self.review_history.append({
            "agent_name": agent_name,
            "timestamp": None,  # 可添加时间戳
            "score": review_result.overall_score,
            "passes": review_result.passes_threshold
        })

        # 保留最近100条记录
        if len(self.review_history) > 100:
            self.review_history = self.review_history[-100:]

    def get_quality_trend(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取质量趋势

        Args:
            agent_name: 指定Agent，None表示全部

        Returns:
            趋势数据
        """
        # 过滤记录
        if agent_name:
            filtered = [
                r for r in self.review_history
                if r["agent_name"] == agent_name
            ]
        else:
            filtered = self.review_history

        if not filtered:
            return {
                "average_score": 0,
                "pass_rate": 0,
                "trend": "stable",
                "count": 0
            }

        # 计算统计
        scores = [r["score"] for r in filtered]
        avg_score = sum(scores) / len(scores)
        pass_rate = sum(1 for r in filtered if r["passes"]) / len(filtered)

        # 判断趋势
        if len(filtered) >= 5:
            recent_avg = sum(scores[-5:]) / 5
            earlier_avg = sum(scores[:-5]) / len(scores[:-5]) if len(scores) > 5 else recent_avg
            if recent_avg > earlier_avg + 5:
                trend = "improving"
            elif recent_avg < earlier_avg - 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "average_score": round(avg_score, 2),
            "pass_rate": round(pass_rate * 100, 2),
            "trend": trend,
            "count": len(filtered)
        }

    def add_custom_criterion(self, criterion: ReviewCriterion):
        """添加自定义评审标准"""
        self.criteria.append(criterion)
        logger.info(f"添加自定义评审标准: {criterion.name}")

    def update_threshold(self, new_threshold: float):
        """更新质量阈值"""
        self.quality_threshold = max(0, min(100, new_threshold))
        logger.info(f"质量阈值更新为: {self.quality_threshold}")


from pydantic import BaseModel  # 确保导入
