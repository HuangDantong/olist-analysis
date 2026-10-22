# -*- coding: utf-8 -*-
"""图表复刻 7/15 —— 蝴蝶图（单元格 REPT 版）

复刻对象：`第二章 图表(前15).xlsx` 工作表「7 蝴蝶图」右半部分的那块成品图。

这张图和其它 14 张不一样：它**根本不是图表对象**，而是用单元格堆出来的
（俗称 REPT 图 / 字符条形图）。工作表里 H、J 两列是草稿区，真正拿得出手的
成品在 Q~U 列：

    Q7  0.36              2022 年的数，百分比格式，右对齐
    R7  =REPT("|",C3*200) 把数值乘 200，重复出 72 个「|」——这就是柱子
    S7  华东              类别名，居中
    T7  =REPT("|",D3*200) 2021 年的柱子
    U7  0.42              2021 年的数，左对齐

所以柱子的长度不是画出来的，是「竖线字符的个数」堆出来的；条子上那层细密
竖纹就是 Stencil 字体里「|」字形的本来面目（Stencil 是套镂空字，竖线本身
就是个带纹理的长方块）。本脚本照搬这套算法：**长度 = 字符数 × 字距 + 前导**，
超出单元格可见宽度的部分截断（原图第 1、2 行的蓝柱就是这么被切齐的）。

条子的纹理没有用 matplotlib 排 Stencil 字，而是按实测的三色周期铺一层位图：
Excel 用 GDI 光栅化出来的笔画比 FreeType 粗半像素，逐像素比下来整片柱子的
底色会差十几个色阶，而柱子在图上占的面积又最大（这一项就吃掉了一半的误差）。
两者一圈的平均色是一样的，只是明暗调制深度不同，所以照实测周期铺色更准。

样式全部取自 `xl/worksheets/sheet7.xml` 的单元格样式（s=29/31/38/39/40）
与 `xl/styles.xml`：

    底色        单元格填充 FF1A1E43
    柱子字体    Stencil 12pt；2022 列 FF0070C0，2021 列 FFE74E69
    数值字体    微软雅黑 8pt，白色，百分比格式（numFmtId=9，即 0%）
    类别字体    微软雅黑 8pt，白色，居中
    标题        微软雅黑 14pt 加粗，白色
    副标题      微软雅黑 10pt，白色
    脚注        微软雅黑 8pt，白色
    行高        15.75pt（第 7~11 行），换算成 2px/pt 就是 31.5px 一档

几何量取自 reference/chart7_excel.png（Excel 把 B2:U22 这块区域按 2px/pt
导出后的像素坐标）——单元格坐标算起来要绕一圈列宽磅值，直接量更准。

运行：python chart7_rept_butterfly.py
输出：chart7_rept_butterfly.png（714 x 390，与导出的那块区域同尺寸）
"""

import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# --------------------------------------------------------------------------
# 常量
# --------------------------------------------------------------------------

DPI = 100
FIG_W_PX, FIG_H_PX = 714, 390

# 字号换算：Excel 图表按 2px/pt 导出，matplotlib dpi=100 时 1pt = 100/72 px
FONT_SCALE = 2 * 72 / DPI  # 1.44

BACKGROUND = "#1A1E43"
TEXT_COLOR = "white"
UI_FONT = "Microsoft YaHei"

CATEGORIES = ["华东", "西北", "东北", "华北", "华南"]
VALUES_2022 = [0.36, 0.31, 0.18, 0.13, 0.09]   # '7 蝴蝶图'!C3:C7
VALUES_2021 = [0.42, 0.26, 0.19, 0.12, 0.05]   # '7 蝴蝶图'!D3:D7
REPT_SCALE = 200                                # =REPT("|", 数值 * 200)

TITLE = "2022年第一季度销售目标完成情况"
SUBTITLE = "华东区域完成率最高达到36%，但是相比去年的42%有所下降"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.03.31"

# ---- 行几何（实测）----
# 五根柱子是第 7~11 行，行高 15.75pt -> 31.5px，柱子的墨迹高 20px（Stencil
# 12pt 的「|」字高）。
BAR_TOP = 148.0          # 第 7 行柱子的墨迹顶边（实测）
BAR_ROW_PITCH = 32.0     # 行距（实测）
BAR_INK_HEIGHT = 20.0    # 柱子墨迹高度（实测）

# ---- 横向布局（实测）----
LEFT_VALUE_RIGHT = 104.0     # Q 列数值右对齐到这条线
BAR_2022_RIGHT = 289.0       # R 列柱子的右端（2022 柱右对齐）
BAR_2022_MAX = 182.0         # R 列可见宽度，超出部分被单元格切掉
CATEGORY_CENTER = 344.0      # S 列类别名居中
BAR_2021_LEFT = 398.0        # T 列柱子的左端（2021 柱左对齐）
BAR_2021_MAX = 233.0         # T 列可见宽度
RIGHT_VALUE_LEFT = 613.0     # U 列数值左对齐到这条线

