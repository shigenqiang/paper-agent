"""搜索后 LLM 相关性过滤 — 判断论文是否真正与查询主题相关"""

from __future__ import annotations

from loguru import logger

from src.agents_v3.research_workspace.search.base import SearchResult

_SYSTEM_PROMPT = """## 1. 角色定义
你是一个学术论文相关性判断专家。给定一个搜索查询和一批论文，判断每篇论文是否与查询主题真正相关。

## 2. 能力边界
- 能够区分"论文标题/摘要中包含查询词"和"论文真正研究查询主题"
- 理解学术术语的语义关系
- 识别泛匹配（如"deep learning"匹配所有DL论文）vs 精确匹配

## 3. 行为准则
判断相关性时：
- 论文的核心研究主题必须与查询主题一致或高度相关
- 仅在标题/摘要中出现个别查询词，但研究主题不同的，判定为不相关
- 综述论文如果覆盖了查询主题，判定为相关
- 应用论文如果主要应用了查询中的方法/技术，判定为相关

## 4. 约束限制
- 只返回判定结果，不加解释
- 对于无法判断的论文，判定为不相关（宁缺毋滥）

## 5. 输出格式
返回 JSON 数组，每个元素包含论文序号和判定结果：
```json
[{"id": 1, "relevant": true}, {"id": 2, "relevant": false}]
```"""


def _format_papers_for_llm(results: list[SearchResult]) -> str:
    """将论文列表格式化为 LLM 可读的文本"""
    lines = []
    for i, r in enumerate(results, 1):
        title = r.title or "(无标题)"
        abstract = (r.abstract or "")[:300]
        if len(r.abstract or "") > 300:
            abstract += "..."
        lines.append(f"[{i}] {title}\n    摘要: {abstract}")
    return "\n".join(lines)


def filter_relevant_papers(
    results: list[SearchResult],
    query: str,
    min_relevant: int = 1,
) -> list[SearchResult]:
    """用 LLM 判断搜索结果中哪些论文与查询真正相关

    Args:
        results: 搜索结果列表
        query: 原始搜索查询
        min_relevant: 最少返回的论文数（避免过滤过严导致0结果）

    Returns:
        过滤后的相关论文列表
    """
    if not results:
        return []

    if len(results) <= 3:
        return results  # 太少就不浪费 API 调用了

    try:
        from src.agents_v3.research_workspace.llm.service import get_llm_service
        from src.agents_v3.research_workspace.llm.json_utils import extract_json

        llm = get_llm_service()
        papers_text = _format_papers_for_llm(results)
        user_prompt = f"搜索查询：{query}\n\n论文列表：\n{papers_text}"

        response = llm.invoke(_SYSTEM_PROMPT, user_prompt)
        parsed = extract_json(response)

        if not isinstance(parsed, list):
            logger.warning(f"LLM relevance filter returned non-list: {type(parsed)}")
            return results

        relevant_ids = {item.get("id") for item in parsed if item.get("relevant")}
        filtered = [r for i, r in enumerate(results, 1) if i in relevant_ids]

        if len(filtered) < min_relevant:
            logger.info(f"LLM filter too strict ({len(filtered)} < {min_relevant}), keeping top results by score")
            results.sort(key=lambda r: r.final_score or 0, reverse=True)
            return results[:max(min_relevant, len(results) // 2)]

        logger.info(f"LLM relevance filter: {len(results)} → {len(filtered)} papers")
        return filtered

    except Exception as e:
        logger.warning(f"LLM relevance filter failed: {e}")
        return results
