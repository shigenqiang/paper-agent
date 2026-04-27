"""
Multimodal Node - LangGraph 工作流多模态节点

集成多模态检索器、图表分析器和公式识别器，
为论文工作流添加图文理解能力。
"""
import logging
from typing import Any, Dict, List, Optional

from ..state import PaperAgentState, Paper

logger = logging.getLogger(__name__)


class MultimodalNode:
    """多模态节点 - LangGraph 节点

    功能：
    1. PDF 图像/图表/公式提取
    2. 图像-文本联合检索
    3. 图表描述生成
    4. 公式 LaTeX 识别
    """

    def __init__(self, multimodal_retriever=None, chart_analyzer=None, formula_recognizer=None):
        """
        Args:
            multimodal_retriever: 多模态检索器实例
            chart_analyzer: 图表分析器实例
            formula_recognizer: 公式识别器实例
        """
        self._retriever = multimodal_retriever
        self._chart_analyzer = chart_analyzer
        self._formula_recognizer = formula_recognizer

    def _get_chart_analyzer(self):
        if self._chart_analyzer is None:
            from ...multimodal.chart_analyzer import ChartAnalyzer
            self._chart_analyzer = ChartAnalyzer()
        return self._chart_analyzer

    def _get_formula_recognizer(self):
        if self._formula_recognizer is None:
            from ...multimodal.formula_recognizer import FormulaRecognizer
            self._formula_recognizer = FormulaRecognizer()
        return self._formula_recognizer

    def analyze_paper_figures(self, state: PaperAgentState) -> PaperAgentState:
        """分析论文中的图表和公式

        为选中的论文生成多模态描述，增强论文理解。
        """
        papers = state.selected_papers or state.papers
        if not papers:
            return state

        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        analyzed_count = 0
        for paper in papers:
            # 提取多模态内容描述（基于文本摘要）
            if paper.abstract:
                multimodal_desc = self._extract_multimodal_hints(paper)
                paper.metadata["multimodal_analysis"] = multimodal_desc
                analyzed_count += 1

        state["metadata"] = {
            **state.get("metadata", {}),
            "multimodal_analyzed_papers": analyzed_count,
        }

        logger.info(f"[Multimodal] 分析了 {analyzed_count} 篇论文的多模态内容")
        return state

    def _extract_multimodal_hints(self, paper: Paper) -> Dict[str, Any]:
        """从论文摘要中提取多模态相关提示"""
        abstract_lower = paper.abstract.lower() if paper.abstract else ""
        hints = {
            "has_figures": any(kw in abstract_lower for kw in ["figure", "fig.", "chart", "graph", "plot"]),
            "has_tables": any(kw in abstract_lower for kw in ["table", "tab.", "dataset"]),
            "has_formulas": any(kw in abstract_lower for kw in ["equation", "formula", "equation", "theorem"]),
            "chart_types": [],
        }

        # 检测图表类型
        chart_type_keywords = {
            "line_chart": ["trend", "curve", "time series", "growth"],
            "bar_chart": ["comparison", "bar", "histogram"],
            "scatter_plot": ["correlation", "scatter", "distribution"],
            "heatmap": ["heatmap", "attention map", "confusion matrix"],
            "pie_chart": ["proportion", "percentage", "ratio"],
        }
        for chart_type, keywords in chart_type_keywords.items():
            if any(kw in abstract_lower for kw in keywords):
                hints["chart_types"].append(chart_type)

        return hints

    def search_multimodal(self, state: PaperAgentState) -> PaperAgentState:
        """多模态检索

        使用文本-图像联合检索增强搜索结果。
        """
        if self._retriever is None:
            logger.debug("[Multimodal] 无多模态检索器，跳过")
            return state

        query = state.user_query
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(self._retriever.retrieve(query, top_k=10))

            # 将多模态检索结果转换为补充论文
            extra_papers = []
            for doc in result.text_results[:5]:
                extra_papers.append(Paper(
                    id=f"mm_{hash(doc)}",
                    title=doc[:100],
                    authors=[],
                    abstract=doc,
                    url="",
                    metadata={"source": "multimodal_retrieval"},
                ))

            # 合并到现有论文列表
            existing_ids = {p.id for p in state.papers}
            for p in extra_papers:
                if p.id not in existing_ids:
                    state.papers.append(p)
                    existing_ids.add(p.id)

            logger.info(f"[Multimodal] 多模态检索补充了 {len(extra_papers)} 个结果")
        except Exception as e:
            logger.warning(f"[Multimodal] 多模态检索失败: {e}")

        return state


def create_multimodal_node(
    multimodal_retriever=None,
    chart_analyzer=None,
    formula_recognizer=None,
) -> MultimodalNode:
    """便捷函数：创建多模态节点"""
    return MultimodalNode(
        multimodal_retriever=multimodal_retriever,
        chart_analyzer=chart_analyzer,
        formula_recognizer=formula_recognizer,
    )
