"""
问答回答节点 - QA Answer Node

功能：
1. 根据综合分析生成回答
2. 支持引用论文
3. 生成结构化的回答内容

设计原则：
- 基于综合数据生成回答
- 包含论文引用
- 可读性强的回答格式
"""
from typing import Dict, Any
from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class QAAnswerNode:
    """问答回答节点 - 生成最终回答"""

    def __init__(self, llm_provider=None):
        """初始化问答回答节点

        Args:
            llm_provider: LLM 提供者（可选），用于生成回答
        """
        self.llm_provider = llm_provider

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
            # 生成回答
            answer = self._generate_answer(user_query, synthesis, papers)
            state["answer"] = answer

            logger.info("QA answer generation completed")

        except Exception as e:
            logger.error(f"QA answer generation failed: {e}")
            state["answer"] = "抱歉，回答生成失败。"
            state.setdefault("errors", []).append(f"QA answer error: {str(e)}")

        return state

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
