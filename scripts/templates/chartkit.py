# -*- coding: utf-8 -*-
"""复刻第二章图表时反复用到的公共部件。

三件事：

1. **画布换算**——Excel 里的图表对象尺寸以 pt 计，导出 PNG 时是 2 px/pt，
   所以画布像素 = pt × 2；字号同步放大 1.44 倍（2 × 72 / 100）。
2. **读样式**——从 xlsx 里把 chartN.xml（绘图区、坐标轴、系列）和图表
   userShapes（标题、副标题、脚注、手工拖拽的标注框）解析成 Python 对象。
3. **量位置**——直接从 Excel 导出图上量文字/图形的墨迹范围，用来校准
   matplotlib 的落点。Excel 的文本行盒和 matplotlib 的基线规则不一样，
   靠算容易差几个像素，量一下最省事。
"""

import os
import re
import zipfile
from xml.etree import ElementTree as ET

import numpy as np
from matplotlib import font_manager
from PIL import Image

# --------------------------------------------------------------------------
# 换算常量
# --------------------------------------------------------------------------

DPI = 100
PX_PER_PT = 2.0                 # Excel 图表导出成 PNG 时的比例
FONT_SCALE = PX_PER_PT * 72 / DPI   # Excel 字号(9pt) -> matplotlib 字号(12.96pt)
BACKGROUND = "#1A1E43"          # 所有图表的图表区底色 srgbClr 1A1E43
EMU_PER_PT = 12700.0

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
C = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
CDR = "{http://schemas.openxmlformats.org/drawingml/2006/chartDrawing}"

DEFAULT_XLSX = (r"D:\大数据分析及数据可视化\《Excel数据可视化 - 从图表到数据大屏》"
                r"-清华-郭宏远\第二章 图表(前15).xlsx")
XLSX = os.environ.get("TEMPLATE_XLSX", DEFAULT_XLSX)

# --------------------------------------------------------------------------
# 字体
# --------------------------------------------------------------------------


