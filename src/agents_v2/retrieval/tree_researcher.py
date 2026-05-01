"""
Tree-Deep Researcher - GPT Researcher 式树状深度研究

借鉴 GPT Researcher 的核心设计：
1. Sub-question Decomposition：将研究问题分解为子问题
2. Recursive Exploration：对每个子问题递归搜索和提取
3. Aggregation：聚合所有分支的结果生成最终报告

使用示例:
    from agents_v2.retrieval.tree_researcher import TreeResearcher

    researcher = TreeResearcher(llm_provider=my_llm)
    report = await researcher.research(
        query="深度学习在医疗影像中的应用",
        max_depth=2,
        max_sub_questions=3,
    )
    print(report.summary)
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ResearchNodeType(str, Enum):
    """研究节点类型"""
    ROOT = "root"           # 根节点（原始问题）
    BRANCH = "branch"       # 分支节点（子问题）
    LEAF = "leaf"           # 叶子节点（最终搜索结果）


@dataclass
class SearchResult:
    """单条搜索结果"""
    title: str
    snippet: str
    url: str = ""
    source: str = ""
    relevance_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "snippet": self.snippet,
            "url": self.url,
            "source": self.source,
            "relevance_score": self.relevance_score,
        }


@dataclass
class ResearchNode:
    """研究树节点"""
    node_id: str
    question: str
    node_type: ResearchNodeType
    depth: int
    parent_id: Optional[str] = None
    sub_questions: List[str] = field(default_factory=list)
    search_results: List[SearchResult] = field(default_factory=list)
    summary: str = ""
    status: str = "pending"  # pending/searching/synthesizing/done/failed

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "question": self.question,
            "node_type": self.node_type.value,
            "depth": self.depth,
            "parent_id": self.parent_id,
            "sub_questions": self.sub_questions,
            "search_results_count": len(self.search_results),
            "summary": self.summary,
            "status": self.status,
        }


@dataclass
class ResearchReport:
    """研究报告"""
    query: str
    summary: str
    key_findings: List[str] = field(default_factory=list)
    sources: List[SearchResult] = field(default_factory=list)
    research_tree: List[ResearchNode] = field(default_factory=list)
    total_searches: int = 0
    total_depth: int = 0
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "sources_count": len(self.sources),
            "total_searches": self.total_searches,
            "total_depth": self.total_depth,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "tree_nodes": len(self.research_tree),
        }


class TreeResearcher:
    """树状深度研究器

    实现 GPT Researcher 式的研究流程：
    1. 将研究问题分解为子问题（广度优先）
    2. 对每个子问题进行搜索和信息提取（深度优先）
    3. 如果深度未达上限，递归分解子问题
    4. 聚合所有搜索结果生成最终报告

    Args:
        llm_provider: LLM 调用函数（async callable）
        search_fn: 搜索函数（async callable，接受 query 返回 SearchResult 列表）
        max_depth: 最大递归深度（默认 2）
        max_sub_questions: 每层最大子问题数（默认 3）
        max_results_per_search: 每次搜索最大结果数（默认 5）
    """

    def __init__(
        self,
        llm_provider: Optional[Callable] = None,
        search_fn: Optional[Callable] = None,
        max_depth: int = 2,
        max_sub_questions: int = 3,
        max_results_per_search: int = 5,
    ):
        self.llm_provider = llm_provider
        self.search_fn = search_fn
        self.max_depth = max_depth
        self.max_sub_questions = max_sub_questions
        self.max_results_per_search = max_results_per_search
        self._node_counter = 0

    def _next_node_id(self) -> str:
        self._node_counter += 1
        return f"node_{self._node_counter}"

    async def research(
        self,
        query: str,
        max_depth: Optional[int] = None,
        max_sub_questions: Optional[int] = None,
    ) -> ResearchReport:
        """执行树状深度研究

        Args:
            query: 研究问题
            max_depth: 覆盖默认最大深度
            max_sub_questions: 覆盖默认最大子问题数

        Returns:
            ResearchReport: 研究报告
        """
        start_time = time.time()
        depth = max_depth or self.max_depth
        sub_q_count = max_sub_questions or self.max_sub_questions

        logger.info(f"TreeResearcher: starting research on '{query}' (depth={depth}, sub_q={sub_q_count})")

        # 构建研究树
        all_nodes = []
        all_sources = []
        total_searches = 0

        # 创建根节点
        root = ResearchNode(
            node_id=self._next_node_id(),
            question=query,
            node_type=ResearchNodeType.ROOT,
            depth=0,
        )
        all_nodes.append(root)

        # 递归研究
        await self._recursive_research(root, depth, sub_q_count, all_nodes, all_sources)
        total_searches = sum(1 for n in all_nodes if n.search_results)

        # 聚合生成报告
        summary = await self._synthesize_report(query, all_nodes, all_sources)

        elapsed = time.time() - start_time
        logger.info(f"TreeResearcher: done in {elapsed:.1f}s, {total_searches} searches, {len(all_nodes)} nodes")

        return ResearchReport(
            query=query,
            summary=summary,
            key_findings=self._extract_key_findings(all_nodes),
            sources=all_sources,
            research_tree=all_nodes,
            total_searches=total_searches,
            total_depth=depth,
            elapsed_seconds=elapsed,
        )

    async def _recursive_research(
        self,
        node: ResearchNode,
        remaining_depth: int,
        max_sub_q: int,
        all_nodes: List[ResearchNode],
        all_sources: List[SearchResult],
    ):
        """递归研究一个节点

        Args:
            node: 当前研究节点
            remaining_depth: 剩余递归深度
            max_sub_q: 最大子问题数
            all_nodes: 所有节点列表（累加）
            all_sources: 所有来源列表（累加）
        """
        node.status = "searching"
        logger.debug(f"TreeResearcher: researching node {node.node_id} (depth={node.depth}): {node.question[:50]}...")

        # Step 1: 搜索当前问题
        results = await self._search(node.question)
        node.search_results = results[:self.max_results_per_search]
        all_sources.extend(node.search_results)

        # Step 2: 生成当前节点的摘要
        if node.search_results:
            node.summary = await self._summarize_results(node.question, node.search_results)

        # Step 3: 如果还有深度，分解子问题
        if remaining_depth > 0 and node.search_results:
            node.status = "synthesizing"
            sub_questions = await self._decompose_question(
                node.question, node.search_results, max_sub_q
            )
            node.sub_questions = sub_questions

            # 对每个子问题创建子节点并递归研究
            child_tasks = []
            for sq in sub_questions:
                child = ResearchNode(
                    node_id=self._next_node_id(),
                    question=sq,
                    node_type=ResearchNodeType.BRANCH if remaining_depth > 1 else ResearchNodeType.LEAF,
                    depth=node.depth + 1,
                    parent_id=node.node_id,
                )
                all_nodes.append(child)
                child_tasks.append(
                    self._recursive_research(child, remaining_depth - 1, max_sub_q, all_nodes, all_sources)
                )

            # 并发执行子研究（最多 3 个并发）
            semaphore = asyncio.Semaphore(3)

            async def _limited(task):
                async with semaphore:
                    await task

            await asyncio.gather(*[_limited(t) for t in child_tasks], return_exceptions=True)

        node.status = "done"

    async def _search(self, query: str) -> List[SearchResult]:
        """执行搜索

        Args:
            query: 搜索查询

        Returns:
            List[SearchResult]
        """
        if self.search_fn:
            try:
                results = await self.search_fn(query)
                if isinstance(results, list):
                    return results
                return []
            except Exception as e:
                logger.warning(f"TreeResearcher: search failed for '{query[:30]}': {e}")
                return []

        # 无搜索函数时返回空结果
        return []

    async def _decompose_question(
        self,
        question: str,
        search_results: List[SearchResult],
        max_sub_q: int,
    ) -> List[str]:
        """将研究问题分解为子问题

        Args:
            question: 原始问题
            search_results: 已有的搜索结果
            max_sub_q: 最大子问题数

        Returns:
            List[str]: 子问题列表
        """
        if not self.llm_provider:
            return self._rule_based_decompose(question, max_sub_q)

        # 构建搜索结果摘要
        results_text = "\n".join(
            f"- {r.title}: {r.snippet[:100]}"
            for r in search_results[:5]
        )

        prompt = f"""你是一位学术研究助手。基于以下研究问题和已有的搜索结果，生成 {max_sub_q} 个更具体的子问题，以便深入探索该主题。

