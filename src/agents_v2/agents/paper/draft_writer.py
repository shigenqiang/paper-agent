"""
DraftWriterAgent - 分节撰写Agent

职责：
- 按大纲撰写各章节
- 保持内容连贯性
- 添加引用和参考文献
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

import json

import asyncio

from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig

logger = get_logging_logger(__name__)


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

        # Debug logging
        self.logger.info(f"[DraftWriter] execute() - outline_keys={list(outline.keys()) if isinstance(outline, dict) else 'not_a_dict'}, chapters_count={len(outline.get('chapters', [])) if isinstance(outline, dict) else 'N/A'}")

        # 处理嵌套的outline结构 - OutlineAgent返回 {'outline': {'structure':..., 'chapters':..., 'key_arguments':...}}
        if isinstance(outline, dict) and "outline" in outline:
            # 从嵌套结构中提取chapters
            inner_outline = outline.get("outline", {})
            if isinstance(inner_outline, dict):
                chapter_plans = inner_outline.get("chapters", [])
                self.logger.info(f"[DraftWriter] Extracted chapters from nested outline: {len(chapter_plans)}")
            else:
                chapter_plans = []
        elif isinstance(outline, dict):
            # 直接从outline获取chapters
            chapter_plans = outline.get("chapters", [])
            self.logger.info(f"[DraftWriter] Direct outline chapters: {len(chapter_plans)}")
        else:
            chapter_plans = []

        self.logger.info(f"[DraftWriter] final chapter_plans count: {len(chapter_plans)}")

        if not thesis:
            thesis = "Research topic"

        try:
            # 2. 分析章节依赖关系，独立章节并行撰写
            # 约定：第一个章节（引言）必须首先顺序撰写，其他章节可并行
            independent_chapters = []
            dependent_chapters = []

            for i, chapter in enumerate(chapter_plans):
                if i == 0:
                    # 引言必须首先撰写（依赖章节）
                    dependent_chapters.append((i, chapter))
                else:
                    # 其他章节可并行撰写
                    independent_chapters.append((i, chapter))

            # 并行撰写独立章节
            written_chapters = {}
            if independent_chapters:
                tasks = [
                    self._write_chapter(chap, thesis, literature, context, idx)
                    for idx, chap in independent_chapters
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for (idx, _), result in zip(independent_chapters, results):
                    if not isinstance(result, Exception):
                        written_chapters[idx] = result

            # 顺序撰写依赖章节（引言）
            for idx, chapter in dependent_chapters:
                if idx not in written_chapters:
                    result = await self._write_chapter(chapter, thesis, literature, context, idx)
                    written_chapters[idx] = result

            # 按顺序整理章节
            written_chapters = [written_chapters[i] for i in sorted(written_chapters.keys())]

            # Debug: log written chapters
            self.logger.info(f"[DraftWriter] Written {len(written_chapters)} chapters: {[ch.get('title', 'unknown') for ch in written_chapters]}")

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
        context: Optional[Dict[str, Any]],
        chapter_index: int = 0
    ) -> Dict[str, Any]:
        """撰写单个章节"""
        chapter_name = chapter.get("name", "")
        main_points = chapter.get("main_points", [])
        citations_needed = chapter.get("citations_needed", [])
        paper_analyses = literature.get("paper_analyses", []) if literature else []

        # 根据章节类型选择写作提示（支持中英文匹配）
        writing_prompts = {
            "引言": self._write_introduction,
            "introduction": self._write_introduction,
            "文献综述": self._write_literature_review,
            "literature review": self._write_literature_review,
            "理论框架": self._write_literature_review,
            "方法": self._write_methodology,
            "methodology": self._write_methodology,
            "结果": self._write_results,
            "results": self._write_results,
            "讨论": self._write_discussion,
            "discussion": self._write_discussion,
            "结论": self._write_conclusion,
            "conclusion": self._write_conclusion
        }

        # 找到对应的写作方法（先精确匹配，再模糊匹配）
        prompt_func = None
        chapter_name_lower = chapter_name.lower()

        # 先尝试完整匹配
        for key, func in writing_prompts.items():
            if key.lower() == chapter_name_lower:
                prompt_func = func
                break

        # 再尝试包含匹配
        if not prompt_func:
            for key, func in writing_prompts.items():
                if key.lower() in chapter_name_lower:
                    prompt_func = func
                    break

        if prompt_func:
            content = await prompt_func(chapter_name, thesis, main_points, paper_analyses, context)
        else:
            content = await self._write_general_section(chapter_name, thesis, main_points, paper_analyses)

        return {
            "index": chapter_index,
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
        # 提取paper_analyses中的研究背景信息
        background_info = ""
        if paper_analyses:
            backgrounds = [p.get("key_findings", "")[:200] for p in paper_analyses[:5] if p.get("key_findings")]
            if backgrounds:
                background_info = "\n相关研究背景：\n" + "\n".join([f"- {b}" for b in backgrounds])

        prompt = f"""
你是一位专业的学术论文写作者。请根据以下大纲信息，撰写一篇完整、详细的学术论文引言章节。

