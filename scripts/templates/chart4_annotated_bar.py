# -*- coding: utf-8 -*-
"""
图表复刻 4/15 —— 标注柱形图

复刻对象：`第二章 图表(前15).xlsx` 工作表「4 标注柱形图」中的图表。
每根柱子单独设色，柱顶外侧挂着「气泡标注式」数据标签（pdataLbl 被改成了
wedgeRectCallout 形状：一个矩形气泡 + 一个指向柱顶的三角小尾巴）。

数据来源：'4 标注柱形图'!$C$3:$C$10

样式规格全部取自该 xlsx 的图表 XML（xl/charts/chart4.xml、
xl/drawings/drawing8.xml）：

    图表区背景          srgbClr 1A1E43
    绘图区              manualLayout x=0.142034 y=0.298733 w=0.786205 h=0.537685
    柱形系列            默认填充 7BBDD5，逐点覆盖见 POINT_COLORS（c:dPt）
    柱宽/间距           gapWidth=100%  ->  柱宽 = 类别宽 / 2
    数值轴              majorUnit=2000，范围 0~10000（无 min/max，Excel 自动取整）
                        标签 9pt，bg1 lumMod 95% (#F2F2F2)，Latin +mn-lt = Calibri
    网格线              bg1 lumMod 95% alpha 20%，线宽 6350EMU = 0.5pt，prstDash="lgDash"
    类别轴              轴线 noFill（不画）；标签 8pt，微软雅黑，#F2F2F2
    数据标签            c:dLbl 逐个带 manualLayout，位置见 CALLOUTS（实测）
                        文字 8pt，#F2F2F2；气泡填充 = 该点的柱色
    标题                微软雅黑 18pt 加粗 白色
    副标题              微软雅黑 12pt 白色
    脚注                微软雅黑 8pt，bg1 lumMod 85% (#D9D9D9)

坐标轴/数据标签的 Latin 字体继承主题 (+mn-lt = Calibri)，中日韩字形
继承工作簿默认字体（等线 / DengXian）；类别轴标签则显式写死微软雅黑。

数据标签的气泡形状没有出现在 XML 里（Excel 只会输出 c:dLbl 的
manualLayout 偏移），气泡矩形、尾巴三角、以及数字墨迹的位置全部是在
reference/chart4_excel.png 上逐点量出来的，落在 CALLOUTS / LABEL_INK 里。

运行：python chart4_annotated_bar.py
输出：chart4_annotated_bar.png（832 x 616，与 Excel 导出图等比同尺寸）
"""

import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch, Polygon, Rectangle
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D, ScaledTranslation

# --------------------------------------------------------------------------
# 常量：全部按 Excel 图表的原始定义换算
# --------------------------------------------------------------------------

# Excel 图表对象尺寸 416 x 308 pt，按 2 px/pt 导出
DPI = 100
FIG_W_PX, FIG_H_PX = 832, 616

# 字号换算：画布是 Excel 图表的 1.44 倍（= 2 * 72 / 100）
FONT_SCALE = 2 * 72 / DPI  # 1.44

BACKGROUND = "#1A1E43"
LABEL_COLOR = "#F2F2F2"      # bg1 lumMod 95%，数值轴/类别轴/数据标签都用它
TITLE_COLOR = "#FFFFFF"      # bg1，标题与副标题
FOOTNOTE_COLOR = "#D9D9D9"   # bg1 lumMod 85%

CATEGORIES = ["口红", "面膜", "隔离", "防晒", "精华", "面霜", "眼影", "气垫"]
SALES = [9221, 5102, 6571, 5760, 6321, 8612, 2645, 5321]

# 逐点覆盖色：第 0 点没有 c:dPt，用系列默认填充 7BBDD5；其余取各自 c:dPt
POINT_COLORS = ["#7BBDD5", "#49A098", "#E66B4C", "#FFC000",
                "#0097E0", "#0070C0", "#4A5BD1", "#464CAC"]

