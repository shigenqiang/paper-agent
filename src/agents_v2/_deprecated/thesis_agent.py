"""
ThesisAgent - 研究问题凝练Agent

职责：
- 分析文献综述
- 凝练研究动机
- 明确研究目标
- 定义研究范围
- 形成Thesis Statement
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger
from pydantic import BaseModel, Field

import json

from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig
from ..unified.pydantic_validator import parse_with_pydantic, parse_json

logger = get_logging_logger(__name__)


# Pydantic Models for Thesis
class ResearchAnalysis(BaseModel):
    """研究分析"""
    summary: str = Field(default="", description="研究总结")
    key_themes: List[str] = Field(default_factory=list, description="关键主题")
    main_methods: List[str] = Field(default_factory=list, description="主要方法")
    main_gaps: List[str] = Field(default_factory=list, description="研究空白")
    trends: List[str] = Field(default_factory=list, description="发展趋势")


class ResearchMotivation(BaseModel):
    """研究动机"""
    primary_motivation: str = Field(default="", description="主要动机")
    secondary_motivation: str = Field(default="", description="次要动机")
    academic_significance: str = Field(default="", description="学术意义")
    practical_significance: str = Field(default="", description="实践意义")
    justification: str = Field(default="", description="必要性论证")


class ResearchObjective(BaseModel):
    """研究目标"""
    id: int = Field(default=0, ge=1)
    description: str = Field(default="", description="目标描述")
    measurability: str = Field(default="", description="如何测量")
    alignment: str = Field(default="", description="对应的研究空白")


class ObjectivesResponse(BaseModel):
    """目标响应"""
    objectives: List[ResearchObjective] = Field(default_factory=list)


class ScopeResponse(BaseModel):
    """研究范围响应"""
    scope: Dict[str, Any] = Field(default_factory=dict)


class HypothesesResponse(BaseModel):
    """研究假设响应"""
    hypotheses: List[str] = Field(default_factory=list)


class ThesisAgent(PaperAgentBase):
    """
    ThesisAgent - 研究问题凝练

    职责：
    - 分析文献综述
    - 凝练研究动机
    - 明确研究目标
    - 定义研究范围
    - 形成Thesis Statement
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个学术研究策划专家。
你的职责是：
1. 分析现有文献和研究空白
2. 凝练研究动机和意义
3. 明确具体研究目标
4. 定义研究范围和假设
5. 形成清晰的研究陈述(Thesis Statement)

