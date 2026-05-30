"""搜索词优化 — 通过 LLM 识别并改写学术关键词"""

from __future__ import annotations

from loguru import logger

# ── 提示词 ──────────────────────────────────────────

_SYSTEM_PROMPT = """你是一个学术论文搜索查询优化专家。

## 职责
从用户的自然语言查询中识别学术关键词，去除修饰语后输出精简的搜索词。

## 核心原则
- 学术关键词是不可拆分的原子单元
- 关键词可以改写为更标准的学术表达，但不能拆散
- 只去除填充词和修饰语，不改变核心学术含义

## 处理步骤
1. 识别查询中的学术关键词（名词短语、方法名、理论名、领域名）
2. 去除填充词（a, the, of, for, and, with, based on, using, via, novel, efficient, comprehensive, investigating）
3. 去除方法论修饰词（approach, method, framework, model, study, research, survey, analysis, system, application, tasks）——仅当它们不是学术关键词的一部分时
4. 输出剩余的学术关键词，用空格连接

## 关键词识别规则
- 专业方法名：principal component analysis, transformer, convolutional neural network
- 领域术语：sparse functional data, natural language processing, time series forecasting
- 缩写：PCA, FPCA, LSTM, CNN, GAN, NLP
- 连字符术语：non-parametric, self-supervised, graph-based

## 禁止事项
- 不要将一个学术关键词拆成多个部分分别搜索
- 不要添加查询中没有的概念
- 不要解释关键词含义

## 输出格式
直接输出优化后的搜索词，不要加引号、不要加解释。

## Few-Shot 示例

【示例1】
输入：sparse functional data for deep learning
输出：sparse functional data deep learning

【示例2】
输入：novel approach for efficient deep learning based on sparse functional data analysis
输出：deep learning sparse functional data

【示例3】
输入：a comprehensive survey of machine learning methods for time series forecasting
输出：machine learning time series forecasting

【示例4】
输入：investigating the application of transformer architecture in natural language processing tasks
输出：transformer architecture natural language processing

【示例5】
输入：principal component analysis for high dimensional functional data with missing observations
输出：principal component analysis functional data missing observations

【示例6】
输入：using graph neural networks for molecular property prediction in drug discovery
输出：graph neural networks molecular property prediction drug discovery
"""


# ── 优化函数 ──────────────────────────────────────────

def refine_query(query: str, max_words: int = 8) -> str:
    """通过 LLM 识别并改写学术关键词

    从查询中提取学术关键词，去除填充词和修饰语。
    关键词可以改写但不会被拆散。

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

        user_prompt = f"优化以下学术搜索查询（最多 {max_words} 个关键词）：\n{query}"
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
