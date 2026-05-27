"""
Intent Confidence - 意图置信度计算器

提供意图识别的置信度评估和校准功能。
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math


@dataclass
class ConfidenceResult:
    """置信度评估结果"""
    confidence: float
    confidence_level: str  # high, medium, low, unknown
    factors: Dict[str, float] = field(default_factory=dict)
    calibration_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_reliable(self, threshold: float = 0.7) -> bool:
        return self.confidence >= threshold and self.confidence_level in ("high", "medium")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence": self.confidence,
            "confidence_level": self.confidence_level,
            "factors": self.factors,
            "calibration_score": self.calibration_score,
            "is_reliable": self.is_reliable(),
            "metadata": self.metadata
        }


class IntentConfidence:
    """
    意图置信度计算器

    提供:
    - 多维度置信度计算
    - 置信度校准
    - 历史准确率反馈

    使用示例:
        calculator = IntentConfidence()

        result = calculator.calculate(
            intent_type=IntentType.LITERATURE_SEARCH,
            keyword_matches=3,
            query_length=20,
            context_diversity=0.5
        )
        print(f"置信度: {result.confidence}")
        print(f"等级: {result.confidence_level}")
    """

    # 置信度等级阈值
    CONFIDENCE_THRESHOLDS = {
        "high": 0.8,
        "medium": 0.5,
        "low": 0.3,
    }

    # 各因素权重
    FACTOR_WEIGHTS = {
        "keyword_match": 0.35,
        "query_clarity": 0.20,
        "context_specificity": 0.20,
        "historical_accuracy": 0.15,
        "length_score": 0.10,
    }

    # 关键词匹配分数映射
    KEYWORD_MATCH_SCORES = {
        0: 0.0,
        1: 0.3,
        2: 0.6,
        3: 0.8,
        4: 0.9,
        5: 1.0,
    }

    # 查询长度评分
    LENGTH_SCORES = {
        (0, 5): 0.3,    # 非常短
        (6, 15): 0.6,   # 较短
        (16, 50): 1.0,  # 适中
        (51, 100): 0.8, # 较长
        (101, float('inf')): 0.5,  # 过长
    }

    def __init__(self, enable_calibration: bool = False):
        """
        初始化置信度计算器

        Args:
            enable_calibration: 是否启用校准
        """
        self.enable_calibration = enable_calibration
        self._historical_accuracies: Dict[str, List[float]] = {}

    def calculate(
        self,
        intent_type: str,
        keyword_matches: int = 0,
        query_length: int = 0,
        context_diversity: float = 0.5,
        historical_accuracy: Optional[float] = None,
        explicit_intent: bool = False,
        has_clarifiers: bool = False,
        **kwargs
    ) -> ConfidenceResult:
        """
        计算置信度

        Args:
            intent_type: 意图类型
            keyword_matches: 关键词匹配数量
            query_length: 查询长度
            context_diversity: 上下文多样性 (0-1)
            historical_accuracy: 历史准确率 (0-1)
            explicit_intent: 是否有明确意图表达
            has_clarifiers: 是否有澄清词（如"帮我"、"请"）
            **kwargs: 其他参数

        Returns:
            ConfidenceResult: 置信度结果
        """
        # 1. 计算各因素得分
        factors = {
            "keyword_match": self._calc_keyword_score(keyword_matches),
            "query_clarity": self._calc_clarity_score(
                query_length, explicit_intent, has_clarifiers
            ),
            "context_specificity": context_diversity,
            "historical_accuracy": historical_accuracy or self._get_historical_accuracy(intent_type),
            "length_score": self._calc_length_score(query_length),
        }

        # 2. 加权计算总体置信度
        total_confidence = sum(
            factors.get(key, 0) * self.FACTOR_WEIGHTS.get(key, 0)
            for key in self.FACTOR_WEIGHTS
        )

        # 3. 确定置信度等级
        confidence_level = self._get_confidence_level(total_confidence)

        # 4. 校准（如果启用）
        calibration_score = 1.0
        if self.enable_calibration and historical_accuracy is not None:
            calibration_score = self._calibrate(total_confidence, historical_accuracy)
            total_confidence = (total_confidence + calibration_score) / 2

        return ConfidenceResult(
            confidence=min(1.0, max(0.0, total_confidence)),
            confidence_level=confidence_level,
            factors=factors,
            calibration_score=calibration_score,
            metadata={
                "intent_type": intent_type,
                "raw_score": total_confidence,
                **kwargs
            }
        )

    def _calc_keyword_score(self, matches: int) -> float:
        """计算关键词匹配得分"""
        if matches >= 5:
            return 1.0
        return self.KEYWORD_MATCH_SCORES.get(matches, 0.3)

    def _calc_clarity_score(
        self,
        query_length: int,
        explicit_intent: bool,
        has_clarifiers: bool
    ) -> float:
        """计算清晰度得分"""
        base = 0.5

        # 有明确的意图表达
        if explicit_intent:
            base += 0.3

        # 有澄清词
        if has_clarifiers:
            base += 0.1

        # 查询长度适中
        if 10 <= query_length <= 100:
            base += 0.1

        return min(1.0, base)

    def _calc_length_score(self, length: int) -> float:
        """计算长度得分"""
        for (min_len, max_len), score in self.LENGTH_SCORES.items():
            if min_len <= length <= max_len:
                return score
        return 0.3

    def _get_confidence_level(self, confidence: float) -> str:
        """获取置信度等级"""
        if confidence >= self.CONFIDENCE_THRESHOLDS["high"]:
            return "high"
        elif confidence >= self.CONFIDENCE_THRESHOLDS["medium"]:
            return "medium"
        elif confidence >= self.CONFIDENCE_THRESHOLDS["low"]:
            return "low"
        else:
            return "unknown"

    def _get_historical_accuracy(self, intent_type: str) -> float:
        """获取历史准确率"""
        if intent_type not in self._historical_accuracies:
            return 0.7  # 默认值

        accuracies = self._historical_accuracies[intent_type]
        if not accuracies:
            return 0.7

        # 返回最近10次的平均
        recent = accuracies[-10:]
        return sum(recent) / len(recent)

    def _calibrate(self, confidence: float, observed_accuracy: float) -> float:
        """校准置信度"""
        # 简单的线性校准
        if observed_accuracy < 0.5:
            # 低准确率，降低置信度
            return confidence * 0.9
        else:
            return (confidence + observed_accuracy) / 2

    def update_accuracy(
        self,
        intent_type: str,
        correct: bool,
        predicted_confidence: float
    ):
        """更新准确率记录"""
        if intent_type not in self._historical_accuracies:
            self._historical_accuracies[intent_type] = []

        accuracy = 1.0 if correct else 0.0
        self._historical_accuracies[intent_type].append(accuracy)

        # 只保留最近50条记录
        if len(self._historical_accuracies[intent_type]) > 50:
            self._historical_accuracies[intent_type].pop(0)

    def get_accuracy_stats(self) -> Dict[str, Dict[str, float]]:
        """获取准确率统计"""
        stats = {}
        for intent_type, accuracies in self._historical_accuracies.items():
            if accuracies:
                stats[intent_type] = {
                    "count": len(accuracies),
                    "average": sum(accuracies) / len(accuracies),
                    "recent_10": sum(accuracies[-10:]) / min(10, len(accuracies))
                    if len(accuracies) >= 1 else 0.0
                }
        return stats

    def calculate_from_result(
        self,
        intent_result: Any,
        query_length: int = 0,
        **kwargs
    ) -> ConfidenceResult:
        """
        从IntentResult计算置信度

        Args:
            intent_result: IntentResult对象
            query_length: 查询长度

        Returns:
            ConfidenceResult: 置信度结果
        """
        return self.calculate(
            intent_type=intent_result.intent.value if hasattr(intent_result.intent, 'value') else str(intent_result.intent),
            keyword_matches=len(intent_result.alternatives) + 1 if intent_result.alternatives else 1,
            query_length=query_length,
            context_diversity=kwargs.get("context_diversity", 0.5),
            explicit_intent=kwargs.get("explicit_intent", True),
            has_clarifiers=kwargs.get("has_clarifiers", False)
        )


def calculate_confidence(**kwargs) -> ConfidenceResult:
    """便捷函数：计算置信度"""
    calculator = IntentConfidence()
    return calculator.calculate(**kwargs)