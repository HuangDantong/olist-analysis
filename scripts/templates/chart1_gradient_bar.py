# -*- coding: utf-8 -*-
"""
图表复刻 1/15 —— 渐变柱形图

复刻对象：`第二章 图表(前15).xlsx` 工作表「1 渐变柱形图」中的图表。
原始图表由 Excel 生成，本脚本用 matplotlib 逐像素还原其外观。

数据来源：'1 渐变柱形图'!$B$3:$C$8

样式规格全部取自该 xlsx 的图表 XML（xl/charts/chart1.xml、
xl/drawings/drawing2.xml），关键参数如下：

    图表区背景          srgbClr 1A1E43
    绘图区              manualLayout x=0.143995 y=0.318858 w=0.760232 h=0.525407
    柱形渐变            gradFill 线性 ang=5400000（自上而下）
                        pos=0     0070C0
                        pos=100000 00B0F0
    柱宽/间距           gapWidth=219%  ->  柱宽 = 类别宽 / 3.19
    数值轴              majorUnit=1000，范围 0~4000，标签色 bg1 lumMod 95% (#F2F2F2)
    网格线              tx1 lumMod 15% lumOff 85% alpha 20%（即 #D9D9D9 @ 20%）
                        线宽 9525EMU = 0.75pt，prstDash="lgDash"
    数据标签            dLblPos="outEnd"，showVal=1，9pt，白色
    坐标轴标签          9pt
    标题                微软雅黑 20pt 加粗 白色，行距 24pt
    副标题              微软雅黑 14pt 白色，行距 24pt
    脚注                微软雅黑 8pt，bg1 lumMod 85% (#D9D9D9)

坐标轴/数据标签的 Latin 字体继承主题 (+mn-lt = Calibri)，中日韩字形
继承工作簿默认字体（等线 / DengXian）。

运行：python chart1_gradient_bar.py
输出：chart1_gradient_bar.png（832 x 617，与 Excel 导出图等比同尺寸）
"""

import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.transforms import ScaledTranslation

# --------------------------------------------------------------------------
# 常量：全部按 Excel 图表的原始定义换算
# --------------------------------------------------------------------------

# Excel 图表对象尺寸 416 x 308.75 pt；此处按 2 px/pt 导出，
# 因此画布取 832 x 617 px，1 个参考像素 = 1 个输出像素。
DPI = 100
FIG_W_PX, FIG_H_PX = 832, 617

# 字号换算：画布尺寸是 Excel 图表的 1.44 倍（= 2 * 72 / 100），
# 所以 matplotlib 字号 = Excel 字号 * 1.44。
FONT_SCALE = 2 * 72 / DPI  # 1.44

BACKGROUND = "#1A1E43"
BAR_GRADIENT = ("#0070C0", "#00B0F0")  # 顶部 -> 底部
GRID_COLOR = "#D9D9D9"
GRID_ALPHA = 0.20
VALUE_LABEL_COLOR = "#F2F2F2"
FOOTNOTE_COLOR = "#D9D9D9"

REGIONS = ["华北", "华南", "东北", "西北", "西南", "华东"]
SALES = [2354, 1902, 3524, 2698, 2896, 2563]

TITLE = "3月各区域销量分布"
SUBTITLE = "东北销量最多占比总销量的22%，华南销量最低"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.03.31"

# 绘图区在图表中的相对位置（取自 chart1.xml 的 manualLayout）
AXES_LEFT = 0.14399451906746949
AXES_WIDTH = 0.7602323606607998
AXES_TOP = 0.31885801039575934
AXES_HEIGHT = 0.5254068241469817

# gapWidth=219%：柱宽占类别宽的比例为 1 / (1 + 2.19)
BAR_WIDTH = 1.0 / (1.0 + 219.0 / 100.0)

Y_MAX = 4000
Y_TICKS = [0, 1000, 2000, 3000, 4000]


def _pick_font(candidates, fallback="DejaVu Sans"):
    """返回第一个已安装的字体名，用于在缺少中文字体的机器上仍可运行。"""
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in installed:
            return name
    return fallback


# 标题/副标题/脚注在 XML 中显式指定了「微软雅黑」
UI_FONT = _pick_font(["Microsoft YaHei", "微软雅黑", "SimHei", "DengXian"])
# 坐标轴与数据标签：Latin 用 Calibri，中文回退到等线（工作簿默认字体）
AXIS_FONT = _pick_font(["Calibri"])
AXIS_CJK_FONT = _pick_font(["DengXian", "等线", "SimSun", "Microsoft YaHei"])
AXIS_FONTS = [AXIS_FONT, AXIS_CJK_FONT]  # matplotlib 逐字符回退

plt.rcParams["axes.unicode_minus"] = False
# 网格线虚线按 XML 的实测长度给定，不再乘线宽
plt.rcParams["lines.scale_dashes"] = False


