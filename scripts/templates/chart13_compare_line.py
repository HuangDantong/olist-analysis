# -*- coding: utf-8 -*-
"""
图表复刻 13/15 —— 对比折线图

复刻对象：`第二章 图表(前15).xlsx` 工作表「13 对比折线图」中的图表。
原始图表由 Excel 生成，本脚本用 matplotlib 逐像素还原其外观。

**注意编号**：工作表序号 13 对应的图表部件是 xl/charts/chart12.xml，
它的 userShapes 是 xl/drawings/drawing25.xml。核对方法：chart12.xml 里
所有 c:f 公式都指向 '13 对比折线图'!，且 reference/chart13_excel.png 与
该工作表导出的图一致（图表对象 416 x 311 pt -> 832 x 622 px）。

图表结构：两条带实心圆点标记的折线，6 个类别（1月…6月）：
  2021年  #E74E69 洋红   1686 1345 1934 1658 1865 1936
  2022年  #0070C0 蓝     1385 1846 1654 1936 2564 2236
每个数据点旁边有 9pt 的数值标签：一半走系列默认的 dLblPos="t"（点在线上方），
另一半被手工拖到线下方（c:dLbl/c:layout/c:manualLayout 记着拖动量）。

数据来源：
  '13 对比折线图'!$B$3:$B$8   类别  1月 … 6月
  '13 对比折线图'!$C$3:$C$8   系列0 2021年
  '13 对比折线图'!$D$3:$D$8   系列1 2022年

样式规格全部取自该 xlsx 的图表 XML（xl/charts/chart12.xml、
xl/drawings/drawing25.xml），关键参数如下：

    XML 里的定义                                  matplotlib 实现
    -------------------------------------------   ------------------------------
    图表区背景 srgbClr 1A1E43                     figure 底色 chartkit.BACKGROUND
    绘图区 manualLayout                           chartkit.plot_area()
      x=0.13012043 y=0.35889338 w=0.81350702 h=0.48976043
    系列0 线 a:ln w=19050EMU(1.50pt) srgbClr       plot(linewidth=1.5*FONT_SCALE)
      E74E69，cap=rnd                              solid_capstyle="round"
    系列1 线 srgbClr 0070C0                        BLUE
    平滑 c:smooth val="0"                          直线段（matplotlib 默认）
    标记 c:marker symbol=circle size=5             plot(marker="o",
      spPr 填充 E74E69 / 0070C0                      markersize=5*FONT_SCALE)
      spPr 描边 1A1E43 w=9525EMU(0.75pt)             markeredgecolor=BACKGROUND
    数值轴 majorGridlines a:ln w=6350EMU(0.5pt)     axhline，dashes=(8,3)
      bg1 lumMod95% alpha=20000 prstDash=lgDash     （lgDash = 8d 3d，d=线宽）
    两个坐标轴 spPr 都是 noFill/ln noFill           spines 全部隐藏、无刻度线
    数值轴刻度 0~3000 步长 500（自动取整）          yticks 0,500,…,3000
    刻度标签 9pt bg1 lumMod95%（#F2F2F2）           #F2F2F2
    数据标签 dLbls dLblPos="t" showVal=1 9pt       6 个默认标签排在线之上
       bg1 lumMod95%，txPr 与坐标轴共用              见 ABOVE_LABEL_* 常量
    12 个标签里的 6 个带                          ABOVE_LABEL_* / MOVED_LABELS
      c:dLbl/c:layout/c:manualLayout               （x/y 是相对图表区的位移）
    图例 c:legend manualLayout                     手工画「线段 + 圆点 + 文字」
      x=0.63851 y=0.27300 w=0.30141 h=0.050676      见 LEGEND_* 常量
    标题 微软雅黑 20pt 加粗 白色                    userShapes 文本框 11
    副标题 微软雅黑 12pt 白色                       同一文本框的第 2 段
    脚注 微软雅黑 8pt bg1 lumMod85%（#D9D9D9）     userShapes 文本框 12

series 的 spPr 里颜色是写死的 srgbClr（不是主题 accent），所以直接照抄即可。
坐标轴/数据标签的 Latin 字形继承主题字体（+mn-lt = Calibri），中日韩字形
继承工作簿默认字体（等线 / DengXian）；图例文字与数据标签同源，也用这套回退。

运行：python chart13_compare_line.py
输出：chart13_compare_line.png（832 x 622，与 Excel 导出图等比同尺寸）
"""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.transforms import ScaledTranslation