def pick_font(candidates, fallback="DejaVu Sans"):
    """返回第一个本机已安装的字体名，缺失时退到 fallback。"""
    installed = {font.name for font in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in installed:
            return name
    return fallback


# 标题/副标题/脚注在 XML 里显式写死了「微软雅黑」
UI_FONT = pick_font(["Microsoft YaHei", "微软雅黑", "SimHei", "DengXian"])
# 坐标轴与数据标签：拉丁字形走主题字体 Calibri，中文回退到工作簿默认字体等线
AXIS_FONTS = [pick_font(["Calibri"]),
              pick_font(["DengXian", "等线", "SimSun", "Microsoft YaHei"])]


# --------------------------------------------------------------------------
# 读 workbook
# --------------------------------------------------------------------------


def _read(part):
    with zipfile.ZipFile(XLSX) as archive:
        return archive.read(part).decode("utf-8")


def chart_root(number):
    """返回 chartN.xml 的根节点（c:chartSpace）。"""
    return ET.fromstring(_read("xl/charts/chart%d.xml" % number))


def user_shapes(number):
    """解析图表的 userShapes，返回覆盖元素列表。

    只有一层的 cdr:sp / cdr:cxnSp，够用；标题、副标题、脚注、标注框都在这里。
    """
    rels = _read("xl/charts/_rels/chart%d.xml.rels" % number)
    match = re.search(r'Target="\.\./drawings/(drawing\d+\.xml)"', rels)
    if not match:
        return []
    root = ET.fromstring(_read("xl/drawings/" + match.group(1)))

    shapes = []
    for anchor in root:
        start, end = anchor.find(CDR + "from"), anchor.find(CDR + "to")
        box = None
        if start is not None and end is not None:
            box = (
                float(start.find(CDR + "x").text), float(start.find(CDR + "y").text),
                float(end.find(CDR + "x").text), float(end.find(CDR + "y").text),
            )
        for child in anchor:
            kind = child.tag.split("}")[-1]
            if kind not in ("sp", "pic", "cxnSp", "graphicFrame", "grpSp"):
                continue
            name_node = child.find(".//" + CDR + "cNvPr")
            sp_pr = child.find(CDR + "spPr")
            geom, offset, extent = None, None, None
            if sp_pr is not None:
                xfrm = sp_pr.find(A + "xfrm")
                if xfrm is not None:
                    off, ext = xfrm.find(A + "off"), xfrm.find(A + "ext")
                    if off is not None:
                        offset = (int(off.get("x")) / EMU_PER_PT,
                                  int(off.get("y")) / EMU_PER_PT)
                    if ext is not None:
                        extent = (int(ext.get("cx")) / EMU_PER_PT,
                                  int(ext.get("cy")) / EMU_PER_PT)
                node = sp_pr.find(A + "prstGeom")
                if node is not None:
                    geom = node.get("prst")
            shapes.append({
                "kind": kind,
                "name": name_node.get("name") if name_node is not None else "",
                "geom": geom,
                "rel": box,
                "offset_pt": offset,
                "extent_pt": extent,
                "fill": fill_of(sp_pr.find(A + "solidFill")) if sp_pr is not None else None,
                "line": line_of(sp_pr.find(A + "ln")) if sp_pr is not None else None,
                "paragraphs": paragraphs_of(child.find(CDR + "txBody")),
            })
    return shapes


def fill_of(node):
    """<a:solidFill> -> ('#RRGGBB', alpha)，取不到时返回 None。"""
    if node is None:
        return None
    srgb = node.find(A + "srgbClr")
    if srgb is not None:
        alpha = srgb.find(A + "alpha")
        return ("#" + srgb.get("val"),
                int(alpha.get("val")) / 100000.0 if alpha is not None else 1.0)
    scheme = node.find(A + "schemeClr")
    if scheme is not None:
        return ("scheme:" + scheme.get("val"), 1.0)
    return None


def line_of(node):
    """<a:ln> -> 线宽(pt) 与颜色，用于还原连接符。</a:ln>。"""
    if node is None:
        return None
    width = int(node.get("w")) / EMU_PER_PT if node.get("w") else None
    head = node.find(A + "headEnd")
    return {"width_pt": width, "fill": fill_of(node.find(A + "solidFill")),
            "head": head.get("type") if head is not None else None}


def paragraphs_of(tx_body):
    """把 txBody 拆成 [(文本, 字号pt, 粗体, 颜色, 字体)] 的段落列表。"""
    if tx_body is None:
        return []
    out = []
    for para in tx_body.findall(A + "p"):
        runs = []
        for run in list(para.findall(A + "r")) + list(para.findall(A + "fld")):
            rpr = run.find(A + "rPr")
            latin = rpr.find(A + "latin") if rpr is not None else None
            runs.append({
                "text": "".join(t.text or "" for t in run.iter(A + "t")),
                "size_pt": int(rpr.get("sz")) / 100 if (rpr is not None and rpr.get("sz")) else None,
                "bold": rpr is not None and rpr.get("b") == "1",
                "color": fill_of(rpr.find(A + "solidFill")) if rpr is not None else None,
                "face": latin.get("typeface") if latin is not None else None,
            })
        if runs:
            out.append(runs)
    return out


def manual_layout(number):
    """绘图区在图表区里的相对位置，取自 plotArea/layout/manualLayout。"""
    root = chart_root(number)
    plot = root.find(C + "chart").find(C + "plotArea")
    layout = plot.find(C + "layout")
    if layout is None:
        return None
    manual = layout.find(C + "manualLayout")
    if manual is None:
        return None
    return {child.tag.split("}")[-1]: child.get("val") for child in manual}


# --------------------------------------------------------------------------
# 画布
# --------------------------------------------------------------------------


def new_figure(width_px, height_px, facecolor=BACKGROUND):
    """建一个与 Excel 导出图同尺寸的画布（1 参考像素 = 1 输出像素）。"""
    import matplotlib.pyplot as plt
    figure = plt.figure(figsize=(width_px / DPI, height_px / DPI), dpi=DPI)
    figure.patch.set_facecolor(facecolor)
    return figure


def plot_area(figure, layout, height_px, dy_px=0.0):
    """按 manualLayout 加一个 axes，坐标用相对画布的比例。

    dy_px 是竖直微调：manualLayout 存的是小数坐标，Excel 渲染时取整到
    设备像素，实测往往要比标注值高半个像素，需要时由调用方传进来。
    """
    left = float(layout["x"])
    top = float(layout["y"])
    width = float(layout["w"])
    height = float(layout["h"])
    bottom = 1.0 - top - height - dy_px / height_px
    axis = figure.add_axes([left, bottom, width, height])
    axis.set_facecolor(BACKGROUND)
    return axis


def save(figure, name):
    """把图存到脚本所在目录，返回完整路径。"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    figure.savefig(path, dpi=200, facecolor=figure.get_facecolor())
    print("saved:", path)
    return path


def height_px_of(number):
    """Excel 里图表对象的高度(pt) × 2，即导出 PNG 的像素高。"""
    meta = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "reference", "chart%d_meta.txt" % number)
    with open(meta, encoding="utf-8") as handle:
        match = re.search(r"w=([\d.]+)pt h=([\d.]+)pt", handle.read())
    return int(round(float(match.group(2)) * PX_PER_PT))


# --------------------------------------------------------------------------
# 从导出图上量位置
# --------------------------------------------------------------------------


def as_array(image):
    """接受路径或 ndarray，返回 HxWx3 的 int 数组。"""
    if isinstance(image, str):
        return np.array(Image.open(image).convert("RGB")).astype(int)
    return np.asarray(image).astype(int)


def ink_bbox(image, top, bottom, left, right, brightness=250, background=BACKGROUND):
    """给定区域内「比底色亮」的像素的包围盒，用来对齐文字和图形。

    brightness 是 RGB 三通道之和的阈值：默认 250 意味着明显亮于
    #1A1E43（26+30+67=123）的像素才算墨迹。
    """
    array = as_array(image)
    sub = array[top:bottom, left:right]
    mask = sub.sum(2) > brightness
    rows = np.where(mask.sum(1) > 0)[0]
    cols = np.where(mask.sum(0) > 0)[0]
    if not len(rows) or not len(cols):
        return None
    return (top + int(rows.min()), top + int(rows.max()),
            left + int(cols.min()), left + int(cols.max()))


def band_rows(image, top, bottom, left, right, brightness=250, gap=3):
    """把区域内的墨迹按行切成若干条带，用于区分标题/副标题等多行文字。"""
    array = as_array(image)
    sub = array[top:bottom, left:right]
    mask = sub.sum(2) > brightness
    rows = np.where(mask.sum(1) > 0)[0]
    if not len(rows):
        return []
    bands, start, previous = [], rows[0], rows[0]
    for row in rows[1:]:
        if row > previous + gap:
            bands.append((top + int(start), top + int(previous)))
            start = row
        previous = row
    bands.append((top + int(start), top + int(previous)))
    return bands


def to_rgb(color):
    """'#1A1E43' -> (26, 30, 67)。"""
    color = color.lstrip("#")
    return np.array([int(color[i:i + 2], 16) for i in (0, 2, 4)])


def runs_in_row(array, row, background=BACKGROUND):
    """某一行的连续非底色区段 [(x0, x1, color)]，用来量柱宽、间距。"""
    array = as_array(array)
    background = to_rgb(background) if isinstance(background, str) else np.array(background)
    out, start = [], None
    for x in range(array.shape[1]):
        differs = not np.array_equal(array[row, x], background)
        if differs and start is None:
            start = x
        elif not differs and start is not None:
            out.append((start, x - 1, tuple(array[row, (start + x - 1) // 2])))
            start = None
    if start is not None:
        out.append((start, array.shape[1] - 1,
                    tuple(array[row, (start + array.shape[1] - 1) // 2])))
    return out
