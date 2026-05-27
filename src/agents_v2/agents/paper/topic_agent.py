"""
TopicAgent - 主题选择Agent

职责：
- 分析研究领域
- 生成候选主题
- 评估可行性
- 凝练具体研究问题
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

import json
import re
from pydantic import BaseModel, Field, ValidationError, field_validator

from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig
from src.agents_v2.workflow.unified.error_handler import log_error_with_context

logger = get_logging_logger(__name__)


# ==================== Pydantic Models ====================

class DomainAnalysis(BaseModel):
    """领域分析结果模型"""
    main_domain: str = Field(default="未知", description="主要学科领域")
    sub_domains: List[str] = Field(default_factory=list, description="子领域")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    related_fields: List[str] = Field(default_factory=list, description="相关领域")
    research_level: str = Field(default="硕士", description="研究水平")


class TopicCandidate(BaseModel):
    """主题候选模型"""
    title: str = Field(default="", description="主题标题")
    description: str = Field(default="", description="主题描述")
    scope: str = Field(default="", description="研究范围")
    innovation: str = Field(default="", description="主要创新点")
    feasibility: float = Field(default=0.7, description="可行性评分")
    literature_support: str = Field(default="", description="文献支持情况")
    key_references: List[str] = Field(default_factory=list, description="关键参考文献")
    potential_methods: List[str] = Field(default_factory=list, description="可能使用的方法")
    expected_contribution: str = Field(default="", description="预期贡献")

    @field_validator('feasibility', mode='before')
    @classmethod
    def clamp_feasibility(cls, v):
        """修正超出范围的feasibility值（LLM可能输出7而非0.7）"""
        if isinstance(v, (int, float)):
            if v > 1:
                # 假设LLM输出的是10分制分数，转换为小数
                if v > 10:
                    v = 1.0  # 超出范围则设为默认值
                else:
                    v = v / 10.0
            return v
        return 0.7


class TopicScores(BaseModel):
    """主题评分模型"""
    literature_adequacy: float = Field(default=5.0, ge=1, le=10, description="文献充足性")
    method_feasibility: float = Field(default=5.0, ge=1, le=10, description="方法可行性")
    novelty: float = Field(default=5.0, ge=1, le=10, description="创新性")
    time_reasonableness: float = Field(default=5.0, ge=1, le=10, description="时间合理性")
    resource_accessibility: float = Field(default=5.0, ge=1, le=10, description="资源可获取性")


class EvaluatedTopic(BaseModel):
    """评估后的主题模型"""
    original: TopicCandidate = Field(default_factory=TopicCandidate, description="原始主题")
    scores: TopicScores = Field(default_factory=TopicScores, description="评分")
    overall_score: float = Field(default=5.0, ge=0, le=10, description="综合评分")
    risk_factors: List[str] = Field(default_factory=list, description="风险因素")


class CandidatesResponse(BaseModel):
    """候选主题响应模型"""
    candidates: List[TopicCandidate] = Field(default_factory=list)


class EvaluatedResponse(BaseModel):
    """评估响应模型"""
    evaluated: List[EvaluatedTopic] = Field(default_factory=list)


def _clean_json_markdown(text: str) -> str:
    """清理JSON markdown格式，移除思考块"""
    if not text:
        return ""

    # 移除思考块
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^```\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE)
    text = text.strip()

    if not text:
        return ""

    if not text.startswith('{') and not text.startswith('['):
        match = re.search(r'[\[{]', text)
        if match:
            text = text[match.start():]

    if text.startswith('{') or text.startswith('['):
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            first_char = text[0] if text else None
            start_char = '{' if first_char == '{' else '[' if first_char == '[' else None
            if not start_char:
                return text

            opening_mark = start_char
            closing_mark = '}' if start_char == '{' else ']'

            start = 0
            depth = 0
            end_pos = -1
            for i, c in enumerate(text):
                if c == opening_mark:
                    depth += 1
                elif c == closing_mark:
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break
            if end_pos > 0:
                extracted = text[:end_pos]
                try:
                    json.loads(extracted)
                    return extracted
                except json.JSONDecodeError:
                    pass

    return text


def parse_with_pydantic(text: str, model_class: type[BaseModel], default_value: Any = None) -> Any:
    """使用 Pydantic 模型解析 JSON 文本

    Args:
        text: LLM 返回的文本
        model_class: Pydantic 模型类
        default_value: 解析失败时的默认值

    Returns:
        解析后的 Pydantic 模型实例或默认值
    """
    try:
        cleaned = _clean_json_markdown(text)
        data = json.loads(cleaned)
        return model_class.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"Pydantic parse failed: {e}, raw_input={text[:500] if text else 'empty'}, trying regex extraction")
        # 尝试正则提取
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return model_class.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e2:
                logger.warning(f"Regex extraction also failed: {e2}, raw_input={text[:500] if text else 'empty'}")
                return default_value
        return default_value


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
        system_prompt = """你是一个学术研究主题选择专家，专注于帮助研究者找到有价值且可行的研究主题。

