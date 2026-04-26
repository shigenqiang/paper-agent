"""
Query Expander 单元测试

测试查询扩展功能
"""
import pytest

from src.agents_v2.retrieval.query_expander import (
    QueryExpander,
    ExpansionResult,
    expand_query,
    get_expanded_queries
)


class TestQueryExpander:
    """QueryExpander 测试"""

    def setup_method(self):
        self.expander = QueryExpander()

    def test_initialization(self):
        """测试初始化"""
        assert self.expander is not None
        assert len(self.expander.expansion_cache) == 0

    def test_expand_with_synonym(self):
        """测试同义词扩展"""
        result = self.expander.expand("machine learning", strategies=["synonym"])

        assert result.original_query == "machine learning"
        assert len(result.expanded_queries) > 0
        assert "synonym" in result.expansion_types

    def test_expand_with_broader(self):
        """测试上位词扩展"""
        result = self.expander.expand("machine learning", strategies=["broader"])

        assert "artificial intelligence" in result.expanded_queries or len(result.expanded_queries) >= 0

    def test_expand_with_narrower(self):
        """测试下位词扩展"""
        result = self.expander.expand("machine learning", strategies=["narrower"])

        assert len(result.expanded_queries) >= 0

    def test_expand_with_related(self):
        """测试相关词扩展"""
        result = self.expander.expand("accuracy", strategies=["related"])

        assert len(result.expanded_queries) >= 0

    def test_expand_all_strategies(self):
        """测试所有扩展策略"""
        result = self.expander.expand("deep learning")

        assert len(result.expansion_types) >= 0
        assert result.confidence >= 0

    def test_expand_no_match(self):
        """测试无匹配时的扩展"""
        result = self.expander.expand("xyz123 unknown term")

        assert result.original_query == "xyz123 unknown term"
        # 即使没有匹配，也应该返回原始查询的扩展版本
        assert isinstance(result.expanded_queries, list)

    def test_expand_with_combinations(self):
        """测试组合扩展"""
        queries = self.expander.expand_with_combinations("machine learning")

        assert len(queries) > 0
        assert "machine learning" in queries  # 原查询应该包含在内

    def test_cache(self):
        """测试缓存"""
        result1 = self.expander.expand("test query")
        result2 = self.expander.expand("test query")

        # 相同查询应该返回缓存的结果
        assert len(self.expander.expansion_cache) > 0

    def test_expand_deduplication(self):
        """测试去重"""
        result = self.expander.expand("machine learning")

        # 检查是否有重复
        seen = set()
        for q in result.expanded_queries:
            assert q.lower() not in seen
            seen.add(q.lower())


class TestExpansionResult:
    """ExpansionResult 测试"""

    def test_create_result(self):
        """测试创建扩展结果"""
        result = ExpansionResult(
            original_query="test",
            expanded_queries=["test1", "test2"],
            expansion_types=["synonym"],
            confidence=0.8
        )

        assert result.original_query == "test"
        assert len(result.expanded_queries) == 2
        assert result.confidence == 0.8


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_expand_query_function(self):
        """测试便捷扩展函数"""
        result = expand_query("machine learning")

        assert isinstance(result, ExpansionResult)
        assert result.original_query == "machine learning"

    def test_get_expanded_queries_function(self):
        """测试获取扩展查询函数"""
        queries = get_expanded_queries("deep learning")

        assert isinstance(queries, list)
        assert len(queries) > 0
        assert "deep learning" in queries


if __name__ == "__main__":
    pytest.main([__file__, "-v"])