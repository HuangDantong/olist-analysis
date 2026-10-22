# -*- coding: utf-8 -*-
"""
图表复刻 6/15 —— 蝴蝶图（tornado chart）

复刻对象：`第二章 图表(前15).xlsx` 工作表「6 蝴蝶图」中的图表。

这其实是一张**横向堆积条形图**（barDir="bar" + grouping="stacked"），
靠两条"隐形占位系列"把可见的柱子推到左右两侧，做出"从中间向两侧生长"的效果：

    系列0  占位1     noFill（完全透明）  —— 把 2022 年柱推到右侧对齐
    系列1  2022年销量 0070C0（蓝）        —— 可见，左半边
    系列2  占位2     noFill（完全透明）  —— 中间那条"空白带"，类别名就写在这里
    系列3  2021年销量 E74E69（红）        —— 可见，右半边

关键机关（数据见 xl/charts/chart6.xml 的 numCache）：

  * 占位1 是镜像公式 =$D$3+$D$7-$D$3 ... 即 3453-$D_i（3453 = 2022 年最大值 2238
    + 最小值 1215）。于是 占位1+2022 = 3453 恒等，五根蓝柱的**右端全部对齐**在
    x=3453，左端参差不齐 —— 这就是"向左生长"的观感。
  * 占位2 五格恒为 1215，把 3453~4668 这段做成固定宽的空白，类别名（华南/华北/…）
    就是这一系列的数据标签（dLblPos="ctr"，标签内容取自 B3:B7 的类别名）。
  * 系列3 从 4668 起画，所以五根红柱**左端全部对齐**在 x=4668，右端参差不齐。

数据来源：
  '6 蝴蝶图'!$B$3:$B$7    类别  华东/西北/东北/华北/华南（图中从下往上排）
  '6 蝴蝶图'!$C$3:$C$7    占位1 2238/2132/2027/1922/1215
  '6 蝴蝶图'!$D$3:$D$7    2022年销量 1215/1321/1426/1531/2238
  '6 蝴蝶图'!$E$3:$E$7    占位2 恒 1215
  '6 蝴蝶图'!$F$3:$F$7    2021年销量 1003/1265/1531/1436/2066

样式规格全部取自该 xlsx 的图表 XML（xl/charts/chart6.xml、xl/drawings/drawing12.xml）：

    图表区背景      srgbClr 1A1E43
    绘图区          manualLayout x=0.034313725 y=0.284856169 w=0.946078431 h=0.598455761
    gapWidth=150    → 条宽 = 类别带宽 / 2.5（实测 70.38px 带宽 → 28.1px 条宽）
    overlap=100     → 同一类别内各系列首尾相接
    2022 系列       纯色 0070C0，标签 dLblPos="inBase"（贴在条子起点一侧，即左侧）
                    9pt，bg1 lumMod 95% = #F2F2F2
    2021 系列       纯色 E74E69，标签 dLblPos="inEnd"（贴在条子终点一侧，即右侧）
                    9pt，bg1 lumMod 85% = #D9D9D9
    占位2 的标签    dLblPos="ctr"，内容为类别名，9pt，#F2F2F2
    两条坐标轴      catAx 与 valAx 全部 delete="1" —— 无轴线、无刻度、无网格线
    数值轴范围      0~8000（轴被删除，但刻度仍是 Excel 自动取整的 8000；
                    由柱宽实测 10.18 值/px 反推得到）
    标题            微软雅黑 18pt 加粗，白色，单行
    副标题          微软雅黑 11pt，白色
    图例标题框      「2022」0070C0 /「2021」F94C66，微软雅黑 11pt，
                    是 userShapes 里的一个独立文本框（不是图表图例）
    脚注            微软雅黑 8pt，#D9D9D9

运行：python chart6_butterfly.py
输出：chart6_butterfly.png（832 x 588，与 Excel 导出图完全同尺寸）
"""

import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

# --------------------------------------------------------------------------
# 常量
# --------------------------------------------------------------------------

DPI = 100
FIG_W_PX, FIG_H_PX = 832, 588

# 字号换算：Excel 图表按 2px/pt 导出，matplotlib dpi=100 时 1pt = 100/72 px
FONT_SCALE = 2 * 72 / DPI  # 1.44

