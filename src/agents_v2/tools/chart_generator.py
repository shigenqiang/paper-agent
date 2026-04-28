"""
Chart Generator - 论文级图表生成工具

基于Matplotlib/Seaborn生成学术论文级图表。
支持:
- 折线图、柱状图、散点图、饼图、热力图
- 论文级配色和样式
- PDF/EPS矢量输出
- 多面板组合图
"""
import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class ChartStyle:
    """图表样式预设"""

    # 学术论文常用配色 (避免红绿色盲问题)
    PAPER_COLORS = [
        "#2E86AB",  # 蓝色
        "#A23B72",  # 紫红色
        "#F18F01",  # 橙色
        "#C73E1D",  # 红色
        "#3B1F2B",  # 深红
        "#44AF69",  # 绿色
        "#FCCA46",  # 黄色
        "#6B7B8C",  # 灰色
    ]

    # Nature期刊风格
    NATURE = {
        "axes.facecolor": "white",
        "axes.edgecolor": "black",
        "axes.linewidth": 0.8,
        "grid.linewidth": 0.5,
        "font.family": "sans-serif",
        "font.size": 10,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
    }

    # Science期刊风格
    SCIENCE = {
        "axes.facecolor": "#F0F0F0",
        "axes.edgecolor": "black",
        "axes.linewidth": 1.0,
        "grid.linewidth": 0.3,
        "font.family": "sans-serif",
        "font.size": 9,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
    }

    # 纯黑白风格 (兼容打印)
    PRINT = {
        "axes.facecolor": "white",
        "axes.edgecolor": "black",
        "axes.linewidth": 0.8,
        "grid.linewidth": 0,
        "font.family": "sans-serif",
        "font.size": 10,
        "legend.fontsize": 9,
    }


class ChartConfig:
    """图表配置"""

    def __init__(
        self,
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
        style: str = "nature",
        figsize: Tuple[float, float] = (6, 4),
        dpi: int = 300,
        output_dir: str = ".",
        legend_loc: str = "best",
        grid: bool = True,
        tight_layout: bool = True,
    ):
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.style = style
        self.figsize = figsize
        self.dpi = dpi
        self.output_dir = output_dir
        self.legend_loc = legend_loc
        self.grid = grid
        self.tight_layout = tight_layout

    def apply_style(self):
        """应用样式设置"""
        import matplotlib.pyplot as plt

        style_map = {
            "nature": ChartStyle.NATURE,
            "science": ChartStyle.SCIENCE,
            "print": ChartStyle.PRINT,
        }

        params = style_map.get(self.style, ChartStyle.NATURE)
        plt.rcParams.update(params)


