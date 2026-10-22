# -*- coding: utf-8 -*-
"""
图表复刻 5/15 —— 簇状柱形图（工作簿里叫「层叠柱形图」）

复刻对象：`第二章 图表(前15).xlsx` 工作表「5 层叠柱形图」中的图表。
原始图表由 Excel 生成，本脚本用 matplotlib 逐像素还原其外观。

数据来源：
  '5 层叠柱形图'!$B$3:$B$8    类别  2021Q1 / Q2 / Q3 / Q4 / 2022Q1 / Q2
  '5 层叠柱形图'!$C$3:$C$8    销售额 3121 4086 4321 4601 4936 4231
  '5 层叠柱形图'!$D$3:$D$8    利润额 1020 1421 1502 1623 1781 1432

样式规格全部取自该 xlsx 的图表 XML（xl/charts/chart5.xml、
xl/drawings/drawing10.xml），关键参数如下：

    XML 里的定义                                  matplotlib 实现
    -------------------------------------------   ------------------------------
    图表区背景 srgbClr 1A1E43                     figure 底色 chartkit.BACKGROUND
    绘图区 manualLayout                           chartkit.plot_area()
      x=0.0882353 y=0.2642642 w=0.8088235 h=0.5806152
    柱形系列 0「销售额」srgbClr 0070C0            bar(facecolor="#0070C0")
    柱形系列 1「利润额」srgbClr E74E69            bar(facecolor="#E74E69")
    系列边框 ln/noFill                             edgecolor="none"
    gapWidth=219% overlap=30%                     BAR_WIDTH=1/(2+2.19-0.30)
                                                  SERIES_STEP=0.70*BAR_WIDTH
    数值轴 delete="1"                             不画 y 轴、不画网格线
    ylim 由 Excel 自动取整                         Y_MAX=6000
    类别轴轴线 bg1 lumMod95% alpha20%，9525EMU    bottom spine #F2F2F2 alpha .2
    类别标签 9pt bg1 lumMod95%（#F2F2F2）          xticklabels #F2F2F2
    数据标签 dLblPos="outEnd" showVal=1 9pt       柱顶上方基线
              bg1 lumMod95%（#F2F2F2）
    数据标签（手工拖过的）系列1 第6点有             见 MOVED_LABEL
      c:dLbl/c:layout/c:manualLayout y=0.0096096
    标题 微软雅黑 20pt 加粗 白色                   userShapes 文本框 11
    副标题 微软雅黑 12pt 白色                      同一文本框的第 2 段
    脚注 微软雅黑 8pt bg1 lumMod85%（#D9D9D9）    userShapes 文本框 12
    图例 不是 Excel 图例，而是 userShapes 里手工放的   legend_boxes() +
      两个矩形（文本框 6 / 7）：填充 1A1E43、           patches.Rectangle
      描边 0070C0 / E74E69、内含 8pt #F2F2F2 文字
      「销售额」「利润额」，压在最后一组柱子上

坐标轴/数据标签的 Latin 字体继承主题 (+mn-lt = Calibri)，中日韩字形
继承工作簿默认字体（等线 / DengXian）。

运行：python chart5_clustered_bar.py
输出：chart5_clustered_bar.png（832 x 588，与 Excel 导出图等比同尺寸）
"""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

import chartkit

# --------------------------------------------------------------------------
# 常量：全部按 Excel 图表的原始定义换算
# --------------------------------------------------------------------------

# Excel 图表对象尺寸 416 x 294 pt；按 2 px/pt 导出，画布取 832 x 588 px，
# 1 个参考像素 = 1 个输出像素。
DPI = chartkit.DPI
FIG_W_PX, FIG_H_PX = 832, chartkit.height_px_of(5)

# 字号换算：画布尺寸是 Excel 图表的 1.44 倍（= 2 * 72 / 100），
# 所以 matplotlib 字号 = Excel 字号 * 1.44。
FONT_SCALE = chartkit.FONT_SCALE

