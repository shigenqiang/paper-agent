"""
多模态模块测试

测试:
- VisionEncoder: CLIP视觉编码
- ChartAnalyzer: 图表分析
- FormulaRecognizer: 公式识别
- DiagramParser: 流程图解析
- MultimodalRetriever: 多模态检索
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch


class TestVisionEncoder:
    """VisionEncoder测试"""

    def test_init(self):
        """测试初始化"""
        from src.agents_v2.multimodal import VisionEncoder

        encoder = VisionEncoder()
        assert encoder is not None
        assert encoder.model_name == "openai/clip-vit-base-patch32"

    def test_encode_text_simple(self):
        """测试简单文本编码"""
        from src.agents_v2.multimodal import VisionEncoder

        encoder = VisionEncoder()
        result = encoder._encode_text_simple("测试文本")

        assert len(result) == 512
        assert all(0 <= v <= 1 for v in result)

    def test_encode_image_simple(self):
        """测试简单图像编码（无模型时）"""
        from src.agents_v2.multimodal import VisionEncoder
        from PIL import Image

        encoder = VisionEncoder()
        # 创建空白图像
        img = Image.new('RGB', (100, 100), color='white')

        result = encoder._encode_simple(img)

        assert len(result) == 512

    def test_cosine_similarity_in_multimodal(self):
        """测试MultimodalRetriever的余弦相似度"""
        from src.agents_v2.multimodal import MultimodalRetriever

        retriever = MultimodalRetriever()

        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        assert retriever._cosine_similarity(vec1, vec2) == pytest.approx(1.0)

        vec3 = [0.0, 1.0, 0.0]
        assert retriever._cosine_similarity(vec1, vec3) == pytest.approx(0.0)

        vec4 = [0.5, 0.5, 0.0]
        similarity = retriever._cosine_similarity(vec1, vec4)
        assert 0.5 < similarity < 1.0


class TestImageTextMatcher:
    """ImageTextMatcher测试"""

    def test_init(self):
        """测试初始化"""
        from src.agents_v2.multimodal import VisionEncoder, ImageTextMatcher

        encoder = VisionEncoder()
        matcher = ImageTextMatcher(vision_encoder=encoder)

        assert matcher.encoder is not None


class TestChartType:
    """ChartType枚举测试"""

    def test_chart_types(self):
        """测试图表类型枚举"""
        from src.agents_v2.multimodal import ChartType

        assert ChartType.LINE.value == "line"
        assert ChartType.BAR.value == "bar"
        assert ChartType.PIE.value == "pie"
        assert ChartType.SCATTER.value == "scatter"
        assert ChartType.HEATMAP.value == "heatmap"
        assert ChartType.UNKNOWN.value == "unknown"


class TestChartAnalyzer:
    """ChartAnalyzer测试"""

    def test_init(self):
        """测试初始化"""
        from src.agents_v2.multimodal import ChartAnalyzer

        analyzer = ChartAnalyzer()
        assert analyzer is not None

    def test_parse_chart_type(self):
        """测试图表类型解析"""
        from src.agents_v2.multimodal import ChartAnalyzer, ChartType

        analyzer = ChartAnalyzer()

        assert analyzer._parse_chart_type("line") == ChartType.LINE
        assert analyzer._parse_chart_type("折线") == ChartType.LINE
        assert analyzer._parse_chart_type("bar") == ChartType.BAR
        assert analyzer._parse_chart_type("柱状") == ChartType.BAR
        assert analyzer._parse_chart_type("pie") == ChartType.PIE
        assert analyzer._parse_chart_type("饼") == ChartType.PIE

    def test_extract_json(self):
        """测试JSON提取"""
        from src.agents_v2.multimodal import ChartAnalyzer

        analyzer = ChartAnalyzer()

        # 测试简单JSON
        text = '{"title": "测试", "value": 123}'
        result = analyzer._extract_json(text)
        assert result is not None
        assert result["title"] == "测试"

        # 测试带反引号的JSON
        text = '```json\n{"title": "测试"}\n```'
        result = analyzer._extract_json(text)
        assert result is not None
        assert result["title"] == "测试"

    @pytest.mark.asyncio
    async def test_analyze_line_chart_fallback(self):
        """测试折线图分析回退"""
        from src.agents_v2.multimodal import ChartAnalyzer, ChartType

        analyzer = ChartAnalyzer()
        result = await analyzer._analyze_line_chart(None)

        assert result.chart_type == ChartType.LINE
        assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_analyze_generic(self):
        """测试通用分析"""
        from src.agents_v2.multimodal import ChartAnalyzer, ChartType

        analyzer = ChartAnalyzer()
        result = await analyzer._analyze_generic(None)

        assert result.chart_type == ChartType.UNKNOWN
        assert result.confidence == 0.3


class TestFormulaRecognizer:
    """FormulaRecognizer测试"""

    def test_init(self):
        """测试初始化"""
        from src.agents_v2.multimodal import FormulaRecognizer

        recognizer = FormulaRecognizer()
        assert recognizer is not None

    def test_validate_latex(self):
        """测试LaTeX验证"""
        from src.agents_v2.multimodal import FormulaRecognizer

        recognizer = FormulaRecognizer()

        # 有效的分数公式
        assert recognizer.validate("\\frac{a}{b}") == True

        # 无效的括号不匹配
        assert recognizer.validate("\\frac{a}{b") == False

    def test_latex_to_plain_text(self):
        """测试LaTeX转纯文本"""
        from src.agents_v2.multimodal import FormulaRecognizer

        recognizer = FormulaRecognizer()

        result = recognizer._latex_to_plain_text("\\frac{a}{b}")
        assert "(" in result and ")" in result

    def test_simple_explanation(self):
        """测试简单解释"""
        from src.agents_v2.multimodal import FormulaRecognizer

        recognizer = FormulaRecognizer()

        assert "分数" in recognizer._simple_explanation("\\frac{a}{b}")
        assert "积分" in recognizer._simple_explanation("\\int_{a}^{b}")


class TestLaTeXRenderer:
    """LaTeXRenderer测试"""

    def test_init(self):
        """测试初始化"""
        from src.agents_v2.multimodal import LaTeXRenderer

        renderer = LaTeXRenderer()
        assert renderer.backend == "simple"

    def test_simple_render(self):
        """测试简单渲染"""
        from src.agents_v2.multimodal import LaTeXRenderer

        renderer = LaTeXRenderer()
        result = renderer._simple_render("x^2 + y^2")

        from PIL import Image
        assert isinstance(result, Image.Image)


class TestDiagramNode:
    """DiagramNode测试"""

    def test_init(self):
        """测试初始化"""
        from src.agents_v2.multimodal import DiagramNode

        node = DiagramNode(
            id="1",
            label="开始",
            node_type="start",
            position=(100, 200)
        )

        assert node.id == "1"
        assert node.label == "开始"
        assert node.node_type == "start"
        assert node.position == (100, 200)


class TestDiagramEdge:
    """DiagramEdge测试"""

    def test_init(self):
        """测试初始化"""
        from src.agents_v2.multimodal import DiagramEdge

        edge = DiagramEdge(
            source="1",
            target="2",
            label="下一步",
            edge_type="arrow"
        )

        assert edge.source == "1"
        assert edge.target == "2"
        assert edge.label == "下一步"
        assert edge.edge_type == "arrow"


class TestDiagramParser:
    """DiagramParser测试"""

    def test_init(self):
        """测试初始化"""
        from src.agents_v2.multimodal import DiagramParser

        parser = DiagramParser()
        assert parser is not None

    def test_simple_description_no_nodes(self):
        """测试空流程图描述"""
        from src.agents_v2.multimodal import DiagramParser

        parser = DiagramParser()
        result = parser._simple_description([], [])

        assert result == "空流程图"

    def test_simple_description_with_nodes(self):
        """测试流程图描述"""
        from src.agents_v2.multimodal import DiagramParser, DiagramNode, DiagramEdge

        parser = DiagramParser()

        nodes = [
            DiagramNode(id="1", label="开始", node_type="start"),
            DiagramNode(id="2", label="结束", node_type="end")
        ]
        edges = [DiagramEdge(source="1", target="2")]

        result = parser._simple_description(nodes, edges)

        assert "2个节点" in result
        assert "1条边" in result
        assert "开始" in result

    def test_build_graph_without_networkx(self):
        """测试无networkx构建图"""
        from src.agents_v2.multimodal import DiagramParser, DiagramNode, DiagramEdge

        parser = DiagramParser()
        parser._load_model = lambda: None  # 模拟无networkx

        nodes = [
            DiagramNode(id="1", label="A", node_type="process"),
            DiagramNode(id="2", label="B", node_type="process")
        ]
        edges = [DiagramEdge(source="1", target="2")]

        result = parser._build_graph(nodes, edges)

        assert result["node_count"] == 2
        assert result["edge_count"] == 1


class TestMultimodalRetrievalResult:
    """MultimodalRetrievalResult测试"""

    def test_init(self):
        """测试初始化"""
        from src.agents_v2.multimodal import MultimodalRetrievalResult

        result = MultimodalRetrievalResult(
            text_results=["doc1", "doc2"],
            combined_context="测试上下文"
        )

        assert len(result.text_results) == 2
        assert result.combined_context == "测试上下文"


class TestMultimodalRetriever:
    """MultimodalRetriever测试"""

    def test_init(self):
        """测试初始化"""
        from src.agents_v2.multimodal import MultimodalRetriever

        retriever = MultimodalRetriever()
        assert retriever is not None
        assert retriever.vision_encoder is not None
        assert retriever.chart_analyzer is not None
        assert retriever.formula_recognizer is not None
        assert retriever.diagram_parser is not None

    def test_cosine_similarity(self):
        """测试余弦相似度"""
        from src.agents_v2.multimodal import MultimodalRetriever

        retriever = MultimodalRetriever()

        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        assert retriever._cosine_similarity(vec1, vec2) == pytest.approx(1.0)

        vec3 = [0.0, 0.0, 1.0]
        assert retriever._cosine_similarity(vec1, vec3) == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_retrieve_with_mock_retriever(self):
        """测试带模拟检索器的检索"""
        from src.agents_v2.multimodal import MultimodalRetriever

        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=["doc1", "doc2"])

        retriever = MultimodalRetriever(text_retriever=mock_retriever)
        result = await retriever.retrieve("测试查询", top_k=5)

        assert len(result.text_results) == 2
        assert "text_count" in result.metadata

    def test_build_context_empty(self):
        """测试空结果构建上下文"""
        from src.agents_v2.multimodal import MultimodalRetriever, MultimodalRetrievalResult

        retriever = MultimodalRetriever()
        result = MultimodalRetrievalResult()

        context = retriever._build_context(result)
        assert context == ""

    def test_build_context_with_text(self):
        """测试带文本的结果构建上下文"""
        from src.agents_v2.multimodal import MultimodalRetriever, MultimodalRetrievalResult

        retriever = MultimodalRetriever()
        result = MultimodalRetrievalResult(
            text_results=["这是第一个文档", "这是第二个文档"]
        )

        context = retriever._build_context(result)
        assert "文本检索结果" in context
        assert "[文本1]" in context


class TestConvenienceFunctions:
    """便捷函数测试"""

    @pytest.mark.asyncio
    async def test_multimodal_retrieve(self):
        """测试多模态检索便捷函数"""
        from src.agents_v2.multimodal import multimodal_retrieve

        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=["doc1"])

        result = await multimodal_retrieve("测试", text_retriever=mock_retriever)
        assert result is not None

    @pytest.mark.asyncio
    async def test_analyze_image_multimodal(self):
        """测试图像多模态分析便捷函数"""
        from src.agents_v2.multimodal import analyze_image_multimodal
        from PIL import Image

        # 创建一个简单的测试图像
        img = Image.new('RGB', (50, 50), color='white')

        result = await analyze_image_multimodal(img)
        assert "type" in result
        assert "description" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])