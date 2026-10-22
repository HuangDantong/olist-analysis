# -*- coding: utf-8 -*-
"""
02_clean.py —— 数据清洗、指标派生、多表整合与 SQLite 导出

处理内容
--------
1. 类型统一：时间字段转 datetime，邮编前缀按字符串保留前导零；
2. 缺失值：商品品类/尺寸、评价正文等按业务含义填充或标记；
3. 异常/重复：评论按订单去重、地理表按邮编前缀聚合；
4. 指标派生：下单月份、配送时长、是否延迟、商品体积等；
5. 多表整合：生成订单级宽表 orders_enriched；
6. 导出 CSV 与 SQLite（data/clean/olist.db），并生成清洗报告。

口径说明
--------
- `orders_clean` 保留全部 99,441 个订单，不删除取消/不可用订单；
- `is_valid_order = order_status not in ("canceled", "unavailable")`，
  做 GMV/客户分析时按该字段过滤；
- 配送时长、延迟天数只在有实际送达时间时计算，否则为 NaN；
- 订单级评价：同一订单多条评价取 `review_answer_timestamp` 最新的一条；
- 地理表：同一邮编前缀取经纬度中位数，1,000,163 行压缩到约 1.9 万行。

用法
----
    python scripts/02_clean.py
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "olist"
CLEAN_DIR = ROOT / "data" / "clean"
TABLES_DIR = ROOT / "outputs" / "tables"
REPORT_PATH = ROOT / "docs" / "cleaning_report.md"
DB_PATH = CLEAN_DIR / "olist.db"

RANDOM_SEED = 42

RAW_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

DTYPES = {
    "customers": {"customer_zip_code_prefix": "string"},
    "sellers": {"seller_zip_code_prefix": "string"},
    "geolocation": {"geolocation_zip_code_prefix": "string"},
}

ORDER_DATETIME_COLS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

PRODUCT_DIM_COLS = [
    "product_weight_g",
    "product_length_cm",
    "product_height_cm",
    "product_width_cm",
]


def read_raw() -> dict[str, pd.DataFrame]:
    missing = [f for f in RAW_FILES.values() if not (RAW_DIR / f).is_file()]
    if missing:
        raise SystemExit(
            f"原始数据不完整，缺少: {missing}\n请先运行: python scripts/00_download.py"
        )
    return {
        name: pd.read_csv(RAW_DIR / filename, dtype=DTYPES.get(name, {}))
        for name, filename in RAW_FILES.items()
    }


def clean_orders(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    for col in ORDER_DATETIME_COLS:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    purchase = df["order_purchase_timestamp"]
    delivered = df["order_delivered_customer_date"]
    estimated = df["order_estimated_delivery_date"]

    # 存为 ISO 字符串，避免 sqlite3 对 datetime.date 的适配问题
    df["purchase_date"] = purchase.dt.strftime("%Y-%m-%d")
    df["purchase_month"] = purchase.dt.strftime("%Y-%m")
    df["purchase_year"] = purchase.dt.year.astype("Int64")
    df["approval_hours"] = (
        df["order_approved_at"] - purchase
    ).dt.total_seconds() / 3600
    df["delivery_days"] = (delivered - purchase).dt.total_seconds() / 86400
    df["estimated_days"] = (estimated - purchase).dt.total_seconds() / 86400
    df["late_days"] = ((delivered - estimated).dt.total_seconds() / 86400).clip(lower=0)

    has_both = delivered.notna() & estimated.notna()
    df["is_late"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
    df.loc[has_both, "is_late"] = (delivered[has_both] > estimated[has_both]).astype(bool)

    df["is_valid_order"] = ~df["order_status"].isin(["canceled", "unavailable"])
    return df


def clean_customers(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["customer_zip_code_prefix"] = df["customer_zip_code_prefix"].astype("string").str.zfill(5)
    df["customer_city"] = df["customer_city"].astype("string").str.strip().str.lower()
    df["customer_state"] = df["customer_state"].astype("string").str.strip().str.upper()
    return df


def clean_sellers(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["seller_zip_code_prefix"] = df["seller_zip_code_prefix"].astype("string").str.zfill(5)
    df["seller_city"] = df["seller_city"].astype("string").str.strip().str.lower()
    df["seller_state"] = df["seller_state"].astype("string").str.strip().str.upper()
    return df


def clean_products(raw: pd.DataFrame, translation: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df = df.rename(columns={
        "product_name_lenght": "product_name_length",
        "product_description_lenght": "product_description_length",
    })

    df["has_category"] = df["product_category_name"].notna()
    df["product_category_name"] = df["product_category_name"].fillna("unknown")

    df = df.merge(translation, on="product_category_name", how="left")
    df["has_translation"] = df["product_category_name_english"].notna()
    df["product_category_name_english"] = df["product_category_name_english"].fillna("unknown")

    df["has_dimensions"] = df[PRODUCT_DIM_COLS].notna().all(axis=1)
    for col in PRODUCT_DIM_COLS:
        df[col] = df[col].fillna(df[col].median())
    df["product_volume_cm3"] = (
        df["product_length_cm"] * df["product_height_cm"] * df["product_width_cm"]
    )
    return df


def clean_order_items(
    raw_items: pd.DataFrame, products: pd.DataFrame
) -> pd.DataFrame:
    df = raw_items.copy()
    df["shipping_limit_date"] = pd.to_datetime(df["shipping_limit_date"], errors="coerce")
    df["total_value"] = df["price"] + df["freight_value"]

    product_cols = [
        "product_id",
        "product_category_name",
        "product_category_name_english",
        "product_weight_g",
        "product_volume_cm3",
        "has_category",
        "has_dimensions",
    ]
    df = df.merge(products[product_cols], on="product_id", how="left")
    return df


def clean_payments(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["payment_type"] = df["payment_type"].astype("string").str.strip().str.lower()
    return df


def aggregate_payments(payments: pd.DataFrame) -> pd.DataFrame:
    agg = payments.groupby("order_id", as_index=False).agg(
        payment_value_sum=("payment_value", "sum"),
        payment_count=("payment_sequential", "count"),
        payment_installments_max=("payment_installments", "max"),
        payment_type_main=("payment_type", "first"),
    )
    return agg


def clean_reviews(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = raw.copy()
    df["review_creation_date"] = pd.to_datetime(df["review_creation_date"], errors="coerce")
    df["review_answer_timestamp"] = pd.to_datetime(
        df["review_answer_timestamp"], errors="coerce"
    )
    df["has_comment"] = df["review_comment_message"].notna()
    df["comment_length"] = df["review_comment_message"].fillna("").astype("string").str.len()
    df["review_id_dup_count"] = df.groupby("review_id")["order_id"].transform("nunique")

    # 订单级：同一订单多条评价，取填写时间最新的一条
    order_level = (
        df.sort_values(["order_id", "review_answer_timestamp"], na_position="last")
        .drop_duplicates("order_id", keep="last")
        .reset_index(drop=True)
    )
    return df, order_level


def clean_geolocation(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["geolocation_zip_code_prefix"] = (
        df["geolocation_zip_code_prefix"].astype("string").str.zfill(5)
    )
    df["geolocation_city"] = df["geolocation_city"].astype("string").str.strip().str.lower()
    df["geolocation_state"] = (
        df["geolocation_state"].astype("string").str.strip().str.upper()
    )
    agg = df.groupby("geolocation_zip_code_prefix", as_index=False).agg(
        geolocation_lat=("geolocation_lat", "median"),
        geolocation_lng=("geolocation_lng", "median"),
        geolocation_city=("geolocation_city", "first"),
        geolocation_state=("geolocation_state", "first"),
        point_count=("geolocation_lat", "size"),
    )
    return agg


def aggregate_items(items: pd.DataFrame) -> pd.DataFrame:
    return items.groupby("order_id", as_index=False).agg(
        item_count=("order_item_id", "count"),
        seller_count=("seller_id", "nunique"),
        product_count=("product_id", "nunique"),
        gmv=("price", "sum"),
        freight_total=("freight_value", "sum"),
    )


def build_enriched(
    orders: pd.DataFrame,
    items_agg: pd.DataFrame,
    payments_agg: pd.DataFrame,
    reviews_order: pd.DataFrame,
    customers: pd.DataFrame,
) -> pd.DataFrame:
    df = orders.merge(items_agg, on="order_id", how="left")
    df = df.merge(payments_agg, on="order_id", how="left")
    df = df.merge(
        reviews_order[["order_id", "review_score", "has_comment", "comment_length"]],
        on="order_id",
        how="left",
    )
    df = df.merge(
        customers[
            [
                "customer_id",
                "customer_unique_id",
                "customer_city",
                "customer_state",
                "customer_zip_code_prefix",
            ]
        ],
        on="customer_id",
        how="left",
    )
    df["item_value_total"] = df["gmv"] + df["freight_total"]
    df["payment_diff"] = df["payment_value_sum"] - df["item_value_total"]
    df["has_items"] = df["item_count"].notna()
    return df


def export_csv(tables: dict[str, pd.DataFrame]) -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        path = CLEAN_DIR / f"{name}.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        print(f"  写出 {path.name:28s} {len(df):>9,d} 行 × {df.shape[1]:>2d} 列")


def export_sqlite(tables: dict[str, pd.DataFrame]) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # 不删除旧文件：Windows 下其他进程（如大屏）持有句柄时 unlink 会失败；
    # to_sql(if_exists="replace") 足以重建全部表。
    conn = sqlite3.connect(DB_PATH)
    try:
        for name, df in tables.items():
            df.to_sql(name, conn, if_exists="replace", index=False, chunksize=50_000)
        indexes = {
            "orders": ["order_id", "customer_id", "purchase_month", "order_status"],
            "order_items": ["order_id", "product_id", "seller_id"],
            "payments": ["order_id"],
            "reviews": ["order_id", "review_id"],
            "customers": ["customer_id", "customer_unique_id"],
            "products": ["product_id", "product_category_name_english"],
            "sellers": ["seller_id"],
            "geolocation": ["geolocation_zip_code_prefix"],
            "orders_enriched": ["order_id", "customer_unique_id", "purchase_month"],
        }
        for table, cols in indexes.items():
            if table not in tables:
                continue
            for col in cols:
                conn.execute(
                    f'CREATE INDEX IF NOT EXISTS "idx_{table}_{col}" ON "{table}" ("{col}")'
                )
        conn.commit()
    finally:
        conn.close()
    print(f"  SQLite: {DB_PATH} ({DB_PATH.stat().st_size / 2**20:.1f} MB)")


def build_report(
    raw: dict[str, pd.DataFrame],
    clean: dict[str, pd.DataFrame],
    orders: pd.DataFrame,
    reviews: pd.DataFrame,
    reviews_order: pd.DataFrame,
    products: pd.DataFrame,
    geolocation: pd.DataFrame,
) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    invalid_orders = int((~orders["is_valid_order"]).sum())
    orders_with_items = int(orders_with_items_count(orders))
    delivered = orders["order_status"].eq("delivered").sum()
    missing_delivered = int(
        orders.loc[orders["order_status"].eq("delivered"),
                   "order_delivered_customer_date"].isna().sum()
    )
    late_orders = int(orders["is_late"].fillna(False).sum())
    unknown_category = int((~products["has_category"]).sum())
    missing_translation = int((~products["has_translation"]).sum())
    missing_dims = int((~products["has_dimensions"]).sum())
    dup_review_orders = int((reviews_order["review_id_dup_count"] > 1).sum())

    lines = [
        "# 数据清洗报告",
        "",
        f"- 生成时间：{now}",
        "- 输入：`data/raw/olist/`（原始数据，未修改）",
        "- 输出：`data/clean/*.csv` 与 `data/clean/olist.db`",
        "",
        "## 一、行数变化",
        "",
        "| 表 | 原始行数 | 清洗后行数 | 说明 |",
        "|---|---:|---:|---|",
        f"| orders | {len(raw['orders']):,} | {len(clean['orders']):,} | 保留全部订单，新增派生字段 |",
        f"| order_items | {len(raw['order_items']):,} | {len(clean['order_items']):,} | 关联商品品类与体积 |",
        f"| payments | {len(raw['payments']):,} | {len(clean['payments']):,} | 类型规范化 |",
        f"| reviews | {len(raw['reviews']):,} | {len(clean['reviews']):,} | 保留全部评价，新增评论文本标记 |",
        f"| reviews（订单级） | — | {len(reviews_order):,} | 每单取最新一条评价 |",
        f"| customers | {len(raw['customers']):,} | {len(clean['customers']):,} | 邮编补零、城市/州规范化 |",
        f"| products | {len(raw['products']):,} | {len(clean['products']):,} | 品类翻译、尺寸缺失填充 |",
        f"| sellers | {len(raw['sellers']):,} | {len(clean['sellers']):,} | 邮编补零、城市/州规范化 |",
        f"| geolocation | {len(raw['geolocation']):,} | {len(geolocation):,} | 按邮编前缀聚合（经纬度中位数） |",
        f"| category_translation | {len(raw['category_translation']):,} | {len(clean['category_translation']):,} | 原样保留 |",
        f"| **orders_enriched** | — | {len(clean['orders_enriched']):,} | 订单级宽表（订单 + 商品 + 支付 + 评价 + 客户） |",
        "",
        "## 二、清洗规则",
        "",
        "1. **时间字段**：5 个订单时间字段、发货截止时间、评价时间统一转为 datetime；无法解析的置为 NaT。",
        "2. **邮编前缀**：按字符串读取并 `zfill(5)`，保留 `01037` 这类前导零。",
        f"3. **商品品类**：缺失品类标记为 `unknown`（{unknown_category:,} 个），并合并英文翻译表；"
        f"无对应翻译的标记为 `unknown`（{missing_translation:,} 个）。",
        f"4. **商品尺寸**：重量/长/高/宽缺失时用该列中位数填充，并用 `has_dimensions` 标记原始记录是否完整"
        f"（{missing_dims:,} 个商品存在缺失）。",
        f"5. **评价**：同一 `review_id` 可能对应多个订单（{int((reviews['review_id_dup_count'] > 1).sum()):,} 条评价涉及多单）；"
        "订单级分析取该订单最新一条评价，评价级分析保留全部记录。",
        f"6. **地理表**：同一邮编前缀的多条坐标取经纬度中位数，城市/州取第一条，"
        f"并由 {len(raw['geolocation']):,} 行压缩为 {len(geolocation):,} 行。",
        "7. **订单状态**：保留全部订单；新增 `is_valid_order` 标记，取消/不可用订单为 False。",
        "",
        "## 三、派生指标",
        "",
        "| 字段 | 所属表 | 含义 |",
        "|---|---|---|",
        "| `purchase_date` | orders | 下单日期 |",
        "| `purchase_month` | orders | 下单月份（YYYY-MM） |",
        "| `purchase_year` | orders | 下单年份 |",
        "| `approval_hours` | orders | 下单到支付审核通过的小时数 |",
        "| `delivery_days` | orders | 下单到实际送达的天数 |",
        "| `estimated_days` | orders | 下单到承诺送达的天数 |",
        "| `late_days` | orders | 超过承诺送达的天数（未延迟为 0） |",
        "| `is_late` | orders | 是否延迟送达（缺时间时为 NA） |",
        "| `is_valid_order` | orders | 是否非取消/非不可用订单 |",
        "| `total_value` | order_items | `price + freight_value` |",
        "| `product_volume_cm3` | products | 长 × 高 × 宽（cm³） |",
        "| `item_count` | orders_enriched | 订单商品件数 |",
        "| `seller_count` | orders_enriched | 订单涉及卖家数 |",
        "| `product_count` | orders_enriched | 订单涉及商品数 |",
        "| `gmv` | orders_enriched | 订单商品金额合计 |",
        "| `freight_total` | orders_enriched | 订单运费合计 |",
        "| `item_value_total` | orders_enriched | 商品金额 + 运费 |",
        "| `payment_value_sum` | orders_enriched | 订单支付金额合计 |",
        "| `payment_diff` | orders_enriched | 支付金额 −（商品 + 运费） |",
        "| `payment_type_main` | orders_enriched | 订单第一笔支付方式 |",
        "| `review_score` | orders_enriched | 订单最新评价分数 |",
        "| `has_comment` | orders_enriched | 最新评价是否含文字 |",
        "",
        "## 四、质量统计",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 订单总数 | {len(orders):,} |",
        f"| 取消/不可用订单 | {invalid_orders:,} |",
        f"| 已送达订单 | {delivered:,} |",
        f"| 已送达但缺送达时间 | {missing_delivered:,} |",
        f"| 延迟送达订单（is_late=True） | {late_orders:,} |",
        f"| 有商品明细的订单 | {orders_with_items:,} |",
        f"| 无商品明细的订单 | {len(orders) - orders_with_items:,} |",
        f"| 订单级评价数 | {len(reviews_order):,} |",
        f"| 涉及多单的 review_id 记录 | {dup_review_orders:,} |",
        "",
        "## 五、输出文件",
        "",
        "| 文件 | 内容 |",
        "|---|---|",
        "| `data/clean/orders.csv` | 订单主表 + 时间派生指标 |",
        "| `data/clean/order_items.csv` | 商品明细 + 品类/体积 |",
        "| `data/clean/payments.csv` | 支付明细 |",
        "| `data/clean/reviews.csv` | 评价明细（保留重复 review_id） |",
        "| `data/clean/customers.csv` | 客户表 |",
        "| `data/clean/products.csv` | 商品表 + 英文品类 + 体积 |",
        "| `data/clean/sellers.csv` | 卖家表 |",
        "| `data/clean/geolocation.csv` | 邮编前缀级地理坐标 |",
        "| `data/clean/category_translation.csv` | 品类翻译表 |",
        "| `data/clean/orders_enriched.csv` | 订单级分析宽表 |",
        "| `data/clean/olist.db` | 上述表的 SQLite 版本（带索引） |",
        "",
        f"> 本报告由 `scripts/02_clean.py` 自动生成；随机种子 `RANDOM_SEED = {RANDOM_SEED}`。",
        "",
    ]
    return "\n".join(lines)


def orders_with_items_count(orders: pd.DataFrame) -> int:
    return int(orders["has_items"].sum())


def main() -> int:
    np.random.seed(RANDOM_SEED)

    print("=" * 60)
    print("02_clean.py —— 数据清洗与整合")
    print("=" * 60)
    print("读取原始数据 ...")
    raw = read_raw()

    print("清洗各表 ...")
    orders = clean_orders(raw["orders"])
    customers = clean_customers(raw["customers"])
    sellers = clean_sellers(raw["sellers"])
    products = clean_products(raw["products"], raw["category_translation"])
    order_items = clean_order_items(raw["order_items"], products)
    payments = clean_payments(raw["payments"])
    reviews, reviews_order = clean_reviews(raw["reviews"])
    geolocation = clean_geolocation(raw["geolocation"])
    category_translation = raw["category_translation"].copy()

    print("聚合与整合 ...")
    items_agg = aggregate_items(order_items)
    payments_agg = aggregate_payments(payments)
    orders_enriched = build_enriched(
        orders, items_agg, payments_agg, reviews_order, customers
    )
    orders = orders.merge(items_agg[["order_id", "item_count"]], on="order_id", how="left")
    orders["has_items"] = orders["item_count"].notna()

    clean_tables = {
        "orders": orders,
        "order_items": order_items,
        "payments": payments,
        "reviews": reviews,
        "customers": customers,
        "products": products,
        "sellers": sellers,
        "geolocation": geolocation,
        "category_translation": category_translation,
        "orders_enriched": orders_enriched,
    }

    print("导出 CSV ...")
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    export_csv(clean_tables)

    print("导出 SQLite ...")
    export_sqlite(clean_tables)

    print("生成清洗报告 ...")
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        build_report(
            raw, clean_tables, orders, reviews, reviews_order, products, geolocation
        ),
        encoding="utf-8",
    )
    summary_rows = [
        {
            "table": name,
            "raw_rows": len(raw[name]) if name in raw else np.nan,
            "clean_rows": len(df),
            "clean_cols": df.shape[1],
        }
        for name, df in clean_tables.items()
    ]
    pd.DataFrame(summary_rows).to_csv(
        TABLES_DIR / "cleaning_summary.csv", index=False, encoding="utf-8-sig"
    )

    print("\n" + "-" * 60)
    print(f"订单: {len(orders):,} | 有效订单: {int(orders['is_valid_order'].sum()):,} | "
          f"有商品明细: {int(orders['has_items'].sum()):,}")
    print(f"订单级宽表: {len(orders_enriched):,} 行 × {orders_enriched.shape[1]} 列")
    print(f"地理表: {len(raw['geolocation']):,} → {len(geolocation):,} 个邮编前缀")
    print(f"评估: 延迟订单 {int(orders['is_late'].fillna(False).sum()):,} | "
          f"平均配送 {orders['delivery_days'].mean():.1f} 天")
    print(f"SQLite: {DB_PATH}")
    print(f"报告: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
