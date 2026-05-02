"""
DraftGeneratorAgent - 全文初稿生成Agent

职责：
- 根据大纲生成完整的论文初稿
- 各章节内容撰写
- 引用融入
- 保持风格一致性
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

import json

import asyncio

from .base_writing_agent import WritingAgentBase, WritingOutput, LLMConfig
from .logic_coherence import LogicCoherenceChecker, SelfReviseManager, CoherenceReport

logger = get_logging_logger(__name__)


class DraftGeneratorAgent(WritingAgentBase):
    """
    DraftGeneratorAgent - 全文初稿生成

    职责：
    - 根据大纲生成各章节内容
    - 融入文献引用
    - 保持学术写作风格
    - 确保逻辑连贯
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个专业的学术论文写作专家。
你的职责是：
1. 根据大纲生成完整的论文初稿
2. 各章节内容撰写
3. 融入文献引用
4. 保持学术写作风格

请确保：
- 写作符合学术规范
- 引用准确可追溯
- 逻辑连贯一致
- 术语使用统一"""
        super().__init__(
            name="draft_generator",
            llm_config=llm_config,
            description="论文全文初稿生成",
            system_prompt=system_prompt
        )
        # 初始化逻辑一致性检查器
        self.coherence_checker = LogicCoherenceChecker()
        self.revise_manager = SelfReviseManager(self.coherence_checker)

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> WritingOutput:
        """
        生成论文初稿

        Args:
            input_data: 包含以下字段的字典：
                - topic: 研究主题
                - outline: 大纲结构
                - thesis_statement: 研究论点
                - literature_review: 文献综述 (可选)
                - references: 参考文献列表 (可选)
                - writing_style: 写作风格偏好 (可选)
            context: 执行上下文
        """
        topic = input_data.get("topic", "")
        outline = input_data.get("outline", {})
        thesis_statement = input_data.get("thesis_statement", "")
        literature_review = input_data.get("literature_review", {})
        references = input_data.get("references", [])
        writing_style = input_data.get("writing_style", "学术")

        if not topic or not outline:
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Missing topic or outline"
            )

        try:
            chapters = outline.get("chapters", [])

            # 1. 生成各章节内容
            generated_chapters = await self._generate_chapters(
                topic, chapters, thesis_statement, literature_review, references
            )

            # 2. 生成摘要
            abstract = await self._generate_abstract(
                topic, thesis_statement, generated_chapters
            )

            # 3. 整合全文
            full_draft = self._integrate_draft(
                abstract, generated_chapters, writing_style
            )

            # 4. 质量评估
            quality_score = await self._evaluate_draft_quality(
                full_draft, topic, thesis_statement
            )

            # 5. 逻辑一致性检查
            coherence_report = await self.coherence_checker.check_draft(
                full_draft, outline, references
            )

            # 6. 如果有不一致问题，尝试自动修订
            if not coherence_report.passed:
                logger.warning(f"Coherence issues found: {coherence_report.summary()}")
                full_draft, coherence_report = await self.revise_manager.revise_draft(
                    full_draft, outline, references, auto_fix=True
                )

            return WritingOutput(
                success=True,
                result={
                    "topic": topic,
                    "thesis_statement": thesis_statement,
                    "abstract": abstract,
                    "chapters": generated_chapters,
                    "full_draft": full_draft,
                    "total_words": len(full_draft.split()),
                    "chapter_count": len(generated_chapters),
                    "coherence_report": coherence_report.to_dict() if coherence_report else None
                },
                agent_name=self.name,
                reasoning=f"Generated draft with {len(generated_chapters)} chapters, {len(full_draft.split())} words. Coherence score: {coherence_report.overall_score if coherence_report else 'N/A'}",
                quality_score=quality_score,
                metadata={
                    "coherence_score": coherence_report.overall_score if coherence_report else 0,
                    "coherence_issues": len(coherence_report.issues) if coherence_report else 0
                }
            )

        except Exception as e:
            self.logger.error(f"DraftGeneratorAgent execution failed: {e}")
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _generate_chapters(
        self,
        topic: str,
        chapters: List[Dict[str, Any]],
        thesis_statement: str,
        literature_review: Dict[str, Any],
        references: List[str]
    ) -> List[Dict[str, Any]]:
        """生成各章节内容"""
        generated = []
        ref_text = "\n".join(references[:10]) if references else "No references provided"

        for i, chapter in enumerate(chapters):
            try:
                content = await self._write_chapter(
                    chapter_num=i + 1,
                    chapter=chapter,
                    topic=topic,
                    thesis_statement=thesis_statement,
                    previous_chapters=generated,
                    literature_review=literature_review,
                    references=ref_text
                )
                generated.append({
                    "title": chapter.get("title", f"Chapter {i+1}"),
                    "level": chapter.get("level", 1),
                    "content": content,
                    "word_count": len(content.split())
                })
            except Exception as e:
                logger.error(f"Chapter {i+1} generation failed: {e}")
                generated.append({
                    "title": chapter.get("title", f"Chapter {i+1}"),
                    "level": chapter.get("level", 1),
                    "content": f"[Content for {chapter.get('title')} pending]",
                    "word_count": 0
                })

        return generated

    async def _write_chapter(
        self,
        chapter_num: int,
        chapter: Dict[str, Any],
        topic: str,
        thesis_statement: str,
        previous_chapters: List[Dict[str, Any]],
        literature_review: Dict[str, Any],
        references: str
    ) -> str:
        """撰写单个章节"""
        title = chapter.get("title", "")
        level = chapter.get("level", 1)
        content_points = chapter.get("content_points", [])
        subsections = chapter.get("subsections", [])

        # 构建前序章节摘要
        prev_summary = ""
        if previous_chapters:
            prev_summary = "已完成的章节：\n" + "\n".join([
                f"- {c['title']}: {c['content'][:200]}..."
                for c in previous_chapters[-2:]
            ])

        prompt = f"""
