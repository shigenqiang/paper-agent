"""
OutlineAgent - 大纲制定Agent

职责：
- 设计论文结构
- 规划各章节内容
- 确定关键论点
"""
from typing import Any, Dict, List, Optional
import json
import logging

from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig

logger = logging.getLogger(__name__)


class OutlineAgent(PaperAgentBase):
    """
    OutlineAgent - 大纲制定

    职责：
    - 设计论文结构
    - 规划各章节内容
    - 确定关键论点
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一位资深的学术论文结构规划专家，擅长根据不同研究领域和主题设计个性化的论文框架。
请遵循以下原则：
1. 根据研究主题的特点选择最合适的论文结构（实证研究、综述、理论分析、系统设计等）
2. 章节设计要紧密结合研究主题，避免通用的空泛标题
3. 各章节之间有严密的逻辑递进关系
4. 关键论点要具有学术深度和创新性
5. 章节名称要具体、有学术感，避免"引言"、"结论"等通用名称

输出要求：只返回JSON，不要包含其他解释文字。"""
        super().__init__(
            name="outline_agent",
            llm_config=llm_config,
            description="论文大纲制定",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        执行大纲制定

        Args:
            input_data: 包含topic的字典
            context: 执行上下文（包含thesis和literature）
        """
        thesis = ""
        literature = {}

        if context:
            thesis = context.get("thesis_statement", "")
            literature = context.get("literature_result", {})

        if not thesis:
            thesis = input_data.get("task_description", "Research topic")

        try:
            # 1. 设计章节结构
            structure = await self._design_structure(thesis)

            # 2. 规划各章节内容
            chapter_plans = await self._plan_chapters(structure, literature)

            # 3. 确定关键论点
            key_arguments = await self._identify_key_arguments(thesis, literature)

            # 4. 整合大纲
            outline = {
                "structure": structure,
                "chapters": chapter_plans,
                "key_arguments": key_arguments
            }

            return AgentOutput(
                success=True,
                result={"outline": outline},
                agent_name=self.name,
                reasoning=f"Created outline with {len(chapter_plans)} chapters",
                quality_score=0.8
            )

        except Exception as e:
            self.logger.error(f"OutlineAgent execution failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _design_structure(self, thesis: str) -> Dict[str, Any]:
        """设计章节结构"""
        prompt = f"""请为以下研究主题设计最合适的论文结构。

研究主题：{thesis}

要求：
1. 根据主题判断论文类型（实证研究/文献综述/理论分析/系统设计/对比实验等），选择最匹配的结构
2. 章节标题必须与研究主题紧密相关，使用学术化、具体化的表述
3. 不要使用"引言"、"文献综述"、"结论"等通用标题——请用主题相关的表述
4. 总章节数5-8章，每章有明确的学术目的

请输出以下JSON格式（仅JSON，不要其他内容）：
{{"structure": {{
    "title": "结合主题的论文标题建议",
    "paper_type": "empirical|review|theoretical|system|comparison",
    "chapters": [
        {{
            "name": "具体化的章节名称（紧扣主题）",
            "purpose": "该章节在本研究中的具体目的",
            "order": 1
        }}
    ],
    "total_chapters": 5,
    "word_count_estimate": 8000
}}}}"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            structure = data.get("structure", {})
            if not structure or not structure.get("chapters"):
                raise ValueError("LLM returned empty structure")
            return structure
        except Exception as e:
            self.logger.error(f"Structure design failed: {e}")
            raise

    async def _plan_chapters(
        self,
        structure: Dict[str, Any],
        literature: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """规划各章节内容"""
        chapters = structure.get("chapters", [])
        paper_type = structure.get("paper_type", "empirical")
        paper_analyses = literature.get("paper_analyses", [])[:10] if literature else []

        lit_context = f"""
相关文献参考：{json.dumps(paper_analyses, ensure_ascii=False)}""" if paper_analyses else "暂无相关文献，请根据学术常识规划内容。"

        prompt = f"""请为以下论文章节规划详细内容。

论文类型：{paper_type}
章节列表：
{json.dumps(chapters, ensure_ascii=False, indent=2)}

{lit_context}

要求：
1. main_points 必须是具体、有实质内容的学术要点（而非泛泛的描述）
2. 每个章节的 content_guidance 要说明"本章节应该写什么、为什么写、如何组织"
3. 避免通用的写作建议，要紧扣论文章节的具体内容
4. citations_needed 列出具体的研究方向或技术点

输出以下JSON格式：
{{"chapter_plans": [
    {{
        "name": "与输入章节名称一致",
        "main_points": ["具体学术要点1", "具体学术要点2", "具体学术要点3"],
        "citations_needed": ["需要引用的研究方向或技术"],
        "key_arguments": ["核心论据1", "核心论据2"],
        "content_guidance": "本章节的具体写作指导"
    }}
]}}"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("chapter_plans", chapters)
        except Exception as e:
            self.logger.error(f"Chapter planning failed: {e}")
            return chapters

    async def _identify_key_arguments(
        self,
        thesis: str,
        literature: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """确定关键论点"""
        paper_analyses = literature.get("paper_analyses", []) if literature else []
        lit_context = f"""
相关文献分析：{json.dumps(paper_analyses[:10], ensure_ascii=False)}""" if paper_analyses else ""

        prompt = f"""请基于以下研究主题，确定论文的关键学术论点。

📝 研究主题：{thesis}
{lit_context}

要求：
1. 论点必须与研究主题紧密相关，体现该领域的核心学术问题
2. 每个论点要有明确的可论证性，不是空泛的陈述
3. supporting_evidence 列出具体的实验结果、理论分析或已有研究
4. counter_arguments 要真实反映该领域可能存在的争议或质疑
5. rebuttal 要有理有据，体现学术思辨

输出以下JSON格式：
{{"key_arguments": [
    {{
        "id": 1,
        "argument": "具体的学术论点描述",
        "supporting_evidence": ["具体支持证据或已有研究"],
        "counter_arguments": ["可能的学术质疑"],
        "rebuttal": "学术反驳"
    }}
]}}"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("key_arguments", [])
        except Exception as e:
            self.logger.error(f"Key arguments identification failed: {e}")
            return []
