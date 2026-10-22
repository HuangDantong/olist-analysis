# 数据源说明与合规声明

## 1. 基本信息

| 项目 | 内容 |
|---|---|
| 数据集名称 | Brazilian E-Commerce Public Dataset by Olist |
| 中文名称 | Olist 巴西电商公开数据集 |
| 平台 | Kaggle |
| 数据集主页 | https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce |
| 数据提供方 | Olist（巴西电商平台） |
| 获取日期 | 2026-10-19 |
| 数据规模 | 9 张表、99,441 个订单、112,650 条商品明细、约 120 MB（解压后） |
| 时间范围 | 2016-09-04 ～ 2018-10-17 |
| 语言 | 葡萄牙语（附英文品类翻译表） |
| License | **CC BY-NC-SA 4.0** |

## 2. 合规获取方式（白名单）

本项目使用 **Kaggle 官方数据集 API** 获取数据，属于作业允许的“官方下载文件 / 官方数据接口”方式：

```
https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce
```

- 该接口是 Kaggle 官方 API，对公开数据集返回 302 跳转至 Google Storage 的签名下载地址；
- 全程使用标准库 `urllib` 跟随跳转，**没有编写或使用任何网页爬虫**；
- 本次获取时无需登录 Kaggle 账号，也未使用任何非公开接口；
- 下载脚本：`scripts/00_download.py`，内置文件大小与 SHA256 校验。

### 文件校验

| 项目 | 值 |
|---|---|
| 压缩包大小 | 44,717,580 字节（约 42.6 MB） |
| SHA256 | `967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784` |

## 3. 许可与使用声明

该数据集采用 **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International（CC BY-NC-SA 4.0）** 许可：

- **署名（BY）**：使用时应注明数据来源为 Olist / Kaggle；
- **非商业（NC）**：仅用于课程作业、学术研究与教学演示，不得用于商业用途；
- **相同方式共享（SA）**：对数据的衍生作品需以相同许可共享。

本项目仅用于嘉兴大学数据科学学院《商业数据分析》期末大作业，属于非商业学术用途。原始数据文件不提交到公开仓库，仓库仅保留下载脚本与校验信息，以控制体积并尊重数据许可。

## 4. 数据表结构

| 表名 | 文件 | 行数 | 粒度 | 主键 |
|---|---|---:|---|---|
| orders | `olist_orders_dataset.csv` | 99,441 | 一行一个订单 | `order_id` |
| order_items | `olist_order_items_dataset.csv` | 112,650 | 一行一个订单商品 | `order_id` + `order_item_id` |
| payments | `olist_order_payments_dataset.csv` | 103,886 | 一行一笔支付 | `order_id` + `payment_sequential` |
| reviews | `olist_order_reviews_dataset.csv` | 99,224 | 一行一条评价 | `review_id`（需校验） |
| customers | `olist_customers_dataset.csv` | 99,441 | 一行一个订单客户 | `customer_id` |
| products | `olist_products_dataset.csv` | 32,951 | 一行一个商品 | `product_id` |
| sellers | `olist_sellers_dataset.csv` | 3,095 | 一行一个卖家 | `seller_id` |
| geolocation | `olist_geolocation_dataset.csv` | 1,000,163 | 一行一个邮编坐标 | 无（邮编前缀可重复） |
| category_translation | `product_category_name_translation.csv` | 71 | 一行一个品类翻译 | `product_category_name` |

### 主外键关系

```
customers 1 ──── N orders 1 ──── N order_items N ──── 1 products
                              │                └────── 1 sellers
                              ├──── N payments
                              └──── N reviews

products.product_category_name ──── category_translation.product_category_name
customers.customer_zip_code_prefix ─┐
sellers.seller_zip_code_prefix ─────┴── geolocation.geolocation_zip_code_prefix（多对多）
```

## 5. 字段字典

### orders（订单主表）

| 字段 | 类型 | 含义 |
|---|---|---|
| `order_id` | string | 订单唯一标识 |
| `customer_id` | string | 订单级客户标识，关联 `customers.customer_id` |
| `order_status` | string | 订单状态：delivered / shipped / canceled / unavailable 等 |
| `order_purchase_timestamp` | datetime | 下单时间 |
| `order_approved_at` | datetime | 支付审核通过时间 |
| `order_delivered_carrier_date` | datetime | 交付承运商时间 |
| `order_delivered_customer_date` | datetime | 实际送达客户时间 |
| `order_estimated_delivery_date` | datetime | 平台承诺送达时间 |

