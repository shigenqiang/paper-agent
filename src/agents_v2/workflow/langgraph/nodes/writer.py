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

            llm: LangChain LLM 实例。必须提供，不支持模板回退。

        """

        if llm is None:

            raise ValueError("WriterAgent 必须配置 LLM，不支持模板回退")

        self.llm = llm



    def _build_section_template(self, section: Dict, papers: List[Paper]) -> str:

        """基于模板生成章节内容（降级方案 - 仅在 LLM 不可用时使用）"""

        title = section.get("title", "Untitled")

        description = section.get("description", "")

        key_points = section.get("key_points", [])

        ref_ids = section.get("references", [])



        def get_paper_id(p):

            return p.id if hasattr(p, 'id') else p.get("paper_id", p.get("id", ""))



        def get_paper_attr(p, key, default=""):

            return getattr(p, key, None) if hasattr(p, key) else p.get(key, default)



        ref_papers = [p for p in papers if get_paper_id(p) in ref_ids]



        lines = [f"## {title}", "", description, ""]

        for i, point in enumerate(key_points, 1):

            lines.append(f"### {i}. {point}")

            lines.append("")



        for p in ref_papers[:5]:

            p_title = get_paper_attr(p, 'title', 'Unknown')

            p_year = get_paper_attr(p, 'year', 'N/A')

            lines.append(f"- **{p_title}** ({p_year})")



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
        timeout_seconds = 180.0


        logger.info(f"[Writer] 开始撰写章节: {title}")



        # 准备论文上下文

        ref_ids = section.get("references", [])



        def get_paper_id(p):

            return p.id if hasattr(p, 'id') else p.get("paper_id", p.get("id", ""))



        def get_paper_attr(p, key, default=""):

            return getattr(p, key, None) if hasattr(p, key) else p.get(key, default)



        ref_papers = [p for p in papers if get_paper_id(p) in ref_ids]



        paper_contexts = []

        for p in ref_papers[:8]:

            p_title = get_paper_attr(p, 'title', 'Unknown')

            p_year = get_paper_attr(p, 'year', 'N/A')

            p_authors = get_paper_attr(p, 'authors', [])

            p_abstract = get_paper_attr(p, 'abstract', '')

            paper_contexts.append(

                f"[{p_title}] ({p_year}) by {', '.join(p_authors[:3])}{' et al.' if len(p_authors) > 3 else ''}. "

                f"Abstract: {p_abstract[:300]}"

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

            logger.info(f"[Writer] 等待 LLM 响应: {title}")

            response = await asyncio.wait_for(
                self.llm.ainvoke([HumanMessage(content=prompt)]),
                timeout=timeout_seconds
            )

            logger.info(f"[Writer] LLM 响应完成: {title}, 长度={len(response.content) if response.content else 0}")
            return response.content.strip()

        except asyncio.TimeoutError:
            logger.error(f"LLM 章节写作超时（{timeout_seconds}秒）: {title}")
            raise RuntimeError(f"章节写作超时（{timeout_seconds}秒）: {title}") from None

        except Exception as e:
            logger.error(f"LLM 章节写作失败: {e}")
            raise RuntimeError(f"章节写作失败: {e}") from e



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

                # 模板回退已禁用，使用占位符

                contents.append(f"## {sections[i].get('title', 'Section')}\n\n[内容生成失败，请重试]")

            else:

                contents.append(result)



        return contents