TITLE = "2021年商品销量情况"
SUBTITLE = "口红销量最好达9221，是眼影最低值2645近3.5倍"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.08.31"

# 绘图区在图表中的相对位置（取自 chart4.xml 的 manualLayout）
AXES_LEFT = 0.14203431372549019
AXES_TOP = 0.29873290354927151
AXES_WIDTH = 0.78620522618496225
AXES_HEIGHT = 0.53768486197969612

# gapWidth=100%：柱宽占类别宽的比例为 1 / (1 + 1.00)
BAR_WIDTH = 1.0 / (1.0 + 100.0 / 100.0)

Y_MAX = 10000
Y_TICKS = [0, 2000, 4000, 6000, 8000, 10000]

# 数据标签气泡的几何（全部为在原图 reference/chart4_excel.png 上实测的像素值）。
# 每项 = (矩形左, 矩形上, 矩形宽, 矩形高, 尾巴底边左, 尾巴底边右, 尾巴尖 x, 尾巴尖 y)
# 矩形统一 45x26px；尾巴是贴在矩形下边上的一小块三角形，尖落在柱顶附近。
# 这些偏移是原作者手工拖出来的，没有规律可循，只能逐个实测。
CALLOUTS = [
    (140.0, 173.0, 45.0, 26.0, 147.5, 157.5, 156.5, 208.5),
    (219.0, 305.0, 45.0, 26.0, 245.5, 254.5, 245.5, 339.0),
    (300.0, 261.0, 45.0, 26.0, 308.5, 317.5, 319.7, 296.4),
    (384.0, 288.0, 45.0, 26.0, 410.5, 418.5, 409.5, 318.0),
    (466.0, 273.0, 45.0, 26.0, 475.5, 483.5, 485.8, 303.5),
    (548.0, 195.0, 45.0, 26.0, 556.5, 565.5, 569.0, 227.7),
    (630.0, 389.0, 45.0, 26.0, 638.5, 647.5, 649.3, 424.1),
    (714.0, 300.0, 45.0, 26.0, 722.5, 731.5, 733.2, 333.0),
]

# 气泡里那串数字的墨迹包围盒 (左, 上, 宽, 高)，逐点在原图上量出。
# 有了它就可以把字形轮廓直接钉在实测位置上，不必依赖字体度量。
LABEL_INK = [
    (147.0, 181.0, 30.0, 10.0),
    (226.0, 313.0, 30.0, 10.0),
    (307.0, 269.0, 30.0, 10.0),
    (392.0, 296.0, 31.0, 10.0),
    (473.0, 282.0, 30.0, 10.0),
    (555.0, 204.0, 30.0, 10.0),
    (637.0, 397.0, 30.0, 10.0),
    (721.0, 309.0, 30.0, 10.0),
]

# 三段文字的落点。原图上量到的墨迹是：
#   标题   y 42~77   x 56~393      副标题 y 100~123  x 56~583
#   脚注   y 581~595 x 49~451
# 但 ha="left"/va="baseline" 对的是含左留白与基线的文本框，和墨迹差着一点点，
# 所以这里的数值是按「渲染后墨迹落回上面那几行」反推出来的（差 <1px）。
TITLE_LEFT_PX, TITLE_BASE_PX = 54.25, 72.0
SUBTITLE_LEFT_PX, SUBTITLE_BASE_PX = 54.0, 120.0
FOOTNOTE_LEFT_PX, FOOTNOTE_BASE_PX = 48.0, 594.0


def _pick_font(candidates, fallback="DejaVu Sans"):
    """返回第一个已安装的字体名，用于在缺少中文字体的机器上仍可运行。"""
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in installed:
            return name
    return fallback