## 1. 角色定义 (Role Definition)
你是一位资深学术研究顾问，擅长从广泛的研究兴趣中提炼出具体、可行的研究主题。
你了解各学科的研究前沿和发展趋势，能够评估主题的创新性和可行性。

## 2. 能力边界 (Capabilities)
- 分析用户的研究兴趣和背景
- 生成3-5个候选研究主题
- 评估每个主题的可行性（0.0-1.0）
- 评估创新性和文献支持程度
- 凝练具体的研究问题

## 3. 行为准则 (Guidelines)
生成主题时应该：
1. 从用户的研究兴趣出发
2. 确保主题具体、可执行
3. 平衡创新性和可行性
4. 考虑时间和资源限制

## 4. 约束限制 (Constraints)
- 每个主题必须有明确的研究问题
- 创新性不能依赖简单的模型替换
- 必须有足够的文献支持
- 主题范围适合用户的研究水平

## 5. 输出格式 (Output Format)
严格按以下JSON格式输出：

{
    "title": "具体的研究主题标题",
    "description": "研究内容的详细描述（100-200字）",
    "scope": "研究范围的精确定义",
    "innovation": "主要创新点描述",
    "feasibility": 0.0-1.0,
    "literature_support": "文献支持情况评估",
    "key_references": ["关键参考文献（可选）"],
    "potential_methods": ["可能使用的研究方法"],
    "expected_contribution": "预期贡献"
}

## 质量评分标准
- 优秀 (≥0.8): 主题具体、创新性强、可行、文献支持充分
- 良好 (≥0.6): 整体良好，部分可优化
- 一般 (≥0.4): 存在较大问题需改进
- 需改进 (<0.4): 主题方向有问题

## Few-Shot Examples

【示例1：主题选择】
输入：我想研究人工智能在教育领域的应用
输出：
{
    "title": "基于大语言模型的个性化自适应学习系统研究",
    "description": "利用LLM技术构建能够根据学生学习行为自动调整难度的智能辅导系统，通过知识追踪和生成式AI的结合，实现真正的个性化学习体验。",
    "scope": "聚焦于K-12数学教育场景，主要研究自适应难度调整算法和个性化内容生成",
    "innovation": "将生成式AI与知识追踪结合，创新性地实现实时难度调整和个性化内容生成",
    "feasibility": 0.85,
    "literature_support": "深度学习、教育AI、知识追踪相关文献充足，LLM在教育领域的应用是当前热点",
    "potential_methods": ["大语言模型微调", "知识追踪模型", "强化学习"],
    "expected_contribution": "提供一个可部署的个性化学习系统，发表高质量学术论文"
}

【示例2：聚焦具体问题】
输入：我想做机器学习方面的研究
输出：
{
    "title": "联邦学习中的隐私保护梯度压缩方法研究",
    "description": "在保证差分隐私前提下，通过自适应梯度压缩减少通信开销，同时保持模型精度。",
    "scope": "聚焦于图像分类任务的联邦学习场景，重点研究通信效率与模型精度的平衡",
    "innovation": "提出一种新的压缩比自适应策略，根据本地梯度分布动态调整压缩比",
    "feasibility": 0.78,
    "literature_support": "联邦学习、差分隐私相关文献丰富，是当前研究热点",
    "potential_methods": ["梯度压缩", "差分隐私", "联邦优化算法"],
    "expected_contribution": "提出新的梯度压缩方法，在保证隐私的情况下显著降低通信成本"
}

【示例3：跨学科研究】
输入：我想研究AI和生物学的交叉方向
输出：
{
    "title": "基于深度学习的蛋白质结构预测优化方法",
    "description": "改进AlphaFold2的预测精度和推理速度，提出轻量化网络结构降低计算资源需求。",
    "scope": "聚焦于单域蛋白质的结构预测，重点优化推理效率",
    "innovation": "提出轻量化网络结构，在保持预测精度的同时大幅降低计算资源需求",
    "feasibility": 0.72,
    "literature_support": "AlphaFold相关文献较多，但应用优化方向较少，创新空间大",
    "potential_methods": ["深度学习模型压缩", "知识蒸馏", "网络结构搜索"],
    "expected_contribution": "提供一个高效轻量的蛋白质结构预测工具"
}"""
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
        prompt = f"""分析以下研究请求，确定相关的研究领域。严格按照JSON格式输出，不要包含任何其他文字。

