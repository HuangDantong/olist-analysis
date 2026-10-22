# -*- coding: utf-8 -*-
"""
03_models.py —— 五个商业分析模型

模型清单
--------
1. RFM 客户分层（八分类 + 1–5 分）
2. 同期群（Cohort）留存
3. ABC / Pareto 商品分类
4. 波士顿矩阵（品类份额 × 同比增长）
5. SARIMA 月度 GMV 预测（含回测、95% 置信区间、MAPE/RMSE）

输入
----
data/clean/orders_enriched.csv
data/clean/order_items.csv

输出
----
outputs/tables/rfm_customers.csv
outputs/tables/rfm_segment_summary.csv
outputs/tables/cohort_retention.csv
outputs/tables/cohort_long.csv
outputs/tables/abc_products.csv
outputs/tables/abc_categories.csv
outputs/tables/abc_summary.csv
outputs/tables/boston_matrix.csv
outputs/tables/sarima_forecast.csv
outputs/tables/sarima_metrics.csv
outputs/tables/sarima_order.json
docs/models_report.md

用法
----
    python scripts/03_models.py
"""
from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"
OUT_DIR = ROOT / "outputs" / "tables"
REPORT_PATH = ROOT / "docs" / "models_report.md"

RANDOM_SEED = 42
SNAPSHOT_DAYS = 1

