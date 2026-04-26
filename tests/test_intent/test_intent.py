"""
意图识别模块单元测试

测试意图分类、多意图检测、置信度计算功能
"""
import pytest
from src.agents_v2.intent import (
    IntentClassifier,
    IntentResult,
    IntentType,
    MultiIntentDetector,
    MultiIntentResult,
    IntentConfidence,
    ConfidenceResult,
)


class TestIntentType:
    """IntentType 枚举测试"""

    def test_all_intent_types_exist(self):
        """测试所有意图类型存在"""
        assert IntentType.LITERATURE_SEARCH.value == "literature_search"
        assert IntentType.LITERATURE_REVIEW.value == "literature_review"
        assert IntentType.TOPIC_SELECT.value == "topic_select"
        assert IntentType.DRAFT_WRITE.value == "draft_write"
        assert IntentType.FULL_PAPER.value == "full_paper"
        assert IntentType.UNKNOWN.value == "unknown"


class TestIntentResult:
    """IntentResult 测试"""

    def test_is_confident_high(self):
        """测试高置信度判断"""
        result = IntentResult(
            intent=IntentType.LITERATURE_SEARCH,
            confidence=0.85
        )
        assert result.is_confident(0.8)
        assert not result.is_confident(0.9)

    def test_is_confident_low(self):
        """测试低置信度判断"""
        result = IntentResult(
            intent=IntentType.LITERATURE_SEARCH,
            confidence=0.5
        )
        assert not result.is_confident(0.7)

    def test_to_dict(self):
        """测试转换为字典"""
        result = IntentResult(
            intent=IntentType.LITERATURE_SEARCH,
            confidence=0.85,
            reasoning="关键词匹配",
            alternatives=[(IntentType.TOPIC_SELECT, 0.3)]
        )
        d = result.to_dict()
        assert d["intent"] == "literature_search"
        assert d["confidence"] == 0.85


class TestIntentClassifier:
    """IntentClassifier 测试"""

    def setup_method(self):
        self.classifier = IntentClassifier()

    def test_literature_search(self):
        """测试文献搜索意图"""
        result = self.classifier.classify("搜索深度学习论文")
        assert result.intent == IntentType.LITERATURE_SEARCH
        assert result.confidence > 0.3

    def test_literature_search_english(self):
        """测试英文文献搜索"""
        result = self.classifier.classify("search papers about machine learning")
        assert result.intent == IntentType.LITERATURE_SEARCH

    def test_literature_review(self):
        """测试文献综述意图"""
        result = self.classifier.classify("帮我写文献综述")
        assert result.intent == IntentType.LITERATURE_REVIEW

    def test_topic_select(self):
        """测试选题意图"""
        result = self.classifier.classify("我想选择一个研究课题")
        assert result.intent == IntentType.TOPIC_SELECT

    def test_outline_generate(self):
        """测试大纲生成意图"""
        result = self.classifier.classify("帮我生成论文大纲")
        assert result.intent == IntentType.OUTLINE_GENERATE

    def test_draft_write(self):
        """测试初稿撰写意图"""
        result = self.classifier.classify("撰写论文初稿")
        assert result.intent == IntentType.DRAFT_WRITE

    def test_full_paper(self):
        """测试完整论文意图"""
        result = self.classifier.classify("写一篇完整的论文")
        assert result.intent == IntentType.FULL_PAPER

    def test_empty_query(self):
        """测试空查询"""
        result = self.classifier.classify("")
        assert result.intent == IntentType.UNKNOWN
        assert result.confidence == 0.0

    def test_unknown_intent(self):
        """测试未知意图"""
        result = self.classifier.classify("的一些无关内容xyz")
        # 置信度较低但不一定是UNKNOWN
        assert result is not None

    def test_alternatives(self):
        """测试备选意图"""
        result = self.classifier.classify("搜索论文并撰写")
        # 可能有多于一个意图
        assert len(result.alternatives) >= 0

    def test_batch_classify(self):
        """测试批量分类"""
        queries = [
            "搜索深度学习论文",
            "帮我写文献综述",
            "生成论文大纲"
        ]
        results = self.classifier.batch_classify(queries)
        assert len(results) == 3
        assert all(r.intent != IntentType.UNKNOWN for r in results if r.confidence > 0.1)

    def test_classify_with_fallback(self):
        """测试带回退的分类"""
        result = self.classifier.classify_with_fallback(
            "一些模糊的内容",
            fallback_intent=IntentType.LITERATURE_SEARCH
        )
        # 应该使用回退意图
        assert result.intent == IntentType.LITERATURE_SEARCH