def draw_gradient_bars(axis, positions, values):
    """绘制带线性渐变填充的柱形。

    Excel 的渐变作用在单个柱子上（每根柱子的渐变都铺满自身高度），
    因此逐柱贴一张渐变位图，并用柱子自身作为裁剪路径。
    """
    cmap = LinearSegmentedColormap.from_list("bar_gradient", BAR_GRADIENT)
    # 第一行对应 extent 顶部 —— origin='upper'，故 0 在顶、1 在底。
    ramp = np.linspace(0.0, 1.0, 256).reshape(-1, 1)

    bars = axis.bar(
        positions,
        values,
        width=BAR_WIDTH,
        facecolor="none",
        edgecolor="none",
        zorder=2,
    )

    for bar in bars:
        left = bar.get_x()
        right = left + bar.get_width()
        axis.imshow(
            ramp,
            extent=(left, right, 0, bar.get_height()),
            cmap=cmap,
            origin="upper",
            aspect="auto",
            interpolation="bilinear",
            clip_path=bar,
            clip_on=True,
            zorder=2,
        )


def main():
    figure = plt.figure(figsize=(FIG_W_PX / DPI, FIG_H_PX / DPI), dpi=DPI)
    figure.patch.set_facecolor(BACKGROUND)

    axis = figure.add_axes(
        [
            AXES_LEFT,
            1.0 - AXES_TOP - AXES_HEIGHT,
            AXES_WIDTH,
            AXES_HEIGHT,
        ]
    )
    axis.set_facecolor(BACKGROUND)

    positions = np.arange(len(REGIONS))
    draw_gradient_bars(axis, positions, SALES)

    # 坐标范围：每个类别占 1 格，两侧各留半格
    axis.set_xlim(-0.5, len(REGIONS) - 0.5)
    axis.set_ylim(0, Y_MAX)

    # ---- 坐标轴 ----
    axis.set_axisbelow(True)
    axis.grid(
        axis="y",
        color=GRID_COLOR,
        alpha=GRID_ALPHA,
        linewidth=0.75 * FONT_SCALE,          # 9525 EMU = 0.75pt -> 1.08pt
        linestyle=(0, (11.52, 4.32)),         # prstDash="lgDash"，按导出图实测
        zorder=0,
    )

    axis.set_xticks(positions)
    axis.set_xticklabels(
        REGIONS,
        color="white",
        fontsize=9 * FONT_SCALE,
        fontfamily=AXIS_FONTS,
    )
    axis.set_yticks(Y_TICKS)
    axis.set_yticklabels(
        [str(v) for v in Y_TICKS],
        color=VALUE_LABEL_COLOR,
        fontsize=9 * FONT_SCALE,
        fontfamily=AXIS_FONTS,
    )

    axis.tick_params(axis="x", length=0, pad=11.2)   # 柱底到类别文字 15.5px
    axis.tick_params(axis="y", length=0, pad=12.1)   # 绘图区左缘到数字 17.8px

    # Excel 把刻度文字按行框垂直居中，matplotlib 按墨迹包围盒居中，
    # 两者相差约 1.5px，这里补一个竖直微调。
    shift = ScaledTranslation(0, 1.5 / DPI, figure.dpi_scale_trans)
    for label in axis.get_yticklabels():
        label.set_transform(label.get_transform() + shift)

    for spine in axis.spines.values():
        spine.set_visible(False)

    # ---- 数据标签：位于柱顶上方，基线距柱顶 15px ----
    for position, value in zip(positions, SALES):
        axis.annotate(
            str(value),
            xy=(position, value),
            xytext=(0, 15 * 72 / DPI),
            textcoords="offset points",
            ha="center",
            va="baseline",
            color="white",
            fontsize=9 * FONT_SCALE,
            fontfamily=AXIS_FONTS,
            zorder=3,
        )

    # ---- 文本：按 XML 中文本框位置与基线对齐 ----
    figure.text(
        0.07770,
        1.0 - 80.0 / FIG_H_PX,
        TITLE,
        ha="left",
        va="baseline",
        color="white",
        fontsize=20 * FONT_SCALE,
        fontweight="bold",
        fontfamily=UI_FONT,
    )
    figure.text(
        0.07770,
        1.0 - 128.5 / FIG_H_PX,
        SUBTITLE,
        ha="left",
        va="baseline",
        color="white",
        fontsize=14 * FONT_SCALE,
        fontfamily=UI_FONT,
    )
    figure.text(
        0.05847,
        1.0 - 592.0 / FIG_H_PX,
        FOOTNOTE,
        ha="left",
        va="baseline",
        color=FOOTNOTE_COLOR,
        fontsize=8 * FONT_SCALE,
        fontfamily=UI_FONT,
    )

    output = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "chart1_gradient_bar.png")
    figure.savefig(output, dpi=200, facecolor=BACKGROUND)
    print("saved:", output)
    return figure


if __name__ == "__main__":
    if matplotlib.get_backend().lower() == "agg":
        main()
    else:
        main()
        plt.show()
