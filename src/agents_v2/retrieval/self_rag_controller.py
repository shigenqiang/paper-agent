"""
SELF-RAG控制器 - Self-RAG Reflection Controller

核心思想（来自论文Self-RAG, 2024）：
1. 判断是否需要检索：模型决定何时应该检索
2. 评估检索质量：判断检索结果是否相关
3. 决定是否采纳：根据质量决定是否使用检索结果
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """RAG响应"""
    answer: str
    used_docs: List[str]
    reflection: str
    retrieval_needed: bool = True
    documents_evaluated: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentEvaluation:
    """文档评估结果"""
    document: str
    relevance_score: float  # 0-1
    utility_score: float    # 0-1，对回答的有用程度
    should_use: bool
    reasoning: str


class SELF_RAGController:
    """SELF-RAG反思控制器"""

    def __init__(self,
                 llm: Any,
                 relevance_threshold: float = 0.7,
                 utility_threshold: float = 0.5):
        """初始化SELF-RAG控制器

        Args:
            llm: LLM实例
            relevance_threshold: 相关性阈值
            utility_threshold: 有用性阈值
        """
        self.llm = llm
        self.relevance_threshold = relevance_threshold
        self.utility_threshold = utility_threshold

    async def should_retrieve(self, query: str) -> bool:
        """判断是否需要检索

        Args:
            query: 查询字符串

        Returns:
            bool: 是否需要检索
        """
        prompt = f"""
查询: {query}

判断：是否需要从外部知识库检索信息来回答这个问题？
如果模型自身的知识已经足够回答，返回"否"。
如果需要最新信息、专业知识或事实数据，返回"是"。

返回：是 / 否
"""
        try:
            result = await self.llm.agenerate([prompt])
            response = result.generations[0][0].text.strip()

            # 解析响应
            if "否" in response and "是" not in response:
                logger.info(f"查询 '{query}' 不需要检索")
                return False
            else:
                logger.info(f"查询 '{query}' 需要检索")
                return True

        except Exception as e:
            logger.error(f"判断检索需求时出错: {e}")
            # 出错时默认检索
            return True

    async def evaluate_relevance(self, doc: str, query: str) -> float:
        """评估单个文档与查询的相关性 (0-1)

        Args:
            doc: 文档内容
            query: 查询字符串

        Returns:
            float: 相关性分数
        """
        # 截取文档前500字符进行评估
        doc_preview = doc[:500] if len(doc) > 500 else doc

        prompt = f"""
查询: {query}

文档内容:
{doc_preview}...

评估这个文档对回答查询的相关程度。
考虑：
- 内容是否直接相关？
- 信息是否准确？
- 是否有助于回答问题？

评分0-1，1表示高度相关，0表示完全不相关。
只返回一个数字。
"""
        try:
            result = await self.llm.agenerate([prompt])
            response = result.generations[0][0].text.strip()

            # 提取数字
            import re
            match = re.search(r'0?\.\d+', response)
            if match:
                score = float(match.group())
                return max(0.0, min(1.0, score))

            # 尝试解析整数
            match = re.search(r'\d+', response)
            if match:
                score = int(match.group())
                if score > 1:
                    score = score / 10.0
                return max(0.0, min(1.0, score))

            return 0.5  # 默认中等相关

        except Exception as e:
            logger.error(f"评估相关性时出错: {e}")
            return 0.5

    async def evaluate_utility(self, doc: str, query: str, partial_answer: str = "") -> float:
        """评估文档对当前回答的有用性 (0-1)

        Args:
            doc: 文档内容
            query: 查询字符串
            partial_answer: 当前的（部分）回答

        Returns:
            float: 有用性分数
        """
        doc_preview = doc[:500] if len(doc) > 500 else doc

        prompt = f"""
查询: {query}

当前回答（如果有）:
{partial_answer if partial_answer else "(无)"}

文档内容:
{doc_preview}...

评估这个文档对完善当前回答的有用程度。
考虑：
- 是否提供新的信息或证据？
- 是否有助于增强回答的完整性？
- 是否包含重要的引用或来源？

