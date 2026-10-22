# -*- coding: utf-8 -*-
"""
图表复刻 11/15 —— 平滑折线图

复刻对象：`第二章 图表(前15).xlsx` 工作表「11 平滑折线图」中的图表。
（注意编号错位：工作表 11 对应 xl/charts/chart10.xml，userShapes 是
xl/drawings/drawing21.xml，比对基准是 reference/chart11_excel.png。）

这张图的结构比柱形图简单，但有三处容易做错：

  1. **折线是平滑的**（`c:smooth val="1"`）。Excel 的平滑 = 相邻点之间插一段
     三次贝塞尔，控制点取「相邻两点的差向量 / 6」，也就是均匀参数化的
     Catmull-Rom 样条。用 `Path.CURVE4` 逐段拼出来即可，不用 scipy。
  2. **绘图区下方那条年份色带不是坐标轴**，是 userShapes 里的两个圆角矩形
     （2021 浅蓝 #66CBDD、2022 黄 #F5C353），连同顶端那条竖直虚线、标题、
     副标题、脚注一起，都按 relSizeAnchor 的比例 × 画布尺寸落点。
  3. **数值轴标签是橙色的**（srgbClr E66B4C，跟折线同色，不是通用的浅灰），
     字号只有 8pt，换算成 matplotlib 是 11.52pt —— 本机 Calibri 在这个尺寸
     下抗锯齿会渲染成空白，所以用 TextPath + PathPatch 绕过（见 draw_text）。

数据来源：'11 平滑折线图'!$C$3:$C$13（类别）、$D$3:$D$13（销量）

样式规格全部取自该 xlsx 的图表 XML（xl/charts/chart10.xml、
xl/drawings/drawing21.xml）与主题 xl/theme/theme1.xml：

    XML 里的定义                          matplotlib 实现
    -----------------------------------   -----------------------------------
    图表区背景 srgbClr 1A1E43             figure facecolor BACKGROUND
    绘图区 manualLayout x=.116897 y=.292385
        w=.843596 h=.470107               figure.add_axes([...])
    lineChart + smooth=1                  逐段三次贝塞尔（Catmull-Rom，张力 1/6）
    系列线 srgbClr E66B4C w=12700EMU(1pt)
        cap=rnd + a:round                 线宽 1.44pt(=2px)，圆头圆角
    marker symbol=none                    不画标记点
    catAx majorTickMark=out                每两个类别之间一根 6px 短刻度
    catAx 轴线 srgbClr D9D9D9 w=6350(0.5pt) 底边 spine 1px 浅灰
    catAx 文字 9pt bg1 lumMod95%          #F2F2F2，9 × FONT_SCALE
    valAx max=4000 majorUnit=1000         刻度 0..4000 步长 1000
    valAx numFmt '#,##0'                  '4,000' 千分位
    valAx 文字 8pt srgbClr E66B4C          #E66B4C，8 × FONT_SCALE
    valAx 轴线 noFill / 刻度 none          不画左边框、不画刻度线
    c:dLbl idx=8 pos=t                     '3782' 落在 1 月点正上方
    userShapes 圆角矩形 2021/2022          FancyBboxPatch，圆角 = 短边/6
    userShapes 连接符 prstDash=lgDash      #E66B4C 虚线，8×/3× 线宽
    标题/副标题 20pt bold / 14pt 微软雅黑    UI_FONT，逐字符回退
    脚注 8pt bg1 lumMod85%                #D9D9D9

运行：python chart11_smooth_line.py
输出：chart11_smooth_line.png（832 x 616，与 Excel 导出图同尺寸）
"""

import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch, PathPatch
from matplotlib.path import Path
from matplotlib.textpath import TextPath

import chartkit

# --------------------------------------------------------------------------
# 常量：全部按 Excel 图表的原始定义换算
# --------------------------------------------------------------------------

# Excel 图表对象 416.00 x 308.13 pt，2 px/pt 导出成 832 x 616
DPI = chartkit.DPI
FIG_W_PX = 832
FIG_H_PX = 616

FONT_SCALE = chartkit.FONT_SCALE             # 1.44，Excel pt -> matplotlib pt

BACKGROUND = chartkit.BACKGROUND             # 1A1E43
LINE_COLOR = "#E66B4C"                       # 系列线 / 数值轴文字 / 虚线连接符
LABEL_COLOR = "#F2F2F2"                      # bg1 lumMod 95%
FOOTNOTE_COLOR = "#D9D9D9"                   # bg1 lumMod 85%
AXIS_LINE_COLOR = "#D9D9D9"                  # catAx 轴线 srgbClr D9D9D9
BAND_2021 = "#66CBDD"                        # 圆角矩形 1
BAND_2022 = "#F5C353"                        # 圆角矩形 2

