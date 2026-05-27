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
import os
import asyncio
import math

from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig
from src.agents_v2.agents.report.paper_search import PaperSearchAgent
from src.agents_v2.core.storage.paper_db import get_paper_db as get_db
from src.agents_v2.workflow.unified.error_handler import log_error_with_context
from src.agents_v2.workflow.unified.pydantic_validator import parse_json

logger = get_logging_logger(__name__)


def _get_concurrency(env_key: str, default: int) -> int:
    """从环境变量获取并发数配置"""
    try:
        return int(os.getenv(env_key, str(default)))
    except (ValueError, TypeError):
        return default


class LiteratureAgent(PaperAgentBase):
    """
    LiteratureAgent - 文献收集与综述

    职责：
    - 多源文献搜索
    - 质量筛选
    - PDF阅读与信息提取
    - 识别研究空白
    """
    # 并发数环境变量配置
    ENV_FALLBACK_SEARCH_CONCURRENCY = "LITERATURE_FALLBACK_SEARCH_CONCURRENCY"
    ENV_MAIN_SEARCH_CONCURRENCY = "LITERATURE_MAIN_SEARCH_CONCURRENCY"
    ENV_DEEP_READ_CONCURRENCY = "LITERATURE_DEEP_READ_CONCURRENCY"

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

        # 本地嵌入模型（已移除云端API，直接使用本地模型避免限流）
        self._local_embedding_model = None

    def _get_local_embedding_model(self):
        """获取本地嵌入模型（懒加载）"""
        if self._local_embedding_model is None:
            try:
                from src.agents_v2.core.embedding import get_local_embedding_model
                self._local_embedding_model = get_local_embedding_model()
                logger.info("Local embedding model initialized")
            except Exception as e:
                logger.debug(f"Local embedding model init failed: {e}")
        return self._local_embedding_model

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def _keyword_similarity(self, text1: str, text2: str) -> float:
        """基于关键词的简单相似度计算（embedding失败时的后备方案）"""
        if not text1 or not text2:
            return 0.0

        # 简单分词
        import re
        words1 = set(re.findall(r'[\w]+', text1.lower()))
        words2 = set(re.findall(r'[\w]+', text2.lower()))

        # 移除停用词
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                     'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                     'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i',
                     'we', 'they', 'he', 'she', 'it', 'my', 'our', 'their', 'its', 'of',
                     'and', 'et', 'al', 'via', 'using', 'based', 'using', 'method', 'methods'}

        words1 = words1 - stopwords
        words2 = words2 - stopwords

        if not words1 or not words2:
            return 0.0

        # Jaccard 相似度
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union) if union else 0.0

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本嵌入向量 - 直接使用本地模型，不再调用云端API"""
        # 直接使用本地模型，避免云端API限流问题
        local_model = self._get_local_embedding_model()
        if local_model:
            try:
                # 本地模型推理，60秒超时
                embedding = await asyncio.wait_for(
                    asyncio.to_thread(local_model.get_embedding, text),
                    timeout=60.0
                )
                if embedding:
                    return embedding
            except asyncio.TimeoutError:
                logger.warning("Local embedding timeout")
                raise RuntimeError("Embedding 计算超时（30秒），模型推理速度过慢")
            except Exception as e:
                logger.debug(f"Local embedding failed: {e}")

        return None

    async def _compute_paper_relevance(
        self,
        papers: List[Dict[str, Any]],
        topic: str
    ) -> List[Dict[str, Any]]:
        """使用嵌入计算论文与主题的相关性"""
        if not papers:
            return papers

        # 限制处理论文数量，避免耗时过长（增大到50篇以充分利用Diagnostic预计算结果）
        papers_to_process = papers[:50]

        # 获取主题嵌入
        topic_embedding = await self._get_embedding(topic)

        # 使用embedding计算
        semaphore = asyncio.Semaphore(10)

        async def process_paper(paper: Dict[str, Any]) -> tuple:
            async with semaphore:
                try:
                    # 检查是否已有预计算的embedding
                    existing_embedding = paper.get("embedding")
                    if existing_embedding and topic_embedding:
                        similarity = self._cosine_similarity(topic_embedding, existing_embedding)
                        return paper, similarity

                    # 没有预计算embedding，重新计算
                    text_to_embed = f"{paper.get('title', '')} {paper.get('abstract', '')}"
                    embedding = await self._get_embedding(text_to_embed)
                    if embedding:
                        similarity = self._cosine_similarity(topic_embedding, embedding)
                        return paper, similarity
                    raise RuntimeError("Embedding 计算返回 None")
                except Exception as e:
                    logger.debug(f"Paper embedding failed: {e}")
                    raise

        results = await asyncio.gather(*[process_paper(p) for p in papers_to_process], return_exceptions=True)
        scored_papers = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Paper {i} embedding failed: {result}")
                papers_to_process[i]["embedding_relevance"] = 0.0
                scored_papers.append(papers_to_process[i])
            else:
                paper, score = result
                paper["embedding_relevance"] = round(score, 3)
                scored_papers.append(paper)
        scored_papers.sort(key=lambda x: x.get("embedding_relevance", 0), reverse=True)
        # 合并未处理的论文
        return scored_papers + papers[20:]

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
            # 0. 检查是否有 Diagnostic 阶段复用的论文
            diagnostic_papers = context.get("diagnostic_papers", []) if context else []
            search_queries = []  # 初始化，避免后续访问未定义
            self.logger.info(f"[Literature] 收到 Diagnostic 阶段 {len(diagnostic_papers)} 篇论文")

            # 提取 Topic 阶段传递的关键词
            topic_keywords = []
            if context:
                topic_keywords = context.get("topic_keywords", [])
                if topic_keywords:
                    self.logger.info(f"[Literature] 使用 Topic 关键词: {topic_keywords[:5]}...")

            # 优先使用 Diagnostic 论文进行相关性筛选
            if diagnostic_papers:
                self.logger.info(f"[Literature] 使用 Diagnostic 论文进行相似度筛选")
                try:
                    ranked_from_diagnostic = await asyncio.wait_for(
                        self._compute_paper_relevance(diagnostic_papers, topic),
                        timeout=60.0
                    )
                    filtered_diagnostic = [
                        p for p in ranked_from_diagnostic
                        if p.get("embedding_relevance", 0) > 0.5
                    ]
                except asyncio.TimeoutError:
                    self.logger.warning(f"[Literature] Diagnostic 论文相关性排序超时，跳过embedding过滤")
                    filtered_diagnostic = diagnostic_papers  # 超时时使用全部论文
                except Exception as e:
                    self.logger.warning(f"[Literature] 论文相似度计算失败: {e}，使用全部论文")
                    filtered_diagnostic = diagnostic_papers

                self.logger.info(f"[Literature] Diagnostic 论文相似度过滤后: {len(filtered_diagnostic)} 篇 (阈值>0.5)")

                # 如果 Diagnostic 论文足够，直接使用；否则搜索补充
                if len(filtered_diagnostic) >= 15:
                    all_papers = filtered_diagnostic
                    self.logger.info(f"[Literature] Diagnostic 论文数量充足 ({len(all_papers)} 篇)，跳过搜索")
                else:
                    self.logger.info(f"[Literature] Diagnostic 论文不足 ({len(filtered_diagnostic)} < 15)，补充搜索")
                    # 补充搜索
                    search_queries = await asyncio.wait_for(
                        self._generate_search_queries(topic, research_question, context),
                        timeout=30.0
                    )
                    more_papers = await asyncio.wait_for(
                        self._multi_engine_search(search_queries, topic),
                        timeout=120.0
                    )
                    # 合并去重
                    existing_ids = {p.get("id") or p.get("paper_id") or "" for p in filtered_diagnostic}
                    for p in more_papers:
                        pid = p.get("id") or p.get("paper_id") or ""
                        if pid and pid not in existing_ids:
                            filtered_diagnostic.append(p)
                            existing_ids.add(pid)
                    all_papers = filtered_diagnostic
            else:
                # 没有 Diagnostic 论文，正常搜索流程
                # 1. 多角度搜索查询 (30秒超时)
                search_queries = await asyncio.wait_for(
                    self._generate_search_queries(topic, research_question, context),
                    timeout=30.0
                )
                self.logger.info(f"[Literature] 生成 {len(search_queries)} 个搜索查询")

                # 2. 多引擎并行搜索 (120秒超时，arXiv API可能限流)
                all_papers = await asyncio.wait_for(
                    self._multi_engine_search(search_queries, topic),  # 传递原始 topic 用于本地查找
                    timeout=120.0
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

            # 3. 质量筛选与排序：使用嵌入计算相关性
            # 注意：禁止使用关键词匹配后备，embedding 必须成功
            try:
                ranked_papers = await asyncio.wait_for(
                    self._compute_paper_relevance(all_papers, topic),
                    timeout=90.0
                )
            except asyncio.TimeoutError:
                self.logger.warning(f"[Literature] 论文相关性排序超时（90秒），使用原始论文列表")
                ranked_papers = all_papers
            except Exception as e:
                self.logger.warning(f"[Literature] 论文相似度计算失败: {e}，使用原始论文列表")
                ranked_papers = all_papers
            self.logger.info(f"[Literature] 排序后 {len(ranked_papers)} 篇论文")

            # 4. 深度阅读：过滤相关度达标的论文，最多20篇
            # 注意：必须使用 embedding 分数，禁止使用关键词匹配
            high_relevance_papers = []
            has_embedding_scores = any(p.get("embedding_relevance", 0) > 0.5 for p in ranked_papers)

            if not has_embedding_scores:
                self.logger.warning(f"[Literature] 论文缺少 embedding 分数，使用原始列表继续")

            # Embedding模式：阈值0.6（降低阈值确保有足够论文）
            high_relevance_papers = [
                p for p in ranked_papers
                if p.get("embedding_relevance", 0) > 0.6
            ][:20]
            self.logger.info(f"[Literature] Embedding模式，高相关性论文（>0.6）数量: {len(high_relevance_papers)}")

            try:
                # 限制深度阅读论文数量，加速处理
                papers_for_deep_read = high_relevance_papers[:10]
                paper_analyses = await asyncio.wait_for(
                    self._deep_read(papers_for_deep_read),
                    timeout=120.0
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
                reasoning=f"Collected {len(ranked_papers)} papers from multiple sources, analyzed {len(paper_analyses) if paper_analyses else 0}, identified {len(gaps) if gaps else 0} research gaps",
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
        finally:
            # 已移除云端Embedding客户端，无需清理
            pass

    async def _generate_search_queries(
        self,
        topic: str,
        research_question: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """生成多角度搜索查询"""
        # 优先使用 Topic 阶段传递的关键词进行精确搜索
        topic_keywords = []
        if context:
            topic_keywords = context.get("topic_keywords", [])

        keywords_context = ""
        if topic_keywords:
            keywords_context = f"\n\n参考关键词（来自选题阶段）：{', '.join(topic_keywords[:10])}"

        prompt = f"""为以下研究主题生成多个搜索角度：

