# -*- coding: utf-8 -*-
"""
图表复刻 12/15 —— 菱形走势图（棒棒糖图）

复刻对象：`第二章 图表(前15).xlsx` 工作表「12 菱形走势图」中的图表。
原始图表由 Excel 生成，本脚本用 matplotlib 逐像素还原其外观。

**注意编号**：工作表序号是 12，但对应的图表部件是 xl/charts/chart11.xml
（xl/drawings/drawing23.xml 是它的 userShapes）。核对方法：chart11.xml 里
所有 c:f 公式都指向 '12 菱形走势图'!，且 reference/chart12_excel.png 与该
工作表导出的图一致。

图表结构：一根被「拆开」的折线图（lineChart, grouping=standard）。
折线本身没有线（c:spPr 里 ln/noFill），只剩 8 个菱形标记；再从每个标记
垂直落一条 dropLines 到类别轴，于是每个类别看上去就是一支「棒棒糖」：
细红线 + 顶端空心菱形 + 菱形上方居中的两位小数百分比标签。

数据来源：'12 菱形走势图'!$B$3:$B$10（类别）与 $C$3:$C$10（完成率）

样式规格全部取自该 xlsx 的图表 XML（chart11.xml）与 userShapes（drawing23.xml）：

    XML 里的定义                                matplotlib 实现
    -----------------------------------------   --------------------------------
    图表区底色 srgbClr 1A1E43                   chartkit.BACKGROUND
    绘图区 manualLayout x=0.0808452 y=0.2772785 chartkit.plot_area()
      w=0.8652580 h=0.5467754（layoutTarget=inner, xMode/yMode=edge）
    折线系列 spPr ln/noFill w=28575            不画折线
    marker symbol=diamond size=8                Polygon 空心菱形（逐点手绘）
      spPr solidFill 1A1E43（= 底色，即「空心」）
      ln w=9525 srgbClr E74E69                  描边 0.75pt #E74E69
    dropLines ln w=9525 srgbClr E74E69          竖线 0.75pt #E74E69
    数据标签 dLblPos="t" showVal=1              菱形上方居中
      9pt b=0，bg1 lumMod 95%（#F2F2F2），+mn-lt = Calibri
    数值轴 valAx delete="1"                     整条 y 轴删除（无线无标签无网格）
    数值轴 numFmt=0.00%，范围由 Excel 自动取整     ylim=(0, 0.8)（见下）
    类别轴 catAx delete=0                       只画轴线，无刻度线
      轴线 ln w=6350（0.5pt）bg1 lumMod95%        1 设备像素 #F2F2F2 alpha 0.4
        + alpha 40000
      标签 9pt bg1 lumMod95%（#F2F2F2）           xticklabels #F2F2F2
    标题   微软雅黑 20pt 加粗 白色                userShapes 文本框 11 第 1 段
    副标题 微软雅黑 12pt 白色                     userShapes 文本框 11 第 2 段
    脚注   微软雅黑 8pt  bg1 lumMod85%（#D9D9D9） userShapes 文本框 12

两处需要说明的取值：

1. **数值轴范围 0~0.8**：valAx 被删掉了，XML 里没有 c:min/c:max。把图上量到的
   8 个菱形中心对数据值做最小二乘，得到 y = 486.00 - 403.27×v（残差全部
   < 0.6px）；403.27 × 0.8 = 322.62px，与 manualLayout 的绘图区高 322.60px
   吻合，故上限就是 0.8，且「v=0」正落在绘图区下缘 y=486.0。
2. **绘图区横向取整**：manualLayout 的 x=0.0808452 → 67.26px、w=0.8652580 →
   719.90px，但 8 条竖线的中心实测恰好在 112.0 / 202.0 / … / 742.0，间隔
   严格 90.0px，即 Excel 渲染时把绘图区取整成了 [67, 787]。故横向用
   67.0 / 720.0，纵向仍用 manualLayout 原值。

坐标轴/数据标签的 Latin 字形继承主题字体（+mn-lt = Calibri），中日韩字形
继承工作簿默认字体（等线 / DengXian）。

运行：python chart12_diamond_lollipop.py
输出：chart12_diamond_lollipop.png（832 x 590，与 Excel 导出图等比同尺寸）
"""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

import chartkit

# --------------------------------------------------------------------------
# 常量：全部按 Excel 图表的原始定义换算
# --------------------------------------------------------------------------

DPI = chartkit.DPI                              # 100
FIG_W_PX = 832                                  # Excel 图表对象宽 416pt × 2
FIG_H_PX = chartkit.height_px_of(12)            # 图表对象高 294.75pt × 2 = 590
FONT_SCALE = chartkit.FONT_SCALE                # 字号换算：2 * 72 / DPI = 1.44

BACKGROUND = chartkit.BACKGROUND                # 图表区底色 #1A1E43
MARKER_FILL = "#1A1E43"      # marker spPr solidFill：与底色同色，故菱形是「空心」
MARKER_EDGE = "#E74E69"      # marker/dropLines 的 ln srgbClr
LABEL_COLOR = "#F2F2F2"      # bg1 lumMod 95%：类别标签与数据标签共用
AXIS_LINE_ALPHA = 0.40       # 类别轴轴线 bg1 lumMod95% alpha=40000
FOOTNOTE_COLOR = "#D9D9D9"   # bg1 lumMod 85%：脚注

