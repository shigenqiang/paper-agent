"""
布局分析器 - Layout Analyzer

功能:
1. PDF布局分析
2. 栏检测
3. 段落检测
4. 阅读顺序判断

设计原则:
- 多栏布局支持
- 图像和表格区域识别
- 阅读顺序重建
"""
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class LayoutType(str, Enum):
    """布局类型"""
    SINGLE_COLUMN = "single_column"
    TWO_COLUMN = "two_column"
    MULTI_COLUMN = "multi_column"
    MIXED = "mixed"  # 混合布局


@dataclass
class LayoutBlock:
    """布局块"""
    block_id: str
    block_type: str  # "text", "image", "table", "header", "footer"
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    content: Optional[str] = None
    reading_order: int = 0
    column: Optional[int] = None
    page: int = 0


@dataclass
class LayoutAnalysisResult:
    """布局分析结果"""
    layout_type: LayoutType
    num_columns: int
    blocks: List[LayoutBlock]
    page_count: int
    reading_order_blocks: List[LayoutBlock]


class LayoutAnalyzer:
    """布局分析器"""

    def __init__(self):
        self._block_id_counter = 0

    def analyze_page(
        self,
        page_content: Dict[str, Any]
    ) -> Tuple[LayoutType, int, List[LayoutBlock]]:
        """分析单页布局

        Args:
            page_content: 页面内容，包含blocks等信息

        Returns:
            Tuple[LayoutType, int, List[LayoutBlock]]: (布局类型, 列数, 布局块)
        """
        blocks = page_content.get("blocks", [])

        if not blocks:
            return LayoutType.SINGLE_COLUMN, 1, []

        # 转换为LayoutBlock
        layout_blocks = []
        for block in blocks:
            layout_block = LayoutBlock(
                block_id=f"block_{self._block_id_counter}",
                block_type=block.get("type", "text"),
                bbox=block.get("bbox", (0, 0, 0, 0)),
                content=block.get("content"),
                page=block.get("page", 0)
            )
            layout_blocks.append(layout_block)
            self._block_id_counter += 1

        # 检测列数
        num_columns = self._detect_columns(layout_blocks)

        # 确定布局类型
        layout_type = self._determine_layout_type(num_columns)

        return layout_type, num_columns, layout_blocks

    def _detect_columns(self, blocks: List[LayoutBlock]) -> int:
        """检测列数"""
        if not blocks:
            return 1

        # 获取所有block的水平位置
        x_positions = []
        for block in blocks:
            x0, _, x1, _ = block.bbox
            x_positions.append(x0)
            x_positions.append(x1)

        if not x_positions:
            return 1

        # 计算页面的x范围
        min_x = min(x_positions)
        max_x = max(x_positions)
        page_width = max_x - min_x

        # 分析x位置分布
        # 使用聚类方法检测列边界
        left_blocks = [b for b in blocks if b.bbox[0] < min_x + page_width * 0.4]
        right_blocks = [b for b in blocks if b.bbox[0] > min_x + page_width * 0.6]

        # 如果左右两侧都有大量block，则为双栏
        if len(left_blocks) > len(blocks) * 0.3 and len(right_blocks) > len(blocks) * 0.3:
            return 2

        return 1

    def _determine_layout_type(self, num_columns: int) -> LayoutType:
        """确定布局类型"""
        if num_columns == 1:
            return LayoutType.SINGLE_COLUMN
        elif num_columns == 2:
            return LayoutType.TWO_COLUMN
        else:
            return LayoutType.MULTI_COLUMN

    def determine_reading_order(
        self,
        blocks: List[LayoutBlock],
        layout_type: LayoutType,
        num_columns: int
    ) -> List[LayoutBlock]:
        """确定阅读顺序

        Args:
            blocks: 布局块
            layout_type: 布局类型
            num_columns: 列数

        Returns:
            List[LayoutBlock]: 按阅读顺序排序的块
        """
        if layout_type == LayoutType.SINGLE_COLUMN:
            # 单栏：按y坐标排序（从上到下）
            return sorted(blocks, key=lambda b: b.bbox[1])

        elif layout_type == LayoutType.TWO_COLUMN:
            # 双栏：先按行分组，再按列排序
            # 简化实现：按y坐标分组，然后交替从左到右

            # 按y坐标排序
            sorted_blocks = sorted(blocks, key=lambda b: b.bbox[1])

            # 分配列
            if sorted_blocks:
                # 使用第一个block的x作为分界线
                mid_x = sum(b.bbox[0] for b in sorted_blocks[:5]) / 5

                for block in sorted_blocks:
                    if block.bbox[0] < mid_x:
                        block.column = 0
                    else:
                        block.column = 1

            # 按行和列排序
            def sort_key(block):
                y_row = int(block.bbox[1] / 50)  # 按50像素一行分组
                return (y_row, block.column or 0)

            return sorted(sorted_blocks, key=sort_key)

        else:
            # 多栏：简化处理，按x和y排序
            return sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))

    def analyze_document(
        self,
        pages: List[Dict[str, Any]]
    ) -> LayoutAnalysisResult:
        """分析整个文档的布局

        Args:
            pages: 页面列表

        Returns:
            LayoutAnalysisResult: 布局分析结果
        """
        all_blocks = []
        page_count = len(pages)
        max_columns = 1

        for page_num, page_content in enumerate(pages):
            layout_type, num_columns, blocks = self.analyze_page(page_content)
            max_columns = max(max_columns, num_columns)

            # 更新页码
            for block in blocks:
                block.page = page_num

            all_blocks.extend(blocks)

        # 确定整体布局类型
        if max_columns == 1:
            overall_layout = LayoutType.SINGLE_COLUMN
        elif max_columns == 2:
            overall_layout = LayoutType.TWO_COLUMN
        else:
            overall_layout = LayoutType.MULTI_COLUMN

        # 确定阅读顺序
        reading_order_blocks = self.determine_reading_order(
            all_blocks,
            overall_layout,
            max_columns
        )

        # 分配阅读顺序号
        for i, block in enumerate(reading_order_blocks):
            block.reading_order = i

        return LayoutAnalysisResult(
            layout_type=overall_layout,
            num_columns=max_columns,
            blocks=all_blocks,
            page_count=page_count,
            reading_order_blocks=reading_order_blocks
        )

    def extract_text_regions(
        self,
        blocks: List[LayoutBlock]
    ) -> List[LayoutBlock]:
        """提取文本区域"""
        return [b for b in blocks if b.block_type == "text"]

    def extract_image_regions(
        self,
        blocks: List[LayoutBlock]
    ) -> List[LayoutBlock]:
        """提取图像区域"""
        return [b for b in blocks if b.block_type == "image"]

    def extract_table_regions(
        self,
        blocks: List[LayoutBlock]
    ) -> List[LayoutBlock]:
        """提取表格区域"""
        return [b for b in blocks if b.block_type == "table"]


# 便捷函数
def analyze_layout(page_content: Dict[str, Any]) -> Tuple[LayoutType, int, List[LayoutBlock]]:
    """便捷布局分析函数"""
    analyzer = LayoutAnalyzer()
    return analyzer.analyze_page(page_content)
