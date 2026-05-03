"""
Self-RAG 控制器 - Self-RAG Controller

Self-RAG 反思机制实现。
通过反思令牌评估：
1. 是否需要检索
2. 检索结果相关性
3. 生成内容的支撑度
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from src.agents_v2.logging_config import get_logging_logger

import asyncio

logger = get_logging_logger(__name__)


class ReflectionToken(Enum):
    """反思令牌"""
    # 检索决策
    NEED_RETRIEVAL = "[检索]"  # 需要检索外部知识
    NO_RETRIEVAL = "[不检索]"  # 不需要检索，现有知识足够

    # 相关性评估
    RELEVANT = "[相关]"  # 检索结果与问题相关
    NOT_RELEVANT = "[不相关]"  # 检索结果与问题不相关

    # 支撑度评估
    FULLY_SUPPORTED = "[支持]"  # 生成内容被检索结果完全支持
    PARTIALLY_SUPPORTED = "[部分支持]"  # 生成内容部分被支持
    CONTRADICT = "[矛盾]"  # 生成内容与检索结果矛盾


@dataclass
class SelfRAGResult:
    """Self-RAG 结果"""
    answer: str
    used_retrieval: bool
    context: List[Dict[str, Any]] = field(default_factory=list)
    reflection_log: List[str] = field(default_factory=list)
    relevance_scores: List[float] = field(default_factory=list)
    groundedness: float = 0.0
    is_relevant: bool = True


class SelfRAGController:
    """Self-RAG 控制器

    反思机制：
    1. 判断是否需要检索
    2. 评估检索结果相关性
    3. 评估生成内容的事实支撑度
    """

    # 反思提示词
    RETRIEVAL_PROMPT = """分析以下用户问题，判断是否需要从外部知识库检索信息来回答。

问题: {query}

判断标准:
- 需要检索: 问题涉及特定事实、数据、日期、专业知识、最新研究、具体数值等
- 不需要检索: 问题涉及通用常识、观点询问、主观评价、明显的通用知识等

请只输出"检索"或"不检索"，不要解释。"""

    RELEVANCE_PROMPT = """评估以下检索结果对于回答用户问题的相关性。

用户问题: {query}

检索文档: {doc_content}

评分标准 (1-5分):
- 5分: 完全相关，直接支持答案
- 4分: 高度相关，提供重要支持
- 3分: 中度相关，部分支持
- 2分: 低度相关，边际支持
- 1分: 不相关，无法支持答案

请只输出一个数字分数，不要解释。"""

    GROUNDEDNESS_PROMPT = """评估以下答案是否被提供的上下文完全支撑。

问题: {query}

上下文: {context}

答案: {answer}

判断标准:
- 支持: 答案中的所有事实声明都可以从上下文中推断出来
- 部分支持: 部分事实可从上下文推断，部分需要外部知识
- 矛盾: 答案与上下文存在冲突

