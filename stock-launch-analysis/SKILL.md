---
name: stock-launch-analysis
display_name: 股票启动形态分析
title: 股票启动形态分析 skill
description: 基于K线形态 + 资金意图双重验证，筛选即将启动或加速的主板强势股。形态逻辑：前期连续大涨 → 断板 → 大跌 → 昨日大低开承接 → 今日低开反弹。
author: Hermes Agent
version: 1.4
tags: [A股, 超短线, 选股, 形态分析]
mandatory_safety_check: true  # ⚠️ 强制：选股输出的每只观察股必须经过 trap-detector + lhb-analyzer 安全检查
---

# 股票启动形态分析 skill

## 核心逻辑

形态链五步（标准达实智能路径）：
1. **连续拉升**：近10天有3天及以上连续上涨（含涨停优先）
2. **断板**：连续拉升后出现平盘日（涨幅 0%~8%，主板涨停10%）
3. **大跌**：断板后次日跌幅 ≥5%
4. **昨日承接**：昨日大低开（≥3%），收盘 > 开盘（低点被收复，不要求收红）
5. **今日反弹**：今日低开（≥1%），当前价 > 开盘价

**硬条件**：大跌（步骤3）是形态完整的必要条件，缺则形态不标准。

---

## 机器人板块选股关键词（2026-05-22 验证）

扩大关键词表用于"机器人/智能制造/高端装备"板块扫描：

```
ROBOT_KW = [
    "机器人", "智能", "工业", "机械", "自动", "控制", "传感", "电机",
    "驱动", "装备", "系统", "数控", "工控", "机床", "加工中心", "激光",
    "协作机器人", "人型机器人", "人形机器人", "减速器", "RV", "谐波",
    "伺服", "PLC", "变频", "轨交", "航天", "航空", "军工", "碳纤维",
    "传感器", "机器视觉", "工业软件", "精密", "高端", "新质",
    "丝杠", "导轨", "轴承", "液压", "气动", "3D打印", "增材",
    "军工", "国防", "军民融合", "商业航天", "卫星", "火箭", "发动机",
    "航发", "兵装", "北方", "船舶", "海工", "核电",
    "算力", "AI", "人工智能", "具身智能", "灵巧手", "关节",
    "半导体", "芯片", "光刻", "先进封装", "HBM", "AI芯片",
    "PCB", "CCL", "玻纤", "电子", "连接器", "汽车电子",
    "雷达", "毫米波", "导航", "惯性", "光电", "红外", "热成像",
]
```

注意：以上关键词用于**名称匹配**，可能漏掉一些业务相关但名称不匹配的股票（如铜陵有色等周期股可能被误入）。**最终必须用腾讯K线形态验证**，不能只靠名称筛选。

---

## 数据源（2026-05-25 实测修正）

| 用途 | 首选 | 备选 | 状态 |
|------|------|------|------|
| K线历史 | **腾讯 `web.ifzq.gtimg.cn`** | 东财 | ✅ 稳定，完整前复权日K，注意日期顺序（见下方说明） |
| 全市场扫描 | **mx-data `claw/stock-screen`** | — | ✅ 主力数据源，2026-05-25验证正常 |
| 实时价格/涨幅 | **腾讯 `qt.gtimg.cn`** | Sina | ✅ 批量接口稳定 |

### ⚠️ 重要：Sina全市场接口已失效（2026-05-25确认）

`Market_Center.getHQNodeDataSimple` 接口返回 `Invalid service name`，**严禁使用Sina进行全市场扫描**。

**替代方案**：
1. **首选**：mx-data `claw/stock-screen` 接口，支持自然语言条件筛选（涨幅/市值/PE等）
2. **次选**：腾讯 `qt.gtimg.cn` 批量实时行情（每80只/次）

### ⚠️ 强警告：Sina K线接口对涨停股严重失真

Sina `CN_MarketData.getKLineData` 和 `money.finance.sina.com.cn` 接口在以下场景**完全错误**：
- 连续涨停股（收盘价与实际不符，涨跌幅误差可达20%）
- 跌停股（低开高走显示为大涨）
- 任何当日波动>10%的股票

