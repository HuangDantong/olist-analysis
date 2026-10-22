# -*- coding: utf-8 -*-
"""
图表复刻 3/15 —— 渐变圆角柱形图

复刻对象：`第二章 图表(前15).xlsx` 工作表「3 渐变圆角柱形图」中的图表。

这张图与图1 的差别有三处，也是它容易被做错的地方：

  1. **柱子是图片填充**，不是渐变填充。每个 `c:dPt` 里挂的是 `a:blipFill`，
     指向 xl/media/image1.png ~ image4.png 这四张「胶囊形」小图（12px 宽，
     顶部圆头、底部圆头都烘焙在图里，靠 alpha 通道实现）。Excel 用
     `a:stretch` + `a:fillRect` 把整张图拉进柱子矩形，所以复刻时直接
     `imshow(..., extent=(柱左, 柱右, 0, 柱高))` 拉满即可。
  2. **六个数值标签都被手工拖过**，落点由 `c:dLbls` 里每个 `c:dLbl` 的
     `c:layout/c:manualLayout` 给出；同一条数据线上还有 6 个手工画的
     userShapes（圆角标注框 + 带圆头连接符）。
  3. **标注框压在数字上面**（半透明 0070C0@20%），所以数字的颜色会被
     冲淡成 #C2D8E8 左右；绘制顺序必须是 柱子 < 数据标签 < 标注框 < 连接符。

数据来源：'3 渐变圆角柱形图'!$B$3:$B$8（类别）、$C$3:$C$8（销量）

样式规格全部取自该 xlsx 的图表 XML（xl/charts/chart3.xml、
xl/drawings/drawing6.xml）与主题 xl/theme/theme1.xml：

    XML 里的定义                          matplotlib 实现
    -----------------------------------   -----------------------------------
    图表区背景 srgbClr 1A1E43             figure facecolor BACKGROUND
    绘图区 manualLayout x=.135022 y=.291720
        w=.788997 h=.536467               figure.add_axes([...])
    barDir=col / grouping=clustered       柱心落在整数类别位置，两侧各留半格
    gapWidth=500（柱宽 = 类别宽 / 6）      BAR_WIDTH = 1/6
    数据点 blipFill rId3~rId6             imshow 拉伸 xl/media/image1~4.png
    valAx max=1200，majorUnit 自动 = 200   ylim(0, 1200)，刻度 0..1200 步长 200
    网格线 w=6350EMU(0.5pt)、prstDash=lgDash、
        tx1 lumMod15 lumOff85 alpha20     #D9D9D9 @ 0.20，虚线 8×/3× 线宽，
                                          逐条画（axis.grid() 会把 0 那条裁掉）
    坐标轴文字 9pt bg1 lumMod95%          #F2F2F2，9 × FONT_SCALE
    数据标签 outEnd + 逐点 manualLayout   按实测基准 + XML 偏移摆放
    标注框 roundRect 29.9×15.5pt
        srgbClr 0070C0 alpha20            FancyBboxPatch，圆角 = 短边/6
    连接符 prstGeom=line，lnRef idx=1
        （主题 lnStyleLst[1] w=12700EMU）
        headEnd type=oval                 线色 accent1 #5B9BD5，线宽 1pt，
                                          线头一个直径 11px 的圆
    标题/副标题 20pt bold / 14pt 微软雅黑    UI_FONT，逐字符回退
    脚注 8pt bg1 lumMod85%                #D9D9D9

运行：python chart3_rounded_gradient_bar.py
输出：chart3_rounded_gradient_bar.png（832 x 617，与 Excel 导出图等比同尺寸）
"""

import io
import os
import zipfile

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch
from matplotlib.transforms import ScaledTranslation
from PIL import Image

import chartkit

# --------------------------------------------------------------------------
# 常量：全部按 Excel 图表的原始定义换算
# --------------------------------------------------------------------------

# Excel 图表对象尺寸 416 x 308.125 pt，按 2 px/pt 导出取整成 832 x 617
# （reference/chart3_excel.png 实测 617；height_px_of 会四舍五入成 616，故写死）
DPI = chartkit.DPI
FIG_W_PX = 832
FIG_H_PX = 617

# 字号换算：画布是 Excel 图表的 1.44 倍（= 2 * 72 / 100）
FONT_SCALE = chartkit.FONT_SCALE             # 1.44

