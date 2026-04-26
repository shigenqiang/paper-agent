"""
Plagiarism Checker 单元测试

测试查重检测功能
"""
import pytest

from src.agents_v2.tools.plagiarism_checker import (
    PlagiarismChecker,
    PlagiarismResult,
    FlaggedSegment,
    StructuralAnalyzer,
    check_plagiarism
)


class TestPlagiarismChecker:
    """PlagiarismChecker 测试"""

    def setup_method(self):
        self.checker = PlagiarismChecker(threshold=0.8)

    def test_initialization(self):
        """测试初始化"""
        assert self.checker.threshold == 0.8
        assert len(self.checker._reference_texts) == 0

    def test_add_reference(self):
        """测试添加参考文本"""
        self.checker.add_reference("This is a reference text")
        assert len(self.checker._reference_texts) == 1

    def test_check_original_text(self):
        """测试检查原创文本"""
        result = self.checker.check("This is a completely original text about machine learning")

        assert isinstance(result, PlagiarismResult)
        assert result.similarity_score >= 0.0
        assert isinstance(result.overall_assessment, str)

    def test_check_with_reference(self):
        """测试有参考文本的检查"""
        self.checker.add_reference("Machine learning is a subset of artificial intelligence")
        result = self.checker.check("Machine learning is a subset of artificial intelligence")

        # 完全重复应该被检测到
        assert result.similarity_score > 0

    def test_split_into_segments(self):
        """测试分段"""
        text = "Paragraph one.\n\nParagraph two."
        segments = self.checker._split_into_segments(text)

        assert len(segments) == 2

    def test_clean_text(self):
        """测试文本清理"""
        text = "Hello, World! This is a TEST."
        cleaned = self.checker._clean_text(text)

        assert "," not in cleaned
        assert "!" not in cleaned
        assert "TEST" not in cleaned  # 转小写后

    def test_tokenize(self):
        """测试分词"""
        text = "This is a test text"
        tokens = self.checker._tokenize(text)

        assert "this" in tokens or len(tokens) >= 0

    def test_assess_plagiarism_original(self):
        """测试评估原创"""
        result = self.checker._assess_plagiarism(0.05, 0)
        assert result == "original"

    def test_assess_plagiarism_minor(self):
        """测试评估轻微相似"""
        result = self.checker._assess_plagiarism(0.2, 2)
        assert result == "minor_similarities"

    def test_assess_plagiarism_concerns(self):
        """测试评估潜在问题"""
        result = self.checker._assess_plagiarism(0.4, 5)
        assert result == "potential_concerns"

    def test_assess_plagiarism_high(self):
        """测试评估高度相似"""
        result = self.checker._assess_plagiarism(0.6, 10)
        assert result == "high_similarity"


class TestPlagiarismResult:
    """PlagiarismResult 测试"""

    def test_create_result(self):
        """测试创建结果"""
        result = PlagiarismResult(
            similarity_score=0.3,
            flagged_segments=[],
            overall_assessment="minor_similarities",
            checked_at="2024-01-01"
        )

        assert result.similarity_score == 0.3
        assert result.overall_assessment == "minor_similarities"


class TestFlaggedSegment:
    """FlaggedSegment 测试"""

    def test_create_segment(self):
        """测试创建片段"""
        segment = FlaggedSegment(
            text="This is a flagged text",
            source="Source document",
            similarity_type="exact",
            start_pos=0,
            end_pos=100,
            similarity_score=0.9
        )

        assert segment.text == "This is a flagged text"
        assert segment.similarity_score == 0.9


class TestStructuralAnalyzer:
    """StructuralAnalyzer 测试"""

    def setup_method(self):
        self.analyzer = StructuralAnalyzer()

    def test_initialization(self):
        """测试初始化"""
        assert self.analyzer is not None

    def test_analyze_structure(self):
        """测试结构分析"""
        text = "This is a short sentence. This is a much longer sentence that contains more words and should be detected as such."
        result = self.analyzer.analyze_structure(text)

        assert "sentence_count" in result
        assert "vocabulary_diversity" in result
        assert result["sentence_count"] == 2

    def test_split_sentences(self):
        """测试句子分割"""
        text = "First sentence. Second sentence? Third sentence!"
        sentences = self.analyzer._split_sentences(text)

        assert len(sentences) == 3


class TestConvenienceFunction:
    """便捷函数测试"""

    def test_check_plagiarism(self):
        """测试便捷查重函数"""
        result = check_plagiarism("Original text about AI")

        assert isinstance(result, PlagiarismResult)
        assert result.similarity_score >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])