**2026-05-22 实测京能电力**：Sina 显示昨日涨跌约+1.6%，实际为 **低开-5.5%后涨停+9.95%**。误差接近20个百分点。

**结论**：K线验证必须用腾讯接口，严禁使用Sina K线接口判断涨停/跌停。

### ⚠️ 涨跌幅计算基准（必须用昨收，非当日开盘）

```
正确: pct = (今日收盘 - 昨日收盘) / 昨日收盘 × 100
错误: pct = (今日收盘 - 今日开盘) / 今日开盘 × 100  ← 旧版脚本BUG
```

### RSI计算（Wilder RSI14，必须手算）

```python
def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    for i in range(len(gains) - period, len(gains) - 1, -1):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    rs = avg_gain / avg_loss if avg_loss else 999
    return 100 - (100 / (1 + rs))
```

**严禁使用Sina K线的`pct_change`字段**（Sina对涨停股严重失真），也**不要用mx-data返回的RSI接口**（2026-05实测返回6日RSI偏差高达47点）。

### 腾讯K线接口格式

```
GET https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayhfq&param={mkt}{code},day,,{end_date},{count},qfq
GET（无end_date）: https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayhfq&param={mkt}{code},day,,,{count},qfq
Response: kline_dayhfq={...}  →  json.loads(text.replace("kline_dayhfq=", "", 1))
返回结构: data['{mkt}{code}']['qfqday'] = [[日期, 开, 收, 高, 低, 量(手)], ...]
字段索引: [0]=日期 [1]=开 [2]=收 [3]=高 [4]=低 [5]=量

⚠️ 日期顺序与end_date参数强相关，必须实测确认：

| 调用方式 | 日期顺序 | 示例 |
|---------|---------|------|
| 带end_date参数 | 最新日期在前（降序） | end_date="2026-05-22" → qfqday[0]=05-22 |
| 不带end_date参数 | 最旧日期在前（升序）⚠️ | qfqday[0]=2026-04-08 |

**强烈建议**：始终使用不带end_date的调用方式（默认升序），直接用 `klines[i]` 访问，**不要反转数组**。

```python
# ✅ 推荐：升序直接用
klines_asc = [row[:6] for row in klines_raw]  # 已是旧→新
for i, d in enumerate(klines_asc):
    d.append(0.0)
    if i > 0:
        d[-1] = (float(d[2]) - float(klines_asc[i-1][2])) / float(klines_asc[i-1][2]) * 100

# klines_asc[0] = 最早, klines_asc[-1] = 昨天
# n = len(klines_asc)
# 昨天 = klines_asc[n-1], 大跌日 = klines_asc[n-2], 断板日 = klines_asc[n-3]
```

**⚠️ 之前版本错误说"日期最新在前"，这是带end_date参数时的行为，不带时为升序。**

**返回key**：是完整前缀如 `sh600578`，不是纯代码 `600578`
**访问方式**：必须用 `data["data"][f"{mkt}{code}"]["qfqday"]` 直接访问，禁止用 `for k, v in kdata.items()` 遍历。
```

---

## 执行脚本

执行脚本：`scripts/analyze_launch.py`（2026-05-25 重写，已修复所有BUG）

使用前：
1. 编辑脚本顶部 `TODAY = "2026-05-25"` 改为当日日期
2. 确保 `~/.hermes/.env` 中有 `MX_APIKEY`
3. 运行：`python3 scripts/analyze_launch.py`

```bash
# 快速运行
TODAY="2026-05-25" python3 scripts/analyze_launch.py
```

---

## 评分标准（5分制）

| 条件 | 分数 |
|------|------|
| 连涨≥3天 | 1分 |
| 断板（涨幅0~8%） | 1分 |
| 大跌（跌幅≥5%） | 1分 |
| 昨日承接（低开≥3%且收盘>开盘） | 1分 |
| 今日反弹（低开≥1%且高走） | 1分 |