import chartkit

# --------------------------------------------------------------------------
# 常量：全部按 Excel 图表的原始定义换算
# --------------------------------------------------------------------------

DPI = chartkit.DPI                              # 100
FIG_W_PX = 832                                  # Excel 图表对象宽 416pt × 2
FIG_H_PX = chartkit.height_px_of(13)            # 图表对象高 311pt × 2 = 622
FONT_SCALE = chartkit.FONT_SCALE                # 字号/线宽换算：2 * 72 / DPI = 1.44

BACKGROUND = chartkit.BACKGROUND                # 图表区底色 #1A1E43
RED = "#E74E69"                                 # 系列0 线/标记 srgbClr
BLUE = "#0070C0"                                # 系列1 线/标记 srgbClr
LABEL_COLOR = "#F2F2F2"                         # bg1 lumMod 95%：刻度/数据标签/图例
FOOTNOTE_COLOR = "#D9D9D9"                      # bg1 lumMod 85%：脚注
GRID_COLOR = LABEL_COLOR                        # 网格线同色，靠 alpha 压暗
GRID_ALPHA = 0.20                               # bg1 lumMod95% alpha=20000

CATEGORIES = ["1月", "2月", "3月", "4月", "5月", "6月"]
SERIES = [
    ("2021年", RED, [1686, 1345, 1934, 1658, 1865, 1936]),   # $C$3:$C$8
    ("2022年", BLUE, [1385, 1846, 1654, 1936, 2564, 2236]),  # $D$3:$D$8
]

TITLE = "2022年上半年各月同比去年销量"                     # 20pt 加粗
SUBTITLE = "上半年同比去年增长明显，5月份同比增长最多，增长近40%"   # 12pt
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.06.30"    # 8pt

# ---- 绘图区：chart12.xml 的 plotArea/layout/manualLayout（相对图表区的比例）----
# x*832 = 108.26px，y*622 = 223.23px，w*832 = 676.84px，h*622 = 304.63px；
# 原图实测最上一条网格线（3000）落在第 223 行、最下一条（0）落在第 527 行，
# 首末两个数据点圆心实测 x≈164.5 / 728.6，与上面换算出的 164.66 / 728.69 吻合。
AXES_LEFT_PX = 0.13012042612320518 * FIG_W_PX
AXES_TOP_PX = 0.3588933815705469 * FIG_H_PX
AXES_WIDTH_PX = 0.81350702485718696 * FIG_W_PX
AXES_HEIGHT_PX = 0.48976042613837895 * FIG_H_PX
AXES_BOTTOM_PX = AXES_TOP_PX + AXES_HEIGHT_PX   # 527.86px

# 数值轴：valAx 没有 c:max/c:majorUnit，范围由 Excel 按最大值 2564 自动取整。
# 原图网格线共 7 条、间距 50.7px，对应 0 / 500 / … / 3000（每 500 约 50.77px）。
Y_MAX = 3000
Y_TICKS = np.arange(0, Y_MAX + 1, 500)

# 线宽 19050EMU = 1.50pt，Excel 按 2px/pt 导出成 3px；
# matplotlib 的 linewidth 以 pt 计（100dpi 下 1pt = 1.389px），故同样乘 FONT_SCALE。
LINE_WIDTH_PT = 1.50 * FONT_SCALE               # -> 3px
# 标记 size=5（直径 5pt = 10px），描边 9525EMU = 0.75pt = 1.5px，颜色同底色
MARKER_SIZE_PT = 5.0 * FONT_SCALE               # -> 10px
MARKER_EDGE_PT = 0.75 * FONT_SCALE              # -> 1.5px

