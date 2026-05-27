"""
答案生成器 - Answer Generator

基础 RAG 生成，支持带引用的结构化输出。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from src.agents_v2.logging_config import get_logging_logger

import asyncio
import time

logger = get_logging_logger(__name__)


@dataclass
class GeneratedAnswer:
    """生成的答案"""
    answer: str
    citations: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    hallucination_risk: str = "unknown"
    used_retrieval: bool = True
    reflection_log: List[str] = field(default_factory=list)
    generation_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class AnswerGenerator:
    """答案生成器

    支持：
    1. 基于检索上下文的答案生成
    2. 带引用的结构化输出
    3. 置信度评估
    """

    def __init__(
        self,
        llm: Any,
        max_context_docs: int = 5,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ):
        """初始化答案生成器

        Args:
            llm: LLM 实例
            max_context_docs: 最大使用的上下文文档数
            temperature: 生成温度
            max_tokens: 最大 token 数
        """
        self.llm = llm
        self.max_context_docs = max_context_docs
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def generate(
        self,
        query: str,
        context_docs: List[Dict[str, Any]],
        include_citations: bool = True,
        generate_reflection: bool = False,
    ) -> GeneratedAnswer:
        """生成答案

        Args:
            query: 用户问题
            context_docs: 检索到的上下文文档
            include_citations: 是否包含引用
            generate_reflection: 是否生成反思日志

        Returns:
            GeneratedAnswer: 生成的答案
        """
        start_time = time.time()

        if not context_docs:
            return await self._generate_without_context(query, start_time)

        # 构建上下文
        context = self._build_context(context_docs)

        # 生成答案
        if include_citations:
            answer, citations = await self._generate_with_citations(query, context)
        else:
            answer = await self._generate_simple(query, context)
            citations = []

        # 评估置信度
        confidence = self._estimate_confidence(answer, context_docs)

        # 评估幻觉风险
        hallucination_risk = self._estimate_hallucination_risk(answer, context_docs)

        # 生成反思日志
        reflection_log = []
        if generate_reflection:
            reflection_log = self._generate_reflection_log(
                query, context_docs, answer, confidence
            )

        generation_time = time.time() - start_time

        return GeneratedAnswer(
            answer=answer,
            citations=citations,
            confidence=confidence,
            hallucination_risk=hallucination_risk,
            used_retrieval=True,
            reflection_log=reflection_log,
            generation_time=generation_time,
            metadata={
                "num_docs_used": len(context_docs),
                "context_length": len(context),
            }
        )

    async def _generate_with_citations(
        self,
        query: str,
        context: str,
    ) -> tuple:
        """生成带引用的答案

        Returns:
            tuple: (answer, citations)
        """
        prompt = f"""基于以下学术文献内容回答问题。
请确保：
1. 答案准确基于提供的文献
2. 每个重要论点都标注引用来源
3. 如文献不足，明确说明
4. 使用 [1], [2], [3] 等标记引用文献

文献内容:
{context}

问题: {query}

请生成结构化的学术答案："""

        try:
            # 调用 LLM 生成
            result = await self._call_llm(prompt)
            answer = result.strip()

            # 提取引用
            citations = self._extract_citations(answer, context)

            return answer, citations

        except Exception as e:
            logger.error(f"生成答案失败: {e}")
            return "抱歉，生成答案时发生错误。", []

    async def _generate_simple(
        self,
        query: str,
        context: str,
    ) -> str:
        """简单答案生成（不带引用）"""
        prompt = f"""基于以下内容回答问题。

内容:
{context}

问题: {query}

回答："""

        try:
            return await self._call_llm(prompt)
        except Exception as e:
            logger.error(f"生成答案失败: {e}")
            return "抱歉，生成答案时发生错误。"

    async def _generate_without_context(
        self,
        query: str,
        start_time: float,
    ) -> GeneratedAnswer:
        """无上下文时的生成

        当检索结果为空时，使用模型自身知识回答。
        """
        logger.warning("No relevant documents, using model knowledge")

        prompt = f"""问题: {query}

