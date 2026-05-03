"""
TopicRefinerAgent - 选题精炼Agent

针对问题：选题困难、选题太大/太偏/缺乏创新性

职责：
- 分析用户初步想法
- 评估选题可行性
- 帮助缩小/优化选题
- 检查创新性
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

import json

from .base_problem_agent import ProblemAgentBase, AgentOutput, LLMConfig

logger = get_logging_logger(__name__)


def _clean_json_markdown(text: str) -> str:
    """清理JSON markdown格式（去除```json...```包裹），并提取纯JSON"""
    import re
    if not text:
        return ""

    # 移除思考块
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    # 去除 ```json ... ``` 包裹
    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE)
    # 去除 ``` ... ``` 包裹
    text = re.sub(r'^```\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE)
    text = text.strip()

    if not text:
        return ""

    # 如果不是以 { 开头，尝试找到第一个 { 的位置
    if not text.startswith('{'):
        match = re.search(r'\{', text)
        if match:
            text = text[match.start():]

    # 尝试只提取第一个完整的JSON对象（处理JSON后有多余内容的情况）
    if text.startswith('{'):
        try:
            # 尝试标准 json.loads
            json.loads(text)
            return text
        except json.JSONDecodeError:
            # 如果失败，尝试找到匹配的闭合括号
            start = text.index('{')
            depth = 0
            end_pos = -1

            for i, c in enumerate(text[start:], start):
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break

            if end_pos > 0:
                extracted = text[start:end_pos]
                try:
                    json.loads(extracted)
                    return extracted
                except json.JSONDecodeError:
                    pass

    return text


class TopicRefinerAgent(ProblemAgentBase):
    """
    TopicRefinerAgent - 选题精炼

    针对问题：
    - 选题太大或太偏
    - 缺乏创新性/跟风
    - 超出研究能力
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个学术研究选题专家，专注于帮助研究者优化和精炼研究主题。

## 1. 角色定义 (Role Definition)
你是一位经验丰富的学术研究顾问，擅长诊断选题问题并提供针对性改进建议。
你了解各学科的研究前沿，能够评估选题的创新性和可行性。

## 2. 能力边界 (Capabilities)
- 诊断选题问题（太大/太小/太偏/缺乏创新）
- 评估研究者能力匹配度（本科/硕士/博士/教授）
- 分析研究时间和资源限制
- 提供具体的改进建议和优化方向

## 3. 行为准则 (Guidelines)
处理选题分析时应该：
1. 从范围、创新性、可行性、价值四个维度诊断
2. 根据研究者水平调整建议的难度
3. 给出具体可执行的改进建议
4. 标注主要问题和次要问题

## 4. 约束限制 (Constraints)
- 选题必须在研究者能力范围内
- 创新性必须是真实的，而非改头换面
- 时间限制内必须能完成
- 有足够的文献支持

## 5. 输出格式 (Output Format)
严格按以下JSON格式输出：

{
    "diagnosis": {
        "scope": "too_broad | appropriate | too_narrow",
        "innovation": "high | medium | low",
        "feasibility": 0.0-1.0,
        "value": "high | medium | low"
    },
    "main_issues": ["问题1", "问题2"],
    "severity": {"问题1": 0.9, "问题2": 0.6},
    "recommendations": ["具体改进建议1", "具体改进建议2"],
    "suggested_topic": "优化后的选题（如果需要）",
    "reasoning": "分析推理过程（100-300字）"
}

## 质量评分标准
- 优秀 (≥0.8): 选题具体、创新性强、可行
- 良好 (≥0.6): 整体良好，部分可优化
- 一般 (≥0.4): 存在较大问题需改进
- 需改进 (<0.4): 选题方向有问题

## Few-Shot Examples

【示例1：选题太宽泛】
输入：我想研究机器学习
输出：
{
    "diagnosis": {"scope": "too_broad", "innovation": "low", "feasibility": 0.3, "value": "medium"},
    "main_issues": ["选题范围太广，无法聚焦", "缺乏具体研究问题"],
    "severity": {"范围过广": 0.9, "缺乏聚焦": 0.8},
    "recommendations": ["聚焦于具体任务（如图像分类）", "限定到特定方法（如Transformer）"],
    "suggested_topic": "基于Transformer的医学图像分类方法研究",
    "reasoning": "原始选题'机器学习'过于宽泛，建议聚焦到具体任务和方法。医学图像分类是一个有价值且有足够文献支持的子领域。"
}

【示例2：缺乏创新性】
输入：我想用CNN做图像分类，和ResNet差不多
输出：
{
    "diagnosis": {"scope": "appropriate", "innovation": "low", "feasibility": 0.6, "value": "medium"},
    "main_issues": ["与现有工作（ResNet）高度重复", "缺乏独特贡献点"],
    "severity": {"创新性不足": 0.9, "贡献点模糊": 0.7},
    "recommendations": ["考虑结合新的应用场景（如医学影像）", "引入新的损失函数或正则化方法", "与最新模型（如ViT）对比"],
    "suggested_topic": "轻量化CNN在移动端医学图像分类中的应用",
    "reasoning": "直接复现ResNet缺乏创新。建议在应用场景（新领域）和模型优化（轻量化）两个方向寻找突破口。"
}

