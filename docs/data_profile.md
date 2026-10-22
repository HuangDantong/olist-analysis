# Olist 数据概览与质量体检

- 生成时间：2026-10-22 10:00:11 中国标准时间
- 数据目录：`D:\大数据分析及数据可视化\olist-analysis\data\raw\olist`
- 主表：`orders`，**99,441 行**（作业要求 ≥ 500 行：✅ 满足）

## 一、业务规模速览

| 指标 | 数值 |
|---|---:|
| 订单数 | 99,441 |
| 已送达订单 | 96,478 |
| 取消订单 | 625 |
| 不可用订单 | 609 |
| 下单时间范围 | 2016-09-04 ～ 2018-10-17 |
| 商品明细行数 | 112,650 |
| 有商品明细的订单 | 98,666 |
| 无商品明细的订单 | 775 |
| 商品数 | 32,951 |
| 卖家数 | 3,095 |
| GMV（商品价格合计） | R$ 13,591,643.70 |
| 运费合计 | R$ 2,251,909.54 |
| 客户数（customer_id） | 99,441 |
| 去重客户数（customer_unique_id） | 96,096 |
| 评论数 | 99,224 |
| 平均评分 | 4.09 / 5 |
| 已送达但缺送达时间 | 2,965 |

## 二、表级汇总

| 表 | 行数 | 列数 | 内存 (MB) | 缺失单元格 | 缺失率 | 全行重复 | 主键 | 主键重复 | 主键为空 |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| `orders` | 99,441 | 8 | 21.9 | 4,908 | 0.62% | 0 | order_id | 0 | 0 |
| `order_items` | 112,650 | 7 | 18.4 | 0 | 0.00% | 0 | order_id + order_item_id | 0 | 0 |
| `payments` | 103,886 | 5 | 8.1 | 0 | 0.00% | 0 | order_id + payment_sequential | 0 | 0 |
| `reviews` | 99,224 | 7 | 17.8 | 145,903 | 21.01% | 0 | review_id | 814 | 0 |
| `customers` | 99,441 | 5 | 11.5 | 0 | 0.00% | 0 | customer_id | 0 | 0 |
| `products` | 32,951 | 9 | 3.7 | 2,448 | 0.83% | 0 | product_id | 0 | 0 |
| `sellers` | 3,095 | 4 | 0.2 | 0 | 0.00% | 0 | seller_id | 0 | 0 |
| `category_translation` | 71 | 2 | 0.0 | 0 | 0.00% | 0 | product_category_name | 0 | 0 |
| `geolocation` | 1,000,163 | 5 | 54.9 | 0 | 0.00% | 261,831 | —（无唯一键） | — | — |

## 三、外键完整性

| 子表.字段 | 父表.字段 | 检查行数 | 命中 | 未命中 | 命中率 |
|---|---|---:|---:|---:|---:|
| `orders.customer_id` | `customers.customer_id` | 99,441 | 99,441 | 0 | 100.00% |
| `order_items.order_id` | `orders.order_id` | 112,650 | 112,650 | 0 | 100.00% |
| `order_items.product_id` | `products.product_id` | 112,650 | 112,650 | 0 | 100.00% |
| `order_items.seller_id` | `sellers.seller_id` | 112,650 | 112,650 | 0 | 100.00% |
| `payments.order_id` | `orders.order_id` | 103,886 | 103,886 | 0 | 100.00% |
| `reviews.order_id` | `orders.order_id` | 99,224 | 99,224 | 0 | 100.00% |
| `products.product_category_name` | `category_translation.product_category_name` | 32,341 | 32,328 | 13 | 99.96% |

## 四、字段明细

### `orders`（99,441 行 × 8 列）