CATEGORIES = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月"]
# '12 菱形走势图'!$C$3:$C$10
COMPLETION = [0.536, 0.498, 0.527, 0.708, 0.609, 0.496, 0.586, 0.704]
# 数据标签走 numFmt 0.00%，保持 Excel 的两位小数写法（0.496 显示成 49.60%）
LABELS = ["%.2f%%" % (value * 100) for value in COMPLETION]

TITLE = "2022年1-8月公司计划完成率"                                      # 20pt 加粗
SUBTITLE = "公司整体完成率55%，4月和8月超过70%，2月和6月较低未过半"    # 12pt
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.08.31"       # 8pt

# 绘图区：横向取整到设备像素（见模块 docstring 第 2 点），纵向用 XML 原值
LAYOUT = chartkit.manual_layout(11)
AXES_LEFT_PX = 67.0                                  # 实测：manualLayout 67.26 → 67
AXES_WIDTH_PX = 720.0                                # 实测：manualLayout 719.90 → 720
AXES_TOP = float(LAYOUT["y"])                        # 0.27727852489010746
AXES_HEIGHT = float(LAYOUT["h"])                     # 0.54677535345127803

# 数值轴范围：最小二乘拟合实测菱形中心得到 0~0.8（见模块 docstring 第 1 点）
Y_MAX = 0.8

# 类别轴轴线：ln w=6350EMU=0.5pt，bg1 lumMod95% + alpha 40%。
# 实测原图 1px、颜色 #717389（= #1A1E43 上叠 40% 的 #F2F2F2），
# 横向跨 67.26~787.16px，纵向独占 y=485 这一行（即线心在 485.5）。
AXIS_LINE_Y_PX = 485.5
AXIS_LINE_X0_PX = float(LAYOUT["x"]) * FIG_W_PX                        # 67.26
AXIS_LINE_X1_PX = (float(LAYOUT["x"]) + float(LAYOUT["w"])) * FIG_W_PX  # 787.16

# ---- 菱形标记（全部为在 reference/chart12_excel.png 上实测的像素值）----
# marker size=8 -> 标记外框 8pt = 16px；Excel 画的是内接菱形，
# 实测墨迹横向 103~120（含 1.5px 描边），故路径半宽 7.85px、半高 7.4px。
MARKER_HALF_W_PX = 7.85
MARKER_HALF_H_PX = 7.4

# ---- 文字落点（实测值，详见各自注释）----
# 标题墨迹行 45~83、x 起 57；副标题 106~129、x 起 55；脚注 549~563、x 起 60。
TITLE_LEFT_PX = 55.0
TITLE_BASELINE_PX = 78.5
SUBTITLE_LEFT_PX = 55.0
SUBTITLE_BASELINE_PX = 126.5
FOOTNOTE_LEFT_PX = 59.0
FOOTNOTE_BASELINE_PX = 561.0

# 数据标签：实测 8 个标签的墨迹底边都比菱形中心高 23px（26.0 那点高 22px），
# 且 x 与类别中心对齐（ha="center"）。
LABEL_GAP_PX = 23.0
# 类别标签：轴线行 485，标签墨迹行 501~516（实测）
CATEGORY_LABEL_BASELINE_PX = 516.0

plt.rcParams["axes.unicode_minus"] = False

# 标题/副标题/脚注在 XML 中显式指定了「微软雅黑」
UI_FONT = chartkit.UI_FONT
# 坐标轴与数据标签：Latin 用 Calibri，中文回退到等线（工作簿默认字体）
AXIS_FONTS = chartkit.AXIS_FONTS


def diamond(figure, center_x_px, center_y_px):
    """一个类别的菱形标记：中心在画布像素 (x, y)，返回挂在 figure 上的 Polygon。

    Excel 的菱形是「空心」的——c:marker/c:spPr 的填充被写成 1A1E43，
    正好等于图表区底色，视觉上只剩一个 E74E69 的描边。
    """
    corners = [(center_x_px, center_y_px - MARKER_HALF_H_PX),
               (center_x_px + MARKER_HALF_W_PX, center_y_px),
               (center_x_px, center_y_px + MARKER_HALF_H_PX),
               (center_x_px - MARKER_HALF_W_PX, center_y_px)]
    return Polygon([(px / FIG_W_PX, 1.0 - py / FIG_H_PX) for px, py in corners],
                   closed=True, transform=figure.transFigure,
                   facecolor=MARKER_FILL, edgecolor=MARKER_EDGE,
                   linewidth=0.75 * FONT_SCALE, joinstyle="miter", zorder=4)