XLSX_SHEET = "11 平滑折线图"
CATEGORIES = ["5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月",
              "1月", "2月", "3月"]
VALUES = [146, 198, 296, 412, 506, 615, 789, 1021, 3782, 3215, 2936]

# 绘图区在图表区里的相对位置（chart10.xml 的 manualLayout）
AXES_LAYOUT = {"x": "0.11689671144048171", "y": "0.2923847646798442",
               "w": "0.84359618650609847", "h": "0.4701066067940679"}

Y_MAX = 4000                                 # valAx scaling/max
Y_STEP = 1000                                # valAx majorUnit
Y_TICKS = [0, 1000, 2000, 3000, 4000]

# 绘图区实测比 manualLayout 标注值高 0.7px：按标注值放，整条折线会比原图低
# 0.7px（对 11 个数据点逐个量残差，平均 -0.68，最大 -0.9）
PLOT_DY_PX = -0.7

# 数据标签（c:dLbl idx=8，pos=t，showVal=1）：实测墨迹 x 622~656、底边 y=176
DATA_LABEL_INDEX = 8
DATA_LABEL_BASELINE_PX = 176.5

# userShapes：coord 是 relSizeAnchor 的比例，实测 1.0 = 整个画布(832 x 616)
# （sp 自己的 a:off/a:ext 是 408 x 305.25pt 的旧坐标系，跟渲染结果对不上，
# 比如圆角矩形 1 的 ext 只有 261pt 宽，而实测色带宽 532px = 266pt）
BAND_2021_REL = (0.09325, 0.83552, 0.73338, 0.88698)
BAND_2022_REL = (0.74219, 0.83427, 0.97702, 0.88943)
BAND_TEXT_PT = 10.0                          # 两个矩形的文字都是 sz=1000
# roundRect 的 avLst 为空 -> 预设圆角半径 = 短边的 1/6
BAND_RADIUS_FRAC = 1.0 / 6.0

# 竖直虚线连接符（prstDash=lgDash，线宽取主题 lnStyleLst idx=1 = 6350EMU=0.5pt）
DASH_X_REL = 0.7791
DASH_TOP_REL = 0.30958
DASH_BOTTOM_REL = 0.76167
DASH_WIDTH_PT = 0.5
DASH_DASH_PX = 8.0                           # lgDash = 8 倍线宽
DASH_GAP_PX = 3.0                            #         3 倍线宽

# 标题/副标题文本框：rel 左缘 + bodyPr 默认内边距 lIns=91440EMU(7.2pt)
TEXT_INSET_PX = 7.2 * chartkit.PX_PER_PT     # 14.4px
TITLE_X_REL = 0.03554
TITLE_TEXT_X_PX = TITLE_X_REL * FIG_W_PX + TEXT_INSET_PX     # 43.96px（实测 44）
TITLE_BASELINE = 71.0                        # 实测：标题墨迹 37~76
SUBTITLE_BASELINE = 118.5                    # 实测：副标题墨迹 95~122
FOOTNOTE_X_REL = 0.02819
FOOTNOTE_TEXT_X_PX = FOOTNOTE_X_REL * FIG_W_PX + TEXT_INSET_PX   # 37.9px（实测 39）
FOOTNOTE_BASELINE = 588.0                    # 实测：脚注墨迹 575~589

# 「文本框 11」里是同两段：第一段 20pt 加粗做标题，第二段 14pt 做副标题
TITLE = "化妆品品类月度销量走势"
SUBTITLE = "2022年销量迅速增加，1月最高，销量达到3782"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.03.31"

# 刻度：catAx majorTickMark=out，实测从轴线 469 往下画到 475（6px）
TICK_LENGTH_PX = 6.0
CAT_LABEL_BASELINE = 500.5                   # 实测：类别文字墨迹 485~500
Y_LABEL_COLOR = LINE_COLOR
Y_LABEL_RIGHT_PX = 77.5                      # 实测：数值轴文字墨迹右缘
Y_LABEL_BASELINE_DY_PX = 5.1                 # 实测：基线比刻度值中心低 5.1px

plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["lines.scale_dashes"] = False   # 虚线段长按 XML 给，不再乘线宽

UI_FONT = chartkit.UI_FONT                   # 微软雅黑
AXIS_FONTS = chartkit.AXIS_FONTS             # Calibri + 等线


def value_px(value):
    """销量 value 对应的纵坐标（像素，自上而下）。"""
    top = (float(AXES_LAYOUT["y"]) + float(AXES_LAYOUT["h"])) * FIG_H_PX
    return top + PLOT_DY_PX - value / float(Y_MAX) * float(AXES_LAYOUT["h"]) * FIG_H_PX