BACKGROUND = chartkit.BACKGROUND             # 1A1E43
LABEL_COLOR = "#F2F2F2"                      # bg1 lumMod 95%
FOOTNOTE_COLOR = "#D9D9D9"                   # bg1 lumMod 85%
GRID_COLOR = "#D9D9D9"                       # tx1 lumMod 15% lumOff 85%
GRID_ALPHA = 0.20                            # alpha 20000
CHIP_COLOR = "#0070C0"                       # 标注框 srgbClr 0070C0
CHIP_ALPHA = 0.20                            # alpha 20000
CONNECTOR_COLOR = "#5B9BD5"                  # 主题 accent1

CATEGORIES = ["口红", "面膜", "隔离", "防晒", "精华", "面霜"]
SALES = [653, 523, 648, 856, 714, 785]

# 每个数据点用的填充图：rId3->image1、rId4->image2、rId5->image3、rId6->image4
BAR_IMAGES = ["image1.png", "image2.png", "image1.png",
              "image3.png", "image4.png", "image1.png"]

TITLE = "3月商品销量对比"
SUBTITLE = "防晒销量最多，3月销量856；面膜最少，3月销量523"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.03.31"

# 绘图区在图表中的相对位置（取自 chart3.xml 的 manualLayout）
AXES_LEFT = 0.13502238690751892
AXES_TOP = 0.29172025230356308
AXES_WIDTH = 0.78899722093561842
AXES_HEIGHT = 0.53646680816245673

BAR_WIDTH = 1.0 / (1.0 + 500.0 / 100.0)      # gapWidth=500 -> 柱宽 = 类别宽 / 6
Y_MAX = 1200                                 # valAx scaling/max
Y_TICKS = [0, 200, 400, 600, 800, 1000, 1200]   # majorUnit 未写死，Excel 自动取 200

# 数据标签：{类别序号: (x 偏移, y 偏移)}，直接取自 chart3.xml 每个 c:dLbl 的
# c:layout/c:manualLayout。两个偏移都是比例：
#   x 偏移 × 408pt（userShapes 的横向坐标空间）= 实际横向位移
#   y 偏移 × 305.25pt（纵向坐标空间）= 实际纵向位移（负值向上）
LABEL_OFFSETS = {
    0: (0.026960784313725492, -0.026208026208026210),
    1: (0.029411764705882307, -0.009828007292845727),
    2: (0.026960784313725492, -0.013104013104013164),
    3: (0.026960784313725401, -0.006552006552006552),
    4: (0.034313725490195991, -0.009828009828009889),
    5: (0.029411764705882353, -0.006552006552006552),
}

# Excel 里 outEnd 数据标签的默认落点：基线在柱顶上方这么多像素（实测：
# 用每个点的 manualLayout 偏移反推，六根柱子的残差落在 14.1±0.4 内，
# 与图2 的 DEFAULT_LABEL_GAP 一致）
LABEL_GAP_PX = 14.1

# 标注框（cdr:sp，roundRect，29.9 x 15.5pt），坐标是相对图表区的比例，
# 与连接符一起按 rel × (FIG_W_PX, FIG_H_PX) 落到画布上（实测：这组比例
# 的分母是 408 x 305.25pt，正好铺满 832 x 617 像素）
CHIPS = [
    (0.18076, 0.45536, 0.25400, 0.50604),   # 口红 653
    (0.31587, 0.52416, 0.38911, 0.57484),   # 面膜 523
    (0.44638, 0.46765, 0.51962, 0.51833),   # 隔离 648
    (0.58150, 0.37920, 0.65473, 0.42987),   # 防晒 856
    (0.71444, 0.44195, 0.78768, 0.49263),   # 精华 714
    (0.84161, 0.41237, 0.91485, 0.46304),   # 面霜 785
]
# roundRect 的 prstGeom 没写 avLst，用预设圆角半径 = 短边的 1/6
CHIP_RADIUS_PX = (0.50604 - 0.45536) * FIG_H_PX / 6.0

# 连接符（cdr:cxnSp，prstGeom=line），前两个略斜（cx≈0.375pt），其余是竖线
CONNECTORS = [
    (0.19945, 0.48280, 0.20037, 0.53808),   # 口红
    (0.33058, 0.55733, 0.33150, 0.61261),   # 面膜
    (0.46293, 0.49713, 0.46293, 0.54177),   # 隔离
    (0.59589, 0.40704, 0.59589, 0.45168),   # 防晒
    (0.73009, 0.46847, 0.73009, 0.51310),   # 精华
    (0.85968, 0.43898, 0.85968, 0.48362),   # 面霜
]
CONNECTOR_WIDTH_PT = 1.0        # 主题 lnStyleLst[1]：w=12700 EMU = 1pt
CONNECTOR_DOT_PX = 11.0         # headEnd type="oval"，导出图上实测直径 11px

