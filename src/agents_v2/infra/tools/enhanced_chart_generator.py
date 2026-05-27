"""
Enhanced Chart Generator - 交互式图表生成器

支持:
1. Matplotlib - 论文级矢量图表 (PDF/EPS)
2. Plotly - 交互式HTML图表
3. 统计图表 - 箱线图、小提琴图、密度图

架构:
    EnhancedChartGenerator
        ├── MatplotlibChartMaker (静态矢量图)
        ├── PlotlyChartMaker (交互式图表)
        └── StatisticalChartMaker (统计图表)
"""
from src.agents_v2.logging_config import get_logging_logger

import json

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = get_logging_logger(__name__)


# 学术论文配色方案
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

# Plotly配色方案
PLOTLY_COLORS = [
    "#2E86AB",
    "#A23B72",
    "#F18F01",
    "#C73E1D",
    "#44AF69",
    "#636EFA",
    "#BABABA",
]


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
        font_family: str = "sans-serif",
        font_size: int = 10,
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
        self.font_family = font_family
        self.font_size = font_size

    def apply_matplotlib_style(self):
        """应用Matplotlib样式"""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        params = {
            "axes.facecolor": "white",
            "axes.edgecolor": "black",
            "axes.linewidth": 0.8,
            "grid.linewidth": 0.5,
            "font.family": self.font_family,
            "font.size": self.font_size,
            "legend.fontsize": self.font_size - 1,
            "xtick.labelsize": self.font_size - 1,
            "ytick.labelsize": self.font_size - 1,
        }

        if self.style == "science":
            params["axes.facecolor"] = "#F0F0F0"
        elif self.style == "print":
            params["grid.linewidth"] = 0

        plt.rcParams.update(params)


class PlotlyConfig:
    """Plotly图表配置"""

    def __init__(
        self,
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
        template: str = "plotly_white",
        width: int = None,
        height: int = None,
    ):
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.template = template
        self.width = width or 800
        self.height = height or 500


