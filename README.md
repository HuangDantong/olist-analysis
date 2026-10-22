# Olist 巴西电商商业数据分析

> 嘉兴大学 数据科学学院《商业数据分析》期末大作业
>
> 从真实数据获取 → 清洗治理 → 商业模型 → 图表复现与业务可视化 → 交互式大屏 → 商业洞察

## 项目简介

本项目基于 Kaggle 公开数据集 **Brazilian E-Commerce Public Dataset by Olist**，完成一套端到端的商业数据分析：

- **数据**：9 张关联表，99,441 个订单、112,650 条商品明细，2016-09 ～ 2018-10；
- **模型**：RFM 客户分层、同期群留存、ABC/Pareto、波士顿矩阵、SARIMA 销售预测；
- **可视化**：教材前 15 套模板复现 + 10 张真实业务图表；
- **大屏**：Streamlit 交互式看板，支持日期、州、品类、订单状态联动筛选；
- **论文**：`docs/paper_outline.md`（框架）+ `docs/paper_draft.md`（正文初稿）+ `docs/论文框架.docx`（Word 骨架）；`scripts/08_write_paper.py` 可按学校模板生成 Word 初稿。

## 快速开始

```bash
# 1. 安装依赖（国内建议使用清华镜像）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 一键跑通数据、模型与图表（数据已存在时自动跳过下载）
python run_all.py

# 3. 启动交互式大屏
streamlit run scripts/06_dashboard.py
# 浏览器打开 http://localhost:8501
```

单独运行各步骤：

```bash
python scripts/00_download.py          # 下载 + SHA256 校验 + 安全解压
python scripts/01_load.py              # 数据导入与质量体检
python scripts/02_clean.py             # 清洗、指标派生、SQLite 导出
python scripts/03_models.py            # RFM / 同期群 / ABC / 波士顿 / SARIMA
python scripts/04_visuals_templates.py # 教材模板复现 15 张
python scripts/05_visuals_business.py  # 10 张真实业务图表
python scripts/06_dashboard.py         # Streamlit 大屏（需用 streamlit run）
python scripts/07_paper_skeleton.py    # 生成 docs/论文框架.docx
python scripts/08_write_paper.py       # 按学校模板生成论文初稿（Word + Markdown）
```

## 成果预览

| 成果 | 位置 |
|---|---|
| 数据体检报告 | `docs/data_profile.md` |
| 清洗报告 | `docs/cleaning_report.md` |
| 模型报告 | `docs/models_report.md` |
| 论文框架 | `docs/paper_outline.md`、`docs/论文框架.docx` |
| 论文正文初稿 | `docs/paper_draft.md`；Word 版由 `scripts/08_write_paper.py` 在本地生成，不随仓库提交 |
| 教材模板图（15 张） | `outputs/figures/templates/`；索引 `docs/template_charts.md` |
| 业务图（10 张） | `outputs/figures/business/` |
| 大屏截图 | `outputs/figures/dashboard_preview.png`、`dashboard_tab1—4.png` |
| 模型结果表 | `outputs/tables/` |
| SQLite 数据库 | `data/clean/olist.db`（git 忽略） |

## 论文

- 写作框架：`docs/paper_outline.md`
- 正文初稿（Markdown）：`docs/paper_draft.md`
- Word 初稿：由 `scripts/08_write_paper.py` 在本地生成，默认输出到 `../大作业/Olist商业数据分析_论文初稿.docx`，不随仓库提交
- 重新生成：`python scripts/08_write_paper.py`
- 自定义学校模板/输出路径：
  ```bash
  PAPER_TEMPLATE="D:/path/to/模板.docx" PAPER_OUT="D:/path/to/论文初稿.docx" python scripts/08_write_paper.py
  ```

## 目录结构

```
olist-analysis/
├─ data/
│  ├─ raw/                  # 原始 CSV（git 忽略，由 00_download.py 获取）
│  └─ clean/                # 清洗后 CSV 与 SQLite（git 忽略）
├─ scripts/
│  ├─ 00_download.py        # 下载 + SHA256 校验 + 安全解压
│  ├─ 01_load.py            # 导入、字段概览、主外键检查
│  ├─ 02_clean.py           # 清洗、类型统一、指标派生、SQLite 导出
│  ├─ 03_models.py          # RFM / 同期群 / ABC / 波士顿 / SARIMA
│  ├─ 04_visuals_templates.py   # 教材模板复现 15 张
│  ├─ 05_visuals_business.py    # 10 张真实业务图表
│  ├─ 06_dashboard.py       # Streamlit 交互式大屏
│  ├─ 07_paper_skeleton.py  # 生成论文 Word 框架
│  ├─ 08_write_paper.py     # 按学校模板生成论文初稿
│  ├─ viz_style.py          # matplotlib / Plotly 统一配色与样式
│  └─ templates/            # 15 张模板渲染脚本与高度 meta
├─ outputs/
│  ├─ figures/
│  │  ├─ templates/         # fig01—fig15
│  │  ├─ business/          # fig16—fig25
│  │  └─ dashboard_*.png    # 大屏截图
│  └─ tables/               # 模型结果 CSV
├─ docs/
│  ├─ data_source.md        # 数据源、许可、字段字典
│  ├─ data_profile.md       # 数据体检报告（自动生成）
│  ├─ cleaning_report.md    # 清洗报告（自动生成）
│  ├─ models_report.md      # 模型报告（自动生成）
│  ├─ template_charts.md    # 模板图索引（自动生成）
│  ├─ template_plan.md      # 30 个模板清单与复现方案
│  ├─ paper_outline.md      # 论文框架与写作要点
│  ├─ paper_draft.md        # 论文正文初稿（Markdown）
│  └─ 论文框架.docx         # Word 骨架
├─ requirements.txt
├─ run_all.py
└─ README.md
```