| 字段 | 类型 | 非空 | 缺失率 | 唯一值 | 样例值 | 最早 | 最晚 |
|---|---|---:|---:|---:|---|---|---|---|
| `order_id` | str | 99,441 | 0.00% | 99,441 | e481f51cbdc54678b7cc49136f2d6af7 / 53cdb2fc8bc7dce0b6741e2150273451 / 47770eb9100c2d0c44946d9cf07ec65d |  |  |
| `customer_id` | str | 99,441 | 0.00% | 99,441 | 9ef432eb6251297304e76186b10a928d / b0830fb4747a6c6d20dea0b8c802d7ef / 41ce2a54c0b03bf3443c3d931a367089 |  |  |
| `order_status` | str | 99,441 | 0.00% | 8 | delivered / invoiced / shipped |  |  |
| `order_purchase_timestamp` | str | 99,441 | 0.00% | 98,875 | 2017-10-02 10:56:33 / 2018-07-24 20:41:37 / 2018-08-08 08:38:49 | 2016-09-04 21:15:19 | 2018-10-17 17:30:18 |
| `order_approved_at` | str | 99,281 | 0.16% | 90,733 | 2017-10-02 11:07:15 / 2018-07-26 03:24:27 / 2018-08-08 08:55:23 | 2016-09-15 12:16:38 | 2018-09-03 17:40:06 |
| `order_delivered_carrier_date` | str | 97,658 | 1.79% | 81,018 | 2017-10-04 19:55:00 / 2018-07-26 14:31:00 / 2018-08-08 13:50:00 | 2016-10-08 10:34:01 | 2018-09-11 19:48:28 |
| `order_delivered_customer_date` | str | 96,476 | 2.98% | 95,664 | 2017-10-10 21:25:13 / 2018-08-07 15:27:45 / 2018-08-17 18:06:29 | 2016-10-11 13:46:32 | 2018-10-17 13:22:46 |
| `order_estimated_delivery_date` | str | 99,441 | 0.00% | 459 | 2017-10-18 00:00:00 / 2018-08-13 00:00:00 / 2018-09-04 00:00:00 | 2016-09-30 00:00:00 | 2018-11-12 00:00:00 |

### `order_items`（112,650 行 × 7 列）

| 字段 | 类型 | 非空 | 缺失率 | 唯一值 | 样例值 | 最早 | 最晚 |
|---|---|---:|---:|---:|---|---|---|---|
| `order_id` | str | 112,650 | 0.00% | 98,666 | 00010242fe8c5a6d1ba2dd792cb16214 / 00018f77f2f0320c557190d7a144bdd3 / 000229ec398224ef6ca0657da4fc703e |  |  |
| `order_item_id` | int64 | 112,650 | 0.00% | 21 | 1 / 2 / 3 |  |  |
| `product_id` | str | 112,650 | 0.00% | 32,951 | 4244733e06e7ecb4970a6e2683c13e61 / e5f2d52b802189ee658865ca93d83a8f / c777355d18b72b67abbeef9df44fd0fd |  |  |
| `seller_id` | str | 112,650 | 0.00% | 3,095 | 48436dade18ac8b2bce089ec2a041202 / dd7ddc04e1b6c2c614352b383efe2d36 / 5b51032eddd242adc84c38acab88f23d |  |  |
| `shipping_limit_date` | str | 112,650 | 0.00% | 93,318 | 2017-09-19 09:45:35 / 2017-05-03 11:05:13 / 2018-01-18 14:48:30 | 2016-09-19 00:15:34 | 2020-04-09 22:35:08 |
| `price` | float64 | 112,650 | 0.00% | 5,968 | 58.9 / 239.9 / 199.0 |  |  |
| `freight_value` | float64 | 112,650 | 0.00% | 6,999 | 13.29 / 19.93 / 17.87 |  |  |

### `payments`（103,886 行 × 5 列）

| 字段 | 类型 | 非空 | 缺失率 | 唯一值 | 样例值 | 最早 | 最晚 |
|---|---|---:|---:|---:|---|---|---|---|
| `order_id` | str | 103,886 | 0.00% | 99,440 | b81ef226f3fe1789b1e8b2acac839d17 / a9810da82917af2d9aefd1278f1dcfa0 / 25e8ea4e93396b6fa0d3dd708e76c1bd |  |  |
| `payment_sequential` | int64 | 103,886 | 0.00% | 29 | 1 / 2 / 4 |  |  |
| `payment_type` | str | 103,886 | 0.00% | 5 | credit_card / boleto / voucher |  |  |
| `payment_installments` | int64 | 103,886 | 0.00% | 24 | 8 / 1 / 2 |  |  |
| `payment_value` | float64 | 103,886 | 0.00% | 29,077 | 99.33 / 24.39 / 65.71 |  |  |

