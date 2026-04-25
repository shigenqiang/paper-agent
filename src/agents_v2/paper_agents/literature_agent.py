"""
LiteratureAgent - 文献工作Agent

职责：
- 多源文献搜索
- 质量筛选
- PDF阅读与信息提取
- 识别研究空白
"""
from typing import Any, Dict, List, Optional
import json
import logging
import asyncio

from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig

logger = logging.getLogger(__name__)


class LiteratureAgent(PaperAgentBase):
    """
    LiteratureAgent - 文献收集与综述

    职责：
    - 多源文献搜索
    - 质量筛选
    - PDF阅读与信息提取
    - 识别研究空白
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
- 提取信息准确、结构化"""
        super().__init__(
            name="literature_agent",
            llm_config=llm_config,
            description="文献搜索、筛选与综述",
            system_prompt=system_prompt
        )

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
            # 1. 多角度搜索查询
            search_queries = await self._generate_search_queries(topic, research_question)

            # 2. 多引擎并行搜索
            all_papers = await self._multi_engine_search(search_queries)

            # 3. 质量筛选与排序
            ranked_papers = await self._rank_papers(topic, all_papers)

            # 4. 深度阅读（只处理Top论文）
            paper_analyses = await self._deep_read(ranked_papers[:20])

            # 5. 识别研究空白
            gaps = await self._identify_gaps(paper_analyses, topic, research_question)

            return AgentOutput(
                success=True,
                result={
                    "papers": ranked_papers,
                    "paper_analyses": paper_analyses,
                    "research_gaps": gaps,
                    "search_queries": search_queries,
                    "total_found": len(all_papers),
                    "total_analyzed": len(paper_analyses)
                },
                agent_name=self.name,
                reasoning=f"Collected {len(ranked_papers)} papers, analyzed {len(paper_analyses)}, identified {len(gaps)} gaps",
                quality_score=min(1.0, len(paper_analyses) / 15)
            )

        except Exception as e:
            self.logger.error(f"LiteratureAgent execution failed: {e}")
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
            data = json.loads(response)
            return data.get("queries", [{"query": topic, "strategy": "基础", "aspect": "综合"}])
        except Exception as e:
            self.logger.error(f"Query generation failed: {e}")
            return [{"query": topic, "strategy": "基础", "aspect": "综合"}]

    async def _multi_engine_search(self, queries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """多引擎并行搜索"""
        async def search_single(query_obj: Dict[str, str]) -> List[Dict[str, Any]]:
            # 这里应该调用实际的搜索API
            # 目前返回模拟数据
            query = query_obj.get("query", "")
            return [{
                "title": f"Paper about {query}",
                "abstract": f"Abstract for {query}",
                "authors": ["Author 1", "Author 2"],
                "year": 2024,
                "source": f"search_{query_obj.get('strategy', 'default')}",
                "url": f"https://example.com/{query}",
                "citations": 50,
                "relevance_score": 0.8
            }]

        # 并行搜索（限制并发数）
        semaphore = asyncio.Semaphore(3)
        async def bounded_search(q):
            async with semaphore:
                return await search_single(q)

        tasks = [bounded_search(q) for q in queries[:8]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        all_papers = []
        for result in results:
            if isinstance(result, list):
                all_papers.extend(result)

        # 去重
        seen = set()
        unique_papers = []
        for p in all_papers:
            title = p.get("title", "")
            if title and title not in seen:
                seen.add(title)
                unique_papers.append(p)

        return unique_papers

    async def _rank_papers(self, topic: str, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """排序论文"""
        if not papers:
            return []

        prompt = f"""
对以下论文进行相关性排序：

主题：{topic}
论文列表：{json.dumps([{"title": p.get("title"), "abstract": p.get("abstract")} for p in papers[:30]], ensure_ascii=False)}

请按相关性排序，输出JSON格式：
{{
    "ranked": [
        {{"original_index": 0, "rank": 1, "reason": "原因"}},
        ...
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            ranked_info = data.get("ranked", [])

            # 创建排序映射
            rank_map = {r["original_index"]: r["rank"] for r in ranked_info}

            # 重新排序
            indexed_papers = list(enumerate(papers))
            sorted_papers = sorted(indexed_papers, key=lambda x: rank_map.get(x[0], 999))
            return [p for _, p in sorted_papers]

        except Exception as e:
            self.logger.error(f"Ranking failed: {e}")
            return sorted(papers, key=lambda p: p.get("relevance_score", 0), reverse=True)

    async def _deep_read(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """深度阅读论文"""
        analyses = []

        for paper in papers:
            try:
                analysis = await self._extract_paper_info(paper)
                analyses.append(analysis)
            except Exception as e:
                self.logger.error(f"Paper analysis failed: {e}")
                continue

        return analyses

    async def _extract_paper_info(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """提取论文关键信息"""
        prompt = f"""
分析以下论文，提取关键信息：

论文标题：{paper.get('title', '')}
摘要：{paper.get('abstract', '')}

请提取以下信息，输出JSON格式：
{{
    "paper_id": "论文ID",
    "title": "标题",
    "core_problem": "核心研究问题",
    "key_methodology": "主要方法",
    "key_findings": "主要发现",
    "limitations": "局限性",
    "datasets": ["数据集1", "数据集2"],
    "evaluation_metrics": ["指标1", "指标2"],
    "related_work": ["相关工作1", "相关工作2"],
    "potential_gaps": "可能的gap"
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            self.logger.error(f"Paper info extraction failed: {e}")
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

        prompt = f"""
基于以下论文分析，识别研究空白：

主题：{topic}
研究问题：{research_question}

论文分析：{json.dumps(paper_analyses[:15], ensure_ascii=False)}

请识别3-5个研究空白，输出JSON格式：
{{
    "gaps": [
        {{
            "description": "gap描述",
            "evidence": "证据（哪些论文支持这个gap）",
            "potential_directions": ["潜在研究方向1", "潜在研究方向2"]
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("gaps", [])
        except Exception as e:
            self.logger.error(f"Gap identification failed: {e}")
            return [{"description": "Further research needed", "evidence": "", "potential_direction": "Explore new methods"}]
