# -*- coding: utf-8 -*-
"""
run_all.py —— 一键复现流水线

按顺序执行 scripts/ 下的步骤；尚未完成的脚本会自动跳过并提示。
数据文件已存在时，00_download.py 会自动跳过下载。

用法
----
    python run_all.py
    python run_all.py --skip-download
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"

STEPS = [
    ("00_download.py", "下载并校验原始数据"),
    ("01_load.py", "数据导入与质量体检"),
    ("02_clean.py", "数据清洗与 SQLite 导出"),
    ("03_models.py", "商业分析模型"),
    ("04_visuals_templates.py", "教材模板复现（15 张）"),
    ("05_visuals_business.py", "真实数据业务图表"),
    ("07_paper_skeleton.py", "生成论文 Word 框架"),
]

RANDOM_SEED_NOTE = "所有随机过程统一使用 RANDOM_SEED = 42"


def main() -> int:
    parser = argparse.ArgumentParser(description="一键复现 Olist 分析流水线")
    parser.add_argument("--skip-download", action="store_true",
                        help="跳过 00_download.py（数据已就绪时使用）")
    args = parser.parse_args()

    print("=" * 64)
    print("Olist 商业数据分析 —— 一键复现")
    print(RANDOM_SEED_NOTE)
    print("=" * 64)

    ran = 0
    for filename, title in STEPS:
        if args.skip_download and filename == "00_download.py":
            print(f"\n[跳过] {filename}  {title}")
            continue

        script = SCRIPTS / filename
        if not script.is_file():
            print(f"\n[未实现] {filename}  {title}（脚本尚不存在，跳过）")
            continue

        print(f"\n{'=' * 64}\n[执行] {filename}  {title}\n{'=' * 64}", flush=True)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        result = subprocess.run([sys.executable, str(script)], cwd=ROOT, env=env)
        if result.returncode != 0:
            print(f"\n[失败] {filename} 退出码 {result.returncode}", file=sys.stderr)
            return result.returncode
        ran += 1

    print(f"\n{'=' * 64}")
    print(f"完成：实际执行 {ran} 个脚本。")
    print(f"图表输出：{ROOT / 'outputs' / 'figures'}")
    print(f"数据表输出：{ROOT / 'outputs' / 'tables'}")
    print("大屏启动：streamlit run scripts/06_dashboard.py")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
