"""
TopicAgent - 主题选择Agent

职责：
- 分析研究领域
- 生成候选主题
- 评估可行性
- 凝练具体研究问题
"""
from typing import Any, Dict, List, Optional
import json
import logging

from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig
from ..unified.error_handler import log_error_with_context

logger = logging.getLogger(__name__)


class TopicAgent(PaperAgentBase):
    """
    TopicAgent - 主题选择与范围缩小

    职责：
    - 分析研究领域
    - 生成候选主题
    - 评估可行性
    - 凝练具体研究问题
    """

    # Few-shot示例 - 帮助模型理解期望的输出格式和质量
    FEW_SHOT_EXAMPLES = """

## 输出格式示例

【示例1：主题选择】
输入：我想研究人工智能在教育领域的应用
输出：
{
    "title": "基于大语言模型的个性化自适应学习系统研究",
    "description": "利用LLM技术构建能够根据学生学习行为自动调整难度的智能辅导系统",
    "scope": "聚焦于K-12数学教育场景",
    "innovation": "将生成式AI与知识追踪结合，实现真正的个性化",
    "feasibility": 0.85,
    "literature_support": "深度学习、教育AI、知识追踪相关文献充足"
}

【示例2：聚焦具体问题】
输入：我想做机器学习方面的研究
输出：
{
    "title": "联邦学习中的隐私保护梯度压缩方法研究",
    "description": "在保证差分隐私前提下，通过梯度压缩减少通信开销",
    "scope": "聚焦于图像分类任务的联邦学习场景",
    "innovation": "提出一种新的压缩比自适应策略，平衡隐私和效率",
    "feasibility": 0.78,
    "literature_support": "联邦学习、差分隐私相关文献丰富"
}

【示例3：跨学科研究】
输入：我想研究AI和生物学的交叉方向
输出：
{
    "title": "基于深度学习的蛋白质结构预测优化方法",
    "description": "改进AlphaFold2的预测精度和推理速度",
    "scope": "聚焦于单域蛋白质的结构预测",
    "innovation": "提出轻量化网络结构，降低计算资源需求",
    "feasibility": 0.72,
    "literature_support": "AlphaFold相关文献较多，但应用优化方向较少"
}
"""

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个学术研究主题选择专家。
你的职责是：
1. 分析用户的研究需求
2. 生成多个候选研究主题
3. 评估各主题的可行性和创新性
4. 选择最佳主题并凝练具体研究问题

请确保选择的主题：
- 具有研究价值和创新性
- 在现有技术和资源下可行
- 有足够的文献支持
- 具有实际应用意义""" + self.FEW_SHOT_EXAMPLES
        super().__init__(
            name="topic_agent",
            llm_config=llm_config,
            description="主题选择与研究问题凝练",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        执行主题选择

        Args:
            input_data: 包含user_request的字典
            context: 执行上下文
        """
        user_request = input_data.get("user_request", "")

        if not user_request:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Empty user request"
            )

        try:
            # 1. 领域分析
            domain_analysis = await self._analyze_domain(user_request)

            # 2. 生成候选主题
            candidates = await self._generate_topic_candidates(domain_analysis, user_request)

            # 3. 评估可行性
            evaluated = await self._evaluate_feasibility(candidates)

            # 4. 选择最佳主题
            best_topic = await self._select_best_topic(evaluated)

            return AgentOutput(
                success=True,
                result={
                    "selected_topic": best_topic,
                    "alternative_topics": evaluated[1:3],
                    "domain_analysis": domain_analysis,
                    "all_candidates": evaluated
                },
                agent_name=self.name,
                reasoning=f"Selected topic: {best_topic.get('title', 'unknown')}",
                quality_score=best_topic.get("overall_score", 0.7)
            )

        except Exception as e:
            log_error_with_context(self.logger, e, "TopicAgent execution", recovered=True)
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _analyze_domain(self, user_request: str) -> Dict[str, Any]:
        """分析研究领域"""
        prompt = f"""
分析以下研究请求，确定相关的研究领域：

研究请求：{user_request}

请输出JSON格式的领域分析：
{{
    "main_domain": "主要学科领域",
    "sub_domains": ["子领域1", "子领域2"],
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "related_fields": ["相关领域1", "相关领域2"],
    "research_level": "本科/硕士/博士/博士后"
}}
"""
        try:
            response = await self._llm_call(prompt)
            return json.loads(response)
        except Exception as e:
            log_error_with_context(self.logger, e, "Domain analysis", recovered=True)
            return {
                "main_domain": "未知",
                "sub_domains": [],
                "keywords": user_request.split()[:5],
                "related_fields": [],
                "research_level": "硕士"
            }

    async def _generate_topic_candidates(
        self,
        domain_analysis: Dict[str, Any],
        user_request: str
    ) -> List[Dict[str, Any]]:
        """生成候选主题"""
        prompt = f"""
基于以下领域分析，生成5个候选研究主题：

领域分析：{json.dumps(domain_analysis, ensure_ascii=False)}
原始请求：{user_request}

要求：
1. 每个主题要有创新性
2. 要具体可执行
3. 要有研究价值
4. 要考虑可行性

输出JSON格式：
{{
    "candidates": [
        {{
            "title": "主题标题",
            "description": "主题描述",
            "scope": "研究范围",
            "potential_methods": ["方法1", "方法2"],
            "expected_contribution": "预期贡献"
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("candidates", [])
        except Exception as e:
            log_error_with_context(self.logger, e, "Candidate generation", recovered=True)
            return [{"title": user_request, "description": "Research topic", "scope": "中等"}]

    async def _evaluate_feasibility(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """评估可行性"""
        if not candidates:
            return []

        prompt = f"""
评估以下研究主题的可行性：

主题列表：{json.dumps(candidates, ensure_ascii=False)}

评估维度：
1. 文献充足性 (1-10)
2. 方法可行性 (1-10)
3. 创新性 (1-10)
4. 时间合理性 (1-10)
5. 资源可获取性 (1-10)

输出JSON格式：
{{
    "evaluated": [
        {{
            "original": {{"title": "...", "description": "..."}},
            "scores": {{
                "literature_adequacy": 8,
                "method_feasibility": 7,
                "novelty": 9,
                "time_reasonableness": 8,
                "resource_accessibility": 7
            }},
            "overall_score": 7.8,
            "risk_factors": ["风险1", "风险2"]
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            evaluated = data.get("evaluated", [])

            # 按overall_score排序
            evaluated = sorted(evaluated, key=lambda x: x.get("overall_score", 0), reverse=True)
            return evaluated

        except Exception as e:
            log_error_with_context(self.logger, e, "Feasibility evaluation", recovered=True)
            return [{"original": c, "scores": {}, "overall_score": 0.5} for c in candidates]

    async def _select_best_topic(self, evaluated: List[Dict[str, Any]]) -> Dict[str, Any]:
        """选择最佳主题"""
        if not evaluated:
            return {"title": "Default Topic", "description": "Default research topic"}

        best = evaluated[0]
        return {
            "title": best.get("original", {}).get("title", ""),
            "description": best.get("original", {}).get("description", ""),
            "scope": best.get("original", {}).get("scope", ""),
            "potential_methods": best.get("original", {}).get("potential_methods", []),
            "expected_contribution": best.get("original", {}).get("expected_contribution", ""),
            "scores": best.get("scores", {}),
            "overall_score": best.get("overall_score", 0.5),
            "risk_factors": best.get("risk_factors", [])
        }