## 数据源与合规

| 项目 | 内容 |
|---|---|
| 数据集 | Brazilian E-Commerce Public Dataset by Olist |
| 主页 | https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce |
| 获取方式 | Kaggle 官方数据集 API（官方下载，非爬虫） |
| License | CC BY-NC-SA 4.0（非商业、署名、相同方式共享） |
| 校验 | SHA256 `967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784` |

详见 [`docs/data_source.md`](docs/data_source.md)。

> 原始数据不提交到仓库：一方面体积较大，另一方面需遵守数据许可。任何人克隆仓库后运行 `python scripts/00_download.py` 即可复现。

## 可视化与大屏

- **模板复现（15 张）**：教材第二章前 15 套——渐变柱形、带均值柱形、渐变圆角、标注柱形、层叠柱形、蝴蝶图、REPT 蝴蝶、数值百分比、对比柱形、甘特图、平滑折线、菱形走势、对比折线、单值圆环、水球图；全部 matplotlib 生成，200 dpi。
- **业务图表**：fig16 月度 GMV 与预测、fig17 RFM 分层、fig18 同期群留存、fig19 ABC/Pareto、fig20 波士顿矩阵、fig21 品类 Top 15、fig22 配送延迟与评分、fig23 支付方式、fig24 RFM 气泡散点、fig25 订单转化漏斗。
- **大屏**：KPI 行（GMV / 订单 / 客户 / 客单价 / 延迟率）+ 4 个页签（经营总览、客户与留存、品类与预测、数据明细）+ 侧边栏筛选联动。
- **配色**：业务图使用通过 CVD / 对比度校验的 8 色分类色板与单一蓝色顺序色阶。

## 作业可视化要求对照

| 要求 | 本项目 |
|---|---|
| 模板复现类 ≥10 种 | **15 张**：教材第二章前 15 套模板，覆盖柱形、蝴蝶、甘特、圆环、水球等类型 |
| 业务模型类 ≥6 张 | 10 张；其中模型类 7 张（RFM 分层 + RFM 气泡、同期群、ABC/Pareto、波士顿、SARIMA、订单漏斗），另有 3 张描述性业务图 |
| 交互式大屏 ≥1 个、≥6 个联动组件 | Streamlit 大屏：5 个 KPI、4 个页签、日期/州/品类/状态筛选联动、明细表与 CSV 下载 |
| 全部由 Python 生成 | matplotlib / Plotly / Streamlit；未使用 Power BI、Tableau、Fine BI 或 Excel 图表截图 |
| 中文、坐标轴、单位、配色、≥150 dpi、统一命名 | 中文字体；模板图与业务图均 200 dpi；命名 `figNN_描述.png` |
| 交互增强 | 悬停提示、缩放、联动筛选、明细下钻、暗色模板原色 |

## 复现规范

- Python 3.11+（开发环境 3.13.1；当前依赖在 pandas 3.0.6 下验证通过）；
- 所有随机过程固定随机种子（`RANDOM_SEED = 42`）；
- 图表统一 200 dpi、中文字体（微软雅黑 / 等线）、文件名 `figNN_描述.png`；
- 每个脚本可独立运行，路径基于仓库根目录解析，不依赖当前工作目录；
- 数据获取日期、字段口径、过滤规则均写入 `docs/`；
- 大屏中 RFM、同期群、波士顿矩阵、SARIMA 为离线全量结果，不随筛选变化，页面已注明；
- 教材模板复现需要教材 xlsx，可用 `TEMPLATE_XLSX="D:/path/to/第二章 图表(前15).xlsx"` 指定；论文生成用 `PAPER_TEMPLATE`、`PAPER_OUT` 指定模板和输出路径。

## 进度

- [x] 数据源可行性验证与许可确认
- [x] 仓库骨架、依赖清单、数据下载脚本
- [x] `01_load.py` 数据导入与质量体检
- [x] `02_clean.py` 数据清洗与 SQLite 导出
- [x] `03_models.py` 五个商业分析模型
- [x] 教材模板复现 15 张（第二章前 15 套）
- [x] 10 张真实数据业务图表
- [x] Streamlit 交互式大屏（≥ 6 组件）
- [x] 论文框架（Markdown + Word 骨架）
- [x] 论文正文初稿（3,866 字，含图表、参考文献与 AI 披露）
- [ ] 论文定稿与最终排版校对（补专业班级/学号/仓库链接）
- [ ] 最终公开仓库检查与提交

## 说明

模板复现使用教材配套案例数据；业务图表与模型使用 Olist 数据。两类图表在论文中分别标注。