研究问题：{question}

已有搜索结果：
{results_text}

请生成 {max_sub_q} 个具体的子问题，每个子问题应该：
1. 聚焦于研究问题的某个特定方面
2. 可以通过学术搜索找到答案
3. 与已有搜索结果互补（避免重复）

以 JSON 数组格式返回，只返回问题列表：
["子问题1", "子问题2", "子问题3"]"""

        try:
            response = await self.llm_provider(prompt)
            import json
            # 解析响应
            content = response.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            questions = json.loads(content)
            if isinstance(questions, list):
                return [str(q) for q in questions[:max_sub_q]]
        except Exception as e:
            logger.warning(f"TreeResearcher: LLM decompose failed: {e}")

        return self._rule_based_decompose(question, max_sub_q)

    def _rule_based_decompose(self, question: str, max_sub_q: int) -> List[str]:
        """基于规则的问题分解（LLM 不可用时的回退）"""
        # 简单的模板化分解
        aspects = ["方法和技术", "应用场景", "挑战和局限性", "最新进展", "未来方向"]
        sub_questions = []
        for aspect in aspects[:max_sub_q]:
            sub_questions.append(f"{question} - {aspect}")
        return sub_questions

    async def _summarize_results(
        self,
        question: str,
        results: List[SearchResult],
    ) -> str:
        """总结搜索结果

        Args:
            question: 研究问题
            results: 搜索结果

        Returns:
            str: 摘要文本
        """
        if not self.llm_provider:
            # 无 LLM 时简单拼接
            snippets = [r.snippet[:150] for r in results[:3]]
            return " ".join(snippets)

        results_text = "\n".join(
            f"[{i+1}] {r.title}: {r.snippet}"
            for i, r in enumerate(results)
        )

        prompt = f"""请总结以下关于"{question}"的搜索结果，提取关键信息：

