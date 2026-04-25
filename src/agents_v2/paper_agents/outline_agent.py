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
        system_prompt = """你是一个学术论文结构规划专家。
你的职责是：
1. 设计清晰的论文结构
2. 规划各章节的内容要点
3. 确定关键论点和论据
4. 确保逻辑连贯性

请确保：
- 结构符合学术规范
- 各章节有明确目的
- 内容安排有逻辑性"""
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
        prompt = f"""
为以下Thesis Statement设计论文结构：

Thesis: {thesis}

请设计一个标准的学术论文结构，输出JSON格式：
{{
    "structure": {{
        "title": "论文标题建议",
        "chapters": [
            {{
                "name": "章节名称",
                "purpose": "章节目的",
                "order": 1
            }}
        ],
        "total_chapters": 7,
        "word_count_estimate": 10000
    }}
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("structure", {})
        except Exception as e:
            self.logger.error(f"Structure design failed: {e}")
            return {
                "title": "Research Paper",
                "chapters": [
                    {"name": "Introduction", "purpose": "Introduce topic", "order": 1},
                    {"name": "Literature Review", "purpose": "Review existing work", "order": 2},
                    {"name": "Methodology", "purpose": "Describe methods", "order": 3},
                    {"name": "Results", "purpose": "Present findings", "order": 4},
                    {"name": "Discussion", "purpose": "Interpret results", "order": 5},
                    {"name": "Conclusion", "purpose": "Summarize", "order": 6}
                ]
            }

    async def _plan_chapters(
        self,
        structure: Dict[str, Any],
        literature: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """规划各章节内容"""
        chapters = structure.get("chapters", [])
        paper_analyses = literature.get("paper_analyses", [])[:10] if literature else []

        prompt = f"""
为以下章节规划详细内容：

章节列表：{json.dumps(chapters, ensure_ascii=False)}
相关文献分析：{json.dumps(paper_analyses, ensure_ascii=False)}

请为每个章节规划：
1. 主要内容要点
2. 需要引用的文献
3. 关键论据

输出JSON格式：
{{
    "chapter_plans": [
        {{
            "name": "章节名称",
            "main_points": ["要点1", "要点2"],
            "citations_needed": ["引用1", "引用2"],
            "key_arguments": ["论据1", "论据2"],
            "content_guidance": "内容指导"
        }}
    ]
}}
"""
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

        prompt = f"""
基于Thesis和文献分析，确定论文的关键论点：

Thesis: {thesis}
文献分析：{json.dumps(paper_analyses[:10], ensure_ascii=False)}

请确定3-5个关键论点，输出JSON格式：
{{
    "key_arguments": [
        {{
            "id": 1,
            "argument": "论点描述",
            "supporting_evidence": ["支持证据1", "支持证据2"],
            "counter_arguments": ["可能的反对意见"],
            "rebuttal": "反驳"
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("key_arguments", [])
        except Exception as e:
            self.logger.error(f"Key arguments identification failed: {e}")
            return []
