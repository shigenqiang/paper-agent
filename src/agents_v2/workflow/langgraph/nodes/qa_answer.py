"""
问答回答节点 - QA Answer Node

功能：
1. 根据综合分析生成回答
2. 支持引用论文
3. 生成结构化的回答内容
4. 集成 AcademicQASystem 实现严格模式

设计原则：
- 基于综合数据生成回答
- 包含论文引用
- 可读性强的回答格式
- 可选的严格模式（幻觉检测、置信度校准）
"""
from typing import Dict, Any, Optional, Callable
from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class QAAnswerNode:
    """问答回答节点 - 生成最终回答"""

    def __init__(self, llm_provider=None, use_academic_qa: bool = True):
        """初始化问答回答节点

        Args:
            llm_provider: LLM 提供者（可选），用于生成回答
            use_academic_qa: 是否使用 AcademicQASystem（严格模式）
        """
        self.llm_provider = llm_provider
        self.use_academic_qa = use_academic_qa
        self._academic_qa_system = None

    def _get_academic_qa_system(self):
        """获取或初始化 AcademicQASystem"""
        if self._academic_qa_system is None and self.use_academic_qa:
            try:
                from ...academic_qa import AcademicQASystem, AcademicQAConfig
                config = AcademicQAConfig(
                    llm=self.llm_provider,
                    enable_crag=True,
                    enable_self_rag=True,
                    enable_hallucination_detection=True,
                    enable_confidence_calibration=True,
                    enable_multi_hop=True,
                )
                self._academic_qa_system = AcademicQASystem(config=config)
                logger.info("AcademicQASystem initialized for QA answer")
            except Exception as e:
                logger.warning(f"Failed to initialize AcademicQASystem: {e}")
                self._academic_qa_system = None
        return self._academic_qa_system

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行问答回答生成

        Args:
            state: 当前状态，需包含 qa_synthesis 和 user_query

        Returns:
            更新后的状态，添加 answer 字段
        """
        synthesis = state.get("qa_synthesis", {})
        user_query = state.get("user_query", "")
        papers = state.get("papers", [])

        if not synthesis or not papers:
            logger.warning("No synthesis data for answer generation")
            state["answer"] = "抱歉，未找到相关信息。"
            return state

        try:
            # 尝试使用 AcademicQASystem（严格模式）
            academic_qa = self._get_academic_qa_system()

            if academic_qa:
                # 使用 AcademicQASystem 生成答案
                contexts = self._build_contexts(synthesis, papers)
                qa_result = await academic_qa.ask(
                    query=user_query,
                    contexts=contexts,
                    mode="strict"
                )
                answer = academic_qa.format_answer_with_citations(qa_result)
                state["answer"] = answer
                state["qa_confidence"] = qa_result.confidence
                state["qa_hallucination_score"] = qa_result.hallucination_score
                logger.info(f"AcademicQA answer generated: confidence={qa_result.confidence:.2f}")
            else:
                # 降级到基础模式
                answer = self._generate_answer(user_query, synthesis, papers)
                state["answer"] = answer

            logger.info("QA answer generation completed")

        except Exception as e:
            logger.error(f"QA answer generation failed: {e}")
            state["answer"] = "抱歉，回答生成失败。"
            state.setdefault("errors", []).append(f"QA answer error: {str(e)}")

        return state

    def _build_contexts(self, synthesis: Dict[str, Any], papers: list) -> list:
        """从 synthesis 和 papers 构建上下文列表"""
        contexts = []

        # 添加综合分析摘要
        if synthesis.get("answer"):
            contexts.append(synthesis["answer"])

        # 添加关键洞察
        key_insights = synthesis.get("key_insights", [])
        for insight in key_insights[:3]:
            contexts.append(f"关键洞察: {insight}")

        # 添加论文内容
        for paper in papers[:10]:
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")
            if abstract:
                contexts.append(f"论文: {title}\n摘要: {abstract[:300]}")

        return contexts

    def _generate_answer(
        self,
        query: str,
        synthesis: Dict[str, Any],
        papers: list
    ) -> str:
        """生成回答内容"""
        sections = []

        # 回答摘要
        summary = synthesis.get("summary", "")
        sections.append(f"{summary}\n\n")

        # 主要发现
        if "comparison_groups" in synthesis:
            sections.append(self._format_comparison(synthesis))
        elif "year_distribution" in synthesis:
            sections.append(self._format_trend(synthesis))
        else:
            sections.append(self._format_basic(synthesis, papers))

        # 参考文献
        sections.append("\n## 参考文献\n\n")
        top_papers = papers[:5]
        for i, paper in enumerate(top_papers, 1):
            title = paper.get("title", "Unknown")
            authors = paper.get("authors", [])
            author_str = ", ".join(authors[:3]) if authors else "Unknown"
            year = paper.get("year", "")
            citations = paper.get("citations", 0)

            sections.append(
                f"{i}. {title}\n"
                f"   - 作者: {author_str}\n"
                f"   - 年份: {year}, 引用: {citations}\n\n"
            )

        return "".join(sections)

    def _format_basic(self, synthesis: Dict[str, Any], papers: list) -> str:
        """格式化基础回答"""
        sections = []

        sections.append("## 主要发现\n\n")

        # 关键作者
        key_authors = synthesis.get("key_authors", [])
        if key_authors:
            sections.append(f"**主要研究者**: {', '.join(key_authors)}\n\n")

        # 关键场所
        key_venues = synthesis.get("key_venues", [])
        if key_venues:
            sections.append(f"**主要发表场所**: {', '.join(key_venues)}\n\n")

        # Top 论文
        top_papers = synthesis.get("top_papers", [])[:3]
        if top_papers:
            sections.append("**重要论文**:\n")
            for paper in top_papers:
                title = paper.get("title", "Unknown")
                citations = paper.get("citations", 0)
                sections.append(f"- {title} ({citations} 引用)\n")
            sections.append("\n")

        return "".join(sections)

    def _format_comparison(self, synthesis: Dict[str, Any]) -> str:
        """格式化比较分析回答"""
        sections = []
        sections.append("## 比较分析\n\n")

        groups = synthesis.get("comparison_groups", {})
        for keyword, papers in groups.items():
            sections.append(f"### {keyword}\n")
            sections.append(f"- 相关论文数: {len(papers)}\n")
            if papers:
                top_paper = papers[0]
                sections.append(f"- 代表论文: {top_paper.get('title', 'Unknown')}\n")
            sections.append("\n")

        return "".join(sections)

    def _format_trend(self, synthesis: Dict[str, Any]) -> str:
        """格式化趋势分析回答"""
        sections = []
        sections.append("## 趋势分析\n\n")

        year_dist = synthesis.get("year_distribution", {})
        if year_dist:
            sections.append("**年份分布**:\n")
            for year, count in sorted(year_dist.items(), reverse=True)[:5]:
                sections.append(f"- {year}: {count} 篇\n")
            sections.append("\n")

        recent = synthesis.get("recent_papers", [])[:3]
        if recent:
            sections.append("**最新研究**:\n")
            for paper in recent:
                title = paper.get("title", "Unknown")
                year = paper.get("year", "")
                sections.append(f"- ({year}) {title}\n")
            sections.append("\n")

        return "".join(sections)
