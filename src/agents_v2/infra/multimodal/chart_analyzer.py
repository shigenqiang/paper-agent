"""
图表分析器 - Chart Analyzer

支持图表类型:
- 折线图: 趋势识别、极值检测
- 柱状图: 比较分析、排序
- 饼图: 占比分析
- 散点图: 相关性识别、离群点
- 热力图: 分布分析、密度
"""
from src.agents_v2.logging_config import get_logging_logger

import re

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

logger = get_logging_logger(__name__)


class ChartType(Enum):
    """图表类型"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    UNKNOWN = "unknown"


@dataclass
class ChartAnalysis:
    """图表分析结果"""
    chart_type: ChartType
    title: str = ""
    description: str = ""
    key_points: List[str] = field(default_factory=list)
    data_points: List[Dict] = field(default_factory=list)
    trends: List[str] = field(default_factory=list)
    anomalies: List[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChartAnalyzer:
    """图表理解与分析器"""

    def __init__(self, llm: Any = None):
        """初始化图表分析器

        Args:
            llm: 可选的LLM实例，用于生成描述
        """
        self.llm = llm

    async def analyze(self, image: Any, chart_type: str = None) -> ChartAnalysis:
        """分析图表内容

        Args:
            image: 图表图像 (PIL.Image或图像路径)
            chart_type: 图表类型（自动检测如果不指定）

        Returns:
            ChartAnalysis: 分析结果
        """
        # 检测图表类型
        if chart_type is None:
            detected_type = await self._detect_chart_type(image)
        else:
            detected_type = self._parse_chart_type(chart_type)

        # 根据类型选择分析策略
        type_mapping = {
            ChartType.LINE: self._analyze_line_chart,
            ChartType.BAR: self._analyze_bar_chart,
            ChartType.PIE: self._analyze_pie_chart,
            ChartType.SCATTER: self._analyze_scatter_chart,
            ChartType.HEATMAP: self._analyze_heatmap,
            ChartType.UNKNOWN: self._analyze_generic
        }

        analyzer = type_mapping.get(detected_type, self._analyze_generic)

        return await analyzer(image)

    async def _detect_chart_type(self, image: Any) -> ChartType:
        """检测图表类型

        Args:
            image: 图像

        Returns:
            ChartType: 检测到的类型
        """
        # 简单的基于视觉特征的检测
        # 实际应用中应该使用图像分类模型

        if self.llm:
            try:
                prompt = """
分析这个图表，判断其类型。图表类型包括：
- line: 折线图，用于显示趋势
- bar: 柱状图，用于比较数量
- pie: 饼图，用于显示占比
- scatter: 散点图，用于显示相关性
- heatmap: 热力图，用于显示密度分布

只返回一个类型名称：line/bar/pie/scatter/heatmap
"""
                result = await self.llm.agenerate([prompt])
                response = result.generations[0][0].text.strip().lower()

                return self._parse_chart_type(response)

            except Exception as e:
                logger.warning(f"LLM类型检测失败: {e}")

        return ChartType.UNKNOWN

    def _parse_chart_type(self, chart_type: str) -> ChartType:
        """解析图表类型字符串"""
        type_mapping = {
            "line": ChartType.LINE,
            "折线": ChartType.LINE,
            "bar": ChartType.BAR,
            "柱状": ChartType.BAR,
            "条形": ChartType.BAR,
            "pie": ChartType.PIE,
            "饼": ChartType.PIE,
            "scatter": ChartType.SCATTER,
            "散点": ChartType.SCATTER,
            "heatmap": ChartType.HEATMAP,
            "热力": ChartType.HEATMAP
        }

        for key, vtype in type_mapping.items():
            if key in chart_type.lower():
                return vtype

        return ChartType.UNKNOWN

    async def _analyze_line_chart(self, image: Any) -> ChartAnalysis:
        """分析折线图"""
        # 提取图像信息
        image_info = await self._extract_image_info(image)

        prompt = f"""
分析这个折线图，提取：
1. 标题和坐标轴标签
2. 数据趋势（上升/下降/平稳）
3. 关键数据点和极值
4. 图表描述（2-3句话）

