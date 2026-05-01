"""
问答搜索节点 - QA Search Node

功能：
1. 根据问题类型搜索相关论文
2. 复用现有的 PaperSearchAgent 和 QueryRouter
3. 支持基础查询、比较分析、前沿追踪等模式

设计原则：
- 复用 qa/paper_search.py 和 qa/query_router.py
- 根据问题类型调整搜索策略
- 为问答生成提供相关论文
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class QASearchNode:
    """问答搜索节点 - 为问答搜索相关论文"""

    def __init__(self):
        """初始化问答搜索节点"""
        from ...paper_search.paper_search import PaperSearchAgent
        from ...paper_search.query_router import QueryRouter

        self.search_agent = PaperSearchAgent()
        self.query_router = QueryRouter()

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行问答论文���索

        Args:
            state: 当前状态，需包含 user_query

        Returns:
            更新后的状态，添加 papers 和 question_type 字段
        """
        user_query = state.get("user_query", "")

        if not user_query:
            logger.warning("No query for QA search")
            state["papers"] = []
            return state

        try:
            # 使用 QueryRouter 识别问题类型
            routing_decision = self.query_router.decide_with_rules(user_query)
            question_type = routing_decision.question_type
            route = routing_decision.route

            state["question_type"] = question_type
            state["qa_route"] = route

            # 根据路由选择搜索源
            search_source = self._map_route_to_source(route)

            # 执行搜索
            search_params = {
                "source": search_source,
                "max_results": 20
            }

            result = await self.search_agent.execute(user_query, search_params)

            # 更新状态
            papers = result.get("papers", [])
            state["papers"] = papers
            state["qa_search_count"] = len(papers)

            logger.info(
                f"QA search completed: {len(papers)} papers found "
                f"for question type '{question_type}'"
            )

        except Exception as e:
            logger.error(f"QA search failed: {e}")
            state["papers"] = []
            state["question_type"] = "BASIC_QUERY"
            state.setdefault("errors", []).append(f"QA search error: {str(e)}")

        return state

    def _map_route_to_source(self, route: str) -> str:
        """将路由映射到搜索源"""
        route_source_map = {
            "knowledge_base": "all",
            "paper_search": "all",
            "arxiv_search": "arxiv",
            "pubmed_search": "pubmed"
        }
        return route_source_map.get(route, "all")
