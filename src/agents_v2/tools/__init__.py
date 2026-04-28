"""
工具模块 - 统一管理Agent工具

提供:
1. 工具规格定义 (ToolSpec, ParameterSpec)
2. 工具注册表 (ToolRegistry)
3. 工具协同引擎 (ToolCoordinationEngine)
4. 内置工具 (buildin_tools)
5. PDF解析工具 (citation_extractor, table_detector, etc.)
6. 布局分析器 (LayoutAnalyzer)
7. 图表分类器 (FigureClassifier)
8. Marker增强解析器 (marker_pdf_parser)
"""
from .tool_spec import (
    ToolSpec,
    ParameterSpec,
    ParameterType,
    ValidationResult,
    ToolResult
)
from .registry import (
    ToolRegistry,
    get_tool_registry,
    register_builtin_tools
)
from .tool_coordinator import (
    ToolCoordinationEngine,
    DependencyType,
    ToolDependency,
    ExecutionPlan,
    get_coordination_engine
)
from .buildin_tools import register_all
from .extended_search import register_extended
from .paper_tools import register_paper_tools
from .layout_analyzer import (
    LayoutAnalyzer,
    LayoutType,
    LayoutBlock,
    LayoutAnalysisResult,
    analyze_layout
)
from .figure_classifier import (
    FigureClassifier,
    FigureType,
    FigureClassification,
    FigureAnalysisResult,
    classify_figure
)
from .marker_pdf_parser import (
    MarkerPDFParser,
    MarkerConfig,
    MarkerLatexExtractor,
    convert_pdf_with_marker,
    extract_paper_formulas,
    extract_paper_tables
)
from .zotero_client import (
    ZoteroClient,
    ZoteroConfig,
    ZoteroItem,
    search_zotero,
    export_zotero_bibtex
)
from .chart_generator import (
    ChartGenerator,
    ChartConfig,
    ChartStyle,
    create_line_chart,
    create_bar_chart,
    create_scatter_plot,
    create_heatmap,
)
from .enhanced_chart_generator import (
    EnhancedChartGenerator,
    MatplotlibChartMaker,
    PlotlyChartMaker,
    create_enhanced_chart,
)
from .enhanced_pdf_parser import (
    EnhancedPDFParser,
    ParsedContent,
    FormulaResult,
    TableResult,
    FigureResult,
    parse_pdf_enhanced,
)
from .doi_utils import (
    DOIVerifier,
    DOIResult,
    DOIMetadataFetcher,
    verify_doi,
    verify_dois,
    fetch_doi_metadata,
    extract_doi_from_text,
    build_citation_from_doi,
)

__all__ = [
    # 工具规格
    "ToolSpec",
    "ParameterSpec",
    "ParameterType",
    "ValidationResult",
    "ToolResult",
    # 注册表
    "ToolRegistry",
    "get_tool_registry",
    "register_builtin_tools",
    # 协同引擎
    "ToolCoordinationEngine",
    "DependencyType",
    "ToolDependency",
    "ExecutionPlan",
    "get_coordination_engine",
    # 内置工具
    "register_all",
    "register_extended",
    "register_paper_tools",
    # 布局分析
    "LayoutAnalyzer",
    "LayoutType",
    "LayoutBlock",
    "LayoutAnalysisResult",
    "analyze_layout",
    # 图表分类
    "FigureClassifier",
    "FigureType",
    "FigureClassification",
    "FigureAnalysisResult",
    "classify_figure",
    # Marker增强PDF解析
    "MarkerPDFParser",
    "MarkerConfig",
    "MarkerLatexExtractor",
    "convert_pdf_with_marker",
    "extract_paper_formulas",
    "extract_paper_tables",
    # Zotero引用管理
    "ZoteroClient",
    "ZoteroConfig",
    "ZoteroItem",
    "search_zotero",
    "export_zotero_bibtex",
    # 图表生成
    "ChartGenerator",
    "ChartConfig",
    "ChartStyle",
    "create_line_chart",
    "create_bar_chart",
    "create_scatter_plot",
    "create_heatmap",
    # 增强图表生成
    "EnhancedChartGenerator",
    "MatplotlibChartMaker",
    "PlotlyChartMaker",
    "create_enhanced_chart",
    # 增强PDF解析
    "EnhancedPDFParser",
    "ParsedContent",
    "FormulaResult",
    "TableResult",
    "FigureResult",
    "parse_pdf_enhanced",
    # DOI工具
    "DOIVerifier",
    "DOIResult",
    "DOIMetadataFetcher",
    "verify_doi",
    "verify_dois",
    "fetch_doi_metadata",
    "extract_doi_from_text",
    "build_citation_from_doi",
]