class MatplotlibChartMaker:
    """Matplotlib图表制作器"""

    def __init__(self, config: ChartConfig):
        self.config = config

    def _get_colors(self, n: int) -> List[str]:
        colors = PAPER_COLORS
        return [colors[i % len(colors)] for i in range(n)]

    def _save_fig(self, fig, filename: str, formats: List[str]) -> Dict[str, str]:
        """保存图表"""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        paths = {}
        for fmt in formats:
            filepath = output_dir / f"{filename}.{fmt}"
            fig.savefig(
                filepath,
                format=fmt,
                dpi=self.config.dpi,
                bbox_inches="tight",
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
        """折线图"""
        import matplotlib.pyplot as plt

        self.config.apply_matplotlib_style()
        fig, ax = plt.subplots(figsize=self.config.figsize)

        if isinstance(y_data, dict):
            colors = self._get_colors(len(y_data))
            for i, (label, y) in enumerate(y_data.items()):
                ax.plot(x_data, y, label=label, color=colors[i], linewidth=1.5, marker="o", markersize=4)
        else:
            ax.plot(x_data, y_data, linewidth=1.5, color=colors[0] if "colors" in dir() else self._get_colors(1)[0], marker="o", markersize=4)

        if xerr is not None or yerr is not None:
            ax.errorbar(x_data, y_data, xerr=xerr, yerr=yerr, fmt="none", color="black", capsize=2)

        ax.set_xlabel(self.config.xlabel, fontsize=self.config.font_size)
        ax.set_ylabel(self.config.ylabel, fontsize=self.config.font_size)
        if self.config.title:
            ax.set_title(self.config.title, fontsize=self.config.font_size + 2, fontweight="bold")
        if self.config.grid:
            ax.grid(True, linestyle="--", alpha=0.5)
        if isinstance(y_data, dict):
            ax.legend(loc=self.config.legend_loc)

        paths = self._save_fig(fig, filename, ["png", "pdf"])
        plt.close()

        return {"success": True, "type": "line_chart", "filename": filename, "paths": paths}

    def bar_chart(
        self,
        x_data: List[str],
        y_data: Union[List[float], Dict[str, List[float]]],
        filename: str = "bar_chart",
        horizontal: bool = False,
    ) -> Dict[str, Any]:
        """柱状图"""
        import matplotlib.pyplot as plt

        self.config.apply_matplotlib_style()
        fig, ax = plt.subplots(figsize=self.config.figsize)

        colors = self._get_colors(len(x_data))

        if isinstance(y_data, dict):
            n_groups = len(x_data)
            n_bars = len(y_data)
            bar_width = 0.8 / n_bars

            for i, (label, values) in enumerate(y_data.items()):
                x_pos = [x + i * bar_width for x in range(n_groups)]
                if horizontal:
                    ax.barh(x_pos, values, bar_width, label=label, color=self._get_colors(n_bars)[i])
                else:
                    ax.bar(x_pos, values, bar_width, label=label, color=self._get_colors(n_bars)[i])

            if horizontal:
                ax.set_yticks([x + bar_width * (n_bars - 1) / 2 for x in range(n_groups)])
                ax.set_yticklabels(x_data)
            else:
                ax.set_xticks([x + bar_width * (n_bars - 1) / 2 for x in range(n_groups)])
                ax.set_xticklabels(x_data, rotation=45, ha="right")

            ax.legend(loc=self.config.legend_loc)
        else:
            if horizontal:
                ax.barh(x_data, y_data, color=colors)
            else:
                ax.bar(x_data, y_data, color=colors)

        ax.set_xlabel(self.config.xlabel, fontsize=self.config.font_size)
        ax.set_ylabel(self.config.ylabel, fontsize=self.config.font_size)
        if self.config.title:
            ax.set_title(self.config.title, fontsize=self.config.font_size + 2, fontweight="bold")
        if self.config.grid and not horizontal:
            ax.grid(True, axis="y", linestyle="--", alpha=0.5)

        paths = self._save_fig(fig, filename, ["png", "pdf"])
        plt.close()

        return {"success": True, "type": "bar_chart", "filename": filename, "paths": paths}

    def scatter_plot(
        self,
        x_data: List[float],
        y_data: List[float],
        labels: Optional[List[str]] = None,
        sizes: Optional[List[float]] = None,
        filename: str = "scatter",
    ) -> Dict[str, Any]:
        """散点图"""
        import matplotlib.pyplot as plt

        self.config.apply_matplotlib_style()
        fig, ax = plt.subplots(figsize=self.config.figsize)

        default_size = 50
        point_sizes = sizes if sizes is not None else [default_size] * len(x_data)

        ax.scatter(x_data, y_data, s=point_sizes, c=self._get_colors(1)[0], alpha=0.6, edgecolors="white", linewidth=0.5)

        if labels:
            for i, label in enumerate(labels):
                ax.annotate(label, (x_data[i], y_data[i]), fontsize=7, alpha=0.7)

        ax.set_xlabel(self.config.xlabel, fontsize=self.config.font_size)
        ax.set_ylabel(self.config.ylabel, fontsize=self.config.font_size)
        if self.config.title:
            ax.set_title(self.config.title, fontsize=self.config.font_size + 2, fontweight="bold")
        if self.config.grid:
            ax.grid(True, linestyle="--", alpha=0.3)

        paths = self._save_fig(fig, filename, ["png", "pdf"])
        plt.close()

        return {"success": True, "type": "scatter", "filename": filename, "paths": paths}

    def heatmap(
        self,
        data: List[List[float]],
        x_labels: Optional[List[str]] = None,
        y_labels: Optional[List[str]] = None,
        filename: str = "heatmap",
        cmap: str = "RdBu_r",
    ) -> Dict[str, Any]:
        """热力图"""
        import matplotlib.pyplot as plt
        import numpy as np

        self.config.apply_matplotlib_style()
        fig, ax = plt.subplots(figsize=self.config.figsize)

        im = ax.imshow(data, cmap=cmap, aspect="auto")

        cbar = plt.colorbar(im, ax=ax)
        cbar.ax.set_ylabel(self.config.ylabel, fontsize=self.config.font_size - 1)

        if x_labels:
            ax.set_xticks(np.arange(len(x_labels)))
            ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=self.config.font_size - 2)
        if y_labels:
            ax.set_yticks(np.arange(len(y_labels)))
            ax.set_yticklabels(y_labels, fontsize=self.config.font_size - 2)

        if self.config.title:
            ax.set_title(self.config.title, fontsize=self.config.font_size + 2, fontweight="bold")

        paths = self._save_fig(fig, filename, ["png", "pdf"])
        plt.close()

        return {"success": True, "type": "heatmap", "filename": filename, "paths": paths}