评分0-1，1表示非常有帮助，0表示没有帮助。
只返回一个数字。
"""
        try:
            result = await self.llm.agenerate([prompt])
            response = result.generations[0][0].text.strip()

            import re
            match = re.search(r'0?\.\d+', response)
            if match:
                return float(match.group())

            match = re.search(r'\d+', response)
            if match:
                score = int(match.group())
                if score > 1:
                    score = score / 10.0
                return max(0.0, min(1.0, score))

            return 0.5

        except Exception as e:
            logger.error(f"评估有用性时出错: {e}")
            return 0.5

    async def should_use_document(self, doc: str, query: str, partial_answer: str = "") -> bool:
        """判断是否应该使用该文档

        Args:
            doc: 文档内容
            query: 查询字符串
            partial_answer: 当前的（部分）回答

        Returns:
            bool: 是否应该使用
        """
        # 评估相关性
        relevance = await self.evaluate_relevance(doc, query)
        if relevance < self.relevance_threshold:
            return False

        # 评估有用性
        utility = await self.evaluate_utility(doc, query, partial_answer)
        if utility < self.utility_threshold:
            return False

        return True

    async def evaluate_documents(self, docs: List[str], query: str) -> List[DocumentEvaluation]:
        """批量评估文档

        Args:
            docs: 文档列表
            query: 查询字符串

        Returns:
            List[DocumentEvaluation]: 评估结果列表
        """
        evaluations = []

        for i, doc in enumerate(docs):
            relevance = await self.evaluate_relevance(doc, query)
            utility = await self.evaluate_utility(doc, query)
            should_use = relevance >= self.relevance_threshold and utility >= self.utility_threshold

            evaluation = DocumentEvaluation(
                document=doc[:100] + "..." if len(doc) > 100 else doc,  # 截断存储
                relevance_score=relevance,
                utility_score=utility,
                should_use=should_use,
                reasoning=f"相关性={relevance:.2f}, 有用性={utility:.2f}"
            )
            evaluations.append(evaluation)

            logger.debug(f"文档 {i+1}: 相关性={relevance:.2f}, 有用性={utility:.2f}, 使用={should_use}")

        return evaluations

    async def generate_with_reflection(self,
                                      query: str,
                                      retrieved_docs: List[str],
                                      max_context_docs: int = 5) -> RAGResponse:
        """带反思的RAG生成

        Args:
            query: 查询字符串
            retrieved_docs: 检索到的文档列表
            max_context_docs: 最多使用的文档数

        Returns:
            RAGResponse: RAG响应
        """
        start_time = time.time()

        # 1. 评估所有文档
        evaluations = await self.evaluate_documents(retrieved_docs, query)

        # 2. 选择要使用的文档
        selected_docs = []
        for eval_result in evaluations:
            if eval_result.should_use:
                # 找到原始文档
                original_doc = next(
                    (d for d in retrieved_docs if eval_result.document[:50] in d),
                    None
                )
                if original_doc and original_doc not in selected_docs:
                    selected_docs.append(original_doc)

                if len(selected_docs) >= max_context_docs:
                    break

        # 3. 如果没有相关文档
        if not selected_docs:
            logger.warning("没有找到相关文档，直接使用模型知识回答")

            # 直接使用模型知识回答
            answer_prompt = f"""
问题：{query}

请直接回答这个问题。
"""
            answer_result = await self.llm.agenerate([answer_prompt])
            answer = answer_result.generations[0][0].text.strip()

            return RAGResponse(
                answer=answer,
                used_docs=[],
                reflection="未找到相关文档，直接基于模型知识回答",
                retrieval_needed=True,
                documents_evaluated=len(retrieved_docs),
                metadata={"generation_time": time.time() - start_time}
            )

        # 4. 使用相关文档生成答案
        context = "\n\n".join([f"[文档{i+1}]\n{doc[:1000]}" for i, doc in enumerate(selected_docs)])

        answer_prompt = f"""
基于以下参考资料回答问题。每个文档开头标注了编号。

参考资料：
{context}

问题：{query}

请基于以上参考资料回答问题。
- 如果参考资料中有相关信息，基于这些信息回答
- 如果没有相关信息，说明你无法回答
- 引用你使用的参考资料编号

