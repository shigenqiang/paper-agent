"""
OutlineGeneratorAgent - 大纲生成Agent

职责：
- 根据题目和研究目标生成完整论文大纲
- 设计章节结构
- 规划内容分配
- 确保逻辑连贯性
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

import json

from .base_writing_agent import WritingAgentBase, WritingOutput, LLMConfig

logger = get_logging_logger(__name__)


class OutlineGeneratorAgent(WritingAgentBase):
    """
    OutlineGeneratorAgent - 论文大纲生成

    职责：
    - 根据主题生成完整大纲
    - 设计章节层级结构
    - 规划每个章节的内容要点
    - 确保逻辑连贯性
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个专业的学术论文大纲设计专家。
你的职责是：
1. 根据研究主题生成完整论文大纲
2. 设计清晰的章节结构
3. 规划每个章节的核心内容
4. 确保论文逻辑连贯性

请确保：
- 大纲结构符合学术规范
- 章节安排逻辑清晰
- 各部分内容分配合理
- 与研究问题紧密相关"""
        super().__init__(
            name="outline_generator",
            llm_config=llm_config,
            description="论文大纲生成",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> WritingOutput:
        """
        生成论文大纲

        Args:
            input_data: 包含以下字段的字典：
                - topic: 研究主题
                - thesis_statement: 研究论点 (可选)
                - literature_review: 文献综述结果 (可选)
                - target_venue: 目标期刊/会议 (可选)
                - academic_level: 学术水平 (本科/硕士/博士)
            context: 执行上下文
        """
        topic = input_data.get("topic", "")
        thesis_statement = input_data.get("thesis_statement", "")
        literature_review = input_data.get("literature_review", {})
        target_venue = input_data.get("target_venue", "")
        academic_level = input_data.get("academic_level", "硕士")

        if not topic:
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Empty topic"
            )

        try:
            # 1. 分析研究主题和要求
            analysis = await self._analyze_requirements(
                topic, thesis_statement, target_venue, academic_level
            )

            # 2. 生成大纲结构
            outline = await self._generate_outline_structure(
                topic, thesis_statement, analysis
            )

            # 3. 详细规划每个章节
            chapter_details = await self._plan_chapter_details(
                outline, literature_review
            )

            # 4. 评估大纲质量
            quality_score = await self._evaluate_outline_quality(
                topic, outline, chapter_details
            )

            return WritingOutput(
                success=True,
                result={
                    "topic": topic,
                    "thesis_statement": thesis_statement,
                    "target_venue": target_venue,
                    "academic_level": academic_level,
                    "outline": outline,
                    "chapter_details": chapter_details,
                    "total_chapters": len(outline.get("chapters", [])),
                    "estimated_words": outline.get("estimated_words", 0)
                },
                agent_name=self.name,
                reasoning=f"Generated outline with {len(outline.get('chapters', []))} chapters",
                quality_score=quality_score
            )

        except Exception as e:
            self.logger.error(f"OutlineGeneratorAgent execution failed: {e}")
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _analyze_requirements(
        self,
        topic: str,
        thesis_statement: str,
        target_venue: str,
        academic_level: str
    ) -> Dict[str, Any]:
        """分析研究要求"""
        prompt = f"""
分析以下论文需求：

主题：{topic}
研究论点：{thesis_statement}
目标期刊/会议：{target_venue}
学术水平：{academic_level}

请分析：
1. 研究类型（理论/应用/实证）
2. 论文结构偏好（根据目标期刊）
3. 章节重点（根据论点）
4. 字数估算

