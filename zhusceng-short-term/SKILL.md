---
name: zhusceng-short-term
version: 1.0
tags: [A股, 短线, 主升浪, 趋势股]
category: trading
description: "主升浪短线策略 — 流通值>30亿 + 涨幅>5% + 成交额>10亿，筛选趋势主升浪个股"
data_source_priority:
  1: "东方财富push2delay行业板块数据 — 强势板块识别（m:90+t:2）"
  2: "东方财富个股实时数据 — 涨幅/成交额/市值过滤（f3/f6/f20/f2）"
  3: "Sina hq_str + K线 — RSI计算"
  4: "mx-search stock-screen — 条件选股"
use_when:
  - 用户明确要求使用主升浪策略选股
  - 用户说"帮我看看主升浪"或"趋势股选股"
  - ⚠️ 注意：本skill输出的观察股必须经过 trap-detector + lhb-analyzer 安全检查后才能给出买卖建议
not_for:
  - 弱市（大盘跌幅>-2%时效果差）
platforms: [macos, linux, windows]
---

# 主升浪短线策略

> 来源：用户自定义策略（2026-05-22）
> 周期：超短线（1～5日），趋势跟随为主
> 定位：模拟交易参考，不构成投资建议

---

## 一、选股条件

### 1.1 硬性条件（必须同时满足）

| 条件 | 标准 | 说明 |
|------|------|------|
| 流通市值 | **> 30亿** | 排除小盘股，聚焦中大流动性标的 |
| 涨幅 | **> 5%** | 必须是当日强势股，在主升浪中 |
| 成交额 | **> 10亿** | 高成交额=资金认可，流动性好 |
| ST | 非ST | 排除风险 |
| 板块 | 主板 | 排除创业板高波动 |

### 1.2 主升浪板块识别

```
主线板块标准：
  - 板块涨幅 > 大盘涨幅的3倍
  - 或板块当日涨幅 > 2%
  - 且板块内有>=3只个股满足上述三条件

主升浪股必须是主线板块内的个股，孤立强势股不碰
```

---

## 二、买点

### 2.1 标准买点

```
✅ 买点 = 板块处于主升浪 + 个股满足三条件 + RSI<75 + 成交额持续放大
```

**买入时机**：
- 尾盘14:30后确认形态有效后买入
- 板块当日强势，个股涨停优先（封板坚决=主力控盘）

### 2.2 变体买点

```
⚠️ 变体买点 = 板块龙头RSI>80超买 + 次龙头RSI<70 + 三条件满足
  → 控仓<=10%介入
```

---

## 三、卖点

| 情形 | 操作 |
|------|------|
| 跌破分时均线30分钟不修复 | 减仓 |
| RSI>90 | 止盈 |
| 成交额萎缩至<5亿 | 减仓 |
| 涨幅>10%次日高开 | 止盈 |

---

## 四、止损

- 硬止损：亏损-7%无条件止损
- 10日线止损：收盘跌破10日线不收回，次日止损

---

## 五、数据获取

### 5.1 东方财富行业板块（判断主线）

```python
import requests

url = "http://push2delay.eastmoney.com/api/qt/clist/get"
params = {
    "pn": 1, "pz": 100, "po": 1, "np": 1,
    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
    "fltt": 2, "invt": 2, "fid": "f3",
    "fs": "m:90+t:2",
    "fields": "f12,f14,f3,f6,f8"
}
r = requests.get(url, params=params, timeout=15)
items = r.json()["data"]["diff"]
# 按涨幅排序，识别主线板块
```

### 5.2 东方财富个股筛选

```python
# 从东财行情接口筛选满足三条件的股票
# f3=涨跌幅% f6=成交额 f20=总市值 f2=最新价
params = {
    "pn": 1, "pz": 200, "po": 1, "np": 1,
    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
    "fltt": 2, "invt": 2, "fid": "f3",
    "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
    "fields": "f12,f14,f3,f6,f8,f20,f2"
}
# 过滤: f3>5 and f6>10e8 and f20>30e8
```

### 5.3 RSI计算（Sina K线手算）

```python
import requests, re

# 获取K线
url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code_prefix}{code}&scale=240&ma=no&datalen=20"
r = requests.get(url, headers={"Referer": "http://finance.sina.com.cn"}, timeout=10)
klines = r.json()

# Wilder RSI(14)
closes = [float(k["close"]) for k in klines]
gains, losses = [], []
for i in range(1, len(closes)):
    delta = closes[i] - closes[i-1]
    gains.append(max(delta, 0))
    losses.append(max(-delta, 0))

avg_gain = sum(gains[:14]) / 14
avg_loss = sum(losses[:14]) / 14
for i in range(14, len(gains)):
    avg_gain = (avg_gain * 13 + gains[i]) / 14
    avg_loss = (avg_loss * 13 + losses[i]) / 14

rs = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 100
```

---

## 六、实战案例（2026-05-21）

| 股票 | 代码 | 涨幅 | 成交额 | 市值 | RSI | 结论 |
|------|------|------|--------|------|-----|------|
| 德赛西威 | sz002920 | +10.00% | — | — | — | ✅ 涨停主升浪 |
| 红板科技 | sh603459 | +6.78% | — | — | — | ✅ 主升浪 |
| 博云新材 | sz002297 | +4.88% | — | — | — | ⚠️ 接近门槛 |
| 威龙股份 | sh603779 | +10.00% | — | 65亿 | RSI>95 | ❌ RSI>95排除 |
| 利仁科技 | sz001259 | +9.28% | — | — | RSI极高 | ❌ 触板未封 |

---

## 参考资料

- `references/capital-intent-patterns.md` — 派发模式 vs 主升浪模式对比：凯莱英(拉高出货)/四环生物(短庄建仓→主升浪)，含资金意图四维判断流程
