"""
Intent Classifier - 意图分类器

基于规则和LLM的意图分类器，支持多种意图类型。
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.agents_v2.core.exceptions import ValidationError


class IntentType(str, Enum):
    """意图类型枚举"""
    LITERATURE_SEARCH = "literature_search"
    LITERATURE_REVIEW = "literature_review"
    TOPIC_SELECT = "topic_select"
    THESIS_FORMULATE = "thesis_formulate"
    OUTLINE_GENERATE = "outline_generate"
    DRAFT_WRITE = "draft_write"
    FULL_PAPER = "full_paper"
    DIAGNOSTIC = "diagnostic"
    QUESTION_ANSWER = "question_answer"
    SUMMARY = "summary"
    TRANSLATION = "translation"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: IntentType
    confidence: float
    reasoning: str = ""
    alternatives: List[Tuple[IntentType, float]] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_confident(self, threshold: float = 0.7) -> bool:
        return self.confidence >= threshold

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value if isinstance(self.intent, Enum) else self.intent,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternatives": [(t.value, c) for t, c in self.alternatives],
            "entities": self.entities,
            "metadata": self.metadata
        }


class IntentClassifier:
    """
    意图分类器

    支持:
    - 基于关键词的快速分类
    - 基于LLM的深度分类
    - 多意图检测
    - 置信度评估

    使用示例:
        classifier = IntentClassifier()

        # 单一意图分类
        result = classifier.classify("帮我搜索关于深度学习的论文")
        print(f"意图: {result.intent}, 置信度: {result.confidence}")

        # 带阈值的判断
        if result.is_confident(0.8):
            print("高置信度意图")
    """

    # 意图关键词映射
    INTENT_KEYWORDS = {
        IntentType.LITERATURE_SEARCH: [
            "搜索", "查找", "检索", "找论文", "搜论文", "search", "find",
            "papers about", "文献检索", "搜索论文"
        ],
        IntentType.LITERATURE_REVIEW: [
            "综述", "文献综述", "总结", "review", "survey", "overview",
            "研究现状", "国内外研究"
        ],
        IntentType.TOPIC_SELECT: [
            "选题", "方向", "选择课题", "研究主题", "topic", "subject",
            "研究方向", "研究课题"
        ],
        IntentType.THESIS_FORMULATE: [
            "凝练", "thesis", "论题", "论点", "研究问题", "research question",
            "研究目标"
        ],
        IntentType.OUTLINE_GENERATE: [
            "大纲", "提纲", "结构", "outline", "框架", "目录",
            "章节安排", "论文结构"
        ],
        IntentType.DRAFT_WRITE: [
            "撰写", "写作", "写", "write", "draft", "初稿", "起草",
            "论文写作", "内容撰写"
        ],
        IntentType.FULL_PAPER: [
            "完整论文", "整个论文", "全文", "full paper", "complete",
            "一篇完整的论文", "写完整论文"
        ],
        IntentType.DIAGNOSTIC: [
            "诊断", "检查", "分析问题", "diagnostic", "check", "问题诊断",
            "分析"
        ],
        IntentType.QUESTION_ANSWER: [
            "问答", "回答问题", "问答系统", "question", "answer", "问答",
            "问题回答", "QA"
        ],
        IntentType.SUMMARY: [
            "摘要", "总结", "概要", "summary", "abstract", "概述",
            "内容总结"
        ],
        IntentType.TRANSLATION: [
            "翻译", "译", "translate", "translation", "中英翻译"
        ],
    }

    # 意图优先级（用于平分时）
    INTENT_PRIORITY = {
        IntentType.FULL_PAPER: 10,
        IntentType.LITERATURE_SEARCH: 8,
        IntentType.DRAFT_WRITE: 7,
        IntentType.OUTLINE_GENERATE: 6,
        IntentType.LITERATURE_REVIEW: 5,
        IntentType.TOPIC_SELECT: 4,
        IntentType.THESIS_FORMULATE: 3,
        IntentType.DIAGNOSTIC: 2,
        IntentType.QUESTION_ANSWER: 1,
        IntentType.SUMMARY: 1,
        IntentType.TRANSLATION: 1,
        IntentType.UNKNOWN: 0,
    }

    def __init__(
        self,
        use_llm: bool = False,
        confidence_threshold: float = 0.7,
        enable_multi_intent: bool = False
    ):
        """
        初始化意图分类器

        Args:
            use_llm: 是否使用LLM进行分类
            confidence_threshold: 置信度阈值
            enable_multi_intent: 是否支持多意图
        """
        self.use_llm = use_llm
        self.confidence_threshold = confidence_threshold
        self.enable_multi_intent = enable_multi_intent

    def classify(self, query: str) -> IntentResult:
        """
        分类用户意图

        Args:
            query: 用户查询

        Returns:
            IntentResult: 意图识别结果
        """
        if not query or not query.strip():
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                reasoning="Empty query"
            )

        # 1. 快速关键词匹配
        keyword_scores = self._calculate_keyword_scores(query)

        # 2. 获取最高匹配意图
        best_intent, base_confidence = self._get_best_intent(keyword_scores)

        # 3. 生成推理说明
        reasoning = self._generate_reasoning(query, best_intent, keyword_scores)

        # 4. 构建结果
        result = IntentResult(
            intent=best_intent,
            confidence=base_confidence,
            reasoning=reasoning,
            alternatives=self._get_alternatives(keyword_scores)
        )

        return result

    def _calculate_keyword_scores(self, query: str) -> Dict[IntentType, float]:
        """计算各意图的关键词匹配分数"""
        scores: Dict[IntentType, float] = {}
        query_lower = query.lower()

        for intent_type, keywords in self.INTENT_KEYWORDS.items():
            score = 0.0
            matched_keywords = []

            for keyword in keywords:
                if keyword.lower() in query_lower:
                    score += 1.0
                    matched_keywords.append(keyword)

            # 归一化分数
            if keywords:
                normalized_score = score / len(keywords)
                # 增加分数如果有关键词匹配
                if score > 0:
                    # 更多匹配 = 更高分数
                    normalized_score = min(1.0, normalized_score + 0.2 * score)
                scores[intent_type] = normalized_score

        return scores

    def _get_best_intent(
        self,
        scores: Dict[IntentType, float]
    ) -> Tuple[IntentType, float]:
        """获取最佳意图"""
        if not scores:
            return IntentType.UNKNOWN, 0.0

        # 排序：先按分数，再按优先级
        sorted_intents = sorted(
            scores.items(),
            key=lambda x: (x[1], self.INTENT_PRIORITY.get(x[0], 0)),
            reverse=True
        )

        best_intent, best_score = sorted_intents[0]

        # 如果最高分低于阈值，返回UNKNOWN
        if best_score < 0.1:
            return IntentType.UNKNOWN, best_score

        return best_intent, min(1.0, best_score)

    def _get_alternatives(
        self,
        scores: Dict[IntentType, float],
        top_k: int = 3
    ) -> List[Tuple[IntentType, float]]:
        """获取备选意图"""
        sorted_intents = sorted(
            scores.items(),
            key=lambda x: (x[1], self.INTENT_PRIORITY.get(x[0], 0)),
            reverse=True
        )

        alternatives = []
        for intent, score in sorted_intents[1:top_k + 1]:
            if score > 0.05:
                alternatives.append((intent, score))

        return alternatives

    def _generate_reasoning(
        self,
        query: str,
        intent: IntentType,
        scores: Dict[IntentType, float]
    ) -> str:
        """生成推理说明"""
        matched = []
        query_lower = query.lower()

        for keyword in self.INTENT_KEYWORDS.get(intent, []):
            if keyword.lower() in query_lower:
                matched.append(keyword)

        if matched:
            return f"关键词匹配: {', '.join(matched)}"
        elif intent == IntentType.UNKNOWN:
            return "未检测到明确意图关键词"
        else:
            return f"基于上下文推断为{intent.value}"

    def classify_with_fallback(
        self,
        query: str,
        fallback_intent: IntentType = IntentType.LITERATURE_SEARCH
    ) -> IntentResult:
        """
        带回退的意图分类

        Args:
            query: 用户查询
            fallback_intent: 无法识别时的默认意图

        Returns:
            IntentResult: 意图识别结果
        """
        result = self.classify(query)

        # 如果置信度过低，使用回退意图
        if not result.is_confident(self.confidence_threshold):
            result.intent = fallback_intent
            result.confidence = 0.5
            result.reasoning += f" (使用回退意图: {fallback_intent.value})"

        return result

    def batch_classify(self, queries: List[str]) -> List[IntentResult]:
        """批量分类"""
        return [self.classify(q) for q in queries]


def classify_intent(query: str) -> IntentResult:
    """便捷函数：意图分类"""
    classifier = IntentClassifier()
    return classifier.classify(query)