def category_px(index):
    """第 index 个类别的中心横坐标（像素），折线点落在类别中心上。"""
    left = float(AXES_LAYOUT["x"]) * FIG_W_PX
    width = float(AXES_LAYOUT["w"]) * FIG_W_PX
    return left + (index + 0.5) * width / len(VALUES)


def smooth_path(xs, ys):
    """把折线点转成 Catmull-Rom 平滑路径（每段一条三次贝塞尔）。

    Excel 的控制点 = 前后相邻点的差向量 / 6：
        c1 = p[i]   + (p[i+1] - p[i-1]) / 6
        c2 = p[i+1] - (p[i+2] - p[i])   / 6
    首尾点没有外邻，就退化成用自己补齐（等价于端点切线减半）。
    """
    verts = [(xs[0], ys[0])]
    codes = [Path.MOVETO]
    for i in range(len(xs) - 1):
        previous = i - 1 if i > 0 else i
        following = i + 2 if i + 2 < len(xs) else i + 1
        control1 = (xs[i] + (xs[i + 1] - xs[previous]) / 6.0,
                    ys[i] + (ys[i + 1] - ys[previous]) / 6.0)
        control2 = (xs[i + 1] - (xs[following] - xs[i]) / 6.0,
                    ys[i + 1] - (ys[following] - ys[i]) / 6.0)
        verts += [control1, control2, (xs[i + 1], ys[i + 1])]
        codes += [Path.CURVE4] * 3
    return Path(verts, codes)


def draw_text(overlay, x_px, y_px, text, size_pt, color, weight="normal",
              align="left"):
    """用 TextPath + PathPatch 画一段文字，落点就是基线。

    Excel 里 8pt 的数值轴标签换算成 matplotlib 是 11.52pt，本机 Calibri 在
    这个尺寸上用普通 text() 走抗锯齿路径会输出空白，所以统一走矢量路径填充。

    TextPath 的坐标是 y 向上、基线在 0，而 overlay 的 y 轴向下，所以先在
    数据坐标里做一次「翻转 + 平移」再交给 transData（顺序不能反，反过来就
    变成在显示坐标里镜像了）。
    """
    font = FontProperties(family=AXIS_FONTS, size=size_pt * FONT_SCALE,
                          weight=weight)
    path = TextPath((0, 0), text, prop=font, size=size_pt * FONT_SCALE)
    box = path.get_extents()
    if align == "right":
        shift_x = -box.x1
    elif align == "center":
        shift_x = -(box.x0 + box.x1) / 2.0
    else:
        shift_x = -box.x0
    transform = (Affine2D().scale(1, -1).translate(x_px + shift_x, y_px)
                 + overlay.transData)
    overlay.add_patch(PathPatch(path, facecolor=color, edgecolor="none",
                                transform=transform, zorder=6))


from matplotlib.transforms import Affine2D          # noqa: E402


