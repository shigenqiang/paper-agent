"""
Table Detector - 表格检测器

检测PDF或图像中的表格位置和结构。
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import re

logger = logging.getLogger(__name__)


@dataclass
class BoundingBox:
    """边界框"""
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return self.width * self.height

    def intersects(self, other: "BoundingBox") -> bool:
        """检测是否与另一个边界框相交"""
        return not (
            self.x + self.width < other.x or
            other.x + other.width < self.x or
            self.y + self.height < other.y or
            other.y + other.height < self.y
        )


@dataclass
class TableCell:
    """表格单元格"""
    row: int
    col: int
    content: str
    bbox: BoundingBox
    is_header: bool = False
    row_span: int = 1
    col_span: int = 1


@dataclass
class DetectedTable:
    """检测到的表格"""
    id: int
    bbox: BoundingBox
    cells: List[List[str]]
    headers: List[str]
    num_rows: int
    num_cols: int
    confidence: float
    table_type: str  # "standard", "bordered", "borderless"


class TableDetector:
    """表格检测器

    检测PDF页面或图像中的表格。
    支持三种表格类型：
    - bordered: 有明显边框的表格
    - borderless: 无边框的表格
    - semi-bordered: 部分边框的表格
    """

    # 表格检测的启发式规则
    HORIZONTAL_LINE_THRESHOLD = 0.8  # 水平线置信度阈值
    VERTICAL_LINE_THRESHOLD = 0.8   # 垂直线置信度阈值
    MIN_TABLE_ROWS = 2
    MIN_TABLE_COLS = 2

    def __init__(self, image_mode: bool = False):
        """初始化表格检测器

        Args:
            image_mode: 是否为图像模式（True=使用CV，False=使用文本分析）
        """
        self.image_mode = image_mode
        self._table_counter = 0

    def detect(self, page_content: Any) -> List[DetectedTable]:
        """检测页面中的表格

        Args:
            page_content: 页面内容（图像或文本+坐标）

        Returns:
            List[DetectedTable]: 检测到的表格列表
        """
        if self.image_mode:
            return self._detect_from_image(page_content)
        else:
            return self._detect_from_text(page_content)

    def _detect_from_image(self, image: Any) -> List[DetectedTable]:
        """从图像检测表格（需要OpenCV）

        Args:
            image: 图像数据

        Returns:
            List[DetectedTable]: 检测到的表格列表
        """
        try:
            import cv2
            import numpy as np

            # 转换为灰度图
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # 边缘检测
            edges = cv2.Canny(gray, 50, 150)

            # 检测水平线
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
            horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)

            # 检测垂直线
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))
            vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)

            # 合并线段
            table_mask = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0)

            # 轮廓检测
            contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            tables = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > 50 and h > 50:  # 最小尺寸过滤
                    bbox = BoundingBox(x=float(x), y=float(y), width=float(w), height=float(h))
                    table = DetectedTable(
                        id=self._next_id(),
                        bbox=bbox,
                        cells=[],
                        headers=[],
                        num_rows=0,
                        num_cols=0,
                        confidence=0.8,
                        table_type="bordered"
                    )
                    tables.append(table)

            return tables

        except ImportError:
            logger.warning("OpenCV未安装，无法进行图像表格检测")
            return []
        except Exception as e:
            logger.error(f"图像表格检测失败: {e}")
            return []

    def _detect_from_text(self, page_text: Any) -> List[DetectedTable]:
        """从文本检测表格（基于启发式规则）

        Args:
            page_text: 页面文本内容

        Returns:
            List[DetectedTable]: 检测到的表格列表
        """
        if isinstance(page_text, str):
            return self._detect_tables_in_text(page_text)
        elif isinstance(page_text, dict):
            return self._detect_tables_in_elements(page_text)
        else:
            return []

    def _detect_tables_in_text(self, text: str) -> List[DetectedTable]:
        """在文本中检测表格

        Args:
            text: 页面文本

        Returns:
            List[DetectedTable]: 检测到的表格列表
        """
        tables = []
        lines = text.split("\n")

        # 检测表格模式
        i = 0
        while i < len(lines):
            if self._is_table_line(lines[i]):
                table_lines = [lines[i]]
                j = i + 1

                # 收集表格行
                while j < len(lines) and self._is_table_line(lines[j]):
                    table_lines.append(lines[j])
                    j += 1

                # 解析表格
                if len(table_lines) >= self.MIN_TABLE_ROWS:
                    table = self._parse_table_lines(table_lines)
                    if table:
                        tables.append(table)

                i = j
            else:
                i += 1

        return tables

    def _detect_tables_in_elements(self, elements: Dict[str, Any]) -> List[DetectedTable]:
        """从带坐标的元素中检测表格

        Args:
            elements: 带坐标的页面元素

        Returns:
            List[DetectedTable]: 检测到的表格列表
        """
        tables = []

        # 查找表格起始位置（包含多个对齐的列分隔符）
        table_regions = self._find_table_regions(elements)

        for region in table_regions:
            cells = self._extract_cells_from_region(region)
            if cells:
                table = self._create_table_from_cells(cells)
                if table:
                    tables.append(table)

        return tables

    def _is_table_line(self, line: str) -> bool:
        """判断行是否是表格行

        Args:
            line: 文本行

        Returns:
            bool: 是否是表格行
        """
        # 检查是否包含表格分隔符
        separators = ["|", "│", "┃", "┌", "┐", "└", "┘", "├", "┤", "┬", "┴", "┼"]
        if any(sep in line for sep in separators):
            return True

        # 检查是否是对齐的制表符分隔内容
        if "\t" in line:
            parts = line.split("\t")
            if len(parts) >= self.MIN_TABLE_COLS:
                # 检查对齐一致性
                if all(parts[0].strip()) and len(set(len(p.split()[0]) if p.strip() else 0 for p in parts)) > 1:
                    return True

        # 检查是否是空格分隔的列（固定宽度格式）
        if "  " in line and len(line.split()) >= self.MIN_TABLE_COLS:
            # 表格行通常有多个空格分隔的内容
            parts = line.split()
            if len(parts) >= 2:
                return True

        return False

    def _parse_table_lines(self, lines: List[str]) -> Optional[DetectedTable]:
        """解析表格行

        Args:
            lines: 表格文本行

        Returns:
            DetectedTable或None
        """
        cells = []

        for line in lines:
            if "│" in line or "|" in line:
                # 行列分隔符格式
                parts = re.split(r'│|\|', line)
            elif "\t" in line:
                # 制表符格式
                parts = line.split("\t")
            else:
                # 空格分隔格式
                parts = line.split()

            cells.append([p.strip() for p in parts if p.strip()])

        if not cells:
            return None

        # 检测表头（第一行）
        headers = cells[0] if cells else []
        num_rows = len(cells)
        num_cols = max(len(row) for row in cells)

        # 估算边界框（基于文本位置）
        bbox = BoundingBox(x=0.0, y=0.0, width=100.0, height=num_rows * 10.0)

        return DetectedTable(
            id=self._next_id(),
            bbox=bbox,
            cells=cells,
            headers=headers,
            num_rows=num_rows,
            num_cols=num_cols,
            confidence=0.7,
            table_type="text"
        )

    def _find_table_regions(self, elements: Dict[str, Any]) -> List[List[Dict]]:
        """查找表格区域

        Args:
            elements: 页面元素

        Returns:
            List[List[Dict]]: 表格区域列表
        """
        regions = []

        # 简单实现：查找垂直对齐的元素组
        if "blocks" in elements:
            blocks = elements["blocks"]
            current_region = []

            for block in blocks:
                if self._is_table_block(block):
                    current_region.append(block)
                else:
                    if current_region:
                        regions.append(current_region)
                        current_region = []

            if current_region:
                regions.append(current_region)

        return regions

    def _is_table_block(self, block: Dict) -> bool:
        """判断块是否是表格块

        Args:
            block: 页面块

        Returns:
            bool: 是否是表格块
        """
        # 检查是否有表格特征
        if "lines" in block:
            for line in block["lines"]:
                if self._is_table_line(line.get("text", "")):
                    return True
        return False

    def _extract_cells_from_region(self, region: List[Dict]) -> List[List[str]]:
        """从区域提取单元格

        Args:
            region: 表格区域

        Returns:
            List[List[str]]: 单元格内容
        """
        cells = []

        for block in region:
            if "lines" in block:
                row = []
                for line in block["lines"]:
                    text = line.get("text", "").strip()
                    if text:
                        row.append(text)
                if row:
                    cells.append(row)

        return cells

    def _create_table_from_cells(self, cells: List[List[str]]) -> Optional[DetectedTable]:
        """从单元格创建表格

        Args:
            cells: 单元格内容

        Returns:
            DetectedTable或None
        """
        if not cells or len(cells) < self.MIN_TABLE_ROWS:
            return None

        headers = cells[0] if cells else []
        num_rows = len(cells)
        num_cols = max(len(row) for row in cells)

        bbox = BoundingBox(x=0.0, y=0.0, width=100.0, height=num_rows * 10.0)

        return DetectedTable(
            id=self._next_id(),
            bbox=bbox,
            cells=cells,
            headers=headers,
            num_rows=num_rows,
            num_cols=num_cols,
            confidence=0.75,
            table_type="structured"
        )

    def _next_id(self) -> int:
        """获取下一个表格ID"""
        self._table_counter += 1
        return self._table_counter


# 便捷函数
def detect_tables(page_content: Any) -> List[DetectedTable]:
    """检测页面中的表格

    Args:
        page_content: 页面内容

    Returns:
        List[DetectedTable]: 检测到的表格列表
    """
    detector = TableDetector()
    return detector.detect(page_content)
