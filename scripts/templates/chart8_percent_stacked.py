# -*- coding: utf-8 -*-
"""
图表复刻 8/15 —— 数值百分比条形图

复刻对象：`第二章 图表(前15).xlsx` 工作表「8 数值百分比」中的图表。
原始图表由 Excel 生成，本脚本用 matplotlib 逐像素还原其外观。

**注意编号**：工作表序号是 8，但对应的图表部件是 xl/charts/chart7.xml
（xl/drawings/drawing15.xml 是它的 userShapes）。核对方法：chart7.xml 里
所有 c:f 公式都指向 '8 数值百分比'!，且 reference/chart8_excel.png 与该
工作表导出的图一致。

图表结构：6 行横向**百分比堆积条形图**（barDir=bar、grouping=stacked、
overlap=100），每行由三段叠加而成：

    系列0 销量   #09387E 深蓝  实际销量，段内右端标注数值（dLblPos=inEnd）
    系列1 占位1  #82ADD7 浅蓝  纯占位，把深蓝顶到左边（无数据标签）
    系列2 占位2  #9B3D4F 暗红  固定 1080.25，段内居中标注同比百分比（dLblPos=ctr）

三段的巧思：销量 + 占位1 = 4321（每行都相等），再叠加固定的 1080.25，
于是每根条总长恒为 5401.25 = 4321 + 1080.25。这样深蓝段长度直接等于
销量本身，而暗红段始终占右侧固定的 20%（= 1080.25 / 5401.25），
百分比标签因此天然排在一条竖线上。

数据来源：
  '8 数值百分比'!$B$3:$B$8   类别（华北…华东，倒序绘制）
  '8 数值百分比'!$C$3:$C$8   销量     [4321, 1946, 1536, 1872, 1369, 2109]
  '8 数值百分比'!$D$3:$D$8   占位1    [0, 2375, 2785, 2449, 2952, 2212]
  '8 数值百分比'!$E$3:$E$8   占位2    恒为 1080.25
  '8 数值百分比'!$F$3:$F$8   百分比   [-13.6%, -20.8%, -9.3%, -15.9%, -17.9%, -5.8%]
             （百分比以 c15:datalabelsRange 的单元格区域标签形式给出）

样式规格全部取自该 xlsx 的图表 XML（chart7.xml）与 userShapes（drawing15.xml）：

    XML 里的定义                          matplotlib 实现
    -----------------------------------   ----------------------------------------
    图表区底色 srgbClr 1A1E43             chartkit.BACKGROUND
    绘图区 manualLayout x=0.127081        chartkit.plot_area(figure, layout, ...)
        y=0.281424 w=0.816546 h=0.608752  （六个条心实测残差 < 1px，无需微调）
    条方向 barDir=bar，堆叠 stacked       axis.barh(...)，逐系列叠加
    条高 gapWidth=30%                     BAR_HEIGHT = 1 / (1 + 0.30)
    系列0 填充 srgbClr 09387E（深蓝）      DARK_BLUE
    系列1 填充 srgbClr 82ADD7（浅蓝）      LIGHT_BLUE
    系列2 填充 srgbClr 9B3D4F（暗红）      DARK_RED
    边框 ln/noFill（三段都无描边）         edgecolor="none"
    数值轴 valAx delete=1（整条删除）      xlim 手动给 (0, 6000)，无刻度无网格
    类别轴 catAx 线 noFill                spines 全部隐藏
    类别标签 9pt，bg1 lumMod 95%          #F2F2F2，9pt × 1.44，无刻度线
    数据标签 10pt，b="0"（非粗体）        #F2F2F2，10pt × 1.44
        bg1 lumMod 95%
    系列0 标签 dLblPos=inEnd              ha="right"，右端内缩 VALUE_LABEL_INSET_PX
    系列2 标签 dLblPos=ctr                ha="center"，居中于暗红段
    标题  18pt 加粗 微软雅黑              TITLE
    副标题 11pt 微软雅黑                  SUBTITLE
    脚注  8pt bg1 lumMod 85% 微软雅黑      FOOTNOTE，#D9D9D9

数值轴被删除后 Excel 仍按自动刻度取整，原图实测条长对应 xlim 上限 6000
（总量 5401.25 在绘图区里占 90.0% 宽，实测 611 / 679 px = 90.0%）。

关于图片填充：xl/charts/_rels/chart7.xml.rels 里**没有**任何 image 关系
（只有 style7/colors7/drawing15 三条），所以本图三个系列都是纯色填充。
那张 50x1 的 ../media/image5.png 属于 chart8.xml（工作表「9 对比柱形图」，
用 srgbClr 之外的 blip 填充），与图 8 无关，切勿混用。

坐标轴/数据标签的 Latin 字形继承主题字体（+mn-lt = Calibri），中日韩字形
继承工作簿默认字体（等线 / DengXian）。

运行：python chart8_percent_stacked.py
输出：chart8_percent_stacked.png（832 x 588，与 Excel 导出图等比同尺寸）
"""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.transforms import ScaledTranslation

