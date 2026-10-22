# -*- coding: utf-8 -*-
"""
07_paper_skeleton.py —— 生成论文 Word 框架

读取 docs/paper_outline.md 的结构，生成一份可直接编辑的
docs/论文框架.docx（宋体小四、1.5 倍行距、黑体标题）。

用法
----
    python scripts/07_paper_skeleton.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "论文框架.docx"


def set_run_font(run, name_cn: str, size: float, bold: bool = False):
    run.font.name = name_cn
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name_cn)
    run.font.size = Pt(size)
    run.bold = bold


def set_style_font(style, name_cn: str, size: float, bold: bool = False):
    style.font.name = name_cn
    style._element.rPr.rFonts.set(qn("w:eastAsia"), name_cn)
    style.font.size = Pt(size)
    style.font.bold = bold


def add_heading(doc: Document, text: str, level: int = 1):
    p = doc.add_heading(level=level)
    run = p.add_run(text)
    if level == 1:
        set_run_font(run, "黑体", 16, bold=True)
    else:
        set_run_font(run, "黑体", 14, bold=True)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    return p


def add_body(doc: Document, text: str, italic: bool = False):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(24)
    p.paragraph_format.line_spacing = 1.5
    run = p.add_run(text)
    set_run_font(run, "宋体", 12)
    run.italic = italic
    return p


def add_bullet(doc: Document, text: str):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.line_spacing = 1.5
    run = p.add_run(text)
    set_run_font(run, "宋体", 12)
    return p


def main() -> int:
    doc = Document()

    # 页面边距
    for section in doc.sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(2.8)
        section.right_margin = Cm(2.8)

    # 默认样式
    normal = doc.styles["Normal"]
    set_style_font(normal, "宋体", 12)
    normal.paragraph_format.line_spacing = 1.5

    # ---------------- 封面 ----------------
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("商业数据分析")
    set_run_font(run, "黑体", 26, bold=True)
    p.paragraph_format.space_before = Pt(80)

    for _ in range(3):
        doc.add_paragraph()

    cover_items = [
        ("题　　目：", "Olist 巴西电商商业数据分析：客户分层、品类结构与销售预测"),
        ("学　　院：", "数据科学学院"),
        ("专业班级：", "【填写专业班级】"),
        ("学　　号：", "【填写学号】"),
        ("姓　　名：", "【填写姓名】"),
        ("完成日期：", "2026 年 11 月"),
    ]
    for label, value in cover_items:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(label + value)
        set_run_font(run, "宋体", 14)

    doc.add_page_break()

    # ---------------- 摘要 ----------------
    add_heading(doc, "摘　要", 1)
    add_body(
        doc,
        "本文以 Olist 巴西电商公开数据集为研究对象，基于 2016—2018 年的 99,441 个订单、"
        "112,650 条商品明细和 99,224 条评价，构建了从数据获取、清洗治理、商业建模到可视化大屏的"
        "端到端分析链路。在完成多表关联、缺失值处理与指标派生后，本文使用 RFM 八分层、同期群留存、"
        "ABC/Pareto、波士顿矩阵和 SARIMA 时间序列模型，识别客户价值结构、复购规律、品类贡献与"
        "销售趋势，复现教材模板 15 张、绘制 10 张业务图、搭建 Streamlit 交互式大屏。研究发现："
        "约 47.5% 的高价值客户贡献了 78.0% 的 GMV；首购后第 1 个月平均留存率仅 0.44%；"
        "25.9% 的商品贡献 80.0% 的 GMV；延迟 4 天以上订单的平均评分由 4.29 降至 2.32；"
        "ARIMA(1,1,1) 的六个月回测 MAPE 为 5.59%。研究结果可为电商客户运营、品类管理、"
        "物流优化与销售预测提供参考。",
    )
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(24)
    run = p.add_run(
        "关键词：电商数据分析；RFM 模型；同期群分析；波士顿矩阵；SARIMA；可视化大屏"
    )
    set_run_font(run, "宋体", 12, bold=True)

    # ---------------- 正文 ----------------
    chapters = [
        ("第 1 章 引言", [
            "1.1 研究背景：巴西电商增长、Olist 平台背景、数据丰富但洞察不足。",
            "1.2 研究目的：验证公开电商数据能否支撑完整分析链路；用五个模型回答客户、商品、复购与预测问题。",
            "1.3 研究意义：实践意义、方法意义、教学意义。",
            "【写作提示】可在本章末尾插入图 26（大屏总览截图），先展示最终成果。",
        ]),
        ("第 2 章 数据准备与预处理", [
            "2.1 数据源介绍：Olist 数据集、9 张表、99,441 个订单、2016-09～2018-10、CC BY-NC-SA 4.0。",
            "2.2 合规获取方式：Kaggle 官方数据集 API，非爬虫；SHA256 校验；原始数据不入库。",
            "2.3 数据清洗与治理：时间字段、邮编前导零、缺失值、重复值、地理表聚合、指标派生。",
            "2.4 数据集概述与关联关系：主表 orders，多表通过 order_id/customer_id/product_id/seller_id 关联。",
            "【表格】表 1 数据表结构；表 2 清洗前后行数。",
            "【写作提示】模板复现图 1—15，业务图 16—25。",
        ]),
        ("第 3 章 商业分析模型", [
            "3.1 模型选型与阈值依据：RFM、同期群、ABC/Pareto、波士顿矩阵、SARIMA。",
            "3.2 RFM 客户分层：R/M 中位数，F ≥ 2；重要发展 + 重要挽留贡献 78.0% GMV。",
            "3.3 同期群留存：23 个同期群；第 1 月留存 0.44%，第 6 月 0.19%。",
            "3.4 ABC/Pareto：8,478 个 A 类商品（25.9%）贡献 80.0% GMV。",
            "3.5 波士顿矩阵：15 明星、17 现金牛、17 问题、14 瘦狗。",
            "3.6 SARIMA 预测：ARIMA(1,1,1) 最优，RMSE 67,582，MAPE 5.59%；未来 6 个月均值约 R$86 万/月。",
            "3.7 订单转化漏斗：下单 99,441 → 支付 99,281 → 发货 97,658 → 送达 96,476；总体送达率 97.0%。",
            "【表格】表 3 RFM 八分层；表 4 ABC 汇总；表 5 波士顿象限；表 6 SARIMA 指标；表 7 漏斗转化。",
            "【图表】图 16—图 25。",
        ]),
        ("第 4 章 可视化复现与大屏", [
            "4.0 作业要求对照：模板复现 15 张（要求 ≥10 种）、业务模型 10 张（模型类 7 张，≥6）、大屏 1 个（≥6 联动组件）、全部 Python 生成、200 dpi。",
            "4.1 教材模板复现（15 张）：教材第二章前 15 套，matplotlib 逐像素还原；平均通道误差 1.61—5.76/255，像素一致率 87.42%—96.43%；200 dpi。",
            "4.2 真实业务图表：10 张图的内容与核心结论（见图 16—图 25）。",
            "4.3 Streamlit 交互式大屏：KPI、趋势、品类、州、RFM、同期群、配送、波士顿、预测、支付、明细表；侧边栏联动。",
            "【图表】图 1—15 为模板复现；图 16—26 为业务图与大屏。",
        ]),
        ("第 5 章 商业洞察与建议", [
            "5.1 客户结构：抓住 47.5% 的高价值客群，分层运营。",
            "5.2 复购与留存：首购后 30/60/90 天触达，提升复购。",
            "5.3 商品与库存：A 类保库存，B 类组合销售，C 类长尾清理。",
            "5.4 品类策略：明星加投放、现金牛控成本、问题小步测试、瘦狗收缩。",
            "5.5 物流体验：延迟 4 天是分水岭，做承运商考核与主动补偿。",
            "5.6 支付结构：信用卡 + Boleto 双主力，优化分期与代金券。",
            "5.7 预测与备货：按区间备货，每月滚动更新。",
            "5.8 履约漏斗：总体送达率 97.0%，主要损失在取消/不可用；对取消原因分类并考核履约稳定性。",
            "【写作提示】每条建议写成“结论 + 证据 + 动作”，并对应一张图。",
        ]),
        ("第 6 章 总结与展望", [
            "6.1 研究总结：9 表关联、99,441 订单、5 个模型、15 张模板复现、10 张业务图、1 个大屏。",
            "6.2 主要结论：高价值客户集中、复购率低、A 类商品贡献 80%、物流延迟影响评分、预测 MAPE 5.59%。",
            "6.3 研究局限：数据年份较早、月度样本仅 20 个月、缺少成本/利润字段、RFM 阈值依赖中位数。",
            "6.4 未来展望：引入利润与 CLV、Prophet/LSTM 对比、实时数据大屏、A/B 实验。",
        ]),
    ]

    for title, points in chapters:
        add_heading(doc, title, 1)
        for point in points:
            if point.startswith("【"):
                add_body(doc, point, italic=True)
            else:
                add_bullet(doc, point)

    # ---------------- 参考文献 ----------------
    add_heading(doc, "参考文献", 1)
    refs = [
        "Olist. Brazilian E-Commerce Public Dataset by Olist[DB/OL]. Kaggle, 2018. "
        "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce.",
        "郭宏远. Excel数据可视化——从图表到数据大屏[M]. 北京: 清华大学出版社, 2022.",
        "Hughes A M. Strategic Database Marketing[M]. Chicago: Probus Publishing, 1994.",
        "Chen D, Sain S L, Guo K. Data mining for the online retail industry: A case study of "
        "RFM model-based customer segmentation[J]. Journal of Database Marketing & Customer "
        "Strategy Management, 2012, 19(3): 197-208.",
        "Box G E P, Jenkins G M, Reinsel G C, et al. Time Series Analysis: Forecasting and "
        "Control[M]. 5th ed. Hoboken: Wiley, 2015.",
        "Streamlit. Streamlit Documentation[EB/OL]. https://docs.streamlit.io.",
        "Plotly. Plotly Python Open Source Graphing Library[EB/OL]. https://plotly.com/python/.",
    ]
    for i, ref in enumerate(refs, 1):
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.5
        run = p.add_run(f"[{i}] {ref}")
        set_run_font(run, "宋体", 10.5)

    # ---------------- 附录 ----------------
    add_heading(doc, "附录 A AI 使用披露", 1)
    for item in [
        "使用工具：Claude Code（Anthropic）。",
        "使用环节：数据下载脚本、清洗流水线、RFM/同期群/ABC/波士顿/SARIMA 代码、"
        "matplotlib/Plotly 图表、Streamlit 大屏、论文框架。",
        "提示词示例：基于 Olist 数据集设计分析流程；用 matplotlib 绘制 10 张业务图；"
        "生成 Streamlit 大屏，包含 6 个以上组件和侧边栏联动筛选。",
        "人工审核：作者检查了数据许可、字段口径、模型阈值、图表结论与论文表述；"
        "所有数字均来自可复现脚本，未使用 AI 编造数据。",
        "声明：AI 仅作为辅助工具，论文的观点、结论与最终表述由作者负责。",
    ]:
        add_bullet(doc, item)

    add_heading(doc, "附录 B 代码与复现", 1)
    add_body(doc, "项目根目录：olist-analysis/；一键复现命令见 README.md。")
    for cmd in [
        "pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple",
        "python scripts/00_download.py",
        "python scripts/01_load.py",
        "python scripts/02_clean.py",
        "python scripts/03_models.py",
        "python scripts/05_visuals_business.py",
        "streamlit run scripts/06_dashboard.py",
    ]:
        p = doc.add_paragraph()
        run = p.add_run(cmd)
        run.font.name = "Consolas"
        run.font.size = Pt(10)

    add_heading(doc, "附录 C 图表索引", 1)
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, text in enumerate(["图号", "文件", "说明"]):
        hdr[i].text = ""
        run = hdr[i].paragraphs[0].add_run(text)
        set_run_font(run, "黑体", 10.5, bold=True)

    chart_rows = [
        ("图 1—15", "outputs/figures/templates/", "教材模板复现（15 张）"),
        ("图 16", "fig16_月度GMV与预测.png", "月度 GMV 与预测"),
        ("图 17", "fig17_RFM分层贡献.png", "RFM 分层"),
        ("图 18", "fig18_同期群留存热力图.png", "同期群留存"),
        ("图 19", "fig19_ABC帕累托图.png", "ABC/Pareto"),
        ("图 20", "fig20_波士顿矩阵.png", "波士顿矩阵"),
        ("图 21", "fig21_品类GMV前15.png", "品类 Top 15"),
        ("图 22", "fig22_配送延迟与评价.png", "配送延迟与评分"),
        ("图 23", "fig23_支付方式结构.png", "支付方式"),
        ("图 24", "fig24_RFM气泡散点图.png", "RFM 气泡散点"),
        ("图 25", "fig25_订单转化漏斗.png", "订单转化漏斗"),
        ("图 26", "dashboard_preview.png", "Streamlit 大屏"),
    ]
    for row in chart_rows:
        cells = table.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(text)
            set_run_font(run, "宋体", 10.5)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"已生成: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
