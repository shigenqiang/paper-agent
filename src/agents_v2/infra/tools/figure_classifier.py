"""
图表分类器 - Figure Classifier

功能:
1. 图表类型识别
2. 图表描述生成
3. 数据提取

设计原则:
- 支持多种图表类型
- 基于视觉特征分类
- 可扩展的分类器
"""
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class FigureType(str, Enum):
    """图表类型"""
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    SCATTER_PLOT = "scatter_plot"
    HEATMAP = "heatmap"
    FLOWCHART = "flowchart"
    DIAGRAM = "diagram"
    TABLE = "table"
    IMAGE = "image"
    FORMULA = "formula"
    UNKNOWN = "unknown"


@dataclass
class FigureClassification:
    """图表分类结果"""
    figure_type: FigureType
    confidence: float
    sub_type: Optional[str] = None
    description: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None


@dataclass
class FigureAnalysisResult:
    """图表分析结果"""
    classification: FigureClassification
    caption: Optional[str] = None
    axis_labels: Optional[Dict[str, str]] = None
    legend: Optional[List[str]] = None
    data_points: Optional[List[Any]] = None


class FigureClassifier:
    """图表分类器"""

    def __init__(
        self,
        vision_encoder: Optional[Callable] = None,
        classifier_model: Optional[Callable] = None
    ):
        self.vision_encoder = vision_encoder
        self.classifier_model = classifier_model

        # 图表特征模式
        self._feature_patterns = {
            FigureType.LINE_CHART: {
                "indicators": ["折线", "趋势", "line", "时间序列"],
                "visual_hints": ["点", "线段", "坐标轴"]
            },
            FigureType.BAR_CHART: {
                "indicators": ["柱状", "条形", "bar", "比较"],
                "visual_hints": ["矩形", "柱子", "高度"]
            },
            FigureType.PIE_CHART: {
                "indicators": ["饼图", "比例", "占比", "pie"],
                "visual_hints": ["圆形", "扇形", "百分比"]
            },
            FigureType.SCATTER_PLOT: {
                "indicators": ["散点", "分布", "scatter", "相关性"],
                "visual_hints": ["点", "分布", "坐标"]
            },
            FigureType.HEATMAP: {
                "indicators": ["热力", "密度", "heatmap", "颜色深浅"],
                "visual_hints": ["颜色渐变", "矩阵", "色块"]
            },
            FigureType.FLOWCHART: {
                "indicators": ["流程", "步骤", "flowchart", "箭头"],
                "visual_hints": ["矩形", "菱形", "箭头", "连接线"]
            },
            FigureType.DIAGRAM: {
                "indicators": ["图示", "架构", "diagram", "结构"],
                "visual_hints": ["框图", "连接线", "层次"]
            },
            FigureType.TABLE: {
                "indicators": ["表格", "表", "table", "行列"],
                "visual_hints": ["网格", "单元格", "行列线"]
            },
            FigureType.FORMULA: {
                "indicators": ["公式", "方程", "formula", "latex", "数学"],
                "visual_hints": ["数学符号", "分数", "上下标"]
            }
        }

    async def classify(
        self,
        figure_input: Any,  # 可以是图像路径、base64、或者特征向量
        use_vision: bool = False
    ) -> FigureClassification:
        """分类图表

        Args:
            figure_input: 图表输入
            use_vision: 是否使用视觉模型

        Returns:
            FigureClassification: 分类结果
        """
        if use_vision and self.classifier_model:
            return await self._classify_with_vision(figure_input)
        else:
            return self._classify_by_features(figure_input)

    def _classify_by_features(self, figure_input: Any) -> FigureClassification:
        """基于特征分类

        Args:
            figure_input: 特征数据（可以是文本描述、URL等）

        Returns:
            FigureClassification: 分类结果
        """
        # 将输入转为字符串分析
        text = str(figure_input).lower()

        scores = {}

        for figure_type, patterns in self._feature_patterns.items():
            score = 0

            # 检查指标词
            for indicator in patterns["indicators"]:
                if indicator.lower() in text:
                    score += 1

            # 检查视觉提示
            for hint in patterns["visual_hints"]:
                if hint.lower() in text:
                    score += 0.5

            if score > 0:
                scores[figure_type] = score

        if not scores:
            return FigureClassification(
                figure_type=FigureType.UNKNOWN,
                confidence=0.5
            )

        # 选择得分最高的类型
        best_type = max(scores.keys(), key=lambda x: scores[x])
        max_score = scores[best_type]

        # 计算置信度
        confidence = min(max_score / 3.0, 1.0) if max_score > 0 else 0.5

        return FigureClassification(
            figure_type=best_type,
            confidence=confidence
        )

    async def _classify_with_vision(self, figure_input: Any) -> FigureClassification:
        """使用视觉模型分类"""
        # 使用vision encoder获取特征
        if self.vision_encoder:
            features = await self.vision_encoder(figure_input)
        else:
            features = figure_input

        # 使用分类器模型
        if self.classifier_model:
            result = await self.classifier_model(features)
            return FigureClassification(
                figure_type=FigureType(result.get("type", "unknown")),
                confidence=result.get("confidence", 0.5),
                sub_type=result.get("sub_type")
            )

        # 回退到基于特征的方法
        return self._classify_by_features(features)

    def extract_data_from_figure(
        self,
        figure_type: FigureType,
        figure_data: Any
    ) -> Optional[Dict[str, Any]]:
        """从图表中提取数据

        Args:
            figure_type: 图表类型
            figure_data: 图表数据

        Returns:
            Optional[Dict[str, Any]]: 提取的数据
        """
        if figure_type == FigureType.BAR_CHART:
            return self._extract_bar_chart_data(figure_data)
        elif figure_type == FigureType.LINE_CHART:
            return self._extract_line_chart_data(figure_data)
        elif figure_type == FigureType.PIE_CHART:
            return self._extract_pie_chart_data(figure_data)
        elif figure_type == FigureType.TABLE:
            return self._extract_table_data(figure_data)
        else:
            return None

    def _extract_bar_chart_data(self, data: Any) -> Dict[str, Any]:
        """提取柱状图数据"""
        # 简化实现
        return {
            "categories": [],
            "values": [],
            "title": ""
        }

    def _extract_line_chart_data(self, data: Any) -> Dict[str, Any]:
        """提取折线图数据"""
        return {
            "x_values": [],
            "y_values": [],
            "series": []
        }

    def _extract_pie_chart_data(self, data: Any) -> Dict[str, Any]:
        """提取饼图数据"""
        return {
            "labels": [],
            "values": [],
            "percentages": []
        }

    def _extract_table_data(self, data: Any) -> Dict[str, Any]:
        """提取表格数据"""
        return {
            "headers": [],
            "rows": [],
            "num_rows": 0,
            "num_cols": 0
        }


class ChartAnalyzer:
    """图表分析器"""

    def __init__(self):
        self.classifier = FigureClassifier()

    async def analyze(
        self,
        figure_input: Any,
        use_vision: bool = False
    ) -> FigureAnalysisResult:
        """分析图表

        Args:
            figure_input: 图表输入
            use_vision: 是否使用视觉模型

        Returns:
            FigureAnalysisResult: 分析结果
        """
        classification = await self.classifier.classify(figure_input, use_vision)

        # 提取数据
        extracted_data = None
        if classification.confidence > 0.7:
            extracted_data = self.classifier.extract_data_from_figure(
                classification.figure_type,
                figure_input
            )

        return FigureAnalysisResult(
            classification=classification,
            extracted_data=extracted_data
        )


# 便捷函数
async def classify_figure(
    figure_input: Any,
    use_vision: bool = False
) -> FigureClassification:
    """便捷图表分类函数"""
    classifier = FigureClassifier()
    return await classifier.classify(figure_input, use_vision)
