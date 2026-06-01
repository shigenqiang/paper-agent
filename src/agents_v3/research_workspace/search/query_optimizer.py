"""搜索词优化 — 通过 LLM 识别并改写学术关键词"""

from __future__ import annotations

from loguru import logger

# ── 提示词（遵循 Agent提示词工程指南 5 部分结构）──────────

_SYSTEM_PROMPT = """## 1. 角色定义 (Role Definition)
你是一个学术论文搜索查询优化专家，擅长从用户的自然语言描述中识别学术关键词，并将其转换为适合 OpenAlex、arXiv、Semantic Scholar 等学术搜索引擎的精简查询。

## 2. 能力边界 (Capabilities)
- 能够识别学术名词短语（方法名、理论名、领域名、数据集名）
- 能够区分核心学术术语和修饰性填充词
- 能够将口语化表达改写为标准学术用语
- 熟悉统计学、计算机科学、生物医学等主要学科的术语

## 3. 行为准则 (Guidelines)
处理查询时应遵循：

步骤1：识别学术关键词
- 扫描查询，识别所有学术名词短语
- 学术关键词示例：sparse functional data, principal component analysis, transformer, natural language processing, time series forecasting, graph neural networks, drug discovery

步骤2：去除填充词
- 填充词列表：a, the, of, for, and, with, from, based on, using, via, in, on, to, about
- 修饰词列表：novel, efficient, comprehensive, investigating, new, advanced, improved

步骤3：去除方法论泛化词（仅当不是关键词组成部分时）
- 泛化词列表：approach, method, methods, framework, model, study, research, survey, analysis, system, application, tasks, techniques
- 判断方法：如果这些词是学术关键词的一部分（如 "principal component analysis" 中的 "analysis"），则保留；否则去除

步骤4：输出精简查询
- 将剩余的学术关键词用空格连接
- 保持关键词的原始顺序（不重新排序）

## 4. 约束限制 (Constraints)
- 学术关键词是不可拆分的原子单元，绝不能将 "sparse functional data" 拆成 "sparse" 和 "functional data"
- 只能去除填充词和修饰词，不能改变核心学术含义
- 不能添加查询中没有的概念
- 不能将一个查询拆分为多个子查询
- 输出的关键词数量不超过用户指定的最大值

## 5. 输出格式 (Output Format)
直接输出优化后的搜索词，不要加引号、不要加解释、不要加前缀。

## Few-Shot Examples

【示例1：去除填充词】
输入：sparse functional data for deep learning
分析：学术关键词 = [sparse functional data, deep learning]，填充词 = [for]
输出：sparse functional data deep learning

【示例2：去除修饰词和方法论泛化词】
输入：novel approach for efficient deep learning based on sparse functional data analysis
分析：学术关键词 = [deep learning, sparse functional data]，修饰词 = [novel, efficient]，填充词 = [for, based on]，泛化词 = [approach, analysis]（不是关键词组成部分）
输出：deep learning sparse functional data

【示例3：保留完整领域术语】
输入：a comprehensive survey of machine learning methods for time series forecasting
分析：学术关键词 = [machine learning, time series forecasting]，填充词 = [a, of, for]，修饰词 = [comprehensive]，泛化词 = [survey, methods]
输出：machine learning time series forecasting

【示例4：保留架构名和领域名】
输入：investigating the application of transformer architecture in natural language processing tasks
分析：学术关键词 = [transformer architecture, natural language processing]，填充词 = [the, of, in]，修饰词 = [investigating]，泛化词 = [application, tasks]
输出：transformer architecture natural language processing

【示例5：保留方法名完整】
输入：principal component analysis for high dimensional functional data with missing observations
分析：学术关键词 = [principal component analysis, functional data, missing observations]，填充词 = [for, with]，修饰词 = [high dimensional]
输出：principal component analysis functional data missing observations

【示例6：跨领域关键词】
输入：using graph neural networks for molecular property prediction in drug discovery
分析：学术关键词 = [graph neural networks, molecular property prediction, drug discovery]，填充词 = [using, for, in]
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


# ── Multi-Query 多查询变体 ──────────────────────────────

_MULTI_QUERY_PROMPT = """## 角色
你是学术论文搜索查询改写专家。

## 任务
将用户查询改写为 {n} 个不同的搜索变体，每个变体从不同角度表达相同的研究需求。

## 规则
1. 保留核心学术概念（如 "sparse functional data" 是一个整体，不能拆开）
2. 每个变体使用不同的同义词、相关术语或表达方式
3. 变体之间应有差异，不要只是调换词序
4. 适合在 OpenAlex、arXiv、Semantic Scholar 上搜索
5. 每个变体不超过 10 个词

## 示例
输入：sparse functional data for deep learning
输出：
sparse functional regression neural network
functional data analysis sparsity regularization deep learning
irregular functional data representation learning
sparse sampling functional estimation deep learning

## 输出格式
每行一个变体，不要编号、不要解释。"""


def multi_query(query: str, n: int = 4) -> list[str]:
    """生成多个查询变体（Multi-Query 策略）

    Returns:
        变体列表（不含原始查询）
    """
    try:
        from src.agents_v3.research_workspace.llm.service import get_llm_service
        llm = get_llm_service()

        user_prompt = f"改写以下查询为 {n} 个变体：\n{query}"
        result = llm.invoke(_MULTI_QUERY_PROMPT.format(n=n), user_prompt).strip()

        variants = []
        for line in result.strip().split("\n"):
            line = line.strip().strip('"').strip("'")
            # 去掉可能的编号前缀
            line = __import__("re").sub(r"^\d+[\.\)]\s*", "", line)
            if line and line.lower() != query.lower() and len(line.split()) >= 2:
                variants.append(line)

        logger.info(f"Multi-Query: \"{query}\" → {len(variants)} variants")
        for i, v in enumerate(variants):
            logger.info(f"  [{i+1}] {v}")
        return variants[:n]

    except Exception as e:
        logger.warning(f"Multi-Query failed: {e}")
        return []


# ── HyDE 假设性文档 ────────────────────────────────────

_HYDE_PROMPT = """## 角色
你是学术论文摘要撰写专家。

## 任务
根据用户的研究查询，撰写一篇**假设性论文摘要**（150-200词），描述一篇理想中完全匹配该查询的论文。

## 规则
1. 摘要应包含查询中的核心学术概念
2. 使用标准的学术论文摘要语言风格
3. 包含方法、数据、结果等关键要素
4. 使用该领域的专业术语
5. 不要编造具体的数字或引用

## 输出格式
直接输出摘要文本，不要加标题、不要加解释。"""


def hyde_query(query: str) -> str:
    """生成假设性论文摘要（HyDE 策略）

    Returns:
        假设性摘要文本，用于增强搜索
    """
    try:
        from src.agents_v3.research_workspace.llm.service import get_llm_service
        llm = get_llm_service()

        user_prompt = f"为以下研究查询撰写假设性论文摘要：\n{query}"
        result = llm.invoke(_HYDE_PROMPT, user_prompt).strip().strip('"').strip("'")

        if result and len(result) > 50:
            logger.info(f"HyDE: generated {len(result)} chars hypothetical abstract")
            return result
    except Exception as e:
        logger.warning(f"HyDE failed: {e}")

    return ""
