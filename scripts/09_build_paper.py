# -*- coding: utf-8 -*-
"""
09_build_paper.py —— 论文导出 / 同步 / 重建

三种用法
--------
    python scripts/09_build_paper.py --pdf-only   # 在 Word 里改了内容或排版：保存 → 导出 PDF → 同步 docs/论文终稿.pdf
    python scripts/09_build_paper.py             # 改的是 08_write_paper.py：重新生成 Word → 导出 PDF → 同步
    python scripts/09_build_paper.py --force     # 确认要用脚本覆盖 Word 手工修改时使用

说明
----
- 一旦开始在 Word/WPS 里直接改内容，就把 docx 当作唯一源文件，之后只用 --pdf-only，
  不要再运行默认模式（08 脚本会按模板重新生成，覆盖 Word 手工修改）。
- --pdf-only 导出的是磁盘上最后一次保存的版本，运行前请先在 Word/WPS 中保存并关闭文件。
- 为避免文件被 Word/WPS 占用，--pdf-only 会先复制一份临时 docx 再导出。
- PDF 导出依赖本机 Microsoft Word（pywin32 调用）。
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts" / "08_write_paper.py"
PAPER_MD = ROOT / "docs" / "paper_draft.md"
PDF_DEST = ROOT / "docs" / "论文终稿.pdf"


def load_writer():
    spec = importlib.util.spec_from_file_location("paper_writer", WRITER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def export_pdf(docx_path: Path, *, copy_first: bool = False) -> Path:
    pdf_path = docx_path.with_suffix(".pdf")
    try:
        import win32com.client as win32
    except ImportError:
        print("未安装 pywin32，无法自动导出 PDF。\n"
              "请先运行：pip install pywin32\n"
              "或在 Word 中打开 docx，选择“另存为 → PDF”。", file=sys.stderr)
        raise SystemExit(1)

    temp_dir = None
    source = docx_path
    if copy_first:
        # 复制后导出，避免 Word/WPS 正在打开文件时被锁住
        temp_dir = Path(tempfile.mkdtemp(prefix="paper_export_"))
        source = temp_dir / docx_path.name
        try:
            shutil.copy2(docx_path, source)
        except OSError as exc:
            print(f"无法读取 docx：{exc}\n请先在 Word/WPS 中保存并关闭文件。", file=sys.stderr)
            raise SystemExit(1)

    word = win32.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    doc = None
    try:
        doc = word.Documents.Open(str(source), ReadOnly=True, AddToRecentFiles=False)
        pages = doc.ComputeStatistics(2)
        chars = doc.ComputeStatistics(3)
        doc.ExportAsFixedFormat(str(pdf_path), 17)  # wdExportFormatPDF
        print(f"已导出 PDF：{pdf_path}（{pages} 页，{chars} 字符）")
    except Exception as exc:
        print(f"PDF 导出失败：{exc}\n"
              "请确认文件已保存，且本机已安装 Microsoft Word。", file=sys.stderr)
        raise SystemExit(1)
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        word.Quit()
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)
    return pdf_path


def main() -> int:
    parser = argparse.ArgumentParser(description="导出论文 PDF 并同步到仓库 docs/")
    parser.add_argument("--pdf-only", action="store_true",
                        help="不重新生成 docx，只导出当前 docx（Word 手工改内容/排版后用这个）")
    parser.add_argument("--force", action="store_true",
                        help="确认用 08 脚本重新生成并覆盖 Word 手工修改")
    args = parser.parse_args()

    writer = load_writer()
    docx_path = Path(writer.OUT_DOCX)

    if not args.pdf_only:
        # 保护 Word 手工修改：docx 明显比 Markdown 新时，要求显式 --force
        if (not args.force and docx_path.is_file() and PAPER_MD.is_file()
                and docx_path.stat().st_mtime > PAPER_MD.stat().st_mtime + 5):
            print("检测到 docx 比 docs/paper_draft.md 新，可能包含 Word 手工修改。\n"
                  "默认模式会用 08 脚本重新生成并覆盖这些修改。\n"
                  "如果确实要覆盖，请加 --force；如果只想导出当前 Word，请用 --pdf-only。",
                  file=sys.stderr)
            return 2
        print("重新生成 Word 终稿与 Markdown …")
        result = subprocess.run([sys.executable, str(WRITER)], cwd=ROOT)
        if result.returncode != 0:
            return result.returncode
    else:
        print("导出当前 docx（请确认已在 Word/WPS 中保存）…")

    if not docx_path.is_file():
        print(f"找不到 docx：{docx_path}", file=sys.stderr)
        return 1

    pdf_path = export_pdf(docx_path, copy_first=args.pdf_only)
    PDF_DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf_path, PDF_DEST)
    print(f"已同步到仓库：{PDF_DEST}")
    print("下一步：git add -A && git commit -m \"更新论文\"")
    print("推送：git push ssh://git@ssh.github.com:443/HuangDantong/olist-analysis.git main")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
