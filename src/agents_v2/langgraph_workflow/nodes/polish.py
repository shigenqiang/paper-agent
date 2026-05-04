"""
Polish Node - LangGraph 工作流节点

对应 MasterSupervisor 的 polish 阶段：
- 多轮迭代优化论文质量
- 评审-修改-精炼循环
- 质量评估与改进
- 针对性问题修复
"""
from src.agents_v2.logging_config import get_logging_logger

import json
import time
import os
from typing import Any, Dict, Optional

logger = get_logging_logger(__name__)

# Polish 阶段质量阈值（最终润色需要更高）
POLISH_QUALITY_THRESHOLD = 0.8


def _get_llm_config():
    """获取 LLM 配置"""
    from src.agents_v2.config import LLMConfig

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.minimax.chat/v1")
    model_name = os.getenv("LLM_MODEL", "MiniMax-M2.7")

    return LLMConfig(
        provider="openai",
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.7,
        max_tokens=4096
    )


class PolishNode:
    """润色节点 - 调用 LanguagePolisherAgent、SmartReviserAgent 等"""

    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider

    async def _run_language_polisher(
        self,
        text: str,
        language: str = "zh",
        polish_level: str = "medium"
    ) -> Dict[str, Any]:
        """运行语言润色"""
        try:
            from src.agents_v2.problem_oriented.language_polisher import LanguagePolisherAgent

            llm_config = _get_llm_config()
            agent = LanguagePolisherAgent(llm_config=llm_config)
            result = await agent.diagnose({
                "text": text,
                "language": language,
                "polish_level": polish_level
            }, {})

            return {
                "success": result.success,
                "polished_text": result.result.get("polished_text", text) if isinstance(result.result, dict) else (result.result if isinstance(result.result, str) else text),
                "quality_score": result.quality_score / 10.0 if result.quality_score else 0,
                "diagnosed_issues": result.diagnosed_issues,
                "recommendations": result.recommendations,
                "error": result.error
            }
        except Exception as e:
            logger.warning(f"Language polisher failed: {e}")
            return {
                "success": False,
                "polished_text": text,  # 回退到原文
                "quality_score": 0.0,
                "diagnosed_issues": [],
                "recommendations": [],
                "error": str(e)
            }

    async def _run_smart_reviser(
        self,
        text: str,
        diagnostic_result: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """运行智能修订"""
        try:
            from src.agents_v2.writing.smart_reviser import SmartReviserAgent

            llm_config = _get_llm_config()
            agent = SmartReviserAgent(llm_config=llm_config)
            result = await agent.execute({
                "task": "revision",
                "text": text,
                "diagnostic": diagnostic_result
            }, {})

            return {
                "success": result.success,
                "revised_text": result.result.get("revised_text", text) if isinstance(result.result, dict) else (result.result if isinstance(result.result, str) else text),
                "quality_score": result.quality_score / 10.0 if result.quality_score else 0,
                "error": result.error
            }
        except Exception as e:
            logger.warning(f"Smart reviser failed: {e}")
            return {
                "success": False,
                "revised_text": text,
                "quality_score": 0.0,
                "error": str(e)
            }

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph 节点入口（同步包装）

        Args:
            state: 当前状态，需包含 draft

        Returns:
            更新后的状态
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.__call__(state))

    async def _run_citation_processor(
        self,
        text: str,
        papers: list,
        citation_style: str = "GB_T"
    ) -> Dict[str, Any]:
        """处理文献引用 - 插入文中引用并生成参考文献"""
        if not papers:
            return {
                "success": True,
                "cited_text": text,
                "reference_list": "",
                "citation_count": 0
            }

        try:
            from src.agents_v2.writing.citation_generator import CitationGenerator, CitationStyle
            from src.agents_v2.writing.reference_processor import ReferenceProcessorAgent

            # 1. 转换 papers 为 Citation 对象
            citations = []
            for paper in papers:
                if isinstance(paper, dict):
                    authors = paper.get("authors", [])
                    if isinstance(authors, str):
                        authors = [a.strip() for a in authors.split(",")]
                    citation = {
                        "authors": authors,
                        "year": str(paper.get("year", "")),
                        "title": paper.get("title", ""),
                        "journal": paper.get("journal", "") or paper.get("venue", ""),
                        "volume": paper.get("volume", ""),
                        "issue": paper.get("issue", ""),
                        "pages": paper.get("pages", ""),
                        "doi": paper.get("doi", "")
                    }
                    citations.append(citation)

            # 2. 使用 ReferenceProcessorAgent 处理引用
            llm_config = _get_llm_config()
            ref_agent = ReferenceProcessorAgent(llm_config=llm_config)

            ref_result = await ref_agent.execute({
                "paper_content": text,
                "raw_references": citations,
                "citation_style": citation_style
            }, {})

            # 3. 提取格式化后的参考文献
            reference_list = ""
            if ref_result.success and ref_result.result:
                reference_list = ref_result.result.get("reference_list", "")

            # 4. 使用 LLM 在正文中插入引用标记
            cited_text = await self._insert_citations(text, papers, citation_style)

            return {
                "success": True,
                "cited_text": cited_text,
                "reference_list": reference_list,
                "citation_count": len(citations)
            }

        except Exception as e:
            logger.warning(f"Citation processor failed: {e}")
            return {
                "success": False,
                "cited_text": text,
                "reference_list": "",
                "citation_count": 0,
                "error": str(e)
            }

    async def _insert_citations(
        self,
        text: str,
        papers: list,
        citation_style: str = "GB_T"
    ) -> str:
        """使用 LLM 在正文中适当位置插入引用"""
        if not papers:
            return text

        # 构建引用上下文
        citation_context = []
        for i, paper in enumerate(papers[:20], 1):  # 最多20篇
            title = paper.get("title", "")
            authors = paper.get("authors", [])
            year = paper.get("year", "")
            if isinstance(authors, list):
                first_author = authors[0] if authors else ""
                if "," in first_author:
                    first_author = first_author.split(",")[0].strip()
            else:
                first_author = str(authors).split(",")[0] if authors else ""
            citation_context.append(f"[{i}] {first_author}等. {title} ({year})")

        papers_json = json.dumps(citation_context, ensure_ascii=False, indent=2)

        prompt = f"""请在论文正文中适当位置插入文献引用。

论文正文：
{text[:8000]}

可用文献（按编号）：
{papers_json}

引用格式：GB/T 7714标准，使用上标 [编号] 或 (作者, 年份) 格式。

要求：
1. 在提到研究背景、方法、结果时插入对应文献引用
2. 引用位置应紧跟在相关陈述之后
3. 保持原文不变，只在适当位置添加引用标记
4. 优先引用最近5年内的论文

输出格式：
{{
    "cited_paper": "已插入引用的论文正文"
}}
"""
        try:
            from src.agents_v2.config import LLMConfig
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.minimax.chat/v1")
            model_name = os.getenv("LLM_MODEL", "MiniMax-M2.7")
            llm_config = LLMConfig(
                provider="openai",
                model_name=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=0.3,
                max_tokens=8192
            )

            from src.agents_v2.unified.pydantic_validator import parse_json
            response = await self._llm_call(prompt, llm_config)
            data = parse_json(response)
            if data and "cited_paper" in data:
                return data["cited_paper"]
        except Exception as e:
            logger.warning(f"Citation insertion failed: {e}")

        return text

    async def _llm_call(self, prompt: str, llm_config) -> str:
        """调用 LLM"""
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=llm_config.api_key,
            base_url=llm_config.base_url
        )
        response = await client.chat.completions.create(
            model=llm_config.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens
        )
        return response.choices[0].message.content

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行语言润色（异步接口，兼容 LangGraph）

        Args:
            state: 当前状态，需包含 draft

        Returns:
            更新后的状态
        """
        draft = state.get("draft", "")
        if not draft:
            logger.warning("[Polish] No draft to polish")
            state["polish_success"] = False
            state["polished_text"] = ""
            return state

        logger.info(f"[Polish] 开始论文润色，draft length={len(draft)}...")
        start = time.time()

        # 获取诊断结果
        diagnostic_result = state.get("diagnostic_result", {})
        # 获取文献列表（用于引用处理）
        papers = state.get("papers", [])

        # 0. 引用处理（插入文献引用）
        citation_result = await self._run_citation_processor(
            text=draft,
            papers=papers,
            citation_style="GB_T"
        )
        cited_text = citation_result.get("cited_text", draft)
        reference_list = citation_result.get("reference_list", "")
        citation_count = citation_result.get("citation_count", 0)

        logger.info(f"[Polish] 引用处理完成: {citation_count} 篇文献被引用")

        # 1. 语言润色
        polish_result = await self._run_language_polisher(
            text=cited_text,
            language=state.get("language", "zh"),
            polish_level="medium"
        )

        polished_text = polish_result.get("polished_text", cited_text)
        language_score = polish_result.get("quality_score", 0)
        language_issues = polish_result.get("diagnosed_issues", [])

        # 2. 智能修订（如果有问题）
        revised_text = polished_text
        revision_score = 0.0
        if language_issues:
            revision_result = await self._run_smart_reviser(polished_text, diagnostic_result)
            revised_text = revision_result.get("revised_text", polished_text)
            revision_score = revision_result.get("quality_score", 0)

        # 存储结果
        state["polished_text"] = revised_text
        state["polish_quality_score"] = (language_score + revision_score) / 2
        state["polish_success"] = polish_result.get("success", False)
        state["polish_issues"] = language_issues
        state["reference_list"] = reference_list  # 参考文献列表
        state["citation_count"] = citation_count  # 引用数量

        elapsed = time.time() - start
        logger.info(
            f"[Polish] 润色完成: polished_text type={type(polished_text)}, length={len(polished_text) if isinstance(polished_text, str) else 'N/A'}, "
            f"language_score={language_score:.3f}, revision_score={revision_score:.3f}, total={state['polish_quality_score']:.3f}, "
            f"引用={citation_count}篇, 耗时 {elapsed:.2f}s"
        )

        state["current_phase"] = "polish"
        return state

    def get_quality_threshold(self) -> float:
        """获取润色阶段质量阈值"""
        return POLISH_QUALITY_THRESHOLD