主题：{topic}
研究问题：{research_question}{keywords_context}

请生成8-12个不同角度的搜索查询，每个查询应：
1. 覆盖不同的子主题或方面
2. 使用不同的关键词组合
3. 包含同义词和相关术语
4. **优先使用上述参考关键词进行精确匹配**

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

    async def _multi_engine_search(self, queries: List[Dict[str, str]], original_topic: str = "") -> List[Dict[str, Any]]:
        """多引擎并行搜索 - 使用真实API + 本地缓存"""
        # 优先从本地数据库查找已存在的论文
        db = get_db()
        local_papers_map = {}  # title -> paper 用于快速去重

        # 先用原始查询（可能是中文）在本地数据库查找
        if original_topic:
            try:
                existing = db.find_by_title(original_topic)
                if existing:
                    logger.info(f"本地数据库找到论文: {existing.title[:50]}...")
                    local_papers_map[existing.title.lower().strip()] = existing.to_dict() if hasattr(existing, 'to_dict') else {
                        "paper_id": existing.paper_id,
                        "title": existing.title,
                        "authors": existing.authors,
                        "year": existing.year,
                        "abstract": existing.abstract or "",
                        "url": existing.url or "",
                        "source": existing.source or "",
                        "relevance_score": 0.95  # 本地已有的论文高相关性
                    }
            except Exception as e:
                logger.debug(f"本地查询跳过: {e}")

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
                # 扩大时间范围到5年，提高找到论文的概率
                result = await self.search_agent.execute(
                    query,
                    {"source": source, "time_range": 1825, "max_results": 5}  # 减少返回数量加速
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
                from src.agents_v2.search.sources.search_factory import SearchFactory
                from src.agents_v2.search.sources.base_searcher import SearchResponse

                # 只使用最快的搜索器，减少延迟
                searcher_names = ["openalex", "crossref"]
                fallback_papers = []
                fallback_concurrency = _get_concurrency(self.ENV_FALLBACK_SEARCH_CONCURRENCY, 2)
                semaphore = asyncio.Semaphore(fallback_concurrency)

                async def search_one(name: str) -> List[Dict[str, Any]]:
                    async with semaphore:
                        try:
                            searcher = SearchFactory.get(name)
                            if not searcher:
                                return []
                            result = await asyncio.wait_for(
                                searcher.search(query, 5),
                                timeout=5.0  # 减少超时时间
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
        main_concurrency = _get_concurrency(self.ENV_MAIN_SEARCH_CONCURRENCY, 4)
        semaphore = asyncio.Semaphore(main_concurrency)
        async def bounded_search(q):
            async with semaphore:
                return await search_single(q)

        tasks = [bounded_search(q) for q in queries[:8]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果（使用local_papers_map已去重）
        all_papers = list(local_papers_map.values())

        # 并行触发多平台搜索（与主搜索并行进行，补充结果）
        logger.info("并行触发多平台 fallback 搜索...")
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
        deep_read_concurrency = _get_concurrency(self.ENV_DEEP_READ_CONCURRENCY, 4)
        semaphore = asyncio.Semaphore(deep_read_concurrency)

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