### `reviews`（99,224 行 × 7 列）

| 字段 | 类型 | 非空 | 缺失率 | 唯一值 | 样例值 | 最早 | 最晚 |
|---|---|---:|---:|---:|---|---|---|---|
| `review_id` | str | 99,224 | 0.00% | 98,410 | 7bc2406110b926393aa56f80a40eba40 / 80e641a11e56f04c1ad469d5645fdfde / 228ce5500dc1d8e020d8d1322874b6f0 |  |  |
| `order_id` | str | 99,224 | 0.00% | 98,673 | 73fc7af87114b39712e6da79b0a377eb / a548910a1c6147796b98fdf73dbeba33 / f9e4b658b201a9f2ecdecbb34bed034b |  |  |
| `review_score` | int64 | 99,224 | 0.00% | 5 | 4 / 5 / 1 |  |  |
| `review_comment_title` | str | 11,568 | 88.34% | 4,527 | recomendo / Super recomendo / Não chegou meu produto |  |  |
| `review_comment_message` | str | 40,977 | 58.70% | 36,159 | Recebi bem antes do prazo estipulado… / Parabéns lojas lannister adorei comp… / aparelho eficiente. no site a marca … |  |  |
| `review_creation_date` | str | 99,224 | 0.00% | 636 | 2018-01-18 00:00:00 / 2018-03-10 00:00:00 / 2018-02-17 00:00:00 | 2016-10-02 00:00:00 | 2018-08-31 00:00:00 |
| `review_answer_timestamp` | str | 99,224 | 0.00% | 98,248 | 2018-01-18 21:46:59 / 2018-03-11 03:05:13 / 2018-02-18 14:36:24 | 2016-10-07 18:32:28 | 2018-10-29 12:27:35 |

### `customers`（99,441 行 × 5 列）

| 字段 | 类型 | 非空 | 缺失率 | 唯一值 | 样例值 | 最早 | 最晚 |
|---|---|---:|---:|---:|---|---|---|---|
| `customer_id` | str | 99,441 | 0.00% | 99,441 | 06b8999e2fba1a1fbc88172c00ba8bc7 / 18955e83d337fd6b2def6b18a428ac77 / 4e7b3e00288586ebd08712fdd0374a03 |  |  |
| `customer_unique_id` | str | 99,441 | 0.00% | 96,096 | 861eff4711a542e4b93843c6dd7febb0 / 290c77bc529b7ac935b93aa66c333dc3 / 060e732b5b29e8181a18229c7b0b2b5e |  |  |
| `customer_zip_code_prefix` | string | 99,441 | 0.00% | 14,994 | 14409 / 09790 / 01151 |  |  |
| `customer_city` | str | 99,441 | 0.00% | 4,119 | franca / sao bernardo do campo / sao paulo |  |  |
| `customer_state` | str | 99,441 | 0.00% | 27 | SP / SC / MG |  |  |

### `products`（32,951 行 × 9 列）