返回JSON格式：
{{
    "title": "图表标题",
    "x_label": "X轴标签",
    "y_label": "Y轴标签",
    "trend": "上升/下降/平稳/波动",
    "key_points": ["点1描述", "点2描述"],
    "description": "图表描述",
    "confidence": 0.85
}}
"""
        if self.llm:
            try:
                result = await self.llm.agenerate([prompt])
                response = result.generations[0][0].text.strip()

                # 解析JSON响应
                import json
                data = self._extract_json(response)

                if data:
                    return ChartAnalysis(
                        chart_type=ChartType.LINE,
                        title=data.get("title", ""),
                        description=data.get("description", ""),
                        key_points=data.get("key_points", []),
                        trends=[data.get("trend", "")],
                        confidence=data.get("confidence", 0.8),
                        metadata={
                            "x_label": data.get("x_label", ""),
                            "y_label": data.get("y_label", "")
                        }
                    )
            except Exception as e:
                logger.error(f"LLM分析折线图失败: {e}")

        # 回退到简单分析
        return ChartAnalysis(
            chart_type=ChartType.LINE,
            title="折线图",
            description="显示数据趋势的折线图",
            confidence=0.5,
            trends=["需要更详细的分析"]
        )

    async def _analyze_bar_chart(self, image: Any) -> ChartAnalysis:
        """分析柱状图"""
        prompt = f"""
分析这个柱状图，提取：
1. 标题和坐标轴标签
2. 各柱子的数值排序
3. 最高和最低的柱子
4. 图表描述

返回JSON格式：
{{
    "title": "图表标题",
    "x_label": "X轴标签",
    "y_label": "Y轴标签",
    "sorted_values": [["类别1", 100], ["类别2", 80]],
    "highest": "类别名称",
    "lowest": "类别名称",
    "description": "图表描述",
    "confidence": 0.85
}}
"""
        if self.llm:
            try:
                result = await self.llm.agenerate([prompt])
                response = result.generations[0][0].text.strip()

                data = self._extract_json(response)

                if data:
                    return ChartAnalysis(
                        chart_type=ChartType.BAR,
                        title=data.get("title", ""),
                        description=data.get("description", ""),
                        key_points=[f"{item[0]}: {item[1]}" for item in data.get("sorted_values", [])[:5]],
                        data_points=[{"category": item[0], "value": item[1]} for item in data.get("sorted_values", [])],
                        confidence=data.get("confidence", 0.8),
                        metadata={
                            "highest": data.get("highest", ""),
                            "lowest": data.get("lowest", "")
                        }
                    )
            except Exception as e:
                logger.error(f"LLM分析柱状图失败: {e}")

        return ChartAnalysis(
            chart_type=ChartType.BAR,
            title="柱状图",
            description="用于比较数量的柱状图",
            confidence=0.5
        )

    async def _analyze_pie_chart(self, image: Any) -> ChartAnalysis:
        """分析饼图"""
        prompt = f"""
分析这个饼图，提取：
1. 标题
2. 各部分占比（百分比）
3. 最大的部分
4. 图表描述

返回JSON格式：
{{
    "title": "图表标题",
    "slices": [["类别1", 35], ["类别2", 25]],
    "largest_slice": "类别名称",
    "description": "图表描述",
    "confidence": 0.85
}}
"""
        if self.llm:
            try:
                result = await self.llm.agenerate([prompt])
                response = result.generations[0][0].text.strip()

                data = self._extract_json(response)

                if data:
                    return ChartAnalysis(
                        chart_type=ChartType.PIE,
                        title=data.get("title", ""),
                        description=data.get("description", ""),
                        key_points=[f"{item[0]}: {item[1]}%" for item in data.get("slices", [])],
                        data_points=[{"category": item[0], "percentage": item[1]} for item in data.get("slices", [])],
                        confidence=data.get("confidence", 0.8),
                        metadata={"largest_slice": data.get("largest_slice", "")}
                    )
            except Exception as e:
                logger.error(f"LLM分析饼图失败: {e}")

        return ChartAnalysis(
            chart_type=ChartType.PIE,
            title="饼图",
            description="显示占比的饼图",
            confidence=0.5
        )

    async def _analyze_scatter_chart(self, image: Any) -> ChartAnalysis:
        """分析散点图"""
        prompt = f"""
