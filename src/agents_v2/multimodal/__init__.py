"""
Multimodal模块 - 多模态理解与检索

包含:
- VisionEncoder: CLIP视觉编码器
- ChartAnalyzer: 图表分析器
- FormulaRecognizer: 公式识别器
- DiagramParser: 流程图解析器
- MultimodalRetriever: 多模态检索器
"""
from .vision_encoder import (
    VisionEncoder,
    VisionResult,
    ImageTextMatcher,
    encode_image,
    compute_image_text_similarity
)
from .chart_analyzer import (
    ChartAnalyzer,
    ChartType,
    ChartAnalysis,
    analyze_chart
)
from .formula_recognizer import (
    FormulaRecognizer,
    FormulaRecognition,
    LaTeXRenderer,
    recognize_formula,
    explain_formula
)
from .diagram_parser import (
    DiagramParser,
    DiagramNode,
    DiagramEdge,
    DiagramResult,
    NodeDetector,
    EdgeDetector,
    parse_diagram
)
from .multimodal_retriever import (
    MultimodalRetriever,
    MultimodalRetrievalResult,
    multimodal_retrieve,
    analyze_image_multimodal
)

__all__ = [
    # 视觉编码器
    "VisionEncoder",
    "VisionResult",
    "ImageTextMatcher",
    "encode_image",
    "compute_image_text_similarity",

    # 图表分析
    "ChartAnalyzer",
    "ChartType",
    "ChartAnalysis",
    "analyze_chart",

    # 公式识别
    "FormulaRecognizer",
    "FormulaRecognition",
    "LaTeXRenderer",
    "recognize_formula",
    "explain_formula",

    # 流程图解析
    "DiagramParser",
    "DiagramNode",
    "DiagramEdge",
    "DiagramResult",
    "NodeDetector",
    "EdgeDetector",
    "parse_diagram",

    # 多模态检索
    "MultimodalRetriever",
    "MultimodalRetrievalResult",
    "multimodal_retrieve",
    "analyze_image_multimodal"
]