class ChartGenerator:
    """
    图表生成器

    支持多种图表类型，自动应用论文级样式。
    """

    def __init__(self, config: Optional[ChartConfig] = None):
        self.config = config or ChartConfig()

    def _get_plt(self):
        """获取matplotlib.pyplot (延迟导入)"""
        import matplotlib

        matplotlib.use("Agg")  # 非交互式后端
        import matplotlib.pyplot as plt

        return plt

    def _get_colors(self, n: int) -> List[str]:
        """获取颜色列表"""
        colors = ChartStyle.PAPER_COLORS
        if n <= len(colors):
            return colors[:n]
        # 循环使用颜色
        return [colors[i % len(colors)] for i in range(n)]

    def _save_fig(
        self, filename: str, formats: List[str] = None
    ) -> Dict[str, str]:
        """保存图表到文件"""
        import matplotlib.pyplot as plt

        if formats is None:
            formats = ["png", "pdf"]

        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        paths = {}
        for fmt in formats:
            filepath = output_dir / f"{filename}.{fmt}"
            plt.savefig(
                filepath,
                format=fmt,
                dpi=self.config.dpi,
                bbox_inches="tight" if self.config.tight_layout else None,
            )
            paths[fmt] = str(filepath)

        return paths

    def line_chart(
        self,
        x_data: List[Any],
        y_data: Union[List[float], Dict[str, List[float]]],
        filename: str = "line_chart",
        xerr: Optional[List[float]] = None,
        yerr: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        生成折线图

        Args:
            x_data: X轴数据
            y_data: Y轴数据，可以是列表(单条线)或字典(多条线)
            filename: 保存文件名
            xerr: X轴误差
            yerr: Y轴误差

        Returns:
            包含图表路径和元数据的字典
        """
        plt = self._get_plt()
        self.config.apply_style()

        fig, ax = plt.subplots(figsize=self.config.figsize)

        if isinstance(y_data, dict):
            # 多条线
            colors = self._get_colors(len(y_data))
            for i, (label, y) in enumerate(y_data.items()):
                ax.plot(
                    x_data,
                    y,
                    label=label,
                    color=colors[i],
                    linewidth=1.5,
                    marker="o",
                    markersize=4,
                )
        else:
            # 单条线
            ax.plot(
                x_data, y_data, linewidth=1.5, color=self._get_colors(1)[0], marker="o", markersize=4
            )

        if xerr is not None or yerr is not None:
            ax.errorbar(x_data, y_data, xerr=xerr, yerr=yerr, fmt="none", color="black", capsize=2)

        ax.set_xlabel(self.config.xlabel, fontsize=10)
        ax.set_ylabel(self.config.ylabel, fontsize=10)
        if self.config.title:
            ax.set_title(self.config.title, fontsize=12, fontweight="bold")

        if self.config.grid:
            ax.grid(True, linestyle="--", alpha=0.5)

        if isinstance(y_data, dict):
            ax.legend(loc=self.config.legend_loc)

        paths = self._save_fig(filename)
        plt.close()

        return {
            "success": True,
            "type": "line_chart",
            "filename": filename,
            "paths": paths,
        }

    def bar_chart(
        self,
        x_data: List[str],
        y_data: Union[List[float], Dict[str, List[float]]],
        filename: str = "bar_chart",
        horizontal: bool = False,
    ) -> Dict[str, Any]:
        """
        生成柱状图

        Args:
            x_data: X轴类别
            y_data: Y轴数据
            filename: 保存文件名
            horizontal: 是否水平柱状图

        Returns:
            包含图表路径和元数据的字典
        """
        plt = self._get_plt()
        self.config.apply_style()

        fig, ax = plt.subplots(figsize=self.config.figsize)

        if isinstance(y_data, dict):
            # 分组柱状图
            n_groups = len(x_data)
            n_bars = len(y_data)
            bar_width = 0.8 / n_bars
            colors = self._get_colors(n_bars)

            for i, (label, values) in enumerate(y_data.items()):
                x_pos = [x + i * bar_width for x in range(n_groups)]
                if horizontal:
                    ax.barh(x_pos, values, bar_width, label=label, color=colors[i])
                else:
                    ax.bar(x_pos, values, bar_width, label=label, color=colors[i])

            if horizontal:
                ax.set_yticks([x + bar_width * (n_bars - 1) / 2 for x in range(n_groups)])
                ax.set_yticklabels(x_data)
            else:
                ax.set_xticks([x + bar_width * (n_bars - 1) / 2 for x in range(n_groups)])
                ax.set_xticklabels(x_data, rotation=45, ha="right")

            ax.legend(loc=self.config.legend_loc)
        else:
            # 单组柱状图
            colors = self._get_colors(len(x_data))
            if horizontal:
                ax.barh(x_data, y_data, color=colors)
            else:
                ax.bar(x_data, y_data, color=colors)

        ax.set_xlabel(self.config.xlabel, fontsize=10)
        ax.set_ylabel(self.config.ylabel, fontsize=10)
        if self.config.title:
            ax.set_title(self.config.title, fontsize=12, fontweight="bold")

        if self.config.grid and not horizontal:
            ax.grid(True, axis="y", linestyle="--", alpha=0.5)

        paths = self._save_fig(filename)
        plt.close()

        return {
            "success": True,
            "type": "bar_chart",
            "filename": filename,
            "paths": paths,
        }

    def scatter_plot(
        self,
        x_data: List[float],
        y_data: List[float],
        filename: str = "scatter",
        labels: Optional[List[str]] = None,
        sizes: Optional[List[float]] = None,
        colors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        生成散点图

        Args:
            x_data: X轴数据
            y_data: Y轴数据
            filename: 保存文件名
            labels: 数据点标签
            sizes: 数据点大小
            colors: 数据点颜色

        Returns:
            包含图表路径和元数据的字典
        """
        plt = self._get_plt()
        self.config.apply_style()

        fig, ax = plt.subplots(figsize=self.config.figsize)

        # 设置点大小和颜色
        default_size = 50
        default_color = self._get_colors(1)[0]

        point_sizes = sizes if sizes is not None else [default_size] * len(x_data)
        point_colors = colors if colors is not None else [default_color] * len(x_data)

        ax.scatter(x_data, y_data, s=point_sizes, c=point_colors, alpha=0.6, edgecolors="white", linewidth=0.5)

        # 添加标签
        if labels:
            for i, label in enumerate(labels):
                ax.annotate(label, (x_data[i], y_data[i]), fontsize=7, alpha=0.7)

        ax.set_xlabel(self.config.xlabel, fontsize=10)
        ax.set_ylabel(self.config.ylabel, fontsize=10)
        if self.config.title:
            ax.set_title(self.config.title, fontsize=12, fontweight="bold")

        if self.config.grid:
            ax.grid(True, linestyle="--", alpha=0.3)

        paths = self._save_fig(filename)
        plt.close()

        return {
            "success": True,
            "type": "scatter_plot",
            "filename": filename,
            "paths": paths,
        }

    def histogram(
        self,
        data: List[float],
        bins: int = 20,
        filename: str = "histogram",
        density: bool = False,
    ) -> Dict[str, Any]:
        """
        生成直方图

        Args:
            data: 数据列表
            bins: 分箱数
            filename: 保存文件名
            density: 是否显示密度

        Returns:
            包含图表路径和元数据的字典
        """
        plt = self._get_plt()
        self.config.apply_style()

        fig, ax = plt.subplots(figsize=self.config.figsize)

        n, bins_edges, patches = ax.hist(data, bins=bins, density=density, color=self._get_colors(1)[0], alpha=0.7, edgecolor="white")

        ax.set_xlabel(self.config.xlabel, fontsize=10)
        ax.set_ylabel("Density" if density else "Count", fontsize=10)
        if self.config.title:
            ax.set_title(self.config.title, fontsize=12, fontweight="bold")

        if self.config.grid:
            ax.grid(True, axis="y", linestyle="--", alpha=0.3)

        paths = self._save_fig(filename)
        plt.close()

        return {
            "success": True,
            "type": "histogram",
            "filename": filename,
            "paths": paths,
            "bins": bins,
            "counts": n.tolist() if hasattr(n, "tolist") else list(n),
        }

    def heatmap(
        self,
        data: List[List[float]],
        filename: str = "heatmap",
        x_labels: Optional[List[str]] = None,
        y_labels: Optional[List[str]] = None,
        cmap: str = "RdBu_r",
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        生成热力图

        Args:
            data: 2D数据矩阵
            filename: 保存文件名
            x_labels: X轴标签
            y_labels: Y轴标签
            cmap: 颜色映射
            vmin: 最小值
            vmax: 最大值

        Returns:
            包含图表路径和元数据的字典
        """
        plt = self._get_plt()
        self.config.apply_style()

        import numpy as np

        fig, ax = plt.subplots(figsize=self.config.figsize)

        im = ax.imshow(
            data,
            cmap=cmap,
            aspect="auto",
            vmin=vmin,
            vmax=vmax,
        )

        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax)
        cbar.ax.set_ylabel(self.config.ylabel, fontsize=10)

        # 设置标签
        if x_labels:
            ax.set_xticks(np.arange(len(x_labels)))
            ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=8)
        if y_labels:
            ax.set_yticks(np.arange(len(y_labels)))
            ax.set_yticklabels(y_labels, fontsize=8)

        if self.config.title:
            ax.set_title(self.config.title, fontsize=12, fontweight="bold")

        paths = self._save_fig(filename)
        plt.close()

        return {
            "success": True,
            "type": "heatmap",
            "filename": filename,
            "paths": paths,
        }

    def box_plot(
        self,
        data: Dict[str, List[float]],
        filename: str = "box_plot",
    ) -> Dict[str, Any]:
        """
        生成箱线图

        Args:
            data: 字典，键为组名，值为数据列表
            filename: 保存文件名

        Returns:
            包含图表路径和元数据的字典
        """
        plt = self._get_plt()
        self.config.apply_style()

        fig, ax = plt.subplots(figsize=self.config.figsize)

        labels = list(data.keys())
        values = list(data.values())
        colors = self._get_colors(len(labels))

        bp = ax.boxplot(values, labels=labels, patch_artist=True)

        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)

        ax.set_xlabel(self.config.xlabel, fontsize=10)
        ax.set_ylabel(self.config.ylabel, fontsize=10)
        if self.config.title:
            ax.set_title(self.config.title, fontsize=12, fontweight="bold")

        if self.config.grid:
            ax.grid(True, axis="y", linestyle="--", alpha=0.3)

        paths = self._save_fig(filename)
        plt.close()

        return {
            "success": True,
            "type": "box_plot",
            "filename": filename,
            "paths": paths,
        }

    def multi_panel(
        self,
        panels: List[Dict[str, Any]],
        filename: str = "multi_panel",
        nrows: int = 1,
        ncols: int = 2,
    ) -> Dict[str, Any]:
        """
        生成多面板组合图

        Args:
            panels: 面板配置列表，每个包含:
                - type: 图表类型 (line, bar, scatter, etc.)
                - data: 图表数据
                - title: 标题 (可选)
                - xlabel: X轴标签 (可选)
                - ylabel: Y轴标签 (可选)
            filename: 保存文件名
            nrows: 行数
            ncols: 列数

        Returns:
            包含图表路径和元数据的字典
        """
        plt = self._get_plt()
        self.config.apply_style()

        fig, axes = plt.subplots(nrows, ncols, figsize=(self.config.figsize[0] * ncols, self.config.figsize[1] * nrows))
        axes = axes.flatten() if nrows * ncols > 1 else [axes]

        for i, panel in enumerate(panels):
            if i >= len(axes):
                break

            ax = axes[i]
            panel_type = panel.get("type", "line")
            panel_data = panel.get("data", {})
            panel_title = panel.get("title", "")
            xlabel = panel.get("xlabel", self.config.xlabel)
            ylabel = panel.get("ylabel", self.config.ylabel)

            colors = self._get_colors(5)

            if panel_type == "line":
                y = panel_data.get("y", [])
                x = panel_data.get("x", range(len(y)))
                ax.plot(x, y, color=colors[0], linewidth=1.5, marker="o", markersize=3)

            elif panel_type == "bar":
                x = panel_data.get("x", range(len(panel_data.get("y", []))))
                y = panel_data.get("y", [])
                ax.bar(x, y, color=colors[0])

            elif panel_type == "scatter":
                x = panel_data.get("x", [])
                y = panel_data.get("y", [])
                ax.scatter(x, y, s=30, c=colors[0], alpha=0.6)

            ax.set_xlabel(xlabel, fontsize=9)
            ax.set_ylabel(ylabel, fontsize=9)
            if panel_title:
                ax.set_title(panel_title, fontsize=10, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.3)

        # 隐藏多余的子图
        for j in range(len(panels), len(axes)):
            axes[j].set_visible(False)

        if self.config.title:
            fig.suptitle(self.config.title, fontsize=14, fontweight="bold", y=1.02)

        paths = self._save_fig(filename)
        plt.close()

        return {
            "success": True,
            "type": "multi_panel",
            "filename": filename,
            "paths": paths,
            "nrows": nrows,
            "ncols": ncols,
        }


# 便捷函数
def create_line_chart(
    x_data: List[Any],
    y_data: Union[List[float], Dict[str, List[float]]],
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    filename: str = "line_chart",
    style: str = "nature",
) -> Dict[str, Any]:
    """创建折线图"""
    config = ChartConfig(title=title, xlabel=xlabel, ylabel=ylabel, style=style)
    generator = ChartGenerator(config)
    return generator.line_chart(x_data, y_data, filename)


def create_bar_chart(
    x_data: List[str],
    y_data: Union[List[float], Dict[str, List[float]]],
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    filename: str = "bar_chart",
    style: str = "nature",
) -> Dict[str, Any]:
    """创建柱状图"""
    config = ChartConfig(title=title, xlabel=xlabel, ylabel=ylabel, style=style)
    generator = ChartGenerator(config)
    return generator.bar_chart(x_data, y_data, filename)


def create_scatter_plot(
    x_data: List[float],
    y_data: List[float],
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    filename: str = "scatter",
    style: str = "nature",
) -> Dict[str, Any]:
    """创建散点图"""
    config = ChartConfig(title=title, xlabel=xlabel, ylabel=ylabel, style=style)
    generator = ChartGenerator(config)
    return generator.scatter_plot(x_data, y_data, filename)


def create_heatmap(
    data: List[List[float]],
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    filename: str = "heatmap",
    style: str = "nature",
) -> Dict[str, Any]:
    """创建热力图"""
    config = ChartConfig(title=title, xlabel=xlabel, ylabel=ylabel, style=style)
    generator = ChartGenerator(config)
    return generator.heatmap(data, filename)


def get_tool_spec():
    """获取工具规格"""
    from .tool_spec import ToolSpec, ParameterSpec, ParameterType

    return ToolSpec(
        name="generate_chart",
        description="生成学术论文级图表 (折线图/柱状图/散点图/热力图等)",
        parameters=[
            ParameterSpec(
                name="chart_type",
                description="图表类型: line, bar, scatter, histogram, heatmap, box",
                type=ParameterType.STRING,
                required=True,
            ),
            ParameterSpec(
                name="data",
                description="图表数据 (JSON格式)",
                type=ParameterType.OBJECT,
                required=True,
            ),
            ParameterSpec(
                name="title",
                description="图表标题",
                type=ParameterType.STRING,
                required=False,
            ),
            ParameterSpec(
                name="xlabel",
                description="X轴标签",
                type=ParameterType.STRING,
                required=False,
            ),
            ParameterSpec(
                name="ylabel",
                description="Y轴标签",
                type=ParameterType.STRING,
                required=False,
            ),
            ParameterSpec(
                name="filename",
                description="保存文件名",
                type=ParameterType.STRING,
                required=False,
            ),
        ],
        handler=create_line_chart,
        category="visualization",
    )