BACKGROUND = chartkit.BACKGROUND
SALES_COLOR = "#0070C0"      # 系列 0 srgbClr
PROFIT_COLOR = "#E74E69"     # 系列 1 srgbClr
LABEL_COLOR = "#F2F2F2"      # bg1 lumMod 95%：坐标轴标签 / 数据标签 / 图例文字
AXIS_LINE_ALPHA = 0.20       # 类别轴轴线 bg1 lumMod95% alpha=20000
FOOTNOTE_COLOR = "#D9D9D9"   # bg1 lumMod 85%

CATEGORIES = ["2021Q1", "Q2", "Q3", "Q4", "2022Q1", "Q2"]
SALES = [3121, 4086, 4321, 4601, 4936, 4231]
PROFIT = [1020, 1421, 1502, 1623, 1781, 1432]

TITLE = "2021年至今季度销售额(万)和利润额(万)"
SUBTITLE = "2022年第二季度销售额首次出现下降，降幅达到15%"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.06.30"

# 绘图区在图表中的相对位置（取自 chart5.xml 的 manualLayout）
AXES_LEFT = 0.088235311146231121
AXES_TOP = 0.26426422855734538
AXES_WIDTH = 0.80882349251649921
AXES_HEIGHT = 0.58061518247851684

# gapWidth=219%、overlap=30%：
# 单根柱宽 b 时类别宽 = 2b - 0.3b + 2.19b，解出 b = 类别宽 / 3.89
GAP_WIDTH = 219.0 / 100.0
OVERLAP = 30.0 / 100.0
BAR_WIDTH = 1.0 / (2.0 + GAP_WIDTH - OVERLAP)
# 相邻两个系列起点之间的距离：第二系列相对「不重叠」左移 overlap * b
SERIES_STEP = (1.0 - OVERLAP) * BAR_WIDTH
# 整个簇（两根柱子加在一起）占的宽度
CLUSTER_WIDTH = 2.0 * BAR_WIDTH - OVERLAP * BAR_WIDTH

# 数值轴在 XML 里是 delete="1"（整条轴被删掉，无标签无网格线），
# 范围由 Excel 按最大值 4936 自动取整为 0~6000。
Y_MAX = 6000

# ---- 文字基线（单位 px，全部为在 reference/chart5_excel.png 上的实测值）----
# 文本框 bodyPr 没写 lIns，取 DrawingML 默认值 91440EMU = 7.2pt = 14.4px
TEXT_INSET_PX = 7.2 * chartkit.PX_PER_PT
# 标题/副标题文本框 11：relSizeAnchor from x=0.03921
TITLE_LEFT_PX = 0.03921 * FIG_W_PX + TEXT_INSET_PX
# 脚注文本框 12：relSizeAnchor from x=0.02911
FOOTNOTE_SHIFT_PX = 0.5        # 实测：脚注墨迹左缘在原图 x=40，补半个像素
FOOTNOTE_LEFT_PX = 0.02911 * FIG_W_PX + TEXT_INSET_PX + FOOTNOTE_SHIFT_PX
TITLE_BASELINE_PX = 85.0       # 实测：标题「2021」数字墨迹 54~85（底边 85）
SUBTITLE_BASELINE_PX = 134.0   # 实测：副标题「2022」数字墨迹 114~133
FOOTNOTE_BASELINE_PX = 563.0   # 实测：脚注「2022.06.30」数字墨迹 551~562

# ---- 数据标签 ----
# 默认（outEnd）：标签基线在柱顶上方 14px —— 实测 11 个标签的墨迹底边
# 都比柱顶低 14~15px，折中取 14。
LABEL_GAP_PX = 14.0
# 系列 1 第 6 个点（2022Q2 利润额 1432）的标签被手工拖动过，
# chart5.xml 里带 c:dLbl/c:layout/c:manualLayout y=9.6096e-3。
# manualLayout 的 y 是相对图表区高度的位移：0.0096096 * 588 ≈ 5.65px，
# 实测该标签墨迹 396~406（基线 407），而默认位置应是 400.8，正好低 6px。
MOVED_LABEL_INDEX = 5
MOVED_LABEL_BASELINE_PX = 407.0

