"""Critique Agent - 多视角评审Agent"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import json
import logging

from src.core.model import llm

logger = logging.getLogger(__name__)


class CritiqueResult(BaseModel):
    """Critique评估结果"""
    passed: bool = Field(..., description="是否通过评审")
    score: float = Field(..., description="综合评分 0-10")
    missing_topics: List[str] = Field(default_factory=list, description="遗漏的主题")
    suggested_queries: List[str] = Field(default_factory=list, description="建议的补充查询")
    issues: List[str] = Field(default_factory=list, description="发现的问题")
    perspective_scores: Dict[str, float] = Field(default_factory=dict, description="各视角评分")
    confidence: float = Field(default=0.8, description="评估置信度")


# 多视角定义
PERSPECTIVES = [
    {
        "role": "初学者",
        "prompt": """作为刚接触这个领域的学生，评估当前研究的覆盖度。

请检查：
1. 背景介绍是否足够清晰？哪些专业术语没有解释？
2. 概念解释是否从基础到深入？
3. 是否涵盖了领域的基础知识？

输出 JSON 格式：
{
    "score": 1-10,
    "missing_topics": ["遗漏的主题1", "..."],
    "suggested_queries": ["补充搜索词1", "..."],
    "issues": ["问题1", "..."]
}"""
    },
    {
        "role": "专家",
        "prompt": """作为该领域的资深研究者，评估现有研究的深度和广度。

请检查：
1. 重要论文/方法是否被遗漏？
2. 哪些论点缺乏足够的证据支持？
3. 最新的研究进展是否被涵盖？

输出 JSON 格式：
{
    "score": 1-10,
    "missing_topics": ["遗漏的主题1", "..."],
    "suggested_queries": ["补充搜索词1", "..."],
    "issues": ["问题1", "..."]
}"""
    },
    {
        "role": "批评者",
        "prompt": """作为该领域的批评者，找出论证中的薄弱环节。

请检查：
1. 哪些矛盾没有被充分讨论？
2. 哪些假设可能有问题？
3. 论证链中是否有逻辑漏洞？

输出 JSON 格式：
{
    "score": 1-10,
    "missing_topics": ["遗漏的主题1", "..."],
    "suggested_queries": ["补充搜索词1", "..."],
    "issues": ["问题1", "..."]
}"""
    }
]


class CritiqueAgent:
    """
    多视角Critique Agent

    功能：
    - 从三个视角评审研究结果（初学者/专家/批评者）
    - 评估覆盖度，发现遗漏
    - 生成补充搜索建议
    """

    def __init__(self, llm_model=None, quality_threshold: float = 7.0):
        self.llm = llm_model or llm
        self.quality_threshold = quality_threshold

    async def critique(
        self,
        query: str,
        papers: List[Dict[str, Any]],
        themes: List[Dict[str, Any]] = None,
        research_gaps: List[str] = None,
        contradictions: List[str] = None
    ) -> CritiqueResult:
        """
        执行多视角Critique

        Args:
            query: 研究主题
            papers: 论文列表
            themes: 主题聚类结果
            research_gaps: 研究空白
            contradictions: 矛盾发现

        Returns:
            CritiqueResult: 评估结果
        """
        themes = themes or []
        research_gaps = research_gaps or []
        contradictions = contradictions or []

        logger.info(f"Starting critique for query: {query}")

        critiques = []

        # 从三个视角进行评审
        for perspective in PERSPECTIVES:
            try:
                critique_result = await self._critique_from_perspective(
                    perspective, query, papers, themes, research_gaps, contradictions
                )
                critiques.append(critique_result)
            except Exception as e:
                logger.error(f"Critique from {perspective['role']} failed: {e}")

        # 汇总评估
        if not critiques:
            return CritiqueResult(
                passed=False,
                score=0.0,
                issues=["所有视角评审均失败"]
            )

        avg_score = sum(c["score"] for c in critiques) / len(critiques)
        all_missing = set()
        all_queries = set()
        all_issues = set()
        perspective_scores = {}

        for c in critiques:
            perspective_scores[c["role"]] = c["score"]
            all_missing.update(c.get("missing_topics", []))
            all_queries.update(c.get("suggested_queries", []))
            all_issues.update(c.get("issues", []))

        return CritiqueResult(
            passed=avg_score >= self.quality_threshold,
            score=avg_score,
            missing_topics=list(all_missing),
            suggested_queries=list(all_queries),
            issues=list(all_issues),
            perspective_scores=perspective_scores
        )

    async def _critique_from_perspective(
        self,
        perspective: Dict[str, Any],
        query: str,
        papers: List[Dict[str, Any]],
        themes: List[Dict[str, Any]],
        research_gaps: List[str],
        contradictions: List[str]
    ) -> Dict[str, Any]:
        """从特定视角进行评审"""
        role = perspective["role"]
        prompt = perspective["prompt"]

        # 构建上下文信息
        context_parts = [
            f"研究主题: {query}",
            f"论文数量: {len(papers)}",
        ]

        if papers:
            # 显示前几篇论文的标题和摘要摘要
            sample_papers = papers[:5]
            paper_summaries = []
            for p in sample_papers:
                title = p.get("title", "N/A")
                abstract = p.get("abstract", "N/A")[:300]
                paper_summaries.append(f"- {title}: {abstract}...")
            context_parts.append(f"主要论文:\n" + "\n".join(paper_summaries))

        if themes:
            theme_names = [t.get("name", t.get("theme_description", "未知")) for t in themes]
            context_parts.append(f"主题聚类: {', '.join(theme_names)}")

        if research_gaps:
            context_parts.append(f"研究空白: {', '.join(research_gaps)}")

        if contradictions:
            context_parts.append(f"矛盾发现: {', '.join(contradictions)}")

        full_prompt = f"""
{context_parts[0]}
{chr(10).join(context_parts[1:])}

{prompt}

请输出 JSON 格式（不要添加其他内容）：
"""

        try:
            response = await self.llm.ainvoke(full_prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            # 提取 JSON
            json_str = self._extract_json(content)
            result = json.loads(json_str)

            return {
                "role": role,
                "score": float(result.get("score", 5)),
                "missing_topics": result.get("missing_topics", []),
                "suggested_queries": result.get("suggested_queries", []),
                "issues": result.get("issues", [])
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed for {role}: {e}")
            # 返回默认评分
            return {
                "role": role,
                "score": 5.0,
                "missing_topics": [],
                "suggested_queries": [],
                "issues": [f"解析{role}评审结果失败"]
            }

    def _extract_json(self, content: str) -> str:
        """从响应内容中提取JSON"""
        # 尝试直接解析
        content = content.strip()

        # 查找 JSON 块
        if "```json" in content:
            parts = content.split("```json")
            if len(parts) > 1:
                content = parts[1].split("```")[0]
        elif "```" in content:
            parts = content.split("```")
            if len(parts) > 1:
                content = parts[1]

        # 清理
        content = content.strip()

        # 如果还是不是 JSON 格式，尝试找第一个 { 到最后一个 }
        if not content.startswith("{"):
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                content = content[start:end]

        return content


# 全局实例
critique_agent = CritiqueAgent()