class PlotlyChartMaker:
    """Plotly交互式图表制作器"""

    def __init__(self, config: PlotlyConfig):
        self.config = config

    def _get_colors(self, n: int) -> List[str]:
        colors = PLOTLY_COLORS
        return [colors[i % len(colors)] for i in range(n)]

    def _create_layout(self, fig) -> None:
        """创建布局"""
        fig.update_layout(
            title=dict(text=self.config.title, x=0.5, font=dict(size=16)),
            xaxis=dict(title=self.config.xlabel, title_font=dict(size=14)),
            yaxis=dict(title=self.config.ylabel, title_font=dict(size=14)),
            template=self.config.template,
            width=self.config.width,
            height=self.config.height,
            legend=dict(x=1.02, y=1),
        )

    def line_chart(
        self,
        x_data: List[Any],
        y_data: Union[List[float], Dict[str, List[float]]],
        filename: str = "line_chart",
    ) -> Dict[str, Any]:
        """Plotly折线图"""
        import plotly.graph_objects as go

        fig = go.Figure()

        if isinstance(y_data, dict):
            colors = self._get_colors(len(y_data))
            for i, (label, y) in enumerate(y_data.items()):
                fig.add_trace(go.Scatter(x=x_data, y=y, mode="lines+markers", name=label, line=dict(color=colors[i], width=2), marker=dict(size=6)))
        else:
            fig.add_trace(go.Scatter(x=x_data, y=y_data, mode="lines+markers", name="data", line=dict(color=colors[0] if "colors" in dir() else self._get_colors(1)[0], width=2), marker=dict(size=6)))

        self._create_layout(fig)

        html_path = Path(self.config.title or filename).parent / f"{filename}.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)

        fig.write_html(str(html_path))

        return {
            "success": True,
            "type": "line_chart",
            "filename": filename,
            "html_path": str(html_path),
            "interactive": True,
        }

    def bar_chart(
        self,
        x_data: List[str],
        y_data: Union[List[float], Dict[str, List[float]]],
        filename: str = "bar_chart",
    ) -> Dict[str, Any]:
        """Plotly柱状图"""
        import plotly.graph_objects as go

        fig = go.Figure()

        if isinstance(y_data, dict):
            colors = self._get_colors(len(y_data))
            for i, (label, values) in enumerate(y_data.items()):
                fig.add_trace(go.Bar(x=x_data, y=values, name=label, marker_color=colors[i]))
        else:
            fig.add_trace(go.Bar(x=x_data, y=y_data, name="data", marker_color=self._get_colors(1)[0]))

        self._create_layout(fig)
        fig.update_layout(barmode="group" if isinstance(y_data, dict) else "relative")

        html_path = Path(filename).parent / f"{filename}.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)

        fig.write_html(str(html_path))

        return {
            "success": True,
            "type": "bar_chart",
            "filename": filename,
            "html_path": str(html_path),
            "interactive": True,
        }

    def scatter_plot(
        self,
        x_data: List[float],
        y_data: List[float],
        labels: Optional[List[str]] = None,
        sizes: Optional[List[float]] = None,
        filename: str = "scatter",
    ) -> Dict[str, Any]:
        """Plotly散点图"""
        import plotly.graph_objects as go

        fig = go.Figure()

        default_size = 10
        point_sizes = sizes if sizes is not None else [default_size] * len(x_data)

        fig.add_trace(go.Scatter(
            x=x_data,
            y=y_data,
            mode="markers",
            text=labels,
            marker=dict(size=point_sizes, color=self._get_colors(1)[0], opacity=0.6, line=dict(width=1, color="white")),
        ))

        self._create_layout(fig)

        html_path = Path(filename).parent / f"{filename}.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)

        fig.write_html(str(html_path))

        return {
            "success": True,
            "type": "scatter",
            "filename": filename,
            "html_path": str(html_path),
            "interactive": True,
        }

    def heatmap(
        self,
        data: List[List[float]],
        x_labels: Optional[List[str]] = None,
        y_labels: Optional[List[str]] = None,
        filename: str = "heatmap",
    ) -> Dict[str, Any]:
        """Plotly热力图"""
        import plotly.graph_objects as go

        fig = go.Figure(data=go.Heatmap(
            z=data,
            x=x_labels,
            y=y_labels,
            colorscale="RdBu_r",
            colorbar=dict(title=self.config.ylabel),
        ))

        self._create_layout(fig)

        html_path = Path(filename).parent / f"{filename}.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)

        fig.write_html(str(html_path))

        return {
            "success": True,
            "type": "heatmap",
            "filename": filename,
            "html_path": str(html_path),
            "interactive": True,
        }

    def box_plot(
        self,
        data: Dict[str, List[float]],
        filename: str = "box_plot",
    ) -> Dict[str, Any]:
        """箱线图"""
        import plotly.graph_objects as go

        fig = go.Figure()

        colors = self._get_colors(len(data))
        for i, (label, values) in enumerate(data.items()):
            fig.add_trace(go.Box(y=values, name=label, marker_color=colors[i], boxpoints="outliers"))

        self._create_layout(fig)

        html_path = Path(filename).parent / f"{filename}.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)

        fig.write_html(str(html_path))

        return {
            "success": True,
            "type": "box_plot",
            "filename": filename,
            "html_path": str(html_path),
            "interactive": True,
        }

    def violin_plot(
        self,
        data: Dict[str, List[float]],
        filename: str = "violin_plot",
    ) -> Dict[str, Any]:
        """小提琴图"""
        import plotly.graph_objects as go

        fig = go.Figure()

        colors = self._get_colors(len(data))
        for i, (label, values) in enumerate(data.items()):
            fig.add_trace(go.Violin(y=values, name=label, marker_color=colors[i], box_visible=True, meanline_visible=True))

        self._create_layout(fig)

        html_path = Path(filename).parent / f"{filename}.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)

        fig.write_html(str(html_path))

        return {
            "success": True,
            "type": "violin_plot",
            "filename": filename,
            "html_path": str(html_path),
            "interactive": True,
        }


