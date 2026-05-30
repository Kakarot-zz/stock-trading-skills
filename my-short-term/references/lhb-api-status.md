# 龙虎榜API状态记录

## 2026-05-29 全线失效确认

以下接口**全部返回 `code=9501`，报表配置不存在**：

| 接口 | reportName | 状态 |
|------|-----------|------|
| RPT_LHB_ALLSTOCKS | 龙虎榜全个股 | ❌ 9501 |
| RPT_DAILYBILLBOARD | 龙虎榜每日明细 | ❌ 9501 |
| RPT_BILLBOARD_DAILYDETAILSBUY | 龙虎榜营业部和个股 | ❌ 9501（列不存在）|
| RPT_BILLBOARD_INFO | 龙虎榜信息 | ❌ 9501 |
| RHB_LHB_BILLBOARDDETAILSBUY | — | ❌ 9501 |

## mx-data方法

`mx_data.MXData` **没有** `ddx()` 和 `lhb_detail()` 方法。

## HTML方式

`data.eastmoney.com/stock/lhb/{code}.html` 的 pagedata 已不返回BUYSEATS字段，禁止使用正则提取。

## ✅ 当前可用LHB数据获取方式

**`akshare.stock_lhb_detail_em(start_date, end_date)` 可用**（2026-05-29验证成功）：

```python
import akshare as ak
df = ak.stock_lhb_detail_em(start_date='20260525', end_date='20260529')
# 返回列：序号、代码、名称、上榜日、解读、收盘价、涨跌幅、
#         龙虎榜净买额、龙虎榜买入额、龙虎榜卖出额、
#         龙虎榜成交额、市场总成交额、净买额占比、换手率、流通市值、上榜原因、
#         上榜后1日/2日/5日/10日涨跌幅
```

**注意**：`stock_lhb_detail_em` 不使用 `push2his.eastmoney.com`（被封禁的接口），而是直接访问东方财富网站，数据返回正常。函数签名：
```python
stock_lhb_detail_em(start_date: str = 'YYYYMMDD', end_date: str = 'YYYYMMDD')
# 参数格式：'YYYYMMDD' 字符串，非datetime对象
```

## ❌ 已确认失效的LHB接口（2026-05-29）

以下 datacenter-web.eastmoney.com API **全部返回 `code=9501`，报表配置不存在**：

| 接口 | reportName | 状态 |
|------|-----------|------|
| RPT_LHB_ALLSTOCKS | 龙虎榜全个股 | ❌ 9501 |
| RPT_DAILYBILLBOARD | 龙虎榜每日明细 | ❌ 9501 |
| RPT_BILLBOARD_DAILYDETAILSBUY | 龙虎榜营业部和个股 | ❌ 9501 |

**HTML方式**：`data.eastmoney.com/stock/lhb/{code}.html` 的 pagedata 已不返回BUYSEATS字段，禁止使用正则提取。

## 当前对策

席位无法核实 → 操作时视为高风险项：
- 严格控仓≤20%
- 若盘中出现秒级砸盘、分时锯齿（量化特征），立即止损
- 手动在东方财富网页查询作为人工核实备选

## 复现代码

```python
import akshare as ak
# ✅ 正确方式：akshare lhb detail（2026-05-29确认可用）
df = ak.stock_lhb_detail_em(start_date='20260501', end_date='20260529')
bojin = df[df['代码'].astype(str).str.contains('002297')]

# ❌ 失效方式：东方财富datacenter API（全返回9501）
for rp in ["RPT_LHB_ALLSTOCKS","RPT_DAILYBILLBOARD","RPT_BILLBOARD_DAILYDETAILSBUY"]:
    url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName={rp}&columns=ALL&filter=(SCODE=%22002297%22)&pageNumber=1&pageSize=3&sortTypes=-1&sortColumns=HAPPEN_DATE&source=WEB&client=WEB"
    # 全返回 code=9501
```