"""
        try:
            answer_result = await self.llm.agenerate([answer_prompt])
            answer = answer_result.generations[0][0].text.strip()
        except Exception as e:
            logger.error(f"生成答案时出错: {e}")
            answer = "抱歉，生成答案时出现错误。"

        return RAGResponse(
            answer=answer,
            used_docs=[f"[文档{i+1}]" for i in range(len(selected_docs))],
            reflection=f"使用了{len(selected_docs)}个相关文档，总共评估了{len(retrieved_docs)}个文档",
            retrieval_needed=True,
            documents_evaluated=len(retrieved_docs),
            metadata={
                "evaluations": [
                    {"relevance": e.relevance_score, "utility": e.utility_score, "used": e.should_use}
                    for e in evaluations
                ],
                "generation_time": time.time() - start_time
            }
        )

    async def iterative_rag(self,
                           query: str,
                           retriever: Any,
                           max_iterations: int = 3) -> RAGResponse:
        """迭代式RAG

        Args:
            query: 查询字符串
            retriever: 检索器实例，需要有retrieve(query, top_k)方法
            max_iterations: 最大迭代次数

        Returns:
            RAGResponse: RAG响应
        """
        all_results = []
        current_query = query

        for iteration in range(max_iterations):
            logger.info(f"迭代 {iteration + 1}/{max_iterations}: 查询 '{current_query}'")

            # 1. 检查是否需要检索
            if iteration == 0:
                need_retrieve = await self.should_retrieve(current_query)
                if not need_retrieve:
                    # 不需要检索，直接回答
                    answer_result = await self.llm.agenerate([current_query])
                    answer = answer_result.generations[0][0].text.strip()

                    return RAGResponse(
                        answer=answer,
                        used_docs=[],
                        reflection="不需要检索，直接基于模型知识回答",
                        retrieval_needed=False
                    )

            # 2. 检索
            try:
                candidates = await retriever.retrieve(current_query, top_k=20)
            except Exception as e:
                logger.error(f"检索出错: {e}")
                candidates = []

            if not candidates:
                logger.warning("检索返回空结果")
                break

            # 3. 评估并选择文档
            evaluations = await self.evaluate_documents(candidates, current_query)

            relevant_docs = []
            for i, eval_result in enumerate(evaluations):
                if eval_result.should_use and i < len(candidates):
                    relevant_docs.append(candidates[i])

            all_results.extend(relevant_docs)

            # 4. 检查是否足够
            if len(relevant_docs) >= 5:
                logger.info(f"找到足够相关文档 ({len(relevant_docs)})，停止检索")
                break

            # 5. 如果不够，改写查询继续检索
            if len(relevant_docs) < 3 and iteration < max_iterations - 1:
                current_query = await self._rewrite_query(current_query, candidates)

        # 6. 去重
        unique_results = list(dict.fromkeys(all_results))

        # 7. 生成最终答案
        return await self.generate_with_reflection(query, unique_results)

    async def _rewrite_query(self, original: str, irrelevant_docs: List[str]) -> str:
        """根据不相关文档改写查询

        Args:
            original: 原始查询
            irrelevant_docs: 不相关的文档

        Returns:
            str: 改写后的查询
        """
        docs_sample = "\n".join([f"- {d[:100]}..." for d in irrelevant_docs[:3]])

        prompt = f"""
原始查询：{original}

以下文档与查询不相关：
{docs_sample}

分析这些文档为什么不相关，然后改写查询以获得更好的检索结果。
返回改写后的查询，不要其他解释。
"""
        try:
            result = await self.llm.agenerate([prompt])
            rewritten = result.generations[0][0].text.strip()
            logger.info(f"查询改写: '{original}' -> '{rewritten}'")
            return rewritten
        except Exception as e:
            logger.error(f"查询改写失败: {e}")
            return original


# 便捷函数
async def self_rag_answer(query: str,
                          retrieved_docs: List[str],
                          llm: Any) -> RAGResponse:
    """使用SELF-RAG生成答案的便捷函数

    Args:
        query: 查询字符串
        retrieved_docs: 检索到的文档
        llm: LLM实例

    Returns:
        RAGResponse: RAG响应
    """
    controller = SELF_RAGController(llm)
    return await controller.generate_with_reflection(query, retrieved_docs)
