"""
LiteratureAgent - 文献工作Agent

职责：
- 多源文献搜索
- 质量筛选
- PDF阅读与信息提取
- 识别研究空白
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

import json

import asyncio

from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig
from ..paper_search.paper_search import PaperSearchAgent
from ..storage.paper_db import get_paper_db as get_db
from ..unified.error_handler import log_error_with_context
from ..unified.pydantic_validator import parse_json

logger = get_logging_logger(__name__)


class LiteratureAgent(PaperAgentBase):
    """
    LiteratureAgent - 文献收集与综述

    职责：
    - 多源文献搜索
    - 质量筛选
    - PDF阅读与信息提取
    - 识别研究空白
    """

    # Few-shot示例 - 文献工作的期望输出格式
    FEW_SHOT_EXAMPLES = """

## 文献综述输出格式示例

【示例1：高质量文献摘要】
输入：搜索"深度学习医学图像分割"相关文献
输出：
{
    "papers": [
        {
            "title": "Attention U-Net: Learning Where to Look for the Pancreas",
            "authors": "Oktay et al.",
            "year": 2018,
            "venue": "MIDL",
            "impact": "高（被引5000+）",
            "key_contribution": "提出Attention Gate机制，增强模型对目标区域的关注",
            "relevance": 0.95,
            "limitations": "在极端尺度器官上效果有限"
        }
    ],
    "research_gaps": [
        "现有方法在少样本场景下效果不佳",
        "跨模态（CT/MRI）泛化性研究较少"
    ]
}

【示例2：研究空白识别】
输入：分析"目标检测"领域的研究空白
输出：
{
    "identified_gaps": [
        {
            "gap": "小目标检测精度低",
            "severity": "高",
            "opportunity": "提出针对小目标的特征融合策略"
        },
        {
            "gap": "实时性与精度的矛盾",
            "severity": "中",
            "opportunity": "轻量化网络设计"
        }
    ]
}
"""

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个专业的学术文献研究员。
你的职责是：
1. 高效搜索相关文献
2. 筛选高质量论文
3. 深度阅读并提取关键信息
4. 识别研究空白和机会

请确保：
- 搜索全面，不遗漏重要工作
- 筛选严格，只保留高质量文献
- 提取信息准确、结构化""" + """
- 优先选择顶会/顶刊论文
- 关注近3-5年的最新工作
- 识别文献之间的关联和差异""" + self.FEW_SHOT_EXAMPLES
        super().__init__(
            name="literature_agent",
            llm_config=llm_config,
            description="文献搜索、筛选与综述",
            system_prompt=system_prompt
        )
        # 使用真实的论文搜索Agent
        self.search_agent = PaperSearchAgent()

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        执行文献工作

        Args:
            input_data: 包含topic的字典
            context: 执行上下文（包含topic信息）
        """
        topic = input_data.get("topic", "")
        research_question = ""

        # 从context获取更多信息
        if context:
            research_question = context.get("research_question", "")
            if not topic:
                topic = context.get("topic", "")

        if not topic:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Empty topic"
            )

        try:
            # 1. 多角度搜索查询 (30秒超时)
            search_queries = await asyncio.wait_for(
                self._generate_search_queries(topic, research_question),
                timeout=30.0
            )
            self.logger.info(f"[Literature] 生成 {len(search_queries)} 个搜索查询")

            # 2. 多引擎并行搜索 (180秒超时，因为arXiv API可能限流)
            all_papers = await asyncio.wait_for(
                self._multi_engine_search(search_queries),
                timeout=180.0
            )
            self.logger.info(f"[Literature] 搜索到 {len(all_papers)} 篇论文")

            if not all_papers:
                return AgentOutput(
                    success=True,
                    result={"papers": [], "paper_analyses": [], "research_gaps": [], "search_queries": search_queries, "total_found": 0, "total_analyzed": 0},
                    agent_name=self.name,
                    reasoning="No papers found",
                    quality_score=0.0
                )

            # 3. 质量筛选与排序 (180秒超时，增加到180s因为LLM调用可能较慢)
            try:
                ranked_papers = await asyncio.wait_for(
                    self._rank_papers(topic, all_papers),
                    timeout=180.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("[Literature] _rank_papers 超时，尝试返回已排序的论文")
                # 超时时返回原始论文列表（不做排序）
                ranked_papers = all_papers[:30] if len(all_papers) > 30 else all_papers
            self.logger.info(f"[Literature] 排序后 {len(ranked_papers)} 篇论文")

            # 4. 深度阅读 (300秒超时，处理20篇论文需要更长时间)
            try:
                paper_analyses = await asyncio.wait_for(
                    self._deep_read(ranked_papers[:15]),  # 减少到15篇加快速度
                    timeout=300.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("[Literature] _deep_read 超时，返回空分析")
                paper_analyses = []
            self.logger.info(f"[Literature] 深度阅读完成，获得 {len(paper_analyses) if paper_analyses else 0} 个分析")

            # 5. 识别研究空白 (60秒超时，增加到60s)
            try:
                gaps = await asyncio.wait_for(
                    self._identify_gaps(paper_analyses, topic, research_question),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("[Literature] _identify_gaps 超时，返回空研究空白")
                gaps = []

            return AgentOutput(
                success=True,
                result={
                    "papers": ranked_papers,
                    "paper_analyses": paper_analyses or [],
                    "research_gaps": gaps or [],
                    "search_queries": search_queries,
                    "total_found": len(all_papers),
                    "total_analyzed": len(paper_analyses) if paper_analyses else 0
                },
                agent_name=self.name,
                reasoning=f"Collected {len(ranked_papers)} papers, analyzed {len(paper_analyses) if paper_analyses else 0}, identified {len(gaps) if gaps else 0} gaps",
                quality_score=min(1.0, (len(paper_analyses) if paper_analyses else 0) / 15)
            )

        except asyncio.TimeoutError as e:
            self.logger.error(f"[Literature] 操作超时: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=f"Operation timeout: {str(e)}"
            )
        except Exception as e:
            log_error_with_context(self.logger, e, "LiteratureAgent execution", recovered=True)
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _generate_search_queries(
        self,
        topic: str,
        research_question: str = ""
    ) -> List[Dict[str, str]]:
        """生成多角度搜索查询"""
        prompt = f"""
