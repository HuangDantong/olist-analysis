# -*- coding: utf-8 -*-
"""图表复刻 9/15 —— 对比柱形图（带差值箭头）

复刻对象：`第二章 图表(前15).xlsx` 工作表「9 对比柱形图」中的图表。

**注意编号**：工作表序号是 9，但对应的图表部件是 xl/charts/chart8.xml
（userShapes 是 xl/drawings/drawing17.xml）。核对方法：chart8.xml 里所有
c:f 公式都指向 '9 对比柱形图'!，且 reference/chart9_excel.png 与该工作表
导出的图一致。

这张图的机关是**用一条折线系列 + 误差线冒充「差值箭头」**：

    系列0  2021销量  #0070C0  柱形，标签 dLblPos="outEnd"（柱顶外侧）
    系列1  2022销量  #82ADD7  柱形，标签 dLblPos="inEnd"（柱内顶部）
                   外加一条 errBars：errBarType=plus、errValType=cust、
                   值取 $E$3:$E$7（= 2021 − 2022 的差值），线色 bg1 lumMod95%
                   = #F2F2F2、线宽 9525EMU = 0.75pt，
                   `noEndCap=1` + `tailEnd type="triangle"` —— 顶端那个三角箭头
    系列2  折线（值同系列0）  线 noFill（看不见），只保留 marker：
                   `symbol="picture"` + blipFill 指到 media/image5.png
                   （50×1 的深蓝细条），画在深蓝柱顶，向右拖出一条细线
                   dLblPos="r"，标签内容来自 c15:datalabelsRange = $E$3:$E$7

所以肉眼看是「浅蓝柱顶伸出一根带三角箭头的白线，指到深蓝柱顶，旁边写差值」，
实际是：误差线负责那根竖线和箭头，折线的图片标记负责深蓝细横线，
标签来自单元格区域而不是系列值。

数据来源：
  '9 对比柱形图'!$B$3:$B$7   类别 口红/面膜/隔离/防晒/精华
  '9 对比柱形图'!$C$3:$C$7   系列0 2021销量 [3568,4135,4436,4106,4936]
  '9 对比柱形图'!$D$3:$D$7   系列1 2022销量 [2569,3241,2965,3209,3541]
  '9 对比柱形图'!$E$3:$E$7   差值         [999, 894, 1471, 897, 1395]

样式规格全部取自 chart8.xml 与 drawing17.xml：

    XML 里的定义                              matplotlib 实现
    --------------------------------------   ------------------------------------
    图表区底色 srgbClr 1A1E43                chartkit.BACKGROUND
    绘图区 manualLayout x=.063725 y=.291422  chartkit.plot_area(figure, layout, ...)
        w=.855392 h=.544776                  （实测柱底 538、绘图区底 539.4）
    barDir=col grouping=clustered            axis.bar(...)，两条并排
    gapWidth=219 overlap=-27                 柱宽 32px（实测），两根柱心相距 40px
    valAx delete="1"（无轴无网格）           不画数值轴、不画网格线
    valAx 自动刻度：实测 17.10 值/px           ylim 0~6000（351.38px 高）
    系列0 填充 srgbClr 0070C0                 BAR_2021
    系列1 填充 srgbClr 82ADD7                 BAR_2022
    数据标签 9pt bg1 lumMod95%                #F2F2F2，9 × FONT_SCALE
    误差线 ln w=9525(0.75pt) bg1 lumMod95%    #F2F2F2 竖线，宽 2px（实测）
        noEndCap + tailEnd=triangle           顶端画 10×10px 三角（实测）
    折线 marker symbol=picture               深蓝细横线，长 60px（实测）
        blip=media/image5.png                取自 xlsx 里的 image5.png
    图例 manualLayout x=.050342 y=.266916    两个色块 + 文字，位置照实测
        w=.271332 h=.052879，entry idx=2 删除
    标题 20pt 粗 / 副标题 12pt / 脚注 8pt     微软雅黑，来自 userShapes 文本库

坐标轴/数据标签的 Latin 字形继承主题字体（+mn-lt = Calibri），中日韩字形
继承工作簿默认字体（等线 / DengXian）。

运行：python chart9_compare_column.py
输出：chart9_compare_column.png（832 x 645，与 Excel 导出图同尺寸）
"""

import io
import os
import zipfile

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Rectangle

import chartkit

# --------------------------------------------------------------------------
# 常量
# --------------------------------------------------------------------------

DPI = chartkit.DPI
FIG_W_PX = 832
FIG_H_PX = chartkit.height_px_of(9)          # 图表对象高 322.5pt × 2 = 645
FONT_SCALE = chartkit.FONT_SCALE             # 1.44