研究请求：{user_request}

示例输出：
{{
    "main_domain": "计算机科学",
    "sub_domains": ["人工智能", "机器学习"],
    "keywords": ["深度学习", "神经网络", "优化算法"],
    "related_fields": ["统计学", "数学"],
    "research_level": "硕士"
}}

严格按照上述JSON格式输出，JSON外不要有任何内容："""
        try:
            response = await self._llm_call(prompt)
            result = parse_with_pydantic(response, DomainAnalysis, DomainAnalysis())
            return result.model_dump()
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
        prompt = f"""基于以下领域分析，生成5个候选研究主题。严格按照JSON格式输出，不要包含任何其他文字。

领域分析：{json.dumps(domain_analysis, ensure_ascii=False)}
原始请求：{user_request}

要求：
1. 每个主题要有创新性
2. 要具体可执行
3. 要有研究价值
4. 要考虑可行性

示例输出格式：
{{
    "candidates": [
        {{
            "title": "基于深度学习的图像超分辨率重建方法",
            "description": "研究利用深度卷积神经网络提升图像分辨率的技术",
            "scope": "聚焦于自然图像的2倍超分辨率",
            "innovation": "提出一种新的特征融合策略，提升重建质量",
            "feasibility": 0.8,
            "literature_support": "深度学习超分辨率相关文献充足",
            "potential_methods": ["卷积神经网络", "生成对抗网络"],
            "expected_contribution": "提出一种新的特征融合策略"
        }}
    ]
}}

严格按照上述JSON格式输出，JSON外不要有任何内容："""
        try:
            response = await self._llm_call(prompt)
            result = parse_with_pydantic(response, CandidatesResponse, CandidatesResponse())
            return [c.model_dump() for c in result.candidates]
        except Exception as e:
            log_error_with_context(self.logger, e, "Candidate generation", recovered=True)
            return [{"title": user_request, "description": "Research topic", "scope": "中等"}]

    async def _evaluate_feasibility(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """评估可行性"""
        if not candidates:
            return []

        prompt = f"""评估以下研究主题的可行性。严格按照JSON格式输出，不要包含任何其他文字。

主题列表：{json.dumps(candidates, ensure_ascii=False)}

**重要：仔细阅读各字段的评分要求**
评估维度（每个维度1-10分，整数）：
1. literature_adequacy - 文献充足性（1-10分）
2. method_feasibility - 方法可行性（1-10分）
3. novelty - 创新性（1-10分）
4. time_reasonableness - 时间合理性（1-10分）
5. resource_accessibility - 资源可获取性（1-10分）

**feasibility字段说明（重要！）**
- feasibility：必须是0到1之间的小数（如0.8），不是10分制！
- 10分制分数只用于上述5个评估维度
- overall_score：综合评分，使用10分制

示例输出格式：
{{
    "evaluated": [
        {{
            "original": {{"title": "示例主题", "description": "主题描述", "scope": "研究范围", "innovation": "创新点", "feasibility": 0.8, "literature_support": "文献支持"}},
            "scores": {{
                "literature_adequacy": 8,
                "method_feasibility": 7,
                "novelty": 9,
                "time_reasonableness": 8,
                "resource_accessibility": 7
            }},
            "overall_score": 7.8,
            "risk_factors": ["需要大量计算资源"]
        }}
    ]
}}

严格按照上述JSON格式输出，JSON外不要有任何内容："""
        try:
            response = await self._llm_call(prompt)
            result = parse_with_pydantic(response, EvaluatedResponse, EvaluatedResponse())

            evaluated = []
            for item in result.evaluated:
                evaluated.append({
                    "original": item.original.model_dump(),
                    "scores": item.scores.model_dump(),
                    "overall_score": item.overall_score,
                    "risk_factors": item.risk_factors
                })

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
        original = best.get("original", {})
        return {
            "title": original.get("title", ""),
            "description": original.get("description", ""),
            "scope": original.get("scope", ""),
            "innovation": original.get("innovation", ""),
            "feasibility": original.get("feasibility", 0.7),
            "literature_support": original.get("literature_support", ""),
            "potential_methods": original.get("potential_methods", []),
            "expected_contribution": original.get("expected_contribution", ""),
            "scores": best.get("scores", {}),
            "overall_score": best.get("overall_score", 0.5),
            "risk_factors": best.get("risk_factors", [])
        }