BACKGROUND = "#1A1E43"
COLOR_2022 = "#0070C0"        # 系列1 填充
COLOR_2021 = "#E74E69"        # 系列3 填充
LABEL_COLOR_2022 = "#F2F2F2"  # bg1 lumMod 95%
LABEL_COLOR_2021 = "#D9D9D9"  # bg1 lumMod 85%
CATEGORY_COLOR = "#F2F2F2"
FOOTNOTE_COLOR = "#D9D9D9"
HEADER_2022_COLOR = "#0070C0"
HEADER_2021_COLOR = "#F94C66"

# 类别（barDir="bar" 时第一个类别在最下方，与参考图一致）
CATEGORIES = ["华东", "西北", "东北", "华北", "华南"]

PLACEHOLDER_1 = [2238, 2132, 2027, 1922, 1215]      # '6 蝴蝶图'!C3:C7，透明
SALES_2022 = [1215, 1321, 1426, 1531, 2238]         # '6 蝴蝶图'!D3:D7
PLACEHOLDER_2 = [1215, 1215, 1215, 1215, 1215]      # '6 蝴蝶图'!E3:E7，透明
SALES_2021 = [1003, 1265, 1531, 1436, 2066]         # '6 蝴蝶图'!F3:F7

# 堆积偏移：蓝柱左端 = 占位1，红柱左端 = 占位1+2022+占位2（恒为 4668）
LEFT_2022 = np.array(PLACEHOLDER_1, dtype=float)
LEFT_2021 = LEFT_2022 + np.array(SALES_2022, dtype=float) + np.array(PLACEHOLDER_2, dtype=float)
GAP_CENTER = float(LEFT_2022[0] + SALES_2022[0] + PLACEHOLDER_2[0] / 2.0)  # 4060.5

# 绘图区（取自 chart6.xml 的 manualLayout，layoutTarget="inner" / xMode=edge）
AXES_LEFT = 0.034313725490196081
AXES_TOP = 0.28485616938848751
AXES_WIDTH = 0.94607843137254899
AXES_HEIGHT = 0.59845576122345734

# 数值轴：轴被 delete="1"，范围是 Excel 自动取整的 0~8000
X_MAX = 8000.0
BAR_HEIGHT = 1.0 / (1.0 + 150.0 / 100.0)  # gapWidth=150%

# 标签内缩（实测：蓝柱文字左缘距柱左端 13.5px，红柱文字右缘距柱右端 14px）
LABEL_INSET_2022 = 13.5
LABEL_INSET_2021 = 14.0

# 文字基线相对条目中心的像素偏移（Excel 把数据标签在条目里垂直居中，
# 而 matplotlib 的 offset points 是 +y 向上，所以往下的偏移要写成负数）。
# 实测：参考图里「2238」墨迹在 198~208、「华南」墨迹在 194~210，条目中心
# 202.5。下面两个数是把复刻图的墨迹量到同一位置后定下来的。
DIGIT_BASELINE_DY = -6.5   # 9pt Calibri 数字
CJK_BASELINE_DY = -5.5     # 9pt 汉字（等线）

# 标题 / 副标题 / 年份标题 / 脚注（像素坐标，原点在左上角，用于 va="baseline"）
TITLE = "2022年上半年各区域对比去年销量"
SUBTITLE = "2022年整体销量高于2021年，只有东北区域较2021有所下降"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.06.30"
HEADER_2022 = "2022"
HEADER_2021 = "2021"