SEGMENT_MAP = {
    (True, True, True): "重要价值客户",
    (True, False, True): "重要发展客户",
    (False, True, True): "重要保持客户",
    (False, False, True): "重要挽留客户",
    (True, True, False): "一般价值客户",
    (True, False, False): "一般发展客户",
    (False, True, False): "一般保持客户",
    (False, False, False): "一般挽留客户",
}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    orders_path = CLEAN_DIR / "orders_enriched.csv"
    items_path = CLEAN_DIR / "order_items.csv"
    if not orders_path.is_file() or not items_path.is_file():
        raise SystemExit(
            "清洗后数据不存在，请先运行: python scripts/02_clean.py"
        )
    orders = pd.read_csv(
        orders_path,
        parse_dates=[
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    )
    orders["purchase_date"] = pd.to_datetime(orders["purchase_date"], errors="coerce")
    items = pd.read_csv(items_path)
    return orders, items


def valid_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """有效订单：非取消/非不可用，且有商品明细。"""
    return orders[orders["is_valid_order"] & orders["has_items"]].copy()


def safe_qcut(series: pd.Series, q: int = 5) -> pd.Series:
    """先 rank(method='first') 再 qcut，避免重复值导致分箱边界报错。"""
    ranks = series.rank(method="first")
    return pd.qcut(ranks, q=q, labels=False).astype(int) + 1


# ---------------------------------------------------------------------------
# 1. RFM
# ---------------------------------------------------------------------------
def compute_rfm(orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    valid = valid_orders(orders)
    snapshot = valid["purchase_date"].max() + pd.Timedelta(days=SNAPSHOT_DAYS)

    rfm = (
        valid.groupby("customer_unique_id", as_index=False)
        .agg(
            first_purchase=("purchase_date", "min"),
            last_purchase=("purchase_date", "max"),
            frequency=("order_id", "nunique"),
            monetary=("gmv", "sum"),
        )
    )
    rfm["recency"] = (snapshot - rfm["last_purchase"]).dt.days
    rfm["avg_order_value"] = rfm["monetary"] / rfm["frequency"]

    rfm["r_score"] = 6 - safe_qcut(rfm["recency"])   # 越近得分越高
    rfm["f_score"] = safe_qcut(rfm["frequency"])
    rfm["m_score"] = safe_qcut(rfm["monetary"])
    rfm["rfm_score"] = rfm["r_score"] * 100 + rfm["f_score"] * 10 + rfm["m_score"]

    r_median = float(rfm["recency"].median())
    m_median = float(rfm["monetary"].median())
    f_median = float(rfm["frequency"].median())
    # 中位数若为 1，说明一半以上客户只买过一次，此时用 F>=2 区分复购
    f_threshold = max(2.0, f_median)

    rfm["R_high"] = rfm["recency"] <= r_median
    rfm["F_high"] = rfm["frequency"] >= f_threshold
    rfm["M_high"] = rfm["monetary"] >= m_median
    rfm["segment"] = [
        SEGMENT_MAP[(bool(r), bool(f), bool(m))]
        for r, f, m in zip(rfm["R_high"], rfm["F_high"], rfm["M_high"])
    ]

    summary = (
        rfm.groupby("segment", as_index=False)
        .agg(
            customers=("customer_unique_id", "count"),
            monetary=("monetary", "sum"),
            avg_recency=("recency", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
        )
    )
    summary["customer_share"] = summary["customers"] / len(rfm)
    summary["monetary_share"] = summary["monetary"] / rfm["monetary"].sum()
    summary = summary.sort_values("monetary", ascending=False).reset_index(drop=True)

    thresholds = {
        "snapshot_date": snapshot.strftime("%Y-%m-%d"),
        "r_median_days": r_median,
        "f_median": f_median,
        "f_threshold": f_threshold,
        "m_median_brl": m_median,
        "customers": int(len(rfm)),
    }
    return rfm, summary, thresholds


# ---------------------------------------------------------------------------
# 2. 同期群留存
# ---------------------------------------------------------------------------
def compute_cohort(orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    valid = valid_orders(orders).copy()
    valid["purchase_month"] = pd.to_datetime(
        valid["purchase_month"] + "-01", errors="coerce"
    )

    first = valid.groupby("customer_unique_id")["purchase_month"].min()
    valid["cohort"] = valid["customer_unique_id"].map(first)
    valid["cohort_index"] = (
        (valid["purchase_month"].dt.year - valid["cohort"].dt.year) * 12
        + (valid["purchase_month"].dt.month - valid["cohort"].dt.month)
    )

    cohort_size = first.value_counts().sort_index()
    retention = (
        valid.groupby(["cohort", "cohort_index"])["customer_unique_id"]
        .nunique()
        .unstack(fill_value=0)
    )
    retention = retention.reindex(columns=range(0, int(retention.columns.max()) + 1), fill_value=0)
    retention = retention.div(cohort_size, axis=0)

    wide = retention.copy()
    wide.insert(0, "cohort_size", cohort_size.reindex(wide.index).astype(int))
    wide.index = wide.index.strftime("%Y-%m")
    wide.index.name = "cohort"
    wide.columns = ["cohort_size"] + [f"M{i}" for i in retention.columns]

    long = (
        retention.stack()
        .reset_index(name="retention_rate")
        .rename(columns={"cohort": "cohort", "cohort_index": "month_index"})
    )
    long["cohort"] = long["cohort"].dt.strftime("%Y-%m")
    long["cohort_size"] = long["cohort"].map(
        cohort_size.rename(index=lambda x: x.strftime("%Y-%m"))
    )

    # 只统计样本量 >= 30 的同期群，避免早期小样本噪声
    stable = retention[cohort_size >= 30]
    month1 = float(stable[1].mean()) if 1 in stable.columns else float("nan")
    month3 = float(stable[3].mean()) if 3 in stable.columns else float("nan")
    month6 = float(stable[6].mean()) if 6 in stable.columns else float("nan")

    info = {
        "cohorts": int(len(cohort_size)),
        "stable_cohorts": int((cohort_size >= 30).sum()),
        "month1_retention": month1,
        "month3_retention": month3,
        "month6_retention": month6,
    }
    return wide, long, info


# ---------------------------------------------------------------------------
# 3. ABC / Pareto
# ---------------------------------------------------------------------------
def compute_abc(items: pd.DataFrame, valid_ids: set[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sub = items[items["order_id"].isin(valid_ids)].copy()

    products = (
        sub.groupby(["product_id", "product_category_name_english"], as_index=False)
        .agg(
            gmv=("price", "sum"),
            orders=("order_id", "nunique"),
            units=("order_item_id", "count"),
        )
        .sort_values("gmv", ascending=False)
        .reset_index(drop=True)
    )
    products["gmv_share"] = products["gmv"] / products["gmv"].sum()
    products["cum_gmv_share"] = products["gmv"].cumsum() / products["gmv"].sum()
    products["abc_class"] = np.select(
        [products["cum_gmv_share"] <= 0.80, products["cum_gmv_share"] <= 0.95],
        ["A", "B"],
        default="C",
    )

    categories = (
        sub.groupby("product_category_name_english", as_index=False)
        .agg(
            gmv=("price", "sum"),
            orders=("order_id", "nunique"),
            products=("product_id", "nunique"),
            units=("order_item_id", "count"),
        )
        .sort_values("gmv", ascending=False)
        .reset_index(drop=True)
    )
    categories["gmv_share"] = categories["gmv"] / categories["gmv"].sum()
    categories["cum_gmv_share"] = categories["gmv"].cumsum() / categories["gmv"].sum()
    categories["abc_class"] = np.select(
        [categories["cum_gmv_share"] <= 0.80, categories["cum_gmv_share"] <= 0.95],
        ["A", "B"],
        default="C",
    )

    summary = (
        products.groupby("abc_class", as_index=False)
        .agg(products=("product_id", "count"), gmv=("gmv", "sum"))
        .sort_values("abc_class")
    )
    summary["gmv_share"] = summary["gmv"] / summary["gmv"].sum()
    summary["product_share"] = summary["products"] / len(products)

    return products, categories, summary


# ---------------------------------------------------------------------------
# 4. 波士顿矩阵
# ---------------------------------------------------------------------------
def compute_boston(orders: pd.DataFrame, items: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    valid = valid_orders(orders).copy()
    valid["purchase_month"] = pd.to_datetime(
        valid["purchase_month"] + "-01", errors="coerce"
    )

    ids_2017 = set(
        valid.loc[
            (valid["purchase_month"].dt.year == 2017)
            & (valid["purchase_month"].dt.month <= 8),
            "order_id",
        ]
    )
    ids_2018 = set(
        valid.loc[
            (valid["purchase_month"].dt.year == 2018)
            & (valid["purchase_month"].dt.month <= 8),
            "order_id",
        ]
    )

    def category_gmv(ids: set[str]) -> pd.Series:
        sub = items[items["order_id"].isin(ids)]
        return sub.groupby("product_category_name_english")["price"].sum()

    g17 = category_gmv(ids_2017)
    g18 = category_gmv(ids_2018)
    df = pd.DataFrame({"gmv_2017": g17, "gmv_2018": g18}).fillna(0.0)
    df["growth"] = np.where(
        df["gmv_2017"] > 0, df["gmv_2018"] / df["gmv_2017"] - 1, np.nan
    )
    df["share_2018"] = df["gmv_2018"] / df["gmv_2018"].sum()
    df["is_new_category"] = df["gmv_2017"] == 0
    df["is_top20"] = df["gmv_2018"].rank(method="first", ascending=False) <= 20

    # 只有 2017 有销售、且 2018 GMV >= 1000 的品类参与象限划分
    eligible_mask = (df["gmv_2017"] > 0) & (df["gmv_2018"] >= 1000)
    eligible = df[eligible_mask].copy()
    share_median = float(eligible["share_2018"].median())
    growth_median = float(eligible["growth"].median())

    df["quadrant"] = "未纳入"
    if len(eligible):
        conditions = [
            (eligible["share_2018"] >= share_median) & (eligible["growth"] >= growth_median),
            (eligible["share_2018"] >= share_median) & (eligible["growth"] < growth_median),
            (eligible["share_2018"] < share_median) & (eligible["growth"] >= growth_median),
            (eligible["share_2018"] < share_median) & (eligible["growth"] < growth_median),
        ]
        choices = ["明星（高份额/高增长）", "现金牛（高份额/低增长）",
                   "问题（低份额/高增长）", "瘦狗（低份额/低增长）"]
        df.loc[eligible.index, "quadrant"] = np.select(
            conditions, choices, default="未纳入"
        )

    df = df.sort_values("gmv_2018", ascending=False).reset_index()
    info = {
        "share_median": share_median,
        "growth_median": growth_median,
        "eligible_categories": int(eligible_mask.sum()),
        "total_2018_gmv": float(df["gmv_2018"].sum()),
    }
    return df, info


# ---------------------------------------------------------------------------
# 5. SARIMA
# ---------------------------------------------------------------------------
def monthly_gmv(orders: pd.DataFrame) -> pd.Series:
    valid = valid_orders(orders).copy()
    series = valid.groupby("purchase_month")["gmv"].sum().sort_index()
    series.index = pd.PeriodIndex(series.index, freq="M").to_timestamp()
    series = series.asfreq("MS")
    # 完整月份：2017-01 ～ 2018-08；2016 年为平台起步期，2018-09/10 数据不完整
    series = series.loc["2017-01-01":"2018-08-31"]
    if series.isna().any():
        series = series.interpolate()
    return series.astype(float)


def forecast_metrics(actual: np.ndarray, predicted: np.ndarray) -> tuple[float, float]:
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    mask = actual != 0
    mape = float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)
    return rmse, mape


def compute_sarima(orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    series = monthly_gmv(orders)
    test_n = 6
    train, test = series.iloc[:-test_n], series.iloc[-test_n:]

    candidates = [
        ("ARIMA(1,1,1)", (1, 1, 1), (0, 0, 0, 0)),
        ("ARIMA(0,1,1)", (0, 1, 1), (0, 0, 0, 0)),
        ("SARIMA(1,1,1)(1,1,1,12)", (1, 1, 1), (1, 1, 1, 12)),
        ("SARIMA(0,1,1)(0,1,1,12)", (0, 1, 1), (0, 1, 1, 12)),
        ("SARIMA(1,1,1)(0,1,1,12)", (1, 1, 1), (0, 1, 1, 12)),
        # 样本仅 20 个月，季节差分后只剩 2 个观测；补充不做季节差分的候选
        ("SARIMA(1,1,1)(1,0,1,12)", (1, 1, 1), (1, 0, 1, 12)),
        ("SARIMA(0,1,1)(0,0,1,12)", (0, 1, 1), (0, 0, 1, 12)),
        ("SARIMA(1,1,1)(0,0,1,12)", (1, 1, 1), (0, 0, 1, 12)),
    ]

    results: list[dict] = []
    best: dict | None = None
    for name, order, seasonal in candidates:
        try:
            model = SARIMAX(
                train,
                order=order,
                seasonal_order=seasonal,
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            fit = model.fit(disp=False, maxiter=200)
            forecast_obj = fit.get_forecast(steps=test_n)
            pred = forecast_obj.predicted_mean.values
            pred_ci = forecast_obj.conf_int(alpha=0.05).values
            rmse, mape = forecast_metrics(test.values, pred)
            row = {
                "model": name,
                "order": str(order),
                "seasonal_order": str(seasonal),
                "aic": float(fit.aic),
                "rmse": rmse,
                "mape": mape,
                "status": "ok",
            }
            results.append(row)
            if best is None or rmse < best["rmse"]:
                best = {
                    **row,
                    "order_tuple": order,
                    "seasonal_tuple": seasonal,
                    "test_pred": pred,
                    "test_ci": pred_ci,
                }
        except Exception as exc:  # 收敛失败/样本过短
            results.append({
                "model": name,
                "order": str(order),
                "seasonal_order": str(seasonal),
                "aic": np.nan,
                "rmse": np.nan,
                "mape": np.nan,
                "status": f"failed: {type(exc).__name__}",
            })

    if best is None:
        raise RuntimeError("所有 SARIMA 候选模型均拟合失败")

    # 基准：季节朴素（去年同月）
    if len(train) >= 12:
        naive_pred = train.iloc[-12:-12 + test_n].values
    else:
        naive_pred = np.repeat(train.iloc[-1], test_n)
    naive_rmse, naive_mape = forecast_metrics(test.values, naive_pred)

    # 用全量数据重拟合，向前预测 6 个月
    final_model = SARIMAX(
        series,
        order=best["order_tuple"],
        seasonal_order=best["seasonal_tuple"],
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    final_fit = final_model.fit(disp=False, maxiter=200)
    future_index = pd.date_range(
        series.index[-1] + pd.offsets.MonthBegin(1), periods=6, freq="MS"
    )
    future = final_fit.get_forecast(steps=6)
    future_mean = future.predicted_mean
    future_ci = future.conf_int(alpha=0.05)

    backtest = pd.DataFrame({
        "month": test.index,
        "forecast": best["test_pred"],
        "actual": test.values,
        "lower_95": best["test_ci"][:, 0],
        "upper_95": best["test_ci"][:, 1],
        "kind": "backtest",
    })
    future_df = pd.DataFrame({
        "month": future_index,
        "forecast": future_mean.values,
        "actual": np.nan,
        "lower_95": future_ci.iloc[:, 0].values,
        "upper_95": future_ci.iloc[:, 1].values,
        "kind": "future",
    })

    forecast_df = pd.concat([backtest, future_df], ignore_index=True)
    forecast_df["month"] = pd.to_datetime(forecast_df["month"]).dt.strftime("%Y-%m")

    metrics_df = pd.DataFrame(results)
    metrics_df["naive_rmse"] = naive_rmse
    metrics_df["naive_mape"] = naive_mape
    metrics_df["selected"] = metrics_df["model"] == best["model"]

    info = {
        "selected_model": best["model"],
        "order": list(best["order_tuple"]),
        "seasonal_order": list(best["seasonal_tuple"]),
        "train_months": int(len(train)),
        "test_months": int(len(test)),
        "rmse": float(best["rmse"]),
        "mape": float(best["mape"]),
        "naive_rmse": naive_rmse,
        "naive_mape": naive_mape,
        "future_6m_mean": float(future_mean.mean()),
        "series_start": series.index[0].strftime("%Y-%m"),
        "series_end": series.index[-1].strftime("%Y-%m"),
    }
    return forecast_df, metrics_df, info


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------
def build_report(
    rfm_summary: pd.DataFrame,
    rfm_thresholds: dict,
    cohort_info: dict,
    abc_summary: pd.DataFrame,
    boston: pd.DataFrame,
    boston_info: dict,
    sarima_info: dict,
    sarima_metrics: pd.DataFrame,
) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    top_segment = rfm_summary.iloc[0]
    quadrant_counts = (
        boston[boston["quadrant"] != "未纳入"]["quadrant"].value_counts()
    )

    lines = [
        "# 商业分析模型报告",
        "",
        f"- 生成时间：{now}",
        "- 输入：`data/clean/orders_enriched.csv`、`data/clean/order_items.csv`",
        f"- 随机种子：`RANDOM_SEED = {RANDOM_SEED}`",
        "- 有效订单口径：`is_valid_order = True` 且 `has_items = True`（剔除取消/不可用/无商品明细订单）",
        "",
        "## 一、RFM 客户分层",
        "",
        "**口径**：以 `customer_unique_id` 为客户唯一标识；"
        f"快照日为 {rfm_thresholds['snapshot_date']}；"
        "R = 距最近一次购买天数，F = 订单数，M = 商品金额合计（GMV）。",
        "",
        f"**分箱依据**：R 与 M 用中位数切分（R 中位数 {rfm_thresholds['r_median_days']:.0f} 天，"
        f"M 中位数 R$ {rfm_thresholds['m_median_brl']:,.2f}）；"
        f"F 中位数为 {rfm_thresholds['f_median']:.0f}，若直接用中位数会导致所有客户都落在“高频”侧，"
        f"因此采用 **F ≥ {rfm_thresholds['f_threshold']:.0f}** 作为复购客户阈值。"
        "选用中位数而非均值，是因为消费金额右偏严重，均值会被少数大客户拉高。",
        "补充的 1–5 分采用 `rank(method='first')` 后等频分箱；同值客户会按行序拆分，"
        "因此分数仅用于排序参考，八分类以中位数阈值为准。",
        "",
        "| 分层 | 客户数 | 客户占比 | GMV (R$) | GMV 占比 | 平均 R (天) | 平均 F | 平均 M (R$) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in rfm_summary.iterrows():
        lines.append(
            f"| {row['segment']} | {int(row['customers']):,} | {row['customer_share']:.2%} | "
            f"{row['monetary']:,.2f} | {row['monetary_share']:.2%} | "
            f"{row['avg_recency']:.0f} | {row['avg_frequency']:.2f} | {row['avg_monetary']:,.2f} |"
        )

    lines += [
        "",
        f"**解读**：GMV 贡献最高的分层是 **{top_segment['segment']}**，"
        f"客户占比 {top_segment['customer_share']:.2%}，贡献 {top_segment['monetary_share']:.2%} 的 GMV。"
        "“重要保持/挽留”类客户 R 值偏大，应作为召回活动的优先对象。",
        "",
        "## 二、同期群留存",
        "",
        f"共识别 {cohort_info['cohorts']} 个首购月同期群，其中样本量 ≥ 30 的稳定同期群 "
        f"{cohort_info['stable_cohorts']} 个。",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 首月后第 1 个月平均留存率 | {cohort_info['month1_retention']:.2%} |",
        f"| 首月后第 3 个月平均留存率 | {cohort_info['month3_retention']:.2%} |",
        f"| 首月后第 6 个月平均留存率 | {cohort_info['month6_retention']:.2%} |",
        "",
        "> 留存率 = 该同期群在第 N 个月仍有购买的去重客户数 / 同期群初始客户数。"
        "电商复购天然偏低，重点看不同同期群之间的相对走势，以及 2017-11（黑五）等大促月份的异常抬升。",
        "",
        "## 三、ABC / Pareto",
        "",
        "| 类别 | 商品数 | 商品占比 | GMV (R$) | GMV 占比 | 划分规则 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    rules = {"A": "累计 GMV ≤ 80%", "B": "累计 GMV 80%–95%", "C": "累计 GMV > 95%"}
    for _, row in abc_summary.iterrows():
        lines.append(
            f"| {row['abc_class']} | {int(row['products']):,} | {row['product_share']:.2%} | "
            f"{row['gmv']:,.2f} | {row['gmv_share']:.2%} | {rules.get(row['abc_class'], '')} |"
        )

    lines += [
        "",
        "> A 类商品是库存与营销资源的核心；C 类商品数量多但贡献低，可考虑长尾优化。",
        "",
        "## 四、波士顿矩阵",
        "",
        "**口径**：为消除 2018 年数据不完整的影响，同比统一取 **2017 年 1–8 月 vs 2018 年 1–8 月**；"
        f"x 轴为品类 2018 年 GMV 份额，y 轴为同比增长率；参与划分的品类需满足 2017 年有销售且 2018 年 GMV ≥ R$ 1,000。",
        "",
        f"- 份额中位数：{boston_info['share_median']:.2%}",
        f"- 增长率中位数：{boston_info['growth_median']:.2%}",
        f"- 参与划分品类数：{boston_info['eligible_categories']}",
        "",
        "| 象限 | 品类数 |",
        "|---|---:|",
    ]
    for quadrant, count in quadrant_counts.items():
        lines.append(f"| {quadrant} | {count} |")

    lines += [
        "",
        "> 明星品类应加大投入；现金牛品类维持份额、控制成本；问题品类需判断增长是否可持续；"
        "瘦狗品类考虑收缩 SKU。",
        "",
        "## 五、SARIMA 月度 GMV 预测",
        "",
        f"- 建模区间：{sarima_info['series_start']} ～ {sarima_info['series_end']}（完整月份）",
        f"- 训练集：前 {sarima_info['train_months']} 个月；测试集：最后 {sarima_info['test_months']} 个月",
        f"- 最优模型：**{sarima_info['selected_model']}**，order={sarima_info['order']}，"
        f"seasonal_order={sarima_info['seasonal_order']}",
        "",
        "| 模型 | AIC | RMSE | MAPE | 状态 |",
        "|---|---:|---:|---:|---|",
    ]
    for _, row in sarima_metrics.iterrows():
        aic = "—" if pd.isna(row["aic"]) else f"{row['aic']:.1f}"
        rmse = "—" if pd.isna(row["rmse"]) else f"{row['rmse']:,.0f}"
        mape = "—" if pd.isna(row["mape"]) else f"{row['mape']:.2f}%"
        lines.append(
            f"| {row['model']}{' ✅' if row['selected'] else ''} | {aic} | {rmse} | {mape} | {row['status']} |"
        )

    lines += [
        "",
        f"**回测结果**：最优模型 RMSE = R$ {sarima_info['rmse']:,.0f}，"
        f"MAPE = {sarima_info['mape']:.2f}%；季节朴素基准 RMSE = R$ {sarima_info['naive_rmse']:,.0f}，"
        f"MAPE = {sarima_info['naive_mape']:.2f}%。",
        "",
        f"**未来 6 个月预测均值**：R$ {sarima_info['future_6m_mean']:,.0f}/月，"
        "预测区间见 `sarima_forecast.csv` 的 `lower_95` / `upper_95`。",
        "",
        "> 说明：可用月度样本仅 20 个月，季节差分后仅剩 2 个观测，季节项容易过拟合；"
        "因此同时比较了非季节 ARIMA、季节差分 SARIMA（D=1）与不做季节差分的 SARIMA（D=0），"
        "按回测 RMSE 选择最优模型，并报告相对季节朴素基准的提升。论文中需明确这一样本限制。",
        "> AIC 在不同差分阶数之间不可直接比较，模型选择以回测 RMSE 为准。",
        "",
        "## 六、模型输出文件",
        "",
        "| 文件 | 内容 |",
        "|---|---|",
        "| `rfm_customers.csv` | 每个客户的 R/F/M、评分与八分类 |",
        "| `rfm_segment_summary.csv` | 八分类汇总 |",
        "| `cohort_retention.csv` | 同期群留存宽表 |",
        "| `cohort_long.csv` | 同期群留存长表 |",
        "| `abc_products.csv` | 商品级 ABC 分类 |",
        "| `abc_categories.csv` | 品类级 ABC 分类 |",
        "| `abc_summary.csv` | ABC 汇总 |",
        "| `boston_matrix.csv` | 品类份额、增长、象限 |",
        "| `sarima_forecast.csv` | 回测拟合 + 未来 6 个月预测与 95% 区间 |",
        "| `sarima_metrics.csv` | 候选模型与基准指标 |",
        "| `sarima_order.json` | 最优模型参数 |",
        "",
        f"> 本报告由 `scripts/03_models.py` 自动生成。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    np.random.seed(RANDOM_SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("03_models.py —— 商业分析模型")
    print("=" * 60)
    print("读取清洗后数据 ...")
    orders, items = load_data()
    print(f"  订单: {len(orders):,} | 商品明细: {len(items):,}")

    valid = valid_orders(orders)
    valid_ids = set(valid["order_id"])
    print(f"  有效订单: {len(valid):,}")

    print("\n[1/5] RFM ...")
    rfm, rfm_summary, rfm_thresholds = compute_rfm(orders)
    rfm.to_csv(OUT_DIR / "rfm_customers.csv", index=False, encoding="utf-8-sig")
    rfm_summary.to_csv(OUT_DIR / "rfm_segment_summary.csv", index=False, encoding="utf-8-sig")
    print(f"  客户: {len(rfm):,} | 分层: {len(rfm_summary)} 类")

    print("[2/5] 同期群留存 ...")
    cohort_wide, cohort_long, cohort_info = compute_cohort(orders)
    cohort_wide.to_csv(OUT_DIR / "cohort_retention.csv", encoding="utf-8-sig")
    cohort_long.to_csv(OUT_DIR / "cohort_long.csv", index=False, encoding="utf-8-sig")
    print(f"  同期群: {cohort_info['cohorts']} | 第 1 月留存: {cohort_info['month1_retention']:.2%}")

    print("[3/5] ABC / Pareto ...")
    abc_products, abc_categories, abc_summary = compute_abc(items, valid_ids)
    abc_products.to_csv(OUT_DIR / "abc_products.csv", index=False, encoding="utf-8-sig")
    abc_categories.to_csv(OUT_DIR / "abc_categories.csv", index=False, encoding="utf-8-sig")
    abc_summary.to_csv(OUT_DIR / "abc_summary.csv", index=False, encoding="utf-8-sig")
    print(f"  商品: {len(abc_products):,} | A 类: {int((abc_products['abc_class'] == 'A').sum()):,}")

    print("[4/5] 波士顿矩阵 ...")
    boston, boston_info = compute_boston(orders, items)
    boston.to_csv(OUT_DIR / "boston_matrix.csv", index=False, encoding="utf-8-sig")
    print(f"  品类: {len(boston)} | 参与划分: {boston_info['eligible_categories']}")

    print("[5/5] SARIMA ...")
    sarima_forecast, sarima_metrics, sarima_info = compute_sarima(orders)
    sarima_forecast.to_csv(OUT_DIR / "sarima_forecast.csv", index=False, encoding="utf-8-sig")
    sarima_metrics.to_csv(OUT_DIR / "sarima_metrics.csv", index=False, encoding="utf-8-sig")
    (OUT_DIR / "sarima_order.json").write_text(
        json.dumps(sarima_info, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  最优: {sarima_info['selected_model']} | "
          f"RMSE {sarima_info['rmse']:,.0f} | MAPE {sarima_info['mape']:.2f}%")

    print("\n生成模型报告 ...")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        build_report(
            rfm_summary, rfm_thresholds, cohort_info, abc_summary,
            boston, boston_info, sarima_info, sarima_metrics,
        ),
        encoding="utf-8",
    )

    print("\n" + "-" * 60)
    print(f"RFM: {len(rfm):,} 客户，{len(rfm_summary)} 个分层")
    print(f"同期群: {cohort_info['stable_cohorts']} 个稳定同期群，"
          f"第 1 月留存 {cohort_info['month1_retention']:.2%}")
    a_share = abc_summary.loc[abc_summary['abc_class'] == 'A', 'gmv_share']
    print(f"ABC: A 类商品 {int((abc_products['abc_class']=='A').sum()):,} 个，"
          f"贡献 {float(a_share.iloc[0]) if len(a_share) else 0:.2%} GMV")
    print(f"波士顿: {boston_info['eligible_categories']} 个品类参与划分")
    print(f"SARIMA: {sarima_info['selected_model']}，MAPE {sarima_info['mape']:.2f}%")
    print(f"报告: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
