# -*- coding: utf-8 -*-
"""统一的可视化样式：调色板、字体、坐标轴与 Plotly 布局。

调色板来自 dataviz 参考实例（已通过色盲/对比度校验的 8 色分类色板）：
    蓝 #2a78d6 / 橙 #eb6834 / 青 #1baf7a / 黄 #eda100
    品红 #e87ba4 / 绿 #008300 / 紫 #6250d6 / 红 #e34948

顺序固定，不循环生成新色；超过 8 类时折叠为“其他”。
顺序色阶为单一蓝色（浅 -> 深），用于热力图/连续量。
"""
from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

# ---- 画布与文字 ----
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

# ---- 分类色（固定顺序）----
CATEGORICAL = [
    "#2a78d6",  # 1 blue
    "#eb6834",  # 2 orange
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 yellow
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 green
    "#6250d6",  # 7 violet
    "#e34948",  # 8 red
]
BLUE = CATEGORICAL[0]
ORANGE = CATEGORICAL[1]
AQUA = CATEGORICAL[2]
YELLOW = CATEGORICAL[3]
BLUE_DARK = "#184f95"

# ---- 顺序蓝色阶（dataviz 参考实例）----
SEQUENTIAL_BLUE = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef",
    "#6da7ec", "#5598e7", "#3987e5", "#2a78d6",
    "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b",
]
BLUE_CMAP = LinearSegmentedColormap.from_list("olist_blue", SEQUENTIAL_BLUE)


def pick_font() -> str:
    installed = {font.name for font in font_manager.fontManager.ttflist}
    for name in ["Microsoft YaHei", "微软雅黑", "SimHei", "DengXian", "Noto Sans CJK SC"]:
        if name in installed:
            return name
    return "DejaVu Sans"


def setup_matplotlib() -> str:
    """设置 matplotlib 全局样式；返回实际使用的中文字体名。"""
    font = pick_font()
    matplotlib.rcParams.update({
        "font.family": font,
        "axes.unicode_minus": False,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": BASELINE,
        "axes.labelcolor": SECONDARY,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "text.color": INK,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "grid.linestyle": "-",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 200,
        "savefig.dpi": 200,
        "font.size": 10,
    })
    return font


def style_axes(ax, grid_axis: str = "y"):
    """去掉上/右框线，保留一条基准线，网格保持细实线。"""
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8, linestyle="-")
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.spines["left"].set_color(BASELINE)
    return ax


def title_block(ax, title: str, subtitle: str | None = None) -> None:
    """左对齐标题 + 可选副标题（副标题位于标题下方）。"""
    pad = 22 if subtitle else 10
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", color=INK, pad=pad)
    if subtitle:
        ax.text(
            0.0, 1.015, subtitle, transform=ax.transAxes,
            fontsize=9, color=SECONDARY, va="bottom", ha="left",
        )


def source_note(fig, text: str) -> None:
    fig.text(0.008, 0.008, text, fontsize=7, color=MUTED, ha="left", va="bottom")


def brl_wan(value: float, _pos=None) -> str:
    """金额轴：以“万”为单位。"""
    if abs(value) >= 1e8:
        return f"R${value / 1e8:.1f}亿"
    if abs(value) >= 1e4:
        return f"R${value / 1e4:.0f}万"
    return f"R${value:.0f}"


def pct(value: float, _pos=None) -> str:
    return f"{value * 100:.0f}%"


# ---- Plotly 统一布局 ----
def plotly_layout(fig, title: str | None = None, height: int = 360):
    fig.update_layout(
        template="plotly_white",
        colorway=CATEGORICAL,
        font=dict(family="Microsoft YaHei, Segoe UI, Arial", color=INK, size=12),
        title=dict(
            text=title, x=0, xanchor="left",
            font=dict(size=16, color=INK),
        ) if title else None,
        margin=dict(l=8, r=8, t=56 if title else 16, b=8),
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1, font=dict(color=SECONDARY, size=11),
        ),
        hoverlabel=dict(bgcolor="#ffffff", font=dict(color=INK)),
    )
    fig.update_xaxes(showgrid=False, linecolor=BASELINE, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(color=MUTED))
    return fig
