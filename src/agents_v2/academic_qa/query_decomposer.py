"""
查询分解器 - Query Decomposer

将复杂问题分解为可单独回答的子问题。
支持多跳推理。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.agents_v2.logging_config import get_logging_logger

import asyncio
import re

logger = get_logging_logger(__name__)


@dataclass
class SubQuestion:
    """子问题"""
    id: int
    text: str
    is_final: bool = False  # 是否是最终问题（需要综合）
    depends_on: List[int] = field(default_factory=list)  # 依赖的子问题 ID


class QueryDecomposer:
    """查询分解器

    将复杂学术问题分解为简单的子问题，支持多跳推理。
    """

    # 复杂度指标
    COMPLEXITY_INDICATORS = [
        "为什么", "如何", "分析", "比较", "关系",
        "多少个", "哪个更重要", "从...到...",
        "why", "how", "analyze", "compare", "relationship",
        "between", "among", "原因", "结果"
    ]

    # 多跳关键词
    MULTI_HOP_KEYWORDS = [
        "和...相比", "与其...不如", "先...后",
        "因为...所以", "虽然...但是",
        "谁在什么时候做了什么",
        "某人的观点是",
        "compared to", "instead of", "first...then",
        "because...therefore", "although...but"
    ]

    # 最终问题关键词
    FINAL_QUESTION_KEYWORDS = [
        "总结", "结论", "综上", "因此",
        "summarize", "conclude", "overall", "in conclusion"
    ]

    def __init__(
        self,
        llm: Optional[Any] = None,
        decomposition_threshold: int = 2,
        max_sub_questions: int = 5,
    ):
        """初始化查询分解器

        Args:
            llm: LLM 实例
            decomposition_threshold: 触发分解的复杂度阈值
            max_sub_questions: 最大子问题数量
        """
        self.llm = llm
        self.decomposition_threshold = decomposition_threshold
        self.max_sub_questions = max_sub_questions

    async def decompose(self, query: str) -> List[SubQuestion]:
        """分解查询

        Args:
            query: 用户查询

        Returns:
            List[SubQuestion]: 子问题列表
        """
        # 1. 判断是否需要分解
        if not await self._should_decompose(query):
            return [SubQuestion(id=1, text=query, is_final=True)]

        # 2. 执行分解
        if self.llm:
            sub_questions = await self._llm_decompose(query)
        else:
            sub_questions = self._heuristic_decompose(query)

        # 3. 添加依赖关系
        sub_questions = self._add_dependencies(sub_questions)

        return sub_questions

    async def _should_decompose(self, query: str) -> bool:
        """判断是否需要分解

        Args:
            query: 查询

        Returns:
            bool: 是否需要分解
        """
        # 包含多跳关键词必定需要分解
        for keyword in self.MULTI_HOP_KEYWORDS:
            if keyword in query.lower():
                return True

        # 计算复杂度分数
        score = self._calculate_complexity(query)

        return score >= self.decomposition_threshold

    def _calculate_complexity(self, query: str) -> int:
        """计算查询复杂度分数

        Args:
            query: 查询

        Returns:
            int: 复杂度分数
        """
        score = 0

        # 检查复杂度指标
        for indicator in self.COMPLEXITY_INDICATORS:
            if indicator in query.lower():
                score += 1

        # 检查问题长度（过长通常更复杂）
        if len(query) > 50:
            score += 1
        if len(query) > 100:
            score += 1

        # 检查是否包含多个问题
        question_marks = query.count("?")
        if question_marks > 1:
            score += question_marks

        # 检查是否涉及多实体
        entities = self._extract_entities(query)
        if len(entities) > 2:
            score += 1

        return score

    def _extract_entities(self, text: str) -> List[str]:
        """提取实体

        简单的实体提取（人名、机构名等）。
        """
        # 匹配引号内的内容
        quotes = re.findall(r'["""](.+?)["""]', text)
        if quotes:
            return quotes

        # 匹配括号内的内容
        brackets = re.findall(r'[(（](.+?)[)）]', text)
        if brackets:
            return brackets

        return []

    async def _llm_decompose(self, query: str) -> List[SubQuestion]:
        """使用 LLM 分解查询

        Args:
            query: 查询

        Returns:
            List[SubQuestion]: 子问题列表
        """
        prompt = f"""将以下复杂学术问题分解为简单的子问题。
每个子问题应该能够通过单次检索直接回答。

复杂问题: {query}

要求:
1. 分解后的子问题应该覆盖原问题的各个维度
2. 每个子问题应该足够简单，可以直接回答
3. 子问题之间应该有清晰的逻辑关联
4. 如果问题涉及多跳推理，先回答中间问题，再综合
5. 使用数字列表格式输出，每行一个子问题
6. 如果问题很简单不需要分解，输出原问题

子问题:"""

        try:
            response = await self._call_llm(prompt)
            sub_questions = self._parse_sub_questions(response)
            return sub_questions
        except Exception as e:
            logger.error(f"LLM decomposition failed: {e}")
            return self._heuristic_decompose(query)

    def _parse_sub_questions(self, response: str) -> List[SubQuestion]:
        """解析子问题列表

        Args:
            response: LLM 响应

        Returns:
            List[SubQuestion]: 子问题列表
        """
        lines = response.strip().split("\n")
        sub_questions = []

        for line in lines:
            line = line.strip()

            # 匹配数字列表格式: 1. xxx 或 1、xxx
            if not line:
                continue

            # 提取数字和内容
            match = re.match(r'^[\d１-９]+[.、\s]+(.+)', line)
            if match:
                content = match.group(1).strip()
            else:
                # 没有数字，可能是连续文本
                content = line

            if content and len(content) > 5:
                # 检查是否是最终问题
                is_final = any(kw in content for kw in self.FINAL_QUESTION_KEYWORDS)

                sub_questions.append(SubQuestion(
                    id=len(sub_questions) + 1,
                    text=content,
                    is_final=is_final,
                ))

        # 如果没有解析出来，尝试按句子分割
        if not sub_questions:
            sentences = re.split(r'[。！？.!?]+', response)
            for i, sent in enumerate(sentences):
                sent = sent.strip()
                if sent and len(sent) > 10:
                    sub_questions.append(SubQuestion(
                        id=i + 1,
                        text=sent,
                        is_final=any(kw in sent for kw in self.FINAL_QUESTION_KEYWORDS),
                    ))

        # 限制数量
        if len(sub_questions) > self.max_sub_questions:
            logger.warning(f"Too many sub-questions ({len(sub_questions)}), truncating to {self.max_sub_questions}")
            sub_questions = sub_questions[:self.max_sub_questions]

        # 如果只有一个子问题，标记为最终
        if len(sub_questions) == 1:
            sub_questions[0].is_final = True

        return sub_questions

    def _heuristic_decompose(self, query: str) -> List[SubQuestion]:
        """启发式分解

        无 LLM 时的降级方案。
        """
        # 检测是否包含多个部分
        separators = [
            "和", "与", "及", "以及",
            "and", "&", "同时", "另外",
            "而且", "并且"
        ]

        parts = [query]
        for sep in separators:
            new_parts = []
            for part in parts:
                new_parts.extend(part.split(sep))
            if len(new_parts) > len(parts):
                parts = new_parts
                break

        if len(parts) == 1:
            # 没有分隔符，尝试其他方法
            # 检查是否询问关系
            if "关系" in query or "difference" in query.lower():
                # 拆分为比较问题
                return [
                    SubQuestion(id=1, text=f"第一个方面是什么？"),
                    SubQuestion(id=2, text=f"第二个方面是什么？"),
                    SubQuestion(id=3, text=f"两者有什么关系？", is_final=True),
                ]

            # 默认返回原问题
            return [SubQuestion(id=1, text=query, is_final=True)]

        # 创建子问题
        sub_questions = []
        for i, part in enumerate(parts):
            part = part.strip()
            if len(part) > 5:
                is_final = i == len(parts) - 1  # 最后一个作为最终问题
                sub_questions.append(SubQuestion(
                    id=i + 1,
                    text=part,
                    is_final=is_final,
                ))

        return sub_questions if sub_questions else [SubQuestion(id=1, text=query, is_final=True)]

    def _add_dependencies(self, sub_questions: List[SubQuestion]) -> List[SubQuestion]:
        """添加子问题间的依赖关系

        Args:
            sub_questions: 子问题列表

        Returns:
            List[SubQuestion]: 带依赖关系的子问题列表
        """
        # 对于多跳问题，最后一个问题是综合问题，依赖前面的所有问题
        for i, sq in enumerate(sub_questions):
            if sq.is_final and i > 0:
                sq.depends_on = list(range(1, i + 1))

        return sub_questions

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

    def format_decomposition(self, sub_questions: List[SubQuestion]) -> str:
        """格式化分解结果

        Args:
            sub_questions: 子问题列表

        Returns:
            str: 格式化的文本
        """
        lines = ["=== 问题分解 ==="]

        for sq in sub_questions:
            dep_info = f" (依赖: {sq.depends_on})" if sq.depends_on else ""
            final_tag = " [综合]" if sq.is_final else ""
            lines.append(f"{sq.id}. {sq.text}{final_tag}{dep_info}")

        return "\n".join(lines)


# 便捷函数
async def decompose_query(
    query: str,
    llm: Optional[Any] = None,
    **kwargs
) -> List[SubQuestion]:
    """查询分解的便捷函数"""
    decomposer = QueryDecomposer(llm=llm, **kwargs)
    return await decomposer.decompose(query)


def format_sub_questions(sub_questions: List[SubQuestion]) -> str:
    """格式化子问题的便捷函数"""
    decomposer = QueryDecomposer()
    return decomposer.format_decomposition(sub_questions)