论文主题/Thesis: {thesis}

主要要点（必须全部涵盖）：
{json.dumps(main_points, ensure_ascii=False, indent=2)}

{background_info}

引言章节结构要求：
1. **研究背景**（约150字）：从宏观背景逐步聚焦到本研究主题，说明该领域的重要性和研究价值
2. **研究缺口**（约150字）：指出现有研究存在的不足或未解决的问题，为本研究提供必要性
3. **研究目的**（约100字）：明确本研究旨在解决什么问题或验证什么理论假设
4. **研究贡献**（约100字）：概述本研究对理论和实践的潜在贡献
5. **论文结构**（约50字）：简要说明全文的章节安排

请撰写完整的引言章节（约500-600字），内容要详尽深入，不要简略。每个要点都要有具体的内容展开。
确保语言学术规范，逻辑递进清晰（从general到specific）。
"""
        try:
            return await self._llm_call(prompt)
        except Exception as e:
            self.logger.error(f"Introduction writing failed: {e}")
            return f"## {title}\n\n[引言内容待撰写]\n\n论文主题：{thesis}\n\n主要要点：\n" + "\n".join([f"- {mp}" for mp in main_points])

    async def _write_literature_review(
        self,
        title: str,
        thesis: str,
        main_points: List[str],
        paper_analyses: List[Dict],
        context: Optional[Dict]
    ) -> str:
        """撰写文献综述章节"""
        # 提取paper_analyses中的研究信息
        studies_info = ""
        if paper_analyses:
            studies_info = "\n已分析的相关论文：\n"
            for i, p in enumerate(paper_analyses[:8], 1):
                title_p = p.get("title", "未知")
                core_prob = p.get("core_problem", "")
                key_finding = p.get("key_findings", "")
                limitation = p.get("limitations", "")
                studies_info += f"{i}. **{title_p}**\n   - 核心问题: {core_prob}\n   - 主要发现: {key_finding}\n   - 局限性: {limitation}\n"

        prompt = f"""
你是一位专业的学术论文写作者。请根据以下信息，撰写一篇完整、深入的文献综述章节。

论文主题: {thesis}

主要要点（必须全部涵盖）：
{json.dumps(main_points, ensure_ascii=False, indent=2)}

{studies_info}

文献综述章节要求：
1. **核心概念界定**（约150字）：明确定义本研究涉及的关键术语和概念
2. **理论基础**（约150字）：阐述支撑研究的核心理论，说明理论选择的合理性
3. **国内外研究现状**（约300字）：分类梳理该领域的主要研究成果，包括经典研究和最新进展
4. **研究评述**（约150字）：评析现有研究的贡献与不足，识别研究空白
5. **理论框架构建**（约150字）：整合相关理论形成本研究的分析框架

请撰写完整的文献综述章节（约800-1000字），要详尽深入，逻辑清晰，评述客观。
每个小节都要有具体内容展开，不要简略或留空。
请合理引用已有研究（使用占位符如[Author, Year]标注）。
"""
        try:
            return await self._llm_call(prompt)
        except Exception as e:
            self.logger.error(f"Literature review writing failed: {e}")
            return f"## {title}\n\n[文献综述内容待撰写]\n\n主要要点：\n" + "\n".join([f"- {mp}" for mp in main_points])

    async def _write_methodology(
        self,
        title: str,
        thesis: str,
        main_points: List[str],
        paper_analyses: List[Dict],
        context: Optional[Dict]
    ) -> str:
        """撰写方法论章节"""
        # 提取paper_analyses中的方法信息
        methods_info = ""
        if paper_analyses:
            methods = [p.get("key_methodology", "") for p in paper_analyses[:5] if p.get("key_methodology")]
            if methods:
                methods_info = "\n相关研究使用的方法参考：\n- " + "\n- ".join(methods[:5])

        prompt = f"""
你是一位专业的学术论文写作者。请根据以下信息，撰写一篇完整、详细的方法论章节。

论文主题: {thesis}

主要要点（必须全部涵盖）：
{json.dumps(main_points, ensure_ascii=False, indent=2)}

{methods_info}

方法论章节要求：
1. **研究设计**（约150字）：说明研究类型（横截面/纵向、实地实验/实验室实验等），解释选择该设计的理由
2. **样本与数据收集**（约150字）：描述抽样方法、样本量、数据来源和收集过程，说明样本的代表性
3. **变量测量**（约150字）：详述各变量的测量工具、量表来源和信效度检验方法
4. **分析方法**（约100字）：说明拟采用的分析技术和软件工具
5. **伦理考量**（约50字）：描述伦理审查和知情同意等程序

