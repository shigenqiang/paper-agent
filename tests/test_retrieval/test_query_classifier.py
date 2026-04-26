"""
QueryTypeClassifier 单元测试

测试独立的小模块:
1. classify() - 核心分类功能
2. _contains_any() - 关键词匹配
3. get_confidence() - 置信度
"""
import pytest
from src.agents_v2.retrieval.query_classifier import (
    QueryTypeClassifier,
    QueryType,
    classify_query,
    REASONING_KEYWORDS,
    COMPARISON_KEYWORDS,
    DEFINITION_KEYWORDS,
    FACT_KEYWORDS,
    EXPLORATION_KEYWORDS
)


class TestQueryTypeClassifier:
    """QueryTypeClassifier 测试"""

    def setup_method(self):
        """设置测试"""
        self.classifier = QueryTypeClassifier()

    # ===== 基础功能测试 =====

    def test_classifier_init(self):
        """测试分类器初始化"""
        assert self.classifier is not None
        assert len(self.classifier.reasoning_keywords) > 0

    def test_classify_returns_query_type(self):
        """测试分类返回正确的类型"""
        result = self.classifier.classify("测试查询")
        assert isinstance(result, QueryType)

    # ===== 复杂推理测试 =====

    @pytest.mark.parametrize("query", [
        "为什么深度学习效果好？",
        "Reasoning is important",
        "分析Transformer的注意力机制",
        "为什么是Transformer而不是RNN？",
        "prove the convergence",
        "推导这个公式",
        "分析原因",
    ])
    def test_classify_reasoning(self, query):
        """测试复杂推理类查询"""
        result = self.classifier.classify(query)
        assert result == QueryType.COMPLEX_REASONING, f"Failed for: {query}"

    # ===== 比较类测试 =====

    @pytest.mark.parametrize("query", [
        "BERT和GPT有什么区别？",
        "compare Python and Java",
        "哪个更好？",
        "有什么不同",
        "差异点是什么",
        "vs",  # single keyword
        "CNN vs RNN",
    ])
    def test_classify_comparison(self, query):
        """测试比较类查询"""
        result = self.classifier.classify(query)
        assert result == QueryType.COMPARISON, f"Failed for: {query}"

    # ===== 定义类测试 =====

    @pytest.mark.parametrize("query", [
        "什么是机器学习？",
        "What is a neural network?",
        "大语言模型的定义",
        "什么叫过拟合",
        "Self-attention是指什么",
    ])
    def test_classify_definition(self, query):
        """测试定义类查询"""
        result = self.classifier.classify(query)
        assert result == QueryType.DEFINITION, f"Failed for: {query}"

    # ===== 事实查找测试 =====

    @pytest.mark.parametrize("query", [
        "Transformer是谁发明的？",
        "这篇文章发表于哪一年？",
        "How many layers",
        "Who invented it",
        "哪个公司开发了",
        "多少参数",
    ])
    def test_classify_fact_lookup(self, query):
        """测试事实查找类查询"""
        result = self.classifier.classify(query)
        assert result == QueryType.FACT_LOOKUP, f"Failed for: {query}"

    # ===== 探索类测试 =====

    @pytest.mark.parametrize("query", [
        "了解最新的AI研究方向",
        "Explore the latest trends",
        "深度学习研究进展",
        "人工智能领域的发展",
        "Recent developments in NLP",
    ])
    def test_classify_exploration(self, query):
        """测试探索类查询"""
        result = self.classifier.classify(query)
        assert result == QueryType.EXPLORATION, f"Failed for: {query}"

    # ===== 启发式规则测试 =====

    def test_long_query_is_exploration(self):
        """测试长查询默认为探索类"""
        result = self.classifier.classify("这是一个非常长的查询句子用来测试启发式规则是否正常工作")
        assert result == QueryType.EXPLORATION

    def test_short_query_is_fact(self):
        """测试短查询默认为事实查找"""
        result = self.classifier.classify("AI是什么")
        assert result == QueryType.FACT_LOOKUP

    def test_empty_query(self):
        """测试空查询"""
        result = self.classifier.classify("")
        assert result == QueryType.FACT_LOOKUP

    def test_very_short_query(self):
        """测试非常短的查询"""
        result = self.classifier.classify("AI")
        assert result == QueryType.FACT_LOOKUP

    # ===== 优先级测试 =====

    def test_reasoning_over_comparison(self):
        """测试推理关键词优先于比较关键词"""
        # "为什么" should be classified as reasoning even if contains "比较"
        query = "为什么比较这两种方法？"
        result = self.classifier.classify(query)
        assert result == QueryType.COMPLEX_REASONING

    def test_definition_over_fact(self):
        """测试定义关键词优先于事实关键词"""
        # "什么是" should be classified as definition even if contains "谁"
        query = "什么是Transformer？它是谁提出的？"
        result = self.classifier.classify(query)
        assert result == QueryType.DEFINITION

    # ===== 置信度测试 =====

    def test_confidence_single_keyword(self):
        """测试单个关键词的置信度"""
        query = "什么是AI"
        confidence = self.classifier.get_confidence(query)
        assert 0 < confidence <= 1.0

    def test_confidence_multiple_keywords(self):
        """测试多个关键词的置信度"""
        query = "分析原因并证明这个理论"
        confidence = self.classifier.get_confidence(query)
        assert confidence > 0.5

    def test_confidence_no_keywords(self):
        """测试无关键词时的置信度"""
        query = "一些随机的词"
        confidence = self.classifier.get_confidence(query)
        # Short query classified as FACT_LOOKUP via heuristic gives 0.6
        assert confidence == 0.6

    # ===== 便捷函数测试 =====

    def test_convenience_function(self):
        """测试便捷函数"""
        result = classify_query("什么是机器学习")
        assert result == QueryType.DEFINITION


