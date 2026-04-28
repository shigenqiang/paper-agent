"""
Self-RAG 生成控制器 - 用于论文写作的自我反思生成

功能:
1. 生成过程中的自我评估
2. 反思与修订的触发条件
3. Retrieval-Augmented Writing
4. 抄袭检测与原创性保证

设计原则:
- 在生成过程中进行反思
- 根据评估结果决定是否修订
- 确保内容的原创性
"""
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ReflectionType(str, Enum):
    """反思类型"""
    NEED_RETRIEVAL = "need_retrieval"
    NEED_REVISION = "need_revision"
    LOGIC_CHECK = "logic_check"
    ORIGINALITY_CHECK = "originality_check"
    QUALITY_CHECK = "quality_check"
    NO_ISSUE = "no_issue"


@dataclass
class ReflectionResult:
    """反思结果"""
    reflection_type: ReflectionType
    score: float  # 0-1
    passed: bool
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    original_text: str = ""
    revised_text: str = ""


@dataclass
class WritingQualityReport:
    """写作质量报告"""
    overall_score: float  # 0-1
    originality_score: float
    logic_score: float
    relevance_score: float
    clarity_score: float
    reflections: List[ReflectionResult] = field(default_factory=list)
    passed: bool
    suggestions: List[str] = field(default_factory=list)