请确保：
- 研究目标具体可测量
- 研究范围清晰明确
- 研究陈述有说服力"""
        super().__init__(
            name="thesis_agent",
            llm_config=llm_config,
            description="研究问题凝练与Thesis Statement形成",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        执行研究凝练

        Args:
            input_data: 包含topic的字典
            context: 执行上下文（包含文献分析结果）
        """
        topic = input_data.get("topic", "")

        # 从context获取文献分析结果
        literature_result = {}
        if context:
            literature_result = context.get("literature_result", {})

        paper_analyses = literature_result.get("paper_analyses", [])
        existing_gaps = literature_result.get("research_gaps", [])
        papers = literature_result.get("papers", [])

        if not topic:
            topic = input_data.get("task_description", "")

        if not topic:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Empty topic"
            )

        try:
            # 1. 分析现有研究
            analysis = await self._analyze_existing_research(topic, paper_analyses)

            # 2. 凝练研究动机
            motivation = await self._refine_motivation(topic, analysis, existing_gaps)

            # 3. 明确研究目标
            objectives = await self._define_objectives(motivation, existing_gaps)

            # 4. 定义研究范围
            scope = await self._define_scope(objectives)

            # 5. 形成Thesis Statement
            thesis = await self._formulate_thesis(topic, motivation, objectives, scope)

            return AgentOutput(
                success=True,
                result={
                    "thesis_statement": thesis,
                    "research_motivation": motivation,
                    "research_objectives": objectives,
                    "scope": scope,
                    "existing_analysis": analysis,
                    "hypotheses": await self._formulate_hypotheses(objectives, scope)
                },
                agent_name=self.name,
                reasoning="Thesis formulated based on literature analysis",
                quality_score=0.8
            )

        except Exception as e:
            self.logger.error(f"ThesisAgent execution failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _analyze_existing_research(
        self,
        topic: str,
        paper_analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析现有研究"""
        if not paper_analyses:
            return {"summary": "No papers analyzed", "key_themes": [], "main_gaps": []}

        prompt = f"""
分析以下论文，总结现有研究的整体情况：

主题：{topic}
论文分析：{json.dumps(paper_analyses[:15], ensure_ascii=False)}

请输出JSON格式的分析结果：
{{
    "summary": "现有研究总结",
    "key_themes": ["主题1", "主题2"],
    "main_methods": ["方法1", "方法2"],
    "main_gaps": ["gap1", "gap2"],
    "trends": ["趋势1", "趋势2"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            result = parse_with_pydantic(response, ResearchAnalysis, ResearchAnalysis())
            return result.model_dump()
        except Exception as e:
            self.logger.error(f"Research analysis failed: {e}")
            return {"summary": "Analysis failed", "key_themes": [], "main_gaps": []}

    async def _refine_motivation(
        self,
        topic: str,
        analysis: Dict[str, Any],
        existing_gaps: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """凝练研究动机"""
        prompt = f"""
基于以下分析，凝练研究动机：

主题：{topic}
现有研究分析：{json.dumps(analysis, ensure_ascii=False)}
研究空白：{json.dumps(existing_gaps, ensure_ascii=False)}

请输出JSON格式的研究动机：
{{
    "primary_motivation": "主要动机（为什么做这个研究）",
    "secondary_motivation": "次要动机",
    "academic_significance": "学术意义",
    "practical_significance": "实践意义",
    "justification": "研究必要性论证"
}}
"""
        try:
            response = await self._llm_call(prompt)
            result = parse_with_pydantic(response, ResearchMotivation, ResearchMotivation())
            return result.model_dump()
        except Exception as e:
            self.logger.error(f"Motivation refinement failed: {e}")
            return {"primary_motivation": "Research needed", "academic_significance": "Unknown"}

    async def _define_objectives(
        self,
        motivation: Dict[str, str],
        existing_gaps: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """定义研究目标"""
        prompt = f"""
基于以下研究动机，定义具体可测量的研究目标：

动机：{json.dumps(motivation, ensure_ascii=False)}
研究空白：{json.dumps(existing_gaps, ensure_ascii=False)}

请定义3-5个具体的研究目标，输出JSON格式：
{{
    "objectives": [
        {{
            "id": 1,
            "description": "目标描述",
            "measurability": "如何测量",
            "alignment": "对应的研究空白"
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            result = parse_with_pydantic(response, ObjectivesResponse, ObjectivesResponse())
            return [obj.model_dump() for obj in result.objectives]
        except Exception as e:
            self.logger.error(f"Objective definition failed: {e}")
            return [{"id": 1, "description": "Research objective", "measurability": "TBD"}]

    async def _define_scope(self, objectives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """定义研究范围"""
        prompt = f"""
基于以下研究目标，定义研究范围：

目标：{json.dumps(objectives, ensure_ascii=False)}

请输出JSON格式的研究范围：
{{
    "scope": {{
        "content_scope": "内容范围",
        "method_scope": "方法范围",
        "data_scope": "数据范围",
        "limitations": ["限制1", "限制2"],
        "assumptions": ["假设1", "假设2"]
    }}
}}
"""
        try:
            response = await self._llm_call(prompt)
            result = parse_with_pydantic(response, ScopeResponse, ScopeResponse())
            return result.scope
        except Exception as e:
            self.logger.error(f"Scope definition failed: {e}")
            return {"content_scope": "To be determined"}

    async def _formulate_hypotheses(
        self,
        objectives: List[Dict[str, Any]],
        scope: Dict[str, Any]
    ) -> List[str]:
        """形成研究假设"""
        prompt = f"""
基于以下研究目标和范围，形成研究假设：

目标：{json.dumps(objectives, ensure_ascii=False)}
范围：{json.dumps(scope, ensure_ascii=False)}

请形成2-4个可验证的研究假设，输出JSON格式：
{{
    "hypotheses": [
        "假设1的描述",
        "假设2的描述"
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            result = parse_with_pydantic(response, HypothesesResponse, HypothesesResponse())
            return result.hypotheses
        except Exception as e:
            self.logger.error(f"Hypothesis formulation failed: {e}")
            return ["Hypothesis to be defined"]

    async def _formulate_thesis(
        self,
        topic: str,
        motivation: Dict[str, str],
        objectives: List[Dict[str, Any]],
        scope: Dict[str, Any]
    ) -> str:
        """形成Thesis Statement"""
        prompt = f"""
基于以下信息，形成一个清晰、有说服力的Thesis Statement：

主题：{topic}
研究动机：{json.dumps(motivation, ensure_ascii=False)}
研究目标：{json.dumps(objectives, ensure_ascii=False)}
研究范围：{json.dumps(scope, ensure_ascii=False)}

Thesis Statement应该：
1. 明确陈述研究观点
2. 体现研究创新性
3. 可在论文中得到验证

请直接输出Thesis Statement（1-2句话）：
"""
        try:
            response = await self._llm_call(prompt)
            return response.strip()
        except Exception as e:
            self.logger.error(f"Thesis formulation failed: {e}")
            return f"This research aims to investigate {topic} through systematic analysis."