plt.rcParams["axes.unicode_minus"] = False

# 标题/副标题/脚注在 XML 中显式指定了「微软雅黑」
UI_FONT = chartkit.UI_FONT
# 坐标轴与数据标签：Latin 用 Calibri，中文回退到等线（工作簿默认字体）
AXIS_FONTS = chartkit.AXIS_FONTS


def bar_top_px(value, bottom_px, height_px, y_max):
    """数据值 -> 柱顶在画布里的 y 像素（用于手工摆放被拖动过的标签）。"""
    return bottom_px - value * height_px / y_max


def legend_boxes():
    """从 userShapes 里挑出两个手工图例框。

    标题和脚注的文本框 ln/noFill（没有描边），图例框则填 1A1E43 底色、
    带 0070C0 / E74E69 描边，1 个段落 1 段文字，据此筛出来。
    返回 [(relSizeAnchor 的 (x0,y0,x1,y1), 底色, 描边色, 文字)]，
    位置按 userShapes 的 relSizeAnchor 相对坐标 × 画布尺寸换算成像素。
    """
    boxes = []
    for shape in chartkit.user_shapes(5):
        line = shape["line"]
        if not shape["rel"] or not shape["fill"] or not line or not line["fill"]:
            continue
        text = "".join(run["text"] for run in shape["paragraphs"][0])
        boxes.append((shape["rel"], shape["fill"][0], line["fill"][0], text))
    return boxes