请直接回答。如果问题涉及专业知识但你不确定，请明确说明不确定性。"""

        try:
            answer = await self._call_llm(prompt)
        except Exception:
            answer = "抱歉，我无法回答这个问题。"

        return GeneratedAnswer(
            answer=answer,
            citations=[],
            confidence=0.5,  # 无上下文时置信度降低
            hallucination_risk="high",
            used_retrieval=False,
            reflection_log=["无上下文，使用模型知识生成"],
            generation_time=time.time() - start_time,
        )

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM

        支持多种 LLM 接口：
        - LangChain LLM
        - 直接 OpenAI/Anthropic API
        """
        if not self.llm:
            logger.warning("LLM not available, returning empty string")
            return ""

        try:
            # 尝试 LangChain 风格调用
            if hasattr(self.llm, 'agenerate'):
                result = await self.llm.agenerate([prompt])
                return result.generations[0][0].text.strip()
            # 尝试直接调用
            elif hasattr(self.llm, 'generate'):
                result = self.llm.generate([prompt])
                return result.generations[0][0].text.strip()
            # 尝试 chat 接口
            elif hasattr(self.llm, 'chat'):
                response = await self.llm.chat(prompt)
                return response.strip()
            else:
                logger.error(f"LLM 类型未知: {type(self.llm)}")
                return ""
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return ""

    def _build_context(self, context_docs: List[Dict[str, Any]]) -> str:
        """构建上下文文本"""
        if not context_docs:
            return ""

        context_parts = []

        for i, doc in enumerate(context_docs[:self.max_context_docs]):
            content = doc.get("content", doc.get("page_content", str(doc)))
            metadata = doc.get("metadata", {})

            # 添加文档标题
            title = metadata.get("title", f"文档 {i + 1}")
            section = metadata.get("section", "")

            header = f"[文档 {i + 1}]"
            if title:
                header += f" - {title}"
            if section:
                header += f" ({section})"

            context_parts.append(f"{header}\n{content[:1000]}")  # 限制每文档长度

        return "\n\n".join(context_parts)

    def _extract_citations(
        self,
        answer: str,
        context: str,
    ) -> List[Dict[str, Any]]:
        """提取引用

        从答案中提取 [1], [2] 等标记，并关联到实际文档。
        """
        import re

        # 找取引用标记
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, answer)

        citations = []
        for match in matches:
            doc_num = int(match)
            # 关联到实际文档
            # 这里简化处理，实际需要从上下文获取详细信息
            citations.append({
                "index": doc_num,
                "relevance": 0.8,  # 默认值
            })

        return citations

    def _estimate_confidence(
        self,
        answer: str,
        context_docs: List[Dict[str, Any]],
    ) -> float:
        """评估置信度

        基于多个因素：
        1. 上下文文档数量
        2. 答案长度
        3. 不确定性表达
        """
        # 基础分数
        confidence = 0.5

        # 上下文文档数量
        num_docs = len(context_docs)
        if num_docs >= 3:
            confidence += 0.2
        elif num_docs >= 1:
            confidence += 0.1

        # 答案长度（过短可能表示不确定）
        if len(answer) > 100:
            confidence += 0.1
        elif len(answer) < 30:
            confidence -= 0.2

        # 不确定性表达
        uncertainty_indicators = [
            "不确定", "可能", "也许", "不确定是否",
            "无法确定", "我没有足够信息", "我不清楚",
            "not sure", "might be", "perhaps", "uncertain"
        ]

        uncertainty_count = sum(
            1 for ind in uncertainty_indicators
            if ind.lower() in answer.lower()
        )

        confidence -= uncertainty_count * 0.05

        # 限制范围
        return max(0.0, min(1.0, confidence))

    def _estimate_hallucination_risk(
        self,
        answer: str,
        context_docs: List[Dict[str, Any]],
    ) -> str:
        """评估幻觉风险

        简单的启发式方法：
        1. 低风险：答案包含引用标记，有具体信息
        2. 中风险：有不确定性表达但无明显错误
        3. 高风险：无上下文，答案过于流畅
        """
        # 高风险指标
        high_risk_indicators = [
            "我认为", "我相信", "根据我的知识",
            "in my opinion", "I believe", "based on my knowledge"
        ]

        # 中风险指标
        medium_risk_indicators = [
            "可能", "也许", "不确定",
            "might", "perhaps", "probably"
        ]

        # 检查指标
        has_high_risk = any(ind in answer for ind in high_risk_indicators)
        has_medium_risk = any(ind in answer for ind in medium_risk_indicators)

        if has_high_risk and not context_docs:
            return "high"
        elif has_medium_risk:
            return "medium"
        elif not context_docs:
            return "high"
        else:
            return "low"

    def _generate_reflection_log(
        self,
        query: str,
        context_docs: List[Dict[str, Any]],
        answer: str,
        confidence: float,
    ) -> List[str]:
        """生成反思日志"""
        log = []

        # 记录检索使用情况
        log.append(f"检索文档数: {len(context_docs)}")

        # 记录置信度
        log.append(f"置信度: {confidence:.2f}")

        # 记录答案长度
        log.append(f"答案长度: {len(answer)} 字符")

        # 记录引用数量
        import re
        citations = re.findall(r'\[(\d+)\]', answer)
        log.append(f"引用数量: {len(citations)}")

        return log


class AcademicAnswerGenerator(AnswerGenerator):
    """学术专用答案生成器

    继承自 AnswerGenerator，增加了学术写作规范。
    """

    def __init__(self, llm: Any, citation_style: str = "gb7714", **kwargs):
        """初始化学术答案生成器

        Args:
            llm: LLM 实例
            citation_style: 引用格式 ("gb7714", "apa")
            **kwargs: 其他参数
        """
        super().__init__(llm, **kwargs)
        self.citation_style = citation_style

    async def generate_academic(
        self,
        query: str,
        context_docs: List[Dict[str, Any]],
    ) -> GeneratedAnswer:
        """生成学术级答案

        包含：
        1. 严谨的学术表达
        2. 规范的引用格式
        3. 置信度评估
        """
        # 生成答案
        result = await self.generate(
            query,
            context_docs,
            include_citations=True,
            generate_reflection=True,
        )

        # 添加学术风格后处理
        result.answer = self._apply_academic_style(result.answer)

        # 添加学术元数据
        result.metadata["citation_style"] = self.citation_style

        return result

    def _apply_academic_style(self, answer: str) -> str:
        """应用学术风格

        确保答案符合学术写作规范。
        """
        # 移除过于口语化的表达
        informal_phrases = [
            ("我觉得", "根据研究"),
            ("我认为", "研究表明"),
            ("很简单", "直接"),
            ("很容易", "可以"),
        ]

        for old, new in informal_phrases:
            answer = answer.replace(old, new)

        return answer


# 便捷函数
async def generate_answer(
    query: str,
    context_docs: List[Dict[str, Any]],
    llm: Any,
    **kwargs
) -> GeneratedAnswer:
    """生成答案的便捷函数"""
    generator = AnswerGenerator(llm, **kwargs)
    return await generator.generate(query, context_docs)


async def generate_academic_answer(
    query: str,
    context_docs: List[Dict[str, Any]],
    llm: Any,
    **kwargs
) -> GeneratedAnswer:
    """生成学术答案的便捷函数"""
    generator = AcademicAnswerGenerator(llm, **kwargs)
    return await generator.generate_academic(query, context_docs)