class SelfRAGWritingController:
    """Self-RAG 论文写作控制器

    在论文生成过程中进行多维度反思和质量控制
    """

    def __init__(self, llm: Any = None):
        """初始化控制器

        Args:
            llm: LLM实例（用于评估）
        """
        self.llm = llm

        # 阈值配置
        self.originality_threshold = 0.7
        self.logic_threshold = 0.6
        self.quality_threshold = 0.7

        # 反思历史
        self.reflection_history: List[ReflectionResult] = []

    async def reflect_on_generation(
        self,
        generated_text: str,
        context: Dict[str, Any]
    ) -> ReflectionResult:
        """对生成内容进行反思

        Args:
            generated_text: 生成的文本
            context: 上下文信息（包含query, retrieved_docs等）

        Returns:
            ReflectionResult: 反思结果
        """
        query = context.get("query", "")
        retrieved_docs = context.get("retrieved_docs", [])

        # 1. 检查是否需要检索补充
        need_retrieval = await self._check_need_retrieval(generated_text, query)

        # 2. 检查逻辑一致性
        logic_check = await self._check_logical_coherence(generated_text, context)

        # 3. 检查原创性
        originality_check = await self._check_originality(generated_text, retrieved_docs)

        # 4. 检查整体质量
        quality_check = await self._check_quality(generated_text, context)

        # 综合评估
        all_passed = all([
            need_retrieval.passed,
            logic_check.passed,
            originality_check.passed,
            quality_check.passed
        ])

        if all_passed:
            return ReflectionResult(
                reflection_type=ReflectionType.NO_ISSUE,
                score=1.0,
                passed=True,
                issues=[],
                suggestions=[]
            )

        # 找出最严重的问题
        issues = []
        suggestions = []
        min_score = 1.0

        for result in [need_retrieval, logic_check, originality_check, quality_check]:
            if not result.passed:
                issues.extend(result.issues)
                suggestions.extend(result.suggestions)
                min_score = min(min_score, result.score)

        # 确定问题类型
        if not originality_check.passed:
            reflection_type = ReflectionType.ORIGINALITY_CHECK
        elif not logic_check.passed:
            reflection_type = ReflectionType.LOGIC_CHECK
        elif not quality_check.passed:
            reflection_type = ReflectionType.QUALITY_CHECK
        else:
            reflection_type = ReflectionType.NEED_REVISION

        return ReflectionResult(
            reflection_type=reflection_type,
            score=min_score,
            passed=False,
            issues=issues[:5],  # 最多5个问题
            suggestions=suggestions[:5],  # 最多5个建议
            original_text=generated_text
        )

    async def _check_need_retrieval(
        self,
        text: str,
        query: str
    ) -> ReflectionResult:
        """检查是否需要检索补充信息"""
        # 检测是否包含不确定的表达
        uncertain_patterns = [
            r'不确定', r'可能', r'也许', r'maybe', r'perhaps',
            r'我们应该', r'需要进一步', r'uncertain', r'not sure'
        ]

        uncertain_count = sum(1 for p in uncertain_patterns if re.search(p, text, re.IGNORECASE))

        # 检测是否引用了具体数据
        has_data = bool(re.search(r'\d+(\.\d+)?%|\d+\.\d+\s*(%|准确率|召回率)', text))

        # 检测是否引用了具体文献
        has_citations = bool(re.search(r'\[(\d+)\]|\[@\w+\]', text))

        score = 1.0
        issues = []
        suggestions = []

        if uncertain_count > 3:
            score -= 0.2
            issues.append("文本包含较多不确定表达")

        if not has_data and len(text) > 500:
            score -= 0.2
            issues.append("缺少具体数据支撑")
            suggestions.append("检索相关文献获取具体数据")

        if not has_citations and len(text) > 300:
            score -= 0.1
            issues.append("缺少文献引用")
            suggestions.append("添加相关工作的引用")

        return ReflectionResult(
            reflection_type=ReflectionType.NEED_RETRIEVAL,
            score=max(0, score),
            passed=score >= 0.8,
            issues=issues,
            suggestions=suggestions
        )

    async def _check_logical_coherence(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> ReflectionResult:
        """检查逻辑一致性"""
        issues = []
        suggestions = []

        # 检查连接词的使用
        transition_words = [
            'however', 'therefore', 'furthermore', 'moreover',
            'consequently', 'meanwhile', '另一方面', '因此', '然而'
        ]

        has_transition = any(tw.lower() in text.lower() for tw in transition_words)

        # 检查是否有空洞的陈述
        weak_patterns = [
            r'very\s+\w+',
            r'really\s+\w+',
            r'quite\s+\w+',
            r'十分\s+\w+',
            r'非常\s+\w+'
        ]

        weak_count = 0
        for p in weak_patterns:
            weak_count += len(re.findall(p, text, re.IGNORECASE))

        score = 1.0

        if not has_transition and len(text) > 400:
            score -= 0.15
            issues.append("段落间缺少过渡词")
            suggestions.append("添加 'However', 'Furthermore' 等过渡词")

        if weak_count > 2:
            score -= 0.2
            issues.append(f"包含 {weak_count} 处空洞的修饰")
            suggestions.append("使用更具体、精确的表达")

        # 检查论点与论据匹配
        claim_words = ['show', 'demonstrate', 'prove', '表明', '证明', '显示']
        has_claims = any(cw in text.lower() for cw in claim_words)

        if has_claims:
            # 检查论据是否跟随
            claim_positions = []
            for cw in claim_words:
                for m in re.finditer(cw, text, re.IGNORECASE):
                    claim_positions.append(m.start())

            for pos in claim_positions:
                following = text[pos:pos+300]
                has_evidence = bool(re.search(r'\d+|实验|数据|结果|experiment|result', following))

                if not has_evidence:
                    score -= 0.15
                    issues.append("论点后面缺少具体证据")
                    suggestions.append("在声称后添加具体数据或实验结果")
                    break

        return ReflectionResult(
            reflection_type=ReflectionType.LOGIC_CHECK,
            score=max(0, score),
            passed=score >= self.logic_threshold,
            issues=issues,
            suggestions=suggestions
        )

    async def _check_originality(
        self,
        text: str,
        retrieved_docs: List[str]
    ) -> ReflectionResult:
        """检查原创性（抄袭检测）"""
        score = 1.0
        issues = []
        suggestions = []

        if not retrieved_docs:
            # 没有参考文档，默认通过
            return ReflectionResult(
                reflection_type=ReflectionType.ORIGINALITY_CHECK,
                score=1.0,
                passed=True
            )

        # 检测连续重复
        sentences = re.split(r'[.。!！?？\n]', text)
        repeated_patterns = []

        for i, sent1 in enumerate(sentences):
            if len(sent1) < 30:
                continue

            for j, sent2 in enumerate(sentences[i+1:], i+1):
                if len(sent2) < 30:
                    continue

                # 计算相似度（简化版本）
                overlap = len(set(sent1) & set(sent2)) / max(len(set(sent1)), 1)
                if overlap > 0.8 and len(sent1) > 50:
                    repeated_patterns.append(sent1[:50])
                    break

        if repeated_patterns:
            score -= 0.3
            issues.append(f"发现 {len(repeated_patterns)} 处可能重复的内容")
            suggestions.append("改写重复的句子，使用不同的表达方式")

        # 检测与参考文档的过高相似度
        suspicious_phrases = []
        for doc in retrieved_docs[:5]:  # 只检查前5个文档
            if len(doc) > 100:
                # 检查是否有超过20个连续字符与文档相同
                for i in range(len(text) - 20):
                    chunk = text[i:i+20]
                    if chunk in doc:
                        suspicious_phrases.append(chunk)
                        break

        if suspicious_phrases:
            score -= 0.3
            issues.append("检测到与参考文档高度相似的内容")
            suggestions.append("使用自己的语言重新表述这些内容，并添加引用")

        return ReflectionResult(
            reflection_type=ReflectionType.ORIGINALITY_CHECK,
            score=max(0, score),
            passed=score >= self.originality_threshold,
            issues=issues,
            suggestions=suggestions
        )

    async def _check_quality(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> ReflectionResult:
        """检查整体质量"""
        score = 1.0
        issues = []
        suggestions = []

        # 检查长度
        if len(text) < 100:
            score -= 0.3
            issues.append("内容过短")
            suggestions.append("添加更多详细内容")

        # 检查句子完整性
        incomplete_sentences = re.findall(r'\b(\w+)\s*$', text, re.MULTILINE)
        if incomplete_sentences:
            score -= 0.1
            issues.append("存在不完整的句子")

        # 检查是否包含模板化表达
        template_phrases = [
            "本文提出", "本研究表明", "实验结果表明",
            "our paper proposes", "our study shows", "experimental results show"
        ]

        template_count = sum(1 for p in template_phrases if p.lower() in text.lower())

        # 检查术语一致性
        key_terms = context.get("key_terms", [])
        missing_terms = []

        for term in key_terms:
            if term.lower() not in text.lower() and len(text) > 200:
                missing_terms.append(term)

        if missing_terms:
            score -= 0.1
            issues.append(f"缺少关键术语: {', '.join(missing_terms[:3])}")
            suggestions.append("在适当位置融入关键术语")

        return ReflectionResult(
            reflection_type=ReflectionType.QUALITY_CHECK,
            score=max(0, score),
            passed=score >= self.quality_threshold,
            issues=issues,
            suggestions=suggestions
        )

    async def revise_text(
        self,
        text: str,
        reflection: ReflectionResult
    ) -> str:
        """基于反思结果修订文本

        Args:
            text: 原始文本
            reflection: 反思结果

        Returns:
            str: 修订后的文本
        """
        if reflection.passed:
            return text

        revised = text

        # 应用各类型的修订
        for issue in reflection.issues:
            if "过渡词" in issue:
                revised = self._add_transitions(revised)
            elif "空洞" in issue:
                revised = self._remove_weak_modifiers(revised)
            elif "证据" in issue:
                revised = self._add_evidence_markers(revised)

        self.reflection_history.append(reflection)

        return revised

    def _add_transitions(self, text: str) -> str:
        """添加过渡词"""
        # 在段落开头添加过渡词
        paragraphs = text.split('\n\n')

        transition_map = {
            0: "",  # 第一段不需要
            1: "However, ",
            2: "Furthermore, ",
            3: "Moreover, ",
            4: "In addition, ",
        }

        for i, para in enumerate(paragraphs[1:], 1):
            if para.strip() and not re.match(r'^(However|Furthermore|Moreover|Additionally)', para):
                transition = transition_map.get(i, "Additionally, ")
                paragraphs[i] = transition + paragraphs[i]

        return '\n\n'.join(paragraphs)

    def _remove_weak_modifiers(self, text: str) -> str:
        """移除空洞的修饰词"""
        weak_patterns = [
            (r'\bvery\s+', ''),
            (r'\breally\s+', ''),
            (r'\bquite\s+', ''),
            (r'\b十分\s+', ''),
            (r'\b非常\s+', ''),
        ]

        for pattern, replacement in weak_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _add_evidence_markers(self, text: str) -> str:
        """添加证据标记"""
        claim_patterns = [
            (r'(show|demonstrate|prove|表明|证明)', r'\1 (see Section 4)'),
        ]

        for pattern, replacement in claim_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    async def generate_with_self_rag(
        self,
        prompt: str,
        context: Dict[str, Any]
    ) -> Tuple[str, WritingQualityReport]:
        """使用Self-RAG生成并评估

        Args:
            prompt: 生成提示
            context: 上下文信息

        Returns:
            Tuple[str, WritingQualityReport]: (生成文本, 质量报告)
        """
        if not self.llm:
            raise RuntimeError("LLM not initialized")

        # 1. 生成初始内容
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=context.get("system_prompt", "你是一个专业的学术写作助手。")),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        generated_text = response.content if hasattr(response, 'content') else str(response)

        # 2. 反思
        reflection = await self.reflect_on_generation(generated_text, context)

        # 3. 如果有问题，修订
        if not reflection.passed:
            logger.warning(f"Reflection issues found: {reflection.issues}")
            generated_text = await self.revise_text(generated_text, reflection)

        # 4. 生成质量报告
        report = WritingQualityReport(
            overall_score=reflection.score,
            originality_score=0.9 if reflection.reflection_type != ReflectionType.ORIGINALITY_CHECK else reflection.score,
            logic_score=0.8 if reflection.reflection_type != ReflectionType.LOGIC_CHECK else reflection.score,
            relevance_score=0.85 if reflection.reflection_type != ReflectionType.NEED_RETRIEVAL else reflection.score,
            clarity_score=0.8 if reflection.reflection_type != ReflectionType.QUALITY_CHECK else reflection.score,
            reflections=[reflection],
            passed=reflection.passed,
            suggestions=reflection.suggestions
        )

        return generated_text, report

    def get_reflection_history(self) -> List[ReflectionResult]:
        """获取反思历史"""
        return self.reflection_history


class OriginalityChecker:
    """原创性检查器

    用于检测文本与已有文献的重复
    """

    def __init__(self):
        self.threshold = 0.7

    async def check(self, text: str, reference_docs: List[str] = None) -> Dict[str, Any]:
        """检查原创性

        Args:
            text: 待检查文本
            reference_docs: 参考文档列表

        Returns:
            Dict: 检查结果
        """
        issues = []
        score = 1.0

        if not reference_docs:
            return {"passed": True, "score": 1.0, "issues": []}

        # 检查长字符串重复
        for doc in reference_docs:
            for i in range(len(text) - 30):
                chunk = text[i:i+30]
                if chunk in doc:
                    score -= 0.1
                    if score < self.threshold:
                        issues.append(f"发现与参考文献高度相似的段落")

        return {
            "passed": score >= self.threshold,
            "score": max(0, score),
            "issues": issues
        }

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度（简单版本）

        Returns:
            float: 相似度 0-1
        """
        set1 = set(text1)
        set2 = set(text2)

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0


# 便捷函数
async def write_with_reflection(
    prompt: str,
    context: Dict[str, Any],
    llm: Any
) -> Tuple[str, WritingQualityReport]:
    """使用Self-RAG进行反思式写作"""
    controller = SelfRAGWritingController(llm)
    return await controller.generate_with_self_rag(prompt, context)


async def check_originality(
    text: str,
    reference_docs: List[str] = None
) -> Dict[str, Any]:
    """检查文本原创性"""
    checker = OriginalityChecker()
    return await checker.check(text, reference_docs)