BACKGROUND = chartkit.BACKGROUND
BAR_2021 = "#0070C0"        # 系列0 srgbClr
BAR_2022 = "#82ADD7"        # 系列1 srgbClr
LABEL_COLOR = "#F2F2F2"     # bg1 lumMod95000：数据标签 / 类别标签 / 箭头 / 图例
FOOTNOTE_COLOR = "#D9D9D9"  # bg1 lumMod85000

CATEGORIES = ["口红", "面膜", "隔离", "防晒", "精华"]
SALES_2021 = [3568, 4135, 4436, 4106, 4936]     # $C$3:$C$7
SALES_2022 = [2569, 3241, 2965, 3209, 3541]     # $D$3:$D$7
DELTAS = [999, 894, 1471, 897, 1395]            # $E$3:$E$7 = 差值，也是误差线长度

# 数值轴：轴被 delete="1"，范围由 Excel 按最大值 4936 自动取整；
# 实测 17.10 值/px × 绘图区 351.38px = 6009，即 0~6000
Y_MAX = 6000.0

# 绘图区（chart8.xml 的 manualLayout）
LAYOUT = {"x": "6.3725490196078427E-2", "y": "0.29142189259162665",
          "w": "0.85539215686274506", "h": "0.54477585977600662"}
PLOT_LEFT_PX = 0.063725490196078427 * FIG_W_PX        # 53.02
PLOT_WIDTH_PX = 0.85539215686274506 * FIG_W_PX        # 711.69
PLOT_BOTTOM_PX = (0.29142189259162665 + 0.54477585977600662) * FIG_H_PX   # 539.4
PLOT_HEIGHT_PX = 0.54477585977600662 * FIG_H_PX       # 351.38

# 一根柱子的宽度与两根柱心的左右偏移，全部由实测反推：
# 每个类别占 711.69 / 5 = 142.34px，柱宽实测 32px，两根柱心实测相距 40px
BAR_WIDTH = 32.0 / 142.34                             # 数据坐标下的柱宽
BAR_SHIFT = 20.3 / 142.34                             # 数据坐标下的 ±偏移

# ---- 以下落点均为「实测」：在 reference/chart9_excel.png 上量出墨迹行/列范围

# 数据标签：系列0 dLblPos="outEnd"，实测「3568」墨迹 305~315，柱顶 330，
# 即基线比柱顶高 15px（matplotlib 的 offset points 正数向上）
OUT_END_GAP_PX = 15.0
# 系列1 dLblPos="inEnd"，实测贴在柱内顶端，基线比柱顶低 15px
IN_END_GAP_PX = 15.0

# 误差线：竖线宽 2px，从浅蓝柱顶拉到深蓝柱顶；顶端三角实测 10px 宽 10px 高
ARROW_WIDTH_PX = 2.0
ARROW_HEAD_W_PX = 10.0
ARROW_HEAD_H_PX = 10.0

# 折线的图片标记（image5.png 拉伸出来的一条细横线）：实测自深蓝柱左缘起、长 60px
MARKER_LINE_LEN_PX = 60.0

# 差值标签：内容来自 $E$3:$E$7，落点 = 系列2 的 dLblPos="r" 默认锚点 +
# manualLayout 偏移。实测标签墨迹左缘 = 深蓝柱左缘 + 63px；纵向
# 标签中心 = 深蓝柱顶 + y 偏移比例 × 画布高（六个点逐个核对，残差 < 1px）。
DELTA_LABEL_INK_LEFT_PX = 63.0
DELTA_LABEL_X_FRAC = [-1.1204454222633912e-2, -1.1204454222633935e-2,
                      -1.435579743708516e-2, -1.085436930677783e-2,
                      -4.901960784313905e-3]
DELTA_LABEL_Y_FRAC = [6.1300500112635756e-2, 4.7786923247551627e-2,
                      8.5193838367563668e-2, 5.0920491985096059e-2,
                      7.5401559431585372e-2]
DELTA_LABEL_X_REF = DELTA_LABEL_X_FRAC[0]             # 以第 0 个点为基准
DELTA_LABEL_BASELINE_DY_PX = 5.5                      # 墨迹高 11px，基线在中心下方

# 图例：manualLayout (0.050342, 0.266916) 尺寸 (0.271332, 0.052879)
LEGEND_LEFT_PX = 64.0                                 # 实测：第一个色块左缘
LEGEND_TOP_PX = 178.2                                 # 实测：色块顶边 = 181.2
LEGEND_SWATCH_W_PX = 9.0                              # 实测色块 9×9px
LEGEND_SWATCH_H_PX = 9.0
LEGEND_ENTRY_PITCH_PX = 106.0                         # 实测两个色块相距 106px
LEGEND_TEXT_GAP_PX = 7.0                              # 实测色块右缘到文字

