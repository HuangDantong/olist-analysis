# -*- coding: utf-8 -*-
"""
01_load.py —— 数据导入、结构概览与质量体检

做的事情
--------
1. 读取 data/raw/olist 下的 9 张 CSV；
2. 逐表统计行数、列数、字段类型、缺失率、唯一值、样例值；
3. 校验主键唯一性与外键命中率；
4. 输出业务规模速览（订单量、GMV、时间跨度、客户数等）；
5. 生成 docs/data_profile.md 与 outputs/tables/data_profile.csv。

不做的事情
----------
本脚本只读原始数据，不做任何清洗或覆盖写回。

用法
----
    python scripts/01_load.py
    python scripts/01_load.py --raw-dir data/raw/olist --out docs/data_profile.md
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_DIR = ROOT / "data" / "raw" / "olist"
DEFAULT_REPORT = ROOT / "docs" / "data_profile.md"
DEFAULT_CSV = ROOT / "outputs" / "tables" / "data_profile.csv"

# 读取顺序：先小表后大表，便于控制台逐行输出
TABLE_FILES = [
    ("orders", "olist_orders_dataset.csv"),
    ("order_items", "olist_order_items_dataset.csv"),
    ("payments", "olist_order_payments_dataset.csv"),
    ("reviews", "olist_order_reviews_dataset.csv"),
    ("customers", "olist_customers_dataset.csv"),
    ("products", "olist_products_dataset.csv"),
    ("sellers", "olist_sellers_dataset.csv"),
    ("category_translation", "product_category_name_translation.csv"),
    ("geolocation", "olist_geolocation_dataset.csv"),
]

# 邮编前缀必须按字符串读取，否则 "01037" 会被解析成 1037，丢失前导零
DTYPES = {
    "customers": {"customer_zip_code_prefix": "string"},
    "sellers": {"seller_zip_code_prefix": "string"},
    "geolocation": {"geolocation_zip_code_prefix": "string"},
}

DATE_COLUMNS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}

PRIMARY_KEYS = {
    "orders": ["order_id"],
    "order_items": ["order_id", "order_item_id"],
    "payments": ["order_id", "payment_sequential"],
    "reviews": ["review_id"],
    "customers": ["customer_id"],
    "products": ["product_id"],
    "sellers": ["seller_id"],
    "category_translation": ["product_category_name"],
    # geolocation 没有唯一主键：邮编前缀会重复出现
}

FOREIGN_KEYS = [
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("order_items", "seller_id", "sellers", "seller_id"),
    ("payments", "order_id", "orders", "order_id"),
    ("reviews", "order_id", "orders", "order_id"),
    ("products", "product_category_name", "category_translation", "product_category_name"),
]

MAIN_TABLE = "orders"
MIN_MAIN_ROWS = 500


def load_tables(raw_dir: Path) -> dict[str, pd.DataFrame]:
    """按 TABLE_FILES 读取全部 CSV，返回 {表名: DataFrame}。"""
    missing = [f for _, f in TABLE_FILES if not (raw_dir / f).is_file()]
    if missing:
        raise SystemExit(
            f"原始数据不完整，缺少: {missing}\n"
            f"请先运行: python scripts/00_download.py"
        )
    tables: dict[str, pd.DataFrame] = {}
    for name, filename in TABLE_FILES:
        path = raw_dir / filename
        tables[name] = pd.read_csv(path, dtype=DTYPES.get(name, {}))
        print(f"  读取 {name:20s} {len(tables[name]):>9,d} 行  ({path.name})")
    return tables


def _fmt_value(value: object, max_len: int = 36) -> str:
    text = "" if pd.isna(value) else str(value)
    text = text.replace("\r", " ").replace("\n", " ").replace("|", "\\|").strip()
    return text[:max_len] + ("…" if len(text) > max_len else "")


def _mask(text: str) -> str:
    return text.replace("|", "\\|")


def profile_tables(tables: dict[str, pd.DataFrame]) -> tuple[list[dict], dict]:
    """逐表、逐字段统计；返回 (列级统计行, 表级汇总)。"""
    column_rows: list[dict] = []
    table_summary: dict[str, dict] = {}

    for name, _ in TABLE_FILES:
        df = tables[name]
        rows = len(df)
        total_cells = rows * len(df.columns)
        missing_cells = int(df.isna().sum().sum())
        duplicate_rows = int(df.duplicated().sum())

        pk = PRIMARY_KEYS.get(name)
        pk_duplicates = int(df.duplicated(subset=pk).sum()) if pk else None
        pk_nulls = int(df[pk].isna().any(axis=1).sum()) if pk else None

        table_summary[name] = {
            "rows": rows,
            "cols": len(df.columns),
            "memory_mb": df.memory_usage(deep=True).sum() / 2**20,
            "missing_cells": missing_cells,
            "missing_rate": (missing_cells / total_cells * 100) if total_cells else 0.0,
            "duplicate_rows": duplicate_rows,
            "pk": pk,
            "pk_duplicates": pk_duplicates,
            "pk_nulls": pk_nulls,
        }

        for col in df.columns:
            series = df[col]
            non_null = int(series.notna().sum())
            row = {
                "table": name,
                "column": col,
                "dtype": str(series.dtype),
                "rows": rows,
                "non_null": non_null,
                "missing": rows - non_null,
                "missing_rate": ((rows - non_null) / rows * 100) if rows else 0.0,
                "unique": int(series.nunique(dropna=True)),
                "sample": " / ".join(
                    _fmt_value(v) for v in series.dropna().drop_duplicates().head(3)
                ),
                "date_min": "",
                "date_max": "",
                "date_parse_failures": "",
            }

            if col in DATE_COLUMNS.get(name, []):
                parsed = pd.to_datetime(series, errors="coerce")
                failures = int(series.notna().sum() - parsed.notna().sum())
                row["date_min"] = parsed.min().strftime("%Y-%m-%d %H:%M:%S") if parsed.notna().any() else ""
                row["date_max"] = parsed.max().strftime("%Y-%m-%d %H:%M:%S") if parsed.notna().any() else ""
                row["date_parse_failures"] = failures

            column_rows.append(row)

    return column_rows, table_summary


def check_foreign_keys(tables: dict[str, pd.DataFrame]) -> list[dict]:
    """计算每个外键的命中率（父表键集合按非空值构建）。"""
    results = []
    for child, child_col, parent, parent_col in FOREIGN_KEYS:
        source = tables[child][child_col]
        parent_values = set(tables[parent][parent_col].dropna())
        non_null = source.dropna()
        hits = int(non_null.isin(parent_values).sum())
        misses = int(len(non_null) - hits)
        results.append({
            "child": child,
            "child_col": child_col,
            "parent": parent,
            "parent_col": parent_col,
            "checked": int(len(non_null)),
            "hits": hits,
            "misses": misses,
            "hit_rate": (hits / len(non_null) * 100) if len(non_null) else 0.0,
        })
    return results


def business_summary(tables: dict[str, pd.DataFrame]) -> dict:
    """业务规模速览，供报告开头引用。"""
    orders = tables["orders"]
    items = tables["order_items"]
    customers = tables["customers"]
    reviews = tables["reviews"]

    purchase = pd.to_datetime(orders["order_purchase_timestamp"], errors="coerce")
    delivered = pd.to_datetime(orders["order_delivered_customer_date"], errors="coerce")

    return {
        "orders": len(orders),
        "delivered": int((orders["order_status"] == "delivered").sum()),
        "canceled": int((orders["order_status"] == "canceled").sum()),
        "unavailable": int((orders["order_status"] == "unavailable").sum()),
        "purchase_min": purchase.min().strftime("%Y-%m-%d") if purchase.notna().any() else "",
        "purchase_max": purchase.max().strftime("%Y-%m-%d") if purchase.notna().any() else "",
        "items_rows": len(items),
        "items_orders": int(items["order_id"].nunique()),
        "products": int(items["product_id"].nunique()),
        "sellers": int(items["seller_id"].nunique()),
        "gmv": float(items["price"].sum()),
        "freight": float(items["freight_value"].sum()),
        "customers": len(customers),
        "unique_customers": int(customers["customer_unique_id"].nunique()),
        "reviews": len(reviews),
        "avg_review_score": float(reviews["review_score"].mean()),
        "delivered_date_missing": int(delivered.isna().sum()),
        "orders_without_items": len(set(orders["order_id"]) - set(items["order_id"])),
    }


def build_markdown(
    column_rows: list[dict],
    table_summary: dict[str, dict],
    fk_rows: list[dict],
    summary: dict,
    raw_dir: Path,
) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines: list[str] = [
        "# Olist 数据概览与质量体检",
        "",
        f"- 生成时间：{now}",
        f"- 数据目录：`{raw_dir}`",
        f"- 主表：`{MAIN_TABLE}`，**{summary['orders']:,} 行**"
        f"（作业要求 ≥ {MIN_MAIN_ROWS:,} 行：{'✅ 满足' if summary['orders'] >= MIN_MAIN_ROWS else '❌ 不满足'}）",
        "",
        "## 一、业务规模速览",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 订单数 | {summary['orders']:,} |",
        f"| 已送达订单 | {summary['delivered']:,} |",
        f"| 取消订单 | {summary['canceled']:,} |",
        f"| 不可用订单 | {summary['unavailable']:,} |",
        f"| 下单时间范围 | {summary['purchase_min']} ～ {summary['purchase_max']} |",
        f"| 商品明细行数 | {summary['items_rows']:,} |",
        f"| 有商品明细的订单 | {summary['items_orders']:,} |",
        f"| 无商品明细的订单 | {summary['orders_without_items']:,} |",
        f"| 商品数 | {summary['products']:,} |",
        f"| 卖家数 | {summary['sellers']:,} |",
        f"| GMV（商品价格合计） | R$ {summary['gmv']:,.2f} |",
        f"| 运费合计 | R$ {summary['freight']:,.2f} |",
        f"| 客户数（customer_id） | {summary['customers']:,} |",
        f"| 去重客户数（customer_unique_id） | {summary['unique_customers']:,} |",
        f"| 评论数 | {summary['reviews']:,} |",
        f"| 平均评分 | {summary['avg_review_score']:.2f} / 5 |",
        f"| 已送达但缺送达时间 | {summary['delivered_date_missing']:,} |",
        "",
        "## 二、表级汇总",
        "",
        "| 表 | 行数 | 列数 | 内存 (MB) | 缺失单元格 | 缺失率 | 全行重复 | 主键 | 主键重复 | 主键为空 |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|",
    ]

    for name, _ in TABLE_FILES:
        info = table_summary[name]
        pk = " + ".join(info["pk"]) if info["pk"] else "—（无唯一键）"
        pk_dup = f"{info['pk_duplicates']:,}" if info["pk_duplicates"] is not None else "—"
        pk_null = f"{info['pk_nulls']:,}" if info["pk_nulls"] is not None else "—"
        lines.append(
            f"| `{name}` | {info['rows']:,} | {info['cols']} | {info['memory_mb']:.1f} | "
            f"{info['missing_cells']:,} | {info['missing_rate']:.2f}% | "
            f"{info['duplicate_rows']:,} | {pk} | {pk_dup} | {pk_null} |"
        )

    lines += [
        "",
        "## 三、外键完整性",
        "",
        "| 子表.字段 | 父表.字段 | 检查行数 | 命中 | 未命中 | 命中率 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for fk in fk_rows:
        lines.append(
            f"| `{fk['child']}.{fk['child_col']}` | `{fk['parent']}.{fk['parent_col']}` | "
            f"{fk['checked']:,} | {fk['hits']:,} | {fk['misses']:,} | {fk['hit_rate']:.2f}% |"
        )

    lines += ["", "## 四、字段明细", ""]
    for name, _ in TABLE_FILES:
        info = table_summary[name]
        lines += [
            f"### `{name}`（{info['rows']:,} 行 × {info['cols']} 列）",
            "",
            "| 字段 | 类型 | 非空 | 缺失率 | 唯一值 | 样例值 | 最早 | 最晚 |",
            "|---|---|---:|---:|---:|---|---|---|---|",
        ]
        for row in (r for r in column_rows if r["table"] == name):
            lines.append(
                f"| `{row['column']}` | {row['dtype']} | {row['non_null']:,} | "
                f"{row['missing_rate']:.2f}% | {row['unique']:,} | {row['sample']} | "
                f"{row['date_min']} | {row['date_max']} |"
            )
        lines.append("")

    lines += [
        "## 五、体检结论与清洗关注点",
        "",
        f"1. 主表 `orders` 共 {summary['orders']:,} 行，满足作业“主表 ≥ {MIN_MAIN_ROWS} 行”的要求。",
        f"2. 外键命中率见第三节；`order_items` 与 `orders` 的关联覆盖 "
        f"{summary['items_orders']:,} / {summary['orders']:,} 个订单。",
        f"3. {summary['orders_without_items']:,} 个订单没有商品明细，多为取消/不可用订单，建模时需明确过滤规则。",
        f"4. {summary['delivered_date_missing']:,} 个订单缺少实际送达时间，计算配送时长时要单独处理。",
        "5. 品类名为葡萄牙语，需通过 `product_category_name_translation` 映射为英文。",
        "6. `geolocation` 无唯一主键，邮编前缀会重复；地理分析前需按邮编前缀聚合去重。",
        "7. 评论表 `review_id` 需校验唯一性；若存在一单多评，按订单聚合时要去重。",
        "",
        f"> 本报告由 `scripts/01_load.py` 自动生成，数据未做任何修改。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Olist 数据导入与质量体检")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--csv-out", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    print("=" * 60)
    print("01_load.py —— 读取原始数据")
    print("=" * 60)
    tables = load_tables(args.raw_dir)

    print("\n统计字段与质量指标 ...")
    column_rows, table_summary = profile_tables(tables)
    fk_rows = check_foreign_keys(tables)
    summary = business_summary(tables)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.csv_out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        build_markdown(column_rows, table_summary, fk_rows, summary, args.raw_dir),
        encoding="utf-8",
    )
    pd.DataFrame(column_rows).to_csv(args.csv_out, index=False, encoding="utf-8-sig")

    print("\n" + "-" * 60)
    print(f"主表 orders: {summary['orders']:,} 行 "
          f"({'满足' if summary['orders'] >= MIN_MAIN_ROWS else '不满足'} ≥ {MIN_MAIN_ROWS})")
    print(f"GMV: R$ {summary['gmv']:,.2f} | 客户: {summary['unique_customers']:,} | "
          f"商品: {summary['products']:,} | 卖家: {summary['sellers']:,}")
    print(f"时间范围: {summary['purchase_min']} ～ {summary['purchase_max']}")
    worst = min(fk_rows, key=lambda r: r["hit_rate"])
    print(f"最低外键命中率: {worst['child']}.{worst['child_col']} -> "
          f"{worst['parent']}.{worst['parent_col']} = {worst['hit_rate']:.2f}%")
    print("-" * 60)
    print(f"报告: {args.out}")
    print(f"字段统计: {args.csv_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
