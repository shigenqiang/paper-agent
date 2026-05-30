"""搜索词优化 — 通过 LLM 提取学术核心关键词"""

from __future__ import annotations

from loguru import logger

# ── 提示词 ──────────────────────────────────────────

_SYSTEM_PROMPT = """你是一个学术论文搜索查询优化专家。

## 职责
将用户的自然语言查询转换为精确的学术搜索关键词，用于 OpenAlex、arXiv、Semantic Scholar 等学术搜索引擎。

## 优化规则
1. 去除所有泛化词：approach, method, based on, using, for, and, with, novel, efficient, analysis, framework, model, study, research, data, system, application
2. 保留核心学术术语：专业方法名、理论名称、技术领域关键词
3. 保留英文缩写（如 PCA, FPCA, LSTM, CNN）
4. 保留连字符术语（如 non-parametric, self-supervised）
5. 不要解释关键词含义，只输出优化后的搜索词
6. 不要添加原查询中没有的概念

## Few-Shot 示例

【示例1】
输入：sparse functional data for deep learning
输出：sparse functional deep learning

【示例2】
输入：novel approach for efficient deep learning based on sparse functional data analysis
输出：deep learning sparse functional

【示例3】
输入：a comprehensive survey of machine learning methods for time series forecasting
输出：machine learning time series forecasting

【示例4】
输入：investigating the application of transformer architecture in natural language processing tasks
输出：transformer natural language processing

【示例5】
输入：principal component analysis for high dimensional functional data with missing observations
输出：principal component analysis functional data missing observations
"""

_USER_PROMPT_TEMPLATE = "优化以下学术搜索查询（最多 {max_words} 个关键词）：\n{query}"


# ── 优化函数 ──────────────────────────────────────────

def refine_query(query: str, max_words: int = 8) -> str:
    """通过 LLM 提取核心学术搜索关键词

    去除泛化词，保留专业术语和方法名。

    Args:
        query: 原始搜索词
        max_words: 保留的最大词数

    Returns:
        精简后的学术搜索关键词
    """
    words = query.split()
    if len(words) <= 3:
        return query.strip()

    try:
        from src.agents_v3.research_workspace.llm.service import get_llm_service
        llm = get_llm_service()

        user_prompt = _USER_PROMPT_TEMPLATE.format(max_words=max_words, query=query)
        result = llm.invoke(_SYSTEM_PROMPT, user_prompt).strip().strip('"').strip("'")

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
            "你是一个学术搜索查询优化专家。"
            "如果查询包含多个独立的研究概念，将其拆分为 2-3 个子查询，每个子查询聚焦一个概念。"
            "如果查询已经是单一主题，返回原查询。"
            "输出 JSON 数组格式。"
        )
        user_prompt = f"拆分以下查询（如需要）：{query}"

        import json
        result = llm.invoke(system_prompt, user_prompt).strip()
        start = result.find("[")
        end = result.rfind("]")
        if start != -1 and end != -1:
            sub_queries = json.loads(result[start:end + 1])
            if isinstance(sub_queries, list) and len(sub_queries) >= 1:
                return [str(q).strip() for q in sub_queries if q]
    except Exception as e:
        logger.warning(f"LLM query split failed: {e}")

    return [query]
