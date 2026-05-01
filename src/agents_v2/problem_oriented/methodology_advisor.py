"""
MethodologyAdvisorAgent - 方法指导Agent

针对问题：研究方法不当、数据处理不严谨

职责：
- 推荐适合的研究方法
- 检查方法论严谨性
- 辅助统计/数据分析
- 识别方法漏洞
"""
from typing import Any, Dict, List, Optional
import json
import logging

from .base_problem_agent import ProblemAgentBase, AgentOutput, LLMConfig

logger = logging.getLogger(__name__)


def _clean_json_markdown(text: str) -> str:
    """清理JSON markdown格式（去除```json...```包裹）"""
    import re
    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^```\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE)
    return text.strip()


class MethodologyAdvisorAgent(ProblemAgentBase):
    """
    MethodologyAdvisorAgent - 方法指导

    针对问题：
    - 方法选择不当
    - 数据处理不严谨
    - 统计知识不足
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个研究方法论专家。
你的职责是：
1. 推荐适合的研究方法
2. 检查方法严谨性
3. 识别潜在问题
4. 提供改进建议

请确保方法选择科学、严谨、适合研究问题。"""
        super().__init__(
            name="methodology_advisor",
            target_problem="研究方法不当/数据处理不严谨",
            llm_config=llm_config,
            description="研究方法论指导",
            system_prompt=system_prompt
        )

    async def diagnose(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        诊断方法论问题

        输入：
        - topic: 研究主题
        - proposed_method: 提议的研究方法
        - research_type: 研究类型（实证/理论/综述）
        """
        topic = input_data.get("topic", "")
        proposed_method = input_data.get("proposed_method", "")
        research_type = input_data.get("research_type", "实证研究")

        if not topic:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["研究主题为空"],
                recommendations=["请提供研究主题"],
                quality_score=0.0,
                error="Empty topic"
            )

        try:
            # 1. 推荐适合的方法
            recommended_methods = await self._recommend_methods(topic, research_type)

            # 2. 评估提议方法
            method_evaluation = await self._evaluate_method(topic, proposed_method, research_type)

            # 3. 检查严谨性
            rigor_issues = await self._check_rigor(method_evaluation)

            # 4. 识别潜在问题
            potential_problems = await self._identify_problems(topic, method_evaluation)

            # 5. 生成建议
            recommendations = await self._generate_recommendations(
                method_evaluation, rigor_issues, potential_problems
            )

            # 计算质量分数
            rigor_score = 1.0 - (len(rigor_issues) / 10)
            quality_score = round(rigor_score * 0.7 + method_evaluation.get("suitability", 0.5) * 0.3, 2)

            return AgentOutput(
                success=True,
                result={
                    "topic": topic,
                    "research_type": research_type,
                    "proposed_method": proposed_method,
                    "recommended_methods": recommended_methods,
                    "method_evaluation": method_evaluation,
                    "rigor_issues": rigor_issues,
                    "potential_problems": potential_problems
                },
                agent_name=self.name,
                diagnosed_issues=rigor_issues + potential_problems,
                recommendations=recommendations,
                quality_score=quality_score
            )

        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:116] Methodology advisory failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["方法论诊断失败"],
                recommendations=["请详细描述研究方法"],
                quality_score=0.0,
                error=str(e)
            )

    async def _recommend_methods(self, topic: str, research_type: str) -> List[Dict[str, str]]:
        """推荐适合的研究方法"""
        prompt = f"""
为以下研究推荐适合的研究方法：

研究主题：{topic}
研究类型：{research_type}

请推荐3-5种适合的方法，说明每种方法的：
1. 适用场景
2. 优缺点
3. 数据要求

输出JSON格式：
{{
    "methods": [
        {{
            "name": "方法名称",
            "applicability": "适用场景",
            "pros": "优点",
            "cons": "缺点",
            "data_requirements": "数据要求"
        }}
    ]
}}
"""
        cls_name = self.__class__.__name__
        try:
            response = await self._llm_call(prompt)
            if not response or not response.strip():
                self.logger.error(f"[{cls_name}:154] LLM返回空响应")
                return []
            content = _clean_json_markdown(response)
            data = json.loads(content)
            return data.get("methods", [])
        except json.JSONDecodeError as e:
            self.logger.error(f"[{cls_name}:158] Method recommendation failed (JSON解析错误): {e}")
            return []
        except ValueError as e:
            self.logger.error(f"[{cls_name}:160] Method recommendation failed: {e}")
            return []
        except Exception as e:
            self.logger.error(f"[{cls_name}:162] Method recommendation failed: {e}")
            return []

    async def _evaluate_method(
        self,
        topic: str,
        proposed_method: str,
        research_type: str
    ) -> Dict[str, Any]:
        """评估提议方法"""
        prompt = f"""
评估以下研究方法是否适合：

研究主题：{topic}
研究类型：{research_type}
提议方法：{proposed_method}

请评估：
1. 方法-问题匹配度 (1-10)
2. 方法可行性 (1-10)
3. 方法创新性 (1-10)
4. 主要优缺点
5. 潜在风险

输出JSON格式：
{{
    "suitability": 7.5,
    "feasibility": 8.0,
    "novelty": 6.0,
    "pros": ["优点1", "优点2"],
    "cons": ["缺点1", "缺点2"],
    "risks": ["风险1", "风险2"],
    "suitable": true/false
}}
"""
        cls_name = self.__class__.__name__
        try:
            response = await self._llm_call(prompt)
            if not response or not response.strip():
                self.logger.error(f"[{cls_name}:215] LLM返回空响应")
                return {"suitability": 5.0, "suitable": False}
            content = _clean_json_markdown(response)
            data = json.loads(content)
            return data
        except json.JSONDecodeError as e:
            self.logger.error(f"[{cls_name}:219] Method evaluation failed (JSON解析错误): {e}")
            return {"suitability": 5.0, "suitable": False}
        except ValueError as e:
            self.logger.error(f"[{cls_name}:221] Method evaluation failed: {e}")
            return {"suitability": 5.0, "suitable": False}
        except Exception as e:
            self.logger.error(f"[{cls_name}:223] Method evaluation failed: {e}")
            return {"suitability": 5.0, "suitable": False}

    async def _check_rigor(self, method_evaluation: Dict) -> List[str]:
        """检查方法严谨性"""
        issues = []

        if not method_evaluation.get("suitable", False):
            issues.append("方法与研究问题匹配度不高")

        suitability = method_evaluation.get("suitability", 5)
        if suitability < 6:
            issues.append(f"方法适合度偏低: {suitability}/10")

        feasibility = method_evaluation.get("feasibility", 5)
        if feasibility < 6:
            issues.append(f"方法可行性存疑: {feasibility}/10")

        risks = method_evaluation.get("risks", [])
        for risk in risks:
            issues.append(f"潜在风险: {risk}")

        return issues

    async def _identify_problems(self, topic: str, method_evaluation: Dict) -> List[str]:
        """识别潜在方法论问题"""
        prompt = f"""
识别以下研究可能存在的方法论问题：

研究主题：{topic}
方法评估：{json.dumps(method_evaluation, ensure_ascii=False)}

请识别常见问题：
1. 样本量问题
2. 选择偏差
3. 因果推断问题
4. 内部/外部效度问题
5. 统计方法问题

输出JSON格式：
{{
    "problems": [
        {{
            "type": "问题类型",
            "description": "问题描述",
            "severity": "high/medium/low",
            "suggestion": "建议"
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            problems = data.get("problems", [])
            return [p.get("description", "") for p in problems]
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:255] Problem identification failed: {e}")
            return []

    async def _generate_recommendations(
        self,
        method_evaluation: Dict,
        rigor_issues: List[str],
        potential_problems: List[str]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于问题生成建议
        for issue in rigor_issues:
            if "匹配度" in issue:
                recommendations.append("考虑使用更匹配的研究方法")
            if "可行性" in issue:
                recommendations.append("评估是否具备方法所需的资源和能力")

        for problem in potential_problems:
            if "样本量" in problem:
                recommendations.append("确保足够的样本量以保证统计功效")
            if "偏差" in problem:
                recommendations.append("使用随机化或对照设计减少偏差")
            if "因果" in problem:
                recommendations.append("明确区分相关性与因果性")

        if not recommendations:
            recommendations.append("研究方法基本合理，可继续推进")

        return recommendations[:5]