# 标题/副标题/脚注文本框：框左上角 × 画布 + 默认内边距 91440EMU(7.2pt)
TEXT_INSET_PX = 7.2 * chartkit.PX_PER_PT     # bodyPr lIns 默认值
TITLE_X_PX = 0.05116 * FIG_W_PX + TEXT_INSET_PX      # 文本框 11 的左缘 56.96px
TITLE_BASELINE = 63.5                        # 实测：标题墨迹 30~69，数字底 64.5
SUBTITLE_BASELINE = 111.5                    # 实测：副标题墨迹 88~115
FOOTNOTE_X_PX = 0.04289 * FIG_W_PX + TEXT_INSET_PX   # 文本框 12 的左缘 50.08px
FOOTNOTE_BASELINE = 590.0                    # 实测：脚注墨迹 577~591

plt.rcParams["axes.unicode_minus"] = False
# 虚线长度按 XML 的 lgDash（800%/300% 线宽）给定，不再乘线宽
plt.rcParams["lines.scale_dashes"] = False

UI_FONT = chartkit.UI_FONT                   # 微软雅黑
AXIS_FONTS = chartkit.AXIS_FONTS             # Calibri + 等线


def bar_image(name):
    """从 xlsx 里取出柱子填充用的胶囊形 PNG，返回 RGBA 数组。

    图里圆头是靠 alpha 通道做的，所以必须保留 alpha，不能 convert("RGB")。
    """
    with zipfile.ZipFile(chartkit.XLSX) as archive:
        raw = archive.read("xl/media/" + name)
    return np.asarray(Image.open(io.BytesIO(raw)).convert("RGBA"))


def category_px(index):
    """第 index 个类别的柱心横坐标（像素），0 号类别中心在绘图区左缘 + 半格。"""
    return AXES_LEFT * FIG_W_PX + (index + 0.5) * AXES_WIDTH * FIG_W_PX / len(SALES)


def bar_top_px(value):
    """数值 value 对应的柱子顶端纵坐标（像素）。"""
    plot_bottom = (AXES_TOP + AXES_HEIGHT) * FIG_H_PX
    return plot_bottom - value / Y_MAX * AXES_HEIGHT * FIG_H_PX


def draw_bars(axis):
    """逐柱贴一张拉伸的胶囊图，复刻 Excel 的 blipFill + stretch 填充。"""
    images = {}
    for index, value in enumerate(SALES):
        name = BAR_IMAGES[index]
        if name not in images:
            images[name] = bar_image(name)
        axis.imshow(
            images[name],
            extent=(index - BAR_WIDTH / 2.0, index + BAR_WIDTH / 2.0, 0, value),
            origin="upper",                  # 数组第一行落在 extent 顶部
            aspect="auto",
            interpolation="bilinear",
            zorder=2,
        )


def draw_data_labels(overlay):
    """数据标签：默认贴在柱顶上方，再叠加 c:dLbl 里的手工拖拽偏移。"""
    for index, value in enumerate(SALES):
        dx_frac, dy_frac = LABEL_OFFSETS[index]
        x = category_px(index) + dx_frac * FIG_W_PX
        y = bar_top_px(value) - LABEL_GAP_PX + dy_frac * FIG_H_PX
        overlay.text(x, y, str(value), ha="center", va="baseline",
                     color=LABEL_COLOR, fontsize=9 * FONT_SCALE,
                     fontfamily=AXIS_FONTS, zorder=6)


def draw_chips(overlay):
    """userShapes 里的 6 个半透明圆角标注框（压在数据标签上面）。"""
    for x0, y0, x1, y1 in CHIPS:
        overlay.add_patch(FancyBboxPatch(
            (x0 * FIG_W_PX, y0 * FIG_H_PX),
            (x1 - x0) * FIG_W_PX, (y1 - y0) * FIG_H_PX,
            boxstyle="round,pad=0,rounding_size=%.3f" % CHIP_RADIUS_PX,
            facecolor=CHIP_COLOR, alpha=CHIP_ALPHA, edgecolor="none",
            mutation_aspect=1.0, zorder=7))


def draw_connectors(overlay):
    """userShapes 里的 6 根连接符：竖线 + 线头一个实心圆。"""
    for x0, y0, x1, y1 in CONNECTORS:
        overlay.plot([x0 * FIG_W_PX, x1 * FIG_W_PX],
                     [y0 * FIG_H_PX, y1 * FIG_H_PX],
                     color=CONNECTOR_COLOR, linewidth=CONNECTOR_WIDTH_PT * FONT_SCALE,
                     solid_capstyle="round", zorder=8)
        overlay.add_patch(Circle((x0 * FIG_W_PX, y0 * FIG_H_PX),
                                 CONNECTOR_DOT_PX / 2.0,
                                 facecolor=CONNECTOR_COLOR, edgecolor="none",
                                 zorder=8))


