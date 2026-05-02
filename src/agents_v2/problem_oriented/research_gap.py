"""
ResearchGapAnalyzer - 研究空白分析器

系统化识别学术论文研究空白的模块
基于业界研究空白识别方法论

功能：
- 多维度研究空白识别
- 研究机会评分
- 空白可信度评估
- 研究建议生成
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from src.agents_v2.logging_config import get_logging_logger

import json

logger = get_logging_logger(__name__)


class GapType(Enum):
    """研究空白类型"""
    METHODOLOGICAL = "methodological"  # 方法论空白
    EMPIRICAL = "empirical"           # 实证空白
    THEORETICAL = "theoretical"       # 理论空白
    APPLICATION = "application"       # 应用空白
    POPULATION = "population"         # 研究对象空白
    CONTEXTUAL = "contextual"         # 情境空白
    TEMPORAL = "temporal"             # 时间维度空白
    COMPARATIVE = "comparative"       # 对比研究空白


class OpportunityScore(Enum):
    """研究机会评分"""
    HIGH = "high"      # 高机会
    MEDIUM = "medium"  # 中等机会
    LOW = "low"        # 低机会


@dataclass
class ResearchGap:
    """研究空白"""
    gap_type: GapType
    description: str
    evidence: List[str]          # 支持证据（论文引用）
    potential_direction: str     # 潜在研究方向
    opportunity_score: OpportunityScore
    feasibility: float           # 可行性 0-10
    novelty: float               # 创新性 0-10
    impact_potential: float       # 影响力潜力 0-10
    required_resources: List[str]  # 所需资源
    related_methods: List[str]     # 相关方法
    risk_factors: List[str]         # 风险因素


@dataclass
class GapAnalysisResult:
    """空白分析结果"""
    topic: str
    total_papers_analyzed: int
    gaps_identified: List[ResearchGap]
    gap_categories: Dict[str, int]  # 各类别空白数量
    most_promising_gap: Optional[ResearchGap]
    research_recommendations: List[str]
    confidence_level: float  # 分析置信度 0-1


class ResearchGapAnalyzer:
    """
    研究空白分析器

    基于论文分析，系统化识别研究空白
    """

    def __init__(self, llm_config: Optional[Any] = None):
        self.llm_config = llm_config
        self.logger = logger

    async def analyze(
        self,
        topic: str,
        paper_analyses: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> GapAnalysisResult:
        """
        执行研究空白分析

        Args:
            topic: 研究主题
            paper_analyses: 论文分析列表，每篇论文应包含：
                - title: 论文标题
                - core_problem: 核心研究问题
                - key_methodology: 主要方法
                - key_findings: 主要发现
                - limitations: 局限性
                - datasets: 使用的数据集
            context: 额外上下文

        Returns:
            GapAnalysisResult: 分析结果
        """
        if not paper_analyses:
            return GapAnalysisResult(
                topic=topic,
                total_papers_analyzed=0,
                gaps_identified=[],
                gap_categories={},
                most_promising_gap=None,
                research_recommendations=["需要更多论文进行分析"],
                confidence_level=0.0
            )

        try:
            # 1. 分析现有研究的方法论
            methodological_gaps = await self._identify_methodological_gaps(topic, paper_analyses)

            # 2. 识别实证空白
            empirical_gaps = await self._identify_empirical_gaps(topic, paper_analyses)

            # 3. 识别理论空白
            theoretical_gaps = await self._identify_theoretical_gaps(topic, paper_analyses)

            # 4. 识别应用空白
            application_gaps = await self._identify_application_gaps(topic, paper_analyses)

            # 5. 识别比较研究空白
            comparative_gaps = await self._identify_comparative_gaps(topic, paper_analyses)

            # 6. 合并并评估所有空白
            all_gaps = (
                methodological_gaps +
                empirical_gaps +
                theoretical_gaps +
                application_gaps +
                comparative_gaps
            )

            # 7. 评分和排序
            scored_gaps = await self._score_and_rank_gaps(topic, all_gaps, paper_analyses)

            # 8. 生成建议
            recommendations = await self._generate_recommendations(topic, scored_gaps)

            # 9. 计算置信度
            confidence = self._calculate_confidence(len(paper_analyses), len(scored_gaps))

            # 10. 分类统计
            categories = self._categorize_gaps(scored_gaps)

            # 找到最有希望的空白
            most_promising = scored_gaps[0] if scored_gaps else None

            return GapAnalysisResult(
                topic=topic,
                total_papers_analyzed=len(paper_analyses),
                gaps_identified=scored_gaps,
                gap_categories=categories,
                most_promising_gap=most_promising,
                research_recommendations=recommendations,
                confidence_level=confidence
            )

        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:165] Gap analysis failed: {e}")
            return GapAnalysisResult(
                topic=topic,
                total_papers_analyzed=len(paper_analyses),
                gaps_identified=[],
                gap_categories={},
                most_promising_gap=None,
                research_recommendations=["分析过程出错，请重试"],
                confidence_level=0.0
            )

    async def _identify_methodological_gaps(
        self,
        topic: str,
        papers: List[Dict[str, Any]]
    ) -> List[ResearchGap]:
        """识别方法论空白"""
        prompt = f"""
