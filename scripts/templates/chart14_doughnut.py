# -*- coding: utf-8 -*-
"""图表复刻 14/15 —— 单值圆环图

复刻对象：`第二章 图表(前15).xlsx` 工作表「14 单值圆环图」中的图表。

**注意编号**：工作表序号是 14，但对应的图表部件是 xl/charts/chart13.xml
（userShapes 是 xl/drawings/drawing27.xml）。核对方法：chart13.xml 里所有
c:f 公式都指向 '14 单值圆环图'!，且 reference/chart14_excel.png 与该工作表
导出的图一致。

结构很简单，两个数据点拼成一个「进度环」：

    doughnutChart  varyColors=1  holeSize=90  firstSliceAng=300
      点0「完成率」0.85   gradFill 线性 ang=5400000（自上而下）
                          pos=0      7030A0（紫）
                          pos=100000 E74E69（玫红）
      点1「占位」  0.15   bg1 lumMod95% alpha=10% —— 几乎透明的浅灰
                          （10% × #F2F2F2 叠在 #1A1E43 上 = #303455）

数据来源：'14 单值圆环图'!$B$3:$C$3 = [0.85, 0.15]，类别 $B$2:$C$2 = 完成率/占位。

几何：绘图区 manualLayout x=.297335 y=.276744 w=.422488 h=.564701，
圆环外径取绘图区短边 = h×617 = 348.42px，圆心在绘图区正中 (423.1, 345.0)；
holeSize=90 表示内径 = 外径 × 90%，即内半径 156.79px、环宽 17.4px。

**渐变的方向是量出来的，不是算出来的。** XML 写的是线性 ang=5400000（自上而下），
但照这个方向铺，环上凡是同一高度的点颜色都该一样 —— 实测却不是：圆环正右方
（3 点方向）是实打实的 #7030A0 系紫，正左方（9 点方向）却是 #E64E6A 系玫红，
两者 y 完全相同。所以 Excel 渲染这个数据点的渐变时用的不是画布坐标。这里直接
把原图沿一圈每 5° 采一个色写进 RING_GRADIENT 表，画的时候按角度线性插值 ——
比猜 Excel 的坐标变换可靠，也不会在别的机器上跑偏。

圆心的「85%」「目标完成率」和标题/副标题/脚注都来自 userShapes（drawing27.xml）：

    文本框 1   「85%」          36pt 微软雅黑，白色
    文本框 19  「目标完成率」   11pt 微软雅黑，bg1 lumMod95% = #F2F2F2
    文本框 11   标题 18pt 加粗 / 副标题 12pt，微软雅黑，白色
    文本框 12   脚注 8pt，bg1 lumMod85% = #D9D9D9

运行：python chart14_doughnut.py
输出：chart14_doughnut.png（832 x 617，与 Excel 导出图同尺寸）
"""

import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Wedge

import chartkit

# --------------------------------------------------------------------------
# 常量
# --------------------------------------------------------------------------

DPI = chartkit.DPI
FIG_W_PX = 832
FIG_H_PX = chartkit.height_px_of(14)          # 图表对象高 308.5pt × 2 = 617
FONT_SCALE = chartkit.FONT_SCALE              # 1.44

BACKGROUND = chartkit.BACKGROUND
PLACEHOLDER = "#303455"     # 占位段：bg1 lumMod95% alpha10% 叠在 1A1E43 上的合成色
VALUE_COLOR = "white"
SUB_LABEL_COLOR = "#F2F2F2"     # bg1 lumMod95%
FOOTNOTE_COLOR = "#D9D9D9"      # bg1 lumMod85%

VALUES = [0.85, 0.15]       # '14 单值圆环图'!$B$3:$C$3
FIRST_SLICE_ANGLE = 300.0   # firstSliceAng：第一段从「12 点顺时针数 300°」起画
HOLE_SIZE_PCT = 90.0        # holeSize=90 -> 内半径 = 外半径 × 90%

# 绘图区（chart13.xml 的 manualLayout），圆环外径取短边
LAYOUT = {"x": "0.29733460707117493", "y": "0.27674437501209154",
          "w": "0.42248764860274818", "h": "0.56470093572455782"}
PLOT_X_PX = 0.29733460707117493 * FIG_W_PX            # 247.38
PLOT_Y_PX = 0.27674437501209154 * FIG_H_PX            # 170.75
PLOT_W_PX = 0.42248764860274818 * FIG_W_PX            # 351.51
PLOT_H_PX = 0.56470093572455782 * FIG_H_PX            # 348.42