import chartkit

# --------------------------------------------------------------------------
# 常量：全部按 Excel 图表的原始定义换算
# --------------------------------------------------------------------------

DPI = chartkit.DPI                              # 100
FIG_W_PX = 832                                  # Excel 图表对象宽 416pt × 2
FIG_H_PX = chartkit.height_px_of(8)             # 图表对象高 294pt × 2 = 588
FONT_SCALE = chartkit.FONT_SCALE                # 字号换算：2 * 72 / DPI = 1.44

BACKGROUND = chartkit.BACKGROUND                # 图表区底色 #1A1E43

# 三个系列的纯色填充（chart7.xml 里三个 c:spPr 的 srgbClr）
DARK_BLUE = "#09387E"      # 系列0 销量
LIGHT_BLUE = "#82ADD7"     # 系列1 占位1
DARK_RED = "#9B3D4F"       # 系列2 占位2
LABEL_COLOR = "#F2F2F2"    # bg1 lumMod 95%：类别标签与数据标签共用
FOOTNOTE_COLOR = "#D9D9D9"  # bg1 lumMod 85%：脚注

# 类别按 XML 顺序（$B$3:$B$8）；横向条形图里 idx=0 画在最下面
CATEGORIES = ["华北", "华南", "东北", "西北", "西南", "华东"]
SALES = [4321, 1946, 1536, 1872, 1369, 2109]        # 系列0 $C$3:$C$8
PLACEHOLDER = [0, 2375, 2785, 2449, 2952, 2212]     # 系列1 $D$3:$D$8
REFERENCE = 1080.25                                 # 系列2 $E$3:$E$8，六行同值
# 系列2 用「单元格区域标签」显示 $F$3:$F$8，按类别顺序
PERCENT_LABELS = ["-13.6%", "-20.8%", "-9.3%", "-15.9%", "-17.9%", "-5.8%"]

TITLE = "2021年各区域销量及同比情况"                       # 18pt 加粗
SUBTITLE = "各区域商品销量同比去年均有下降，其中华南下降最多，同比下降20.8%"  # 11pt
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.01.01"            # 8pt

# manualLayout 存的是小数坐标，Excel 渲染时会取整到设备像素（图 1/2 都要为此
# 补半像素）。本图实测六个条心相对标注值的残差都在 1px 以内（上边 0.88px、
# 下边 0.09px），试过 -1.5 ~ +1.0px 的扫描，0 就是最优，故不微调。
AXES_DY_PX = 0.0

# gapWidth=30%：条高占类别高的比例为 1 / (1 + 0.30)
GAP_WIDTH_PCT = 30.0
BAR_HEIGHT = 1.0 / (1.0 + GAP_WIDTH_PCT / 100.0)

# 数值轴被删除（valAx delete=1），范围由 Excel 自动取整得到 0~6000；
# 六条总量均为 5401.25，实测条长 611px / 绘图区宽 679px = 90.0% = 5401.25 / 6000
X_MAX = 6000

# ---- 以下落点均为「实测」：在 reference/chart8_excel.png 上量出墨迹行/列范围，
#      再折算成 matplotlib 坐标（Excel 文本行盒与 matplotlib 基线规则不同，硬算易偏）。
#      带 _DY_PX 的常数一律是显示坐标：正值向上。

# 类别标签：绘图区左缘 105.7px，标签墨迹右缘 88px（实测），故间距 17.7px
CATEGORY_LABEL_PAD_PT = 12.0
# 类别标签竖直微调：Excel 把刻度文字按行框居中，matplotlib 按墨迹包围盒居中，
# 等宽汉字两者差 3px，这里把标签整体上移 3px（实测 185~201 vs 188~204）
CATEGORY_LABEL_DY_PX = 3.0

# 系列0 数据标签（dLblPos=inEnd）：数字墨迹右缘距深蓝段末 12.5px（实测六行一致）
VALUE_LABEL_INSET_PX = 12.5
# 数据标签竖直微调：数字墨迹行目标为 189~201（条心 194.5），基线规则差异下移 2px
DATA_LABEL_DY_PX = -2.0

# 标题/副标题文本框：a:off x=241301EMU=19pt，加 bodyPr 默认左内缩 7.2pt，
# 文字左缘落 52.4px（实测标题墨迹起于 55px，'2' 有约 2px 左侧留白）
TEXT_LEFT_PX = 53.0
TITLE_BASELINE_PX = 82.0      # 标题墨迹行 53~87（实测，18pt 加粗）
SUBTITLE_BASELINE_PX = 127.0  # 副标题墨迹行 108~129（实测，11pt）
# 脚注文本框：a:off x=14.9pt + 默认左内缩 7.2pt = 44.2px（实测墨迹起于 46px）
FOOTNOTE_LEFT_PX = 44.2
FOOTNOTE_BASELINE_PX = 561.0  # 脚注墨迹行 548~562（实测，8pt）