请撰写完整的方法论章节（约600-800字），描述要足够详细，使其他研究者能够复制该研究。
每个要点都要有具体内容展开，方法选择要有明确依据。
"""
        try:
            return await self._llm_call(prompt)
        except Exception as e:
            self.logger.error(f"Methodology writing failed: {e}")
            return f"## {title}\n\n[方法论内容待撰写]\n\n主要要点：\n" + "\n".join([f"- {mp}" for mp in main_points])

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
你是一位专业的学术论文写作者。请根据以下信息，撰写一篇完整、详尽的研究结果章节。

论文主题: {thesis}

主要要点（必须全部涵盖）：
{json.dumps(main_points, ensure_ascii=False, indent=2)}

结果章节要求：
1. **描述性统计**（约150字）：呈现样本特征和主要变量的描述性分析，包括均值、标准差等统计量
2. **共同方法偏差检验**（约100字）：验证是否存在系统性测量偏差，说明检验方法和结果
3. **假设检验**（约300字）：逐条报告各假设的检验结果，包括统计量、效应量、置信区间
4. **补充分析**（约150字）：如中介效应、调节效应或稳健性检验

请撰写完整的研究结果章节（约700-800字），要客观呈现数据分析结果，使用表格和图形辅助说明。
每个小节都要有具体数据和分析内容，不要简略。
统计结果要完整报告（t值、df、p值、效应量、置信区间等）。
"""
        try:
            return await self._llm_call(prompt)
        except Exception as e:
            self.logger.error(f"Results writing failed: {e}")
            return f"## {title}\n\n[研究结果内容待撰写]\n\n主要要点：\n" + "\n".join([f"- {mp}" for mp in main_points])

    async def _write_discussion(
        self,
        title: str,
        thesis: str,
        main_points: List[str],
        paper_analyses: List[Dict],
        context: Optional[Dict]
    ) -> str:
        """撰写讨论章节"""
        # 提取相关研究对比信息
        comparison_info = ""
        if paper_analyses:
            findings = [p.get("key_findings", "")[:150] for p in paper_analyses[:5] if p.get("key_findings")]
            if findings:
                comparison_info = "\n相关研究发现对比：\n- " + "\n- ".join(findings)

        prompt = f"""
你是一位专业的学术论文写作者。请根据以下信息，撰写一篇深入、有见地的讨论章节。

论文主题: {thesis}

主要要点（必须全部涵盖）：
{json.dumps(main_points, ensure_ascii=False, indent=2)}

{comparison_info}

讨论章节要求：
1. **结果解释**（约200字）：结合理论阐释研究发现的意义，解释为什么得出这样的结果
2. **与文献对话**（约200字）：将结果与前人研究进行对比分析，说明一致或不一致的原因
3. **理论贡献**（约150字）：阐述研究对理论发展的推进作用，如何丰富或修正现有理论
4. **实践启示**（约150字）：说明研究结果对实际应用的指导价值
5. **研究局限**（约100字）：诚实指出研究的不足之处，说明局限性的影响程度
6. **未来研究方向**（约100字）：提出后续研究的建议

请撰写完整的讨论章节（约900-1000字），这是论文的核心创新部分，要深入分析。
每个要点都要有充分展开，不要简略，要展示批判性思维。
"""
        try:
            return await self._llm_call(prompt)
        except Exception as e:
            self.logger.error(f"Discussion writing failed: {e}")
            return f"## {title}\n\n[讨论内容待撰写]\n\n主要要点：\n" + "\n".join([f"- {mp}" for mp in main_points])

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
你是一位专业的学术论文写作者。请根据以下信息，撰写一篇简洁有力的结论章节。

论文主题: {thesis}

主要要点（必须全部涵盖）：
{json.dumps(main_points, ensure_ascii=False, indent=2)}

结论章节要求：
1. **核心发现总结**（约150字）：凝练概括研究的主要结论，突出最重要的发现
2. **研究价值定位**（约100字）：精炼重述理论贡献与实践意义
3. **研究启示**（约150字）：面向研究者与实践者的具体建议

请撰写完整的结论章节（约400-500字），语言要简洁有力，避免引入新观点。
每个要点都要有充分内容，但保持结论的凝练感。
"""
        try:
            return await self._llm_call(prompt)
        except Exception as e:
            self.logger.error(f"Conclusion writing failed: {e}")
            return f"## {title}\n\n[结论内容待撰写]\n\n主要要点：\n" + "\n".join([f"- {mp}" for mp in main_points])

    async def _write_general_section(
        self,
        title: str,
        thesis: str,
        main_points: List[str],
        paper_analyses: List[Dict]
    ) -> str:
        """撰写通用章节"""
        prompt = f"""
你是一位专业的学术论文写作者。请根据以下信息，撰写一篇完整的学术论文章节。

章节标题: {title}
论文主题: {thesis}

主要要点（必须全部涵盖）：
{json.dumps(main_points, ensure_ascii=False, indent=2)}

请撰写该章节（约500-800字），内容要详尽深入，逻辑清晰。
确保涵盖所有主要要点，每个要点都要有充分展开。
"""
        try:
            return await self._llm_call(prompt)
        except Exception as e:
            self.logger.error(f"General section writing failed: {e}")
            return f"## {title}\n\n[章节内容待撰写]\n\n论文主题：{thesis}\n\n主要要点：\n" + "\n".join([f"- {mp}" for mp in main_points])

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