# 一个「|」的步进宽度：Stencil 12pt 实测 3.0px；外加 4px 的字形前导
# （「|」的笔画并不占满整个字身，第一笔会往前探一点，实测五行都是这个值）。
CHAR_ADVANCE = 3.0
BAR_LEAD_PX = 4.0

# 「|」笔画内部的明暗周期（实测）：Excel 用 GDI 光栅化，笔画略宽，于是每个
# 字身里呈现「亮-中-暗」三列。按 x % 3 取色，2022 / 2021 两列的相位不同。
STRIPE_2022 = [(3, 115, 197), (0, 91, 159), (7, 103, 178)]     # x%3 = 0,1,2
STRIPE_2021 = [(233, 64, 94), (174, 75, 103), (218, 79, 105)]  # x%3 = 0,1,2

# 文字基线（实测：把复刻图的墨迹量到与原图同一行）
DIGIT_BASELINE_DY = 15.0
CJK_BASELINE_DY = 15.0

TITLE_BASELINE = 54.5
SUBTITLE_BASELINE = 93.0
FOOTNOTE_BASELINE = 364.0
TEXT_LEFT = 43.0
FOOTNOTE_LEFT = 28.0

plt.rcParams["axes.unicode_minus"] = False


def stripe_texture(left_px, width_px, colours):
    """铺一行 width_px 像素的三色纹理，相位跟随绝对像素列。"""
    index = (np.arange(width_px) + int(round(left_px))) % 3
    return (np.array(colours, dtype=float)[index] / 255.0).reshape(1, width_px, 3)


def draw_rept_bar(axis, value, maximum, row, colours, right_aligned):
    """把一串「|」画成一根柱子：长度 = 字符数 × 字距 + 前导，再截到单元格宽度。"""
    characters = int(value * REPT_SCALE)
    length = min(characters * CHAR_ADVANCE + BAR_LEAD_PX, maximum)
    left = BAR_2022_RIGHT - length if right_aligned else BAR_2021_LEFT
    top = BAR_TOP + row * BAR_ROW_PITCH
    width = int(round(length))

    axis.imshow(stripe_texture(left, width, colours),
                extent=(left, left + width, top + BAR_INK_HEIGHT, top),
                aspect="auto", interpolation="nearest", zorder=4)


def main():
    figure = plt.figure(figsize=(FIG_W_PX / DPI, FIG_H_PX / DPI), dpi=DPI)
    figure.patch.set_facecolor(BACKGROUND)

    # 整块区域就是图，用一个铺满画布的坐标系，单位直接用导出图的像素，
    # y 轴反转成「向下为正」，这样下面写的都是实测出来的像素坐标。
    axis = figure.add_axes([0, 0, 1, 1])
    axis.set_facecolor(BACKGROUND)
    axis.set_xlim(0, FIG_W_PX)
    axis.set_ylim(FIG_H_PX, 0)
    axis.set_xticks([])
    axis.set_yticks([])
    for spine in axis.spines.values():
        spine.set_visible(False)

    # ---- 标题 / 副标题 / 脚注 ----
    axis.text(TEXT_LEFT, TITLE_BASELINE, TITLE, ha="left", va="baseline",
              color=TEXT_COLOR, fontsize=14 * FONT_SCALE, fontweight="bold",
              fontfamily=UI_FONT)
    axis.text(TEXT_LEFT, SUBTITLE_BASELINE, SUBTITLE, ha="left", va="baseline",
              color=TEXT_COLOR, fontsize=10 * FONT_SCALE, fontfamily=UI_FONT)
    axis.text(FOOTNOTE_LEFT, FOOTNOTE_BASELINE, FOOTNOTE, ha="left", va="baseline",
              color=TEXT_COLOR, fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)

    # ---- 五根柱子 + 两端的数值 + 中间的类别名 ----
    for row, (category, first, second) in enumerate(
            zip(CATEGORIES, VALUES_2022, VALUES_2021)):
        draw_rept_bar(axis, first, BAR_2022_MAX, row, STRIPE_2022, right_aligned=True)
        draw_rept_bar(axis, second, BAR_2021_MAX, row, STRIPE_2021, right_aligned=False)

        top = BAR_TOP + row * BAR_ROW_PITCH
        axis.text(LEFT_VALUE_RIGHT, top + DIGIT_BASELINE_DY,
                  "%.0f%%" % (first * 100), ha="right", va="baseline",
                  color=TEXT_COLOR, fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)
        axis.text(CATEGORY_CENTER, top + CJK_BASELINE_DY, category,
                  ha="center", va="baseline", color=TEXT_COLOR,
                  fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)
        axis.text(RIGHT_VALUE_LEFT, top + DIGIT_BASELINE_DY,
                  "%.0f%%" % (second * 100), ha="left", va="baseline",
                  color=TEXT_COLOR, fontsize=8 * FONT_SCALE, fontfamily=UI_FONT)

    output = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "chart7_rept_butterfly.png")
    figure.savefig(output, dpi=200, facecolor=BACKGROUND)
    print("saved:", output)
    return figure


if __name__ == "__main__":
    if matplotlib.get_backend().lower() == "agg":
        main()
    else:
        main()
        plt.show()
