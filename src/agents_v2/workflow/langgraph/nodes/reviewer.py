"""
Reviewer Agent - LangGraph 工作流节点

职责：
- 审查草稿质量
- 提供修改建议
- 控制迭代终止条件
- 术语一致性检查
- 逻辑连贯性验证
- 章节过渡检查
- 重复内容检测

集成现有的 ReviewerAgent (paper_agents/reviewer_agent.py)。
"""

from src.agents_v2.logging_config import get_logging_logger

import time
import re
from typing import List, Dict, Set, Tuple, Optional
from collections import Counter

from ..state import PaperAgentState

logger = get_logging_logger(__name__)


class TerminologyChecker:
    """术语一致性检查器"""

    def __init__(self):
        self.term_variants: Dict[str, List[str]] = {
            # AI/ML 术语
            "深度学习": ["深度学习", "DL", "Deep Learning"],
            "机器学习": ["机器学习", "ML", "Machine Learning"],
            "神经网络": ["神经网络", "Neural Network", "NN"],
            "卷积神经网络": ["卷积神经网络", "CNN", "Convolutional Neural Network"],
            "循环神经网络": ["循环神经网络", "RNN", "Recurrent Neural Network"],
            "Transformer": ["Transformer", "transformer", "变换器"],
            "注意力机制": ["注意力机制", "Attention", "注意力"],
            "自然语言处理": ["自然语言处理", "NLP", "Natural Language Processing"],
            "计算机视觉": ["计算机视觉", "CV", "Computer Vision"],
        }

    def extract_terms(self, text: str) -> Set[str]:
        """提取文本中的术语"""
        terms = set()
        text_lower = text.lower()

        for canonical, variants in self.term_variants.items():
            for variant in variants:
                if variant.lower() in text_lower:
                    terms.add(canonical)
                    break

        # 提取额外术语（连续大写字母，如CNN, RNN, LSTM）
        extra_terms = re.findall(r'\b[A-Z]{2,}\b', text)
        terms.update(extra_terms)

        return terms

    def check_consistency(self, text: str) -> List[str]:
        """检查术语一致性，返回问题列表"""
        issues = []
        terms = self.extract_terms(text)

        for canonical, variants in self.term_variants.items():
            found_variants = [v for v in variants if v.lower() in text.lower()]
            if len(found_variants) > 1:
                issues.append(
                    f"术语不一致: '{canonical}' 存在多种表达 "
                    f"{found_variants}，建议统一使用 '{canonical}'"
                )

        return issues