def main():
    figure = chartkit.new_figure(FIG_W_PX, FIG_H_PX)

    layout = dict(LAYOUT)
    layout["x"] = AXES_LEFT_PX / FIG_W_PX
    layout["w"] = AXES_WIDTH_PX / FIG_W_PX
    axis = chartkit.plot_area(figure, layout, FIG_H_PX)
    axis.set_facecolor(BACKGROUND)

    positions = np.arange(len(CATEGORIES))

    # ---- 坐标范围：每个类别占 1 格，两侧各留半格；数值轴 0~0.8 ----
    axis.set_xlim(-0.5, len(CATEGORIES) - 0.5)
    axis.set_ylim(0, Y_MAX)

    # 数值轴 delete="1"：无刻度、无网格线、无轴线
    axis.set_yticks([])
    axis.grid(False)
    for spine in axis.spines.values():
        spine.set_visible(False)

    # ---- 每格在画布上的像素宽度（类别中心 = 112 + 90i）----
    px_per_category = AXES_WIDTH_PX / len(CATEGORIES)
    centre_x = AXES_LEFT_PX + (positions + 0.5) * px_per_category
    height_px = AXES_HEIGHT * FIG_H_PX
    bottom_px = (AXES_TOP + AXES_HEIGHT) * FIG_H_PX
    px_per_unit = height_px / Y_MAX

    # ---- dropLines：0.75pt E74E69，从类别轴竖直升到数据点 ----
    # Excel 把 1.5px 的线栅格化成整齐的 2px，故线宽取 1.0*FONT_SCALE = 1.44pt = 2px；
    # snap 关掉，让它保持落在实测的 111~112 这类整列上。
    for x, value in zip(centre_x, COMPLETION):
        figure.add_artist(Line2D([x / FIG_W_PX, x / FIG_W_PX],
                                 [1.0 - bottom_px / FIG_H_PX,
                                  1.0 - (bottom_px - value * px_per_unit) / FIG_H_PX],
                                 transform=figure.transFigure,
                                 color=MARKER_EDGE, linewidth=1.0 * FONT_SCALE,
                                 solid_capstyle="butt", antialiased=False, zorder=3))

    # ---- 菱形标记：压住竖线顶端 ----
    for x, value in zip(centre_x, COMPLETION):
        figure.add_artist(diamond(figure, x, bottom_px - value * px_per_unit))

    # ---- 数据标签：9pt Calibri #F2F2F2，居中于菱形上方 ----
    for x, value in zip(centre_x, COMPLETION):
        baseline = bottom_px - value * px_per_unit - LABEL_GAP_PX
        figure.text(x / FIG_W_PX, 1.0 - baseline / FIG_H_PX,
                    "%.2f%%" % (value * 100), ha="center", va="baseline",
                    color=LABEL_COLOR, fontsize=9 * FONT_SCALE,
                    fontfamily=AXIS_FONTS, zorder=5)

    # ---- 类别标签：9pt #F2F2F2，无刻度线 ----
    for x, name in zip(centre_x, CATEGORIES):
        figure.text(x / FIG_W_PX, 1.0 - CATEGORY_LABEL_BASELINE_PX / FIG_H_PX,
                    name, ha="center", va="baseline",
                    color=LABEL_COLOR, fontsize=9 * FONT_SCALE,
                    fontfamily=AXIS_FONTS, zorder=5)

    # ---- 类别轴轴线：0.5pt #F2F2F2 alpha 40%，独占一整行 ----
    # 这是 valAx crosses="autoZero" 的那条轴，位置在绘图区下缘；用 figure 坐标
    # 单画一条，免得被绘图区边界裁掉半截。
    figure.add_artist(Line2D([AXIS_LINE_X0_PX / FIG_W_PX, AXIS_LINE_X1_PX / FIG_W_PX],
                             [1.0 - AXIS_LINE_Y_PX / FIG_H_PX] * 2,
                             transform=figure.transFigure,
                             color=LABEL_COLOR, alpha=AXIS_LINE_ALPHA,
                             linewidth=0.5 * FONT_SCALE, solid_capstyle="butt",
                             zorder=4))

    # ---- 标题 / 副标题 / 脚注：userShapes(drawing23.xml) 的两个文本框 ----
    figure.text(TITLE_LEFT_PX / FIG_W_PX, 1.0 - TITLE_BASELINE_PX / FIG_H_PX,
                TITLE, ha="left", va="baseline", color="white",
                fontsize=20 * FONT_SCALE, fontweight="bold", fontfamily=UI_FONT)
    figure.text(SUBTITLE_LEFT_PX / FIG_W_PX, 1.0 - SUBTITLE_BASELINE_PX / FIG_H_PX,
                SUBTITLE, ha="left", va="baseline", color="white",
                fontsize=12 * FONT_SCALE, fontfamily=UI_FONT)
    figure.text(FOOTNOTE_LEFT_PX / FIG_W_PX, 1.0 - FOOTNOTE_BASELINE_PX / FIG_H_PX,
                FOOTNOTE, ha="left", va="baseline", color=FOOTNOTE_COLOR,
                fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)

    return chartkit.save(figure, "chart12_diamond_lollipop.png")


if __name__ == "__main__":
    if matplotlib.get_backend().lower() == "agg":
        main()
    else:
        main()
        plt.show()