class TestKeywordSets:
    """关键词集合完整性测试"""

    def test_all_keyword_sets_nonempty(self):
        """测试所有关键词集合非空"""
        assert len(REASONING_KEYWORDS) > 0
        assert len(COMPARISON_KEYWORDS) > 0
        assert len(DEFINITION_KEYWORDS) > 0
        assert len(FACT_KEYWORDS) > 0
        assert len(EXPLORATION_KEYWORDS) > 0

    def test_keyword_sets_are_lowercase(self):
        """测试英文关键词都是小写"""
        for kw in REASONING_KEYWORDS:
            if kw.isalpha():
                assert kw == kw.lower(), f"Keyword {kw} not lowercase"
        for kw in COMPARISON_KEYWORDS:
            if kw.isalpha():
                assert kw == kw.lower(), f"Keyword {kw} not lowercase"
        for kw in DEFINITION_KEYWORDS:
            if kw.isalpha():
                assert kw == kw.lower(), f"Keyword {kw} not lowercase"
        for kw in FACT_KEYWORDS:
            if kw.isalpha():
                assert kw == kw.lower(), f"Keyword {kw} not lowercase"
        for kw in EXPLORATION_KEYWORDS:
            if kw.isalpha():
                assert kw == kw.lower(), f"Keyword {kw} not lowercase"

    def test_keyword_sets_no_duplicates(self):
        """测试关键词集合无重复"""
        all_keywords = (
            list(REASONING_KEYWORDS) +
            list(COMPARISON_KEYWORDS) +
            list(DEFINITION_KEYWORDS) +
            list(FACT_KEYWORDS) +
            list(EXPLORATION_KEYWORDS)
        )
        assert len(all_keywords) == len(set(all_keywords)), "Duplicate keywords found"


class TestEdgeCases:
    """边界情况测试"""

    def setup_method(self):
        self.classifier = QueryTypeClassifier()

    def test_chinese_punctuation(self):
        """测试中文标点"""
        result = self.classifier.classify("什么是机器学习？")
        assert result == QueryType.DEFINITION

    def test_english_punctuation(self):
        """测试英文标点"""
        result = self.classifier.classify("What is machine learning?")
        assert result == QueryType.DEFINITION

    def test_mixed_language(self):
        """测试中英混合"""
        result = self.classifier.classify("Transformer's attention mechanism分析")
        assert result == QueryType.COMPLEX_REASONING

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        result1 = self.classifier.classify("WHAT IS AI")
        result2 = self.classifier.classify("what is ai")
        assert result1 == result2 == QueryType.DEFINITION

    def test_whitespace_handling(self):
        """测试空白字符处理"""
        result = self.classifier.classify("  什么是AI  ")
        assert result == QueryType.DEFINITION

    def test_unicode_special_chars(self):
        """测试Unicode特殊字符"""
        result = self.classifier.classify("什么是​机器学习")  # zero-width space
        assert result == QueryType.DEFINITION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])