TITLE_XY = (54.0, 74.5)
SUBTITLE_XY = (54.0, 119.0)
FOOTNOTE_XY = (51.0, 562.5)
HEADER_2022_XY = (307.5, 171.5)   # 文本框里用空格隔开，这里按实测拆成两个文本
HEADER_2021_XY = (517.0, 171.5)


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

    positions = np.arange(len(CATEGORIES), dtype=float)

    # ---- 系列0「占位1」与系列2「占位2」在 XML 里是 noFill，完全不可见，
    #      它们的作用只是把可见柱推到两侧，所以这里不画，只把偏移量算进去。
    axis.barh(positions, SALES_2022, height=BAR_HEIGHT, left=LEFT_2022,
              color=COLOR_2022, edgecolor="none", zorder=2)
    axis.barh(positions, SALES_2021, height=BAR_HEIGHT, left=LEFT_2021,
              color=COLOR_2021, edgecolor="none", zorder=2)

    # ---- 坐标轴：catAx 与 valAx 都是 delete="1"，整条隐藏 ----
    axis.set_xlim(0, X_MAX)
    axis.set_ylim(-0.5, len(CATEGORIES) - 0.5)
    axis.set_xticks([])
    axis.set_yticks([])
    axis.grid(False)
    for spine in axis.spines.values():
        spine.set_visible(False)

    px_per_value = AXES_WIDTH * FIG_W_PX / X_MAX
    dy_pt = 72.0 / DPI  # 1 像素 = 0.72pt

    # ---- 数据标签：2022 系列 dLblPos="inBase"（贴左端）----
    for index, position in enumerate(positions):
        x = LEFT_2022[index] + LABEL_INSET_2022 / px_per_value
        axis.annotate(str(SALES_2022[index]), xy=(x, position),
                      xytext=(0, DIGIT_BASELINE_DY * dy_pt),
                      textcoords="offset points",
                      ha="left", va="baseline", color=LABEL_COLOR_2022,
                      fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS, zorder=5)

    # ---- 数据标签：2021 系列 dLblPos="inEnd"（贴右端）----
    for index, position in enumerate(positions):
        x = LEFT_2021[index] + SALES_2021[index] - LABEL_INSET_2021 / px_per_value
        axis.annotate(str(SALES_2021[index]), xy=(x, position),
                      xytext=(0, DIGIT_BASELINE_DY * dy_pt),
                      textcoords="offset points",
                      ha="right", va="baseline", color=LABEL_COLOR_2021,
                      fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS, zorder=5)

    # ---- 类别名：其实是「占位2」系列的数据标签，dLblPos="ctr"，
    #      落在 3453~4668 这段空白带的正中央 ----
    for index, position in enumerate(positions):
        axis.annotate(CATEGORIES[index], xy=(GAP_CENTER, position),
                      xytext=(0, CJK_BASELINE_DY * dy_pt),
                      textcoords="offset points",
                      ha="center", va="baseline", color=CATEGORY_COLOR,
                      fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS, zorder=5)

    # ---- 标题 / 副标题 / 年份标题 / 脚注 ----
    figure.text(TITLE_XY[0] / FIG_W_PX, 1.0 - TITLE_XY[1] / FIG_H_PX, TITLE,
                ha="left", va="baseline", color="white",
                fontsize=18 * FONT_SCALE, fontweight="bold", fontfamily=UI_FONT)
    figure.text(SUBTITLE_XY[0] / FIG_W_PX, 1.0 - SUBTITLE_XY[1] / FIG_H_PX, SUBTITLE,
                ha="left", va="baseline", color="white",
                fontsize=11 * FONT_SCALE, fontfamily=UI_FONT)
    figure.text(FOOTNOTE_XY[0] / FIG_W_PX, 1.0 - FOOTNOTE_XY[1] / FIG_H_PX, FOOTNOTE,
                ha="left", va="baseline", color=FOOTNOTE_COLOR,
                fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)

    # 「2022 / 2021」来自 userShapes 里一个 11pt 的文本框（drawing12.xml）。该文本框的
    # 字号虽然是 11pt，但 Latin 字形没有显式指定，走的是主题的 +mn-lt（Calibri），
    # 所以要和坐标轴文字用同一套字体回退，不能用标题的微软雅黑——用雅黑数字会宽 ~17%。
    for (x_px, y_px), text, color in (
            (HEADER_2022_XY, HEADER_2022, HEADER_2022_COLOR),
            (HEADER_2021_XY, HEADER_2021, HEADER_2021_COLOR)):
        figure.text(x_px / FIG_W_PX, 1.0 - y_px / FIG_H_PX, text,
                    ha="center", va="baseline", color=color,
                    fontsize=11 * FONT_SCALE, fontfamily=AXIS_FONTS)

    output = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "chart6_butterfly.png")
    figure.savefig(output, dpi=200, facecolor=BACKGROUND)
    print("saved:", output)
    return figure


if __name__ == "__main__":
    if matplotlib.get_backend().lower() == "agg":
        main()
    else:
        main()
        plt.show()