def main():
    layout = chartkit.manual_layout(7)          # 直接读 chart7.xml，核对编号
    figure = chartkit.new_figure(FIG_W_PX, FIG_H_PX)
    axis = chartkit.plot_area(figure, layout, FIG_H_PX, AXES_DY_PX)
    axis.set_axisbelow(True)

    positions = np.arange(len(CATEGORIES))

    # ---- 三段堆叠条形：left 依次累加，得到经典的比例堆积效果 ----
    axis.barh(positions, SALES, height=BAR_HEIGHT,
              color=DARK_BLUE, edgecolor="none", zorder=2)
    axis.barh(positions, PLACEHOLDER, height=BAR_HEIGHT, left=SALES,
              color=LIGHT_BLUE, edgecolor="none", zorder=2)
    axis.barh(positions, [REFERENCE] * len(CATEGORIES), height=BAR_HEIGHT,
              left=np.array(SALES) + np.array(PLACEHOLDER),
              color=DARK_RED, edgecolor="none", zorder=2)

    # ---- 坐标轴：两个轴都被隐藏（数值轴 delete=1，类别轴无轴线）----
    axis.set_xlim(0, X_MAX)
    axis.set_ylim(-0.5, len(CATEGORIES) - 0.5)
    axis.set_xticks([])
    axis.set_yticks([])
    axis.grid(False)
    for spine in axis.spines.values():
        spine.set_visible(False)

    # ---- 类别标签：画在绘图区左外侧，无刻度线 ----
    axis.set_yticks(positions)
    axis.set_yticklabels(CATEGORIES, color=LABEL_COLOR,
                         fontsize=9 * FONT_SCALE, fontfamily=chartkit.AXIS_FONTS)
    axis.tick_params(axis="y", length=0, pad=CATEGORY_LABEL_PAD_PT)
    shift = ScaledTranslation(0, CATEGORY_LABEL_DY_PX / DPI, figure.dpi_scale_trans)
    for label in axis.get_yticklabels():
        label.set_transform(label.get_transform() + shift)

    # ---- 数据标签 ----
    # 系列0（深蓝）：数字贴在深蓝段右端内侧（inEnd）。
    # 系列2（暗红）：百分比居中于暗红段（六行都落在同一条竖线上）。
    dy = DATA_LABEL_DY_PX * 72 / DPI
    for index, position in enumerate(positions):
        axis.annotate(str(SALES[index]),
                      xy=(SALES[index], position),
                      xytext=(-VALUE_LABEL_INSET_PX * 72 / DPI, dy),
                      textcoords="offset points",
                      ha="right", va="center",
                      color=LABEL_COLOR, fontsize=10 * FONT_SCALE,
                      fontfamily=chartkit.AXIS_FONTS, zorder=5)
        centre = float(SALES[index] + PLACEHOLDER[index]) + REFERENCE / 2.0
        axis.annotate(PERCENT_LABELS[index],
                      xy=(centre, position),
                      xytext=(0, dy),
                      textcoords="offset points",
                      ha="center", va="center",
                      color=LABEL_COLOR, fontsize=10 * FONT_SCALE,
                      fontfamily=chartkit.AXIS_FONTS, zorder=5)

    # ---- 标题 / 副标题 / 脚注：userShapes(drawing15.xml) 里的两个文本框 ----
    figure.text(TEXT_LEFT_PX / FIG_W_PX, 1.0 - TITLE_BASELINE_PX / FIG_H_PX,
                TITLE, ha="left", va="baseline", color="white",
                fontsize=18 * FONT_SCALE, fontweight="bold",
                fontfamily=chartkit.UI_FONT)
    figure.text(TEXT_LEFT_PX / FIG_W_PX, 1.0 - SUBTITLE_BASELINE_PX / FIG_H_PX,
                SUBTITLE, ha="left", va="baseline", color="white",
                fontsize=11 * FONT_SCALE, fontfamily=chartkit.UI_FONT)
    figure.text(FOOTNOTE_LEFT_PX / FIG_W_PX, 1.0 - FOOTNOTE_BASELINE_PX / FIG_H_PX,
                FOOTNOTE, ha="left", va="baseline", color=FOOTNOTE_COLOR,
                fontsize=8 * FONT_SCALE, fontfamily=chartkit.UI_FONT)

    return chartkit.save(figure, "chart8_percent_stacked.png")


if __name__ == "__main__":
    if matplotlib.get_backend().lower() == "agg":
        main()
    else:
        main()
        plt.show()
