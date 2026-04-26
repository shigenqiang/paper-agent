"""
Figure Classifier 单元测试

测试图表分类功能
"""
import pytest

from src.agents_v2.multimodal.figure_classifier import (
    FigureClassifier,
    FigureType,
    FigureClassification,
    ChartDataPoint,
    classify_figure
)


class TestFigureClassifier:
    """FigureClassifier 测试"""

    def setup_method(self):
        self.classifier = FigureClassifier()

    def test_initialization(self):
        """测试初始化"""
        assert self.classifier is not None
        assert self.classifier.model_path is None

    @pytest.mark.asyncio
    async def test_classify_returns_result(self):
        """测试分类返回结果"""
        result = await self.classifier.classify("mock_image")

        assert isinstance(result, FigureClassification)
        assert isinstance(result.figure_type, FigureType)

    @pytest.mark.asyncio
    async def test_detect_type(self):
        """测试类型检测"""
        result = await self.classifier._detect_type("mock_image")

        assert isinstance(result, FigureType)

    @pytest.mark.asyncio
    async def test_describe(self):
        """测试描述生成"""
        result = await self.classifier._describe("mock_image", FigureType.LINE_CHART)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_calculate_match_score(self):
        """测试匹配分数计算"""
        score = self.classifier._calculate_match_score(
            ["line", "axis", "chart"],
            ["line", "bar", "axis"]
        )

        assert 0.0 <= score <= 1.0

    def test_calculate_match_score_empty(self):
        """测试空特征"""
        score = self.classifier._calculate_match_score([], ["line"])
        assert score == 0.0


class TestFigureType:
    """FigureType 测试"""

    def test_figure_types_exist(self):
        """测试图表类型存在"""
        assert FigureType.LINE_CHART.value == "line_chart"
        assert FigureType.BAR_CHART.value == "bar_chart"
        assert FigureType.FLOWCHART.value == "flowchart"

    def test_figure_type_count(self):
        """测试图表类型数量"""
        assert len(FigureType) >= 10


class TestFigureClassification:
    """FigureClassification 测试"""

    def test_create_classification(self):
        """测试创建分类结果"""
        result = FigureClassification(
            figure_type=FigureType.LINE_CHART,
            confidence=0.9
        )

        assert result.figure_type == FigureType.LINE_CHART
        assert result.confidence == 0.9


class TestConvenienceFunction:
    """便捷函数测试"""

    @pytest.mark.asyncio
    async def test_classify_figure(self):
        """测试便捷分类函数"""
        result = await classify_figure("mock_image")

        assert isinstance(result, FigureClassification)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])