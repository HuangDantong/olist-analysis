# -*- coding: utf-8 -*-
"""
图表复刻 10/15 —— 甘特图（进度条）

复刻对象：`第二章 图表(前15).xlsx` 工作表「10 甘特图」中的图表。
原始图表由 Excel 生成，本脚本用 matplotlib 逐像素还原其外观。

**注意编号**：工作表序号是 10，但对应的图表部件是 xl/charts/chart9.xml
（xl/drawings/drawing19.xml 是它的 userShapes）。核对方法：chart9.xml 里
所有 c:f 公式都指向 '10 甘特图'!，且 reference/chart10_excel.png 与该
工作表导出的图一致。

图表结构：7 行横向**堆积条形图**（barDir=bar、grouping=stacked、
overlap=100），把「日期轴 + 起点 + 时长」拼成甘特条：

    系列0「开始日期」  填充 noFill（隐形）        值 = 开始日期序列号
                       误差线 errBarType=plus     值 = 已完成天数 $F$4:$F$10
                       errValType=cust            线宽 184150EMU = 14.5pt
                       noEndCap=1                 颜色 00B0F0 透明度 80%
    系列1「项目天数」  填充 #0070C0                值 = 项目天数 $D$4:$D$10
                       数据标签 pos=ctr            文字取自 $E$4:$E$10（完成率）

因为 grouping=stacked 且 overlap=100，系列1 的条正好从系列0 的条末端接着
画：系列0 是隐形条，长度 = 「开始日期 - 坐标轴最小值」，所以系列1 的**左端
正好落在开始日期**上，这就是 Excel 里做甘特图的标准手法。

系列0 的误差线是**加号方向的自定义误差线**：在横向条形图里误差线沿数值轴
（水平）方向从隐形条末端再向右延伸「已完成天数」，线宽 14.5pt ≈ 与条高相当，
于是它盖在系列1 的条上、把「已完成部分」染成浅蓝：

    00B0F0 以 80% 不透明度叠在 #0070C0 上
    = 0.8×(0,176,240) + 0.2×(0,112,192) = (0,163,230) = #00A3E6

实测原图这两种颜色各占一半面积（#0070C0 7575px、#00A3E6 7072px），证明
误差线确实画在条的**上层**（若在下层会被不透明的条完全遮住）。

数据来源：
  '10 甘特图'!$B$4:$B$10   类别（制定计划…项目总结，倒序绘制：idx0 在最上）
  '10 甘特图'!$C$4:$C$10   开始日期 [44621,44633,44642,44653,44667,44692,44707]
  '10 甘特图'!$D$4:$D$10   项目天数 [11, 8, 10, 13, 24, 14, 7]      → 系列1 值
  '10 甘特图'!$E$4:$E$10   完成率   [51%,32%,21%,85%,36%,68%,68%]   → 数据标签
  '10 甘特图'!$F$4:$F$10   已完成天数 [5.61,2.56,2.1,11.05,8.64,9.52,4.76]
                                       = 项目天数 × 完成率 → 系列0 误差线值

样式规格全部取自该 xlsx 的图表 XML（chart9.xml）与 userShapes（drawing19.xml）：

    XML 里的定义                              matplotlib 实现
    --------------------------------------   ------------------------------------
    图表区底色 srgbClr 1A1E43               chartkit.BACKGROUND
    绘图区 manualLayout x=0.16559865        chartkit.plot_area(figure, layout, ...)
        y=0.22376065 w=0.74318275           （8 条网格线实测落在 146/240/335/
        h=0.71789530                        429/523/617/711/805，残差 < 1px，不微调）
    barDir=bar grouping=stacked             axis.barh(...)，两条叠加
    gapWidth=100%                           条高 = 1/(1+1.00) = 0.5 格 = 30.15px
    overlap=100%                            系列1 的 left = 系列0 的值（起点日期）
    系列0 填充 noFill（隐形条）              不画；只画它的误差线
    系列0 误差线 ln w=184150EMU=14.5pt       ERROR_BAR_HEIGHT = 29px / 60.303px
        srgbClr 00B0F0 alpha=80000           OVERLAY = #00A3E6（与 #0070C0 的叠加结果）
        noEndCap, errBarType=plus            从开始日期向右量 COMPLETED_DAYS 天
    系列1 填充 srgbClr 0070C0                BAR_COLOR
    边框 ln/noFill（两条都无描边）            edgecolor="none"
    valAx min=44621 max=44726 majorUnit=15   xlim = (44621, 44726)，每 15 天一条网格线
    valAx numFmt m/d/yyyy（sourceLinked）    刻度文字实测为 2022/3/1…2022/6/14
    valAx axPos=t（刻度在上方）                axis.xaxis.tick_top()
    valAx 网格线 bg1 lumMod95% alpha40000    GRID_COLOR #717389，线宽 6350EMU=0.5pt
        prstDash=lgDash                      实测虚线节拍 9px 实 / 2px 空（周期 11px）
    catAx txPr sz=900 bg1 lumMod95000        类别标签 #F2F2F2，9pt，tickLblPos=nextTo
    catAx spPr noFill（无类别轴线）           spines 全部隐藏
    valAx spPr noFill（无数值轴线）           spines 全部隐藏
    数据标签 dLblPos=ctr sz=900 bg1 lumMod95% #F2F2F2，居中于系列1 的条
    标题 16pt bold 微软雅黑 scheme:bg1        userShapes 文本框 11（居中、顶部对齐）

坐标轴/数据标签的 Latin 字形继承主题字体（+mn-lt = Calibri），中日韩字形
继承工作簿默认字体（等线 / DengXian）。

运行：python chart10_gantt.py
输出：chart10_gantt.png（886 x 588，与 Excel 导出图同尺寸）
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
FIG_W_PX = 886                                  # Excel 图表对象宽 442.88pt × 2 = 885.76
FIG_H_PX = chartkit.height_px_of(10)            # 图表对象高 294pt × 2 = 588
FONT_SCALE = chartkit.FONT_SCALE                # 字号换算：2 * 72 / DPI = 1.44

BACKGROUND = chartkit.BACKGROUND                # 图表区底色 #1A1E43
BAR_COLOR = "#0070C0"       # 系列1「项目天数」的 srgbClr
OVERLAY_COLOR = "#00A3E6"   # 系列0 误差线 00B0F0(alpha 80%) 叠在条上的合成色
LABEL_COLOR = "#F2F2F2"     # bg1 lumMod95000：类别标签 / 日期标签 / 数据标签
GRID_COLOR = "#717389"      # bg1 lumMod95% alpha40000 叠在 1A1E43 上的合成色

# 类别按 XML 顺序（$B$4:$B$10）；横向条形图里 idx=0 画在最上面
CATEGORIES = ["制定计划", "方案设计", "资源调配", "第一阶段",
              "第二阶段", "第三阶段", "项目总结"]
# $C$4:$C$10 开始日期（Excel 日期序列号），同时是系列0（隐形条）的值
START_DATES = [44621, 44633, 44642, 44653, 44667, 44692, 44707]
DURATIONS = [11, 8, 10, 13, 24, 14, 7]          # $D$4:$D$10 项目天数 → 系列1
COMPLETED = [5.61, 2.56, 2.1, 11.05, 8.64, 9.52, 4.76]   # $F$4:$F$10 已完成天数
PERCENT_LABELS = ["51%", "32%", "21%", "85%", "36%", "68%", "68%"]  # $E$4:$E$10

# valAx scaling min/max，以及 majorUnit=15 天一条网格线
DATE_MIN, DATE_MAX = 44621, 44726
MAJOR_UNIT = 15
# valAx numFmt 是 m/d/yyyy 但 sourceLinked=1，实际跟随单元格格式，实测为 yyyy/m/d
DATE_LABELS = ["2022/3/1", "2022/3/16", "2022/3/31", "2022/4/15",
               "2022/4/30", "2022/5/15", "2022/5/30", "2022/6/14"]

TITLE = "2022年化妆品类目采购项目进度"           # 16pt 加粗 微软雅黑

# gapWidth=100%：条高占类别高的比例为 1 / (1 + 1.00) = 0.5
GAP_WIDTH_PCT = 100.0
BAR_HEIGHT = 1.0 / (1.0 + GAP_WIDTH_PCT / 100.0)

# 绘图区在画布里的像素高度，用来把误差线的 pt 宽度折算成「类别格」高度
PLOT_H_PX = float(chartkit.manual_layout(9)["h"]) * FIG_H_PX
CATEGORY_PX = PLOT_H_PX / len(CATEGORIES)
# 误差线 a:ln w=184150EMU = 14.5pt = 29px（误差线是线，宽度按设备像素栅格化）
ERROR_BAR_HEIGHT = 14.5 * chartkit.PX_PER_PT / CATEGORY_PX

# manualLayout 存的是小数坐标，Excel 渲染时取整到设备像素。本图实测 7 个条心
# 落在 161.5 / 221.5 / … / 523，与标注值（161.72 / 523.5）残差都在 0.5px 内，
# 8 条网格线的列号也完全吻合，故不微调。
AXES_DY_PX = 0.0

# ---- 以下落点均为「实测」：在 reference/chart10_excel.png 上量出墨迹行/列范围，
#      再折算成 matplotlib 坐标（Excel 文本行盒与 matplotlib 基线规则不同，硬算易偏）。

# 类别标签（绘图区左外侧）：墨迹右缘实测 x=128，绘图区左缘 146.65px，间距 18.7px
CATEGORY_LABEL_PAD_PT = 11.9
# 类别标签竖直微调：实测原图墨迹行 152~168，把复刻图量到同一行后定为 +2.5px
# （正数向上）
CATEGORY_LABEL_DY_PX = 2.5

# 日期标签（绘图区上方）：墨迹行 100~114，绘图区顶 131.57px，间距 17.6px
DATE_LABEL_PAD_PT = 9.82

# 数据标签（dLblPos=ctr）：竖直居中于系列1 的条，条心 161.5，墨迹行 156~167
DATA_LABEL_DY_PX = 0.0

# 标题文本框 11：relSizeAnchor from y=0.00129 → 0.76px，加默认上内缩 tIns=3.6pt=7.2px
# 文字水平居中（实测标题墨迹 x 213~673，中心 443 = 画布中心）
TITLE_BASELINE_PX = 48.6      # 标题墨迹行 22~51（实测，16pt 加粗）


def main():
    layout = chartkit.manual_layout(9)          # 直接读 chart9.xml，核对编号
    figure = chartkit.new_figure(FIG_W_PX, FIG_H_PX)
    axis = chartkit.plot_area(figure, layout, FIG_H_PX, AXES_DY_PX)
    axis.set_axisbelow(True)

    positions = np.arange(len(CATEGORIES))

    # ---- 网格线：8 条竖虚线，画在条的下层（原图里条把网格线完全盖住）----
    # 单独用 Line2D 画：axis.grid() 会把绘图区边缘那条（x=44621）裁掉一半。
    for index in range(len(DATE_LABELS)):
        value = DATE_MIN + index * MAJOR_UNIT
        axis.add_line(Line2D([value, value], [6.5, -0.5],     # 自上而下，与虚线起笔一致
                             color=GRID_COLOR, linewidth=0.5 * FONT_SCALE,
                             dashes=(8.5, 2.5), zorder=1, clip_on=False))

    # ---- 甘特条 ----
    # 系列1 的值是「项目天数」，左端由系列0 的隐形条顶到「开始日期」上；
    # 这里直接给出 left = 开始日期，等价于 XML 里的 stacked + overlap=100%。
    axis.barh(positions, DURATIONS, left=START_DATES, height=BAR_HEIGHT,
              color=BAR_COLOR, edgecolor="none", zorder=2)
    # 系列0 的加号误差线：从开始日期再向右 14.5pt 粗、已完成天数长的一段，
    # 盖在条上形成浅蓝色的「已完成部分」（实测与 #00A3E6 完全一致）
    axis.barh(positions, COMPLETED, left=START_DATES, height=ERROR_BAR_HEIGHT,
              color=OVERLAY_COLOR, edgecolor="none", zorder=3)

    # ---- 坐标范围 ----
    axis.set_xlim(DATE_MIN, DATE_MAX)
    # 横向条形图的类别轴是**反向**的：第一类画在最上面（matplotlib 默认 y 向上，
    # 不反过来「制定计划」会跑到最底下，整张图上下颠倒）。
    axis.set_ylim(len(CATEGORIES) - 0.5, -0.5)

    # ---- 两条轴在 XML 里都是 spPr/noFill：没有轴线、没有刻度线 ----
    axis.grid(False)
    for spine in axis.spines.values():
        spine.set_visible(False)

    # ---- 类别标签：画在绘图区左侧外侧 ----
    axis.set_yticks(positions)
    axis.set_yticklabels(CATEGORIES, color=LABEL_COLOR,
                         fontsize=9 * FONT_SCALE, fontfamily=chartkit.AXIS_FONTS)
    axis.tick_params(axis="y", length=0, pad=CATEGORY_LABEL_PAD_PT)
    shift = ScaledTranslation(0, CATEGORY_LABEL_DY_PX / DPI, figure.dpi_scale_trans)
    for label in axis.get_yticklabels():
        label.set_transform(label.get_transform() + shift)

    # ---- 日期标签：valAx 的 axPos="t"，刻度文字在绘图区上方，居中于网格线 ----
    axis.xaxis.tick_top()
    axis.set_xticks([DATE_MIN + i * MAJOR_UNIT for i in range(len(DATE_LABELS))])
    axis.set_xticklabels(DATE_LABELS, color=LABEL_COLOR,
                         fontsize=9 * FONT_SCALE, fontfamily=chartkit.AXIS_FONTS)
    axis.tick_params(axis="x", length=0, pad=DATE_LABEL_PAD_PT)

    # ---- 数据标签：pos=ctr，居中于系列1 的条 ----
    dy = DATA_LABEL_DY_PX * 72 / DPI
    for index, position in enumerate(positions):
        centre = START_DATES[index] + DURATIONS[index] / 2.0
        axis.annotate(PERCENT_LABELS[index],
                      xy=(centre, position),
                      xytext=(0, dy),
                      textcoords="offset points",
                      ha="center", va="center",
                      color=LABEL_COLOR, fontsize=9 * FONT_SCALE,
                      fontfamily=chartkit.AXIS_FONTS, zorder=5)

    # ---- 标题：userShapes(drawing19.xml) 里唯一的文本框，水平居中 ----
    figure.text(0.5, 1.0 - TITLE_BASELINE_PX / FIG_H_PX,
                TITLE, ha="center", va="baseline", color="white",
                fontsize=16 * FONT_SCALE, fontweight="bold",
                fontfamily=chartkit.UI_FONT)

    return chartkit.save(figure, "chart10_gantt.png")


if __name__ == "__main__":
    if matplotlib.get_backend().lower() == "agg":
        main()
    else:
        main()
        plt.show()
