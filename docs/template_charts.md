# 教材模板复现索引（15 张）

- 生成时间：2026-10-22 10:00:34 中国标准时间
- 模板脚本目录：`D:\大数据分析及数据可视化\olist-analysis\scripts\templates`
- 输出目录：`D:\大数据分析及数据可视化\olist-analysis\outputs\figures\templates`
- 教材数据文件：`D:\大数据分析及数据可视化\《Excel数据可视化 - 从图表到数据大屏》-清华-郭宏远\第二章 图表(前15).xlsx`（**不随仓库分发**）

> 15 张图均为逐像素复现，配色、字号、渐变、标注位置取自教材 xlsx 的图表 XML，并与 Excel 导出图做像素比对。复现图使用教材配套数据，以保证与原图对照一致；真实业务图表见 `outputs/figures/business/`。

| # | 图表 | 脚本 | 输出 | 平均通道误差 | 像素一致率 | 状态 |
|---:|---|---|---|---:|---:|---|
| 1 | 渐变填充柱形图 | `chart1_gradient_bar.py` | `fig01_渐变柱形图.png` | 3.26/255 | 93.09% | ✅ 已重新渲染 |
| 2 | 柱形图 + 均值折线 | `chart2_mean_bar.py` | `fig02_带均值柱形图.png` | 2.38/255 | 96.15% | ✅ 已重新渲染 |
| 3 | 图片填充的胶囊柱形 | `chart3_rounded_gradient_bar.py` | `fig03_渐变圆角柱形图.png` | 1.96/255 | 95.91% | ✅ 已重新渲染 |
| 4 | 逐柱设色 + 气泡标注 | `chart4_annotated_bar.py` | `fig04_标注柱形图.png` | 1.67/255 | 96.43% | ✅ 已重新渲染 |
| 5 | 簇状柱形 + 手工图例框 | `chart5_clustered_bar.py` | `fig05_层叠柱形图.png` | 1.92/255 | 96.06% | ✅ 已重新渲染 |
| 6 | 隐形占位系列做的蝴蝶图 | `chart6_butterfly.py` | `fig06_蝴蝶图.png` | 2.12/255 | 96.30% | ✅ 已重新渲染 |
| 7 | 单元格 REPT 字符条形图 | `chart7_rept_butterfly.py` | `fig07_REPT蝴蝶图.png` | 5.76/255 | 87.42% | ✅ 已重新渲染 |
| 8 | 三段百分比堆积条形图 | `chart8_percent_stacked.py` | `fig08_数值百分比.png` | 2.29/255 | 96.01% | ✅ 已重新渲染 |
| 9 | 对比柱形 + 误差线差值箭头 | `chart9_compare_column.py` | `fig09_对比柱形图.png` | 4.22/255 | 94.98% | ✅ 已重新渲染 |
| 10 | 堆积条形 + 误差线做进度条 | `chart10_gantt.py` | `fig10_甘特图.png` | 2.54/255 | 96.34% | ✅ 已重新渲染 |
| 11 | 平滑折线 + 年份色带 | `chart11_smooth_line.py` | `fig11_平滑折线图.png` | 2.65/255 | 95.55% | ✅ 已重新渲染 |
| 12 | 棒棒糖 + 空心菱形标记 | `chart12_diamond_lollipop.py` | `fig12_菱形走势图.png` | 3.27/255 | 95.50% | ✅ 已重新渲染 |
| 13 | 双折线 + 手工标签 | `chart13_compare_line.py` | `fig13_对比折线图.png` | 3.30/255 | 94.61% | ✅ 已重新渲染 |
| 14 | 单值圆环 + 角度渐变 | `chart14_doughnut.py` | `fig14_单值圆环图.png` | 3.90/255 | 94.10% | ✅ 已重新渲染 |
| 15 | 柱形图 + SVG 图片填充 | `chart15_liquid_fill.py` | `fig15_水球图.png` | 1.61/255 | 95.33% | ✅ 已重新渲染 |

## 运行方式

```bash
python scripts/04_visuals_templates.py
```

## 说明

- 教材 xlsx 因版权与体积原因不放入公开仓库；脚本在找不到文件时会保留 `outputs/figures/templates/` 中已生成的 PNG。
- `scripts/templates/reference/` 只保留 15 个 `chartN_meta.txt`（图表高度），不保留 Excel 导出原图。
- 交付图以 **200 dpi** 输出；像素误差/一致率在 100 dpi 基准图上计算。
- 平均通道误差为与原图逐像素的平均通道差（0~255）；像素一致率为 RGB 各通道差值之和小于 12 的像素占比。
- 残余误差主要集中在文字抗锯齿：Excel 与 matplotlib 的字形光栅化器不同，几何位置已对齐。

> 本报告由 `scripts/04_visuals_templates.py` 自动生成。