# 标题/副标题/脚注以及类别轴标签在 XML 中显式指定了「微软雅黑」
UI_FONT = _pick_font(["Microsoft YaHei", "微软雅黑", "SimHei", "DengXian"])
# 数值轴与数据标签：Latin 用 Calibri，中文回退到等线（工作簿默认字体）
AXIS_FONTS = [_pick_font(["Calibri"]),
              _pick_font(["DengXian", "等线", "SimSun", "Microsoft YaHei"])]

plt.rcParams["axes.unicode_minus"] = False
# 网格线虚线长度按 XML 折算后的实测值给定，不再乘线宽
plt.rcParams["lines.scale_dashes"] = False


def add_digit_label(figure, text, ink):
    """把数据标签的数字画进 ink 指定的墨迹包围盒里。

    ink = (左, 上, 宽, 高)，全部是从原图上量出来的像素值。

    这里没有用普通的 figure.text：本机的 calibri.ttf 在 11.52pt（即 Excel
    的 8pt × 1.44）这个尺寸上会命中 FreeType/Agg 的光栅化缺陷，抗锯齿渲染
    出来是一片空白（把 text.antialiased 关掉、或换成 10pt / 13pt 就会出字，
    显然不是位置问题）。为了不把其余文字的抗锯齿一起牺牲掉，这里直接取
    Calibri 的字形轮廓（TextPath）再填色；顺带还能把墨迹钉在实测包围盒上，
    比依赖字体度量更准。
    """
    x0, top, width, _ = ink
    path = TextPath((0.0, 0.0), text, size=8 * FONT_SCALE,
                    prop=FontProperties(family=AXIS_FONTS[0]))
    bounds = path.get_extents()
    # 统一缩放：按墨迹宽度对齐，避免横竖不等比把字形拉变形
    scale = width / bounds.width
    height = bounds.height * scale
    # TextPath 的坐标是 pt，先平移到墨迹左下角、缩放成参考像素，
    # 再换算成 figure 的相对坐标（x 除以画布宽、y 除以画布高）。
    transform = (Affine2D()
                 .translate(-bounds.x0, -bounds.y0)
                 .scale(scale / FIG_W_PX, scale / FIG_H_PX)
                 .translate(x0 / FIG_W_PX, 1.0 - (top + height) / FIG_H_PX))
    figure.add_artist(PathPatch(path, transform=transform + figure.transFigure,
                                facecolor=LABEL_COLOR, edgecolor="none",
                                zorder=6))