# 标题 / 副标题 / 脚注（userShapes 文本框 rel 左缘 + 默认左内缩 lIns=7.2pt）
TEXT_INSET_PX = 7.2 * chartkit.PX_PER_PT              # 14.4px
TITLE_TEXT_X_PX = 0.04105 * FIG_W_PX + TEXT_INSET_PX  # 48.55
FOOTNOTE_TEXT_X_PX = 0.02819 * FIG_W_PX + TEXT_INSET_PX   # 37.85
TITLE = "2022年商品对比去年销售情况"
SUBTITLE = "商品整体比去年销量有所下降，其中隔离下降最多，下降33%"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.01.01"
TITLE_BASELINE_PX = 84.0        # 实测：标题墨迹 51~89（20pt 加粗）
SUBTITLE_BASELINE_PX = 134.5    # 实测：副标题墨迹 114~137（12pt）
FOOTNOTE_BASELINE_PX = 615.0    # 实测：脚注墨迹 603~617（8pt）

plt.rcParams["axes.unicode_minus"] = False

UI_FONT = chartkit.UI_FONT                   # 微软雅黑
AXIS_FONTS = chartkit.AXIS_FONTS             # Calibri + 等线


def value_px(value):
    """销量 value 对应的纵坐标（像素，自上而下）。"""
    return PLOT_BOTTOM_PX - value / Y_MAX * PLOT_HEIGHT_PX


def category_center_px(index):
    """第 index 个类别的中心横坐标（像素）。"""
    return PLOT_LEFT_PX + (index + 0.5) * PLOT_WIDTH_PX / len(CATEGORIES)


def marker_image():
    """把 image5.png 从 xlsx 里读出来，用作折线系列那条深蓝细横线。"""
    with zipfile.ZipFile(chartkit.XLSX) as archive:
        data = archive.read("xl/media/image5.png")
    from PIL import Image
    return np.array(Image.open(io.BytesIO(data)).convert("RGBA"))


