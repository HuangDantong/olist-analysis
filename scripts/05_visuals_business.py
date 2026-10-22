# -*- coding: utf-8 -*-
"""
05_visuals_business.py —— 真实业务图表（8 张）

图表清单
--------
fig16 月度 GMV 与 6 个月预测（含 95% 置信区间）
fig17 RFM 八分层的 GMV 贡献
fig18 同期群留存热力图 + 平均留存曲线
fig19 ABC / Pareto：前 15 单品 + 全量累计曲线
fig20 波士顿矩阵：品类份额 × 同比增长
fig21 2018 年 1–8 月 GMV 前 15 品类
fig22 配送延迟与评价：平均评分 + 差评占比
fig23 支付方式结构（100% 堆积）
fig24 RFM 气泡散点（R × F × M）
fig25 订单转化漏斗（下单 → 支付 → 发货 → 送达）

设计规范
--------
- 配色使用 dataviz 参考调色板（已通过 CVD / 对比度校验）；
- 单系列不画图例，多系列必有图例；
- 不使用双 y 轴；不同量纲拆成上下/左右分面；
- 细网格、细线、直接标注关键值；文字使用墨色而非系列色。

输出
----
outputs/figures/business/*.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, PercentFormatter

from viz_style import (
    AQUA, BASELINE, BLUE, BLUE_CMAP, BLUE_DARK, GRID, INK, MUTED,
    ORANGE, SECONDARY, SURFACE, YELLOW,
    brl_wan, setup_matplotlib, source_note, style_axes, title_block,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"
TABLES_DIR = ROOT / "outputs" / "tables"
FIG_DIR = ROOT / "outputs" / "figures" / "business"

RANDOM_SEED = 42


def load_data():
    orders = pd.read_csv(
        CLEAN_DIR / "orders_enriched.csv",
        parse_dates=["purchase_date"],
    )
    orders["purchase_month"] = pd.to_datetime(
        orders["purchase_month"] + "-01", errors="coerce"
    )
    return {
        "orders": orders,
        "payments": pd.read_csv(CLEAN_DIR / "payments.csv"),
        "rfm": pd.read_csv(TABLES_DIR / "rfm_segment_summary.csv"),
        "rfm_customers": pd.read_csv(TABLES_DIR / "rfm_customers.csv"),
        "cohort": pd.read_csv(TABLES_DIR / "cohort_retention.csv", index_col=0),
        "abc": pd.read_csv(TABLES_DIR / "abc_products.csv"),
        "boston": pd.read_csv(TABLES_DIR / "boston_matrix.csv"),
        "forecast": pd.read_csv(TABLES_DIR / "sarima_forecast.csv"),
    }


def save(fig, name: str) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / name
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print(f"  saved {path.name}")
    return path


# ---------------------------------------------------------------------------
# fig16 月度 GMV 与预测
# ---------------------------------------------------------------------------
def fig16_forecast(data):
    orders = data["orders"]
    valid = orders[orders["is_valid_order"] & orders["has_items"]].copy()
    monthly = valid.groupby("purchase_month")["gmv"].sum().sort_index()
    monthly = monthly.loc["2017-01-01":"2018-08-31"]

    fc = data["forecast"].copy()
    fc["month"] = pd.to_datetime(fc["month"] + "-01")
    ymax = max(float(monthly.max()), float(fc["upper_95"].max())) * 1.14

    fig, ax = plt.subplots(figsize=(11, 5.6))
    ax.fill_between(
        fc["month"], fc["lower_95"], fc["upper_95"],
        color=ORANGE, alpha=0.12, linewidth=0, label="95% 置信区间",
    )
    ax.plot(monthly.index, monthly.values, color=BLUE, lw=2.2, label="实际 GMV")
    ax.plot(fc["month"], fc["forecast"], color=ORANGE, lw=2.2, label="模型拟合 / 预测")

    # 实际值与预测值的端点
    ax.scatter(
        [monthly.index[-1]], [monthly.values[-1]], s=42, color=BLUE,
        edgecolor=SURFACE, linewidth=2, zorder=5,
    )
    ax.scatter(
        [fc["month"].iloc[-1]], [fc["forecast"].iloc[-1]], s=42, color=ORANGE,
        edgecolor=SURFACE, linewidth=2, zorder=5,
    )

    ax.axvline(pd.Timestamp("2018-08-01"), color=BASELINE, lw=1)
    ax.text(
        pd.Timestamp("2018-08-12"), ymax * 0.96, "预测起点",
        color=MUTED, fontsize=8.5, va="top",
    )

    # 2020 年前后大促高点（2017-11）
    peak_month = monthly.idxmax()
    peak_value = monthly.max()
    ax.annotate(
        "2017-11 黑五",
        xy=(peak_month, peak_value),
        xytext=(peak_month - pd.Timedelta(days=110), peak_value * 0.90),
        fontsize=8.5, color=SECONDARY,
        arrowprops=dict(arrowstyle="-", color=BASELINE, lw=1),
    )

    # 仅直接标注预测端点；实际端点由坐标轴承担，避免与预测线重叠
    ax.text(
        fc["month"].iloc[-1], fc["forecast"].iloc[-1] * 1.035,
        f"R${fc['forecast'].iloc[-1] / 1e4:.0f}万", ha="right", fontsize=8.5, color=ORANGE,
    )

    ax.set_ylim(0, ymax)
    ax.yaxis.set_major_formatter(FuncFormatter(brl_wan))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.tick_params(axis="x", rotation=45)
    ax.set_ylabel("月度 GMV")
    title_block(
        ax,
        "月度 GMV：2018 年下半年预测",
        "实际值 2017-01～2018-08；未来 6 个月预测均值约 R$86 万/月；回测 MAPE 5.59%",
    )
    handles = [
        Line2D([0], [0], color=BLUE, lw=2.2, label="实际 GMV"),
        Line2D([0], [0], color=ORANGE, lw=2.2, label="模型拟合 / 预测"),
        Patch(facecolor=ORANGE, alpha=0.15, label="95% 置信区间"),
    ]
    ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=9, ncol=3)
    style_axes(ax, grid_axis="y")
    source_note(
        fig,
        "数据：Olist 2016-09～2018-10，有效订单；模型：ARIMA(1,1,1)，"
        "在 8 个候选模型/基准中按回测 RMSE 选择。",
    )
    return save(fig, "fig16_月度GMV与预测.png")


# ---------------------------------------------------------------------------
# fig17 RFM 分层贡献
# ---------------------------------------------------------------------------
def fig17_rfm(data):
    df = data["rfm"].sort_values("monetary_share", ascending=True).copy()
    values = df["monetary_share"].to_numpy() * 100
    colors = [BLUE_DARK if i >= len(df) - 2 else BLUE for i in range(len(df))]

    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.barh(df["segment"], values, color=colors, height=0.62)
    for i, (value, customers) in enumerate(zip(values, df["customers"])):
        ax.text(
            value + 0.5, i, f"{value:.1f}%  ({customers:,} 人)",
            va="center", fontsize=8.5, color=SECONDARY,
        )
    ax.set_xlim(0, values.max() * 1.42)
    ax.xaxis.set_major_formatter(PercentFormatter())
    ax.set_xlabel("GMV 贡献占比")
    title_block(
        ax,
        "RFM 八分层：谁贡献了 GMV",
        "共 94,983 位客户；R / M 用中位数切分，F ≥ 2 视为复购客户",
    )
    style_axes(ax, grid_axis="x")
    source_note(fig, "数据：Olist 有效订单（非取消/不可用且有商品明细）；口径见 docs/models_report.md。")
    return save(fig, "fig17_RFM分层贡献.png")


# ---------------------------------------------------------------------------
# fig24 RFM 气泡散点
# ---------------------------------------------------------------------------
def _money_log(value: float, _pos=None) -> str:
    if value >= 1e4:
        return f"R${value / 1e4:.0f}万"
    if value >= 1e3:
        return f"R${value / 1e3:.0f}K"
    return f"R${value:.0f}"


def fig24_rfm_bubble(data):
    rfm = data["rfm_customers"].copy()
    sample = rfm.sample(n=min(8000, len(rfm)), random_state=RANDOM_SEED)
    one_time = sample[sample["frequency"] <= 1]
    repeat = sample[sample["frequency"] >= 2]

    def bubble_size(values):
        return 10 + np.minimum(values, 10) * 12

    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    ax.scatter(
        one_time["recency"], one_time["monetary"].clip(lower=1),
        s=bubble_size(one_time["frequency"]), color=BLUE, alpha=0.20,
        edgecolor="none", label="一次性客户（F=1）",
    )
    ax.scatter(
        repeat["recency"], repeat["monetary"].clip(lower=1),
        s=bubble_size(repeat["frequency"]), color=ORANGE, alpha=0.75,
        edgecolor=SURFACE, linewidth=1.0, label="复购客户（F≥2）",
    )

    r_median = float(rfm["recency"].median())
    m_median = float(rfm["monetary"].median())
    ax.axvline(r_median, color=MUTED, lw=1)
    ax.axhline(m_median, color=MUTED, lw=1)

    for x, y, text, ha, va in [
        (0.02, 0.96, "高价值活跃\nR 低 / M 高", "left", "top"),
        (0.98, 0.96, "高价值流失风险\nR 高 / M 高", "right", "top"),
        (0.02, 0.04, "新客 / 低客单\nR 低 / M 低", "left", "bottom"),
        (0.98, 0.04, "沉睡低价值\nR 高 / M 低", "right", "bottom"),
    ]:
        ax.text(
            x, y, text, transform=ax.transAxes, ha=ha, va=va,
            fontsize=8.5, color=MUTED,
        )

    ax.set_yscale("log")
    ax.set_xlim(0, float(rfm["recency"].max()) * 1.02)
    ax.set_ylim(
        max(1.0, float(rfm["monetary"].min()) * 0.8),
        float(rfm["monetary"].max()) * 1.6,
    )
    ax.yaxis.set_major_formatter(FuncFormatter(_money_log))
    ax.set_xlabel("最近一次购买距今天数（R）")
    ax.set_ylabel("GMV（对数刻度）")
    title_block(
        ax,
        "RFM 气泡散点：R × M（气泡 = F）",
        "抽样 8,000 位客户；纵轴 GMV 为对数刻度；橙色为复购客户（F≥2）；气泡大小 = 订单数",
    )
    ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=2,
        frameon=True, facecolor=SURFACE, framealpha=0.92,
        edgecolor=GRID, fontsize=8.5,
    )
    style_axes(ax, grid_axis="both")
    source_note(fig, "数据：Olist 有效订单；R = 距快照日天数，M = GMV，F = 订单数（以气泡大小编码）。")
    return save(fig, "fig24_RFM气泡散点图.png")


# ---------------------------------------------------------------------------
# fig25 订单转化漏斗
# ---------------------------------------------------------------------------
def fig25_funnel(data):
    orders = data["orders"]
    stages = [
        ("下单", len(orders)),
        ("支付通过", int(orders["order_approved_at"].notna().sum())),
        ("发货", int(orders["order_delivered_carrier_date"].notna().sum())),
        ("送达", int(orders["order_delivered_customer_date"].notna().sum())),
    ]
    df = pd.DataFrame(stages, columns=["stage", "count"])
    df["pct_total"] = df["count"] / df["count"].iloc[0] * 100
    df["pct_prev"] = df["count"] / df["count"].shift(1) * 100
    df.to_csv(TABLES_DIR / "funnel.csv", index=False, encoding="utf-8-sig")

    y = np.arange(len(df))
    widths = df["count"].to_numpy()
    colors = ["#184f95", "#2a78d6", "#5598e7", "#86b6ef"]

    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    ax.barh(
        y, widths, left=-widths / 2, height=0.62,
        color=colors, edgecolor=SURFACE, linewidth=1.5,
    )
    for i, row in df.iterrows():
        ax.text(
            widths[i] / 2 + widths.max() * 0.025, i,
            f"{row['count']:,}  ({row['pct_total']:.1f}%)",
            va="center", fontsize=9, color=SECONDARY,
        )
        if i > 0:
            ax.text(
                -widths.max() * 0.66, i - 0.5, f"↓ {row['pct_prev']:.1f}%",
                va="center", ha="right", fontsize=8, color=MUTED,
            )

    ax.set_yticks(y)
    ax.set_yticklabels(df["stage"], fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(-widths.max() * 0.72, widths.max() * 0.78)
    ax.set_xticks([])
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="y", length=0)

    fig.suptitle(
        "订单转化漏斗：从下单到送达",
        x=0.012, y=0.975, ha="left", va="top",
        fontsize=14, fontweight="bold", color=INK,
    )
    fig.text(
        0.012, 0.905,
        f"总体送达率 {df['pct_total'].iloc[-1]:.1f}%\n"
        f"支付通过率 {df['pct_prev'].iloc[1]:.1f}%，发货率 {df['pct_prev'].iloc[2]:.1f}%，"
        f"送达率 {df['pct_prev'].iloc[3]:.1f}%",
        fontsize=9, color=SECONDARY, ha="left", va="top",
    )
    fig.subplots_adjust(top=0.76, bottom=0.08)
    source_note(fig, "数据：Olist 订单表；各阶段按对应时间字段是否非空统计；单位：订单数。")
    return save(fig, "fig25_订单转化漏斗.png")


# ---------------------------------------------------------------------------
# fig18 同期群留存
# ---------------------------------------------------------------------------
def fig18_cohort(data):
    cohort = data["cohort"]
    cohort = cohort[cohort["cohort_size"] >= 30].copy()
    cols = [f"M{i}" for i in range(1, 13) if f"M{i}" in cohort.columns]
    matrix = cohort[cols].astype(float).to_numpy()
    labels = [f"M{i}" for i in range(1, len(cols) + 1)]

    fig = plt.figure(figsize=(12, 6.4))
    gs = fig.add_gridspec(1, 2, width_ratios=[5.2, 1.15], wspace=0.28)
    ax = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    im = ax.imshow(matrix, aspect="auto", cmap=BLUE_CMAP, vmin=0, vmax=0.012)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_yticks(range(len(cohort)))
    ax.set_yticklabels(cohort.index, fontsize=8)
    ax.set_xlabel("首购后月数")
    ax.set_ylabel("首购月份同期群")
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # 仅标注 M1 / M3，避免热力图被文字淹没
    for r in range(matrix.shape[0]):
        for c in [0, 2]:
            value = matrix[r, c]
            if np.isfinite(value):
                ax.text(
                    c, r, f"{value * 100:.1f}",
                    ha="center", va="center", fontsize=6.5,
                    color="white" if value > 0.0068 else INK,
                )

    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02, format=PercentFormatter(1.0))
    cbar.ax.tick_params(labelsize=7, colors=MUTED)
    cbar.set_label("留存率", color=SECONDARY, fontsize=8)

    avg = np.nanmean(matrix, axis=0)
    ax2.plot(range(len(cols)), avg, color=BLUE, lw=2, marker="o", markersize=4.5)
    ax2.set_xticks([0, 2, 5, len(cols) - 1])
    ax2.set_xticklabels([labels[0], labels[2], labels[5], labels[-1]], fontsize=8)
    ax2.set_ylim(0, 0.008)
    ax2.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=1))
    ax2.set_title("平均留存", loc="left", fontsize=10, color=INK, pad=8)
    ax2.set_xlabel("首购后月数")
    style_axes(ax2, grid_axis="y")

    fig.suptitle(
        "同期群留存：首购后第 N 月仍复购的客户占比",
        x=0.012, y=0.985, ha="left", fontsize=14, fontweight="bold", color=INK,
    )
    fig.text(
        0.012, 0.928,
        "仅统计 cohort_size ≥ 30 的同期群；M0 恒为 100%，未展示；格内标注 M1 / M3 留存率（%）",
        fontsize=9, color=SECONDARY, ha="left",
    )
    fig.subplots_adjust(top=0.83, bottom=0.13)
    source_note(fig, "数据：Olist 有效订单；留存率 = 第 N 月仍有购买的去重客户数 / 同期群初始客户数。")
    return save(fig, "fig18_同期群留存热力图.png")


# ---------------------------------------------------------------------------
# fig19 ABC / Pareto
# ---------------------------------------------------------------------------
def fig19_pareto(data):
    products = data["abc"].sort_values("gmv", ascending=False).reset_index(drop=True)
    top = products.head(15).copy()

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11, 7.6),
        gridspec_kw={"height_ratios": [2.5, 1.7], "hspace": 0.38},
    )

    x = np.arange(1, len(top) + 1)
    ax1.bar(x, top["gmv"], color=BLUE, width=0.66)
    for i, (_, row) in enumerate(top.head(3).iterrows()):
        ax1.text(
            i + 1, row["gmv"] * 1.03, f"R${row['gmv'] / 1e4:.0f}万",
            ha="center", fontsize=8, color=SECONDARY,
        )
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(i) for i in x], fontsize=8)
    ax1.set_xlabel("商品排名")
    ax1.yaxis.set_major_formatter(FuncFormatter(brl_wan))
    ax1.set_ylabel("单品 GMV")
    title_block(
        ax1,
        "ABC / Pareto：8,478 个 A 类商品贡献 80% GMV",
        "上：GMV 前 15 的单品；下：全部 32,729 个商品的累计 GMV 曲线（对数横轴）",
    )
    style_axes(ax1, grid_axis="y")

    ranks = np.arange(1, len(products) + 1)
    cum = products["cum_gmv_share"].to_numpy() * 100
    ax2.plot(ranks, cum, color=ORANGE, lw=2)
    ax2.set_xscale("log")
    ax2.set_xlim(1, len(products))
    ax2.set_ylim(0, 102)
    ax2.axhline(80, color=MUTED, lw=1)
    ax2.axhline(95, color=MUTED, lw=1)

    # 与 ABC 汇总表保持同一口径：A 类商品数 / A+B 类商品数
    a_rank = int((products["abc_class"] == "A").sum())
    b_rank = int(products["abc_class"].isin(["A", "B"]).sum())
    ax2.annotate(
        f"80% @ {a_rank:,} 个商品",
        xy=(a_rank, 80), xytext=(a_rank * 0.12, 88),
        fontsize=8, color=SECONDARY,
        arrowprops=dict(arrowstyle="-", color=BASELINE, lw=1),
    )
    ax2.annotate(
        f"95% @ {b_rank:,} 个商品",
        xy=(b_rank, 95), xytext=(b_rank * 0.16, 101),
        fontsize=8, color=SECONDARY,
        arrowprops=dict(arrowstyle="-", color=BASELINE, lw=1),
    )
    ax2.set_xticks([1, 10, 100, 1000, 10000])
    ax2.set_xticklabels(["1", "10", "100", "1,000", "10,000"])
    ax2.yaxis.set_major_formatter(PercentFormatter())
    ax2.set_xlabel("商品排名（按 GMV 降序，对数刻度）")
    ax2.set_ylabel("累计 GMV 占比")
    style_axes(ax2, grid_axis="y")
    source_note(fig, "数据：Olist 有效订单商品金额；A/B/C 边界为累计 GMV 80% / 95%。")
    return save(fig, "fig19_ABC帕累托图.png")


# ---------------------------------------------------------------------------
# fig20 波士顿矩阵
# ---------------------------------------------------------------------------
def fig20_boston(data):
    df = data["boston"]
    eligible = df[df["quadrant"] != "未纳入"].dropna(subset=["growth", "share_2018"]).copy()
    share_med = float(eligible["share_2018"].median())
    growth_med = float(eligible["growth"].median())

    size = 28 + (eligible["gmv_2018"] / eligible["gmv_2018"].max()) * 620
    fig, ax = plt.subplots(figsize=(11, 6.6))
    ax.scatter(
        eligible["share_2018"], eligible["growth"],
        s=size, color=BLUE, alpha=0.78, edgecolor=SURFACE, linewidth=1.6,
    )
    ax.axvline(share_med, color=MUTED, lw=1)
    ax.axhline(growth_med, color=MUTED, lw=1)

    ax.set_xscale("log")
    ax.set_yscale("symlog", linthresh=0.5, linscale=0.9)
    ax.set_xlim(eligible["share_2018"].min() * 0.75, eligible["share_2018"].max() * 1.45)
    ax.set_ylim(-0.8, 320)
    ax.set_yticks([-0.75, -0.5, 0, 0.5, 1, 2, 5, 10, 50, 100])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value * 100:.0f}%"))
    ax.set_xticks([0.0001, 0.001, 0.01, 0.1])
    ax.set_xticklabels(["0.01%", "0.1%", "1%", "10%"])

    # 头部品类彼此靠得很近，减少标签数量并用引线，避免文字叠在一起
    label_offsets = {
        "health_beauty": (-16, 22),
        "watches_gifts": (16, 26),
        "bed_bath_table": (-18, -34),
        "sports_leisure": (18, -24),
        "computers_accessories": (18, 10),
    }
    for _, row in eligible.nlargest(5, "gmv_2018").iterrows():
        category = row["product_category_name_english"]
        ax.annotate(
            category.replace("_", " "),
            xy=(row["share_2018"], row["growth"]),
            xytext=label_offsets.get(category, (8, 8)),
            textcoords="offset points", fontsize=8, color=INK,
            arrowprops=dict(arrowstyle="-", color=BASELINE, lw=0.7),
        )

    for x, y, text, ha, va in [
        (0.015, 0.965, "问题\n低份额 / 高增长", "left", "top"),
        (0.985, 0.965, "明星\n高份额 / 高增长", "right", "top"),
        (0.015, 0.035, "瘦狗\n低份额 / 低增长", "left", "bottom"),
        (0.985, 0.035, "现金牛\n高份额 / 低增长", "right", "bottom"),
    ]:
        ax.text(
            x, y, text, transform=ax.transAxes, ha=ha, va=va,
            fontsize=9, color=MUTED, alpha=0.9,
        )

    ax.set_xlabel("2018 年 1–8 月 GMV 份额（对数刻度）")
    ax.set_ylabel("同比增长率（symlog 刻度）")
    title_block(
        ax,
        "波士顿矩阵：明星、现金牛、问题与瘦狗",
        "63 个品类；气泡大小 = 2018 年 GMV；参考线为份额中位数 0.49% 与增长率中位数 188%",
    )
    style_axes(ax, grid_axis="both")
    source_note(
        fig,
        "数据：Olist 2017 年 1–8 月 vs 2018 年 1–8 月；仅纳入 2017 年有销售且 2018 GMV ≥ R$1,000 的品类。",
    )
    return save(fig, "fig20_波士顿矩阵.png")


# ---------------------------------------------------------------------------
# fig21 品类 GMV 前 15
# ---------------------------------------------------------------------------
def fig21_top_categories(data):
    df = (
        data["boston"].nlargest(15, "gmv_2018")
        .sort_values("gmv_2018", ascending=True)
        .copy()
    )
    df["label"] = df["product_category_name_english"].str.replace("_", " ", regex=False)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(df["label"], df["gmv_2018"], color=BLUE, height=0.62)
    for i, (_, row) in enumerate(df.iterrows()):
        ax.text(
            row["gmv_2018"] * 1.01, i, f"R${row['gmv_2018'] / 1e4:.0f}万",
            va="center", fontsize=8.5, color=SECONDARY,
        )
    ax.set_xlim(0, df["gmv_2018"].max() * 1.22)
    ax.xaxis.set_major_formatter(FuncFormatter(brl_wan))
    ax.set_xlabel("2018 年 1–8 月 GMV")
    title_block(
        ax,
        "2018 年 1–8 月 GMV 前 15 品类",
        "health & beauty、watches & gifts、bed & bath 位列前三",
    )
    style_axes(ax, grid_axis="x")
    source_note(fig, "数据：Olist 有效订单；品类名来自官方英文翻译表。")
    return save(fig, "fig21_品类GMV前15.png")


# ---------------------------------------------------------------------------
# fig22 配送延迟与评价
# ---------------------------------------------------------------------------
def fig22_delivery_reviews(data):
    orders = data["orders"]
    delivered = orders[
        (orders["order_status"] == "delivered") & orders["review_score"].notna()
    ].copy()
    bins = [-0.1, 0, 3, 7, 14, 999]
    labels = ["准时/提前", "1–3 天", "4–7 天", "8–14 天", "15 天以上"]
    delivered["delay_bucket"] = pd.cut(delivered["late_days"], bins=bins, labels=labels)
    grouped = (
        delivered.groupby("delay_bucket", observed=False)
        .agg(
            n=("order_id", "size"),
            score=("review_score", "mean"),
            low_share=("review_score", lambda s: float((s <= 2).mean() * 100)),
        )
        .reset_index()
    )

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.0), sharey=True)
    y = np.arange(len(grouped))
    ax1.barh(y, grouped["score"], color=BLUE, height=0.6)
    ax2.barh(y, grouped["low_share"], color=BLUE, height=0.6)
    for i, row in grouped.iterrows():
        ax1.text(
            row["score"] + 0.06, i, f"{row['score']:.2f}",
            va="center", fontsize=8.5, color=SECONDARY,
        )
        ax2.text(
            row["low_share"] + 1.2, i, f"{row['low_share']:.1f}%",
            va="center", fontsize=8.5, color=SECONDARY,
        )
    ax1.set_yticks(y)
    ax1.set_yticklabels([
        f"{row['delay_bucket']}\n(n={row['n']:,})" for _, row in grouped.iterrows()
    ], fontsize=8.5)
    ax1.invert_yaxis()
    ax1.set_xlim(0, 5)
    ax2.set_xlim(0, 100)
    ax2.xaxis.set_major_formatter(PercentFormatter())
    ax1.set_title("平均评分（1–5）", loc="left", fontsize=10, color=INK, pad=8)
    ax2.set_title("1–2 星差评占比", loc="left", fontsize=10, color=INK, pad=8)
    ax1.set_xlabel("平均评分")
    ax2.set_xlabel("差评占比")

    fig.suptitle(
        "配送延迟与评价：延迟 4 天以上评分断崖式下降",
        x=0.012, y=0.98, ha="left", fontsize=14, fontweight="bold", color=INK,
    )
    fig.text(
        0.012, 0.905,
        "仅统计已送达且有评价的订单（N=95,832）；延迟天数 = 实际送达 − 承诺送达",
        fontsize=9, color=SECONDARY, ha="left",
    )
    fig.subplots_adjust(top=0.78, wspace=0.18)
    style_axes(ax1, grid_axis="x")
    style_axes(ax2, grid_axis="x")
    source_note(fig, "数据：Olist 订单、物流与评价表。")
    return save(fig, "fig22_配送延迟与评价.png")


# ---------------------------------------------------------------------------
# fig23 支付方式结构
# ---------------------------------------------------------------------------
def fig23_payment_mix(data):
    orders = data["orders"][["order_id", "purchase_month"]]
    payments = data["payments"].merge(orders, on="order_id", how="left")
    payments = payments[
        (payments["purchase_month"] >= "2017-01")
        & (payments["purchase_month"] <= "2018-08")
    ]
    keep = ["credit_card", "boleto", "voucher", "debit_card"]
    names = {"credit_card": "信用卡", "boleto": "Boleto 票据",
             "voucher": "代金券", "debit_card": "借记卡"}
    pivot = (
        payments.groupby(["purchase_month", "payment_type"])["payment_value"]
        .sum().unstack(fill_value=0)
        .reindex(columns=keep, fill_value=0)
    )
    pivot = pivot.div(pivot.sum(axis=1), axis=0) * 100
    months = pd.to_datetime(pivot.index)

    fig, ax = plt.subplots(figsize=(11, 5.4))
    bottom = np.zeros(len(pivot))
    colors = [BLUE, ORANGE, AQUA, YELLOW]
    for col, color in zip(keep, colors):
        values = pivot[col].to_numpy()
        ax.bar(
            months, values, bottom=bottom, width=20,
            color=color, edgecolor=SURFACE, linewidth=1.5, label=names[col],
        )
        bottom += values

    # 最后一个月直接标注占比（>= 5% 才标）
    for col, color in zip(keep, colors):
        value = float(pivot[col].iloc[-1])
        if value >= 5:
            before = float(pivot[keep[:keep.index(col)]].iloc[-1].sum()) if keep.index(col) else 0
            ax.text(
                months[-1], before + value / 2, f"{value:.0f}%",
                ha="center", va="center", fontsize=9,
                color="white" if color in (BLUE, ORANGE) else INK,
            )

    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(PercentFormatter())
    ax.set_ylabel("支付金额占比")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.tick_params(axis="x", rotation=45)
    fig.suptitle(
        "支付方式结构：信用卡约占四分之三",
        x=0.012, y=0.975, ha="left", va="top",
        fontsize=14, fontweight="bold", color=INK,
    )
    fig.text(
        0.012, 0.938,
        "按支付金额占比；2017-01～2018-08；Boleto 是巴西常用的银行票据支付方式",
        fontsize=9, color=SECONDARY, ha="left", va="top",
    )
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(
        handles, labels, loc="upper left", bbox_to_anchor=(0.012, 0.905),
        ncol=4, frameon=False, fontsize=9,
    )
    fig.subplots_adjust(top=0.79, bottom=0.20)
    style_axes(ax, grid_axis="y")
    source_note(fig, "数据：Olist 支付表；仅保留四种主要支付方式，not_defined 占比不足 0.1% 未展示。")
    return save(fig, "fig23_支付方式结构.png")


def main() -> int:
    np.random.seed(RANDOM_SEED)
    setup_matplotlib()
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 64)
    print("05_visuals_business.py —— 真实业务图表")
    print("=" * 64)
    print("读取数据 ...")
    data = load_data()
    print(f"  订单: {len(data['orders']):,}")

    print("绘制 10 张业务图 ...")
    outputs = [
        fig16_forecast(data),
        fig17_rfm(data),
        fig18_cohort(data),
        fig19_pareto(data),
        fig20_boston(data),
        fig21_top_categories(data),
        fig22_delivery_reviews(data),
        fig23_payment_mix(data),
        fig24_rfm_bubble(data),
        fig25_funnel(data),
    ]

    print("\n" + "-" * 64)
    print(f"完成: {len(outputs)} 张图 | 输出目录: {FIG_DIR}")
    for path in outputs:
        print(f"  {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
