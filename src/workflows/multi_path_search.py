"""多路径冗余搜索 - Multi-Path Redundant Search

允许多个搜索引擎并行搜索，结果合并后进行评估和选择。
支持：
1. 多引擎并行搜索
2. 引擎级联失败（一个失败切换到另一个）
3. 结果合并与去重
4. 基于质量的路由
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SearchEngine(str, Enum):
    """支持的搜索引擎枚举"""
    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    GOOGLE_SCHOLAR = "google_scholar"
    LOCAL_DB = "local_db"
    MCP_SERVER = "mcp_server"


@dataclass
class SearchResult:
    """搜索结果封装"""
    engine: str
    papers: List[Dict[str, Any]]
    success: bool
    error: Optional[str] = None
    score: float = 1.0
    duration: float = 0.0


@dataclass
class RedundantSearchConfig:
    """冗余搜索配置"""
    # 并行搜索的引擎列表
    engines: List[SearchEngine] = None
    # 达到多少个引擎成功就停止等待
    quorum_size: int = 2
    # 单个引擎超时时间
    engine_timeout: float = 30.0
    # 合并结果时保留每个引擎的数量
    top_k_per_engine: int = 20
    # 最终输出数量
    final_top_k: int = 30
    # 是否启用级联失败（一个引擎失败自动启用备用引擎）
    cascade_enabled: bool = True


class SearchEngineAdapter:
    """搜索引擎适配器基类"""

    def __init__(self, engine: SearchEngine):
        self.engine = engine

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """执行搜索，返回论文列表"""
        raise NotImplementedError

    async def health_check(self) -> bool:
        """健康检查"""
        raise NotImplementedError


class MCPEngineAdapter(SearchEngineAdapter):
    """MCP服务器搜索适配器"""

    def __init__(self, mcp_client=None):
        super().__init__(SearchEngine.MCP_SERVER)
        self.mcp_client = mcp_client

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """通过MCP服务器搜索"""
        try:
            from src.core.model import llm
            from langchain_mcp_adapters.client import MultiServerMCPClient
            from langchain_core.messages import HumanMessage

            if self.mcp_client is None:
                from utils.mcp_utils import mcp_server_config
                self.mcp_client = MultiServerMCPClient(mcp_server_config)

            tools = await self.mcp_client.get_tools()
            if not tools:
                raise RuntimeError("No MCP tools available")

            # 创建临时agent
            from langgraph.prebuilt import create_react_agent
            agent = create_react_agent(model=llm, tools=tools)

            prompt = f"""
            请搜索以下主题的学术论文，返回JSON格式的论文列表。
            每个论文需要包含：title, abstract, authors, url, published_date, source

            搜索主题：{query}

            直接返回JSON数组，不要其他内容。
            """

            response = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
            content = response["messages"][-1].content

            # 解析JSON
            import json
            try:
                # 尝试提取JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                if not content.startswith("["):
                    start = content.find("[")
                    end = content.rfind("]") + 1
                    if start >= 0:
                        content = content[start:end]

                papers = json.loads(content)
                return papers if isinstance(papers, list) else []
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse MCP search results: {e}")
                return []

        except Exception as e:
            logger.error(f"MCP search failed: {e}")
            raise


class FallbackChain:
    """引擎级联失败链"""

    def __init__(self, adapters: List[SearchEngineAdapter]):
        self.adapters = adapters

    async def search(self, query: str, **kwargs) -> SearchResult:
        """依次尝试每个引擎，直到成功"""
        first_error = None

        for adapter in self.adapters:
            try:
                logger.info(f"Trying engine: {adapter.engine}")
                papers = await asyncio.wait_for(
                    adapter.search(query, **kwargs),
                    timeout=kwargs.get("timeout", 30.0)
                )

                if papers:
                    return SearchResult(
                        engine=adapter.engine.value,
                        papers=papers,
                        success=True
                    )

            except asyncio.TimeoutError:
                logger.warning(f"Engine {adapter.engine} timeout")
                first_error = first_error or Exception(f"{adapter.engine} timeout")

            except Exception as e:
                logger.warning(f"Engine {adapter.engine} failed: {e}")
                first_error = first_error or e
                continue

        return SearchResult(
            engine="all_failed",
            papers=[],
            success=False,
            error=str(first_error)
        )


class RedundantSearcher:
    """冗余搜索器"""

    def __init__(self, config: Optional[RedundantSearchConfig] = None):
        self.config = config or RedundantSearchConfig(
            engines=[SearchEngine.MCP_SERVER, SearchEngine.LOCAL_DB]
        )
        self.adapters: Dict[SearchEngine, SearchEngineAdapter] = {}
        self._init_adapters()

    def _init_adapters(self):
        """初始化适配器"""
        for engine in self.config.engines:
            if engine == SearchEngine.MCP_SERVER:
                self.adapters[engine] = MCPEngineAdapter()
            # 可以扩展更多引擎适配器

    async def parallel_search(self, query: str) -> List[Dict[str, Any]]:
        """
        并行搜索多个引擎，然后合并结果
        """
        if len(self.adapters) == 1:
            # 单引擎，直接搜索
            adapter = list(self.adapters.values())[0]
            try:
                return await adapter.search(query)
            except Exception as e:
                logger.error(f"Single engine search failed: {e}")
                return []

        # 多引擎并行
        tasks = []
        for engine, adapter in self.adapters.items():
            task = self._search_with_timeout(engine, adapter, query)
            tasks.append(task)

        # 等待所有任务完成或达到quorum
        results = await self._wait_for_quorum(tasks)

        # 合并结果
        merged = self._merge_results(results)

        # 如果结果太少，尝试fallback chain
        if len(merged) < 5 and self.config.cascade_enabled:
            fallback_result = await self._fallback_search(query)
            if fallback_result.success and fallback_result.papers:
                merged.extend(fallback_result.papers[:10])

        # 去重和排序
        final = self._deduplicate_and_rank(merged)

        logger.info(f"Parallel search completed: {len(merged)} raw, {len(final)} final")
        return final[: self.config.final_top_k]

    async def _search_with_timeout(
        self,
        engine: SearchEngine,
        adapter: SearchEngineAdapter,
        query: str
    ) -> SearchResult:
        """带超时的搜索"""
        import time
        start = time.time()

        try:
            papers = await asyncio.wait_for(
                adapter.search(query),
                timeout=self.config.engine_timeout
            )

            return SearchResult(
                engine=engine.value,
                papers=papers,
                success=True,
                duration=time.time() - start
            )

        except asyncio.TimeoutError:
            return SearchResult(
                engine=engine.value,
                papers=[],
                success=False,
                error="timeout",
                duration=time.time() - start
            )

        except Exception as e:
            return SearchResult(
                engine=engine.value,
                papers=[],
                success=False,
                error=str(e),
                duration=time.time() - start
            )

    async def _wait_for_quorum(self, tasks: List) -> List[SearchResult]:
        """等待达到quorum数量的成功结果"""
        results = []
        pending = set(tasks)

        while pending and len([r for r in results if r.success]) < self.config.quorum_size:
            done, pending = await asyncio.wait(
                pending,
                timeout=self.config.engine_timeout,
                return_when=asyncio.FIRST_COMPLETED
            )

            for d in done:
                try:
                    result = d.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Task failed: {e}")

        # 等待剩余任务完成（用于收集更多结果）
        if pending:
            remaining, _ = await asyncio.wait(pending, timeout=5.0)
            for d in remaining:
                try:
                    results.append(d.result())
                except Exception:
                    pass

        return results

    def _merge_results(self, results: List[SearchResult]) -> List[Dict[str, Any]]:
        """合并多个引擎的结果"""
        all_papers = []

        for result in results:
            if result.success:
                # 每个引擎最多取top_k
                all_papers.extend(result.papers[:self.config.top_k_per_engine])

        return all_papers

    def _deduplicate_and_rank(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重并按质量排序"""
        seen_titles = set()
        unique_papers = []

        for paper in papers:
            title = paper.get("title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_papers.append(paper)

        # 按相关性分数排序（如果有的话）
        unique_papers.sort(
            key=lambda p: p.get("relevance_score", p.get("final_score", 0)),
            reverse=True
        )

        return unique_papers

    async def _fallback_search(self, query: str) -> SearchResult:
        """级联失败时的备用搜索"""
        logger.info("Attempting fallback search...")

        # 使用所有适配器创建fallback链
        adapters = list(self.adapters.values())
        chain = FallbackChain(adapters)

        return await chain.search(query, timeout=self.config.engine_timeout * 2)


async def redundant_search_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph节点：多路径冗余搜索

    使用并行搜索和fallback机制提高搜索成功率
    """
    query = state.get("query", "")
    if not query:
        state["search_error"] = "Empty query"
        return state

    # 配置搜索器
    config = RedundantSearchConfig(
        engines=[SearchEngine.MCP_SERVER, SearchEngine.LOCAL_DB],
        quorum_size=1,  # 一个引擎成功即可
        final_top_k=50
    )

    searcher = RedundantSearcher(config)

    try:
        papers = await searcher.parallel_search(query)
        state["papers"] = papers
        state["papers_raw_count"] = len(papers)
        logger.info(f"Redundant search completed: {len(papers)} papers")

    except Exception as e:
        logger.error(f"Redundant search failed: {e}")
        state["search_error"] = str(e)
        state["papers"] = []

    return state


# ========== 便捷函数 ==========

def create_multi_engine_search(
    engines: List[SearchEngine] = None,
    quorum_size: int = 1
) -> RedundantSearcher:
    """创建多引擎搜索器"""
    config = RedundantSearchConfig(
        engines=engines or [SearchEngine.MCP_SERVER],
        quorum_size=quorum_size
    )
    return RedundantSearcher(config)