【示例3：选题合理】
输入：我想研究联邦学习中的隐私保护梯度压缩方法，用于医学影像分析
输出：
{
    "diagnosis": {"scope": "appropriate", "innovation": "high", "feasibility": 0.75, "value": "high"},
    "main_issues": [],
    "severity": {},
    "recommendations": ["保持当前选题方向"],
    "suggested_topic": null,
    "reasoning": "选题聚焦于联邦学习+隐私保护+梯度压缩的交叉领域，创新性强且有明确的应用场景（医学影像）。研究范围适中，文献支持充分。"
}"""
        super().__init__(
            name="topic_refiner",
            target_problem="选题困难/缺乏创新性",
            llm_config=llm_config,
            description="选题精炼与创新性评估",
            system_prompt=system_prompt
        )

    async def diagnose(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        诊断选题问题

        输入：
        - user_idea: 用户的研究想法/初步主题
        - user_level: 用户研究水平（本科/硕士/博士）
        - available_time: 可用时间
        - available_resources: 可用资源
        """
        user_idea = input_data.get("user_idea", input_data.get("user_request", input_data.get("topic", "")))
        user_level = input_data.get("user_level", "硕士")
        available_time = input_data.get("available_time", "6个月")
        available_resources = input_data.get("available_resources", "一般")

        if not user_idea:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["研究主题为空"],
                recommendations=["请提供具体的研究兴趣或初步想法"],
                quality_score=0.0,
                error="Empty topic"
            )

        try:
            # 1. 分析选题问题
            issues = await self._analyze_topic_issues(user_idea, user_level)

            # 2. 评估可行性
            feasibility = await self._evaluate_feasibility(
                user_idea, user_level, available_time, available_resources
            )

            # 3. 评估创新性
            novelty = await self._evaluate_novelty(user_idea)

            # 4. 生成优化建议
            recommendations = await self._generate_recommendations(
                issues, feasibility, novelty
            )

            # 5. 生成优化后的选题
            refined_topic = await self._refine_topic(user_idea, recommendations)

            # 计算质量分数
            quality_score = self._calculate_quality_score(feasibility, novelty)

            return AgentOutput(
                success=True,
                result={
                    "original_topic": user_idea,
                    "refined_topic": refined_topic,
                    "feasibility": feasibility,
                    "novelty": novelty,
                    "scope_assessment": issues
                },
                agent_name=self.name,
                diagnosed_issues=issues,
                recommendations=recommendations,
                quality_score=quality_score
            )

        except Exception as e:
            cls_name = self.__class__.__name__
            self.logger.error(f"[{cls_name}:194] Topic refinement failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["选题分析失败"],
                recommendations=["请提供更详细的研究想法"],
                quality_score=0.0,
                error=str(e)
            )

    async def _analyze_topic_issues(self, topic: str, user_level: str) -> List[str]:
        """分析选题问题"""
        prompt = f"""
分析以下研究选题的问题：

选题：{topic}
研究者水平：{user_level}

请诊断以下常见问题：
1. 选题是否过于宽泛？
2. 选题是否过于狭窄？
3. 选题是否缺乏创新性？
4. 选题是否符合学术规范？
5. 选题是否适合研究者水平？

输出JSON格式：
{{
    "issues": ["问题1", "问题2", ...],
    "scope_assessment": {{
        "too_broad": true/false,
        "too_narrow": true/false,
        "main_issue": "主要问题描述"
    }}
}}
"""
        try:
            response = await self._llm_call(prompt)
            if not response or not response.strip():
                logger.error(f"[{self.__class__.__name__}:232] LLM返回空响应")
                return ["选题需要进一步明确"]
            # 清理markdown代码块
            content = _clean_json_markdown(response)
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed in _analyze_topic_issues: {e}, raw_input={content[:500] if content else 'empty'}")
                return ["选题需要进一步明确"]
            return data.get("issues", [])
        except ValueError as e:
            logger.error(f"[{self.__class__.__name__}:237] Topic analysis failed: {e}")
            return ["选题需要进一步明确"]
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}:239] Topic analysis failed: {e}")
            return ["选题需要进一步明确"]

    async def _evaluate_feasibility(
        self,
        topic: str,
        user_level: str,
        available_time: str,
        available_resources: str
    ) -> Dict[str, Any]:
        """评估可行性"""
        prompt = f"""
评估以下研究选题的可行性：

选题：{topic}
研究者水平：{user_level}
可用时间：{available_time}
可用资源：{available_resources}

请评估：
1. 时间可行性
2. 资源可行性
3. 能力匹配度
4. 总体可行性评分(1-10)

输出JSON格式：
{{
    "feasible": true/false,
    "time_feasibility": "评估",
    "resource_feasibility": "评估",
    "skill_match": "评估",
    "overall_score": 7.5,
    "concerns": ["担忧1", "担忧2"]
}}
"""
        cls_name = self.__class__.__name__
        try:
            response = await self._llm_call(prompt)
            if not response or not response.strip():
                logger.error(f"[{cls_name}:292] LLM返回空响应")
                return {"feasible": True, "overall_score": 5.0, "concerns": []}
            content = _clean_json_markdown(response)
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed in _evaluate_feasibility: {e}, raw_input={content[:500] if content else 'empty'}")
                return {"feasible": True, "overall_score": 5.0, "concerns": []}
            return data
        except ValueError as e:
            logger.error(f"[{cls_name}:298] Feasibility evaluation failed: {e}")
            return {"feasible": True, "overall_score": 5.0, "concerns": []}
        except Exception as e:
            logger.error(f"[{cls_name}:300] Feasibility evaluation failed: {e}")
            return {"feasible": True, "overall_score": 5.0, "concerns": []}

    async def _evaluate_novelty(self, topic: str) -> Dict[str, Any]:
        """评估创新性"""
        prompt = f"""
评估以下研究选题的创新性：

选题：{topic}

请分析：
1. 是否有新颖的研究角度？
2. 是否填补研究空白？
3. 是否有独特贡献？
4. 创新性评分(1-10)

输出JSON格式：
{{
    "novel": true/false,
    "novelty_aspects": ["创新点1", "创新点2"],
    "potential_gaps": ["gap1", "gap2"],
    "novelty_score": 6.5
}}
"""
        cls_name = self.__class__.__name__
        try:
            response = await self._llm_call(prompt)
            if not response or not response.strip():
                return {"novel": False, "novelty_score": 5.0}
            content = _clean_json_markdown(response)
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed in _evaluate_novelty: {e}, raw_input={content[:500] if content else 'empty'}")
                return {"novel": False, "novelty_score": 5.0}
            return data
        except ValueError as e:
            logger.error(f"[{cls_name}:338] Novelty evaluation failed: {e}")
            return {"novel": False, "novelty_score": 5.0}
        except Exception as e:
            logger.error(f"[{cls_name}:340] Novelty evaluation failed: {e}")
            return {"novel": False, "novelty_score": 5.0}

    async def _generate_recommendations(
        self,
        issues: List[str],
        feasibility: Dict[str, Any],
        novelty: Dict[str, Any]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于问题生成建议
        if any("宽泛" in issue or "too broad" in issue.lower() for issue in issues):
            recommendations.append("缩小研究范围，聚焦于具体问题")

        if any("狭窄" in issue or "too narrow" in issue.lower() for issue in issues):
            recommendations.append("拓宽研究角度，考虑相关领域")

        if not novelty.get("novel", True):
            recommendations.append("寻找独特的研究视角或方法创新")

        if not feasibility.get("feasible", True):
            for concern in feasibility.get("concerns", []):
                recommendations.append(f"解决可行性问题: {concern}")

        if not recommendations:
            recommendations.append("选题基本可行，可进一步细化")

        return recommendations[:5]  # 限制建议数量

    async def _refine_topic(self, original: str, recommendations: List[str]) -> str:
        """生成优化后的选题"""
        prompt = f"""
基于以下建议，优化研究选题：

原始选题：{original}
改进建议：{json.dumps(recommendations, ensure_ascii=False)}

请生成3个优化后的选题建议，每个都要：
1. 具体明确
2. 具有可执行性
3. 体现创新性

输出JSON格式：
{{
    "refined_topics": [
        {{"title": "优化选题1", "description": "描述"}},
        {{"title": "优化选题2", "description": "描述"}},
        {{"title": "优化选题3", "description": "描述"}}
    ],
    "best_choice": "最佳选题标题"
}}
"""
        cls_name = self.__class__.__name__
        try:
            response = await self._llm_call(prompt)
            if not response or not response.strip():
                return original
            content = _clean_json_markdown(response)
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed in _refine_topic: {e}, raw_input={content[:500] if content else 'empty'}")
                return original
            return data.get("best_choice", original)
        except ValueError as e:
            logger.error(f"[{cls_name}:409] Topic refinement failed (original={original}): {e}")
            return original
        except Exception as e:
            logger.error(f"[{cls_name}:411] Topic refinement failed (original={original}): {e}")
            return original

    def _calculate_quality_score(self, feasibility: Dict, novelty: Dict) -> float:
        """计算综合质量分数"""
        fea_score = feasibility.get("overall_score", 5.0) / 10.0
        nov_score = novelty.get("novelty_score", 5.0) / 10.0

        # 综合评分：可行性60%，创新性40%
        return round(fea_score * 0.6 + nov_score * 0.4, 2)
