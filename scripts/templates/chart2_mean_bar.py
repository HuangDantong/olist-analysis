# -*- coding: utf-8 -*-
"""
图表复刻 2/15 —— 带均值柱形图

复刻对象：`第二章 图表(前15).xlsx` 工作表「2 带均值柱形图」中的图表。

这是一个「柱形图 + 折线图」的组合图：
  * 柱形系列「销售量」——纯色填充 0070C0
  * 折线系列「均值」——一条黄色水平线 FFC000，表示六个区域的平均销量

数据来源：
  '2 带均值柱形图'!$B$3:$B$8    区域
  '2 带均值柱形图'!$C$3:$C$8    销售量
  '2 带均值柱形图'!$D$3:$D$8    均值 = AVERAGE($C$3:$C$8) = 2656.1666...

样式规格全部取自该 xlsx 的图表 XML（xl/charts/chart2.xml、
xl/drawings/drawing4.xml）：

    图表区背景      srgbClr 1A1E43
    绘图区          manualLayout x=0.058831 y=0.234382 w=0.904665 h=0.599871
    柱形系列        纯色 0070C0，gapWidth=219%（柱宽 = 类别宽 / 3.19）
    折线系列        0070C0 之外的 FFC000，线宽 19050EMU = 1.5pt，无标记点
    数值轴          delete="1" —— 整条数值轴被删除，既无标签也无网格线
    类别轴          轴线 bg1 lumMod 95% alpha 50%，粗 0.75pt；标签 #F2F2F2 9pt
    数据标签        dLblPos="outEnd"，9pt，#F2F2F2
                    其中第 6 个点（华东）被手工拖到了均值线下方，见 MOVED_LABEL
    标题/副标题     微软雅黑 20pt 加粗 / 14pt，白色，行距 24pt
    脚注            微软雅黑 8pt，#D9D9D9
    均值标注        「平均值：2656」微软雅黑 8pt，#FFC000

运行：python chart2_mean_bar.py
输出：chart2_mean_bar.png（832 x 594，与 Excel 导出图等比同尺寸）
"""

import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

# --------------------------------------------------------------------------
# 常量
# --------------------------------------------------------------------------

# Excel 图表对象尺寸 416 x 296.875 pt，按 2 px/pt 导出
DPI = 100
FIG_W_PX, FIG_H_PX = 832, 594

# 字号换算：画布是 Excel 图表的 1.44 倍（= 2 * 72 / 100）
FONT_SCALE = 2 * 72 / DPI  # 1.44

BACKGROUND = "#1A1E43"
BAR_COLOR = "#0070C0"
MEAN_LINE_COLOR = "#FFC000"
LABEL_COLOR = "#F2F2F2"
FOOTNOTE_COLOR = "#D9D9D9"

REGIONS = ["华北", "华南", "东北", "西北", "西南", "华东"]
SALES = [2354, 1902, 3524, 2698, 2896, 2563]
MEAN = float(np.mean(SALES))  # 2656.1666...，与表里 D 列的 AVERAGE 一致

TITLE = "3月各区域销量分布"
SUBTITLE = "东北销量最多占比总销量的22%，华南销量最低"
FOOTNOTE = " *注：数据来源于公司销售系统，统计日期截至2022.03.31"
MEAN_LABEL = "平均值：{:.0f}".format(MEAN)

# 绘图区在图表中的相对位置（取自 chart2.xml 的 manualLayout）
AXES_LEFT = 0.058831442025629149
AXES_TOP_NOMINAL = 0.23438164632405159
AXES_WIDTH = 0.90466463398940655
AXES_HEIGHT = 0.59987055911086651

# manualLayout 存的是小数坐标，Excel 渲染时会取整到设备像素，实际画出来的
# 绘图区比标注值高半个像素。实测上移 0.5px 后与原图贴合得最好
# （绘图区误差 8.21 -> 5.93），所以这里做半个像素的修正。
AXES_TOP = AXES_TOP_NOMINAL - 0.5 / FIG_H_PX

BAR_WIDTH = 1.0 / (1.0 + 219.0 / 100.0)  # gapWidth = 219%
Y_MAX = 4000  # 数值轴被隐藏，范围由 Excel 自动取整得到 0~4000

# 原图作者手工拖动过的数据标签：{类别序号: (相对柱心的 x 偏移, 标签基线 y)}
# 华东那根柱子的顶端是 267，而均值线压到 258，默认位置会与线重叠，
# 所以被拖到了线下方（272~281）。这里照原样还原。
MOVED_LABEL = {5: (2.5, 282.25)}
DEFAULT_LABEL_GAP = 14.1  # 其余标签基线在柱顶上方约 14px


