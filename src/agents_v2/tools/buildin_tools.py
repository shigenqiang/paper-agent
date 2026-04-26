"""
内置工具实现

提供Paper Agent系统常用的内置工具
"""
import logging
from typing import Any, Dict, List, Optional
from .tool_spec import ToolSpec, ParameterSpec, ParameterType
from .registry import ToolRegistry

logger = logging.getLogger(__name__)


# ============== 搜索工具 ==============

async def search_papers_handler(query: str, source: str = "all", max_results: int = 10) -> Dict[str, Any]:
    """
    搜索学术论文

    Args:
        query: 搜索查询词
        source: 搜索来源 (arxiv/pubmed/all)
        max_results: 最大结果数
    """
    from src.agents_v2.qa import PaperSearchAgent

    try:
        agent = PaperSearchAgent()
        result = await agent.execute(query, {"source": source, "max_results": max_results})

        papers = result.get("papers", [])
        return {
            "total": len(papers),
            "papers": papers[:max_results],
            "query": query,
            "source": source
        }
    except Exception as e:
        logger.error(f"search_papers failed: {e}")
        return {"error": str(e), "total": 0, "papers": []}


async def get_paper_details_handler(paper_id: str) -> Dict[str, Any]:
    """
    获取论文详细信息

    Args:
        paper_id: 论文ID或URL
    """
    return {
        "paper_id": paper_id,
        "title": f"Paper details for {paper_id}",
        "abstract": "Paper abstract...",
        "authors": ["Author 1", "Author 2"],
        "year": 2024
    }


# ============== 草稿工具 ==============

_drafts_storage: Dict[str, Dict] = {}