def main():
    figure = chartkit.new_figure(FIG_W_PX, FIG_H_PX)

    layout = chartkit.manual_layout(5)
    axis = chartkit.plot_area(figure, layout, FIG_H_PX)
    axis.set_facecolor(BACKGROUND)

    positions = np.arange(len(CATEGORIES))
    left = positions - CLUSTER_WIDTH / 2.0      # 每簇左缘

    # ---- 柱形：两根柱子共用一簇，系列 1 压在系列 0 上面（overlap）----
    axis.bar(left, SALES, width=BAR_WIDTH, color=SALES_COLOR,
             edgecolor="none", align="edge", zorder=2)
    axis.bar(left + SERIES_STEP, PROFIT, width=BAR_WIDTH, color=PROFIT_COLOR,
             edgecolor="none", align="edge", zorder=3)

    # ---- 坐标范围：每个类别占 1 格，两侧各留半格 ----
    axis.set_xlim(-0.5, len(CATEGORIES) - 0.5)
    axis.set_ylim(0, Y_MAX)

    # ---- 数值轴在 XML 里是 delete="1"：不要刻度、不要网格线 ----
    axis.set_yticks([])
    axis.grid(False)

    axis.set_xticks(positions)
    axis.set_xticklabels(CATEGORIES, color=LABEL_COLOR,
                         fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS)
    # pad 10.4pt = 14.4px：轴线到类别标签行盒顶的距离（实测墨迹顶在 y=513）
    axis.tick_params(axis="x", length=0, pad=10.4)

    # 只保留类别轴线（底部脊线）：bg1 lumMod95% alpha20%，9525EMU = 0.75pt。
    # Excel 把这条 0.75pt(1.5px) 的线栅格化成整齐的 2px，故线宽取 1.0*FONT_SCALE = 1.44pt = 2px；
    # 而且它压在柱子上（原图柱底那一行是「柱色 + 20% 轴线色」），故 zorder 调高。
    for name, spine in axis.spines.items():
        spine.set_visible(name == "bottom")
    axis.spines["bottom"].set_color(LABEL_COLOR)
    axis.spines["bottom"].set_alpha(AXIS_LINE_ALPHA)
    axis.spines["bottom"].set_linewidth(1.0 * FONT_SCALE)
    axis.spines["bottom"].set_zorder(10)

    # ---- 数据标签：outEnd，基线在柱顶上方 14px ----
    bottom_px = (AXES_TOP + AXES_HEIGHT) * FIG_H_PX
    height_px = AXES_HEIGHT * FIG_H_PX
    px_per_unit = AXES_WIDTH * FIG_W_PX / len(CATEGORIES)
    for series, values in enumerate((SALES, PROFIT)):
        # outEnd 标签对齐的是「柱子本身」的中心，不是类别中心：
        # 簇宽 0.437 类别宽、柱宽 0.257 类别宽，两根柱心各偏离类别中心 ±0.09 格
        bar_center = left + (0.0 if series == 0 else SERIES_STEP) + BAR_WIDTH / 2.0
        for index, value in enumerate(values):
            x = (AXES_LEFT * FIG_W_PX
                 + (bar_center[index] + 0.5) * px_per_unit) / FIG_W_PX
            if series == 1 and index == MOVED_LABEL_INDEX:
                baseline = MOVED_LABEL_BASELINE_PX
            else:
                baseline = bar_top_px(value, bottom_px, height_px, Y_MAX) \
                    - LABEL_GAP_PX
            figure.text(x, 1.0 - baseline / FIG_H_PX, str(value),
                        ha="center", va="baseline", color=LABEL_COLOR,
                        fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS,
                        zorder=5)

    # ---- 图例：userShapes 里手工放的两个描边小方框（不是 Excel 图例）----
    for rel, face, edge, text in legend_boxes():
        x0, y0, x1, y1 = rel
        left_px, top_px = x0 * FIG_W_PX, y0 * FIG_H_PX
        width_px = (x1 - x0) * FIG_W_PX
        height_px_box = (y1 - y0) * FIG_H_PX
        figure.add_artist(Rectangle(
            (left_px / FIG_W_PX, 1.0 - (top_px + height_px_box) / FIG_H_PX),
            width_px / FIG_W_PX, height_px_box / FIG_H_PX,
            transform=figure.transFigure, facecolor=face,
            # 框线 9525EMU = 0.75pt，和坐标轴线一样被 Excel 栅格化成 2px；
            # snap=False 免得 matplotlib 把边框对到整像素上又偏半个像素
            edgecolor=edge, linewidth=1.0 * FONT_SCALE, zorder=6, snap=False))
        figure.text((left_px + width_px / 2.0) / FIG_W_PX,
                    1.0 - (top_px + height_px_box / 2.0) / FIG_H_PX,
                    text, ha="center", va="center", color=LABEL_COLOR,
                    fontsize=8 * FONT_SCALE, fontfamily=UI_FONT, zorder=7)

    # ---- 标题 / 副标题 / 脚注 ----
    figure.text(TITLE_LEFT_PX / FIG_W_PX, 1.0 - TITLE_BASELINE_PX / FIG_H_PX,
                TITLE, ha="left", va="baseline", color="white",
                fontsize=20 * FONT_SCALE, fontweight="bold", fontfamily=UI_FONT)
    figure.text(TITLE_LEFT_PX / FIG_W_PX, 1.0 - SUBTITLE_BASELINE_PX / FIG_H_PX,
                SUBTITLE, ha="left", va="baseline", color="white",
                fontsize=12 * FONT_SCALE, fontfamily=UI_FONT)
    figure.text(FOOTNOTE_LEFT_PX / FIG_W_PX, 1.0 - FOOTNOTE_BASELINE_PX / FIG_H_PX,
                FOOTNOTE, ha="left", va="baseline", color=FOOTNOTE_COLOR,
                fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)

    chartkit.save(figure, "chart5_clustered_bar.png")
    return figure


if __name__ == "__main__":
    if matplotlib.get_backend().lower() == "agg":
        main()
    else:
        main()
        plt.show()
