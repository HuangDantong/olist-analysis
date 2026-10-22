# -*- coding: utf-8 -*-
"""
图表复刻 15/15 —— 水球图（液位填充图）

复刻对象：`第二章 图表(前15).xlsx` 工作表「15 水球图」中的图表。
工作表序号 15 对应 xl/charts/chart14.xml，userShapes 是 xl/drawings/drawing29.xml。

这张图看着像个仪表盘，其实是**一张柱形图 + 两个 userShapes 形状**拼出来的，
也是最容易做错的地方：

  1. **画布上根本没有「水球」这个图形**。chart14.xml 里是一张
     `barChart / barDir=col / grouping=clustered`，只有一个类别，
     `gapWidth=0` + `overlap=100`，两条系列叠在同一根柱子上：

         系列 0「水」 val = 0.65，spPr 是 blipFill -> xl/media/image7.svg
         系列 1「空」 val = 1，   spPr 是 blipFill -> xl/media/image9.svg

     image7.svg 是一张 **实心圆**（#0070C0，直径 192，viewBox 192），
     image9.svg 是一张 **空心圆环**（#0070C0，直径 192、描边 2.667，viewBox 195）。
     柱形图用 pictureFormat=stackScale 把图片按「整根柱子的高度」缩放，
     再按数值裁掉上部，于是：
        - 系列 1（=1）整圆环铺满绘图区高度，就是那个内圈细环；
        - 系列 0（=0.65）同一张实心圆，只露出下面 65%，圆顶被水面切平。
     水面那条水平线不是画出来的，就是「实心圆被数值裁切」的切口。
  2. **外圈那道更粗的环和圆心文字都在 userShapes 里**：
     cdr:sp「椭圆 1」prstGeom=ellipse（a:ln w=22225EMU=1.75pt，srgbClr 0070C0）
     和 cdr:sp「文本框 2」（'65%'，40pt，schemeClr bg1 = 白）。
     userShapes 永远画在图表之上，顺序是 内环/水面 < 外环 < 文字。
  3. **chart14.xml 里没有 manualLayout**（`<c:plotArea><c:layout/>`），
     绘图区由 Excel 自动布局。所以这里不调 chartkit.plot_area，
     改用一张铺满画布的像素坐标 overlay（1 数据单位 = 1 像素），
     圆的几何全部按下面的实测值写死。

样式规格取自该 xlsx 的图表 XML 与导出图原图：

    XML 里的定义                          matplotlib 实现
    -----------------------------------   -----------------------------------
    图表区背景 srgbClr 1A1E43             figure facecolor BACKGROUND
    spPr/ln w=22225EMU = 1.75pt (外环)    Ellipse lw = 1.75pt
    dPt blipFill image7.svg（实心圆）      Ellipse 面填充 #0070C0
    dPt blipFill image9.svg（空心环）      Ellipse facecolor=none + 描边
    valAx min=0 max=1，无 manualLayout     按实测像素直接摆（见下方常量）
    cdr:sp 文本框 2，40pt，schemeClr bg1    白色 40 × FONT_SCALE，Calibri

运行：python chart15_liquid_fill.py
输出：chart15_liquid_fill.png（375 x 372，与 Excel 导出图同尺寸）
"""

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Rectangle

import chartkit

# --------------------------------------------------------------------------
# 常量：全部按 Excel 图表的原始定义 + 导出图实测换算
# --------------------------------------------------------------------------

DPI = chartkit.DPI
FIG_W_PX = 375                               # 187.25pt × 2，Excel 导出取整
FIG_H_PX = chartkit.height_px_of(15)         # 186.00pt × 2 = 372（实测）

BACKGROUND = chartkit.BACKGROUND             # 1A1E43
WATER_COLOR = "#0070C0"                      # image7.svg / image9.svg / 外环 ln 都是 0070C0

FILL_VALUE = 0.65                            # chart14.xml：系列 0 的 c:v = 0.65

# matplotlib 的 linewidth 单位是 pt，导出时 1pt = DPI/72 = 1.3889px
PT_PER_PX = 72.0 / DPI

# ---- 圆的几何（单位：像素，原点在画布左上角，y 向下）----
# 外环：userShapes 的 cdr:relSizeAnchor 锚点 (0.02404,0.03020)-(0.96898,0.97514)，
# 相对图表区 187.25 x 186pt（= 374.5 x 372px）。实测圆心 (185.95,187.0)、
# 椭圆半径 (176.95,175.76)，与锚点算出来的 176.95/175.76 完全吻合。
OUTER_CX_PX = 185.95
OUTER_CY_PX = 187.00
OUTER_RX_PX = 176.95
OUTER_RY_PX = 175.76
OUTER_LW_PX = 1.75 * chartkit.PX_PER_PT      # a:ln w=22225EMU = 1.75pt -> 3.5px

# 内环（= image9.svg 的空心圆环被铺满绘图区高度）。实测：对水面以上
# 孤立的环带做最小二乘圆拟合，中心 (187.0,187.9)，外缘半径 166.17、
# 内缘 160.52 -> 路径半径 163.35、线宽 5.65px。
INNER_CX_PX = 187.00
INNER_CY_PX = 187.90
INNER_R_PX = 163.35
INNER_LW_PX = 5.65

