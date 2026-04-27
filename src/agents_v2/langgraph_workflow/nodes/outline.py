"""
Outline Agent - LangGraph 工作流节点

职责：
- 基于选中论文生成论文大纲
- 包含章节标题、摘要和关键要点

集成现有的 OutlineAgent (paper_agents/outline_agent.py)。
"""
import logging
import time
from typing import Any, Dict, List, Optional

from ..state import PaperAgentState, Paper

logger = logging.getLogger(__name__)


class OutlineAgent:
    """大纲生成 Agent - LangGraph 节点"""

    def __init__(self, llm=None):
        """
        Args:
            llm: LangChain LLM 实例。如果为 None，使用规则生成大纲。
        """
        self.llm = llm

    def _build_rule_based_outline(self, papers: List[Paper], query: str) -> Dict[str, Any]:
        """基于规则生成大纲（无 LLM 时的回退方案）"""
        # 从查询中提取主题
        topic = query.strip()

        # 统计关键词
        keyword_freq: Dict[str, int] = {}
        for paper in papers:
            for term in paper.abstract.lower().split():
                if len(term) > 4:
                    keyword_freq[term] = keyword_freq.get(term, 0) + 1

        top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:5]

        outline: Dict[str, Any] = {
            "title": f"A Survey of {topic}",
            "sections": [
                {
                    "title": "Introduction",
                    "description": f"介绍 {topic} 的背景、动机和本文贡献",
                    "key_points": [
                        f"{topic} 的定义和应用场景",
                        "现有工作的分类与比较",
                        "本文的结构安排",
                    ],
                    "references": [],
                },
                {
                    "title": "Background and Preliminaries",
                    "description": f"介绍 {topic} 的基础概念和理论框架",
                    "key_points": [
                        f"核心概念定义",
                        "基础理论",
                    ],
                    "references": [],
                },
                {
                    "title": "Methods and Approaches",
                    "description": f"分类介绍 {topic} 的主要方法",
                    "key_points": [
                        f"方法分类体系",
                        "每类方法的代表工作",
                        "方法比较与分析",
                    ],
                    "references": [],
                },
                {
                    "title": "Experimental Results",
                    "description": "实验设置与结果分析",
                    "key_points": [
                        "数据集和评估指标",
                        "主要实验结果",
                        "对比分析",
                    ],
                    "references": [],
                },
                {
                    "title": "Challenges and Future Directions",
                    "description": f"分析 {topic} 面临的挑战和未来方向",
                    "key_points": [
                        "当前方法的局限性",
                        "开放性问题",
                        "未来研究机会",
                    ],
                    "references": [],
                },
                {
                    "title": "Conclusion",
                    "description": f"总结 {topic} 的研究现状",
                    "key_points": [
                        "主要发现总结",
                        "对研究社区的启示",
                    ],
                    "references": [],
                },
            ],
            "keywords": [kw for kw, _ in top_keywords],
            "total_papers": len(papers),
        }

        # 将高引用论文分配到 Introduction 作为参考文献
        sorted_by_citations = sorted(papers, key=lambda p: p.citations, reverse=True)
        intro_refs = [p.id for p in sorted_by_citations[:5]]
        outline["sections"][0]["references"] = intro_refs

        return outline

    async def _build_llm_outline(self, papers: List[Paper], query: str) -> Dict[str, Any]:
        """使用 LLM 生成大纲"""
        if self.llm is None:
            return self._build_rule_based_outline(papers, query)

        paper_contexts = []
        for p in papers[:15]:
            paper_contexts.append(
                f"- Title: {p.title}\n  Abstract: {p.abstract[:200]}\n  Citations: {p.citations}"
            )

        prompt = f"""Based on the following papers about "{query}", generate a comprehensive survey outline.

Papers:
{chr(10).join(paper_contexts)}

Return a JSON object with the following structure:
{{
    "title": "Survey Title",
    "sections": [
        {{
            "title": "Section Title",
            "description": "Section description",
            "key_points": ["point1", "point2"],
            "references": ["paper_id1", "paper_id2"]
        }}
    ],
    "keywords": ["keyword1", "keyword2"]
}}

Only return valid JSON, no additional text."""

        try:
            from langchain_core.messages import HumanMessage

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            import json

            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            outline = json.loads(content)
            outline["total_papers"] = len(papers)
            return outline
        except Exception as e:
            logger.warning(f"LLM 大纲生成失败，使用规则生成: {e}")
            return self._build_rule_based_outline(papers, query)

    def execute(self, state: PaperAgentState) -> PaperAgentState:
        """LangGraph 节点入口（同步包装）"""
        papers = state.selected_papers or state.papers
        query = state.user_query
        logger.info(f"[Outline] 开始生成大纲，基于 {len(papers)} 篇论文")
        start = time.time()

        if not papers:
            logger.warning("[Outline] 没有可用论文，生成空大纲")
            state.outline = {"title": f"Survey on {query}", "sections": [], "total_papers": 0}
            state.current_phase = "write"
            return state

        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        outline = loop.run_until_complete(self._build_llm_outline(papers, query))

        elapsed = time.time() - start
        logger.info(f"[Outline] 大纲生成完成，共 {len(outline.get('sections', []))} 个章节，耗时 {elapsed:.2f}s")

        state.outline = outline
        state.current_phase = "write"
        return state
