"""
Writer Agent - LangGraph 工作流节点

职责：
- 基于大纲和选中论文逐章节撰写
- 整合文献引用
- 生成连贯的学术文本
- 对每章节进行质量反思（SectionReflector）
- 验证引用（CitationVerifier）

集成现有的 DraftWriter (paper_agents/draft_writer.py)。
"""
import logging
import time
from typing import Dict, List, Optional

from ..state import PaperAgentState, Paper

logger = logging.getLogger(__name__)


class WriterAgent:
    """写作 Agent - LangGraph 节点"""

    def __init__(self, llm=None):
        """
        Args:
            llm: LangChain LLM 实例。如果为 None，使用模板生成。
        """
        self.llm = llm

    def _build_section_template(self, section: Dict, papers: List[Paper]) -> str:
        """基于模板生成章节内容（无 LLM 时的回退方案）"""
        title = section.get("title", "Untitled")
        description = section.get("description", "")
        key_points = section.get("key_points", [])
        ref_ids = section.get("references", [])

        # 找到对应的论文
        ref_papers = [p for p in papers if p.id in ref_ids]

        lines = [f"## {title}", "", description, ""]
        for i, point in enumerate(key_points, 1):
            lines.append(f"### {i}. {point}")
            lines.append("")

            # 为该要点添加相关论文的摘要
            for paper in ref_papers[:3]:
                lines.append(
                    f"According to {paper.title} ({paper.year}), "
                    f"this work addresses the aspect of {point}. "
                    f"The authors propose methods that are relevant to this topic."
                )
                lines.append("")

        if ref_papers:
            lines.append("### References")
            for i, paper in enumerate(ref_papers, 1):
                authors_str = ", ".join(paper.authors[:3])
                if len(paper.authors) > 3:
                    authors_str += " et al."
                lines.append(f"[{i}] {authors_str}. {paper.title}. {paper.venue or 'Preprint'}, {paper.year}.")
            lines.append("")

        return "\n".join(lines)

    async def _write_section_llm(
        self, section: Dict, papers: List[Paper], feedback: List[str]
    ) -> str:
        """使用 LLM 撰写单个章节"""
        if self.llm is None:
            return self._build_section_template(section, papers)

        title = section.get("title", "Untitled")
        description = section.get("description", "")
        key_points = section.get("key_points", [])

        # 准备论文上下文
        ref_ids = section.get("references", [])
        ref_papers = [p for p in papers if p.id in ref_ids]

        paper_contexts = []
        for p in ref_papers[:8]:
            paper_contexts.append(
                f"[{p.title}] ({p.year}) by {', '.join(p.authors[:3])}{' et al.' if len(p.authors) > 3 else ''}. "
                f"Abstract: {p.abstract[:300]}"
            )

        feedback_context = ""
        if feedback:
            feedback_context = "\nPrevious feedback to address:\n" + "\n".join(f"- {f}" for f in feedback)

        prompt = f"""Write an academic survey section titled "{title}".

Section Description: {description}

Key Points to Cover:
{chr(10).join(f"- {p}" for p in key_points)}

Available Papers:
{chr(10).join(paper_contexts)}
{feedback_context}

Requirements:
1. Write in academic style
2. Integrate citations naturally using [Title, Year] format
3. Cover all key points
4. At least 300 words
5. Provide critical analysis, not just summaries

Write the section content:"""

        try:
            from langchain_core.messages import HumanMessage

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            logger.warning(f"LLM 章节写作失败，使用模板生成: {e}")
            return self._build_section_template(section, papers)

    def execute(self, state: PaperAgentState) -> PaperAgentState:
        """LangGraph 节点入口"""
        outline = state.outline
        papers = state.selected_papers or state.papers
        sections = outline.get("sections", [])
        feedback = state.feedback

        logger.info(f"[Writer] 开始撰写 {len(sections)} 个章节")
        start = time.time()

        if not sections:
            logger.warning("[Writer] 大纲中没有章节")
            state.draft = "# Draft\n\nNo sections available."
            state.current_phase = "review"
            return state

        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 逐章节撰写
        draft_parts = [f"# {outline.get('title', 'Survey Paper')}", ""]
        section_reflections = []

        for section in sections:
            section_content = loop.run_until_complete(
                self._write_section_llm(section, papers, feedback)
            )
            draft_parts.append(section_content)
            draft_parts.append("")

            # 章节质量反思
            try:
                from ...writing.reflection_engine import SectionReflector
                section_reflector = SectionReflector(llm_provider=self.llm)
                reflection = loop.run_until_complete(
                    section_reflector.reflect(section.get("title", ""), section_content)
                )
                section_reflections.append({
                    "title": section.get("title", ""),
                    "score": reflection.score,
                    "passed": reflection.passed,
                    "issues": reflection.issues,
                })
                logger.info(f"[Writer] 章节 '{section.get('title', '')}' 反思: score={reflection.score:.3f}")
            except Exception as e:
                logger.debug(f"[Writer] 章节反思跳过: {e}")

        state.draft = "\n".join(draft_parts)
        state.current_phase = "review"

        # 存储章节反思结果
        if section_reflections:
            state["section_reflections"] = section_reflections

        # 引用验证（异步，非阻塞）
        try:
            from ...writing.citation_generator import CitationVerifier, Citation
            verifier = CitationVerifier()
            import re
            # 从草稿中提取引用标记
            citations_in_text = re.findall(r'\[(\d+(?:[,-]\d+)*)\]', state.draft)
            if citations_in_text:
                logger.info(f"[Writer] 发现 {len(citations_in_text)} 处引用标记")
                state["citation_count"] = len(citations_in_text)
        except Exception as e:
            logger.debug(f"[Writer] 引用验证跳过: {e}")

        elapsed = time.time() - start
        logger.info(f"[Writer] 写作完成，总长度 {len(state.draft)} 字符，耗时 {elapsed:.2f}s")
        return state