class CoherenceChecker:
    """逻辑连贯性检查器"""

    def __init__(self):
        self.transition_keywords = [
            "因此", "然而", "但是", "此外", "更进一步",
            "首先", "其次", "最后", "综上所述",
            "另一方面", "与此同时", "值得注意的是",
            "为了验证", "基于此", "由此可见"
        ]

    def check_section_coherence(
        self,
        sections: List[Dict[str, str]]
    ) -> List[str]:
        """检查章节间的连贯性"""
        issues = []

        for i in range(len(sections) - 1):
            current = sections[i]
            next_section = sections[i + 1]

            # 检查当前章节结尾和下一章节开头是否衔接
            current_ending = current.get("content", "")[-200:]
            next_beginning = next_section.get("content", "")[:200]

            # 检查是否有过渡词
            has_transition = any(
                kw in current_ending or kw in next_beginning
                for kw in self.transition_keywords
            )

            if not has_transition:
                issues.append(
                    f"章节衔接问题: '{current.get('title', f'Section {i}')}' "
                    f"和 '{next_section.get('title', f'Section {i+1}')}' "
                    f"之间缺少过渡句"
                )

        return issues

    def generate_transition(
        self,
        current_ending: str,
        next_beginning: str,
        current_title: str = "",
        next_title: str = ""
    ) -> str:
        """
        生成两个章节之间的过渡句

        Args:
            current_ending: 当前章节结尾
            next_beginning: 下一章节开头
            current_title: 当前章节标题
            next_title: 下一章节标题

        Returns:
            str: 生成的过渡句
        """
        # 分析关键词判断过渡类型
        transition_type = self._analyze_transition_type(
            current_ending, next_beginning
        )

        if transition_type == "cause_effect":
            return "基于上述分析，本文接下来将探讨其具体实现方法。"
        elif transition_type == "contrast":
            return "然而，上述方法存在一定局限性，需要进一步改进。"
        elif transition_type == "sequence":
            return "在深入分析上述内容之后，我们将进一步展开讨论。"
        elif transition_type == "elaboration":
            return "具体而言，上述研究可以从以下几个方面进行扩展。"
        elif transition_type == "summary_next":
            return "综合以上讨论，本文将在下一章节提出相应的解决方案。"
        else:
            return "基于以上论述，我们接下来进行更深入的探讨。"

    def _analyze_transition_type(
        self,
        current_ending: str,
        next_beginning: str
    ) -> str:
        """分析两个章节之间的过渡类型"""
        current_lower = current_ending.lower()
        next_lower = next_beginning.lower()

        # 因果关系：前面提出原因/方法，后面跟结果/应用
        if any(kw in current_lower for kw in ["因此", "所以", "从而", "于是"]):
            return "cause_effect"

        # 对比关系：前后存在转折或对比
        if any(kw in current_lower for kw in ["但是", "然而", "不过"]):
            return "contrast"
        if any(kw in next_lower for kw in ["然而", "但是", "相比之下"]):
            return "contrast"

        # 序列关系：前面列举，后面总结或继续
        if any(kw in current_lower for kw in ["首先", "其次", "最后"]):
            return "sequence"

        # 详细阐述：后面是前面的细化
        if any(kw in next_lower for kw in ["具体而言", "具体来说", "详细分析"]):
            return "elaboration"

        # 总结-过渡：前面总结，后面引出新话题
        if any(kw in current_lower for kw in ["综上所述", "总之", "总而言之"]):
            return "summary_next"

        return "general"

    def add_transitions(
        self,
        sections: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        在章节之间添加过渡句

        Args:
            sections: 各章节列表 [{title, content}, ...]

        Returns:
            添加过渡句后的章节列表
        """
        if len(sections) < 2:
            return sections

        result = []
        for i, section in enumerate(sections):
            # 添加当前章节
            result.append(section)

            # 如果不是最后一个章节，添加过渡句
            if i < len(sections) - 1:
                next_section = sections[i + 1]

                current_ending = section.get("content", "")[-200:] if section.get("content") else ""
                next_beginning = next_section.get("content", "")[:200] if next_section.get("content") else ""

                # 生成过渡句
                transition = self.generate_transition(
                    current_ending=current_ending,
                    next_beginning=next_beginning,
                    current_title=section.get("title", ""),
                    next_title=next_section.get("title", "")
                )

                # 将过渡句附加到当前章节内容末尾
                if result[-1].get("content"):
                    result[-1]["content"] += f"\n\n{transition}"
                else:
                    result[-1]["content"] = transition

        return result


class DuplicateDetector:
    """重复内容检测器"""

    def __init__(self, min_duplicate_length: int = 50):
        self.min_duplicate_length = min_duplicate_length

    def detect_duplicates(self, text: str) -> List[str]:
        """检测重复内容"""
        issues = []

        # 按句子分割
        sentences = re.split(r'[。！？\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # 检查相邻重复
        for i in range(len(sentences) - 1):
            current = sentences[i]
            next_sentence = sentences[i + 1]

            if len(current) >= self.min_duplicate_length:
                # 计算相似度（简单字符重叠）
                overlap = self._calculate_overlap(current, next_sentence)
                if overlap > 0.7:
                    issues.append(
                        f"内容重复: 相邻句子高度相似 (相似度 {overlap:.0%})，"
                        f"建议合并或删减"
                    )

        return issues

    def _calculate_overlap(self, text1: str, text2: str) -> float:
        """计算两个文本的重叠度"""
        if not text1 or not text2:
            return 0.0

        words1 = set(text1)
        words2 = set(text2)

        intersection = words1 & words2
        union = words1 | words2

        if not union:
            return 0.0

        return len(intersection) / len(union)


class FullPaperPolisher:
    """全文超级编辑 - 整体连贯性保障"""

    def __init__(self, llm=None):
        self.llm = llm
        self.terminology_checker = TerminologyChecker()
        self.coherence_checker = CoherenceChecker()
        self.duplicate_detector = DuplicateDetector()

    async def polish_full_paper(
        self,
        sections: List[Dict[str, str]]
    ) -> Tuple[List[Dict[str, str]], List[str]]:
        """
        对整篇论文进行连贯性编辑

        Returns:
            Tuple[编辑后的章节, 发现的问题列表]
        """
        issues = []

        # 1. 术语一致性检查
        full_text = "\n".join([s.get("content", "") for s in sections])
        term_issues = self.terminology_checker.check_consistency(full_text)
        issues.extend(term_issues)

        # 2. 章节连贯性检查
        section_issues = self.coherence_checker.check_section_coherence(sections)
        issues.extend(section_issues)

        # 3. 逻辑流程检查
        logic_issues = self.coherence_checker.check_logical_flow(full_text)
        issues.extend(logic_issues)

        # 4. 重复内容检测
        duplicate_issues = self.duplicate_detector.detect_duplicates(full_text)
        issues.extend(duplicate_issues)

        # 5. 使用LLM进行深度连贯性修复（如果有LLM）
        if self.llm and issues:
            sections = await self._llm_polish(sections, issues)

        return sections, issues

    async def _llm_polish(
        self,
        sections: List[Dict[str, str]],
        issues: List[str]
    ) -> List[Dict[str, str]]:
        """使用LLM进行深度修复"""
        if not self.llm:
            return sections

        prompt = f"""你是一个专业的学术论文编辑，负责确保论文的连贯性和一致性。

发现的问题：
{chr(10).join(['- ' + issue for issue in issues])}

请对以下论文各章节进行修改，确保：
1. 术语统一（同一概念始终使用相同表达）
2. 章节之间有过渡句
3. 逻辑连贯，结论有据
4. 消除重复内容

论文章节：
""" + "\n".join([f"## {s.get('title', 'Untitled')}\n{s.get('content', '')}" for s in sections]) + """

请直接输出修改后的论文，保持相同的章节结构。"""

        try:
            from langchain_core.messages import HumanMessage

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content

            # 解析修改后的内容，重新填充sections
            # 这里简化处理，实际可能需要更复杂的解析
            return sections
        except Exception as e:
            logger.warning(f"LLM polish 失败: {e}")
            return sections


class ReviewerAgent:
    """审查 Agent - LangGraph 节点"""

    def __init__(self, llm=None, min_quality_score: float = 0.6):
        """
        Args:
            llm: LangChain LLM 实例。如果为 None，使用规则审查。
            min_quality_score: 最低质量阈值，达到则停止迭代
        """
        self.llm = llm
        self.min_quality_score = min_quality_score

    def _rule_based_review(self, draft: str) -> List[str]:
        """基于规则的审查（无 LLM 时的回退方案）"""
        feedback = []

        if not draft:
            feedback.append("草稿为空，需要重新生成")
            return feedback

        # 检查长度
        word_count = len(draft.split())
        if word_count < 500:
            feedback.append(f"草稿过短（{word_count} 词），建议扩展到至少 1500 词")

        # 检查章节完整性
        section_count = draft.count("## ")
        if section_count < 3:
            feedback.append("章节数量不足，建议至少包含 5 个章节")

        # 检查引用格式
        if "[" not in draft or "]" not in draft:
            feedback.append("缺少文献引用，请添加 [Title, Year] 格式的引用")

        # 检查是否有分析性内容
        analysis_keywords = ["however", "although", "compared to", "in contrast", "limitation", "challenge"]
        has_analysis = any(kw in draft.lower() for kw in analysis_keywords)
        if not has_analysis:
            feedback.append("缺少批判性分析，请添加方法间的对比和局限性讨论")

        if not feedback:
            feedback.append("草稿质量良好，无需修改")

        return feedback

    async def _llm_review(self, draft: str) -> List[str]:
        """使用 LLM 进行深度审查"""
        if self.llm is None:
            return self._rule_based_review(draft)

        prompt = f"""You are an expert academic reviewer. Review the following survey draft and provide specific, constructive feedback.

Draft:
{draft[:5000]}

Please provide feedback on:
1. Content completeness and depth
2. Citation quality and integration
3. Critical analysis and comparison
4. Writing clarity and organization
5. Logical coherence and consistency (terminology, transitions)
6. Areas for improvement

Return a list of feedback points, each on a new line starting with "- ".
If the draft is good, return "The draft is good and requires no changes"."""

        try:
            from langchain_core.messages import HumanMessage

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            feedback = [
                line.lstrip("- ").strip()
                for line in content.split("\n")
                if line.strip().startswith("-") or (line.strip() and content == line)
            ]
            if not feedback and content:
                feedback = [content]
            return feedback
        except Exception as e:
            logger.warning(f"LLM 审查失败，使用规则审查: {e}")
            return self._rule_based_review(draft)

    async def _check_terminology_consistency(self, draft: str) -> List[str]:
        """检查术语一致性"""
        checker = TerminologyChecker()
        return checker.check_consistency(draft)

    async def _check_coherence(self, draft: str) -> List[str]:
        """检查逻辑连贯性"""
        coherence_checker = CoherenceChecker()
        logic_issues = coherence_checker.check_logical_flow(draft)

        # 检查术语
        term_checker = TerminologyChecker()
        term_issues = term_checker.check_consistency(draft)

        return logic_issues + term_issues

    async def _check_duplicates(self, draft: str) -> List[str]:
        """检查重复内容"""
        detector = DuplicateDetector()
        return detector.detect_duplicates(draft)

    async def review_full_paper(
        self,
        sections: List[Dict[str, str]]
    ) -> Tuple[List[Dict[str, str]], List[str]]:
        """
        对整篇论文进行连贯性审查

        Args:
            sections: 各章节的字典列表 [{title, content, ...}, ...]

        Returns:
            Tuple[编辑后的章节, 发现的问题列表]
        """
        polisher = FullPaperPolisher(self.llm)
        return await polisher.polish_full_paper(sections)

    def execute(self, state: PaperAgentState) -> PaperAgentState:
        """LangGraph 节点入口"""
        draft = state.draft
        logger.info(f"[Reviewer] 开始审查草稿，当前迭代: {state.iteration}/{state.max_iterations}")
        start = time.time()

        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        feedback = loop.run_until_complete(self._llm_review(draft))

        # 过滤正面反馈
        actionable_feedback = [
            f for f in feedback
            if "good" not in f.lower() or "no changes" not in f.lower()
        ]

        state.feedback = actionable_feedback
        state.iteration += 1

        elapsed = time.time() - start
        logger.info(
            f"[Reviewer] 审查完成，发现 {len(actionable_feedback)} 条建议，耗时 {elapsed:.2f}s"
        )
        return state