输出JSON格式：
{{
    "research_type": "理论/应用/实证",
    "structure_preference": "结构偏好",
    "key_sections": ["重点章节"],
    "estimated_words": 总字数估算,
    "special_requirements": ["特殊要求"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"Requirements analysis failed: {e}")
            return {
                "research_type": "应用",
                "estimated_words": 10000,
                "special_requirements": []
            }

    async def _generate_outline_structure(
        self,
        topic: str,
        thesis_statement: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成大纲结构"""
        research_type = analysis.get("research_type", "应用")

        # 根据研究类型选择模板
        templates = {
            "理论": ["引言", "理论背景", "理论框架", "理论验证", "讨论", "结论"],
            "应用": ["引言", "相关工作", "方法", "实验", "结果分析", "讨论", "结论"],
            "实证": ["引言", "文献综述", "研究方法", "数据分析", "结果", "讨论", "结论"]
        }

        template = templates.get(research_type, templates["应用"])

        prompt = f"""
为以下研究主题生成详细论文大纲：

主题：{topic}
研究论点：{thesis_statement}
研究类型：{research_type}
参考模板：{json.dumps(template, ensure_ascii=False)}

请生成完整大纲，包含：
1. 章节列表（带层级）
2. 每章的核心内容概要
3. 各章的逻辑关系说明
4. 总字数估算

输出JSON格式：
{{
    "chapters": [
        {{
            "level": 1,
            "title": "章节标题",
            "subsections": [
                {{"title": "子标题", "content_brief": "内容概要"}}
            ],
            "content_points": ["内容要点1", "内容要点2"],
            "logic_relation": "与前一章的关系"
        }}
    ],
    "estimated_words": 总字数,
    "structure_reasoning": "结构设计理由"
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"Outline generation failed: {e}")
            return {
                "chapters": [{"level": 1, "title": "Introduction"}],
                "estimated_words": 10000
            }

    async def _plan_chapter_details(
        self,
        outline: Dict[str, Any],
        literature_review: Dict[str, Any]
    ) -> Dict[str, Any]:
        """详细规划每个章节"""
        chapters = outline.get("chapters", [])

        if not chapters:
            return {}

        prompt = f"""
为以下大纲的每个章节规划详细内容：

大纲章节：{json.dumps(chapters, ensure_ascii=False)}

文献综述摘要：{json.dumps(literature_review, ensure_ascii=False)}

请为每个章节提供：
1. 核心论点（这个章节要传达什么）
2. 所需证据/材料（需要什么支持）
3. 论述逻辑（如何组织内容）
4. 与其他章节的衔接

输出JSON格式：
{{
    "chapter_plans": {{
        "章节标题": {{
            "core_argument": "核心论点",
            "required_evidence": ["所需证据"],
            "argument_logic": "论述逻辑",
            "transitions": ["衔接说明"]
        }}
    }}
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("chapter_plans", {})
        except Exception as e:
            logger.error(f"Chapter planning failed: {e}")
            return {}

    async def _evaluate_outline_quality(
        self,
        topic: str,
        outline: Dict[str, Any],
        chapter_details: Dict[str, Any]
    ) -> float:
        """评估大纲质量"""
        prompt = f"""
评估以下论文大纲的质量：

主题：{topic}
大纲：{json.dumps(outline, ensure_ascii=False)}
章节详情：{json.dumps(chapter_details, ensure_ascii=False)}

评估维度（每项1-10分）：
1. 结构完整性 - 是否包含所有必要章节
2. 逻辑连贯性 - 章节之间是否逻辑连贯
3. 内容合理性 - 各章节内容分配是否合理
4. 与主题相关性 - 是否紧密围绕主题

输出JSON格式：
{{
    "scores": {{
        "completeness": 分数,
        "coherence": 分数,
        "balance": 分数,
        "relevance": 分数
    }},
    "overall_score": 总分(0-1),
    "suggestions": ["改进建议"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            scores = data.get("scores", {})
            overall = data.get("overall_score", 0.7)

            # 计算平均分
            if scores:
                avg = sum(scores.values()) / len(scores) / 10.0
                return round(avg, 2)

            return overall
        except Exception as e:
            logger.error(f"Outline evaluation failed: {e}")
            return 0.7

    def format_outline_markdown(self, outline: Dict[str, Any]) -> str:
        """将大纲格式化为Markdown"""
        lines = ["# Paper Outline\n"]

        for chapter in outline.get("chapters", []):
            level = chapter.get("level", 1)
            title = chapter.get("title", "")

            # 根据层级添加Markdown标题
            prefix = "#" * level
            lines.append(f"{prefix} {title}\n")

            # 添加子标题
            for sub in chapter.get("subsections", []):
                lines.append(f"## {sub.get('title', '')}")
                if sub.get("content_brief"):
                    lines.append(f"*{sub.get('content_brief')}*\n")

            # 添加内容要点
            if chapter.get("content_points"):
                lines.append("\n**Content Points:**")
                for point in chapter.get("content_points"):
                    lines.append(f"- {point}")

            lines.append("")

        return "\n".join(lines)