- **≥3分**：候选形态
- **5分满分**：标准达实智能路径，需关注位置高低
- **大跌缺失**：形态不完整，仅为"类形态"，不属于标准路径

---

## 形态范本：达实智能(sz002421)

完整走完五步形态链（2026-05-22修正版）：
- 05-15涨停 → 05-18涨停（连续拉升）
- 05-19/20断板（涨幅收敛）
- 05-21跌停（大跌，-10%）
- 05-22低开-2.5%后反弹+10.1%（今日反弹）

这是最标准的参考范本。

---

## 常见误判与陷阱（2026-05-22更新）

**京能电力陷阱（满分5/5，腾讯K线验证）**：
真实形态：9连涨→05-19断板+7.26%→05-20跌停→05-21低开-5.51%后**涨停收盘**→今日低开-3.18%反弹+3.3%。昨日并非低开低走，而是大低开后的强势涨停封板。属于标准达实智能路径，但位置极高（7天5板），明日若高开超3%是卖点。

**贵州燃气陷阱（3/5）**：缺"大跌"硬条件。连续拉升后无≥5%跌幅，形态链不完整，不属于标准路径。

**北自科技陷阱（4/5）**：有断板但连续一字板，承接日收盘-7.08%偏弱。

**昨日承接判断**：原标准"收盘跌幅<|开盘gap|×50%"过于宽松。真实标准：**收盘 > 开盘**（低点被收复即可，不要求收红）。京能电力05-21开盘6.85→收盘8.18（涨停），close > open 明显成立。

---

## 已知局限

- K线为前复权数据，与不分权分时图略有差异
- 新股/次新股（上市<3个月）形态失真度高，建议排除
- ST/\*ST票不参与筛选
- 行情数据为快照，建议结合同花顺/东财分时图二次确认承接力度

---

## ⚠️ analyze_form() 函数BUG（必须修复）

`analyze_form()` 函数在 `scripts/analyze_launch.py` 中有两个严重BUG：

### BUG 1: 涨跌幅基准错误（ pct 计算公式错）
```python
# 错误（用当日开盘价做基准）
pcts = [(closes[i] - opens[i]) / opens[i] * 100 for i in range(len(recent_asc))]

# 正确（用昨日收盘价做基准，才是标准涨跌幅）
pcts = []
for i in range(len(recent_asc)):
    if i == 0:
        pcts.append(0.0)
    else:
        pcts.append((closes[i] - closes[i-1]) / closes[i-1] * 100)
```

### BUG 2: 腾讯K线日期顺序（已修正）

**重要更正（2026-05-25）**：不带end_date参数调用时，返回数组是**升序**（最旧日期在前），不是"最新在前"。

```python
def get_tencent_kline_asc(code, count=30):
    """获取腾讯K线，返回时间正序（旧→新）。不要反转数组！"""
    prefix = "sh" if code.startswith(("6", "9")) else "sz"
    # 不带end_date参数 → 默认升序（最旧日期在前）
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayhfq&param={prefix}{code},day,,,{count},qfq"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
        text = r.read().decode("utf-8").replace("kline_dayhfq=", "", 1)
    data = json.loads(text)
    klines_raw = data.get("data", {}).get(f"{prefix}{code}", {}).get("qfqday", [])
    if not klines_raw:
        return []
    # 直接使用，不要反转！已经是升序
    klines_asc = [row[:6] for row in klines_raw]
    closes = [float(d[2]) for d in klines_asc]
    for i, d in enumerate(klines_asc):
        d.append(0.0)
        if i > 0:
            d[-1] = (closes[i] - closes[i-1]) / closes[i-1] * 100
    return klines_asc
    # klines_asc[0] = 最早, klines_asc[-1] = 昨天
    # n = len(klines_asc)
    # 昨天 = klines_asc[n-1], 大跌日 = klines_asc[n-2], 断板日 = klines_asc[n-3]
```

