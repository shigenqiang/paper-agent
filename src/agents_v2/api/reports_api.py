"""
Reports API - Paper Intelligence Digest API (论文资讯快报)

Auto-generated daily/weekly/monthly paper intelligence reports.
"""
import time
import json
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from aiohttp import web
import uuid
import asyncio

from src.agents_v2.api.paper_api import DEFAULT_API_KEY, DEFAULT_BASE_URL

logger = logging.getLogger(__name__)

# 持久化存储路径
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "../../data")
DIGESTS_FILE = os.path.join(STORAGE_DIR, "digests.json")

# 确保存储目录存在
os.makedirs(STORAGE_DIR, exist_ok=True)

# In-memory storage for paper digests
DIGESTS_STORAGE: Dict[str, Dict] = {}


def _load_digests() -> Dict[str, Dict]:
    """从文件加载日报数据"""
    if os.path.exists(DIGESTS_FILE):
        try:
            with open(DIGESTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} digests from storage")
                return data
        except Exception as e:
            logger.warning(f"Failed to load digests from storage: {e}")
    return {}


def _save_digests() -> None:
    """保存日报数据到文件"""
    try:
        with open(DIGESTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(DIGESTS_STORAGE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save digests to storage: {e}")


# 启动时加载已有数据
DIGESTS_STORAGE = _load_digests()

# Report statuses
STATUS = {
    "generating": "生成中",
    "ready": "就绪",
    "error": "错误"
}


def get_digest_or_404(digest_id: str) -> Optional[Dict]:
    """Get digest by ID or return None"""
    return DIGESTS_STORAGE.get(digest_id)


def generate_digest_id(digest_type: str) -> str:
    """Generate a unique digest ID"""
    return f"{digest_type}_{uuid.uuid4().hex[:8]}"


async def search_papers_for_digest(digest_type: str, date_range: Dict[str, str]) -> List[Dict]:
    """
    Search papers for a specific time period using user's keywords

    Args:
        digest_type: daily, weekly, or monthly
        date_range: dict with start and end dates

    Returns:
        List of paper search results
    """
    try:
        from src.agents_v2.search import search_all, MergeConfig, merge_search_results

        # 从设置获取用户关键词和选择的来源
        from src.agents_v2.api.paper_api import SETTINGS_STORAGE
        keywords = SETTINGS_STORAGE.get("keywords", None)
        # 如果关键词为空或None，使用默认关键词
        if not keywords:
            keywords = [
                "machine learning",
                "deep learning",
                "natural language processing",
                "computer vision",
                "artificial intelligence"
            ]
        enabled_sources = SETTINGS_STORAGE.get("sources", ["arxiv", "pubmed", "semantic_scholar", "openalex"])

        all_papers = []
        seen_ids = set()

        # 根据报告类型决定每关键词搜索数量和总论文数量
        paper_limits = {"daily": 20, "weekly": 40, "monthly": 60}
        per_keyword_limit = {"daily": 15, "weekly": 15, "monthly": 15}
        total_limit = paper_limits.get(digest_type, 20)
        per_kw_limit = per_keyword_limit.get(digest_type, 15)

        for query in keywords:
            try:
                # 根据用户选择的来源进行搜索
                from src.agents_v2.search.search_factory import SearchFactory
                search_results = []
                for source in enabled_sources:
                    searcher = SearchFactory.get(source)
                    if searcher:
                        result = await searcher.search(query, max_results=per_kw_limit)
                        search_results.append(result)

                # 合并去重
                config = MergeConfig(
                    title_similarity_threshold=0.8,
                    citation_weight=0.4,
                    year_weight=0.3,
                    source_weight=0.1,
                    relevance_weight=0.2
                )

                results = await merge_search_results(search_results, config=config)

                for r in results:
                    if r.paper_id not in seen_ids:
                        seen_ids.add(r.paper_id)
                        all_papers.append({
                            "paper_id": r.paper_id,
                            "title": r.title,
                            "abstract": r.abstract,
                            "authors": r.authors,
                            "year": r.year,
                            "venue": r.venue,
                            "url": r.url,
                            "citations": r.citations,
                            "doi": r.doi,
                            "sources": r.sources,
                            "keywords": query.split()
                        })
                        # 只有在超过总限制时才中断，而不是每个关键词后立即限制
                        if len(all_papers) >= total_limit:
                            break

            except Exception as e:
                # API限流、超时等是预期内的错误，记录为WARNING而非ERROR
                error_str = str(e)
                if any(keyword in error_str.lower() for keyword in ['rate limit', 'timeout', 'connection', 'network', '10054', '10060', '429', '500', '503']):
                    logger.warning(f"Search API temporarily unavailable for query '{query}': {error_str[:80]}")
                else:
                    logger.warning(f"Search error for query '{query}': {error_str}")
                continue

            # 如果已经达到总限制，跳出关键词循环
            if len(all_papers) >= total_limit:
                break

        return all_papers

    except Exception as e:
        logger.error(f"Search papers for digest error: {e}")
        return []


async def generate_digest_summary(papers: List[Dict], digest_type: str) -> str:
    """
    Generate analytical report summarizing paper content using DigestReportAgent

    Args:
        papers: List of papers
        digest_type: daily, weekly, monthly

    Returns:
        Generated analytical summary with citations and references
    """
    from datetime import datetime
    if not papers:
        return "# 本期资讯暂无相关论文\n\n请稍后重试或调整关键词。"

    from src.agents_v2.api.paper_api import SETTINGS_STORAGE
    user_keywords = SETTINGS_STORAGE.get("keywords", None) or []
    date_str = datetime.now().strftime('%Y-%m-%d')

    # 计算日期范围
    now = datetime.now()
    if digest_type == "daily":
        date_range = now.strftime('%Y-%m-%d')
    elif digest_type == "weekly":
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        date_range = f"{start_of_week.strftime('%Y-%m-%d')} 至 {end_of_week.strftime('%Y-%m-%d')}"
    else:
        date_range = f"{now.strftime('%Y年%m月')}"

    # 使用 DigestReportAgent 生成报告
    try:
        from src.agents_v2.paper_agents import DigestReportAgent
        from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

        llm_config = LLMConfig(
            provider="openai",
            model_name=os.getenv("LLM_MODEL", "MiniMax-M2.7"),
            temperature=0.7,
            api_key=DEFAULT_API_KEY,
            base_url=DEFAULT_BASE_URL
        )

        agent = DigestReportAgent(llm_config)

        result = await agent.execute({
            "papers": papers,
            "keywords": user_keywords,
            "digest_type": digest_type,
            "date_range": date_range,
            "sources": SETTINGS_STORAGE.get("sources", [])
        })

        if result.success:
            report = result.result.get("report", "")
            # 验证报告内容不是 HTML（网关错误检测）
            if report.strip().startswith('<!') or report.strip().startswith('<html'):
                logger.error("DigestReportAgent returned HTML content - API gateway error")
                raise ValueError("Report contains HTML from API gateway error, falling back to template")
            report += f"\n\n---\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += f"**质量评分**: {result.quality_score:.2f}\n"
            report += f"**报告类型**: {digest_type}\n"
            logger.info(f"DigestReportAgent 生成成功，质量评分: {result.quality_score}")
            return report
        else:
            logger.warning(f"DigestReportAgent 执行失败: {result.error}")

    except Exception as e:
        logger.error(f"使用 DigestReportAgent 生成报告时出错: {e}")

    # Fallback: 使用模板生成
    return _generate_template_report(papers, digest_type, date_str, user_keywords)


def _generate_template_report(papers: List[Dict], digest_type: str, date_str: str, user_keywords: List[str]) -> str:
    """模板方式生成报告（fallback）"""
    from datetime import datetime
    total_count = len(papers)
    sources = {}
    for paper in papers:
        for src in paper.get("sources", []):
            sources[src] = sources.get(src, 0) + 1

    kw_str = '、'.join(user_keywords) if user_keywords else '学术领域'
    source_str = '、'.join(sources.keys()) if sources else '未知'

    summary = f"# {type_name}学术资讯报告 - {date_str}\n\n"

    # 整体概述
    summary += "## 概述\n\n"
    summary += (
        f"本期从 {source_str} 收录了 {total_count} 篇与 {kw_str} 相关的最新研究论文。"
        f"以下按研究方向对本期论文进行综合分析。\n\n"
    )

    # 研究主题聚类
    research_themes = _extract_research_themes(papers)
    if research_themes:
        summary += "## 研究方向分析\n\n"
        for i, theme in enumerate(research_themes, 1):
            theme_papers = theme["papers"]
            summary += f"### {i}. {theme['name']}\n\n"
            summary += f"{theme['description']}\n\n"

            # 综合分析该主题下的论文
            for paper in theme_papers:
                title = paper.get('title', '未知标题')
                abstract = paper.get('abstract', '')
                cite_idx = paper.get("citation_index")
                authors = ', '.join(paper.get('authors', [])[:2])

                if abstract:
                    contribution = _extract_contribution(abstract)
                    summary += f"- **{title}** [{cite_idx}]：{contribution}\n"
                else:
                    summary += f"- **{title}** [{cite_idx}]（{authors}）\n"
            summary += "\n"

    # 参考文献列表
    summary += "## 参考文献\n\n"
    for paper in papers:
        idx = paper.get("citation_index", 0)
        authors = ', '.join(paper.get('authors', [])[:3])
        if len(paper.get('authors', [])) > 3:
            authors += ' et al.'
        title = paper.get('title', '未知标题')
        year = paper.get('year', '未知')
        venue = paper.get('venue', '')
        url = paper.get('url', '')
        source = paper.get('sources', ['未知'])[0] if paper.get('sources') else '未知'

        if url:
            summary += f"[{idx}] {authors}. \"{title}\". {venue}, {year}. [{source}]({url})\n\n"
        else:
            summary += f"[{idx}] {authors}. \"{title}\". {venue}, {year}. {source}\n\n"

    summary += f"---\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    return summary


def _extract_research_themes(papers: List[Dict]) -> List[Dict]:
    """从论文中提取研究主题聚类"""
    themes = []

    keyword_papers = {}
    for paper in papers:
        abstract = (paper.get('abstract', '') + ' ' + paper.get('title', '')).lower()
        direction_keywords = {
            "大语言模型与对话AI": ["large language model", "llm", "chatgpt", "gpt", "dialogue", "conversational", "text generation"],
            "深度学习与神经网络": ["neural network", "deep learning", "transformer", "attention", "convolutional", "residual"],
            "计算机视觉与图像识别": ["image", "vision", "object detection", "segmentation", "classification", "visual"],
            "自然语言处理": ["natural language", "nlp", "sentiment", "text", "language understanding", "translation"],
            "强化学习与决策": ["reinforcement learning", "policy", "reward", "agent", "decision making", "markov"],
            "图神经网络": ["graph neural", "gcn", "graph attention", "knowledge graph", "network embedding"],
            "联邦学习与隐私": ["federated", "privacy", "secure", "distributed learning", "differential privacy"],
            "医学与生物信息学": ["medical", "clinical", "diagnosis", "biomarker", "genomic", "protein", "drug"],
            "机器学习优化方法": ["optimization", "gradient", "convergence", "training", "loss function", "regularization"],
            "可解释性与公平性": ["interpretable", "explainable", "fairness", "bias", "transparency", "trustworthy"],
        }

        matched_themes = []
        for theme_name, keywords in direction_keywords.items():
            for kw in keywords:
                if kw in abstract:
                    matched_themes.append(theme_name)
                    break

        if matched_themes:
            theme = matched_themes[0]
        else:
            theme = "其他研究方向"

        if theme not in keyword_papers:
            keyword_papers[theme] = []
        keyword_papers[theme].append(paper)

    theme_descriptions = {
        "大语言模型与对话AI": "大语言模型在对话理解、文本生成和指令跟随方面的最新进展",
        "深度学习与神经网络": "新型网络架构和训练方法的研究",
        "计算机视觉与图像识别": "图像理解、目标检测和视觉生成的新方法",
        "自然语言处理": "文本分析、情感理解和机器翻译的技术突破",
        "强化学习与决策": "智能体在复杂环境中的学习和决策策略",
        "图神经网络": "图结构数据的表示学习和推理方法",
        "联邦学习与隐私": "分布式机器学习中的隐私保护和数据安全",
        "医学与生物信息学": "AI在医学诊断、基因组学和药物发现中的应用",
        "机器学习优化方法": "提升模型训练效率和收敛性的优化技术",
        "可解释性与公平性": "提高AI系统透明度、公平性和可信度的研究",
    }

    for theme_name, theme_papers in sorted(keyword_papers.items(), key=lambda x: len(x[1]), reverse=True):
        if len(theme_papers) >= 1:
            themes.append({
                "name": theme_name,
                "description": f"共 {len(theme_papers)} 篇论文涉及该方向。{theme_descriptions.get(theme_name, '')}",
                "papers": theme_papers[:5]
            })

    return themes[:5]


def _extract_contribution(abstract: str) -> str:
    """从摘要中提取论文的研究贡献"""
    if not abstract:
        return "本文介绍了相关领域的研究进展。"

    text = abstract[:300]
    sentences = text.replace('. ', '.|||').replace('。', '。|||').split('|||')
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        lower = sent.lower()
        if any(kw in lower for kw in ['propose', 'introduce', 'present', 'develop', 'novel', 'new',
                                        '提出', '开发', '设计', '新方法', '首次']):
            return sent

    first_sentence = sentences[0].strip() if sentences else text[:150]
    return first_sentence


# Digest CRUD endpoints
async def list_digests(request: web.Request) -> web.Response:
    """GET /reports - List all paper digests with optional filtering"""
    try:
        digest_type = request.query.get("type")  # daily, weekly, monthly
        status = request.query.get("status")

        digests = list(DIGESTS_STORAGE.values())

        if digest_type:
            digests = [d for d in digests if d.get("type") == digest_type]
        if status:
            digests = [d for d in digests if d.get("status") == status]

        # Sort by created_at descending
        digests.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return web.json_response({
            "success": True,
            "data": digests,
            "total": len(digests),
        })
    except Exception as e:
        logger.error(f"List digests error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def create_digest(request: web.Request) -> web.Response:
    """POST /reports - Create a new paper digest (async generation)"""
    try:
        data = await request.json()
        digest_type = data.get("type", "daily")

        now = datetime.now()

        # Generate title based on type and date
        if digest_type == "daily":
            title = now.strftime("%Y-%m-%d") + " 每日学术资讯"
            date_range = now.strftime("%Y-%m-%d")
            start_date = now.replace(hour=0, minute=0, second=0)
            end_date = now
        elif digest_type == "weekly":
            week_num = now.isocalendar()[1]
            start_of_week = now - timedelta(days=now.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            title = f"{now.strftime('%Y年%W周')}学术资讯"
            date_range = f"{start_of_week.strftime('%Y-%m-%d')} 至 {end_of_week.strftime('%Y-%m-%d')}"
            start_date = start_of_week.replace(hour=0, minute=0, second=0)
            end_date = end_of_week.replace(hour=23, minute=59, second=59)
        else:  # monthly
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0)
            end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            title = now.strftime("%Y年%m月") + "学术资讯"
            date_range = f"{start_of_month.strftime('%Y-%m-%d')} 至 {end_of_month.strftime('%Y-%m-%d')}"
            start_date = start_of_month
            end_date = end_of_month

        digest_id = generate_digest_id(digest_type)

        digest = {
            "id": digest_id,
            "type": digest_type,
            "title": title,
            "date_range": date_range,
            "content": "",
            "summary": "",
            "papers": [],
            "sources": [],
            "progress": 0,
            "status": "generating",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "error": None,
        }

        DIGESTS_STORAGE[digest_id] = digest
        _save_digests()  # 持久化保存

        # 异步生成内容
        asyncio.create_task(generate_digest_content(digest_id, {
            "start": start_date,
            "end": end_date,
            "type": digest_type
        }))

        return web.json_response({
            "success": True,
            "data": digest,
        }, status=201)
    except Exception as e:
        logger.error(f"Create digest error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def generate_digest_content(digest_id: str, params: Dict):
    """
    Async task to generate digest content

    Args:
        digest_id: Digest ID
        params: Generation parameters including date range
    """
    try:
        digest = DIGESTS_STORAGE.get(digest_id)
        if not digest:
            return

        # 更新状态
        digest["status"] = "generating"
        digest["progress"] = 10
        digest["updated_at"] = datetime.now().isoformat()

        # 搜索论文
        papers = await search_papers_for_digest(params["type"], {
            "start": params["start"].isoformat(),
            "end": params["end"].isoformat()
        })

        digest["progress"] = 50
        digest["updated_at"] = datetime.now().isoformat()

        # 提取来源
        sources_set = set()
        for paper in papers:
            sources_set.update(paper.get("sources", []))
        digest["sources"] = list(sources_set)
        digest["papers"] = papers

        digest["progress"] = 70
        digest["updated_at"] = datetime.now().isoformat()

        # 生成摘要
        summary = await generate_digest_summary(papers, params["type"])
        
        # 从报告内容中提取标题（第一行Markdown标题）
        title_match = re.search(r'^#\s+(.+?)$', summary, re.MULTILINE)
        if title_match:
            digest["title"] = title_match.group(1).strip()
        
        digest["summary"] = summary
        digest["content"] = summary  # 兼容旧字段

        # 完成
        digest["status"] = "ready"
        digest["progress"] = 100
        digest["updated_at"] = datetime.now().isoformat()

        logger.info(f"Digest {digest_id} generated successfully with {len(papers)} papers")

    except Exception as e:
        logger.error(f"Generate digest content error: {e}")
        if digest_id in DIGESTS_STORAGE:
            DIGESTS_STORAGE[digest_id]["status"] = "error"
            DIGESTS_STORAGE[digest_id]["error"] = str(e)
            DIGESTS_STORAGE[digest_id]["updated_at"] = datetime.now().isoformat()
            _save_digests()  # 持久化保存错误状态


async def get_digest(request: web.Request) -> web.Response:
    """GET /reports/{id} - Get digest by ID"""
    try:
        digest_id = request.match_info["id"]
        digest = get_digest_or_404(digest_id)

        if not digest:
            return web.json_response({
                "success": False,
                "error": "Digest not found"
            }, status=404)

        return web.json_response({
            "success": True,
            "data": digest,
        })
    except Exception as e:
        logger.error(f"Get digest error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def update_digest(request: web.Request) -> web.Response:
    """PUT /reports/{id} - Update digest (only for regenerating)"""
    try:
        digest_id = request.match_info["id"]
        digest = get_digest_or_404(digest_id)

        if not digest:
            return web.json_response({
                "success": False,
                "error": "Digest not found"
            }, status=404)

        data = await request.json()

        # 重新生成
        if data.get("regenerate"):
            digest["status"] = "generating"
            digest["progress"] = 0
            digest["updated_at"] = datetime.now().isoformat()

            # 重新计算日期范围
            now = datetime.now()
            if digest["type"] == "daily":
                start_date = now.replace(hour=0, minute=0, second=0)
                end_date = now
            elif digest["type"] == "weekly":
                start_of_week = now - timedelta(days=now.weekday())
                end_of_week = start_of_week + timedelta(days=6)
                start_date = start_of_week.replace(hour=0, minute=0, second=0)
                end_date = end_of_week.replace(hour=23, minute=59, second=59)
            else:
                start_date = now.replace(day=1, hour=0, minute=0, second=0)
                end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

            asyncio.create_task(generate_digest_content(digest_id, {
                "start": start_date,
                "end": end_date,
                "type": digest["type"]
            }))
            _save_digests()  # 持久化保存

        return web.json_response({
            "success": True,
            "data": digest,
        })
    except Exception as e:
        logger.error(f"Update digest error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def delete_digest(request: web.Request) -> web.Response:
    """DELETE /reports/{id} - Delete digest"""
    try:
        digest_id = request.match_info["id"]

        if digest_id not in DIGESTS_STORAGE:
            return web.json_response({
                "success": False,
                "error": "Digest not found"
            }, status=404)

        del DIGESTS_STORAGE[digest_id]
        _save_digests()  # 持久化保存

        return web.json_response({
            "success": True,
            "message": "Digest deleted",
        })
    except Exception as e:
        logger.error(f"Delete digest error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


# Filtered digest lists
async def list_daily_digests(request: web.Request) -> web.Response:
    """GET /reports/daily - List daily digests"""
    try:
        digests = [d for d in DIGESTS_STORAGE.values() if d.get("type") == "daily"]
        digests.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return web.json_response({
            "success": True,
            "data": digests,
            "total": len(digests),
        })
    except Exception as e:
        logger.error(f"List daily digests error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def list_weekly_digests(request: web.Request) -> web.Response:
    """GET /reports/weekly - List weekly digests"""
    try:
        digests = [d for d in DIGESTS_STORAGE.values() if d.get("type") == "weekly"]
        digests.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return web.json_response({
            "success": True,
            "data": digests,
            "total": len(digests),
        })
    except Exception as e:
        logger.error(f"List weekly digests error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def list_monthly_digests(request: web.Request) -> web.Response:
    """GET /reports/monthly - List monthly digests"""
    try:
        digests = [d for d in DIGESTS_STORAGE.values() if d.get("type") == "monthly"]
        digests.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return web.json_response({
            "success": True,
            "data": digests,
            "total": len(digests),
        })
    except Exception as e:
        logger.error(f"List monthly digests error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


def setup_reports_routes(app: web.Application):
    """Setup all reports/digest-related routes"""
    # Digests CRUD
    app.router.add_get('/api/reports', list_digests)
    app.router.add_post('/api/reports', create_digest)
    app.router.add_get('/api/reports/{id}', get_digest)
    app.router.add_put('/api/reports/{id}', update_digest)
    app.router.add_delete('/api/reports/{id}', delete_digest)

    # Filtered lists
    app.router.add_get('/api/reports/daily', list_daily_digests)
    app.router.add_get('/api/reports/weekly', list_weekly_digests)
    app.router.add_get('/api/reports/monthly', list_monthly_digests)
