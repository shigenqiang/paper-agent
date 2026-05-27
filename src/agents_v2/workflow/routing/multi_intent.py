"""
Multi-Intent Detector - 多意图检测器

支持检测用户查询中的多个意图，处理复合意图场景。
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .intent_classifier import IntentType, IntentResult


@dataclass
class IntentCandidate:
    """意图候选"""
    intent: IntentType
    confidence: float
    position: Tuple[int, int]  # start, end in query
    trigger_keyword: str = ""


@dataclass
class MultiIntentResult:
    """多意图检测结果"""
    primary_intent: IntentType
    secondary_intents: List[IntentType] = field(default_factory=list)
    all_intents: List[IntentCandidate] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    is_compound: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_intent": self.primary_intent.value if isinstance(self.primary_intent, Enum) else self.primary_intent,
            "secondary_intents": [i.value if isinstance(i, Enum) else i for i in self.secondary_intents],
            "all_intents": [
                {
                    "intent": c.intent.value if isinstance(c.intent, Enum) else c.intent,
                    "confidence": c.confidence,
                    "position": c.position,
                    "trigger_keyword": c.trigger_keyword
                }
                for c in self.all_intents
            ],
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "is_compound": self.is_compound,
            "metadata": self.metadata
        }


class MultiIntentDetector:
    """
    多意图检测器

    支持检测复合意图，例如：
    - "帮我搜索深度学习论文，然后写个摘要"
    - "查找相关文献并生成大纲"

    使用示例:
        detector = MultiIntentDetector()

        result = detector.detect("搜索机器学习论文并写文献综述")
        print(f"主意图: {result.primary_intent}")
        print(f"次要意图: {result.secondary_intents}")
        print(f"复合意图: {result.is_compound}")
    """

    # 复合意图连接词
    COMPOUND_CONNECTORS = {
        "然后": 1.0,
        "并且": 0.9,
        "并且": 0.9,
        "接着": 0.9,
        "之后": 0.8,
        "再": 0.8,
        "同时": 0.8,
        "以及": 0.9,
        "和": 0.7,
        "以及": 0.9,
        "还有": 0.7,
        "另外": 0.7,
        "此外": 0.7,
        "最后": 0.6,
    }

    # 意图顺序标记（某些意图倾向于在前）
    INTENT_POSITION_BIAS = {
        IntentType.LITERATURE_SEARCH: 0.1,
        IntentType.DIAGNOSTIC: 0.1,
        IntentType.QUESTION_ANSWER: 0.1,
        IntentType.DRAFT_WRITE: 0.0,
        IntentType.OUTLINE_GENERATE: 0.0,
        IntentType.SUMMARY: -0.1,
        IntentType.LITERATURE_REVIEW: -0.05,
    }

    def __init__(self, min_confidence: float = 0.3):
        """
        初始化多意图检测器

        Args:
            min_confidence: 最小置信度阈值
        """
        self.min_confidence = min_confidence

    def detect(self, query: str) -> MultiIntentResult:
        """
        检测多意图

        Args:
            query: 用户查询

        Returns:
            MultiIntentResult: 多意图检测结果
        """
        if not query or not query.strip():
            return MultiIntentResult(
                primary_intent=IntentType.UNKNOWN,
                confidence=0.0,
                reasoning="Empty query"
            )

        # 1. 分割查询为子句
        segments = self._split_into_segments(query)

        # 2. 检测每个子句的意图
        candidates = []
        for segment in segments:
            candidate = self._detect_segment_intent(segment, query)
            if candidate and candidate.confidence >= self.min_confidence:
                candidates.append(candidate)

        # 3. 如果没有检测到多意图，尝试整体检测
        if len(candidates) < 2:
            single_result = self._detect_single_intent(query)
            return single_result

        # 4. 构建多意图结果
        return self._build_multi_intent_result(candidates, query)

    def _split_into_segments(self, query: str) -> List[str]:
        """将查询分割成多个段"""
        import re

        # 按连接词分割
        pattern = '|'.join(re.escape(k) for k in self.COMPOUND_CONNECTORS.keys())
        parts = re.split(f'({pattern})', query)

        segments = []
        current = ""

        for part in parts:
            if part.strip() in self.COMPOUND_CONNECTORS:
                if current.strip():
                    segments.append(current.strip())
                current = ""
            else:
                current += part

        if current.strip():
            segments.append(current.strip())

        return [s for s in segments if s.strip()]

    def _detect_segment_intent(
        self,
        segment: str,
        full_query: str
    ) -> Optional[IntentCandidate]:
        """检测单段的意图"""
        from .intent_classifier import IntentClassifier

        classifier = IntentClassifier()
        result = classifier.classify(segment)

        # 找到触发关键词
        trigger = self._find_trigger_keyword(segment, result.intent)

        # 计算位置
        position = self._find_position(segment, full_query)

        return IntentCandidate(
            intent=result.intent,
            confidence=result.confidence,
            position=position,
            trigger_keyword=trigger
        )

    def _find_trigger_keyword(self, segment: str, intent: IntentType) -> str:
        """找到触发意图的关键词"""
        from .intent_classifier import IntentClassifier

        keywords = IntentClassifier.INTENT_KEYWORDS.get(intent, [])
        segment_lower = segment.lower()

        for kw in keywords:
            if kw.lower() in segment_lower:
                return kw

        return ""

    def _find_position(self, segment: str, full_query: str) -> Tuple[int, int]:
        """找到段在完整查询中的位置"""
        start = full_query.find(segment)
        if start == -1:
            return (0, len(full_query))
        return (start, start + len(segment))

    def _detect_single_intent(self, query: str) -> MultiIntentResult:
        """检测单一意图"""
        from .intent_classifier import IntentClassifier

        classifier = IntentClassifier()
        result = classifier.classify(query)

        return MultiIntentResult(
            primary_intent=result.intent,
            all_intents=[IntentCandidate(
                intent=result.intent,
                confidence=result.confidence,
                position=(0, len(query)),
                trigger_keyword=""
            )],
            confidence=result.confidence,
            reasoning=result.reasoning,
            is_compound=False
        )

    def _build_multi_intent_result(
        self,
        candidates: List[IntentCandidate],
        query: str
    ) -> MultiIntentResult:
        """构建多意图结果"""
        # 按置信度和位置排序
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (
                c.confidence + self.INTENT_POSITION_BIAS.get(c.intent, 0),
                -(c.position[0] / len(query))  # 靠前的权重更高
            ),
            reverse=True
        )

        # 主意图是第一个
        primary = sorted_candidates[0]
        secondary = sorted_candidates[1:]

        # 计算整体置信度
        if len(candidates) == 1:
            confidence = primary.confidence
        else:
            # 多意图时降低置信度
            confidence = primary.confidence * 0.8 + sum(
                c.confidence * 0.2 for c in secondary
            ) / len(secondary)

        # 判断是否是复合意图
        is_compound = len(candidates) > 1 and any(
            c.position[0] > 0 for c in secondary
        )

        # 生成推理说明
        reasoning = self._generate_reasoning(candidates, is_compound)

        return MultiIntentResult(
            primary_intent=primary.intent,
            secondary_intents=[c.intent for c in secondary],
            all_intents=candidates,
            confidence=confidence,
            reasoning=reasoning,
            is_compound=is_compound
        )

    def _generate_reasoning(
        self,
        candidates: List[IntentCandidate],
        is_compound: bool
    ) -> str:
        """生成推理说明"""
        parts = []
        for c in candidates:
            parts.append(f"{c.intent.value}({c.confidence:.2f})")

        if is_compound:
            return f"复合意图检测: {' + '.join(parts)}"
        else:
            return f"单一意图: {parts[0] if parts else 'unknown'}"


def detect_multi_intent(query: str) -> MultiIntentResult:
    """便捷函数：多意图检测"""
    detector = MultiIntentDetector()
    return detector.detect(query)