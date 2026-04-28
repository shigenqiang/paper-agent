"""
Reports API - Paper Intelligence Digest API (论文资讯快报)

Auto-generated daily/weekly/monthly paper intelligence reports.
"""
import time
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from aiohttp import web
import uuid
import asyncio

logger = logging.getLogger(__name__)

# In-memory storage for paper digests
DIGESTS_STORAGE: Dict[str, Dict] = {}

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

        # 从设置获取用户关键词，如果没有则使用默认关键词
        from src.agents_v2.api.paper_api import SETTINGS_STORAGE
        keywords = SETTINGS_STORAGE.get("keywords", [
            "machine learning",
            "deep learning",
            "natural language processing",
            "computer vision",
            "artificial intelligence"
        ])

        all_papers = []
        seen_ids = set()

        for query in keywords:
            try:
                # 使用search_all获取所有源的结果，然后合并去重
                search_results = await search_all(query=query, max_results=20)

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

                # 限制数量
                if len(all_papers) >= 50:
                    break

            except Exception as e:
                logger.error(f"Search error for query '{query}': {e}")
                continue

        return all_papers[:50]  # 最多返回50篇

    except Exception as e:
        logger.error(f"Search papers for digest error: {e}")
        return []


def generate_digest_summary(papers: List[Dict], digest_type: str) -> str:
    """
    Generate report with citation markers and reference list

    Args:
        papers: List of papers
        digest_type: daily, weekly, monthly

    Returns:
        Generated summary text with [1], [2] citations and references
    """
    from datetime import datetime
    if not papers:
        return "本期资讯暂无相关论文。"

    total_count = len(papers)
    venues = {}
    sources = {}

    for paper in papers:
        for src in paper.get("sources", []):
            sources[src] = sources.get(src, 0) + 1
        if paper.get("venue"):
            venues[paper["venue"]] = venues.get(paper["venue"], 0) + 1

    type_name = {"daily": "今日", "weekly": "本周", "monthly": "本月"}.get(digest_type, "本期")
    from src.agents_v2.api.paper_api import SETTINGS_STORAGE
    user_keywords = SETTINGS_STORAGE.get("keywords", [])
    date_str = datetime.now().strftime('%Y-%m-%d')

    # 按引用排序所有论文
    sorted_papers = sorted(papers, key=lambda x: x.get("citations", 0), reverse=True)

    # 为所有论文分配引用编号
    for idx, paper in enumerate(sorted_papers, 1):
        paper["citation_index"] = idx

    # ===== 报告正文 =====
    summary = f"# {type_name}学术资讯快报 - {date_str}\n\n"

    # 概览
    summary += "## 概览\n"
    summary += f"- 收录论文: {total_count} 篇\n"
    summary += f"- 数据来源: {', '.join(sources.keys()) if sources else '未知'}\n"
    summary += f"- 监测关键词: {', '.join(user_keywords) if user_keywords else '全部'}\n\n"

    # 热门发表场所
    if venues:
        summary += "## 热门发表场所\n"
        for k, v in sorted(venues.items(), key=lambda x: x[1], reverse=True)[:5]:
            summary += f"- {k}: {v}篇\n"
        summary += "\n"

    # 高影响力论文
    high_impact = [p for p in sorted_papers if p.get("citations", 0) > 0][:5]
    if high_impact:
        summary += "## 高影响力论文\n\n"
        for paper in high_impact:
            title = paper.get('title', '未知标题')
            authors = ', '.join(paper.get('authors', [])[:3])
            if len(paper.get('authors', [])) > 3:
                authors += ' 等'
            year = paper.get('year', '未知')
            venue = paper.get('venue', '未知')
            citations = paper.get('citations', 0)
            cite_idx = paper.get("citation_index")
            summary += f"- **{title}** [{cite_idx}] ({citations}次引用)\n"
            summary += f"  - {authors} · {venue} ({year})\n\n"

    # 新发表论文
    recent_papers = [p for p in sorted_papers if p.get("year", 0) >= 2024][:5]
    if recent_papers:
        summary += "## 最新研究进展\n\n"
        for paper in recent_papers:
            title = paper.get('title', '未知标题')
            authors = ', '.join(paper.get('authors', [])[:3])
            if len(paper.get('authors', [])) > 3:
                authors += ' 等'
            year = paper.get('year', '未知')
            cite_idx = paper.get("citation_index")
            abstract = paper.get('abstract', '')
            summary += f"- **{title}** [{cite_idx}]\n"
            summary += f"  - 作者: {authors} ({year})\n"
            if abstract:
                summary += f"  - 摘要: {abstract[:200]}{'...' if len(abstract) > 200 else ''}\n"
            summary += "\n"

    # 全部论文列表
    summary += "## 论文列表\n\n"
    for paper in sorted_papers:
        title = paper.get('title', '未知标题')
        authors = ', '.join(paper.get('authors', [])[:3])
        if len(paper.get('authors', [])) > 3:
            authors += ' 等'
        year = paper.get('year', '未知')
        venue = paper.get('venue', '')
        citations = paper.get('citations', 0)
        cite_idx = paper.get("citation_index")
        source = paper.get('sources', ['未知'])[0] if paper.get('sources') else '未知'

        summary += f"{cite_idx}. **{title}**\n"
        summary += f"   - {authors} · {venue} ({year}) · {source}"
        if citations > 0:
            summary += f" · {citations}次引用"
        summary += "\n\n"

    # 参考文献列表
    summary += "## 参考文献\n\n"
    for paper in sorted_papers:
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
        summary = generate_digest_summary(papers, params["type"])
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
