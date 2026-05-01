"""
LiteratureReviewAgent - 文献综述Agent

职责：
- 自动搜索相关论文
- 分类整理文献
- 识别研究空白
- 生成结构化综述报告
- 文献追踪能力（追踪特定主题最新进展）
- 文献总结能力（多篇论文对比分析，优缺点总结）
"""
from typing import Any, Dict, List, Optional
import json
import logging
import asyncio
from datetime import datetime, timedelta

from .base_writing_agent import WritingAgentBase, WritingOutput, LLMConfig
from ..paper_search.paper_search import PaperSearchAgent

logger = logging.getLogger(__name__)


class LiteratureReviewAgent(WritingAgentBase):
    """
    LiteratureReviewAgent - 文献综述生成

    职责：
    - 多源文献搜索 (arXiv, PubMed等)
    - 文献分类整理
    - 研究空白识别
    - 生成结构化综述报告
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个专业的学术文献综述专家。
你的职责是：
1. 系统性地搜索和收集相关文献
2. 对文献进行分类整理
3. 识别研究空白和机会
4. 生成结构化的综述报告

请确保：
- 文献覆盖全面，包括经典工作和最新进展
- 分类清晰，便于理解
- 识别明确的研究空白
- 引用准确可追溯"""
        super().__init__(
            name="literature_review",
            llm_config=llm_config,
            description="文献综述生成",
            system_prompt=system_prompt
        )
        # 使用真实的论文搜索Agent
        self.search_agent = PaperSearchAgent()

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> WritingOutput:
        """
        执行文献综述

        Args:
            input_data: 包含以下字段的字典：
                - topic: 研究主题
                - keywords: 关键词列表
                - min_papers: 最少论文数 (默认10)
                - max_papers: 最多论文数 (默认50)
                - mode: 执行模式 ("full_review", "tracking", "summary")
                      - full_review: 完整文献综述（默认）
                      - tracking: 文献追踪模式，专注于最新论文
                      - summary: 文献总结模式，专注于多篇论文对比分析
                - time_range: 文献追踪的时间范围 (如 "1month", "6months", "1year")
                - compare_papers: 要对比的论文列表 (用于summary模式)
            context: 执行上下文
        """
        topic = input_data.get("topic", "")
        keywords = input_data.get("keywords", [])
        min_papers = input_data.get("min_papers", 10)
        max_papers = input_data.get("max_papers", 50)
        mode = input_data.get("mode", "full_review")
        time_range = input_data.get("time_range", "1year")
        compare_papers = input_data.get("compare_papers", [])

        if not topic:
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Empty topic"
            )

        try:
            if mode == "tracking":
                return await self._execute_tracking(topic, keywords, time_range, max_papers)
            elif mode == "summary":
                return await self._execute_summary(topic, compare_papers, keywords)
            else:
                return await self._execute_full_review(topic, keywords, min_papers, max_papers)

        except Exception as e:
            self.logger.error(f"LiteratureReviewAgent execution failed: {e}")
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _execute_full_review(
        self,
        topic: str,
        keywords: List[str],
        min_papers: int,
        max_papers: int
    ) -> WritingOutput:
        """执行完整文献综述"""
        # 1. 生成搜索查询
        search_queries = await self._generate_search_queries(topic, keywords)

        # 2. 多源并行搜索
        all_papers = await self._multi_source_search(search_queries, max_papers)

        if len(all_papers) < min_papers:
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=f"Found only {len(all_papers)} papers, minimum {min_papers} required"
            )

        # 3. 质量排序
        ranked_papers = await self._quality_rank(all_papers, topic)

        # 4. 分类整理
        categorized = await self._categorize_papers(ranked_papers)

        # 5. 提取关键信息
        paper_details = await self._extract_details(ranked_papers[:30])

        # 6. 识别研究空白
        gaps = await self._identify_research_gaps(paper_details, topic)

        # 7. 生成综述报告
        review_report = await self._generate_review_report(
            topic, categorized, paper_details, gaps
        )

        return WritingOutput(
            success=True,
            result={
                "topic": topic,
                "mode": "full_review",
                "total_papers": len(all_papers),
                "analyzed_papers": len(paper_details),
                "categories": list(categorized.keys()),
                "papers_by_category": {
                    k: len(v) for k, v in categorized.items()
                },
                "research_gaps": gaps,
                "review_report": review_report,
                "references": [p.get("citation", "") for p in ranked_papers[:20]]
            },
            agent_name=self.name,
            reasoning=f"Full review: {len(all_papers)} papers analyzed, {len(gaps)} gaps identified",
            quality_score=min(1.0, len(paper_details) / 20)
        )

    async def _execute_tracking(
        self,
        topic: str,
        keywords: List[str],
        time_range: str,
        max_papers: int
    ) -> WritingOutput:
        """
        执行文献追踪模式

        专注于追踪特定主题的最新进展，返回近期发表的论文及其分析
        """
        # 1. 生成针对最新文献的搜索查询
        search_queries = await self._generate_tracking_queries(topic, keywords, time_range)

        # 2. 搜索最新论文
        latest_papers = await self._multi_source_search(search_queries, max_papers)

        # 3. 添加时间过滤标记
        tracked_papers = []
        for p in latest_papers:
            p["is_tracked"] = True
            p["time_range"] = time_range
            tracked_papers.append(p)

        # 4. 提取详情
        paper_details = await self._extract_details(tracked_papers[:20])

        # 5. 追踪分析：新增内容、技术趋势、领域进展
        tracking_analysis = await self._analyze_tracking(paper_details, topic, time_range)

        # 6. 生成追踪报告
        tracking_report = await self._generate_tracking_report(
            topic, paper_details, tracking_analysis, time_range
        )

        return WritingOutput(
            success=True,
            result={
                "topic": topic,
                "mode": "tracking",
                "time_range": time_range,
                "tracked_papers": len(tracked_papers),
                "papers": tracked_papers,
                "tracking_analysis": tracking_analysis,
                "tracking_report": tracking_report,
                "latest_trends": tracking_analysis.get("latest_trends", []),
                "new_technologies": tracking_analysis.get("new_technologies", [])
            },
            agent_name=self.name,
            reasoning=f"Tracked {len(tracked_papers)} recent papers in {time_range}",
            quality_score=min(1.0, len(paper_details) / 10)
        )

    async def _execute_summary(
        self,
        topic: str,
        compare_papers: List[Dict[str, Any]],
        keywords: List[str]
    ) -> WritingOutput:
        """
        执行文献总结模式

        对多篇论文进行对比分析，清晰总结各论文的优缺点
        """
        if not compare_papers:
            # 如果没有提供论文，搜索相关论文
            search_queries = await self._generate_search_queries(topic, keywords)
            papers = await self._multi_source_search(search_queries, 10)
        else:
            papers = compare_papers

        if not papers:
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="No papers available for summary"
            )

        # 1. 提取每篇论文的详细信息
        paper_details = await self._extract_details(papers)

        # 2. 多论文对比分析
        comparison = await self._compare_papers(paper_details, topic)

        # 3. 总结每篇论文的优缺点
        pros_cons = await self._summarize_pros_cons(paper_details)

        # 4. 生成总结报告
        summary_report = await self._generate_summary_report(
            topic, paper_details, comparison, pros_cons
        )

        return WritingOutput(
            success=True,
            result={
                "topic": topic,
                "mode": "summary",
                "total_papers": len(papers),
                "papers": paper_details,
                "comparison": comparison,
                "pros_cons": pros_cons,
                "summary_report": summary_report,
                "key_findings": comparison.get("key_findings", []),
                "methodology_comparison": comparison.get("methodology", {})
            },
            agent_name=self.name,
            reasoning=f"Compared and summarized {len(papers)} papers",
            quality_score=min(1.0, len(papers) / 10)
        )

    async def _generate_search_queries(
        self,
        topic: str,
        keywords: List[str]
    ) -> List[Dict[str, str]]:
        """生成多角度搜索查询"""
        keyword_str = ", ".join(keywords) if keywords else ""

        prompt = f"""
为以下研究主题生成多个搜索查询：

主题：{topic}
已有关键词：{keyword_str}

请生成8-12个不同角度的搜索查询，覆盖：
1. 核心概念和方法
2. 不同应用场景
3. 相关理论和基础
4. 最新进展和趋势

输出JSON格式：
{{
    "queries": [
        {{"query": "搜索查询", "angle": "角度描述", "priority": "high/medium/low"}}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("queries", [{"query": topic, "angle": "general", "priority": "high"}])
        except Exception as e:
            logger.error(f"Query generation failed: {e}")
            return [{"query": topic, "angle": "general", "priority": "high"}]

    async def _multi_source_search(
        self,
        queries: List[Dict[str, str]],
        max_papers: int
    ) -> List[Dict[str, Any]]:
        """多源并行搜索 - 使用真实API"""
        async def search_with_api(query: str, source: str = "all") -> List[Dict[str, Any]]:
            """使用真实API搜索"""
            try:
                result = await self.search_agent.execute(
                    query,
                    {"source": source, "time_range": 365, "max_results": max_papers // 3}
                )
                return result.get("papers", [])
            except Exception as e:
                logger.error(f"Search failed for query '{query}': {e}")
                return []

        # 并行执行多源搜索
        all_results = []
        semaphore = asyncio.Semaphore(5)

        async def bounded_search(query_obj: Dict[str, str]):
            async with semaphore:
                query_text = query_obj.get("query", "")
                # 同时搜索arXiv和PubMed
                results = await asyncio.gather(
                    search_with_api(query_text, "arxiv"),
                    search_with_api(query_text, "pubmed"),
                    return_exceptions=True
                )
                for result in results:
                    if isinstance(result, list):
                        all_results.extend(result)

        tasks = [bounded_search(q) for q in queries[:8]]
        await asyncio.gather(*tasks, return_exceptions=True)

        # 去重
        seen = set()
        unique_papers = []
        for p in all_results:
            title = p.get("title", "")
            if title and title not in seen:
                seen.add(title)
                unique_papers.append(p)

        return unique_papers[:max_papers]

    async def _quality_rank(
        self,
        papers: List[Dict[str, Any]],
        topic: str
    ) -> List[Dict[str, Any]]:
        """基于质量排序"""
        if not papers:
            return []

        prompt = f"""