# ---- 文字落点（单位 px，全部为在 reference/chart13_excel.png 上的实测值）----
# 文本框 11：a:off x=19.0pt，加 bodyPr 默认左内缩 7.2pt = 14.4px -> 52.4px；
# 实测标题数字「2022」墨迹起于 x=55（20pt 粗体数字自带约 2.6px 左侧留白），
# 副标题汉字「上」墨迹起于 x=54（12pt 汉字留白约 1.6px），两者互相印证。
TEXT_LEFT_PX = 52.4
TITLE_BASELINE_PX = 77.0        # 实测：标题「2022」数字墨迹 46~77（20pt 加粗）
SUBTITLE_BASELINE_PX = 125.0    # 实测：副标题汉字墨迹 105~127（12pt，汉字下缘低于基线）
# 文本框 12：a:off x=18.6pt + 7.2pt 内缩 = 51.6px；实测脚注「*」墨迹起于 x=53
FOOTNOTE_LEFT_PX = 51.6
FOOTNOTE_BASELINE_PX = 595.5    # 实测：脚注「2022.06.30」数字墨迹 584~595

# ---- 数据标签 ----
# 默认标签（dLblPos="t"）：标签中心在数据点上方 24.4px 处（实测 6 个默认标签
# 的墨迹行中心到点心的距离为 24.0~24.9，取 24.36）；数字墨迹高 11px，
# 故基线 = 点心 y - 24.36 + 5.5。
ABOVE_LABEL_CENTRE_GAP_PX = 24.36
LABEL_INK_HALF_PX = 5.5         # 9pt 数字墨迹高 11px 的一半

# 被拖动的标签（c:dLbl 带 manualLayout）：Excel 存的是相对图表区的位移，
# x 占图表区宽、y 占图表区高，叠在「dLblPos="r"」的默认锚点上。
# 默认锚点：标签文本框中心在点心右侧 R_ANCHOR_PX 处（实测 6 个标签为
# 34.1~35.3，均值 34.7），y 与点心同高。
MOVED_LABEL_R_ANCHOR_PX = 34.7
# 纵向：标签中心 = 点心 y + y_frac * 622（六个标签逐个核对，残差 < 0.6px）
MOVED_LABEL_X_FRAC = 0.0        # 占位说明：x 位移见下表

# (系列序号, 数据点序号) -> (x 位移, y 位移)，逐字抄自 chart12.xml 的
# c:lineChart/c:ser/c:dLbls/c:dLbl/c:layout/c:manualLayout
MOVED_LABELS = {
    (0, 1): (-4.9355742296918768e-2, 3.8321983400723555e-2),   # 2021年 2月 1345
    (0, 3): (-5.2156862745098141e-2, 4.733099240973257e-2),    # 2021年 4月 1658
    (0, 4): (-5.2156862745098037e-2, 5.183549691423707e-2),    # 2021年 5月 1865
    (0, 5): (-5.215686274509794e-2, 4.7330992409732486e-2),    # 2021年 6月 1936
    (1, 0): (-5.2156862745098037e-2, 5.183549691423707e-2),    # 2022年 1月 1385
    (1, 2): (-4.9355742296918817e-2, 4.2826487905227979e-2),   # 2022年 3月 1654
}

# ---- 图例（c:legend manualLayout x=0.63851 y=0.27300 w=0.30141 h=0.050676）----
# 换算成像素是 (531.2, 169.8)-(782.0, 201.3)，Excel 把两个图例项横排在里面。
# Excel 的图例项 = 一小段折线 + 圆点居中 + 右侧文字；圆点 size=5 与图上一致。
# 下面四个 x 全部是原图实测（红 553~593 / 蓝 671~711 线段，圆点在正中）。
LEGEND_LINE_Y_PX = 185.0                        # 实测：线段占 184~186 三行
LEGEND_ENTRIES = [
    # (线段左, 线段右, 文字左缘)
    (553.0, 593.0, 597.0),                      # 2021年，文字墨迹 598~649
    (671.0, 711.0, 715.0),                      # 2022年，文字墨迹 716~767
]
LEGEND_TEXT_BASELINE_PX = 189.0                 # 实测：图例数字墨迹 178~188

