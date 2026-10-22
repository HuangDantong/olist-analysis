# 数据清洗报告

- 生成时间：2026-10-22 10:00:22 中国标准时间
- 输入：`data/raw/olist/`（原始数据，未修改）
- 输出：`data/clean/*.csv` 与 `data/clean/olist.db`

## 一、行数变化

| 表 | 原始行数 | 清洗后行数 | 说明 |
|---|---:|---:|---|
| orders | 99,441 | 99,441 | 保留全部订单，新增派生字段 |
| order_items | 112,650 | 112,650 | 关联商品品类与体积 |
| payments | 103,886 | 103,886 | 类型规范化 |
| reviews | 99,224 | 99,224 | 保留全部评价，新增评论文本标记 |
| reviews（订单级） | — | 98,673 | 每单取最新一条评价 |
| customers | 99,441 | 99,441 | 邮编补零、城市/州规范化 |
| products | 32,951 | 32,951 | 品类翻译、尺寸缺失填充 |
| sellers | 3,095 | 3,095 | 邮编补零、城市/州规范化 |
| geolocation | 1,000,163 | 19,015 | 按邮编前缀聚合（经纬度中位数） |
| category_translation | 71 | 71 | 原样保留 |
| **orders_enriched** | — | 99,441 | 订单级宽表（订单 + 商品 + 支付 + 评价 + 客户） |

## 二、清洗规则

1. **时间字段**：5 个订单时间字段、发货截止时间、评价时间统一转为 datetime；无法解析的置为 NaT。
2. **邮编前缀**：按字符串读取并 `zfill(5)`，保留 `01037` 这类前导零。
3. **商品品类**：缺失品类标记为 `unknown`（610 个），并合并英文翻译表；无对应翻译的标记为 `unknown`（623 个）。
4. **商品尺寸**：重量/长/高/宽缺失时用该列中位数填充，并用 `has_dimensions` 标记原始记录是否完整（2 个商品存在缺失）。
5. **评价**：同一 `review_id` 可能对应多个订单（1,603 条评价涉及多单）；订单级分析取该订单最新一条评价，评价级分析保留全部记录。
6. **地理表**：同一邮编前缀的多条坐标取经纬度中位数，城市/州取第一条，并由 1,000,163 行压缩为 19,015 行。
7. **订单状态**：保留全部订单；新增 `is_valid_order` 标记，取消/不可用订单为 False。

## 三、派生指标

| 字段 | 所属表 | 含义 |
|---|---|---|
| `purchase_date` | orders | 下单日期 |
| `purchase_month` | orders | 下单月份（YYYY-MM） |
| `purchase_year` | orders | 下单年份 |
| `approval_hours` | orders | 下单到支付审核通过的小时数 |
| `delivery_days` | orders | 下单到实际送达的天数 |
| `estimated_days` | orders | 下单到承诺送达的天数 |
| `late_days` | orders | 超过承诺送达的天数（未延迟为 0） |
| `is_late` | orders | 是否延迟送达（缺时间时为 NA） |
| `is_valid_order` | orders | 是否非取消/非不可用订单 |
| `total_value` | order_items | `price + freight_value` |
| `product_volume_cm3` | products | 长 × 高 × 宽（cm³） |
| `item_count` | orders_enriched | 订单商品件数 |
| `seller_count` | orders_enriched | 订单涉及卖家数 |
| `product_count` | orders_enriched | 订单涉及商品数 |
| `gmv` | orders_enriched | 订单商品金额合计 |
| `freight_total` | orders_enriched | 订单运费合计 |
| `item_value_total` | orders_enriched | 商品金额 + 运费 |
| `payment_value_sum` | orders_enriched | 订单支付金额合计 |
| `payment_diff` | orders_enriched | 支付金额 −（商品 + 运费） |
| `payment_type_main` | orders_enriched | 订单第一笔支付方式 |
| `review_score` | orders_enriched | 订单最新评价分数 |
| `has_comment` | orders_enriched | 最新评价是否含文字 |

## 四、质量统计

| 指标 | 数值 |
|---|---:|
| 订单总数 | 99,441 |
| 取消/不可用订单 | 1,234 |
| 已送达订单 | 96,478 |
| 已送达但缺送达时间 | 8 |
| 延迟送达订单（is_late=True） | 7,827 |
| 有商品明细的订单 | 98,666 |
| 无商品明细的订单 | 775 |
| 订单级评价数 | 98,673 |
| 涉及多单的 review_id 记录 | 1,276 |

## 五、输出文件

| 文件 | 内容 |
|---|---|
| `data/clean/orders.csv` | 订单主表 + 时间派生指标 |
| `data/clean/order_items.csv` | 商品明细 + 品类/体积 |
| `data/clean/payments.csv` | 支付明细 |
| `data/clean/reviews.csv` | 评价明细（保留重复 review_id） |
| `data/clean/customers.csv` | 客户表 |
| `data/clean/products.csv` | 商品表 + 英文品类 + 体积 |
| `data/clean/sellers.csv` | 卖家表 |
| `data/clean/geolocation.csv` | 邮编前缀级地理坐标 |
| `data/clean/category_translation.csv` | 品类翻译表 |
| `data/clean/orders_enriched.csv` | 订单级分析宽表 |
| `data/clean/olist.db` | 上述表的 SQLite 版本（带索引） |

> 本报告由 `scripts/02_clean.py` 自动生成；随机种子 `RANDOM_SEED = 42`。
