"""
Query Rewriter 单元测试

测试查询改写功能
"""
import pytest

from src.agents_v2.retrieval.query_rewriter import (
    QueryRewriter,
    RewriteResult,
    rewrite_query
)


class TestQueryRewriter:
    """QueryRewriter 测试"""

    def setup_method(self):
        self.rewriter = QueryRewriter()

    def test_initialization(self):
        """测试初始化"""
        assert self.rewriter is not None
        assert self.rewriter.llm is None

    def test_decide_rewrite_type_short_query(self):
        """测试短查询决策"""
        rewrite_type = self.rewriter._decide_rewrite_type("AI", {})
        assert rewrite_type == "expansion"

    def test_decide_rewrite_type_complex_query(self):
        """测试复杂查询决策"""
        rewrite_type = self.rewriter._decide_rewrite_type("深度学习和机器学习的关系和应用", {})
        assert rewrite_type == "decomposition"

    def test_decide_rewrite_type_with_irrelevant_docs(self):
        """测试有无关文档时的决策"""
        context = {"irrelevant_docs": ["doc1", "doc2", "doc3"]}
        rewrite_type = self.rewriter._decide_rewrite_type("机器学习", context)
        assert rewrite_type == "expansion"

    def test_expand_query(self):
        """测试扩展查询"""
        result = self.rewriter._expand_query("ML")

        assert result.rewrite_type == "expansion"
        # 扩展后应该包含更多内容
        assert len(result.rewritten_query) >= len("ML")

    def test_restrict_query(self):
        """测试限制查询"""
        result = self.rewriter._restrict_query("机器学习", {})

        assert result.rewrite_type == "restriction"
        assert "机器学习" in result.rewritten_query

    def test_reformulate_query(self):
        """测试重新表述查询"""
        result = self.rewriter._reformulate_query("我想了解机器学习是什么")

        assert result.rewrite_type == "reformulation"
        assert "我想了解" not in result.rewritten_query

    def test_decompose_query(self):
        """测试分解查询"""
        result = self.rewriter._decompose_query("机器学习和深度学习")

        assert result.rewrite_type == "decomposition"
        assert len(result.reasons) > 0

    def test_decompose_query_cannot_split(self):
        """测试无法分解的查询"""
        result = self.rewriter._decompose_query("机器学习")

        assert result.rewrite_type == "decomposition"
        assert "无法分解" in result.reasons[0]

    def test_get_all_sub_queries(self):
        """测试获取所有子查询"""
        sub_queries = self.rewriter.get_all_sub_queries("机器学习,深度学习,神经网络")

        assert len(sub_queries) == 3
        assert "机器学习" in sub_queries

    def test_get_all_sub_queries_with_comma(self):
        """测试逗号分割"""
        sub_queries = self.rewriter.get_all_sub_queries("AI, ML, DL")

        assert len(sub_queries) == 3


class TestRewriteResult:
    """RewriteResult 测试"""

    def test_create_result(self):
        """测试创建改写结果"""
        result = RewriteResult(
            original_query="old",
            rewritten_query="new",
            rewrite_type="expansion",
            confidence=0.8,
            reasons=["added synonyms"]
        )

        assert result.original_query == "old"
        assert result.rewritten_query == "new"
        assert result.confidence == 0.8


class TestConvenienceFunction:
    """便捷函数测试"""

    def test_rewrite_query(self):
        """测试便捷改写函数"""
        result = rewrite_query("机器学习")

        assert isinstance(result, RewriteResult)
        assert result.original_query == "机器学习"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])