{results_text}

请用 2-3 句话总结关键发现。只返回总结文本，不要额外格式。"""

        try:
            response = await self.llm_provider(prompt)
            return response.strip()
        except Exception as e:
            logger.warning(f"TreeResearcher: summarize failed: {e}")
            snippets = [r.snippet[:100] for r in results[:2]]
            return " ".join(snippets)

    async def _synthesize_report(
        self,
        query: str,
        all_nodes: List[ResearchNode],
        all_sources: List[SearchResult],
    ) -> str:
        """聚合所有研究结果生成最终报告

        Args:
            query: 原始研究问题
            all_nodes: 所有研究节点
            all_sources: 所有来源

        Returns:
            str: 最终报告文本
        """
        if not self.llm_provider:
            # 无 LLM 时聚合所有摘要
            summaries = [n.summary for n in all_nodes if n.summary]
            return "\n\n".join(summaries) if summaries else "未找到相关信息。"

        # 构建研究树摘要
        tree_summaries = []
        for node in all_nodes:
            if node.summary:
                prefix = "  " * node.depth
                tree_summaries.append(f"{prefix}- [{node.question}]: {node.summary}")

        tree_text = "\n".join(tree_summaries)

        prompt = f"""你是一位学术研究专家。请基于以下研究结果，生成一份关于"{query}"的综合研究报告。

研究结果：
{tree_text}

请生成一份结构化的研究报告，包含：
1. 概述（2-3句话）
2. 主要发现（3-5个要点）
3. 结论

只返回报告文本，不要额外格式。"""

        try:
            response = await self.llm_provider(prompt)
            return response.strip()
        except Exception as e:
            logger.warning(f"TreeResearcher: synthesize failed: {e}")
            summaries = [n.summary for n in all_nodes if n.summary]
            return "\n\n".join(summaries) if summaries else "报告生成失败。"

    def _extract_key_findings(self, all_nodes: List[ResearchNode]) -> List[str]:
        """从研究树中提取关键发现"""
        findings = []
        for node in all_nodes:
            if node.summary and node.depth <= 1:
                findings.append(node.summary)
        return findings[:5]


# 便捷函数
async def tree_research(
    query: str,
    llm_provider: Optional[Callable] = None,
    search_fn: Optional[Callable] = None,
    max_depth: int = 2,
    max_sub_questions: int = 3,
) -> ResearchReport:
    """便捷树状研究函数"""
    researcher = TreeResearcher(
        llm_provider=llm_provider,
        search_fn=search_fn,
        max_depth=max_depth,
        max_sub_questions=max_sub_questions,
    )
    return await researcher.research(query)
