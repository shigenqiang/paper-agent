"""搜索词优化 — 通过 LLM 提取核心主题词"""

from __future__ import annotations

from loguru import logger


def refine_query(query: str, max_words: int = 6) -> str:
    """通过 LLM 提取核心学术搜索词

    去除泛化词（approach, method, based on 等），保留核心主题。
    LLM 不可用时回退到原查询。

    Args:
        query: 原始搜索词
        max_words: 保留的最大词数

    Returns:
        精简后的搜索词
    """
    words = query.split()
    if len(words) <= max_words:
        return query.strip()

    try:
        from src.agents_v3.research_workspace.llm.service import get_llm_service
        llm = get_llm_service()

        system_prompt = (
            "You are an academic search query optimizer. "
            "Extract the core research topic from the user's query. "
            "Remove filler words (approach, method, based on, using, for, novel, efficient, etc.). "
            "Keep only the key technical terms that define the research topic. "
            "Return ONLY the optimized query, no explanation."
        )
        user_prompt = f"Optimize this search query for academic paper search (max {max_words} words): {query}"

        result = llm.invoke(system_prompt, user_prompt).strip().strip('"').strip("'")
        if result and len(result.split()) >= 2:
            logger.info(f"Query optimized: \"{query}\" → \"{result}\"")
            return result
    except Exception as e:
        logger.warning(f"LLM query optimization failed: {e}")

    return query.strip()


def truncate_query(query: str, max_chars: int = 250) -> str:
    """截断查询词到指定字符数（用于 arXiv 等有长度限制的 API）"""
    if len(query) <= max_chars:
        return query

    truncated = query[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.8:
        truncated = truncated[:last_space]

    return truncated


def split_query(query: str) -> list[str]:
    """将长查询拆分为多个更精确的子查询（通过 LLM 判断）"""
    words = query.split()
    if len(words) <= 4:
        return [query]

    try:
        from src.agents_v3.research_workspace.llm.service import get_llm_service
        llm = get_llm_service()

        system_prompt = (
            "You are an academic search query optimizer. "
            "If the query contains multiple distinct research concepts, split it into 2-3 sub-queries. "
            "Each sub-query should be a focused search on one concept. "
            "Return a JSON array of strings. If no splitting needed, return a single-element array."
        )
        user_prompt = f"Split this query if needed: {query}"

        import json
        result = llm.invoke(system_prompt, user_prompt).strip()
        # 提取 JSON 数组
        start = result.find("[")
        end = result.rfind("]")
        if start != -1 and end != -1:
            sub_queries = json.loads(result[start:end + 1])
            if isinstance(sub_queries, list) and len(sub_queries) >= 1:
                return [str(q).strip() for q in sub_queries if q]
    except Exception as e:
        logger.warning(f"LLM query split failed: {e}")

    return [query]