| 字段 | 类型 | 非空 | 缺失率 | 唯一值 | 样例值 | 最早 | 最晚 |
|---|---|---:|---:|---:|---|---|---|---|
| `product_id` | str | 32,951 | 0.00% | 32,951 | 1e9e8ef04dbcff4541ed26657ea517e5 / 3aa071139cb16b67ca9e5dea641aaa2f / 96bd76ec8810374ed1b65e291975717f |  |  |
| `product_category_name` | str | 32,341 | 1.85% | 73 | perfumaria / artes / esporte_lazer |  |  |
| `product_name_lenght` | float64 | 32,341 | 1.85% | 66 | 40.0 / 44.0 / 46.0 |  |  |
| `product_description_lenght` | float64 | 32,341 | 1.85% | 2,960 | 287.0 / 276.0 / 250.0 |  |  |
| `product_photos_qty` | float64 | 32,341 | 1.85% | 19 | 1.0 / 4.0 / 2.0 |  |  |
| `product_weight_g` | float64 | 32,949 | 0.01% | 2,204 | 225.0 / 1000.0 / 154.0 |  |  |
| `product_length_cm` | float64 | 32,949 | 0.01% | 99 | 16.0 / 30.0 / 18.0 |  |  |
| `product_height_cm` | float64 | 32,949 | 0.01% | 102 | 10.0 / 18.0 / 9.0 |  |  |
| `product_width_cm` | float64 | 32,949 | 0.01% | 95 | 14.0 / 20.0 / 15.0 |  |  |

### `sellers`（3,095 行 × 4 列）

| 字段 | 类型 | 非空 | 缺失率 | 唯一值 | 样例值 | 最早 | 最晚 |
|---|---|---:|---:|---:|---|---|---|---|
| `seller_id` | str | 3,095 | 0.00% | 3,095 | 3442f8959a84dea7ee197c632cb2df15 / d1b65fc7debc3361ea86b5f14c68d2e2 / ce3ad9de960102d0677a81f5d0bb7b2d |  |  |
| `seller_zip_code_prefix` | string | 3,095 | 0.00% | 2,246 | 13023 / 13844 / 20031 |  |  |
| `seller_city` | str | 3,095 | 0.00% | 611 | campinas / mogi guacu / rio de janeiro |  |  |
| `seller_state` | str | 3,095 | 0.00% | 23 | SP / RJ / PE |  |  |

### `category_translation`（71 行 × 2 列）

| 字段 | 类型 | 非空 | 缺失率 | 唯一值 | 样例值 | 最早 | 最晚 |
|---|---|---:|---:|---:|---|---|---|---|
| `product_category_name` | str | 71 | 0.00% | 71 | beleza_saude / informatica_acessorios / automotivo |  |  |
| `product_category_name_english` | str | 71 | 0.00% | 71 | health_beauty / computers_accessories / auto |  |  |

### `geolocation`（1,000,163 行 × 5 列）

| 字段 | 类型 | 非空 | 缺失率 | 唯一值 | 样例值 | 最早 | 最晚 |
|---|---|---:|---:|---:|---|---|---|---|
| `geolocation_zip_code_prefix` | string | 1,000,163 | 0.00% | 19,015 | 01037 / 01046 / 01041 |  |  |
| `geolocation_lat` | float64 | 1,000,163 | 0.00% | 717,360 | -23.54562128115268 / -23.54608112703553 / -23.54612896641469 |  |  |
| `geolocation_lng` | float64 | 1,000,163 | 0.00% | 717,613 | -46.63929204800168 / -46.64482029837157 / -46.64295148361138 |  |  |
| `geolocation_city` | str | 1,000,163 | 0.00% | 8,011 | sao paulo / são paulo / sao bernardo do campo |  |  |
| `geolocation_state` | str | 1,000,163 | 0.00% | 27 | SP / RN / AC |  |  |

## 五、体检结论与清洗关注点

1. 主表 `orders` 共 99,441 行，满足作业“主表 ≥ 500 行”的要求。
2. 外键命中率见第三节；`order_items` 与 `orders` 的关联覆盖 98,666 / 99,441 个订单。
3. 775 个订单没有商品明细，多为取消/不可用订单，建模时需明确过滤规则。
4. 2,965 个订单缺少实际送达时间，计算配送时长时要单独处理。
5. 品类名为葡萄牙语，需通过 `product_category_name_translation` 映射为英文。
6. `geolocation` 无唯一主键，邮编前缀会重复；地理分析前需按邮编前缀聚合去重。
7. 评论表 `review_id` 需校验唯一性；若存在一单多评，按订单聚合时要去重。

> 本报告由 `scripts/01_load.py` 自动生成，数据未做任何修改。