对以下论文按相关性和质量排序：

主题：{topic}
论文列表：{json.dumps([{"title": p.get("title"), "abstract": p.get("abstract"), "citations": p.get("citations", 0)} for p in papers[:30]], ensure_ascii=False, indent=2)}

排序标准：
1. 与主题的相关性
2. 论文质量（引用数、方法严谨性）
3. 发表 venue 的权威性

输出JSON格式：
{{
    "ranked": [
        {{"index": 0, "rank": 1, "reason": "排序原因"}}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            ranked_info = data.get("ranked", [])

            rank_map = {r["index"]: r["rank"] for r in ranked_info}

            indexed = list(enumerate(papers))
            sorted_papers = sorted(indexed, key=lambda x: rank_map.get(x[0], 999))
            return [p for _, p in sorted_papers]

        except Exception as e:
            logger.error(f"Quality ranking failed: {e}")
            return sorted(papers, key=lambda p: p.get("citations", 0), reverse=True)

    async def _categorize_papers(
        self,
        papers: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """分类整理论文"""
        if not papers:
            return {}

        prompt = f"""
将以下论文按研究类别分类：

论文列表：{json.dumps([{"title": p.get("title"), "abstract": p.get("abstract")} for p in papers[:30]], ensure_ascii=False)}

分类维度：
1. 研究方法
2. 应用领域
3. 理论 vs 应用
4. 问题类型

输出JSON格式：
{{
    "categories": {{
        "类别名称": [论文索引列表]
    }}
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            category_data = data.get("categories", {})

            # 转换为 {category: [papers]} 格式
            result = {}
            for cat, indices in category_data.items():
                result[cat] = [papers[i] for i in indices if i < len(papers)]

            return result

        except Exception as e:
            logger.error(f"Categorization failed: {e}")
            return {"uncategorized": papers}

    async def _extract_details(
        self,
        papers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """提取论文关键信息"""
        details = []

        for paper in papers:
            try:
                detail = await self._extract_single_paper(paper)
                details.append(detail)
            except Exception as e:
                logger.error(f"Paper extraction failed: {e}")
                continue

        return details

    async def _extract_single_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """提取单篇论文的关键信息"""
        prompt = f"""
分析以下论文，提取关键信息：

标题：{paper.get('title', '')}
摘要：{paper.get('abstract', '')}

请提取：
{{
    "title": "标题",
    "authors": ["作者1", "作者2"],
    "year": 年份,
    "core_problem": "核心研究问题",
    "methodology": "研究方法",
    "key_findings": ["主要发现1", "主要发现2"],
    "limitations": ["局限性1", "局限性2"],
    "datasets": ["数据集"],
    "citation": "引用格式（如APA）"
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return {**paper, **data}
        except Exception as e:
            logger.error(f"Single paper extraction failed: {e}")
            return paper

    async def _identify_research_gaps(
        self,
        paper_details: List[Dict[str, Any]],
        topic: str
    ) -> List[Dict[str, Any]]:
        """识别研究空白"""
        if not paper_details:
            return [{"description": "需要更多文献", "direction": "扩大搜索范围"}]

        prompt = f"""
基于以下论文分析，识别研究空白：

主题：{topic}
论文分析：{json.dumps(paper_details[:20], ensure_ascii=False)}

请识别3-5个研究空白，每个空白包含：
{{
    "description": "空白描述",
    "evidence": "支持证据",
    "potential_directions": ["潜在研究方向1", "潜在研究方向2"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("gaps", [])
        except Exception as e:
            logger.error(f"Gap identification failed: {e}")
            return [{"description": "Further investigation needed", "direction": "Explore new angles"}]

    async def _generate_review_report(
        self,
        topic: str,
        categorized: Dict[str, List[Dict[str, Any]]],
        paper_details: List[Dict[str, Any]],
        gaps: List[Dict[str, Any]]
    ) -> str:
        """生成综述报告"""
        prompt = f"""
基于以下材料，生成结构化文献综述报告：

研究主题：{topic}

文献分类：{json.dumps({cat: [p.get('title') for p in papers] for cat, papers in categorized.items()}, ensure_ascii=False)}

论文详情：{json.dumps(paper_details[:15], ensure_ascii=False)}

研究空白：{json.dumps(gaps, ensure_ascii=False)}

报告结构：
1. 引言 - 研究背景和重要性
2. 文献分类
   2.1 各类别的代表工作
   2.2 各类别的特点分析
3. 研究空白
4. 未来研究方向
5. 结论

请生成完整的markdown格式综述报告。
"""
        try:
            response = await self._llm_call(prompt)
            return response
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return f"# Literature Review: {topic}\n\nLiterature review generation failed."

    # ========== 文献追踪相关方法 ==========

    async def _generate_tracking_queries(
        self,
        topic: str,
        keywords: List[str],
        time_range: str
    ) -> List[Dict[str, str]]:
        """生成用于文献追踪的搜索查询（侧重最新文献）"""
        keyword_str = ", ".join(keywords) if keywords else ""

        prompt = f"""
为以下研究主题生成针对最新文献的搜索查询：

主题：{topic}
已有关键词：{keyword_str}
时间范围：{time_range}

请生成5-8个搜索查询，重点关注：
1. 最新方法和进展
2. 新提出的技术框架
3. 近期有突破的研究方向
4. 最新应用案例

每个查询应包含时间相关的限定词。

输出JSON格式：
{{
    "queries": [
        {{"query": "搜索查询（包含最新/近期等限定）", "focus": "关注重点"}}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("queries", [{"query": f"{topic} latest", "focus": "最新进展"}])
        except Exception as e:
            logger.error(f"Tracking query generation failed: {e}")
            return [{"query": topic, "focus": "最新进展"}]

    async def _analyze_tracking(
        self,
        paper_details: List[Dict[str, Any]],
        topic: str,
        time_range: str
    ) -> Dict[str, Any]:
        """分析追踪到的文献，识别趋势"""
        if not paper_details:
            return {"latest_trends": [], "new_technologies": [], "progress_summary": ""}

        prompt = f"""
分析以下近期发表的论文，识别领域最新进展和趋势：

主题：{topic}
时间范围：{time_range}
论文列表：{json.dumps(paper_details, ensure_ascii=False, indent=2)}

请分析并输出JSON格式：
{{
    "latest_trends": ["最新趋势1", "最新趋势2"],
    "new_technologies": ["新技术1", "新技术2"],
    "breakthrough_papers": [
        {{"title": "论文标题", "breakthrough": "突破性贡献"}}
    ],
    "progress_summary": "领域进展总结"
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"Tracking analysis failed: {e}")
            return {"latest_trends": [], "new_technologies": []}

    async def _generate_tracking_report(
        self,
        topic: str,
        paper_details: List[Dict[str, Any]],
        tracking_analysis: Dict[str, Any],
        time_range: str
    ) -> str:
        """生成文献追踪报告"""
        prompt = f"""
为以下主题生成近期文献追踪报告：

主题：{topic}
时间范围：{time_range}

近期论文：{json.dumps([{"title": p.get("title"), "year": p.get("year"), "authors": p.get("authors", [])[:3]} for p in paper_details[:10]], ensure_ascii=False, indent=2)}

追踪分析：
- 最新趋势：{json.dumps(tracking_analysis.get("latest_trends", []), ensure_ascii=False)}
- 新技术：{json.dumps(tracking_analysis.get("new_technologies", []), ensure_ascii=False)}
- 突破性工作：{json.dumps(tracking_analysis.get("breakthrough_papers", []), ensure_ascii=False)}

报告结构：
1. 概述 - 本期追踪范围和总体情况
2. 最新趋势 - 近期的主要发展方向
3. 代表性工作 - 重要论文及贡献
4. 技术进展 - 新方法、新技术
5. 下一步建议 - 可能的研究方向

请生成markdown格式的追踪报告。
"""
        try:
            response = await self._llm_call(prompt)
            return response
        except Exception as e:
            logger.error(f"Tracking report generation failed: {e}")
            return f"# 文献追踪报告: {topic}\n\n追踪时间范围: {time_range}\n\n生成失败"

    # ========== 文献总结对比相关方法 ==========

    async def _compare_papers(
        self,
        paper_details: List[Dict[str, Any]],
        topic: str
    ) -> Dict[str, Any]:
        """多论文对比分析"""
        if len(paper_details) < 2:
            return {"comparison_table": {}, "key_findings": [], "methodology": {}}

        prompt = f"""
对以下论文进行系统性对比分析：

主题：{topic}
论文列表：{json.dumps([{{
    "title": p.get("title"),
    "methodology": p.get("methodology", ""),
    "key_findings": p.get("key_findings", []),
    "datasets": p.get("datasets", []),
    "year": p.get("year")
}} for p in paper_details], ensure_ascii=False, indent=2)}

请从以下维度进行对比分析：
1. 研究方法对比
2. 数据集使用对比
3. 性能/效果对比
4. 适用场景对比
5. 局限性对比

输出JSON格式：
{{
    "comparison_table": {{
        "methodology": {{"paper1": "方法", "paper2": "方法"}},
        "datasets": {{"paper1": "数据集", "paper2": "数据集"}},
        "performance": {{"paper1": "性能", "paper2": "性能"}}
    }},
    "key_findings": ["关键发现1", "关键发现2"],
    "methodology": {{"相同点": [], "不同点": []}},
    "scenarios": {{"paper1": "适用场景", "paper2": "适用场景"}}
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"Paper comparison failed: {e}")
            return {"comparison_table": {}, "key_findings": [], "methodology": {}}

    async def _summarize_pros_cons(
        self,
        paper_details: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """总结每篇论文的优缺点"""
        if not paper_details:
            return []

        prompt = f"""
分析以下论文的优缺点：

论文列表：{json.dumps([{{
    "title": p.get("title"),
    "methodology": p.get("methodology", ""),
    "key_findings": p.get("key_findings", []),
    "limitations": p.get("limitations", [])
}} for p in paper_details], ensure_ascii=False, indent=2)}

请为每篇论文总结：
{{
    "title": "论文标题",
    "pros": ["优点1", "优点2", "优点3"],
    "cons": ["缺点1", "缺点2"],
    "overall_assessment": "总体评价",
    "suitability": "适用场景"
}}

输出JSON格式：
{{
    "summaries": [
        {{"title": "...", "pros": [...], "cons": [...], "overall_assessment": "...", "suitability": "..."}}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("summaries", [])
        except Exception as e:
            logger.error(f"Pros/cons summarization failed: {e}")
            return []

    async def _generate_summary_report(
        self,
        topic: str,
        paper_details: List[Dict[str, Any]],
        comparison: Dict[str, Any],
        pros_cons: List[Dict[str, Any]]
    ) -> str:
        """生成多论文总结报告"""
        prompt = f"""
为以下论文生成对比总结报告：

主题：{topic}

论文列表：{json.dumps([p.get("title", "") for p in paper_details], ensure_ascii=False)}

各论文优缺点：
{json.dumps(pros_cons, ensure_ascii=False, indent=2)}

对比分析：
- 关键发现：{json.dumps(comparison.get("key_findings", []), ensure_ascii=False)}
- 方法论对比：{json.dumps(comparison.get("methodology", {{}}), ensure_ascii=False)}

报告结构：
1. 概述 - 被对比的论文概览
2. 论文优缺点总结（每篇论文独立一节）
   2.1 [论文1标题] - 优点、缺点、总体评价
   2.2 [论文2标题] - 优点、缺点、总体评价
3. 对比分析
   3.1 方法论对比
   3.2 性能/效果对比
   3.3 适用场景对比
4. 综合建议 - 不同场景下的论文选择建议

请生成markdown格式的总结报告，突出展示各论文的优缺点对比。
"""
        try:
            response = await self._llm_call(prompt)
            return response
        except Exception as e:
            logger.error(f"Summary report generation failed: {e}")
            return f"# 论文总结报告: {topic}\n\n生成失败"
