"""
LiteratureMapperAgent - 文献映射Agent

针对问题：文献综述不充分、无法识别研究空白

职责：
- 全面搜索相关文献
- 分类整理现有研究
- 识别研究空白
- 生成文献地图
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

import json
import asyncio

from .base_problem_agent import ProblemAgentBase, AgentOutput, LLMConfig
from src.agents_v2.agents.report.paper_search import PaperSearchAgent
from src.agents_v2.core.embedding import get_local_embedding_model

logger = get_logging_logger(__name__)


def _clean_json_markdown(text: str) -> str:
    """清理JSON markdown格式（去除```json...```包裹），并提取纯JSON"""
    import re
    # 移除思考块
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # 去除 ```json ... ``` 包裹
    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE)
    # 去除 ``` ... ``` 包裹
    text = re.sub(r'^```\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE)
    text = text.strip()

    # 如果不是以 { 开头，尝试找到第一个 { 的位置
    if text and not text.startswith('{'):
        match = re.search(r'\{', text)
        if match:
            text = text[match.start():]
            cls_name = "LiteratureMapperAgent"
            logger.warning(f"[{cls_name}:30] JSON doesn't start with '{{', extracting from position {match.start()}")

    # 尝试只提取第一个完整的JSON对象（处理JSON后有多余内容的情况）
    if text.startswith('{') or text.startswith('['):
        try:
            # 尝试标准 json.loads
            json.loads(text)
            return text
        except json.JSONDecodeError as e:
            # 如果失败，尝试找到匹配的闭合括号
            cls_name = "LiteratureMapperAgent"
            logger.warning(f"[{cls_name}:40] JSON parse failed: {e}, attempting to extract complete JSON")

            # 找到第一个 { 或 [ 的位置
            first_char = text[0] if text else None
            start = 0
            start_char = '{' if first_char == '{' else '[' if first_char == '[' else None

            if not start_char:
                return text

            # 计算起始标记
            opening_mark = start_char
            closing_mark = '}' if start_char == '{' else ']'

            depth = 0
            end_pos = -1

            for i, c in enumerate(text):
                if c == opening_mark:
                    depth += 1
                elif c == closing_mark:
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break

            if end_pos > 0:
                extracted = text[:end_pos]
                try:
                    json.loads(extracted)
                    logger.info(f"[{cls_name}:55] Successfully extracted complete JSON, length={end_pos}")
                    return extracted
                except json.JSONDecodeError:
                    # 如果提取失败，尝试查找下一个JSON对象的开始
                    # 这处理 "}{" 或 "][" 等多个JSON对象连接的情况
                    next_start = end_pos
                    while next_start < len(text):
                        # 跳过空白字符
                        while next_start < len(text) and text[next_start] in ' \t\n\r':
                            next_start += 1
                        if next_start >= len(text):
                            break
                        next_char = text[next_start]
                        if next_char == '{' or next_char == '[':
                            # 找到下一个JSON对象，验证它是否完整
                            sub_text = text[next_start:]
                            try:
                                json.loads(sub_text)
                                # 完整有效，继续使用这个
                                logger.info(f"[{cls_name}:62] Using second JSON object at position {next_start}")
                                return sub_text
                            except json.JSONDecodeError:
                                # 不完整，尝试提取
                                inner_start = 0
                                inner_depth = 0
                                inner_opening = next_char
                                inner_closing = '}' if next_char == '{' else ']'
                                inner_end = -1
                                for j, c2 in enumerate(sub_text):
                                    if c2 == inner_opening:
                                        inner_depth += 1
                                    elif c2 == inner_closing:
                                        inner_depth -= 1
                                        if inner_depth == 0:
                                            inner_end = j + 1
                                            break
                                if inner_end > 0:
                                    extracted2 = sub_text[:inner_end]
                                    try:
                                        json.loads(extracted2)
                                        logger.info(f"[{cls_name}:68] Successfully extracted second JSON, position={next_start}")
                                        return extracted2
                                    except json.JSONDecodeError:
                                        pass
                                next_start += 1
                        else:
                            next_start += 1
                    pass

    return text


class LiteratureMapperAgent(ProblemAgentBase):
    """
    LiteratureMapperAgent - 文献映射

    针对问题：
    - 文献查找不全
    - 综述片面/有偏见
    - 无法识别研究空白
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个专业的文献综述专家。
你的职责是：
1. 全面搜索相关文献
2. 分类整理现有研究
3. 识别研究空白
4. 生成结构化的文献地图

