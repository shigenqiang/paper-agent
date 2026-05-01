"""问题路由Agent - 判断问题类型并决定处理策略"""
from typing import Dict, Any, Optional
import json
import logging

from .base_qa_agent import BaseQAAgent, QuestionType, RoutingDecision

logger = logging.getLogger(__name__)


class QueryRouter(BaseQAAgent):
    """
    问题路由决策Agent

    职责：
    1. 解析问题类型（基础/专业/前沿/应用）
    2. 评估复杂度（简单/中等/复杂）
    3. 决定处理路径（直接回答/搜索论文/LLM增强）

    路由规则：
    | 问题类型 | 特征 | 处理方式 |
    |----------|------|----------|
    | 基础查询 | 定义、公式、概念 | 直接从知识库回答 |
    | 专业问题 | 方法论、理论证明 | 搜索论文后回答 |
    | 前沿探索 | 最新技术、发展趋势 | 搜索arXiv最新论文 |
    | 应用咨询 | 实际数据分析 | 搜索PubMed案例 |
    """

    ROUTING_RULES = {
        QuestionType.BASIC_QUERY: {
            "path": "knowledge_base",
            "priority": 1,
            "keywords": ["什么是", "定义", "概念", "公式", "原理", "哪个是", "区别"]
        },
        QuestionType.PROFESSIONAL: {
            "path": "paper_search",
            "priority": 2,
            "keywords": ["方法", "理论", "证明", "推导", "为什么", "如何", "模型"]
        },
        QuestionType.FRONTIER: {
            "path": "arxiv_search",
            "priority": 3,
            "keywords": ["最新", "前沿", "趋势", "2024", "2025", "2026", "新方法", "突破"]
        },
        QuestionType.APPLICATION: {
            "path": "pubmed_search",
            "priority": 2,
            "keywords": ["应用", "临床", "医学", "生物", "数据", "案例", "实验", "研究"]
        }
    }

    def __init__(self):
        super().__init__(
            name="QueryRouter",
            description="问题路由Agent - 判断问题类型并决定处理策略"
        )
        self.system_prompt = """你是一个专业的问题分类专家，擅长判断用户问题的类型并决定最佳处理策略。

## 1. 角色定义 (Role Definition)
你是一个学术领域问题分类专家，专注于判断用户问题的类型并推荐最佳处理路径。
你有丰富的学术研究背景，熟悉各类问题特征和处理模式。

## 2. 能力边界 (Capabilities)
- 能够准确识别问题类型（基础查询/专业问题/前沿探索/应用咨询）
- 能够评估问题复杂度（简单/中等/复杂）
- 能够推荐最合适的处理路径（知识库/论文搜索/LLM增强）
- 能够识别多语言混合问题（中英文）

## 3. 行为准则 (Guidelines)
处理问题时应该：
1. 仔细分析问题的关键词和语义
2. 根据问题类型选择最合适的处理路径
3. 给出置信度评分（0.0-1.0）
4. 提供清晰的推理过程说明

## 4. 约束限制 (Constraints)
- 不确定时选择置信度较高的路径
- 不推荐无法处理的复杂查询
- 基础查询不搜索论文，直接回答
- 前沿探索只搜索最近2年内论文

## 5. 输出格式 (Output Format)
严格按以下JSON格式输出，字段类型必须匹配：

{
    "question_type": "BASIC_QUERY | PROFESSIONAL | FRONTIER | APPLICATION",
    "confidence": 0.0-1.0,
    "reasoning": "判断理由（50-200字）",
    "suggested_path": "knowledge_base | paper_search | arxiv_search | pubmed_search | llm_enhance",
    "filters": {
        "domain": "学科领域（可选）",
        "time_range": "时间范围天数（可选）",
        "sort_by": "relevance | citations | date（可选）"
    }
}

## 问题类型详细定义

| 类型 | 特征关键词 | 典型示例 | 处理方式 |
|------|-----------|----------|----------|
| BASIC_QUERY | 什么是、定义、概念、公式、原理 | 什么是贝叶斯定理？ | 直接回答 |
| PROFESSIONAL | 方法、理论、证明、推导、模型 | MCMC估计方法有哪些？ | 搜索论文 |
| FRONTIER | 最新、前沿、趋势、2024/2025/2026 | 统计学习新突破？ | 搜索arXiv |
| APPLICATION | 应用、临床、医学、数据、案例 | 医学研究中的应用？ | 搜索PubMed |

## Few-Shot Examples

【示例1：专业问题】
输入：分层模型的MCMC估计方法有哪些？
输出：
{
    "question_type": "PROFESSIONAL",
    "confidence": 0.92,
    "reasoning": "该问题涉及统计方法论的专业知识，需要深入解释。关键词'方法'和'MCMC'表明这是专业问题类型。",
    "suggested_path": "paper_search",
    "filters": {"domain": "statistics", "sort_by": "relevance"}
}

【示例2：前沿探索】
输入：2024年大语言模型有什么新突破？
输出：
{
    "question_type": "FRONTIER",
    "confidence": 0.95,
    "reasoning": "问题明确询问2024年最新进展，属于前沿探索类型。'突破'关键词表明需要最新论文。",
    "suggested_path": "arxiv_search",
    "filters": {"time_range": 365, "sort_by": "date"}
}

【示例3：应用咨询】
输入：如何在医学研究中应用倾向性评分？
输出：
{
    "question_type": "APPLICATION",
    "confidence": 0.88,
    "reasoning": "问题涉及医学领域的实际应用，关键词'医学研究'和'应用'表明是应用咨询类型。",
    "suggested_path": "pubmed_search",
    "filters": {"domain": "medicine", "time_range": 730, "sort_by": "relevance"}
}
"""

    async def execute(self, question: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行问题路由

        Args:
            question: 用户问题
            context: 上下文（可选）

        Returns:
            包含路由决策的字典
        """
        self.logger.info(f"路由问题: {question[:50]}...")

        try:
            # 使用LLM进行路由决策
            decision = await self._decide_with_llm(question)

            self.logger.info(f"路由决策: {decision.question_type.value} -> {decision.suggested_path}")

            return {
                "question": question,
                "question_type": decision.question_type,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning,
                "suggested_path": decision.suggested_path,
                "filters": decision.filters
            }

        except Exception as e:
            self.logger.error(f"路由失败: {e}")
            # 降级：默认专业问题
            return {
                "question": question,
                "question_type": QuestionType.PROFESSIONAL,
                "confidence": 0.5,
                "reasoning": f"路由失败，默认按专业问题处理: {str(e)}",
                "suggested_path": "paper_search",
                "filters": {}
            }

    async def _decide_with_llm(self, question: str) -> RoutingDecision:
        """使用LLM进行路由决策"""
        prompt = f"""请分析以下问题，判断其类型并给出处理建议：

问题：{question}

请输出JSON格式的分类结果。"""

        response = await self._llm_call(prompt, self.system_prompt)
        return self.parse_routing_decision(response)

    def decide_with_rules(self, question: str) -> RoutingDecision:
        """
        基于规则的快速路由（不调用LLM）

        适用于简单场景或作为LLM决策的补充验证
        """
        question_lower = question.lower()

        # 检查关键词
        for qtype, rule in self.ROUTING_RULES.items():
            for keyword in rule["keywords"]:
                if keyword in question_lower:
                    return RoutingDecision(
                        question_type=qtype,
                        confidence=0.7,
                        reasoning=f"基于关键词'{keyword}'匹配",
                        suggested_path=rule["path"],
                        filters={"keyword": keyword}
                    )

        # 默认：专业问题
        return RoutingDecision(
            question_type=QuestionType.PROFESSIONAL,
            confidence=0.5,
            reasoning="无关键词匹配，默认按专业问题处理",
            suggested_path="paper_search",
            filters={}
        )

    def batch_decide(self, questions: list[str]) -> list[Dict[str, Any]]:
        """批量路由（同步方法，用于批处理场景）"""
        results = []
        for q in questions:
            # 使用规则快速判断
            decision = self.decide_with_rules(q)
            results.append({
                "question": q,
                "question_type": decision.question_type,
                "confidence": decision.confidence,
                "suggested_path": decision.suggested_path
            })
        return results