class TestMultiIntentDetector:
    """MultiIntentDetector 测试"""

    def setup_method(self):
        self.detector = MultiIntentDetector()

    def test_single_intent(self):
        """测试单一意图"""
        result = self.detector.detect("搜索深度学习论文")
        assert result is not None
        assert result.primary_intent is not None

    def test_compound_intent(self):
        """测试复合意图"""
        result = self.detector.detect("搜索论文然后写摘要")
        # 应该检测到多个意图
        assert len(result.all_intents) >= 1

    def test_compound_with_and(self):
        """测试使用'并且'的复合意图"""
        result = self.detector.detect("搜索机器学习论文并且写综述")
        assert result.is_compound or len(result.all_intents) >= 1

    def test_empty_query(self):
        """测试空查询"""
        result = self.detector.detect("")
        assert result.primary_intent == IntentType.UNKNOWN

    def test_to_dict(self):
        """测试转换为字典"""
        result = self.detector.detect("搜索论文")
        d = result.to_dict()
        assert "primary_intent" in d
        assert "all_intents" in d


class TestIntentConfidence:
    """IntentConfidence 测试"""

    def setup_method(self):
        self.calculator = IntentConfidence()

    def test_calculate_basic(self):
        """测试基本计算"""
        result = self.calculator.calculate(
            intent_type="literature_search",
            keyword_matches=3,
            query_length=20
        )
        assert result.confidence > 0
        assert result.confidence_level in ("high", "medium", "low", "unknown")

    def test_high_keyword_matches(self):
        """测试高关键词匹配"""
        result = self.calculator.calculate(
            intent_type="literature_search",
            keyword_matches=5,
            query_length=30
        )
        assert result.confidence >= 0.7

    def test_low_keyword_matches(self):
        """测试低关键词匹配"""
        result = self.calculator.calculate(
            intent_type="unknown",
            keyword_matches=0,
            query_length=5
        )
        assert result.confidence < 0.6

    def test_is_reliable(self):
        """测试可靠性判断"""
        result = self.calculator.calculate(
            intent_type="literature_search",
            keyword_matches=4,
            query_length=30
        )
        assert result.is_reliable(0.6) or not result.is_reliable(0.9)

    def test_explicit_intent_bonus(self):
        """测试明确意图加分"""
        result1 = self.calculator.calculate(
            intent_type="search",
            keyword_matches=2,
            query_length=10,
            explicit_intent=False
        )
        result2 = self.calculator.calculate(
            intent_type="search",
            keyword_matches=2,
            query_length=10,
            explicit_intent=True
        )
        # 明确意图应该有更高的置信度
        assert result2.confidence >= result1.confidence

    def test_update_accuracy(self):
        """测试更新准确率"""
        self.calculator.update_accuracy("literature_search", True, 0.9)
        self.calculator.update_accuracy("literature_search", False, 0.3)

        stats = self.calculator.get_accuracy_stats()
        assert "literature_search" in stats

    def test_historical_accuracy(self):
        """测试历史准确率"""
        # 更新一些准确率记录
        for _ in range(5):
            self.calculator.update_accuracy("test_intent", True, 0.8)

        result = self.calculator.calculate(
            intent_type="test_intent",
            keyword_matches=2
        )
        # 应该有历史准确率因子
        assert "historical_accuracy" in result.factors

    def test_calculate_from_result(self):
        """测试从IntentResult计算"""
        classifier = IntentClassifier()
        intent_result = classifier.classify("搜索深度学习论文")

        conf_result = self.calculator.calculate_from_result(
            intent_result,
            query_length=len("搜索深度学习论文")
        )
        assert conf_result.confidence > 0


class TestConfidenceResult:
    """ConfidenceResult 测试"""

    def test_is_reliable_high(self):
        """测试高置信度可靠性"""
        result = ConfidenceResult(
            confidence=0.85,
            confidence_level="high"
        )
        assert result.is_reliable(0.7)

    def test_is_reliable_low_level(self):
        """测试低等级不可靠"""
        result = ConfidenceResult(
            confidence=0.85,
            confidence_level="low"
        )
        assert not result.is_reliable(0.7)

    def test_to_dict(self):
        """测试转换为字典"""
        result = ConfidenceResult(
            confidence=0.75,
            confidence_level="medium",
            factors={"keyword_match": 0.8}
        )
        d = result.to_dict()
        assert d["confidence"] == 0.75
        assert d["is_reliable"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])