def _pick_font(candidates, fallback="DejaVu Sans"):
    """返回第一个已安装的字体名。"""
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in installed:
            return name
    return fallback


UI_FONT = _pick_font(["Microsoft YaHei", "微软雅黑", "SimHei", "DengXian"])
AXIS_FONTS = [_pick_font(["Calibri"]),
              _pick_font(["DengXian", "等线", "SimSun", "Microsoft YaHei"])]

plt.rcParams["axes.unicode_minus"] = False


def main():
    figure = plt.figure(figsize=(FIG_W_PX / DPI, FIG_H_PX / DPI), dpi=DPI)
    figure.patch.set_facecolor(BACKGROUND)

    axis = figure.add_axes([AXES_LEFT,
                            1.0 - AXES_TOP - AXES_HEIGHT,
                            AXES_WIDTH,
                            AXES_HEIGHT])
    axis.set_facecolor(BACKGROUND)

    positions = np.arange(len(REGIONS))

    # ---- 柱形系列：纯色填充（注意不是渐变，这是与图1的主要差别）----
    axis.bar(positions, SALES, width=BAR_WIDTH,
             color=BAR_COLOR, edgecolor="none", zorder=2)

    # ---- 折线系列：一条横贯所有类别的均值线 ----
    # 线只连接各个数据点，所以横向正好从第一根柱心到最后一根柱心
    axis.plot([positions[0], positions[-1]], [MEAN, MEAN],
              color=MEAN_LINE_COLOR, linewidth=1.5 * FONT_SCALE,
              solid_capstyle="round", zorder=4, clip_on=False)

    # ---- 坐标轴 ----
    axis.set_xlim(-0.5, len(REGIONS) - 0.5)
    axis.set_ylim(0, Y_MAX)

    # 数值轴在 XML 里是 delete="1"，整个隐藏：不要刻度、不要网格线
    axis.set_yticks([])
    axis.grid(False)

    axis.set_xticks(positions)
    axis.set_xticklabels(REGIONS, color=LABEL_COLOR,
                         fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS)
    axis.tick_params(axis="x", length=0, pad=10.5)

    # 只保留类别轴线（底部脊线），颜色 bg1 lumMod 95% alpha 50%
    for name, spine in axis.spines.items():
        spine.set_visible(name == "bottom")
    axis.spines["bottom"].set_color(LABEL_COLOR)
    axis.spines["bottom"].set_alpha(0.5)
    axis.spines["bottom"].set_linewidth(0.75 * FONT_SCALE)

    # ---- 数据标签 ----
    for index, (position, value) in enumerate(zip(positions, SALES)):
        if index in MOVED_LABEL:
            dx, baseline_y = MOVED_LABEL[index]
            # 换算成 figure 坐标，柱心 x 是 0 号类别处 +index 个类别宽
            category_px = AXES_WIDTH * FIG_W_PX / len(REGIONS)
            x = (AXES_LEFT * FIG_W_PX + (index + 0.5) * category_px + dx) / FIG_W_PX
            figure.text(x, 1.0 - baseline_y / FIG_H_PX, str(value),
                        ha="center", va="baseline", color=LABEL_COLOR,
                        fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS)
        else:
            axis.annotate(str(value), xy=(position, value),
                          xytext=(0, DEFAULT_LABEL_GAP * 72 / DPI),
                          textcoords="offset points",
                          ha="center", va="baseline", color=LABEL_COLOR,
                          fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS,
                          zorder=5)

    # ---- 标题 / 副标题 / 脚注 / 均值标注 ----
    figure.text(55.15 / FIG_W_PX, 1.0 - 67.0 / FIG_H_PX, TITLE,
                ha="left", va="baseline", color="white",
                fontsize=20 * FONT_SCALE, fontweight="bold", fontfamily=UI_FONT)
    figure.text(55.15 / FIG_W_PX, 1.0 - 115.5 / FIG_H_PX, SUBTITLE,
                ha="left", va="baseline", color="white",
                fontsize=14 * FONT_SCALE, fontfamily=UI_FONT)
    figure.text(45.8 / FIG_W_PX, 1.0 - 570.0 / FIG_H_PX, FOOTNOTE,
                ha="left", va="baseline", color=FOOTNOTE_COLOR,
                fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)
    figure.text(674.6 / FIG_W_PX, 1.0 - 243.5 / FIG_H_PX, MEAN_LABEL,
                ha="left", va="baseline", color=MEAN_LINE_COLOR,
                fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)

    output = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "chart2_mean_bar.png")
    figure.savefig(output, dpi=200, facecolor=BACKGROUND)
    print("saved:", output)
    return figure


if __name__ == "__main__":
    if matplotlib.get_backend().lower() == "agg":
        main()
    else:
        main()
        plt.show()