### order_items（订单商品明细）

| 字段 | 类型 | 含义 |
|---|---|---|
| `order_id` | string | 订单标识 |
| `order_item_id` | int | 同一订单内的商品序号 |
| `product_id` | string | 商品标识 |
| `seller_id` | string | 卖家标识 |
| `shipping_limit_date` | datetime | 卖家发货截止时间 |
| `price` | float | 商品单价（BRL） |
| `freight_value` | float | 运费（BRL） |

### payments（支付）

| 字段 | 类型 | 含义 |
|---|---|---|
| `order_id` | string | 订单标识 |
| `payment_sequential` | int | 同一订单的支付序号 |
| `payment_type` | string | 支付方式：credit_card / boleto / voucher / debit_card |
| `payment_installments` | int | 分期数 |
| `payment_value` | float | 支付金额（BRL） |

### reviews（评价）

| 字段 | 类型 | 含义 |
|---|---|---|
| `review_id` | string | 评价标识 |
| `order_id` | string | 订单标识 |
| `review_score` | int | 评分 1–5 |
| `review_comment_title` | string | 评价标题（葡萄牙语） |
| `review_comment_message` | string | 评价正文（葡萄牙语） |
| `review_creation_date` | datetime | 评价问卷发出时间 |
| `review_answer_timestamp` | datetime | 评价填写时间 |

### customers（客户）

| 字段 | 类型 | 含义 |
|---|---|---|
| `customer_id` | string | 订单级客户标识（一单一个） |
| `customer_unique_id` | string | 真实客户标识（可跨订单复购） |
| `customer_zip_code_prefix` | string | 邮编前 5 位 |
| `customer_city` | string | 城市 |
| `customer_state` | string | 州（2 位缩写） |

### products（商品）

| 字段 | 类型 | 含义 |
|---|---|---|
| `product_id` | string | 商品标识 |
| `product_category_name` | string | 品类名（葡萄牙语） |
| `product_name_lenght` | float | 商品名长度（原字段拼写为 lenght） |
| `product_description_lenght` | float | 描述长度 |
| `product_photos_qty` | float | 图片数量 |
| `product_weight_g` | float | 重量（克） |
| `product_length_cm` | float | 长（厘米） |
| `product_height_cm` | float | 高（厘米） |
| `product_width_cm` | float | 宽（厘米） |

### sellers（卖家）

| 字段 | 类型 | 含义 |
|---|---|---|
| `seller_id` | string | 卖家标识 |
| `seller_zip_code_prefix` | string | 邮编前 5 位 |
| `seller_city` | string | 城市 |
| `seller_state` | string | 州 |

### geolocation（地理坐标）

| 字段 | 类型 | 含义 |
|---|---|---|
| `geolocation_zip_code_prefix` | string | 邮编前 5 位 |
| `geolocation_lat` | float | 纬度 |
| `geolocation_lng` | float | 经度 |
| `geolocation_city` | string | 城市 |
| `geolocation_state` | string | 州 |

### category_translation（品类翻译）

| 字段 | 类型 | 含义 |
|---|---|---|
| `product_category_name` | string | 葡萄牙语品类名 |
| `product_category_name_english` | string | 英文品类名 |

## 6. 已知数据质量问题（清洗阶段处理）

1. `orders` 中约 2,965 个订单缺少实际送达时间，计算配送时长时需剔除或单独标记。
2. 约 775 个订单没有商品明细（主要为 canceled / unavailable 状态），建模口径需明确。
3. `geolocation` 无唯一键，同一邮编前缀有多条记录，需按前缀聚合（如取经纬度中位数）。
4. `products` 的部分字段存在缺失（品类、重量、尺寸），需填充或标记。
5. 品类名为葡萄牙语，分析展示前需通过翻译表映射为英文。
6. `customer_id` 是订单级标识，做复购/RFM 时必须使用 `customer_unique_id`。
7. 三张表的邮编前缀（`*_zip_code_prefix`）含前导零（如 `01037`），读取时必须按字符串处理，否则会丢失前导零导致地理关联错误。