def main():
    figure = plt.figure(figsize=(FIG_W_PX / DPI, FIG_H_PX / DPI), dpi=DPI)
    figure.patch.set_facecolor(BACKGROUND)

    axis = figure.add_axes([AXES_LEFT, 1.0 - AXES_TOP - AXES_HEIGHT,
                            AXES_WIDTH, AXES_HEIGHT])
    axis.set_facecolor(BACKGROUND)

    draw_bars(axis)

    # 坐标范围：每个类别占 1 格，两侧各留半格
    axis.set_xlim(-0.5, len(SALES) - 0.5)
    axis.set_ylim(0, Y_MAX)

    # ---- 网格线 ----
    # 逐条画而不是用 axis.grid()：matplotlib 会把 gridline 裁到绘图区矩形里，
    # 0 刻度那条正好压在绘图区下缘上，会被整条裁掉；Excel 是整条都画。
    axis.set_axisbelow(True)                 # 实测网格线在柱子后面
    for tick in Y_TICKS:
        axis.plot([-0.5, len(SALES) - 0.5], [tick, tick],
                  color=GRID_COLOR, alpha=GRID_ALPHA,
                  linewidth=0.5 * FONT_SCALE,
                  linestyle=(0, (8 * 0.5 * FONT_SCALE, 3 * 0.5 * FONT_SCALE)),
                  dash_capstyle="round",     # XML 里 <a:ln> 带 <a:round/>
                  clip_on=False, zorder=0)

    axis.set_xticks(np.arange(len(CATEGORIES)))
    axis.set_xticklabels(CATEGORIES, color=LABEL_COLOR,
                         fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS)
    axis.set_yticks(Y_TICKS)
    axis.set_yticklabels([str(v) for v in Y_TICKS], color=LABEL_COLOR,
                         fontsize=9 * FONT_SCALE, fontfamily=AXIS_FONTS)

    axis.tick_params(axis="x", length=0, pad=10.8)   # 绘图区底缘到类别文字 15px
    axis.tick_params(axis="y", length=0, pad=12.42)  # 绘图区左缘到数字 17.3px

    # Excel 把刻度文字按行框竖直居中，matplotlib 按墨迹包围盒居中，
    # 两者差约 1px，这里补一个竖直微调（实测输出比原图低 1px）
    shift = ScaledTranslation(0, 1.0 / DPI, figure.dpi_scale_trans)
    for label in axis.get_yticklabels():
        label.set_transform(label.get_transform() + shift)

    for spine in axis.spines.values():
        spine.set_visible(False)

    # ---- userShapes：数据标签 -> 标注框 -> 连接符，依次压在上层 ----
    overlay = figure.add_axes([0, 0, 1, 1], zorder=5)
    overlay.set_xlim(0, FIG_W_PX)
    overlay.set_ylim(FIG_H_PX, 0)            # 纵轴向下，常量直接照实测像素写
    overlay.set_axis_off()
    overlay.patch.set_visible(False)

    draw_data_labels(overlay)
    draw_chips(overlay)
    draw_connectors(overlay)

    # ---- 标题 / 副标题 / 脚注（同一批 userShapes，锚点是"框顶 + 内边距"）----
    figure.text(TITLE_X_PX / FIG_W_PX, 1.0 - TITLE_BASELINE / FIG_H_PX, TITLE,
                ha="left", va="baseline", color="white",
                fontsize=20 * FONT_SCALE, fontweight="bold", fontfamily=UI_FONT)
    figure.text(TITLE_X_PX / FIG_W_PX, 1.0 - SUBTITLE_BASELINE / FIG_H_PX, SUBTITLE,
                ha="left", va="baseline", color="white",
                fontsize=14 * FONT_SCALE, fontfamily=UI_FONT)
    figure.text(FOOTNOTE_X_PX / FIG_W_PX, 1.0 - FOOTNOTE_BASELINE / FIG_H_PX, FOOTNOTE,
                ha="left", va="baseline", color=FOOTNOTE_COLOR,
                fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)

    output = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "chart3_rounded_gradient_bar.png")
    figure.savefig(output, dpi=200, facecolor=BACKGROUND)
    print("saved:", output)
    return figure


if __name__ == "__main__":
    if matplotlib.get_backend().lower() == "agg":
        main()
    else:
        main()
        plt.show()