请确保综述全面、客观、无偏见。"""
        super().__init__(
            name="literature_mapper",
            target_problem="文献综述不充分/无法识别研究空白",
            llm_config=llm_config,
            description="文献搜索与研究空白识别",
            system_prompt=system_prompt
        )
        # 使用真实的论文搜索Agent
        self.search_agent = PaperSearchAgent()

    async def diagnose(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        诊断文献综述问题

        输入：
        - topic: 研究主题
        - existing_papers: 用户已找到的文献（可选）
        - search_queries: 搜索关键词（可选）
        """
        topic = input_data.get("topic", "")
        existing_papers = input_data.get("existing_papers", [])
        search_queries = input_data.get("search_queries", [])

        if not topic:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["研究主题为空"],
                recommendations=["请提供具体的研究主题"],
                quality_score=0.0,
                error="Empty topic"
            )

        try:
            # 1. 生成多角度搜索查询
            queries = await self._generate_search_queries(topic)

            # 2. 文献搜索（已有网络I/O并行优化）
            papers = await self._search_papers(queries, existing_papers)

            # 3. 分类整理文献
            categorized = await self._categorize_papers(papers)

            # 4. 识别研究空白（依赖categorized，需要串行）
            gaps = await self._identify_gaps(topic, categorized)

            # 5. 生成文献地图（依赖categorized和gaps，轻量组装）
            literature_map = {
                "topic": topic,
                "categories": list(categorized.keys()),
                "category_counts": {k: len(v) for k, v in categorized.items()},
                "gaps": gaps,
                "key_papers": self._identify_key_papers_fast(categorized)
            }

            # 6-7. 并行执行：诊断问题和生成建议（相互独立，且都是轻量逻辑）
            issues_task = self._diagnose_review_issues_async(existing_papers, papers)
            recommendations_task = self._generate_recommendations_async(papers)

            issues, recommendations = await asyncio.gather(
                issues_task, recommendations_task,
                return_exceptions=True
            )

            # 处理并行执行中的异常
            if isinstance(issues, Exception):
                self.logger.warning(f"Diagnose issues failed: {issues}, using default")
                issues = ["文献综述基本完整"]
            if isinstance(recommendations, Exception):
                self.logger.warning(f"Generate recommendations failed: {recommendations}, using default")
                recommendations = ["文献综述较为完整，可进入下一阶段"]

            # 8. 预计算论文embedding（后台执行，不阻塞主流程）
            asyncio.create_task(self._embed_papers(papers, topic))
            self.logger.info(f"[{self.__class__.__name__}] 启动后台embedding预计算任务")

            # 质量评分：基于文献数量和空白识别
            quality_score = min(1.0, len(papers) / 20) * 0.5 + (len(gaps) / 5) * 0.5

            return AgentOutput(
                success=True,
                result={
                    "topic": topic,
                    "literature_map": literature_map,
                    "categorized_literature": categorized,
                    "research_gaps": gaps,
                    "total_papers_found": len(papers),
                    "search_queries_used": queries,
                    "papers": papers  # 返回 papers 供后续阶段复用
                },
                agent_name=self.name,
                diagnosed_issues=issues,
                recommendations=recommendations,
                quality_score=quality_score
            )

        except Exception as e:
            self.logger.error(f"Literature mapping failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["文献综述失败"],
                recommendations=["请尝试更具体的搜索关键词"],
                quality_score=0.0,
                error=str(e)
            )

    async def _generate_search_queries(self, topic: str) -> List[str]:
        """生成多角度搜索查询"""
        prompt = f"""
为以下研究主题生成多角度搜索查询（请使用英文关键词，因为arXiv和PubMed是英文数据库）：

主题：{topic}

请生成8-10个不同角度的英文搜索查询，覆盖：
1. 核心主题
2. 相关方法
3. 应用领域
4. 对比研究
5. 最新进展

输出JSON格式：
{{
    "queries": ["english query 1", "english query 2", ...]
}}
"""
        cls_name = self.__class__.__name__
        try:
            response = await self._llm_call(prompt)
            if not response:
                logger.error(f"[{cls_name}:155] LLM返回空响应")
                return [topic]
            content = response.strip()
            if not content:
                logger.error(f"[{cls_name}:158] LLM响应为空格")
                return [topic]

            # 清理markdown代码块标记（使用增强版本，可提取完整JSON）
            content = _clean_json_markdown(content)

            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"[{cls_name}:221] JSON parse failed: {e}, raw_response={content[:500] if content else 'empty'}, using fallback")
                return [topic]
            return data.get("queries", [topic])
        except ValueError as e:
            logger.error(f"[{cls_name}:178] Query generation failed: {e}")
            return [topic]
        except Exception as e:
            logger.error(f"[{cls_name}:178] Query generation failed: {e}")
            return [topic]

    async def _search_papers(
        self,
        queries: List[str],
        existing_papers: List[Dict]
    ) -> List[Dict[str, Any]]:
        """搜索文献 - 使用真实API"""
        import asyncio
        cls_name = self.__class__.__name__

        # 合并已有文献
        all_papers = list(existing_papers)
        self.logger.debug(f"开始搜索文献，查询数量: {len(queries)}, 已有文献: {len(existing_papers)}")

        async def search_query(query: str) -> List[Dict[str, Any]]:
            try:
                # 注意：PaperSearchAgent 会记录 "搜索论文: {query}"，这里不再重复记录
                result = await self.search_agent.execute(
                    query,
                    {"source": "all", "time_range": 365, "max_results": 10}
                )
                papers = result.get("papers", [])
                self.logger.debug(f"查询 '{query[:30]}...' 返回 {len(papers)} 篇论文")
                return papers
            except Exception as e:
                self.logger.error(f"Search failed for query '{query}': {e}")
                return []

        # 并行搜索
        semaphore = asyncio.Semaphore(3)
        async def bounded_search(query):
            async with semaphore:
                return await search_query(query)

        tasks = [bounded_search(q) for q in queries[:4]]  # 限制查询数量，避免过长等待
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_papers.extend(result)

        self.logger.debug(f"搜索完成，总论文数: {len(all_papers)}")

        # 去重
        seen = set()
        unique_papers = []
        for p in all_papers:
            title = p.get("title", "")
            if title and title not in seen:
                seen.add(title)
                unique_papers.append(p)

        self.logger.debug(f"去重后论文数: {len(unique_papers)}")
        return unique_papers

    async def _embed_papers(self, papers: List[Dict[str, Any]], topic: str = "") -> List[Dict[str, Any]]:
        """
        后台预计算论文embedding，供后续LiteratureAgent复用

        Args:
            papers: 论文列表
            topic: 研究主题（用于计算主题embedding）
        Returns:
            带embedding的论文列表
        """
        if not papers:
            return papers

        cls_name = self.__class__.__name__
        self.logger.info(f"[{cls_name}] 开始预计算 {len(papers)} 篇论文的 embedding")

        # 获取本地embedding模型
        local_model = get_local_embedding_model()
        if not local_model:
            self.logger.warning(f"[{cls_name}] 本地embedding模型不可用，跳过预计算")
            return papers

        # 限制处理数量（增大到50篇，加速且覆盖更多论文）
        papers_to_embed = papers[:50]

        # 计算主题embedding（用于相关性计算）
        topic_embedding = None
        if topic:
            try:
                topic_embedding = await asyncio.wait_for(
                    asyncio.to_thread(local_model.get_embedding, topic),
                    timeout=60.0
                )
            except Exception as e:
                self.logger.warning(f"[{cls_name}] 主题embedding计算失败: {e}")

        def compute_embedding_sync(text: str):
            """同步计算embedding（在线程中执行）"""
            try:
                return local_model.get_embedding(text)
            except Exception:
                return None

        async def process_paper(paper: Dict[str, Any], idx: int) -> Dict[str, Any]:
            try:
                text_to_embed = f"{paper.get('title', '')} {paper.get('abstract', '')}"
                embedding = await asyncio.wait_for(
                    asyncio.to_thread(compute_embedding_sync, text_to_embed),
                    timeout=60.0
                )
                paper["embedding"] = embedding
                if embedding and topic_embedding:
                    # 计算余弦相似度
                    dot = sum(a * b for a, b in zip(embedding, topic_embedding))
                    norm1 = sum(a * a for a in embedding) ** 0.5
                    norm2 = sum(b * b for b in topic_embedding) ** 0.5
                    if norm1 > 0 and norm2 > 0:
                        paper["embedding_relevance"] = dot / (norm1 * norm2)
                self.logger.debug(f"[{cls_name}] 论文 {idx+1}/{len(papers_to_embed)} embedding完成")
                return paper
            except asyncio.TimeoutError:
                self.logger.warning(f"[{cls_name}] 论文 {idx} embedding超时")
                return paper
            except Exception as e:
                self.logger.warning(f"[{cls_name}] 论文 {idx} embedding失败: {e}")
                return paper

        # 并行处理（最多10个并发）
        semaphore = asyncio.Semaphore(10)
        async def bounded_process(paper, idx):
            async with semaphore:
                return await process_paper(paper, idx)

        tasks = [bounded_process(p, i) for i, p in enumerate(papers_to_embed)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        embedded = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.warning(f"[{cls_name}] 论文 {i} 处理异常: {result}")
                embedded.append(papers_to_embed[i])
            else:
                embedded.append(result)

        # 未处理的论文保持原样
        embedded.extend(papers[50:])

        self.logger.info(f"[{cls_name}] embedding预计算完成: {len(embedded)} 篇")
        return embedded

    async def _categorize_papers(self, papers: List[Dict[str, Any]]) -> Dict[str, List]:
        """分类整理文献 - 并行版本（分批处理后合并）"""
        if not papers:
            return {
                "methods": [],
                "applications": [],
                "surveys": [],
                "critiques": [],
                "related": []
            }

        # 限制处理数量，截断 abstract 长度
        papers_to_process = papers[:30]
        paper_list = [
            {"title": p.get("title", ""), "abstract": (p.get("abstract") or "")[:200]}
            for p in papers_to_process
        ]

        # 分批处理 - 每批10篇，并行分类后合并
        batch_size = 10
        batches = [paper_list[i:i+batch_size] for i in range(0, len(paper_list), batch_size)]

        async def _categorize_batch(batch: List[Dict]) -> Dict[str, List]:
            """对一批文献进行分类"""
            prompt = f"""将以下文献分类整理：

文献列表：{json.dumps(batch, ensure_ascii=False)}

分类类别：
1. methods: 方法论研究
2. applications: 应用研究
3. surveys: 综述文章
4. critiques: 批评/局限性研究
5. related: 相关但不直接相关

输出JSON格式：
{{
    "methods": [{{"title": "...", "year": 2023, "key_finding": "..."}}],
    "applications": [...],
    "surveys": [...],
    "critiques": [...],
    "related": [...]
}}
"""
            cls_name = self.__class__.__name__
            try:
                response = await self._llm_call(prompt)
                if not response or not response.strip():
                    logger.error(f"[{cls_name}:325] LLM返回空响应")
                    return {cat: [] for cat in ["methods", "applications", "surveys", "critiques", "related"]}
                content = _clean_json_markdown(response)
                try:
                    data = json.loads(content)
                    return data
                except json.JSONDecodeError as e:
                    logger.warning(f"[{cls_name}:338] Batch JSON parse failed: {e}")
                    return {cat: [] for cat in ["methods", "applications", "surveys", "critiques", "related"]}
            except Exception as e:
                logger.error(f"[{cls_name}:342] Batch categorization failed: {e}")
                return {cat: [] for cat in ["methods", "applications", "surveys", "critiques", "related"]}

        # 并行执行所有批次
        import asyncio
        batch_results = await asyncio.gather(*[_categorize_batch(b) for b in batches])

        # 合并结果
        merged = {cat: [] for cat in ["methods", "applications", "surveys", "critiques", "related"]}
        for batch_result in batch_results:
            for cat in merged:
                items = batch_result.get(cat, [])
                if isinstance(items, list):
                    merged[cat].extend(items)

        # 去重（按 title）
        seen_titles = set()
        final_result = {cat: [] for cat in ["methods", "applications", "surveys", "critiques", "related"]}
        for cat in merged:
            for item in merged[cat]:
                title = item.get("title", "")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    final_result[cat].append(item)

        logger.info(f"[{self.__class__.__name__}] 分类完成: methods={len(final_result['methods'])}, applications={len(final_result['applications'])}, surveys={len(final_result['surveys'])}")
        return final_result

    async def _identify_gaps(self, topic: str, categorized: Dict) -> List[Dict[str, str]]:
        """识别研究空白"""
        prompt = f"""
基于以下分类文献，识别研究空白：

主题：{topic}
文献分类：{json.dumps(categorized, ensure_ascii=False)}

请识别3-5个研究空白，并说明：
1. 空白描述
2. 为什么是空白
3. 潜在研究方向

输出JSON格式：
{{
    "gaps": [
        {{
            "description": "空白描述",
            "evidence": "支持证据",
            "potential_direction": "潜在研究方向"
        }}
    ]
}}
"""
        cls_name = self.__class__.__name__
        try:
            response = await self._llm_call(prompt)
            if not response or not response.strip():
                logger.error(f"[{cls_name}:325] LLM返回空响应")
                return [{"description": "Further research needed", "potential_direction": "Explore new methods"}]
            content = _clean_json_markdown(response)
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"[{cls_name}:371] Gap identification JSON parse failed: {e}, raw_response={response[:500] if response else 'empty'}")
                return [{"description": "Further research needed", "potential_direction": "Explore new methods"}]
            return data.get("gaps", [])
        except ValueError as e:
            logger.error(f"[{cls_name}:331] Gap identification failed: {e}", exc_info=True)
            return [{"description": "Further research needed", "potential_direction": "Explore new methods"}]
        except Exception as e:
            logger.error(f"[{cls_name}:333] Gap identification failed: {e}", exc_info=True)
            return [{"description": "Further research needed", "potential_direction": "Explore new methods"}]

    async def _generate_literature_map(
        self,
        topic: str,
        categorized: Dict,
        gaps: List[Dict]
    ) -> Dict[str, Any]:
        """生成文献地图"""
        return {
            "topic": topic,
            "categories": list(categorized.keys()),
            "category_counts": {k: len(v) for k, v in categorized.items()},
            "gaps": gaps,
            "key_papers": await self._identify_key_papers(categorized)
        }

    def _identify_key_papers_fast(self, categorized: Dict) -> List[Dict]:
        """快速识别关键论文（同步版本，无需LLM）"""
        key_papers = []
        for category, papers in categorized.items():
            if papers and isinstance(papers, list):
                for p in papers[:2]:
                    if isinstance(p, dict):
                        key_papers.append({
                            "title": p.get("title", ""),
                            "category": category,
                            "key_finding": p.get("key_finding", "")
                        })
        return key_papers

    async def _identify_key_papers(self, categorized: Dict) -> List[Dict]:
        """识别关键论文"""
        key_papers = []
        for category, papers in categorized.items():
            if papers and isinstance(papers, list):
                # 每类取最重要的2篇
                for p in papers[:2]:
                    if isinstance(p, dict):
                        key_papers.append({
                            "title": p.get("title", ""),
                            "category": category,
                            "key_finding": p.get("key_finding", "")
                        })
        return key_papers

    async def _diagnose_review_issues(
        self,
        existing: List,
        found: List,
        gaps: List
    ) -> List[str]:
        """诊断文献综述问题"""
        issues = []

        if len(existing) < 5:
            issues.append("已有文献数量不足")

        if len(found) < 10:
            issues.append("搜索到的文献数量偏少，建议扩大搜索范围")

        if len(gaps) == 0:
            issues.append("未能识别出明显的研究空白")

        # 检查各类文献是否齐全
        if not issues:
            issues.append("文献综述基本完整")

        return issues

    async def _generate_recommendations(self, issues: List[str], gaps: List) -> List[str]:
        """生成改进建议"""
        recommendations = []

        for issue in issues:
            if "数量不足" in issue:
                recommendations.append("扩大搜索关键词范围，添加同义词和相关术语")
            if "研究空白" in issue:
                if gaps:
                    recommendations.append(f"可考虑以下研究空白: {gaps[0].get('description', '')}")

        if not recommendations:
            recommendations.append("文献综述较为完整，可进入下一阶段")

        return recommendations[:5]

    async def _diagnose_review_issues_async(
        self,
        existing: List,
        found: List
    ) -> List[str]:
        """诊断文献综述问题（异步轻量版本）"""
        issues = []

        if len(existing) < 5:
            issues.append("已有文献数量不足")

        if len(found) < 10:
            issues.append("搜索到的文献数量偏少，建议扩大搜索范围")

        # 检查文献质量
        if found:
            # 检查有多少论文有 abstract
            papers_with_abstract = sum(1 for p in found if p.get("abstract"))
            if papers_with_abstract < len(found) * 0.5:
                issues.append("部分论文缺少摘要，可能影响分析质量")

        if not issues:
            issues.append("文献综述基本完整")

        return issues

    async def _generate_recommendations_async(self, papers: List) -> List[str]:
        """生成改进建议（基于论文列表的轻量版本）"""
        recommendations = []

        if len(papers) < 10:
            recommendations.append("扩大搜索关键词范围，添加同义词和相关术语")
        else:
            recommendations.append("文献综述较为完整，可进入下一阶段")

        return recommendations[:5]
