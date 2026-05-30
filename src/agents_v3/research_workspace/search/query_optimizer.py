"""搜索词优化 — 提取核心主题，去除泛化词"""

from __future__ import annotations

import re

# 学术搜索中的泛化词/停用词（会稀释核心主题）
_ACADEMIC_STOPWORDS = {
    # 介词/连词
    "for", "and", "with", "from", "using", "based", "via", "between",
    "through", "towards", "into", "over", "under", "within",
    # 泛化动词
    "approach", "method", "methods", "analysis", "study", "research",
    "investigation", "evaluation", "comparison", "review", "survey",
    "framework", "model", "models", "technique", "techniques",
    "application", "applications", "system", "systems",
    # 泛化名词
    "data", "dataset", "datasets", "problem", "problems",
    "results", "performance", "improvement", "novel", "new",
    "efficient", "effective", "robust", "advanced",
}


def refine_query(query: str, max_words: int = 6) -> str:
    """提取核心主题词，去除泛化词

    Args:
        query: 原始搜索词
        max_words: 保留的最大词数

    Returns:
        精简后的搜索词
    """
    # 分词并转小写
    words = re.findall(r"\w+", query.lower())

    if len(words) <= max_words:
        return query.strip()

    # 去除泛化词，保留核心主题词
    core_words = [w for w in words if w not in _ACADEMIC_STOPWORDS]

    # 如果核心词太少（<2），回退到取前 max_words 个原词
    if len(core_words) < 2:
        core_words = words[:max_words]

    # 限制长度
    core_words = core_words[:max_words]

    return " ".join(core_words)


def truncate_query(query: str, max_chars: int = 250) -> str:
    """截断查询词到指定字符数（用于 arXiv 等有长度限制的 API）

    Args:
        query: 搜索词
        max_chars: 最大字符数

    Returns:
        截断后的搜索词
    """
    if len(query) <= max_chars:
        return query

    # 按词截断，避免切断单词
    truncated = query[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.8:  # 至少保留 80% 内容
        truncated = truncated[:last_space]

    return truncated


def split_query(query: str) -> list[str]:
    """将长查询拆分为多个更精确的子查询

    如果查询包含明确的连接词（for, and, based on），拆分为子查询。
    每个子查询更短更精确，搜索结果更相关。

    Args:
        query: 搜索词

    Returns:
        子查询列表（如果无需拆分则返回原查询）
    """
    # 检测连接词模式
    patterns = [
        r"\s+for\s+",
        r"\s+and\s+",
        r"\s+based\s+on\s+",
        r"\s+using\s+",
        r"\s+with\s+",
        r"\s+via\s+",
    ]

    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            part1 = query[:match.start()].strip()
            part2 = query[match.end():].strip()

            # 两部分都有实质内容才拆分
            if len(part1.split()) >= 2 and len(part2.split()) >= 2:
                return [part1, part2]

    return [query]
