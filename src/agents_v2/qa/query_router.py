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

问题类型定义：
1. BASIC_QUERY（基础查询）：简单的事实性问题，可以直接回答
   - 例如：什么是贝叶斯定理？正态分布的定义是什么？
   - 处理方式：直接回答，不需要搜索论文

2. PROFESSIONAL（专业问题）：需要深入解释的方法论或理论问题
   - 例如：分层模型的MCMC估计方法有哪些？
   - 处理方式：搜索论文后给出专业回答

3. FRONTIER（前沿探索）：关于最新研究进展的问题
   - 例如：2024年统计学习有什么新突破？
   - 处理方式：搜索arXiv最新论文

4. APPLICATION（应用咨询）：关于在实际场景中应用的问题
   - 例如：如何在医学研究中应用倾向性评分？
   - 处理方式：搜索PubMed案例

输出格式（JSON）：
{
    "question_type": "professional",
    "confidence": 0.85,
    "reasoning": "这是一个关于统计方法的问题，需要搜索论文获得更详细的专业解释",
    "suggested_path": "paper_search",
    "filters": {
        "domain": "statistics",
        "sort_by": "relevance"
    }
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