分析这个散点图，提取：
1. 标题和坐标轴标签
2. 相关性（正相关/负相关/无相关）
3. 离群点（如果有）
4. 图表描述

返回JSON格式：
{{
    "title": "图表标题",
    "x_label": "X轴标签",
    "y_label": "Y轴标签",
    "correlation": "正相关/负相关/无相关",
    "outliers": ["离群点1描述", "离群点2描述"],
    "description": "图表描述",
    "confidence": 0.85
}}
"""
        if self.llm:
            try:
                result = await self.llm.agenerate([prompt])
                response = result.generations[0][0].text.strip()

                data = self._extract_json(response)

                if data:
                    return ChartAnalysis(
                        chart_type=ChartType.SCATTER,
                        title=data.get("title", ""),
                        description=data.get("description", ""),
                        key_points=[data.get("correlation", "")],
                        anomalies=data.get("outliers", []),
                        confidence=data.get("confidence", 0.8),
                        metadata={
                            "x_label": data.get("x_label", ""),
                            "y_label": data.get("y_label", "")
                        }
                    )
            except Exception as e:
                logger.error(f"LLM分析散点图失败: {e}")

        return ChartAnalysis(
            chart_type=ChartType.SCATTER,
            title="散点图",
            description="显示相关性的散点图",
            confidence=0.5
        )

    async def _analyze_heatmap(self, image: Any) -> ChartAnalysis:
        """分析热力图"""
        prompt = f"""
分析这个热力图，提取：
1. 标题和轴标签
2. 高密度区域
3. 低密度区域
4. 整体分布描述

返回JSON格式：
{{
    "title": "图表标题",
    "x_label": "X轴标签",
    "y_label": "Y轴标签",
    "high_density": ["区域1", "区域2"],
    "low_density": ["区域3"],
    "description": "图表描述",
    "confidence": 0.85
}}
"""
        if self.llm:
            try:
                result = await self.llm.agenerate([prompt])
                response = result.generations[0][0].text.strip()

                data = self._extract_json(response)

                if data:
                    return ChartAnalysis(
                        chart_type=ChartType.HEATMAP,
                        title=data.get("title", ""),
                        description=data.get("description", ""),
                        key_points=[f"高密度: {', '.join(data.get('high_density', []))}"],
                        trends=[f"低密度: {', '.join(data.get('low_density', []))}"],
                        confidence=data.get("confidence", 0.8),
                        metadata={
                            "x_label": data.get("x_label", ""),
                            "y_label": data.get("y_label", "")
                        }
                    )
            except Exception as e:
                logger.error(f"LLM分析热力图失败: {e}")

        return ChartAnalysis(
            chart_type=ChartType.HEATMAP,
            title="热力图",
            description="显示密度分布的热力图",
            confidence=0.5
        )

    async def _analyze_generic(self, image: Any) -> ChartAnalysis:
        """通用图表分析"""
        return ChartAnalysis(
            chart_type=ChartType.UNKNOWN,
            title="图表",
            description="无法识别的图表类型",
            confidence=0.3
        )

    async def _extract_image_info(self, image: Any) -> Dict:
        """提取图像基本信息"""
        try:
            from PIL import Image

            if isinstance(image, str):
                image = Image.open(image)

            if isinstance(image, Image.Image):
                return {
                    "size": image.size,
                    "mode": image.mode
                }
        except Exception as e:
            logger.warning(f"图像信息提取失败: {e}")

        return {}

    def _extract_json(self, text: str) -> Optional[Dict]:
        """从文本中提取JSON"""
        import json

        # 尝试直接解析
        try:
            return json.loads(text)
        except:
            pass

        # 尝试从Markdown代码块中提取
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass

        # 尝试提取第一个 { 到最后一个 }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass

        return None


# 便捷函数
async def analyze_chart(image: Any, chart_type: str = None, llm: Any = None) -> ChartAnalysis:
    """分析图表的便捷函数

    Args:
        image: PIL.Image或图像路径
        chart_type: 图表类型
        llm: 可选的LLM实例

    Returns:
        ChartAnalysis: 分析结果
    """
    analyzer = ChartAnalyzer(llm=llm)
    return await analyzer.analyze(image, chart_type)