分析以下论文的方法论，识别方法论研究空白：

主题：{topic}

论文分析：{json.dumps([
    {
        "title": p.get("title", ""),
        "methodology": p.get("key_methodology", ""),
        "limitations": p.get("limitations", [])
    }
    for p in papers[:15]
], ensure_ascii=False)}

请识别方法论层面的研究空白，如：
1. 某方法未应用于该领域
2. 方法的组合/混合使用未被探索
3. 方法的可扩展性问题未解决
4. 方法的鲁棒性/泛化能力未验证

输出JSON格式：
{{
    "gaps": [
        {{
            "description": "空白描述",
            "evidence": ["证据1", "证据2"],
            "potential_direction": "潜在研究方向",
            "required_resources": ["资源1", "资源2"],
            "related_methods": ["相关方法1", "相关方法2"]
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            gaps = []
            for g in data.get("gaps", []):
                gaps.append(ResearchGap(
                    gap_type=GapType.METHODOLOGICAL,
                    description=g.get("description", ""),
                    evidence=g.get("evidence", []),
                    potential_direction=g.get("potential_direction", ""),
                    opportunity_score=OpportunityScore.MEDIUM,
                    feasibility=5.0,
                    novelty=5.0,
                    impact_potential=5.0,
                    required_resources=g.get("required_resources", []),
                    related_methods=g.get("related_methods", []),
                    risk_factors=[]
                ))
            return gaps
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:235] Methodological gap identification failed: {e}")
            return []

    async def _identify_empirical_gaps(
        self,
        topic: str,
        papers: List[Dict[str, Any]]
    ) -> List[ResearchGap]:
        """识别实证空白"""
        # 分析已有研究使用的数据集
        existing_datasets = set()
        for p in papers:
            for ds in p.get("datasets", []):
                existing_datasets.add(ds)

        prompt = f"""
分析以下论文的实证研究，识别实证空白：

主题：{topic}

已有数据集：{list(existing_datasets)}

论文分析：{json.dumps([
    {
        "title": p.get("title", ""),
        "datasets": p.get("datasets", []),
        "limitations": p.get("limitations", []),
        "key_findings": p.get("key_findings", [])
    }
    for p in papers[:15]
], ensure_ascii=False)}

请识别实证研究空白，如：
1. 某数据集未被用于该研究
2. 缺乏大规模/小规模实验验证
3. 缺乏真实世界场景验证
4. 缺乏跨数据集泛化研究

输出JSON格式：
{{
    "gaps": [
        {{
            "description": "空白描述",
            "evidence": ["证据1", "证据2"],
            "potential_direction": "潜在研究方向",
            "required_resources": ["资源1", "资源2"],
            "related_methods": ["相关方法1", "相关方法2"]
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            gaps = []
            for g in data.get("gaps", []):
                gaps.append(ResearchGap(
                    gap_type=GapType.EMPIRICAL,
                    description=g.get("description", ""),
                    evidence=g.get("evidence", []),
                    potential_direction=g.get("potential_direction", ""),
                    opportunity_score=OpportunityScore.MEDIUM,
                    feasibility=6.0,
                    novelty=5.0,
                    impact_potential=5.0,
                    required_resources=g.get("required_resources", []),
                    related_methods=g.get("related_methods", []),
                    risk_factors=[]
                ))
            return gaps
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:306] Empirical gap identification failed: {e}")
            return []

    async def _identify_theoretical_gaps(
        self,
        topic: str,
        papers: List[Dict[str, Any]]
    ) -> List[ResearchGap]:
        """识别理论空白"""
        prompt = f"""
分析以下论文的理论基础，识别理论空白：

主题：{topic}

论文分析：{json.dumps([
    {
        "title": p.get("title", ""),
        "core_problem": p.get("core_problem", ""),
        "key_findings": p.get("key_findings", []),
        "limitations": p.get("limitations", [])
    }
    for p in papers[:15]
], ensure_ascii=False)}

请识别理论层面的空白，如：
1. 缺乏理论解释框架
2. 理论与实证结果不匹配
3. 缺乏跨理论整合
4. 假设未经验证

输出JSON格式：
{{
    "gaps": [
        {{
            "description": "空白描述",
            "evidence": ["证据1", "证据2"],
            "potential_direction": "潜在研究方向",
            "required_resources": ["资源1", "资源2"],
            "related_methods": ["相关方法1", "相关方法2"]
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            gaps = []
            for g in data.get("gaps", []):
                gaps.append(ResearchGap(
                    gap_type=GapType.THEORETICAL,
                    description=g.get("description", ""),
                    evidence=g.get("evidence", []),
                    potential_direction=g.get("potential_direction", ""),
                    opportunity_score=OpportunityScore.MEDIUM,
                    feasibility=4.0,  # 理论工作通常较难
                    novelty=7.0,       # 理论创新性高
                    impact_potential=7.0,
                    required_resources=g.get("required_resources", []),
                    related_methods=g.get("related_methods", []),
                    risk_factors=[]
                ))
            return gaps
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:369] Theoretical gap identification failed: {e}")
            return []

    async def _identify_application_gaps(
        self,
        topic: str,
        papers: List[Dict[str, Any]]
    ) -> List[ResearchGap]:
        """识别应用空白"""
        prompt = f"""
分析以下论文的应用场景，识别应用空白：

主题：{topic}

论文分析：{json.dumps([
    {
        "title": p.get("title", ""),
        "key_findings": p.get("key_findings", []),
        "limitations": p.get("limitations", [])
    }
    for p in papers[:15]
], ensure_ascii=False)}

请识别应用层面的空白，如：
1. 方法未应用于特定领域
2. 跨领域应用未被探索
3. 实际部署场景验证缺失
4. 用户研究/人体研究缺失

输出JSON格式：
{{
    "gaps": [
        {{
            "description": "空白描述",
            "evidence": ["证据1", "证据2"],
            "potential_direction": "潜在研究方向",
            "required_resources": ["资源1", "资源2"],
            "related_methods": ["相关方法1", "相关方法2"]
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            gaps = []
            for g in data.get("gaps", []):
                gaps.append(ResearchGap(
                    gap_type=GapType.APPLICATION,
                    description=g.get("description", ""),
                    evidence=g.get("evidence", []),
                    potential_direction=g.get("potential_direction", ""),
                    opportunity_score=OpportunityScore.HIGH,  # 应用通常可行性高
                    feasibility=7.0,
                    novelty=5.0,
                    impact_potential=6.0,
                    required_resources=g.get("required_resources", []),
                    related_methods=g.get("related_methods", []),
                    risk_factors=[]
                ))
            return gaps
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:431] Application gap identification failed: {e}")
            return []

    async def _identify_comparative_gaps(
        self,
        topic: str,
        papers: List[Dict[str, Any]]
    ) -> List[ResearchGap]:
        """识别对比研究空白"""
        prompt = f"""
分析以下论文的对比研究，识别对比空白：

主题：{topic}

论文分析：{json.dumps([
    {
        "title": p.get("title", ""),
        "methodology": p.get("key_methodology", ""),
        "key_findings": p.get("key_findings", [])
    }
    for p in papers[:15]
], ensure_ascii=False)}

请识别对比研究空白，如：
1. 缺乏方法间系统对比
2. 缺乏跨设置/跨场景对比
3. 缺乏消融实验
4. 缺乏不同数据规模对比

输出JSON格式：
{{
    "gaps": [
        {{
            "description": "空白描述",
            "evidence": ["证据1", "证据2"],
            "potential_direction": "潜在研究方向",
            "required_resources": ["资源1", "资源2"],
            "related_methods": ["相关方法1", "相关方法2"]
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            gaps = []
            for g in data.get("gaps", []):
                gaps.append(ResearchGap(
                    gap_type=GapType.COMPARATIVE,
                    description=g.get("description", ""),
                    evidence=g.get("evidence", []),
                    potential_direction=g.get("potential_direction", ""),
                    opportunity_score=OpportunityScore.MEDIUM,
                    feasibility=6.0,
                    novelty=5.0,
                    impact_potential=5.0,
                    required_resources=g.get("required_resources", []),
                    related_methods=g.get("related_methods", []),
                    risk_factors=[]
                ))
            return gaps
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:493] Comparative gap identification failed: {e}")
            return []

    async def _score_and_rank_gaps(
        self,
        topic: str,
        gaps: List[ResearchGap],
        papers: List[Dict[str, Any]]
    ) -> List[ResearchGap]:
        """对研究空白进行评分和排序"""
        if not gaps:
            return []

        prompt = f"""
评估以下研究空白的机会和可行性：

主题：{topic}
空白数量：{len(gaps)}

空白列表：{json.dumps([
    {
        "index": i,
        "type": g.gap_type.value,
        "description": g.description,
        "evidence": g.evidence,
        "potential_direction": g.potential_direction
    }
    for i, g in enumerate(gaps)
], ensure_ascii=False)}

请对每个空白评分（0-10）：
1. feasibility: 研究可行性
2. novelty: 创新性
3. impact_potential: 潜在影响力

同时给出：
- opportunity_score: high/medium/low
- risk_factors: 风险因素

输出JSON格式：
{{
    "scores": [
        {{
            "index": 0,
            "feasibility": 7.0,
            "novelty": 8.0,
            "impact_potential": 7.0,
            "opportunity_score": "high",
            "risk_factors": ["风险1", "风险2"]
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            scores_map = {s["index"]: s for s in data.get("scores", [])}

            # 更新gaps的评分
            scored_gaps = []
            for i, gap in enumerate(gaps):
                if i in scores_map:
                    score_data = scores_map[i]
                    gap.feasibility = score_data.get("feasibility", 5.0)
                    gap.novelty = score_data.get("novelty", 5.0)
                    gap.impact_potential = score_data.get("impact_potential", 5.0)

                    opp = score_data.get("opportunity_score", "medium")
                    if opp == "high":
                        gap.opportunity_score = OpportunityScore.HIGH
                    elif opp == "low":
                        gap.opportunity_score = OpportunityScore.LOW
                    else:
                        gap.opportunity_score = OpportunityScore.MEDIUM

                    gap.risk_factors = score_data.get("risk_factors", [])

                scored_gaps.append(gap)

            # 按综合评分排序
            scored_gaps.sort(
                key=lambda g: (
                    g.opportunity_score.value,
                    g.feasibility * 0.3 + g.novelty * 0.4 + g.impact_potential * 0.3
                ),
                reverse=True
            )

            return scored_gaps

        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:584] Gap scoring failed: {e}")
            return gaps

    async def _generate_recommendations(
        self,
        topic: str,
        gaps: List[ResearchGap]
    ) -> List[str]:
        """生成研究建议"""
        if not gaps:
            return ["建议扩大文献搜索范围"]

        top_gaps = gaps[:3]

        prompt = f"""
基于以下最有希望的研究空白，为研究者生成具体建议：

主题：{topic}

研究空白：
{json.dumps([
    {
        "type": g.gap_type.value,
        "description": g.description,
        "potential_direction": g.potential_direction,
        "opportunity": g.opportunity_score.value,
        "feasibility": g.feasibility,
        "novelty": g.novelty,
        "impact": g.impact_potential
    }
    for g in top_gaps
], ensure_ascii=False)}

请生成5条具体可执行的研究建议，每条建议应包含：
1. 具体的研究问题
2. 建议的研究方法
3. 预期贡献

输出JSON格式：
{{
    "recommendations": [
        {{
            "research_question": "具体研究问题",
            "suggested_method": "建议方法",
            "expected_contribution": "预期贡献"
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            recs = data.get("recommendations", [])
            return [
                f"问题: {r['research_question']} | 方法: {r['suggested_method']} | 贡献: {r['expected_contribution']}"
                for r in recs
            ]
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:642] Recommendation generation failed: {e}")
            return [f"建议探索: {g.potential_direction}" for g in gaps[:3]]

    def _calculate_confidence(
        self,
        num_papers: int,
        num_gaps: int
    ) -> float:
        """计算分析置信度"""
        # 基于论文数量的置信度
        paper_confidence = min(1.0, num_papers / 20)

        # 基于识别出的空白数量（太多或太少都不好）
        if num_gaps == 0:
            gap_confidence = 0.0
        elif num_gaps <= 3:
            gap_confidence = 0.7
        elif num_gaps <= 8:
            gap_confidence = 1.0
        else:
            gap_confidence = max(0.5, 1.0 - (num_gaps - 8) * 0.05)

        return (paper_confidence * 0.6 + gap_confidence * 0.4)

    def _categorize_gaps(self, gaps: List[ResearchGap]) -> Dict[str, int]:
        """统计各类别空白数量"""
        categories = {}
        for gap in gaps:
            cat_name = gap.gap_type.value
            categories[cat_name] = categories.get(cat_name, 0) + 1
        return categories

    async def _llm_call(self, prompt: str) -> str:
        """调用LLM"""
        try:
            # 使用全局LLM配置
            from ..core.config import get_llm_config
            config = get_llm_config()

            # 创建简单的LLM调用
            from src.agents_v2.core.base_agent import PaperAgentBase, AgentOutput, LLMConfig

            class TempAgent(PaperAgentBase):
                pass

            llm_cfg = self.llm_config if self.llm_config else LLMConfig(
                model=config.get("model", "gpt-4"),
                api_key=config.get("api_key", ""),
                api_base=config.get("api_base", "")
            )

            agent = TempAgent(name="research_gap_temp", llm_config=llm_cfg)
            response = await agent._llm_call(prompt)
            return response
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:697] LLM call failed: {e}")
            raise


def analyze_research_gaps(
    topic: str,
    paper_analyses: List[Dict[str, Any]],
    llm_config: Optional[Any] = None
) -> GapAnalysisResult:
    """
    便捷函数：分析研究空白

    Args:
        topic: 研究主题
        paper_analyses: 论文分析列表
        llm_config: LLM配置

    Returns:
        GapAnalysisResult
    """
    analyzer = ResearchGapAnalyzer(llm_config)
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(analyzer.analyze(topic, paper_analyses))