请只输出一个词：支持 / 部分支持 / 矛盾"""

    def __init__(
        self,
        llm: Optional[Any] = None,
        retriever: Optional[Callable] = None,
        relevance_threshold: float = 3.0,
        min_groundedness: float = 0.5,
    ):
        """初始化 Self-RAG 控制器

        Args:
            llm: LLM 实例
            retriever: 检索器
            relevance_threshold: 相关性阈值（1-5分制）
            min_groundedness: 最低支撑度
        """
        self.llm = llm
        self.retriever = retriever
        self.relevance_threshold = relevance_threshold
        self.min_groundedness = min_groundedness

    async def reflective_generate(
        self,
        query: str,
        top_k: int = 5,
    ) -> SelfRAGResult:
        """带反思的生成

        Args:
            query: 用户问题
            top_k: 检索返回数量

        Returns:
            SelfRAGResult: 生成结果和反思日志
        """
        reflection_log = []
        context = []

        # 1. 判断是否需要检索
        use_retrieval = await self._should_retrieve(query)
        reflection_log.append(f"{ReflectionToken.NEED_RETRIEVAL.value} {'是' if use_retrieval else '否'}")

        if not use_retrieval:
            # 不需要检索，直接生成
            answer = await self._generate_without_context(query)
            return SelfRAGResult(
                answer=answer,
                used_retrieval=False,
                reflection_log=reflection_log,
            )

        # 2. 执行检索
        if self.retriever:
            retrieved_docs = await self._retrieve(query, top_k)
            context = retrieved_docs
        else:
            retrieved_docs = []

        if not retrieved_docs:
            reflection_log.append("[无检索结果]")
            answer = await self._generate_without_context(query)
            return SelfRAGResult(
                answer=answer,
                used_retrieval=True,
                context=[],
                reflection_log=reflection_log,
                is_relevant=False,
            )

        # 3. 评估检索结果相关性
        relevance_scores = []
        for i, doc in enumerate(retrieved_docs):
            score = await self._evaluate_relevance(query, doc)
            relevance_scores.append(score)
            reflection_log.append(f"[相关] 文档{i+1}: {score}/5")

        # 过滤低相关文档
        if any(s < self.relevance_threshold for s in relevance_scores):
            filtered_docs = []
            for doc, score in zip(retrieved_docs, relevance_scores):
                if score >= self.relevance_threshold:
                    filtered_docs.append(doc)

            if filtered_docs:
                retrieved_docs = filtered_docs
                reflection_log.append(f"[过滤] 移除了 {len(context) - len(filtered_docs)} 个低相关文档")
            else:
                reflection_log.append("[警告] 所有文档相关性都低于阈值")

        # 4. 生成答案
        context_content = [doc.get("content", doc.get("page_content", "")) for doc in retrieved_docs]
        answer = await self._generate_with_context(query, context_content, retrieved_docs)

        # 5. 评估生成支撑度
        if context_content:
            groundedness = await self._evaluate_groundedness(
                query, context_content, answer
            )
            reflection_log.append(f"[支撑度] {groundedness:.2f}")

            if groundedness < self.min_groundedness:
                reflection_log.append("[重新生成] 支撑度不足，尝试重新生成")
                # 尝试重新生成（使用更严格的提示）
                answer = await self._regenerate_with_strict_prompt(query, context_content)
                groundedness = await self._evaluate_groundedness(query, context_content, answer)
                reflection_log.append(f"[重新生成后] 支撑度: {groundedness:.2f}")

        else:
            groundedness = 0.0

        return SelfRAGResult(
            answer=answer,
            used_retrieval=True,
            context=retrieved_docs,
            reflection_log=reflection_log,
            relevance_scores=relevance_scores,
            groundedness=groundedness,
            is_relevant=any(s >= self.relevance_threshold for s in relevance_scores),
        )

    async def _should_retrieve(self, query: str) -> bool:
        """判断是否需要检索

        Args:
            query: 用户问题

        Returns:
            bool: 是否需要检索
        """
        if not self.llm:
            # 无 LLM 时，使用启发式判断
            return self._heuristic_retrieval_decision(query)

        prompt = self.RETRIEVAL_PROMPT.format(query=query)

        try:
            response = await self._call_llm(prompt)
            return "检索" in response.strip()
        except Exception as e:
            logger.error(f"Retrieval decision failed: {e}")
            return True  # 默认检索

    def _heuristic_retrieval_decision(self, query: str) -> bool:
        """启发式检索决策

        无 LLM 时的降级方案。
        """
        # 需要检索的关键词
        need_retrieval_keywords = [
            "什么", "多少", "如何", "为什么", "哪个",
            "who", "what", "when", "where", "how", "why",
            "数据", "研究", "论文", "结果", "实验",
        ]

        # 不需要检索的关键词
        no_retrieval_keywords = [
            "你认为", "你觉得", "我觉得",
            "帮我写", "生成",
        ]

        # 检查
        for kw in no_retrieval_keywords:
            if kw in query:
                return False

        for kw in need_retrieval_keywords:
            if kw in query:
                return True

        return True  # 默认检索

    async def _retrieve(
        self,
        query: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """执行检索

        Args:
            query: 查询
            top_k: 返回数量

        Returns:
            List[Dict[str, Any]]: 检索结果
        """
        if not self.retriever:
            return []

        try:
            if asyncio.iscoroutinefunction(self.retriever):
                return await self.retriever(query, top_k=top_k)
            else:
                return self.retriever(query, top_k=top_k)
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []

    async def _evaluate_relevance(
        self,
        query: str,
        doc: Dict[str, Any],
    ) -> float:
        """评估文档相关性（1-5分）

        Args:
            query: 查询
            doc: 文档

        Returns:
            float: 相关性分数
        """
        if not self.llm:
            return self._simple_relevance_score(query, doc)

        content = doc.get("content", doc.get("page_content", str(doc)))[:500]

        prompt = self.RELEVANCE_PROMPT.format(
            query=query,
            doc_content=content,
        )

        try:
            response = await self._call_llm(prompt)
            score = float(response.strip())
            return max(1.0, min(5.0, score))
        except Exception as e:
            logger.error(f"Relevance evaluation failed: {e}")
            return 3.0  # 默认中等相关

    def _simple_relevance_score(self, query: str, doc: Dict[str, Any]) -> float:
        """简单的相关性评分

        无 LLM 时的降级方案。
        """
        content = doc.get("content", doc.get("page_content", str(doc)))
        query_terms = set(query.lower().split())
        content_terms = set(content.lower().split())

        if not query_terms:
            return 3.0

        overlap = len(query_terms & content_terms)
        score = overlap / len(query_terms)

        # 映射到 1-5 分
        if score >= 0.8:
            return 5.0
        elif score >= 0.5:
            return 4.0
        elif score >= 0.3:
            return 3.0
        elif score >= 0.1:
            return 2.0
        else:
            return 1.0

    async def _generate_with_context(
        self,
        query: str,
        context: List[str],
        docs: List[Dict[str, Any]],
    ) -> str:
        """基于上下文生成答案

        Args:
            query: 查询
            context: 上下文内容列表
            docs: 原始文档

        Returns:
            str: 生成的答案
        """
        formatted_context = "\n\n".join([
            f"[文档 {i+1}]\n{ctx[:500]}"
            for i, ctx in enumerate(context)
        ])

        prompt = f"""基于以下学术文献内容回答问题。