def main():
    figure = plt.figure(figsize=(FIG_W_PX / DPI, FIG_H_PX / DPI), dpi=DPI)
    figure.patch.set_facecolor(BACKGROUND)

    axis = chartkit.plot_area(figure, AXES_LAYOUT, FIG_H_PX, dy_px=PLOT_DY_PX)
    axis.set_xlim(-0.5, len(VALUES) - 0.5)
    axis.set_ylim(0, Y_MAX)

    # ---- 折线 ----
    xs = [category_px(i) for i in range(len(VALUES))]
    ys = [value_px(v) for v in VALUES]
    # 换算到 axes 数据坐标
    left = float(AXES_LAYOUT["x"]) * FIG_W_PX
    width = float(AXES_LAYOUT["w"]) * FIG_W_PX
    top = (float(AXES_LAYOUT["y"]) + float(AXES_LAYOUT["h"])) * FIG_H_PX + PLOT_DY_PX
    height = float(AXES_LAYOUT["h"]) * FIG_H_PX

    def to_data(px, py):
        return ((px - left) / width * len(VALUES) - 0.5,
                (top - py) / height * Y_MAX)

    data = [to_data(x, y) for x, y in zip(xs, ys)]
    dx = [p[0] for p in data]
    dy = [p[1] for p in data]
    axis.add_patch(PathPatch(smooth_path(dx, dy), facecolor="none",
                             edgecolor=LINE_COLOR, linewidth=1.0 * FONT_SCALE,
                             capstyle="round", joinstyle="round", zorder=3))

    # ---- 坐标轴 ----
    # catAx：刻度线画在类别交界处，标签落在类别中心（line chart 的规则）
    boundaries = np.arange(len(VALUES) + 1) - 0.5
    axis.set_xticks(boundaries)
    axis.set_xticklabels([])
    axis.set_xticks(np.arange(len(VALUES)), minor=True)
    axis.set_xticklabels(CATEGORIES, minor=True, color=LABEL_COLOR,
                         fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS)
    axis.tick_params(axis="x", which="major", direction="out",
                     length=TICK_LENGTH_PX * 72 / DPI,
                     width=DASH_WIDTH_PT * FONT_SCALE, color=AXIS_LINE_COLOR)
    axis.tick_params(axis="x", which="minor", length=0)
    axis.tick_params(axis="y", length=0)

    # 数值刻度只用来定位置；文字一律由 overlay 上的 draw_text 画（见下），
    # 这里必须清空，否则 matplotlib 会用默认黑色再叠一份出来。
    axis.set_yticks(Y_TICKS)
    axis.set_yticklabels([])

    for side in ("top", "right", "left"):
        axis.spines[side].set_visible(False)
    axis.spines["bottom"].set_color(AXIS_LINE_COLOR)
    axis.spines["bottom"].set_linewidth(DASH_WIDTH_PT * FONT_SCALE)

    # ---- overlay：userShapes 与所有文字 ----
    overlay = figure.add_axes([0, 0, 1, 1], zorder=5)
    overlay.set_xlim(0, FIG_W_PX)
    overlay.set_ylim(FIG_H_PX, 0)            # 纵轴向下，常量直接照实测像素写
    overlay.set_axis_off()
    overlay.patch.set_visible(False)

    # 竖直虚线连接符（prstDash=lgDash：8 倍线宽实、3 倍线宽空，线宽 0.5pt=1px）
    overlay.plot([DASH_X_REL * FIG_W_PX] * 2,
                 [DASH_TOP_REL * FIG_H_PX, DASH_BOTTOM_REL * FIG_H_PX],
                 color=LINE_COLOR, linewidth=DASH_WIDTH_PT * FONT_SCALE,
                 linestyle=(0, (DASH_DASH_PX * 72 / DPI,
                                DASH_GAP_PX * 72 / DPI)),
                 dash_capstyle="butt", zorder=6)

    # 年份色带（两个圆角矩形）
    for rel, color, label in ((BAND_2021_REL, BAND_2021, "2021"),
                              (BAND_2022_REL, BAND_2022, "2022")):
        x0, y0, x1, y1 = (rel[0] * FIG_W_PX, rel[1] * FIG_H_PX,
                          rel[2] * FIG_W_PX, rel[3] * FIG_H_PX)
        radius = (y1 - y0) * BAND_RADIUS_FRAC
        overlay.add_patch(FancyBboxPatch(
            (x0, y0), x1 - x0, y1 - y0,
            boxstyle="round,pad=0,rounding_size=%.3f" % radius,
            facecolor=color, edgecolor="none", mutation_aspect=1.0, zorder=6))
        draw_text(overlay, (x0 + x1) / 2.0, (y0 + y1) / 2.0 + 5.0, label,
                  BAND_TEXT_PT, "white", align="center")

    # 数值轴刻度文字：8pt 橙色，#,##0 千分位，右对齐到 x=77.5（实测墨迹右缘），
    # 竖直方向以刻度值为中心 —— 实测「4,000」墨迹 174~185，中心 179.5，
    # 与 value_px(4000)=179.4 吻合，基线则比中心低 5.1px。
    for tick in Y_TICKS:
        draw_text(overlay, Y_LABEL_RIGHT_PX, value_px(tick) + Y_LABEL_BASELINE_DY_PX,
                  format(tick, ",d"), 8.0, Y_LABEL_COLOR, align="right")

    # ---- 标题 / 副标题 / 脚注：userShapes 的两个文本框 ----
    # 落点 = relSizeAnchor 左缘 × 画布宽 + 文本框默认左内缩 lIns=91440EMU(7.2pt)
    figure.text(TITLE_TEXT_X_PX / FIG_W_PX, 1.0 - TITLE_BASELINE / FIG_H_PX,
                TITLE, ha="left", va="baseline", color="white",
                fontsize=20 * FONT_SCALE, fontweight="bold", fontfamily=UI_FONT)
    figure.text(TITLE_TEXT_X_PX / FIG_W_PX, 1.0 - SUBTITLE_BASELINE / FIG_H_PX,
                SUBTITLE, ha="left", va="baseline", color="white",
                fontsize=14 * FONT_SCALE, fontfamily=UI_FONT)
    figure.text(FOOTNOTE_TEXT_X_PX / FIG_W_PX, 1.0 - FOOTNOTE_BASELINE / FIG_H_PX,
                FOOTNOTE, ha="left", va="baseline", color=FOOTNOTE_COLOR,
                fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)

    output = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "chart11_smooth_line.png")
    figure.savefig(output, dpi=200, facecolor=BACKGROUND)
    print("saved:", output)
    return figure


if __name__ == "__main__":
    main()
    if matplotlib.get_backend().lower() != "agg":
        plt.show()