class EnhancedChartGenerator:
    """
    增强图表生成器

    同时支持Matplotlib (静态) 和 Plotly (交互式)
    """

    def __init__(self, output_dir: str = "./charts"):
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    def create_chart(
        self,
        chart_type: str,
        data: Dict[str, Any],
        interactive: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        创建图表

        Args:
            chart_type: 图表类型 (line, bar, scatter, heatmap, box, violin)
            data: 图表数据
            interactive: 是否创建交互式图表 (Plotly)
            **kwargs: 额外参数

        Returns:
            包含图表路径的字典
        """
        if interactive:
            return self._create_plotly_chart(chart_type, data, **kwargs)
        else:
            return self._create_matplotlib_chart(chart_type, data, **kwargs)

    def _create_matplotlib_chart(
        self,
        chart_type: str,
        data: Dict[str, Any],
        **kwargs,
    ) -> Dict[str, Any]:
        """使用Matplotlib创建图表"""
        config = ChartConfig(
            title=data.get("title", ""),
            xlabel=data.get("xlabel", ""),
            ylabel=data.get("ylabel", ""),
            output_dir=self.output_dir,
            **kwargs,
        )

        maker = MatplotlibChartMaker(config)

        x_data = data.get("x", range(len(data.get("y", []))))
        y_data = data.get("y", {})
        filename = data.get("filename", f"{chart_type}_chart")

        if chart_type == "line":
            return maker.line_chart(x_data, y_data, filename)
        elif chart_type == "bar":
            return maker.bar_chart(x_data, y_data, filename)
        elif chart_type == "scatter":
            return maker.scatter_plot(
                x_data if isinstance(x_data, list) else list(x_data),
                y_data if isinstance(y_data, list) else list(y_data.values())[0] if isinstance(y_data, dict) else [],
                data.get("labels"),
                data.get("sizes"),
                filename,
            )
        elif chart_type == "heatmap":
            return maker.heatmap(
                data.get("data"),
                data.get("x_labels"),
                data.get("y_labels"),
                filename,
            )
        else:
            return {"success": False, "error": f"Unsupported chart type: {chart_type}"}

    def _create_plotly_chart(
        self,
        chart_type: str,
        data: Dict[str, Any],
        **kwargs,
    ) -> Dict[str, Any]:
        """使用Plotly创建图表"""
        config = PlotlyConfig(
            title=data.get("title", ""),
            xlabel=data.get("xlabel", ""),
            ylabel=data.get("ylabel", ""),
        )

        maker = PlotlyChartMaker(config)

        x_data = data.get("x", range(len(data.get("y", []))))
        y_data = data.get("y", {})
        filename = data.get("filename", f"{chart_type}_chart")

        if chart_type == "line":
            return maker.line_chart(x_data, y_data, filename)
        elif chart_type == "bar":
            return maker.bar_chart(x_data, y_data, filename)
        elif chart_type == "scatter":
            return maker.scatter_plot(
                x_data if isinstance(x_data, list) else list(x_data),
                y_data if isinstance(y_data, list) else list(y_data.values())[0] if isinstance(y_data, dict) else [],
                data.get("labels"),
                data.get("sizes"),
                filename,
            )
        elif chart_type == "heatmap":
            return maker.heatmap(
                data.get("data"),
                data.get("x_labels"),
                data.get("y_labels"),
                filename,
            )
        elif chart_type == "box":
            return maker.box_plot(y_data if isinstance(y_data, dict) else {"data": y_data}, filename)
        elif chart_type == "violin":
            return maker.violin_plot(y_data if isinstance(y_data, dict) else {"data": y_data}, filename)
        else:
            return {"success": False, "error": f"Unsupported chart type: {chart_type}"}

    def create_multi_panel(
        self,
        panels: List[Dict[str, Any]],
        filename: str = "multi_panel",
        interactive: bool = False,
        nrows: int = 1,
        ncols: int = 2,
    ) -> Dict[str, Any]:
        """创建多面板图表"""
        import matplotlib.pyplot as plt

        config = ChartConfig(output_dir=self.output_dir)
        config.apply_matplotlib_style()

        fig, axes = plt.subplots(nrows, ncols, figsize=(config.figsize[0] * ncols, config.figsize[1] * nrows))
        if nrows * ncols == 1:
            axes = [axes]
        else:
            axes = axes.flatten()

        colors = PAPER_COLORS

        for i, panel in enumerate(panels):
            if i >= len(axes):
                break

            ax = axes[i]
            panel_type = panel.get("type", "line")
            panel_data = panel.get("data", {})
            xlabel = panel.get("xlabel", "")
            ylabel = panel.get("ylabel", "")

            if panel_type == "line":
                y = panel_data.get("y", [])
                x = panel_data.get("x", range(len(y)))
                ax.plot(x, y, color=colors[i % len(colors)], linewidth=1.5, marker="o", markersize=3)

            elif panel_type == "bar":
                x = panel_data.get("x", range(len(panel_data.get("y", []))))
                y = panel_data.get("y", [])
                ax.bar(x, y, color=colors[i % len(colors)])

            elif panel_type == "scatter":
                x = panel_data.get("x", [])
                y = panel_data.get("y", [])
                ax.scatter(x, y, s=30, color=colors[i % len(colors)], alpha=0.6)

            ax.set_xlabel(xlabel, fontsize=8)
            ax.set_ylabel(ylabel, fontsize=8)
            ax.grid(True, linestyle="--", alpha=0.3)

            if panel.get("title"):
                ax.set_title(panel["title"], fontsize=10, fontweight="bold")

        for j in range(len(panels), len(axes)):
            axes[j].set_visible(False)

        paths = {}
        for fmt in ["png", "pdf"]:
            filepath = Path(self.output_dir) / f"{filename}.{fmt}"
            fig.savefig(filepath, format=fmt, dpi=config.dpi, bbox_inches="tight")
            paths[fmt] = str(filepath)

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
def create_chart(
    chart_type: str,
    data: Dict[str, Any],
    interactive: bool = False,
    output_dir: str = "./charts",
) -> Dict[str, Any]:
    """创建图表"""
    generator = EnhancedChartGenerator(output_dir)
    return generator.create_chart(chart_type, data, interactive)


def create_line_chart(
    x_data: List[Any],
    y_data: Union[List[float], Dict[str, List[float]]],
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    filename: str = "line_chart",
    interactive: bool = False,
) -> Dict[str, Any]:
    """创建折线图"""
    data = {"x": x_data, "y": y_data, "title": title, "xlabel": xlabel, "ylabel": ylabel, "filename": filename}
    return create_chart("line", data, interactive)


def create_bar_chart(
    x_data: List[str],
    y_data: Union[List[float], Dict[str, List[float]]],
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    filename: str = "bar_chart",
    interactive: bool = False,
) -> Dict[str, Any]:
    """创建柱状图"""
    data = {"x": x_data, "y": y_data, "title": title, "xlabel": xlabel, "ylabel": ylabel, "filename": filename}
    return create_chart("bar", data, interactive)


def create_heatmap(
    data: List[List[float]],
    x_labels: Optional[List[str]] = None,
    y_labels: Optional[List[str]] = None,
    title: str = "",
    filename: str = "heatmap",
    interactive: bool = False,
) -> Dict[str, Any]:
    """创建热力图"""
    chart_data = {"data": data, "x_labels": x_labels, "y_labels": y_labels, "title": title, "filename": filename}
    return create_chart("heatmap", chart_data, interactive)


def get_tool_spec():
    """获取工具规格"""
    from .tool_spec import ToolSpec, ParameterSpec, ParameterType

    return ToolSpec(
        name="generate_interactive_chart",
        description="生成交互式图表 (Matplotlib静态图 + Plotly交互式HTML)",
        parameters=[
            ParameterSpec(
                name="chart_type",
                description="图表类型: line, bar, scatter, heatmap, box, violin",
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
                name="interactive",
                description="是否生成交互式图表 (Plotly HTML)",
                type=ParameterType.BOOLEAN,
                required=False,
                default=False,
            ),
        ],
        handler=create_chart,
        category="visualization",
    )