def main():
    layout = chartkit.manual_layout(8)       # 图9 的图表部件是 chart8.xml
    figure = chartkit.new_figure(FIG_W_PX, FIG_H_PX)
    axis = chartkit.plot_area(figure, layout, FIG_H_PX)
    axis.set_xlim(-0.5, len(CATEGORIES) - 0.5)
    axis.set_ylim(0, Y_MAX)

    positions = np.arange(len(CATEGORIES), dtype=float)
    axis.bar(positions - BAR_SHIFT, SALES_2021, width=BAR_WIDTH,
             color=BAR_2021, edgecolor="none", zorder=2)
    axis.bar(positions + BAR_SHIFT, SALES_2022, width=BAR_WIDTH,
             color=BAR_2022, edgecolor="none", zorder=2)

    # 两条轴都是 spPr noFill + valAx delete="1"：没有任何轴线/网格线
    for spine in axis.spines.values():
        spine.set_visible(False)
    axis.set_yticks([])

    axis.set_xticks(positions)
    axis.set_xticklabels(CATEGORIES, color=LABEL_COLOR,
                         fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS)
    axis.tick_params(axis="x", length=0, pad=11.72)

    # ---- 数据标签：系列0 outEnd（柱顶外）/ 系列1 inEnd（柱内顶端）----
    dy_pt = 72.0 / DPI
    for index, position in enumerate(positions):
        axis.annotate(str(SALES_2021[index]),
                      xy=(position - BAR_SHIFT, SALES_2021[index]),
                      xytext=(0, OUT_END_GAP_PX * dy_pt), textcoords="offset points",
                      ha="center", va="baseline", color=LABEL_COLOR,
                      fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS, zorder=5)
        axis.annotate(str(SALES_2022[index]),
                      xy=(position + BAR_SHIFT, SALES_2022[index]),
                      xytext=(0, -IN_END_GAP_PX * dy_pt), textcoords="offset points",
                      ha="center", va="baseline", color=LABEL_COLOR,
                      fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS, zorder=5)

    # ---- overlay：全部按实测像素落点，y 轴向下 ----
    overlay = figure.add_axes([0, 0, 1, 1], zorder=6)
    overlay.set_xlim(0, FIG_W_PX)
    overlay.set_ylim(FIG_H_PX, 0)
    overlay.set_axis_off()
    overlay.patch.set_visible(False)

    marker = marker_image()

    for index, position in enumerate(positions):
        centre = category_center_px(index)
        # 深蓝柱心 = 类别中心 − 20.3px，柱宽 32px
        dark_left = centre - BAR_SHIFT * (PLOT_WIDTH_PX / len(CATEGORIES)) - BAR_WIDTH * (PLOT_WIDTH_PX / len(CATEGORIES)) / 2.0
        dark_top = value_px(SALES_2021[index])
        light_top = value_px(SALES_2022[index])

        # 折线的图片标记：一条深蓝细横线，从深蓝柱左缘往右伸出 60px（实测）
        overlay.imshow(marker, extent=(dark_left, dark_left + MARKER_LINE_LEN_PX,
                                       dark_top + 0.5, dark_top - 0.5),
                       aspect="auto", zorder=7, interpolation="bilinear")

        # 误差线：竖线 + 顶端三角，颜色 #F2F2F2
        shaft_x = centre + BAR_SHIFT * (PLOT_WIDTH_PX / len(CATEGORIES))
        shaft_top = dark_top + ARROW_HEAD_H_PX
        overlay.add_patch(Rectangle((shaft_x - ARROW_WIDTH_PX / 2.0, shaft_top),
                                    ARROW_WIDTH_PX, light_top - shaft_top,
                                    facecolor=LABEL_COLOR, edgecolor="none", zorder=8))
        overlay.add_patch(Polygon(
            [(shaft_x, shaft_top - ARROW_HEAD_H_PX),
             (shaft_x - ARROW_HEAD_W_PX / 2.0, shaft_top),
             (shaft_x + ARROW_HEAD_W_PX / 2.0, shaft_top)],
            closed=True, facecolor=LABEL_COLOR, edgecolor="none", zorder=8))

        # 差值标签：内容取自 $E$3:$E$7，位置 = 实测锚点 + manualLayout 偏移
        label_x = (dark_left + DELTA_LABEL_INK_LEFT_PX
                   + (DELTA_LABEL_X_FRAC[index] - DELTA_LABEL_X_REF) * FIG_W_PX)
        label_y = dark_top + DELTA_LABEL_Y_FRAC[index] * FIG_H_PX
        overlay.text(label_x, label_y + DELTA_LABEL_BASELINE_DY_PX,
                     str(DELTAS[index]), ha="left", va="baseline",
                     color=LABEL_COLOR, fontsize=9 * FONT_SCALE,
                     fontfamily=AXIS_FONTS, zorder=9)

    # ---- 图例：色块 + 文字（entry idx=2 在 XML 里被删除，所以只有两项）----
    for entry, (colour, name) in enumerate(((BAR_2021, "2021销量"),
                                            (BAR_2022, "2022销量"))):
        left = LEGEND_LEFT_PX + entry * LEGEND_ENTRY_PITCH_PX
        overlay.add_patch(Rectangle((left, LEGEND_TOP_PX + 4.3),
                                    LEGEND_SWATCH_W_PX, LEGEND_SWATCH_H_PX,
                                    facecolor=colour, edgecolor="none", zorder=8))
        overlay.text(left + LEGEND_SWATCH_W_PX + LEGEND_TEXT_GAP_PX,
                     LEGEND_TOP_PX + 15.0, name, ha="left", va="baseline",
                     color=LABEL_COLOR, fontsize=9 * FONT_SCALE,
                     fontfamily=AXIS_FONTS, zorder=9)

    # ---- 标题 / 副标题 / 脚注 ----
    figure.text(TITLE_TEXT_X_PX / FIG_W_PX, 1.0 - TITLE_BASELINE_PX / FIG_H_PX,
                TITLE, ha="left", va="baseline", color="white",
                fontsize=20 * FONT_SCALE, fontweight="bold", fontfamily=UI_FONT)
    figure.text(TITLE_TEXT_X_PX / FIG_W_PX, 1.0 - SUBTITLE_BASELINE_PX / FIG_H_PX,
                SUBTITLE, ha="left", va="baseline", color="white",
                fontsize=12 * FONT_SCALE, fontfamily=UI_FONT)
    figure.text(FOOTNOTE_TEXT_X_PX / FIG_W_PX, 1.0 - FOOTNOTE_BASELINE_PX / FIG_H_PX,
                FOOTNOTE, ha="left", va="baseline", color=FOOTNOTE_COLOR,
                fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)

    return chartkit.save(figure, "chart9_compare_column.png")


if __name__ == "__main__":
    if matplotlib.get_backend().lower() == "agg":
        main()
    else:
        main()
        plt.show()