plt.rcParams["axes.unicode_minus"] = False

# 标题/副标题/脚注在 XML 中显式指定了「微软雅黑」
UI_FONT = chartkit.UI_FONT
# 坐标轴/数据标签/图例：Latin 用 Calibri，中文回退到等线（工作簿默认字体）
AXIS_FONTS = chartkit.AXIS_FONTS


def point_px(series_index, point_index):
    """数据点圆心在画布里的像素坐标（Excel 的类别轴从半格处开始）。"""
    value = SERIES[series_index][2][point_index]
    x_px = AXES_LEFT_PX + (point_index + 0.5) * AXES_WIDTH_PX / len(CATEGORIES)
    y_px = AXES_BOTTOM_PX - value * AXES_HEIGHT_PX / Y_MAX
    return x_px, y_px


def draw_series(axis):
    """两条折线 + 实心圆点标记。标记压在线上（Excel 里标记画在线之后）。"""
    positions = np.arange(len(CATEGORIES))
    for _, color, values in SERIES:
        axis.plot(positions, values, color=color, linewidth=LINE_WIDTH_PT,
                  solid_capstyle="round", marker="o", markersize=MARKER_SIZE_PT,
                  markerfacecolor=color, markeredgecolor=BACKGROUND,
                  markeredgewidth=MARKER_EDGE_PT, clip_on=False, zorder=3)


def draw_grid(axis):
    """横向虚线网格线：lgDash(8d 3d)、0.5pt、bg1 lumMod95% alpha20%。

    压在绘图区上下边缘的两条会被坐标区裁掉，所以逐条画并关掉裁剪。
    """
    for value in Y_TICKS:
        axis.axhline(value, color=GRID_COLOR, alpha=GRID_ALPHA,
                     linewidth=0.5 * FONT_SCALE, dashes=(8.0, 3.0),
                     solid_capstyle="butt", clip_on=False, zorder=1)


def draw_data_labels(figure):
    """12 个数值标签：6 个默认（点在线上方）+ 6 个手工拖过的（XML manualLayout）。"""
    for series_index, (_, _, values) in enumerate(SERIES):
        for point_index, value in enumerate(values):
            x_px, y_px = point_px(series_index, point_index)
            if (series_index, point_index) in MOVED_LABELS:
                dx_frac, dy_frac = MOVED_LABELS[(series_index, point_index)]
                centre_x = x_px + MOVED_LABEL_R_ANCHOR_PX + dx_frac * FIG_W_PX
                centre_y = y_px + dy_frac * FIG_H_PX
            else:
                centre_x = x_px
                centre_y = y_px - ABOVE_LABEL_CENTRE_GAP_PX
            baseline = centre_y + LABEL_INK_HALF_PX
            figure.text(centre_x / FIG_W_PX, 1.0 - baseline / FIG_H_PX, str(value),
                        ha="center", va="baseline", color=LABEL_COLOR,
                        fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS, zorder=5)


def draw_legend(figure):
    """图例：Excel 图例项 = 线段 + 居中圆点 + 右侧文字，位置按原图实测摆。"""
    for (left_px, right_px, text_px), (name, color, _) in zip(LEGEND_ENTRIES, SERIES):
        y = 1.0 - LEGEND_LINE_Y_PX / FIG_H_PX
        figure.add_artist(Line2D([left_px / FIG_W_PX, right_px / FIG_W_PX], [y, y],
                                 transform=figure.transFigure, color=color,
                                 linewidth=LINE_WIDTH_PT, solid_capstyle="butt",
                                 zorder=6))
        figure.add_artist(Line2D([(left_px + right_px) / 2.0 / FIG_W_PX], [y],
                                 transform=figure.transFigure, color=color,
                                 linestyle="none", marker="o",
                                 markersize=MARKER_SIZE_PT, markerfacecolor=color,
                                 markeredgecolor=BACKGROUND,
                                 markeredgewidth=MARKER_EDGE_PT, zorder=7))
        figure.text(text_px / FIG_W_PX,
                    1.0 - LEGEND_TEXT_BASELINE_PX / FIG_H_PX, name,
                    ha="left", va="baseline", color=LABEL_COLOR,
                    fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS, zorder=7)


