# -*- coding: utf-8 -*-
"""
00_download.py —— 下载、校验并解压 Olist 巴西电商公开数据集

数据源
------
Kaggle: Brazilian E-Commerce Public Dataset by Olist
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

获取方式（白名单）
------------------
使用 Kaggle 官方数据集 API 下载公开数据集，不涉及网页爬虫。
该接口对公开数据集会返回 302，跳转到 Google Storage 的签名地址；
本脚本用标准库 urllib 直接跟随跳转，无需 Kaggle 账号或 API Token。

License
-------
CC BY-NC-SA 4.0：仅限非商业用途，需署名，并以相同方式共享。
本项目仅用于课程作业与学术研究，论文中已注明来源与许可。

用法
----
    python scripts/00_download.py             # 数据完整时自动跳过
    python scripts/00_download.py --force     # 强制重新下载
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

URL = "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
EXPECTED_SHA256 = "967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784"
EXPECTED_SIZE = 44_717_580

# 压缩包内应包含的 9 个 CSV；用于判断“是否已完整解压”
EXPECTED_FILES = {
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
}

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "data" / "raw" / "olist.zip"
DEFAULT_EXTRACT_DIR = ROOT / "data" / "raw" / "olist"


def sha256_of(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path) -> None:
    """流式下载并显示进度。先写 .part，成功后再改名，避免半截文件。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) olist-coursework/1.0",
            "Accept": "*/*",
        },
    )
    print(f"下载: {url}")
    with urllib.request.urlopen(req, timeout=60) as resp, part.open("wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        next_report = 10
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total:
                pct = done * 100 // total
                if pct >= next_report:
                    print(f"  {pct:3d}%  {done / 2**20:6.1f} / {total / 2**20:.1f} MB")
                    next_report = (pct // 10 + 1) * 10
    part.replace(dest)
    print(f"下载完成: {dest}  ({dest.stat().st_size / 2**20:.1f} MB)")


def safe_extract(zip_path: Path, target: Path) -> None:
    """解压并防止 Zip Slip（条目路径逃逸到目标目录之外）。"""
    target.mkdir(parents=True, exist_ok=True)
    target_resolved = target.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise RuntimeError(f"压缩包损坏，首个损坏条目: {bad}")
        for member in zf.infolist():
            if member.is_dir() or member.filename.startswith("__MACOSX/"):
                continue
            member_path = (target / member.filename).resolve()
            if os.path.commonpath([str(member_path), str(target_resolved)]) != str(target_resolved):
                raise RuntimeError(f"检测到非法解压路径，已中止: {member.filename}")
            member_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, member_path.open("wb") as dst:
                for chunk in iter(lambda: src.read(1 << 20), b""):
                    dst.write(chunk)
    print(f"解压完成: {target}")


def data_is_complete(extract_dir: Path) -> bool:
    return all((extract_dir / name).is_file() and (extract_dir / name).stat().st_size > 0
               for name in EXPECTED_FILES)


def main() -> int:
    parser = argparse.ArgumentParser(description="下载并校验 Olist 数据集")
    parser.add_argument("--url", default=URL, help="数据集下载地址")
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP, help="压缩包保存路径")
    parser.add_argument("--extract-dir", type=Path, default=DEFAULT_EXTRACT_DIR,
                        help="解压目录")
    parser.add_argument("--force", action="store_true", help="忽略已有数据，强制重新下载")
    args = parser.parse_args()

    zip_path: Path = args.zip
    extract_dir: Path = args.extract_dir

    if not args.force and data_is_complete(extract_dir):
        print(f"数据已存在且完整，跳过下载: {extract_dir}")
        return 0

    if args.force and zip_path.exists():
        zip_path.unlink()

    if not zip_path.exists():
        download(args.url, zip_path)

    actual_size = zip_path.stat().st_size
    if actual_size != EXPECTED_SIZE:
        print(f"警告: 文件大小 {actual_size} 与预期 {EXPECTED_SIZE} 不一致，仍继续校验 SHA256",
              file=sys.stderr)

    actual_hash = sha256_of(zip_path)
    if actual_hash != EXPECTED_SHA256:
        print("SHA256 校验失败！", file=sys.stderr)
        print(f"  预期: {EXPECTED_SHA256}", file=sys.stderr)
        print(f"  实际: {actual_hash}", file=sys.stderr)
        print("请删除压缩包后重试；若 Kaggle 已更新数据集，请同步更新脚本中的哈希。",
              file=sys.stderr)
        return 1
    print(f"SHA256 校验通过: {actual_hash}")

    safe_extract(zip_path, extract_dir)

    missing = sorted(EXPECTED_FILES - {p.name for p in extract_dir.glob("*.csv")})
    if missing:
        print(f"错误: 解压后缺少文件: {missing}", file=sys.stderr)
        return 1

    print(f"共 {len(EXPECTED_FILES)} 个 CSV，数据目录: {extract_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