为以下研究主题生成多个搜索角度：

主题：{topic}
研究问题：{research_question}

请生成8-12个不同角度的搜索查询，每个查询应：
1. 覆盖不同的子主题或方面
2. 使用不同的关键词组合
3. 包含同义词和相关术语

输出JSON格式：
{{
    "queries": [
        {{"query": "搜索查询内容", "strategy": "基础/扩展/验证", "aspect": "方法/应用/趋势/背景"}},
        ...
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = parse_json(response)
            if data is None:
                return [{"query": topic, "strategy": "基础", "aspect": "综合"}]
            return data.get("queries", [{"query": topic, "strategy": "基础", "aspect": "综合"}])
        except Exception as e:
            log_error_with_context(self.logger, e, "Query generation", recovered=True)
            return [{"query": topic, "strategy": "基础", "aspect": "综合"}]

    async def _multi_engine_search(self, queries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """多引擎并行搜索 - 使用真实API + 本地缓存"""
        # 优先从本地数据库查找已存在的论文
        db = get_db()
        local_papers_map = {}  # title -> paper 用于快速去重

        async def search_single(query_obj: Dict[str, str]) -> List[Dict[str, Any]]:
            query = query_obj.get("query", "")
            source = "all"
            # 根据策略选择数据源
            strategy = query_obj.get("strategy", "基础")
            if strategy == "扩展":
                source = "arxiv"  # 扩展搜索优先arXiv
            elif strategy == "验证":
                source = "pubmed"  # 验证搜索优先PubMed

            try:
                result = await self.search_agent.execute(
                    query,
                    {"source": source, "time_range": 365, "max_results": 10}
                )
                papers = result.get("papers", [])
                # 过滤掉本地已存在的论文（通过title去重）
                new_papers = []
                for p in papers:
                    title_lower = p.get("title", "").lower().strip()
                    if title_lower and title_lower not in local_papers_map:
                        local_papers_map[title_lower] = p
                        p["relevance_score"] = 0.8  # 默认相关性
                        new_papers.append(p)
                return new_papers
            except Exception as e:
                logger.error(f"Search failed for query '{query}': {e}")
                return []

        # Fallback 搜索：当主搜索失败时尝试其他平台
        async def fallback_search(query: str) -> List[Dict[str, Any]]:
            """通过 SearchFactory 多平台 fallback（直接使用各搜索器）"""
            try:
                from ...search.search_factory import SearchFactory
                from ...search.base_searcher import SearchResponse

                # 直接使用各平台搜索器（SearchFactory 会自动创建）
                searcher_names = ["openalex", "arxiv", "semantic_scholar", "pubmed", "crossref"]
                fallback_papers = []
                semaphore = asyncio.Semaphore(2)

                async def search_one(name: str) -> List[Dict[str, Any]]:
                    async with semaphore:
                        try:
                            searcher = SearchFactory.get(name)
                            if not searcher:
                                return []
                            result = await asyncio.wait_for(
                                searcher.search(query, 5),
                                timeout=8.0
                            )
                            if isinstance(result, SearchResponse):
                                papers = []
                                for r in result.results:
                                    paper_dict = {
                                        "paper_id": r.paper_id,
                                        "title": r.title,
                                        "abstract": r.abstract,
                                        "authors": r.authors or [],
                                        "year": r.year,
                                        "url": r.url,
                                        "source": name,
                                        "citations": r.citations,
                                        "relevance_score": 0.8
                                    }
                                    title_lower = paper_dict.get("title", "").lower().strip()
                                    if title_lower and title_lower not in local_papers_map:
                                        local_papers_map[title_lower] = paper_dict
                                        papers.append(paper_dict)
                                return papers
                            return []
                        except Exception as e:
                            logger.warning(f"Fallback {name} search failed for '{query}': {e}")
                            return []

                # 并行搜索多个平台
                results = await asyncio.gather(*[search_one(n) for n in searcher_names], return_exceptions=True)
                for papers in results:
                    if isinstance(papers, list):
                        fallback_papers.extend(papers)

                if fallback_papers:
                    logger.info(f"Fallback search found {len(fallback_papers)} papers for '{query}'")
                return fallback_papers
            except Exception as e:
                logger.warning(f"Fallback search failed for '{query}': {e}")
                return []

        # 并行搜索（限制并发数）
        semaphore = asyncio.Semaphore(3)
        async def bounded_search(q):
            async with semaphore:
                return await search_single(q)

        tasks = [bounded_search(q) for q in queries[:8]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果（使用local_papers_map已去重）
        all_papers = list(local_papers_map.values())

        # 如果没有找到论文，触发 fallback 多平台搜索
        if not all_papers:
            logger.warning("主搜索未找到论文，触发 fallback 多平台搜索")
            fallback_tasks = [fallback_search(q.get("query", "")) for q in queries[:4]]
            fallback_results = await asyncio.gather(*fallback_tasks, return_exceptions=True)
            for papers in fallback_results:
                if isinstance(papers, list):
                    all_papers.extend(papers)

        # 如果本地已有相关论文，打印日志
        if all_papers:
            logger.info(f"搜索完成，返回 {len(all_papers)} 篇去重后的论文")

        return all_papers

    async def _rank_papers(self, topic: str, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """排序论文 - 并行批处理"""
        if not papers:
            return []

        # 限制排序数量，最多30篇，避免超时
        papers_to_rank = papers[:30] if len(papers) > 30 else papers

        # 分批处理：每批5篇，减少token消耗和延迟
        batch_size = 5
        batches = [papers_to_rank[i:i+batch_size] for i in range(0, len(papers_to_rank), batch_size)]

        async def rank_batch(batch: List[Dict[str, Any]], batch_idx: int) -> List[Dict[str, Any]]:
            """对单批论文排序"""
            prompt = f"""对以下论文进行相关性排序（相对于主题：{topic}）。

论文列表：{json.dumps([{"idx": i, "title": p.get("title", ""), "abstract": p.get("abstract", "")[:200]} for i, p in enumerate(batch)], ensure_ascii=False)}

请按相关性排序，输出JSON格式：
{{"ranked": [{{"original_index": 0, "rank": 1, "reason": "原因"}}]}}
只输出JSON，不要其他内容。"""
            try:
                response = await self._llm_call(prompt)
                data = parse_json(response)
                if data is None:
                    return [{"original_index": i, "rank": i+1} for i in range(len(batch))]
                return data.get("ranked", [{"original_index": i, "rank": i+1} for i in range(len(batch))])
            except Exception as e:
                log_error_with_context(self.logger, e, f"Batch ranking", recovered=True)
                return [{"original_index": i, "rank": i+1} for i in range(len(batch))]

        # 并行处理所有批次
        results = await asyncio.gather(*[rank_batch(b, i) for i, b in enumerate(batches)])

        # 合并结果
        all_ranked = []
        for batch_result in results:
            all_ranked.extend(batch_result)

        # 创建排序映射
        rank_map = {r["original_index"]: r["rank"] for r in all_ranked}

        # 重新排序
        indexed_papers = list(enumerate(papers_to_rank))
        sorted_papers = sorted(indexed_papers, key=lambda x: rank_map.get(x[0], 999))

        # 如果原论文列表被截断，需要映射回原始位置
        if len(papers) > len(papers_to_rank):
            # 排序后的论文需要插入到原始列表的正确位置
            sorted_titles = {p.get("title", "").lower() for _, p in sorted_papers}
            remaining = [p for p in papers[len(papers_to_rank):] if p.get("title", "").lower() not in sorted_titles]
            # 按原始顺序拼接（排序的 + 未排序的）
            return [p for _, p in sorted_papers] + remaining

        return [p for _, p in sorted_papers]

    async def _deep_read(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """深度阅读论文 - 并行处理"""
        semaphore = asyncio.Semaphore(3)  # 限制并发数为3

        async def process_one(paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            async with semaphore:
                try:
                    return await self._extract_paper_info(paper)
                except Exception as e:
                    log_error_with_context(self.logger, e, "Paper analysis", recovered=True)
                    return None

        results = await asyncio.gather(*[process_one(p) for p in papers])
        return [r for r in results if r is not None]

    async def _extract_paper_info(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """提取论文关键信息"""
        prompt = f"""分析以下论文，提取关键信息：

论文标题：{paper.get('title', '')}
摘要：{paper.get('abstract', '')[:800]}

请提取以下信息，输出JSON格式：
{{
    "paper_id": "论文ID或简短标识",
    "title": "标题",
    "core_problem": "核心研究问题",
    "key_methodology": "主要方法",
    "key_findings": "主要发现",
    "limitations": "局限性"
}}

严格只输出JSON。"""
        try:
            response = await self._llm_call(prompt)
            data = parse_json(response)
            if data is None:
                return {
                    "paper_id": paper.get("title", "unknown"),
                    "title": paper.get("title", ""),
                    "core_problem": "Unknown",
                    "key_methodology": "Unknown",
                    "key_findings": "Unknown",
                    "limitations": "Unknown"
                }
            return data
        except Exception as e:
            log_error_with_context(self.logger, e, "Paper info extraction", recovered=True)
            return {
                "paper_id": paper.get("title", "unknown"),
                "title": paper.get("title", ""),
                "core_problem": "Unknown",
                "key_methodology": "Unknown",
                "key_findings": "Unknown",
                "limitations": "Unknown"
            }

    async def _identify_gaps(
        self,
        paper_analyses: List[Dict[str, Any]],
        topic: str,
        research_question: str = ""
    ) -> List[Dict[str, str]]:
        """识别研究空白"""
        if not paper_analyses:
            return [{"description": "需要更多文献分析", "evidence": "", "potential_direction": "扩大搜索范围"}]

        # 过滤掉 None 值
        valid_analyses = [pa for pa in paper_analyses if pa is not None]
        if not valid_analyses:
            return [{"description": "需要更多文献分析", "evidence": "", "potential_direction": "扩大搜索范围"}]

        # 简化论文分析内容，减少token消耗
        simplified = []
        for pa in valid_analyses[:10]:  # 最多10篇
            simplified.append({
                "title": (pa.get("title") or "Unknown")[:100],
                "core_problem": (pa.get("core_problem") or "Unknown")[:200],
                "key_findings": (pa.get("key_findings") or "")[:200] if isinstance(pa.get("key_findings"), str) else ", ".join(pa.get("key_findings") or [])[:200],
                "limitations": (pa.get("limitations") or "Unknown")[:150]
            })

        prompt = f"""基于以下论文分析，识别3-5个研究空白。

主题：{topic}
研究问题：{research_question}

论文分析：
{json.dumps(simplified, ensure_ascii=False, indent=2)}

请识别3-5个研究空白，输出JSON格式：
{{
    "gaps": [
        {{
            "description": "gap描述",
            "evidence": "支持gap的论文列表",
            "potential_directions": ["方向1", "方向2"]
        }}
    ]
}}

严格只输出JSON，不要其他内容。"""
        try:
            response = await self._llm_call(prompt)
            data = parse_json(response)
            if data is None:
                return [{"description": "研究空白识别失败", "evidence": "", "potential_direction": "请检查输入数据"}]
            gaps = data.get("gaps", [])
            return gaps if gaps else [{"description": "未识别到研究空白", "evidence": "", "potential_direction": "扩大文献搜索范围"}]
        except Exception as e:
            log_error_with_context(self.logger, e, "Research gap identification", recovered=True)
            return [{"description": "研究空白识别出错", "evidence": "", "potential_direction": str(e)}]