def main():
    figure = plt.figure(figsize=(FIG_W_PX / DPI, FIG_H_PX / DPI), dpi=DPI)
    figure.patch.set_facecolor(BACKGROUND)

    axis = figure.add_axes([AXES_LEFT,
                            1.0 - AXES_TOP - AXES_HEIGHT,
                            AXES_WIDTH,
                            AXES_HEIGHT])
    axis.set_facecolor(BACKGROUND)

    positions = np.arange(len(CATEGORIES))

    # ---- 柱形系列：每根柱子单独设色（c:dPt），纯色无边框 ----
    axis.bar(positions, SALES, width=BAR_WIDTH,
             color=POINT_COLORS, edgecolor="none", zorder=2)

    axis.set_xlim(-0.5, len(CATEGORIES) - 0.5)
    axis.set_ylim(0, Y_MAX)

    # ---- 网格线：bg1 lumMod95% alpha20%，0.5pt lgDash ----
    # 实测虚线 9px + 间隔 2px（1 参考像素 = 1 输出像素）
    axis.set_axisbelow(True)
    axis.grid(axis="y", color=LABEL_COLOR, alpha=0.20,
              linewidth=0.5 * FONT_SCALE,        # 6350 EMU = 0.5pt -> 0.72pt
              linestyle=(0, (6.48, 1.44)),       # 9px / 2px，按导出图实测
              zorder=0)
    # y=0 那条网格线正落在绘图区下缘，默认会连同下半截一起被裁掉，原图里
    # 它是画满的，所以单独放开裁剪。
    for grid_line in axis.get_ygridlines():
        grid_line.set_clip_on(False)

    # ---- 坐标轴 ----
    # 类别轴：轴线 noFill，不画；标签 8pt 微软雅黑 #F2F2F2
    axis.set_xticks(positions)
    axis.set_xticklabels(CATEGORIES, color=LABEL_COLOR,
                         fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)
    # 数值轴：标签 9pt，#F2F2F2
    axis.set_yticks(Y_TICKS)
    axis.set_yticklabels([str(v) for v in Y_TICKS], color=LABEL_COLOR,
                         fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS)

    for spine in axis.spines.values():
        spine.set_visible(False)

    # 实测：柱底(绘图区下缘 515.2px) 到类别文字墨迹顶 533px，间距 17.8px
    axis.tick_params(axis="x", length=0, pad=13.28)
    # 实测：绘图区左缘 118.2px 到数字墨迹右缘 100px，间距 18.2px
    axis.tick_params(axis="y", length=0, pad=12.16)

    # Excel 把刻度文字按行框垂直居中，matplotlib 按墨迹居中，差约 1px，补回来
    shift = ScaledTranslation(0, 2.0 / DPI, figure.dpi_scale_trans)
    for tick_label in axis.get_yticklabels():
        tick_label.set_transform(tick_label.get_transform() + shift)

    # ---- 数据标签：wedgeRectCallout 气泡（矩形 + 三角尾巴）----
    for index, (value, color) in enumerate(zip(SALES, POINT_COLORS)):
        x, top, width, height, tail_left, tail_right, tip_x, tip_y = CALLOUTS[index]
        # 矩形本体（挂在 figure 上，避免被绘图区裁剪）
        figure.add_artist(Rectangle((x / FIG_W_PX, 1.0 - (top + height) / FIG_H_PX),
                                    width / FIG_W_PX, height / FIG_H_PX,
                                    transform=figure.transFigure,
                                    facecolor=color, edgecolor="none", zorder=4))
        # 贴在矩形下边上的三角尾巴
        figure.add_artist(Polygon([(tail_left / FIG_W_PX, 1.0 - (top + height) / FIG_H_PX),
                                   (tail_right / FIG_W_PX, 1.0 - (top + height) / FIG_H_PX),
                                   (tip_x / FIG_W_PX, 1.0 - tip_y / FIG_H_PX)],
                                  closed=True, transform=figure.transFigure,
                                  facecolor=color, edgecolor="none", zorder=4))
        # 数字放进气泡里（位置由实测墨迹包围盒给定）
        add_digit_label(figure, str(value), LABEL_INK[index])

    # ---- 标题 / 副标题 / 脚注 ----
    figure.text(TITLE_LEFT_PX / FIG_W_PX, 1.0 - TITLE_BASE_PX / FIG_H_PX, TITLE,
                ha="left", va="baseline", color=TITLE_COLOR,
                fontsize=18 * FONT_SCALE, fontweight="bold", fontfamily=UI_FONT)
    figure.text(SUBTITLE_LEFT_PX / FIG_W_PX, 1.0 - SUBTITLE_BASE_PX / FIG_H_PX,
                SUBTITLE, ha="left", va="baseline", color=TITLE_COLOR,
                fontsize=12 * FONT_SCALE, fontfamily=UI_FONT)
    figure.text(FOOTNOTE_LEFT_PX / FIG_W_PX, 1.0 - FOOTNOTE_BASE_PX / FIG_H_PX,
                FOOTNOTE, ha="left", va="baseline", color=FOOTNOTE_COLOR,
                fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)

    output = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "chart4_annotated_bar.png")
    figure.savefig(output, dpi=200, facecolor=BACKGROUND)
    print("saved:", output)
    return figure


if __name__ == "__main__":
    if matplotlib.get_backend().lower() == "agg":
        main()
    else:
        main()
        plt.show()