async def save_draft_handler(content: str, title: str = "Untitled", metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    保存论文草稿

    Args:
        content: 草稿内容
        title: 标题
        metadata: 元数据
    """
    import uuid

    draft_id = f"draft_{uuid.uuid4().hex[:12]}"
    draft_data = {
        "draft_id": draft_id,
        "title": title,
        "content": content,
        "metadata": metadata or {},
        "version": 1
    }

    _drafts_storage[draft_id] = draft_data

    return {
        "success": True,
        "draft_id": draft_id,
        "message": f"Draft saved as {title}"
    }


async def load_draft_handler(draft_id: str) -> Dict[str, Any]:
    """
    加载论文草稿

    Args:
        draft_id: 草稿ID
    """
    if draft_id not in _drafts_storage:
        return {
            "success": False,
            "error": f"Draft not found: {draft_id}"
        }

    return {
        "success": True,
        **(_drafts_storage[draft_id])
    }


async def list_drafts_handler(limit: int = 20) -> Dict[str, Any]:
    """
    列出所有草稿

    Args:
        limit: 返回数量限制
    """
    drafts = list(_drafts_storage.values())[:limit]
    return {
        "total": len(_drafts_storage),
        "drafts": [
            {"draft_id": d["draft_id"], "title": d["title"], "version": d["version"]}
            for d in drafts
        ]
    }


# ============== 验证工具 ==============

async def validate_format_handler(content: str, format_type: str = "academic") -> Dict[str, Any]:
    """
    验证论文格式

    Args:
        content: 论文内容
        format_type: 格式类型 (academic/proposal/report)
    """
    issues = []
    suggestions = []

    # 基本检查
    if len(content) < 100:
        issues.append("内容过短，可能不完整")

    if format_type == "academic":
        # 检查学术论文格式
        if "# " not in content and "## " not in content:
            issues.append("缺少章节标题格式")

        if "abstract" not in content.lower():
            issues.append("缺少摘要部分")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "suggestions": suggestions,
        "format_type": format_type
    }


# ============== 翻译工具 ==============

async def translate_text_handler(text: str, target_lang: str = "en", source_lang: str = "auto") -> Dict[str, Any]:
    """
    翻译文本

    Args:
        text: 待翻译文本
        target_lang: 目标语言 (en/zh/ja/ko)
        source_lang: 源语言 (auto/默认自动检测)
    """
    from src.agents_v2.unified import TranslationWrapper

    try:
        translator = TranslationWrapper()

        if target_lang == "zh":
            result = await translator.process_english_first(
                text, None, translate_output=True
            )
        else:
            # 简化处理，实际应该用更复杂的翻译逻辑
            result = {"translated": text, "target_lang": target_lang}

        return {
            "success": True,
            "original": text,
            "translated": result.get("translated", text),
            "target_lang": target_lang
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "original": text
        }


# ============== 格式化工具 ==============

async def format_citation_handler(paper_info: Dict, style: str = "apa") -> Dict[str, Any]:
    """
    格式化论文引用

    Args:
        paper_info: 论文信息 {title, authors, year, journal}
        style: 引用格式 (apa/ieee/mla/chicago)
    """
    title = paper_info.get("title", "")
    authors = paper_info.get("authors", [])
    year = paper_info.get("year", 2024)
    journal = paper_info.get("journal", "")

    if style == "apa":
        citation = f"{', '.join(authors)} ({year}). {title}. {journal}."
    elif style == "ieee":
        citation = f"{', '.join(authors)}, \"{title},\" {journal}, {year}."
    else:
        citation = f"{', '.join(authors)} ({year}). {title}. {journal}."

    return {
        "success": True,
        "citation": citation,
        "style": style
    }


# ============== 摘要工具 ==============

async def summarize_text_handler(text: str, max_length: int = 200) -> Dict[str, Any]:
    """
    生成文本摘要

    Args:
        text: 待摘要文本
        max_length: 最大摘要长度
    """
    # 简单的摘要逻辑（实际应该用LLM）
    sentences = text.split(". ")
    if len(sentences) <= 3:
        summary = text
    else:
        summary = ". ".join(sentences[:3]) + "."

    if len(summary) > max_length:
        summary = summary[:max_length] + "..."

    return {
        "success": True,
        "original_length": len(text),
        "summary": summary,
        "max_length": max_length
    }


# ============== 关键词提取工具 ==============

async def extract_keywords_handler(text: str, max_keywords: int = 10) -> Dict[str, Any]:
    """
    提取文本关键词

    Args:
        text: 输入文本
        max_keywords: 最大关键词数量
    """
    # 简单的关键词提取（实际应该用NLP）
    import re
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())

    # 停用词
    stop_words = {"that", "this", "with", "from", "they", "have", "been", "will", "would", "could", "should"}
    filtered = [w for w in words if w not in stop_words]

    # 词频统计
    from collections import Counter
    word_freq = Counter(filtered)
    top_keywords = [word for word, _ in word_freq.most_common(max_keywords)]

    return {
        "success": True,
        "keywords": top_keywords,
        "total_unique_words": len(word_freq)
    }


# ============== 参考文献检查工具 ==============

_reference_storage: Dict[str, List[Dict]] = {}


async def add_reference_handler(paper_id: str, references: List[Dict]) -> Dict[str, Any]:
    """
    添加参考文献到库

    Args:
        paper_id: 论文ID
        references: 参考文献列表
    """
    _reference_storage[paper_id] = references

    return {
        "success": True,
        "paper_id": paper_id,
        "added_count": len(references)
    }


async def check_duplicates_handler(paper_id: str, new_references: List[Dict]) -> Dict[str, Any]:
    """
    检查重复参考文献

    Args:
        paper_id: 论文ID
        new_references: 新增的参考文献列表
    """
    existing = _reference_storage.get(paper_id, [])
    existing_titles = {ref.get("title", "").lower() for ref in existing}

    duplicates = []
    new_unique = []

    for ref in new_references:
        title = ref.get("title", "").lower()
        if title in existing_titles:
            duplicates.append(ref)
        else:
            new_unique.append(ref)

    return {
        "success": True,
        "duplicates_found": len(duplicates),
        "duplicates": duplicates,
        "new_unique": len(new_unique)
    }


# ============== 搜索工具注册 ==============

def register_all(registry: ToolRegistry) -> None:
    """注册所有内置工具"""

    # 搜索工具
    registry.register(ToolSpec(
        name="search_papers",
        description="搜索学术论文，支持arXiv和PubMed",
        parameters=[
            ParameterSpec("query", ParameterType.STRING, "搜索查询词", required=True),
            ParameterSpec("source", ParameterType.STRING, "搜索来源: arxiv/pubmed/all", required=False, default="all"),
            ParameterSpec("max_results", ParameterType.INTEGER, "最大结果数", required=False, default=10)
        ],
        handler=search_papers_handler,
        category="search"
    ))

    registry.register(ToolSpec(
        name="get_paper_details",
        description="获取论文详细信息",
        parameters=[
            ParameterSpec("paper_id", ParameterType.STRING, "论文ID或URL", required=True)
        ],
        handler=get_paper_details_handler,
        category="search"
    ))

    # 草稿工具
    registry.register(ToolSpec(
        name="save_draft",
        description="保存论文草稿到本地存储",
        parameters=[
            ParameterSpec("content", ParameterType.STRING, "草稿内容", required=True),
            ParameterSpec("title", ParameterType.STRING, "草稿标题", required=False, default="Untitled"),
            ParameterSpec("metadata", ParameterType.OBJECT, "额外元数据", required=False)
        ],
        handler=save_draft_handler,
        category="storage"
    ))

    registry.register(ToolSpec(
        name="load_draft",
        description="加载已保存的论文草稿",
        parameters=[
            ParameterSpec("draft_id", ParameterType.STRING, "草稿ID", required=True)
        ],
        handler=load_draft_handler,
        category="storage"
    ))

    registry.register(ToolSpec(
        name="list_drafts",
        description="列出所有已保存的草稿",
        parameters=[
            ParameterSpec("limit", ParameterType.INTEGER, "返回数量限制", required=False, default=20)
        ],
        handler=list_drafts_handler,
        category="storage"
    ))

    # 验证工具
    registry.register(ToolSpec(
        name="validate_format",
        description="验证论文格式是否符合标准",
        parameters=[
            ParameterSpec("content", ParameterType.STRING, "论文内容", required=True),
            ParameterSpec("format_type", ParameterType.STRING, "格式类型: academic/proposal/report", required=False, default="academic")
        ],
        handler=validate_format_handler,
        category="validation"
    ))

    # 翻译工具
    registry.register(ToolSpec(
        name="translate_text",
        description="翻译文本，支持中英互译",
        parameters=[
            ParameterSpec("text", ParameterType.STRING, "待翻译文本", required=True),
            ParameterSpec("target_lang", ParameterType.STRING, "目标语言: en/zh", required=False, default="en"),
            ParameterSpec("source_lang", ParameterType.STRING, "源语言: auto/zh/en", required=False, default="auto")
        ],
        handler=translate_text_handler,
        category="utility"
    ))

    # 格式化工具
    registry.register(ToolSpec(
        name="format_citation",
        description="格式化论文引用",
        parameters=[
            ParameterSpec("paper_info", ParameterType.OBJECT, "论文信息 {title, authors, year, journal}", required=True),
            ParameterSpec("style", ParameterType.STRING, "引用格式: apa/ieee/mla/chicago", required=False, default="apa")
        ],
        handler=format_citation_handler,
        category="formatting"
    ))

    # 摘要工具
    registry.register(ToolSpec(
        name="summarize_text",
        description="生成文本摘要",
        parameters=[
            ParameterSpec("text", ParameterType.STRING, "待摘要文本", required=True),
            ParameterSpec("max_length", ParameterType.INTEGER, "最大摘要长度", required=False, default=200)
        ],
        handler=summarize_text_handler,
        category="utility"
    ))

    # 关键词提取工具
    registry.register(ToolSpec(
        name="extract_keywords",
        description="提取文本关键词",
        parameters=[
            ParameterSpec("text", ParameterType.STRING, "输入文本", required=True),
            ParameterSpec("max_keywords", ParameterType.INTEGER, "最大关键词数量", required=False, default=10)
        ],
        handler=extract_keywords_handler,
        category="utility"
    ))

    # 参考文献工具
    registry.register(ToolSpec(
        name="add_reference",
        description="添加参考文献到库",
        parameters=[
            ParameterSpec("paper_id", ParameterType.STRING, "论文ID", required=True),
            ParameterSpec("references", ParameterType.ARRAY, "参考文献列表", required=True)
        ],
        handler=add_reference_handler,
        category="reference"
    ))

    registry.register(ToolSpec(
        name="check_duplicates",
        description="检查重复参考文献",
        parameters=[
            ParameterSpec("paper_id", ParameterType.STRING, "论文ID", required=True),
            ParameterSpec("new_references", ParameterType.ARRAY, "新增参考文献列表", required=True)
        ],
        handler=check_duplicates_handler,
        category="reference"
    ))

    logger.info(f"Registered {len(registry.list_tools())} builtin tools")