### BUG 3: 评分体系与五步形态不匹配
旧版评分是13分制（连涨3/断板2/大跌3/昨日2/今日2/额外1），应统一为**5分制**（每项1分，满分5分）。

### 正确版本参考

正确可用的形态检查函数见本次会话（2026-05-22）执行代码中的 `check_pattern_full()` 实现，以该版本为准。建议重新编写 `scripts/analyze_launch.py` 的 Step 3 函数。

### 腾讯批量实时行情正确用法（2026-05-22 确认）

```python
# ✅ 正确：用 qt.gtimg.cn 的 v_ 前缀格式，q= 参数批量查询
codes = ",".join([f"sh600353", "sh603031", ...])  # 最多80只/次
url = f"https://qt.gtimg.cn/q={codes}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.qq.com"})
# 返回格式: v_sh600353="1~名称~代码~当前价~昨收~今开~..."
# 字段索引: [1]=名称 [3]=当前价 [4]=昨收 [5]=今开 [33]=最高 [34]=最低

# ❌ 错误：用 hq.sinajs.cn 的 hq_str_ 格式做批量实时行情
# hq.sinajs.cn 在部分环境返回空，但 qt.gtimg.cn 稳定
```

### 东财龙虎榜API已变更（2026-05-22 实测）

旧版 `RPT_DRAGON_LIST_DAILYSTATISTIC` 报表已废弃，查询返回 `code=9501 报表配置不存在`。

新发现东财 `datacenter-web.eastmoney.com` 的龙虎榜接口需要用不同的 reportName，当前**推荐使用 mx-search `claw/news-search`** 查询龙虎榜席位明细（已验证2026-05-22有效）。

如需直接查东财龙虎榜，需先探测当前有效的 reportName，建议通过 mx-search 端点获取龙虎榜数据。

### 达实智能形态精确定义（2026-05-22 五步全部满足）

| 步骤 | 达实智能实际走法 | 判断阈值 |
|------|----------------|---------|
| ①连续大涨 | 05-15涨停→05-18涨停→05-19涨停 | 近10日涨停≥1次 |
| ②断板 | 05-19/20涨幅收敛至0~8% | 连续大涨后出现涨幅<9%的交易日 |
| ③大跌 | 05-21跌幅-7.3%（非跌停） | 断板后次日跌幅≥5% |
| ④大低开承接 | 05-22开盘-2.5%收+10.1% | 昨日开盘低开≥2%，收盘>开盘 |
| ⑤今日反弹 | 05-22低开高走涨停 | 今日涨幅>5%，收盘在当日高位 |

**大跌（步骤③）是形态完整的必要条件，缺则降级处理（如贵州燃气）。**

---

## 龙虎榜席位查询（2026-05-22 更新）

**首选：mx-data `claw/news-search`**（2026-05-20/22 确认返回完整席位明细）

```python
import urllib.request, json, os

api_key = next(
    l.split('"')[1] if '"' in l else l.split("'")[1]
    for l in open(os.path.expanduser("~/.hermes/.env"))
    if 'MX_APIKEY' in l
)

BASE_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/news-search"
payload = {"query": "<股票名> <日期> 龙虎榜 席位 买卖明细", "size": 5}
req = urllib.request.Request(BASE_URL,
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "apikey": api_key},
    method="POST")
with urllib.request.urlopen(req, timeout=30) as r:
    result = json.loads(r.read().decode())

items = result["data"]["data"]["llmSearchResponse"]["data"]
for item in items:
    content = item.get("content", "").replace("\\n", "\n")
    print(f"[{item['date']}] {item['title']}")
    print(content[:800])
```

**注意**：`claw/query` 端点不支持龙虎榜（返回空 dataTableDTOList）。`claw/lhb-detail` 也已失效。

**量化席位识别规则**：
- 拉萨天团 ≥ 2个 = 量化，确认排除
- 非拉萨的知名量化席位：国泰海通总部/瑞银/中金上海/高盛中国/中信深圳滨海等
- 量化席位 ≥ 2 → 触发排除铁律