OUTER_R_PX = min(PLOT_W_PX, PLOT_H_PX) / 2.0          # 174.21
INNER_R_PX = OUTER_R_PX * HOLE_SIZE_PCT / 100.0       # 156.79
CENTRE_X_PX = PLOT_X_PX + PLOT_W_PX / 2.0             # 423.14
CENTRE_Y_PX = PLOT_Y_PX + PLOT_H_PX / 2.0             # 344.96

# 圆心文字（userShapes 文本框 1 / 19，都是 anchor="ctr"）
VALUE_TEXT = "85%"
VALUE_TEXT_CENTRE = (0.5 * (0.35768 + 0.65534) * FIG_W_PX,     # 421.4
                     0.5 * (0.42968 + 0.62338) * FIG_H_PX)     # 324.9
VALUE_TEXT_PT = 36.0
SUB_TEXT = "目标完成率"
SUB_TEXT_CENTRE = (0.5 * (0.41054 + 0.59436) * FIG_W_PX,       # 418.0
                   0.5 * (0.62735 + 0.69738) * FIG_H_PX)       # 408.7
SUB_TEXT_PT = 11.0

# 标题 / 副标题 / 脚注（文本框 11 / 12，rel 左缘 + 默认左内缩 lIns=7.2pt）
TEXT_INSET_PX = 7.2 * chartkit.PX_PER_PT
TITLE_TEXT_X_PX = 0.04197 * FIG_W_PX + TEXT_INSET_PX          # 49.3
FOOTNOTE_TEXT_X_PX = 0.03646 * FIG_W_PX + TEXT_INSET_PX       # 44.7
TITLE = "2022年上半年目标完成率"
SUBTITLE = "截至6月30日销售目标总体完成率达到85%"
FOOTNOTE = "*注：数据来源于公司销售系统"
TITLE_BASELINE_PX = 78.5        # 实测：标题墨迹 48~83（18pt 加粗）
SUBTITLE_BASELINE_PX = 123.5    # 实测：副标题墨迹 105~127（12pt）
FOOTNOTE_BASELINE_PX = 588.0    # 实测：脚注墨迹 576~590（8pt）

# ---- 圆环渐变的实测色表：从 12 点方向起、顺时针每 5° 采一次 ----
# 原图沿半径 165px 处采样，值形如 (角度, R, G, B)。
RING_GRADIENT = [
    (0, 113, 48, 160), (5, 114, 48, 160), (10, 114, 48, 160), (15, 115, 49, 159),
    (20, 115, 49, 159), (25, 116, 49, 159), (30, 117, 49, 159), (35, 120, 50, 158),
    (40, 122, 50, 158), (45, 125, 50, 157), (50, 129, 52, 156), (55, 134, 53, 155),
    (60, 139, 54, 153), (65, 146, 56, 151), (70, 153, 57, 149), (75, 160, 59, 146),
    (80, 168, 61, 143), (85, 176, 63, 139), (90, 183, 65, 136), (95, 191, 67, 132),
    (100, 198, 69, 128), (105, 204, 71, 125), (110, 209, 72, 121), (115, 214, 73, 118),
    (120, 218, 74, 116), (125, 221, 75, 113), (130, 223, 76, 112), (135, 225, 76, 110),
    (140, 226, 77, 109), (145, 228, 77, 108), (150, 229, 77, 107), (155, 229, 78, 107),
    (160, 230, 78, 106), (165, 230, 78, 106), (170, 230, 78, 106), (175, 230, 78, 106),
    (180, 230, 78, 106), (185, 230, 78, 106), (190, 230, 78, 106), (195, 230, 78, 106),
    (200, 230, 78, 106), (205, 229, 78, 107), (210, 229, 77, 107), (215, 228, 77, 108),
    (220, 226, 77, 109), (225, 225, 76, 110), (230, 223, 76, 112), (235, 221, 75, 113),
    (240, 218, 74, 116), (245, 214, 73, 118), (250, 48, 52, 85), (255, 48, 52, 85),
    (260, 48, 52, 85), (265, 48, 52, 85), (270, 48, 52, 85), (275, 48, 52, 85),
    (280, 48, 52, 85), (285, 48, 52, 85), (290, 48, 52, 85), (295, 48, 52, 85),
    (300, 48, 52, 85), (305, 134, 53, 155), (310, 129, 52, 156), (315, 125, 50, 157),
    (320, 122, 50, 158), (325, 120, 50, 158), (330, 117, 49, 159), (335, 116, 49, 159),
    (340, 115, 49, 159), (345, 115, 49, 159), (350, 114, 48, 160), (355, 114, 48, 160),
]
GRADIENT_STEP_DEG = 2.0     # 实际描画时每 2° 一个扇形，够密也够快

plt.rcParams["axes.unicode_minus"] = False