# 实心圆（= image7.svg，被 0.65 裁切后就是蓝色水域）。同一个圆换到
# 195 的 viewBox 里，所以比内环路径大 195/192 = 1.0156 倍；实测拟合
# 得到 center (187.0,185.7)、rx=166.1、ry=164.3（略扁，非正圆）。
FILL_CX_PX = 187.00
FILL_CY_PX = 185.70
FILL_RX_PX = 166.10
FILL_RY_PX = 164.30

# 水面与图片底边：绘图区 0 在 y=350.0、1 在 y=350.0-337.9=12.1…… 但图片
# 是 stackScale 缩放的，直接按实测取：水面（=0.65 的切口）在 y=136.5，
# 蓝色最下沿在 y=350.0。内环的下半圈被这张图裁在 350.0，所以看不见。
WATER_Y_PX = 136.5
IMAGE_BOTTOM_PX = 350.0

# 圆心文字：userShapes「文本框 2」锚点 (0.23813,0.37420)-(0.79753,0.57830)，
# 水平中心落在 0.51783 × 374.5 = 193.9px（实测墨迹中心 194.5）；
# 竖直 anchor=ctr，基线用实测墨迹底边 204 反推为 205.0。
TEXT_CENTER_X_PX = 193.93
TEXT_BASELINE_PX = 205.0
TEXT = "65%"
TEXT_SIZE_PT = 40                            # cdr:rPr sz="4000"
TEXT_COLOR = "white"                         # schemeClr bg1

AXIS_FONTS = chartkit.AXIS_FONTS             # ['Calibri', 'DengXian']

plt.rcParams["axes.unicode_minus"] = False


def draw_water(axis):
    """蓝色水域：一张实心圆，下半 65% 露出、上半被水面切掉。

    Excel 是 blipFill + pictureFormat=stackScale，效果等于把实心圆按
    「整根柱子」的高度缩放后，只保留 value=0.65 以下的部分；这里用
    椭圆补丁 + 矩形 clip 复刻同一个切口。
    """
    circle = Ellipse((FILL_CX_PX, FILL_CY_PX), 2 * FILL_RX_PX, 2 * FILL_RY_PX,
                     facecolor=WATER_COLOR, edgecolor="none", zorder=2)
    axis.add_patch(circle)
    # clip 矩形从水面盖到图片底边（图片底边在圆的下方，等于不裁）
    clip = Rectangle((0.0, WATER_Y_PX), FIG_W_PX, IMAGE_BOTTOM_PX - WATER_Y_PX,
                     transform=axis.transData)
    circle.set_clip_path(clip)


def draw_inner_ring(axis):
    """内环：image9.svg 的空心圆环，同样被图片的上下边裁掉一截。"""
    ring = Ellipse((INNER_CX_PX, INNER_CY_PX), 2 * INNER_R_PX, 2 * INNER_R_PX,
                   facecolor="none", edgecolor=WATER_COLOR,
                   linewidth=INNER_LW_PX * PT_PER_PX, zorder=3)
    axis.add_patch(ring)
    clip = Rectangle((0.0, WATER_Y_PX - 400.0), FIG_W_PX,
                     IMAGE_BOTTOM_PX - (WATER_Y_PX - 400.0), transform=axis.transData)
    ring.set_clip_path(clip)


def draw_outer_ring(axis):
    """外环：userShapes 的 cdr:sp「椭圆 1」，1.75pt 的 0070C0 描边，无填充。"""
    axis.add_patch(Ellipse((OUTER_CX_PX, OUTER_CY_PX),
                           2 * OUTER_RX_PX, 2 * OUTER_RY_PX,
                           facecolor="none", edgecolor=WATER_COLOR,
                           linewidth=OUTER_LW_PX * PT_PER_PX, zorder=4))


def draw_center_text(axis):
    """圆心 '65%'：userShapes 文本框，40pt、白色、无衬线主题字体。"""
    axis.text(TEXT_CENTER_X_PX, TEXT_BASELINE_PX, TEXT,
              ha="center", va="baseline", color=TEXT_COLOR,
              fontsize=TEXT_SIZE_PT * chartkit.FONT_SCALE,
              fontfamily=AXIS_FONTS, zorder=5)


def main():
    figure = chartkit.new_figure(FIG_W_PX, FIG_H_PX)

    # 绘图区没有 manualLayout，Excel 自动布局；这里直接铺一张像素坐标 overlay，
    # 让 1 数据单位 = 1 像素，圆的几何常量可以照实测值写。
    axis = figure.add_axes([0, 0, 1, 1])
    axis.set_xlim(0, FIG_W_PX)
    axis.set_ylim(FIG_H_PX, 0)               # 纵轴向下，和图片坐标一致
    axis.set_axis_off()
    axis.patch.set_visible(False)

    draw_water(axis)                         # 最底：蓝色水域
    draw_inner_ring(axis)                    # 内环（下半被水域盖住）
    draw_outer_ring(axis)                    # userShapes 外环
    draw_center_text(axis)                   # 最上：圆心文字

    chartkit.save(figure, "chart15_liquid_fill.png")
    return figure


if __name__ == "__main__":
    if matplotlib.get_backend().lower() == "agg":
        main()
    else:
        main()
        plt.show()
