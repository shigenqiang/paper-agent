"""
DraftWriterAgent - 分节撰写Agent

职责：
- 按大纲撰写各章节
- 保持内容连贯性
- 添加引用和参考文献
"""
from typing import Any, Dict, List, Optional
import json
import logging

from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig

logger = logging.getLogger(__name__)


class DraftWriterAgent(PaperAgentBase):
    """
    DraftWriterAgent - 分节撰写

    职责：
    - 按大纲撰写各章节
    - 保持内容连贯性
    - 添加引用和参考文献
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个专业的学术论文写作者。
你的职责是：
1. 按照大纲撰写各章节
2. 保持学术写作规范
3. 内容连贯、逻辑清晰
4. 正确引用文献

请确保：
- 语言学术规范
- 论述有理有据
- 格式符合要求"""
        super().__init__(
            name="draft_writer_agent",
            llm_config=llm_config,
            description="论文分节撰写",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        执行分节撰写

        Args:
            input_data: 包含task_type的字典
            context: 执行上下文（包含outline、thesis、literature）
        """
        outline = {}
        thesis = ""
        literature = {}

        if context:
            outline = context.get("outline", {})
            thesis = context.get("thesis_statement", "")
            literature = context.get("literature_result", {})

        if not outline:
            outline = input_data.get("outline", {})

        if not thesis:
            thesis = "Research topic"

        try:
            # 1. 获取章节列表
            chapter_plans = outline.get("chapters", [])

            # 2. 按顺序撰写各章节
            written_chapters = []
            for chapter in chapter_plans:
                section = await self._write_chapter(chapter, thesis, literature, context)
                written_chapters.append(section)

            # 3. 整合初稿
            draft = self._compile_draft(written_chapters)

            return AgentOutput(
                success=True,
                result={
                    "chapters": written_chapters,
                    "full_draft": draft,
                    "chapter_count": len(written_chapters)
                },
                agent_name=self.name,
                reasoning=f"Written {len(written_chapters)} sections",
                quality_score=0.7
            )

        except Exception as e:
            self.logger.error(f"DraftWriterAgent execution failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _write_chapter(
        self,
        chapter: Dict[str, Any],
        thesis: str,
        literature: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """撰写单个章节"""
        chapter_name = chapter.get("name", "")
        main_points = chapter.get("main_points", [])
        citations_needed = chapter.get("citations_needed", [])
        paper_analyses = literature.get("paper_analyses", []) if literature else []

        # 根据章节类型选择写作提示
        writing_prompts = {
            "introduction": self._write_introduction,
            "literature review": self._write_literature_review,
            "methodology": self._write_methodology,
            "results": self._write_results,
            "discussion": self._write_discussion,
            "conclusion": self._write_conclusion
        }

        # 找到对应的写作方法
        prompt_func = None
        for key, func in writing_prompts.items():
            if key.lower() in chapter_name.lower():
                prompt_func = func
                break

        if prompt_func:
            content = await prompt_func(chapter_name, thesis, main_points, paper_analyses, context)
        else:
            content = await self._write_general_section(chapter_name, thesis, main_points, paper_analyses)

        return {
            "index": chapter.get("order", 0),
            "title": chapter_name,
            "content": content,
            "citations": citations_needed,
            "completed": True
        }

    async def _write_introduction(
        self,
        title: str,
        thesis: str,
        main_points: List[str],
        paper_analyses: List[Dict],
        context: Optional[Dict]
    ) -> str:
        """撰写引言章节"""
        prompt = f"""
撰写学术论文的引言章节：

论文主题/Thesis: {thesis}
主要要点：{json.dumps(main_points, ensure_ascii=False)}

引言应该包含：
1. 研究背景（ широкой контекст）
2. 问题的提出
3. 研究动机和意义
4. 本文的主要贡献

请撰写引言（约500-800字）：
"""
        try:
            return await self._llm_call(prompt)
        except Exception as e:
            self.logger.error(f"Introduction writing failed: {e}")
            return f"## {title}\n\nIntroduction content for {thesis}..."

    async def _write_literature_review(
        self,
        title: str,
        thesis: str,
        main_points: List[str],
        paper_analyses: List[Dict],
        context: Optional[Dict]
    ) -> str:
        """撰写文献综述章节"""
        prompt = f"""
撰写学术论文的文献综述章节：

Thesis: {thesis}
主要要点：{json.dumps(main_points, ensure_ascii=False)}
相关论文分析：{json.dumps(paper_analyses[:10], ensure_ascii=False)}

文献综述应该：
1. 分类整理现有研究
2. 指出各研究的优缺点
3. 识别研究空白
4. 为本文研究奠定基础

请撰写文献综述（约800-1000字）：
"""
        try:
            return await self._llm_call(prompt)
        except Exception as e:
            self.logger.error(f"Literature review writing failed: {e}")
            return f"## {title}\n\nLiterature review content..."

    async def _write_methodology(
        self,
        title: str,
        thesis: str,
        main_points: List[str],
        paper_analyses: List[Dict],
        context: Optional[Dict]
    ) -> str:
        """撰写方法论章节"""
        prompt = f"""
撰写学术论文的方法论章节：

Thesis: {thesis}
主要要点：{json.dumps(main_points, ensure_ascii=False)}

方法论应该包含：
1. 研究方法的选择依据
2. 方法的详细描述
3. 数据收集/实验设计
4. 分析方法

请撰写方法论章节（约600-800字）：
"""
        try:
            return await self._llm_call(prompt)
        except Exception as e:
            self.logger.error(f"Methodology writing failed: {e}")
            return f"## {title}\n\nMethodology content..."

    async def _write_results(
        self,
        title: str,
        thesis: str,
        main_points: List[str],
        paper_analyses: List[Dict],
        context: Optional[Dict]
    ) -> str:
        """撰写结果章节"""
        prompt = f"""
撰写学术论文的结果章节：

Thesis: {thesis}
主要要点：{json.dumps(main_points, ensure_ascii=False)}

结果章节应该：
1. 客观呈现研究发现
2. 使用表格/图表辅助说明
3. 避免过度解释

请撰写结果章节（约600-800字）：
"""
        try:
            return await self._llm_call(prompt)
        except Exception as e:
            self.logger.error(f"Results writing failed: {e}")
            return f"## {title}\n\nResults content..."

    async def _write_discussion(
        self,
        title: str,
        thesis: str,
        main_points: List[str],
        paper_analyses: List[Dict],
        context: Optional[Dict]
    ) -> str:
        """撰写讨论章节"""
        prompt = f"""
撰写学术论文的讨论章节：

Thesis: {thesis}
主要要点：{json.dumps(main_points, ensure_ascii=False)}

讨论章节应该：
1. 解释结果的含义
2. 与现有研究对比
3. 指出研究的局限性
4. 提出未来研究方向

请撰写讨论章节（约600-800字）：
"""
        try:
            return await self._llm_call(prompt)
        except Exception as e:
            self.logger.error(f"Discussion writing failed: {e}")
            return f"## {title}\n\nDiscussion content..."

    async def _write_conclusion(
        self,
        title: str,
        thesis: str,
        main_points: List[str],
        paper_analyses: List[Dict],
        context: Optional[Dict]
    ) -> str:
        """撰写结论章节"""
        prompt = f"""
撰写学术论文的结论章节：

Thesis: {thesis}
主要要点：{json.dumps(main_points, ensure_ascii=False)}

结论章节应该：
1. 总结主要发现
2. 强调研究贡献
3. 说明研究局限
4. 提出建议

请撰写结论章节（约400-500字）：
"""
        try:
            return await self._llm_call(prompt)
        except Exception as e:
            self.logger.error(f"Conclusion writing failed: {e}")
            return f"## {title}\n\nConclusion content..."

    async def _write_general_section(
        self,
        title: str,
        thesis: str,
        main_points: List[str],
        paper_analyses: List[Dict]
    ) -> str:
        """撰写通用章节"""
        prompt = f"""
撰写以下章节：

标题：{title}
Thesis: {thesis}
主要要点：{json.dumps(main_points, ensure_ascii=False)}

请撰写该章节（约500字）：
"""
        try:
            return await self._llm_call(prompt)
        except Exception as e:
            self.logger.error(f"General section writing failed: {e}")
            return f"## {title}\n\nSection content..."

    def _compile_draft(self, chapters: List[Dict[str, Any]]) -> str:
        """整合初稿"""
        # 按顺序排列章节
        sorted_chapters = sorted(chapters, key=lambda c: c.get("index", 0))

        # 生成各章节内容
        chapter_contents = []
        for chapter in sorted_chapters:
            title = chapter.get("title", "")
            content = chapter.get("content", "")
            chapter_contents.append(f"## {title}\n\n{content}")

        # 添加摘要（如果第一章是引言）
        abstract = "\n\n---\n\n**Abstract** (摘要)\n\n[待补充]\n\n---"

        return abstract + "\n\n".join(chapter_contents)
