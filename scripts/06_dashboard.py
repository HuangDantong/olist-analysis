# -*- coding: utf-8 -*-
"""
06_dashboard.py —— Streamlit 交互式商业分析大屏

运行
----
    streamlit run scripts/06_dashboard.py

功能
----
- 侧边栏筛选：日期范围、州、品类、订单状态、是否只看有效订单；
- KPI 行：GMV、订单数、客户数、客单价、延迟送达率；
- 经营总览：月度 GMV 趋势（含 3 月移动平均）、品类 Top 10、州 Top 10；
- 客户与留存：RFM 分层、同期群留存热力图、配送延迟与评分；
- 品类与预测：波士顿矩阵、GMV 预测与 95% 置信区间、支付方式结构；
- 数据明细：筛选结果表格与 CSV 下载。

说明
----
RFM、同期群、波士顿矩阵、SARIMA 预测是离线模型结果，展示全量口径，
不受侧边栏筛选影响；经营总览、配送、支付和明细表会随筛选联动。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from viz_style import (  # noqa: E402
    BASELINE, BLUE, BLUE_DARK, CATEGORICAL, GRID, INK, MUTED,
    ORANGE, SEQUENTIAL_BLUE, SURFACE, plotly_layout,
)

ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"
TABLES_DIR = ROOT / "outputs" / "tables"

BLUE_SCALE = [
    [i / (len(SEQUENTIAL_BLUE) - 1), color]
    for i, color in enumerate(SEQUENTIAL_BLUE)
]

st.set_page_config(
    page_title="Olist 商业分析大屏",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_data():
    orders = pd.read_csv(
        CLEAN_DIR / "orders_enriched.csv",
        parse_dates=["purchase_date"],
    )
    orders["purchase_month"] = pd.to_datetime(
        orders["purchase_month"] + "-01", errors="coerce"
    )
    items = pd.read_csv(CLEAN_DIR / "order_items.csv")
    payments = pd.read_csv(CLEAN_DIR / "payments.csv")
    rfm = pd.read_csv(TABLES_DIR / "rfm_segment_summary.csv")
    cohort = pd.read_csv(TABLES_DIR / "cohort_retention.csv", index_col=0)
    boston = pd.read_csv(TABLES_DIR / "boston_matrix.csv")
    forecast = pd.read_csv(TABLES_DIR / "sarima_forecast.csv")
    return orders, items, payments, rfm, cohort, boston, forecast


def brl(value: float) -> str:
    if abs(value) >= 1e8:
        return f"R$ {value / 1e8:,.1f} 亿"
    if abs(value) >= 1e4:
        return f"R$ {value / 1e4:,.0f} 万"
    return f"R$ {value:,.0f}"


def filter_data(orders, items, start, end, states, categories, statuses, valid_only):
    mask = (
        (orders["purchase_date"] >= pd.Timestamp(start))
        & (orders["purchase_date"] <= pd.Timestamp(end))
    )
    if states and "全部" not in states:
        mask &= orders["customer_state"].isin(states)
    if statuses and "全部" not in statuses:
        mask &= orders["order_status"].isin(statuses)
    if valid_only:
        mask &= orders["is_valid_order"] & orders["has_items"]

    filtered_orders = orders[mask].copy()
    filtered_items = items[items["order_id"].isin(filtered_orders["order_id"])].copy()

    if categories and "全部" not in categories:
        filtered_items = filtered_items[
            filtered_items["product_category_name_english"].isin(categories)
        ]
        filtered_orders = filtered_orders[
            filtered_orders["order_id"].isin(filtered_items["order_id"])
        ]
    return filtered_orders, filtered_items


def kpi_row(orders, items):
    gmv = float(items["price"].sum())
    order_count = int(orders["order_id"].nunique())
    customers = int(orders["customer_unique_id"].nunique())
    aov = gmv / order_count if order_count else 0.0
    delivered = orders[orders["order_status"] == "delivered"]
    late_rate = float(delivered["is_late"].fillna(False).mean()) if len(delivered) else 0.0

    cols = st.columns(5)
    cols[0].metric("GMV", brl(gmv))
    cols[1].metric("订单数", f"{order_count:,}")
    cols[2].metric("客户数", f"{customers:,}")
    cols[3].metric("客单价", f"R$ {aov:,.0f}")
    cols[4].metric("延迟送达率", f"{late_rate:.1%}")


def fig_monthly(orders, items):
    merged = items.merge(
        orders[["order_id", "purchase_month"]], on="order_id", how="left"
    )
    monthly = (
        merged.groupby("purchase_month")["price"].sum().sort_index()
    )
    if monthly.empty:
        return None

    # 2018-09 以后为数据收尾期，订单极少；趋势图截至 2018-08，避免尾部断崖
    cutoff = pd.Timestamp("2018-08-01")
    if monthly.index.max() > cutoff and (monthly.index <= cutoff).sum() >= 3:
        monthly = monthly.loc[:cutoff]

    ma = monthly.rolling(3, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly.index, y=monthly.values, mode="lines",
        name="月度 GMV", line=dict(color=BLUE, width=2.2),
        hovertemplate="%{x|%Y-%m}<br>GMV R$%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=ma.index, y=ma.values, mode="lines",
        name="3 月移动平均", line=dict(color=ORANGE, width=2),
        hovertemplate="%{x|%Y-%m}<br>3 月均值 R$%{y:,.0f}<extra></extra>",
    ))
    plotly_layout(fig, "月度 GMV 趋势", height=330)
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(tickprefix="R$", tickformat="~s")
    return fig


def fig_category(orders, items, top_n=10):
    merged = items.merge(
        orders[["order_id", "purchase_month"]], on="order_id", how="left"
    )
    grouped = (
        merged.groupby("product_category_name_english")["price"].sum()
        .nlargest(top_n).sort_values()
    )
    if grouped.empty:
        return None
    labels = [c.replace("_", " ") for c in grouped.index]
    fig = go.Figure(go.Bar(
        x=grouped.values, y=labels, orientation="h",
        marker_color=BLUE, width=0.62,
        text=[brl(v) for v in grouped.values], textposition="outside",
        textfont=dict(size=10),
        hovertemplate="%{y}<br>GMV R$%{x:,.0f}<extra></extra>",
    ))
    plotly_layout(fig, f"品类 GMV Top {top_n}", height=340)
    fig.update_xaxes(tickprefix="R$", tickformat="~s", range=[0, grouped.max() * 1.22])
    fig.update_layout(margin=dict(r=175))
    return fig


def fig_state(orders, items, top_n=10):
    merged = items.merge(
        orders[["order_id", "customer_state"]], on="order_id", how="left"
    )
    grouped = (
        merged.groupby("customer_state")["price"].sum()
        .nlargest(top_n).sort_values()
    )
    if grouped.empty:
        return None
    fig = go.Figure(go.Bar(
        x=grouped.values, y=grouped.index, orientation="h",
        marker_color=BLUE, width=0.62,
        text=[brl(v) for v in grouped.values], textposition="outside",
        textfont=dict(size=10),
        hovertemplate="%{y}<br>GMV R$%{x:,.0f}<extra></extra>",
    ))
    plotly_layout(fig, f"州 GMV Top {top_n}", height=340)
    fig.update_xaxes(tickprefix="R$", tickformat="~s", range=[0, grouped.max() * 1.22])
    fig.update_layout(margin=dict(r=175))
    return fig


def fig_rfm(rfm):
    df = rfm.sort_values("monetary_share", ascending=True).copy()
    colors = [BLUE_DARK if i >= len(df) - 2 else BLUE for i in range(len(df))]
    fig = go.Figure(go.Bar(
        x=df["monetary_share"] * 100, y=df["segment"], orientation="h",
        marker_color=colors, width=0.62,
        text=[f"{v:.1f}%" for v in df["monetary_share"] * 100],
        textposition="outside", textfont=dict(size=10),
        customdata=df["customers"],
        hovertemplate="%{y}<br>GMV 占比 %{x:.1f}%<br>客户数 %{customdata:,}<extra></extra>",
    ))
    plotly_layout(fig, "RFM 八分层：GMV 贡献（全量客户）", height=380)
    fig.update_xaxes(ticksuffix="%", range=[0, float(df["monetary_share"].max() * 100) * 1.22])
    fig.update_layout(margin=dict(r=40))
    return fig


def fig_cohort(cohort):
    cohort = cohort[cohort["cohort_size"] >= 30].copy()
    cols = [f"M{i}" for i in range(1, 13) if f"M{i}" in cohort.columns]
    z = cohort[cols].astype(float).to_numpy()
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"M{i}" for i in range(1, len(cols) + 1)], y=cohort.index,
        colorscale=BLUE_SCALE, zmin=0, zmax=0.012,
        colorbar=dict(title="留存率", tickformat=".1%"),
        hovertemplate="同期群 %{y}<br>%{x}<br>留存率 %{z:.2%}<extra></extra>",
    ))
    plotly_layout(fig, "同期群留存（全量口径，cohort_size ≥ 30）", height=420)
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    fig.update_yaxes(type="category", autorange="reversed", tickfont=dict(size=10))
    return fig


def fig_delivery(orders):
    delivered = orders[
        (orders["order_status"] == "delivered") & orders["review_score"].notna()
    ].copy()
    bins = [-0.1, 0, 3, 7, 14, 999]
    labels = ["准时/提前", "1–3 天", "4–7 天", "8–14 天", "15 天以上"]
    delivered["bucket"] = pd.cut(delivered["late_days"], bins=bins, labels=labels)
    grouped = (
        delivered.groupby("bucket", observed=False)
        .agg(
            n=("order_id", "size"),
            score=("review_score", "mean"),
            low=("review_score", lambda s: float((s <= 2).mean() * 100)),
        )
        .reset_index()
    )
    grouped["bucket"] = grouped["bucket"].astype(str)
    fig = go.Figure(go.Bar(
        x=grouped["bucket"], y=grouped["score"],
        marker_color=BLUE, width=0.6,
        text=[f"{v:.2f}" for v in grouped["score"]], textposition="outside",
        customdata=np.stack([grouped["n"], grouped["low"]], axis=-1),
        hovertemplate="%{x}<br>平均评分 %{y:.2f}<br>订单数 %{customdata[0]:,.0f}<br>差评占比 %{customdata[1]:.1f}%<extra></extra>",
    ))
    plotly_layout(fig, "配送延迟与平均评分", height=360)
    fig.update_yaxes(range=[0, 5], title="平均评分")
    fig.update_xaxes(title="")
    return fig


def fig_boston(boston):
    df = boston[boston["quadrant"] != "未纳入"].dropna(subset=["growth", "share_2018"]).copy()
    if df.empty:
        return None
    share_med = float(df["share_2018"].median())
    growth_med = float(df["growth"].median())

    # symlog 近似：sign(x) * log1p(|x|)，悬停显示真实增长率
    y = np.sign(df["growth"]) * np.log1p(np.abs(df["growth"]))
    tick_values = [-0.75, -0.5, 0, 0.5, 1, 2, 5, 10, 50, 100, 300]
    tick_pos = [np.sign(v) * np.log1p(abs(v)) for v in tick_values]

    size = 12 + (df["gmv_2018"] / df["gmv_2018"].max()) * 46

    fig = go.Figure(go.Scatter(
        x=df["share_2018"], y=y, mode="markers",
        marker=dict(size=size, color=BLUE, opacity=0.75,
                    line=dict(color=SURFACE, width=1.5)),
        customdata=np.stack([
            df["product_category_name_english"].str.replace("_", " ", regex=False),
            df["growth"], df["gmv_2018"],
        ], axis=-1),
        hovertemplate="%{customdata[0]}<br>份额 %{x:.2%}<br>增长 %{customdata[1]:.1%}<br>GMV R$%{customdata[2]:,.0f}<extra></extra>",
    ))
    fig.add_vline(x=share_med, line_color=BASELINE, line_width=1)
    fig.add_hline(y=np.log1p(growth_med), line_color=BASELINE, line_width=1)
    plotly_layout(fig, "波士顿矩阵（全量口径）", height=430)
    fig.update_layout(margin=dict(l=62, r=10, t=50, b=10))
    fig.update_xaxes(
        type="log", title="2018 年 1–8 月 GMV 份额（对数）",
        tickvals=[0.0001, 0.001, 0.01, 0.1],
        ticktext=["0.01%", "0.1%", "1%", "10%"],
    )
    fig.update_yaxes(
        title="同比增长率", title_standoff=8, tickvals=tick_pos,
        ticktext=[f"{v * 100:.0f}%" for v in tick_values],
    )
    return fig


def fig_forecast(forecast, orders):
    fc = forecast.copy()
    fc["month"] = pd.to_datetime(fc["month"] + "-01")
    valid = orders[orders["is_valid_order"] & orders["has_items"]].copy()
    actual_series = (
        valid.groupby("purchase_month")["gmv"].sum().sort_index()
    ).loc["2017-01-01":"2018-08-31"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=fc["month"], y=fc["upper_95"], mode="lines",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=fc["month"], y=fc["lower_95"], mode="lines",
        line=dict(width=0), fill="tonexty", fillcolor="rgba(235,104,52,0.12)",
        name="95% 置信区间", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=actual_series.index, y=actual_series.values, mode="lines",
        name="实际 GMV", line=dict(color=BLUE, width=2.2),
        hovertemplate="%{x|%Y-%m}<br>实际 R$%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=fc["month"], y=fc["forecast"], mode="lines",
        name="拟合 / 预测", line=dict(color=ORANGE, width=2.2),
        hovertemplate="%{x|%Y-%m}<br>预测 R$%{y:,.0f}<extra></extra>",
    ))
    fig.add_vline(x=pd.Timestamp("2018-08-01"), line_color=BASELINE, line_width=1)
    plotly_layout(fig, "月度 GMV 预测（全量口径）", height=400)
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(tickprefix="R$", tickformat="~s")
    return fig


def fig_payment(orders, payments):
    merged = payments.merge(orders[["order_id"]], on="order_id", how="inner")
    if merged.empty:
        return None
    names = {"credit_card": "信用卡", "boleto": "Boleto 票据",
             "voucher": "代金券", "debit_card": "借记卡"}
    grouped = (
        merged.groupby("payment_type")["payment_value"].sum()
        .reindex(["credit_card", "boleto", "voucher", "debit_card"])
        .fillna(0)
    )
    total = grouped.sum()
    shares = grouped / total * 100 if total else grouped * 0
    # 小占比切片不直接标字，交给图例，避免文字互相遮挡
    texts = [f"{v:.1f}%" if v >= 5 else "" for v in shares]
    fig = go.Figure(go.Pie(
        labels=[names.get(k, k) for k in grouped.index],
        values=grouped.values, hole=0.55,
        marker_colors=CATEGORICAL[:4],
        text=texts, textinfo="text", textposition="outside",
        hovertemplate="%{label}<br>支付金额 R$%{value:,.0f}<br>占比 %{percent}<extra></extra>",
    ))
    plotly_layout(fig, "支付方式结构", height=410)
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="top", y=-0.02,
            xanchor="center", x=0.5, font=dict(size=10, color=MUTED),
        ),
        margin=dict(l=8, r=8, t=56, b=50),
    )
    return fig


def main():
    orders, items, payments, rfm, cohort, boston, forecast = load_data()

    st.title("Olist 巴西电商商业分析大屏")
    st.caption(
        "数据：Brazilian E-Commerce Public Dataset by Olist（CC BY-NC-SA 4.0）｜"
        "2016-09～2018-10｜99,441 个订单"
    )

    with st.sidebar:
        st.header("筛选器")
        min_date = orders["purchase_date"].min().date()
        max_date = orders["purchase_date"].max().date()
        date_range = st.date_input(
            "日期范围", value=(min_date, max_date),
            min_value=min_date, max_value=max_date,
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start, end = date_range
        else:
            start = end = date_range

        state_options = ["全部"] + sorted(orders["customer_state"].dropna().unique())
        states = st.multiselect("州", state_options, default=["全部"])

        top_categories = (
            items.groupby("product_category_name_english")["price"].sum()
            .nlargest(20).index.tolist()
        )
        category_options = ["全部"] + top_categories
        categories = st.multiselect("品类（Top 20）", category_options, default=["全部"])

        status_options = ["全部"] + sorted(orders["order_status"].dropna().unique())
        statuses = st.multiselect("订单状态", status_options, default=["全部"])

        valid_only = st.checkbox("只看有效订单（非取消/不可用且有商品明细）", value=True)

        st.caption(
            "RFM、同期群、波士顿矩阵、SARIMA 预测为离线全量结果，"
            "不随筛选器变化；其余图表与明细表联动。"
        )

    filtered_orders, filtered_items = filter_data(
        orders, items, start, end, states, categories, statuses, valid_only
    )

    if filtered_orders.empty:
        st.warning("当前筛选条件下没有订单，请放宽筛选。")
        return

    st.caption(
        f"当前筛选：{start} ～ {end}｜订单 {len(filtered_orders):,}｜"
        f"商品明细 {len(filtered_items):,}"
    )
    kpi_row(filtered_orders, filtered_items)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["经营总览", "客户与留存", "品类与预测", "数据明细"]
    )

    with tab1:
        fig = fig_monthly(filtered_orders, filtered_items)
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
            st.caption("注：2018-09 以后为数据收尾期，趋势图截至 2018-08。")
        col1, col2 = st.columns(2)
        with col1:
            fig = fig_category(filtered_orders, filtered_items)
            if fig is not None:
                st.plotly_chart(fig, width="stretch")
        with col2:
            fig = fig_state(filtered_orders, filtered_items)
            if fig is not None:
                st.plotly_chart(fig, width="stretch")

    with tab2:
        col1, col2 = st.columns([1, 1.6])
        with col1:
            st.plotly_chart(fig_rfm(rfm), width="stretch")
        with col2:
            st.plotly_chart(fig_cohort(cohort), width="stretch")
        st.plotly_chart(fig_delivery(filtered_orders), width="stretch")

    with tab3:
        col1, col2 = st.columns([1.35, 1])
        with col1:
            fig = fig_boston(boston)
            if fig is not None:
                st.plotly_chart(fig, width="stretch")
                st.caption("悬停气泡查看品类名、GMV 份额与同比增长率。")
        with col2:
            fig = fig_payment(filtered_orders, payments)
            if fig is not None:
                st.plotly_chart(fig, width="stretch")
        st.plotly_chart(fig_forecast(forecast, orders), width="stretch")

    with tab4:
        table_cols = [
            "order_id", "purchase_date", "order_status", "customer_state",
            "gmv", "freight_total", "review_score", "payment_type_main",
            "purchase_month", "is_late",
        ]
        table = filtered_orders[table_cols].copy()
        table["purchase_date"] = table["purchase_date"].dt.strftime("%Y-%m-%d")
        table["purchase_month"] = table["purchase_month"].dt.strftime("%Y-%m")
        table["gmv"] = table["gmv"].round(2)
        table["freight_total"] = table["freight_total"].round(2)
        st.caption(f"共 {len(table):,} 行，页面展示前 5,000 行；下载按钮导出全部筛选结果。")
        st.dataframe(table.head(5000), width="stretch", hide_index=True)
        csv = table.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "下载筛选结果 CSV", csv, "olist_filtered_orders.csv", "text/csv"
        )

    st.divider()
    st.caption(
        "数据来源：Kaggle / Olist｜License: CC BY-NC-SA 4.0｜"
        "模型与图表代码见项目 README｜本页面仅用于课程作业与学术研究。"
    )


if __name__ == "__main__":
    main()