请确保：
1. 答案准确基于提供的文献
2. 每个重要论点都标注引用来源，如 [1], [2]
3. 如文献不足，明确说明

文献内容:
{formatted_context}

问题: {query}

答案："""

        try:
            return await self._call_llm(prompt)
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return "生成答案时发生错误。"

    async def _generate_without_context(self, query: str) -> str:
        """无上下文生成

        Args:
            query: 查询

        Returns:
            str: 生成的答案
        """
        prompt = f"""问题: {query}

请直接回答。如果问题涉及专业知识但你不确定，请明确说明不确定性。"""

        try:
            return await self._call_llm(prompt)
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return "无法回答这个问题。"

    async def _evaluate_groundedness(
        self,
        query: str,
        context: List[str],
        answer: str,
    ) -> float:
        """评估答案的事实支撑度

        Args:
            query: 查询
            context: 上下文
            answer: 答案

        Returns:
            float: 支撑度分数 (0-1)
        """
        if not self.llm:
            return self._simple_groundedness_score(answer, context)

        formatted_context = "\n\n".join(ctx[:300] for ctx in context[:3])

        prompt = self.GROUNDEDNESS_PROMPT.format(
            query=query,
            context=formatted_context,
            answer=answer,
        )

        try:
            response = await self._call_llm(prompt)
            response = response.strip()

            if "支持" in response and "部分" not in response:
                return 1.0
            elif "部分支持" in response:
                return 0.6
            elif "矛盾" in response:
                return 0.2
            else:
                return 0.5

        except Exception as e:
            logger.error(f"Groundedness evaluation failed: {e}")
            return 0.5

    def _simple_groundedness_score(self, answer: str, context: List[str]) -> float:
        """简单的支撑度评分

        无 LLM 时的降级方案。
        """
        if not context:
            return 0.3

        # 检查答案中的关键术语是否在上下文中出现
        answer_terms = set(answer.lower().split())
        context_text = " ".join(ctx.lower() for ctx in context)
        context_terms = set(context_text.split())

        overlap = len(answer_terms & context_terms)
        if answer_terms:
            score = overlap / len(answer_terms)
        else:
            score = 0.5

        return min(1.0, score * 1.5)  # 简单缩放

    async def _regenerate_with_strict_prompt(
        self,
        query: str,
        context: List[str],
    ) -> str:
        """使用更严格的提示重新生成

        Args:
            query: 查询
            context: 上下文

        Returns:
            str: 重新生成的答案
        """
        formatted_context = "\n\n".join([
            f"[文档 {i+1}]\n{ctx[:500]}"
            for i, ctx in enumerate(context)
        ])

        prompt = f"""严格基于以下文献回答问题。
只使用文献中明确提到的信息，不要添加外部知识。

文献内容:
{formatted_context}

问题: {query}

要求：
1. 只使用文献中的信息
2. 不确定的信息明确说明
3. 使用 [1], [2] 标注引用

答案："""

        try:
            return await self._call_llm(prompt)
        except Exception as e:
            logger.error(f"Regeneration failed: {e}")
            return "重新生成失败。"

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        try:
            if hasattr(self.llm, 'agenerate'):
                result = await self.llm.agenerate([prompt])
                return result.generations[0][0].text.strip()
            elif hasattr(self.llm, 'generate'):
                result = self.llm.generate([prompt])
                return result.generations[0][0].text.strip()
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise


# 便捷函数
async def self_rag_answer(
    query: str,
    llm: Optional[Any] = None,
    retriever: Optional[Callable] = None,
    **kwargs
) -> SelfRAGResult:
    """Self-RAG 答案生成的便捷函数"""
    controller = SelfRAGController(llm=llm, retriever=retriever, **kwargs)
    return await controller.reflective_generate(query)