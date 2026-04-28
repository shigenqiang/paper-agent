"""
学术搜索 MCP Server
提供 Semantic Scholar 和 arXiv 论文搜索工具
"""
import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
from fastmcp import FastMCP

mcp = FastMCP("paper-search")

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_URL = "http://export.arxiv.org/api/query"


def _fetch_json(url: str, params: dict) -> dict:
    """安全发起 HTTP GET 请求并解析 JSON"""
    query_string = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    full_url = f"{url}?{query_string}"

    context = ssl.create_default_context()
    req = urllib.request.Request(full_url, headers={"User-Agent": "PaperAgent/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=15, context=context) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def search_semantic_scholar(
    query: str,
    limit: int = 20,
    year_start: int = None,
    year_end: int = None,
    fields: str = "title,authors,year,abstract,citationCount,tldr,openAccessPdf,publicationVenue,externalIds"
) -> list:
    """搜索 Semantic Scholar 学术论文。

    Args:
        query: 搜索关键词或查询语句
        limit: 返回结果数量上限 (默认 20)
        year_start: 起始年份 (如 2020)
        year_end: 结束年份 (如 2026)
        fields: 返回字段列表，逗号分隔
    """
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": fields,
    }
    if year_start or year_end:
        params["year"] = f"{year_start or ''}-{year_end or ''}"

    result = _fetch_json(SEMANTIC_SCHOLAR_URL, params)

    if "error" in result:
        return []

    papers = result.get("data", [])
    return [_normalize_semantic_scholar_paper(p) for p in papers if p]


@mcp.tool()
async def search_arxiv(
    query: str,
    max_results: int = 20,
    sort_by: str = "relevance",
) -> list:
    """搜索 arXiv 预印本论文。

    Args:
        query: 搜索关键词
        max_results: 返回结果数量上限 (默认 20)
        sort_by: 排序方式 ("relevance", "submittedDate", "lastUpdatedDate")
    """
    sort_map = {
        "relevance": "relevance",
        "submittedDate": "submittedDate",
        "lastUpdatedDate": "lastUpdatedDate",
    }
    sort = sort_map.get(sort_by, "relevance")

    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": min(max_results, 100),
        "sortBy": sort,
        "sortOrder": "descending",
    }

    result = _fetch_json(ARXIV_URL, params)
    if "error" in result:
        return []

    return _parse_arxiv_response(result)


@mcp.tool()
async def download_paper_pdf(pdf_url: str, save_path: str) -> str:
    """下载论文 PDF 到本地路径。

    Args:
        pdf_url: PDF 文件的 URL
        save_path: 保存的本地路径
    """
    context = ssl.create_default_context()
    req = urllib.request.Request(pdf_url, headers={"User-Agent": "PaperAgent/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60, context=context) as resp:
            with open(save_path, "wb") as f:
                f.write(resp.read())
        return f"Saved to {save_path}"
    except Exception as e:
        return f"Download failed: {e}"


# ─── Normalization helpers ───────────────────────────────────────────────

def _normalize_semantic_scholar_paper(paper: dict) -> dict:
    """将 Semantic Scholar API 结果统一为 Paper 格式"""
    authors = paper.get("authors", [])
    author_names = [a.get("name", "Unknown") for a in authors[:5]] if isinstance(authors, list) else []

    year = paper.get("year")
    published_date = f"{year}-01-01" if year else None

    return {
        "paper_id": paper.get("paperId", ""),
        "title": paper.get("title", ""),
        "authors": author_names,
        "abstract": paper.get("abstract", ""),
        "url": f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
        "pdf_url": paper.get("openAccessPdf", {}).get("url") if paper.get("openAccessPdf") else None,
        "published_date": published_date,
        "source": "semantic_scholar",
        "categories": [],
        "doi": paper.get("externalIds", {}).get("DOI") if paper.get("externalIds") else None,
        "citation_count": paper.get("citationCount", 0),
        "tldr": paper.get("tldr", {}).get("text") if paper.get("tldr") else None,
    }


def _parse_arxiv_response(xml_text: str) -> list:
    """解析 arXiv Atom XML 响应"""
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    papers = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        published_el = entry.find("atom:published", ns)
        id_el = entry.find("atom:id", ns)

        title = title_el.text.strip() if title_el is not None else ""
        abstract = summary_el.text.strip() if summary_el is not None else ""
        published = published_el.text[:10] if published_el is not None else None
        entry_id = id_el.text.strip() if id_el is not None else ""

        # 提取作者
        author_names = []
        for author in entry.findall("atom:author", ns):
            name_el = author.find("atom:name", ns)
            if name_el is not None:
                author_names.append(name_el.text)

        # 提取标签
        categories = []
        for category in entry.findall("atom:category", ns):
            term = category.get("term")
            if term:
                categories.append(term)

        # 提取 PDF 链接
        pdf_url = None
        for link in entry.findall("atom:link", ns):
            if link.get("type") == "application/pdf":
                pdf_url = link.get("href")

        papers.append({
            "paper_id": entry_id.split("/")[-1] if "/" in entry_id else entry_id,
            "title": title,
            "authors": author_names[:5],
            "abstract": abstract,
            "url": entry_id,
            "pdf_url": pdf_url,
            "published_date": published,
            "source": "arxiv",
            "categories": categories,
            "doi": None,
        })

    return papers


if __name__ == "__main__":
    mcp.run(transport="stdio")