def main():
    figure = chartkit.new_figure(FIG_W_PX, FIG_H_PX)

    layout = chartkit.manual_layout(12)         # 图13 的图表部件是 chart12.xml，核对编号
    axis = chartkit.plot_area(figure, layout, FIG_H_PX)
    axis.set_facecolor(BACKGROUND)

    draw_grid(axis)
    draw_series(axis)

    # 两个坐标轴在 XML 里都是 spPr noFill + ln noFill，而且 majorTickMark=none：
    # 既没有轴线也没有刻度线，连类别轴的底线都没有（最下面那条是 0 的网格线）。
    axis.set_xlim(-0.5, len(CATEGORIES) - 0.5)
    axis.set_ylim(0, Y_MAX)
    for spine in axis.spines.values():
        spine.set_visible(False)

    # 数值轴标签：9pt #F2F2F2，右对齐，实测墨迹右缘在 x=90（绘图区左缘 108.26），
    # 数字右侧还有约 1.3px 的留白，故 pad 取到 91.3px = 16.96px = 12.2pt。
    axis.set_yticks(Y_TICKS)
    axis.set_yticklabels([str(int(v)) for v in Y_TICKS], color=LABEL_COLOR,
                         fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS)
    axis.tick_params(axis="y", length=0, pad=12.2, labelright=False)
    # Excel 把刻度文字按行框垂直居中，matplotlib 按墨迹包围盒居中；实测复刻图
    # 比原图低 2px（原图七条刻度文字的中心 222/273/…，复刻图 224/…），补个微调。
    shift = ScaledTranslation(0, 2.0 / chartkit.DPI, figure.dpi_scale_trans)
    for label in axis.get_yticklabels():
        label.set_transform(label.get_transform() + shift)

    # 类别轴标签：9pt #F2F2F2，居中在数据点下方；实测「月」墨迹 543~558，
    # 绘图区底缘 527.86px，即标签行盒顶到轴线 15.1px。
    axis.set_xticks(np.arange(len(CATEGORIES)))
    axis.set_xticklabels(CATEGORIES, color=LABEL_COLOR,
                         fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS)
    axis.tick_params(axis="x", length=0, pad=10.9)

    draw_data_labels(figure)
    draw_legend(figure)

    # ---- 标题 / 副标题 ----
    figure.text(TEXT_LEFT_PX / FIG_W_PX, 1.0 - TITLE_BASELINE_PX / FIG_H_PX,
                TITLE, ha="left", va="baseline", color="white",
                fontsize=20 * FONT_SCALE, fontweight="bold", fontfamily=UI_FONT)
    figure.text(TEXT_LEFT_PX / FIG_W_PX, 1.0 - SUBTITLE_BASELINE_PX / FIG_H_PX,
                SUBTITLE, ha="left", va="baseline", color="white",
                fontsize=12 * FONT_SCALE, fontfamily=UI_FONT)
    figure.text(FOOTNOTE_LEFT_PX / FIG_W_PX, 1.0 - FOOTNOTE_BASELINE_PX / FIG_H_PX,
                FOOTNOTE, ha="left", va="baseline", color=FOOTNOTE_COLOR,
                fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)

    return chartkit.save(figure, "chart13_compare_line.png")


if __name__ == "__main__":
    if matplotlib.get_backend().lower() == "agg":
        main()
    else:
        main()
        plt.show()
