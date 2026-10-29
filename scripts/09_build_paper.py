# -*- coding: utf-8 -*-
"""
09_build_paper.py —— 论文一键生成 / 导出 / 同步到仓库

用法
----
    python scripts/09_build_paper.py            # 改完 08_write_paper.py 后：重新生成 Word → 导出 PDF → 同步 docs/论文终稿.pdf
    python scripts/09_build_paper.py --pdf-only # 只在 Word 里改了排版：直接导出当前 docx → 同步 PDF

说明
----
- 论文正文的“唯一源文件”是 scripts/08_write_paper.py 里的 ABSTRACT、KEYWORDS、SECTIONS；
  直接改 Word 后如果又运行默认模式，手工修改会被覆盖。
- 只改字体、行距、图片位置等排版时，用 --pdf-only，避免覆盖 Word 里的手工调整。
- PDF 导出依赖本机安装的 Microsoft Word（通过 pywin32 调用）。
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts" / "08_write_paper.py"
PDF_DEST = ROOT / "docs" / "论文终稿.pdf"


def load_writer():
    spec = importlib.util.spec_from_file_location("paper_writer", WRITER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def export_pdf(docx_path: Path) -> Path:
    pdf_path = docx_path.with_suffix(".pdf")
    try:
        import win32com.client as win32
    except ImportError:
        print("未安装 pywin32，无法自动导出 PDF。\n"
              "请先运行：pip install pywin32\n"
              "或在 Word 中打开 docx，选择“另存为 → PDF”。", file=sys.stderr)
        raise SystemExit(1)

    word = win32.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    doc = None
    try:
        doc = word.Documents.Open(str(docx_path), ReadOnly=True, AddToRecentFiles=False)
        pages = doc.ComputeStatistics(2)
        chars = doc.ComputeStatistics(3)
        doc.ExportAsFixedFormat(str(pdf_path), 17)  # wdExportFormatPDF
        print(f"已导出 PDF：{pdf_path}（{pages} 页，{chars} 字符）")
    except Exception as exc:
        print(f"PDF 导出失败：{exc}\n"
              "请确认 docx 未在 Word 中打开，且本机已安装 Microsoft Word。", file=sys.stderr)
        raise SystemExit(1)
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        word.Quit()
    return pdf_path


def main() -> int:
    parser = argparse.ArgumentParser(description="生成论文终稿并同步 PDF 到仓库 docs/")
    parser.add_argument("--pdf-only", action="store_true",
                        help="跳过重新生成 docx，只把当前 docx 导出为 PDF（保留 Word 手工排版）")
    args = parser.parse_args()

    writer = load_writer()
    docx_path = Path(writer.OUT_DOCX)

    if not args.pdf_only:
        print("重新生成 Word 终稿与 Markdown …")
        result = subprocess.run([sys.executable, str(WRITER)], cwd=ROOT)
        if result.returncode != 0:
            return result.returncode
    elif not docx_path.is_file():
        print(f"找不到 docx：{docx_path}", file=sys.stderr)
        return 1

    if not docx_path.is_file():
        print(f"找不到 docx：{docx_path}", file=sys.stderr)
        return 1

    pdf_path = export_pdf(docx_path)
    PDF_DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf_path, PDF_DEST)
    print(f"已同步到仓库：{PDF_DEST}")
    print("下一步：git add -A && git commit -m \"更新论文\" && git push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
