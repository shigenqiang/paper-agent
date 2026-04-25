"""RCS 重排序 - Re-ranking + Contextual Summarization (PaperQA2启发)"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional

from src.core.model import embed_model, llm

logger = logging.getLogger(__name__)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算余弦相似度"""
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


async def rcs_rank(
    query: str,
    papers: List[Dict[str, Any]],
    k: int = 50,
    top_n: int = 20
) -> List[Dict[str, Any]]:
    """
    RCS: Re-ranking + Contextual Summarization (PaperQA2启发)

    流程：
    1. Embed query + abstract → 初排（向量相似度）
    2. LLM对top-k每篇打分(1-10) + 300字摘要
    3. 按分数重排，返回top_n

    Args:
        query: 搜索查询
        papers: 论文列表
        k: LLM重排的候选数量
        top_n: 最终返回数量

    Returns:
        重排后的论文列表（包含 relevance_score 和 rcs_summary）
    """
    if not papers:
        return []

    logger.info(f"RCS ranking: {len(papers)} papers, k={k}, top_n={top_n}")

    # ========== Step 1: 向量初排 ==========
    query_emb = embed_model.embed_query(query)

    paper_abss = []
    for p in papers:
        # 安全获取摘要
        abstract = ""
        if isinstance(p, dict):
            abstract = p.get("abstract", "")
        elif hasattr(p, "abstract"):
            abstract = p.abstract or ""
        paper_abss.append(abstract or " ")

    # 批量编码
    paper_embs = embed_model.embed_documents(paper_abss)

    # 计算余弦相似度
    scores = []
    for emb in paper_embs:
        sim = cosine_similarity(query_emb, emb)
        scores.append(sim)

    # 按分数排序
    scored_papers = sorted(
        [(p, s) for p, s in zip(papers, scores)],
        key=lambda x: x[1],
        reverse=True
    )

    # 取top-k候选
    top_candidates = scored_papers[:k]
    logger.info(f"Vector ranking done, top {len(top_candidates)} candidates")

    # ========== Step 2: LLM重排 + 摘要 ==========
    async def score_and_summarize(paper: Dict[str, Any], idx: int) -> Optional[Dict[str, Any]]:
        """对单篇论文进行评分和摘要"""
        try:
            title = paper.get("title", "") if isinstance(paper, dict) else getattr(paper, "title", "")
            abstract = paper.get("abstract", "")[:500] if isinstance(paper, dict) else getattr(paper, "abstract", "")[:500]

            prompt = f"""Query: {query}

Paper Title: {title}

Abstract: {abstract}

请评估这篇论文与查询的相关性，输出JSON格式：
{{"score": 1-10的整数, "summary": "300字左右的中文摘要"}}

只返回JSON，不要其他内容。"""

            response = await llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            # 提取JSON
            json_str = _extract_json(content)
            data = json.loads(json_str)

            score = int(data.get("score", 5))
            summary = data.get("summary", "")

            # 准备结果
            result = dict(paper) if isinstance(paper, dict) else paper.model_dump()
            result["relevance_score"] = score / 10.0
            result["rcs_summary"] = summary
            result["initial_score"] = scores[idx]

            return result

        except Exception as e:
            logger.warning(f"LLM scoring failed for paper {idx}: {e}")
            return None

    # 并行调用LLM
    original_indices = []
    for i, (paper, _) in enumerate(top_candidates):
        # 找到在原始列表中的索引
        for j, p in enumerate(papers):
            if p == paper or (isinstance(p, dict) and isinstance(paper, dict) and p.get("paper_id") == paper.get("paper_id")):
                original_indices.append(j)
                break
        else:
            original_indices.append(i)

    tasks = [
        score_and_summarize(paper, orig_idx)
        for (paper, _), orig_idx in zip(top_candidates, original_indices)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 收集成功的结果
    scored_results = []
    for result in results:
        if isinstance(result, Exception):
            continue
        if result is not None:
            scored_results.append(result)

    # ========== Step 3: 按分数重排 ==========
    scored_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    # 返回top_n
    final_results = scored_results[:top_n]

    logger.info(f"RCS ranking completed: {len(final_results)} papers returned")

    return final_results


def _extract_json(content: str) -> str:
    """从响应内容中提取JSON"""
    content = content.strip()

    if "```json" in content:
        parts = content.split("```json")
        if len(parts) > 1:
            content = parts[1].split("```")[0]
    elif "```" in content:
        parts = content.split("```")
        if len(parts) > 1:
            content = parts[1]

    if not content.startswith("{"):
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            content = content[start:end]

    return content


async def rcs_rank_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph节点：RCS重排序

    使用RCS对搜索结果进行重排序，提高相关性
    """
    query = state.get("query", "")
    papers = state.get("papers", [])

    if not papers:
        logger.warning("No papers to rank")
        return state

    if not query:
        logger.warning("No query for ranking")
        return state

    logger.info(f"RCS rank node: {len(papers)} papers for query '{query}'")

    # 执行RCS重排序
    ranked_papers = await rcs_rank(query, papers, k=50, top_n=20)

    # 更新状态
    state["papers"] = ranked_papers
    state["papers_after_rank"] = ranked_papers

    logger.info(f"RCS rank node completed: {len(ranked_papers)} papers returned")

    return state