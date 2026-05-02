"""
Writer Agent - LangGraph 工作流节点

职责：
- 基于大纲和选中论文逐章节撰写
- 整合文献引用
- 章节并行生成（核心优化）
"""

from src.agents_v2.logging_config import get_logging_logger

import time
import asyncio
from typing import Dict, List, Optional

from ..state import PaperAgentState, Paper

logger = get_logging_logger(__name__)


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
        """LangGraph 节点入口 - 章节并行撰写优化版"""
        outline = state.outline
        papers = state.selected_papers or state.papers
        sections = outline.get("sections", [])
        feedback = state.feedback

        logger.info(f"[Writer] 开始撰写 {len(sections)} 个章节（并行模式）")
        start = time.time()

        if not sections:
            logger.warning("[Writer] 大纲中没有章节")
            state.draft = "# Draft\n\nNo sections available."
            state.current_phase = "review"
            return state

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 并行撰写所有章节
        draft_contents = loop.run_until_complete(
            self._write_sections_parallel(sections, papers, feedback, loop)
        )

        # 组装草稿
        draft_parts = [f"# {outline.get('title', 'Survey Paper')}", ""]
        for content in draft_contents:
            draft_parts.append(content)
            draft_parts.append("")

        state.draft = "\n".join(draft_parts)
        state.current_phase = "review"

        # 引用验证
        try:
            from ...writing.citation_generator import CitationVerifier
            import re
            citations_in_text = re.findall(r'\[(\d+(?:[,-]\d+)*)\]', state.draft)
            if citations_in_text:
                logger.info(f"[Writer] 发现 {len(citations_in_text)} 处引用标记")
                state["citation_count"] = len(citations_in_text)
        except Exception as e:
            logger.debug(f"[Writer] 引用验证跳过: {e}")

        elapsed = time.time() - start
        logger.info(f"[Writer] 写作完成（并行），总长度 {len(state.draft)} 字符，耗时 {elapsed:.2f}s")
        return state

    async def _write_sections_parallel(
        self,
        sections: List[Dict],
        papers: List[Paper],
        feedback: List[str],
        loop
    ) -> List[str]:
        """并行撰写所有章节

        使用 asyncio.gather 实现章节并行生成，显著减少总耗时。
        """
        semaphore = asyncio.Semaphore(3)  # 限制并发数，避免API限流

        async def write_section_with_semaphore(section: Dict) -> str:
            async with semaphore:
                return await self._write_section_llm(section, papers, feedback)

        # 创建所有章节的写作任务
        tasks = [write_section_with_semaphore(section) for section in sections]

        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        contents = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"[Writer] 章节 {i} 生成失败: {result}")
                # 使用模板作为降级
                contents.append(self._build_section_template(sections[i], papers))
            else:
                contents.append(result)

        return contents