def gradient_color(compass_deg):
    """按实测色表取某个「12 点起顺时针」角度上的颜色，线性插值。"""
    compass_deg %= 360.0
    index = int(compass_deg // 5) % 72
    low, high = RING_GRADIENT[index], RING_GRADIENT[(index + 1) % 72]
    span = (high[0] - low[0]) % 360 or 5
    ratio = ((compass_deg - low[0]) % 360) / span
    return tuple((low[i] + (high[i] - low[i]) * ratio) / 255.0 for i in range(1, 4))


def draw_ring(axis):
    """把数据段画成一圈细扇形，颜色按实测色表插值。"""
    start = FIRST_SLICE_ANGLE                      # 300°，顺时针
    sweep = VALUES[0] * 360.0                      # 85% -> 306°

    for index in np.arange(0, sweep, GRADIENT_STEP_DEG):
        # 罗盘角（12 点起、顺时针）转成 matplotlib 的数学角（3 点起、逆时针）
        compass = start + index
        theta1 = 90.0 - (compass + GRADIENT_STEP_DEG)
        theta2 = 90.0 - compass
        axis.add_patch(Wedge((CENTRE_X_PX, CENTRE_Y_PX), OUTER_R_PX,
                             theta1, theta2, width=OUTER_R_PX - INNER_R_PX,
                             facecolor=gradient_color(compass + GRADIENT_STEP_DEG / 2.0),
                             edgecolor="none", linewidth=0))

    # 占位段：一段几乎透明的浅灰，从数据段末尾接着画满一圈
    compass_end = (start + sweep) % 360.0
    axis.add_patch(Wedge((CENTRE_X_PX, CENTRE_Y_PX), OUTER_R_PX,
                         90.0 - (compass_end + (360.0 - sweep)), 90.0 - compass_end,
                         width=OUTER_R_PX - INNER_R_PX,
                         facecolor=PLACEHOLDER, edgecolor="none", linewidth=0))


def main():
    figure = chartkit.new_figure(FIG_W_PX, FIG_H_PX)

    # 整张图用一个铺满画布的像素坐标系（y 向下），圆环和文字都用实测像素落点
    axis = figure.add_axes([0, 0, 1, 1])
    axis.set_facecolor(BACKGROUND)
    axis.set_xlim(0, FIG_W_PX)
    axis.set_ylim(FIG_H_PX, 0)
    axis.set_xticks([])
    axis.set_yticks([])
    for spine in axis.spines.values():
        spine.set_visible(False)

    draw_ring(axis)

    # ---- 圆心文字 ----
    # 这两个文本框在 XML 里都没指定字体，Latin 走主题的 +mn-lt（Calibri）、
    # 中文走 +mn-ea（等线），不是标题那套微软雅黑 —— 用雅黑「85%」会宽出 18%。
    axis.text(VALUE_TEXT_CENTRE[0], VALUE_TEXT_CENTRE[1] + 25.5, VALUE_TEXT,
              ha="center", va="baseline", color=VALUE_COLOR,
              fontsize=VALUE_TEXT_PT * FONT_SCALE, fontfamily=chartkit.AXIS_FONTS)
    axis.text(SUB_TEXT_CENTRE[0], SUB_TEXT_CENTRE[1] + 7.0, SUB_TEXT,
              ha="center", va="baseline", color=SUB_LABEL_COLOR,
              fontsize=SUB_TEXT_PT * FONT_SCALE, fontfamily=chartkit.AXIS_FONTS)

    # ---- 标题 / 副标题 / 脚注 ----
    figure.text(TITLE_TEXT_X_PX / FIG_W_PX, 1.0 - TITLE_BASELINE_PX / FIG_H_PX,
                TITLE, ha="left", va="baseline", color="white",
                fontsize=18 * FONT_SCALE, fontweight="bold", fontfamily=chartkit.UI_FONT)
    figure.text(TITLE_TEXT_X_PX / FIG_W_PX, 1.0 - SUBTITLE_BASELINE_PX / FIG_H_PX,
                SUBTITLE, ha="left", va="baseline", color="white",
                fontsize=12 * FONT_SCALE, fontfamily=chartkit.UI_FONT)
    figure.text(FOOTNOTE_TEXT_X_PX / FIG_W_PX, 1.0 - FOOTNOTE_BASELINE_PX / FIG_H_PX,
                FOOTNOTE, ha="left", va="baseline", color=FOOTNOTE_COLOR,
                fontsize=8 * FONT_SCALE, fontfamily=chartkit.UI_FONT)

    return chartkit.save(figure, "chart14_doughnut.png")


if __name__ == "__main__":
    if matplotlib.get_backend().lower() == "agg":
        main()
    else:
        main()
        plt.show()