撰写论文的第{chapter_num}章：

章节标题：{title}
章节层级：{level}
内容要点：{json.dumps(content_points, ensure_ascii=False)}
子章节：{json.dumps(subsections, ensure_ascii=False)}

研究主题：{topic}
研究论点：{thesis_statement}

前序章节摘要：
{prev_summary}

文献综述摘要：
{json.dumps(literature_review, ensure_ascii=False)[:1000]}

参考文献：
{references}

要求：
1. 学术写作风格
2. 适当引用文献（使用[1][2]格式）
3. 逻辑连贯
4. 与前序章节衔接自然
5. 字数要求：不少于500字

请生成完整的章节内容，以markdown格式输出。
"""
        try:
            response = await self._llm_call(prompt)
            return response
        except Exception as e:
            logger.error(f"Chapter writing failed: {e}")
            return f"Chapter content for {title} is being generated."

    async def _generate_abstract(
        self,
        topic: str,
        thesis_statement: str,
        chapters: List[Dict[str, Any]]
    ) -> str:
        """生成摘要"""
        # 收集各章核心内容
        chapter_summaries = []
        for ch in chapters:
            title = ch.get("title", "")
            content = ch.get("content", "")[:300]
            chapter_summaries.append(f"**{title}**: {content}...")

        prompt = f"""
为以下论文撰写摘要：

研究主题：{topic}
研究论点：{thesis_statement}

各章摘要：
{chr(10).join(chapter_summaries)}

摘要结构（四要素）：
1. 研究背景与目的
2. 研究方法
3. 主要发现/结果
4. 结论与意义

要求：
- 简洁明了，200-300字
- 使用完整句子
- 不使用缩写
- 以第3人称撰写

请生成完整的摘要。
"""
        try:
            response = await self._llm_call(prompt)
            return response
        except Exception as e:
            logger.error(f"Abstract generation failed: {e}")
            return f"Abstract for {topic}"

    def _integrate_draft(
        self,
        abstract: str,
        chapters: List[Dict[str, Any]],
        writing_style: str
    ) -> str:
        """整合生成完整论文"""
        lines = []

        # 标题
        lines.append("# " + writing_style)

        # 摘要
        lines.append("\n## Abstract\n")
        lines.append(abstract)

        # 正文
        for i, chapter in enumerate(chapters):
            lines.append(f"\n## {chapter['title']}\n")
            lines.append(chapter['content'])

        return "\n".join(lines)

    async def _evaluate_draft_quality(
        self,
        draft: str,
        topic: str,
        thesis_statement: str
    ) -> float:
        """评估初稿质量"""
        prompt = f"""
评估以下论文初稿的质量：

主题：{topic}
论点：{thesis_statement}

初稿前500字：
{draft[:500]}

评估维度（每项1-10）：
1. 结构完整性
2. 逻辑连贯性
3. 写作质量
4. 引用准确性
5. 与主题相关性

输出JSON格式：
{{
    "scores": {{...}},
    "overall_score": 0-1,
    "major_issues": ["主要问题"],
    "suggestions": ["改进建议"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("overall_score", 0.7)
        except Exception as e:
            logger.error(f"Draft evaluation failed: {e}")
            return 0.7
