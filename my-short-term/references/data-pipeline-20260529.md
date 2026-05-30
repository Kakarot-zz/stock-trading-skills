# 数据管线确认（2026-05-29）

## 当前环境可用数据源

| 数据需求 | 推荐来源 | 路径/命令 | 状态 |
|---------|---------|----------|------|
| 涨停池（含连板数/炸板/封板时间） | akshare | `ak.stock_zt_pool_em(date='YYYYMMDD')` | ✅ 可用 |
| 大盘指数实时价格 | 腾讯行情 | `qt.gtimg.cn/q=sh000001,sz399006...` | ✅ 可用 |
| 涨幅3~9%全市场扫描 | Sina涨幅排行 | `vip.stock.finance.sina.com.cn...Market_Center.getHQNodeData` | ✅ 可用 |
| 流通市值/换手率 | akshare涨停池 | `stock_zt_pool_em` 的流通市值字段 | ✅ 可用 |
| 个股资金流向（DDX/DDY） | mx-data | `client.query('股票名')` 取 rawTable | ⚠️ 部分返回N/A |
| 龙虎榜席位 | mx-data自然语言 | `client.query('股票名 今日龙虎榜席位')` | ⚠️ 席位名称多为"未披露"，无法核实量化席位 |
| RSI-14计算 | **腾讯K线 bracket-counting** | `web.ifzq.gtimg.cn/appstock/app/fqkline/get` + bracket解析 | ✅ 可靠 |
| RSI-14备选 | akshare | 无直接RSI字段 | ❌ |

## RSI计算方案（2026-05-29确认可用）

**腾讯K线 bracket-counting 解析法（可靠）**：

腾讯K线返回体形如 `kline_dayhfq={"code":0,"data":{"sz002491":{"qfqday":[...]}}}`，内层数组不能直接 json.loads，需用 bracket-counting 解析：

```python
import re, urllib.request, ssl, json

def fetch_kline(prefix, code, count=30):
    # prefix已含完整前缀（如sz002491），不能再加code
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayhfq&param={prefix}{code},day,,,{count},qfq"
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, timeout=15, context=ctx) as r:
        raw = r.read().decode('utf-8')
    m = re.search(r'=\s*(\{.*\})', raw)
    if not m: return []
    text = m.group(1)
    # bracket-counting 找最外层 {...}
    start = text.index('{'); end = len(text); depth = 0
    for i, c in enumerate(text):
        if c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0: end = i+1; break
    obj = json.loads(text[start:end])
    prefix_key = prefix if prefix in obj.get('data', {}) else list(obj['data'].keys())[0]
    return obj['data'][prefix_key].get('qfqday') or obj['data'][prefix_key].get('day', [])

def calc_rsi(klines, period=14):
    """klines: [(date, open, close, ...), ...] 返回 RSI-6"""
    if len(klines) < period+1: return None
    closes = [float(k[2]) for k in klines]
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period-1) + gains[i]) / period
        avg_loss = (avg_loss * (period-1) + losses[i]) / period
    if avg_loss == 0: return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100/(1+rs), 1)
```

**RSI处理规则（已更新）**：
- RSI>80 → 排除（超买，回调概率>70%）
- RSI=100 → 非连板股RSI=100是数值溢出，排除
- RSI<40 → 关注，等回调到位
- 涨停股RSI=100是正常现象（连板导致），不作为排除依据

## LHB席位查询降级路径

1. `datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_DAILYBILLBOARD` → ❌ 报表配置不存在（2026-05-29）
2. `datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LHB_ALLSTOCKS` → ❌ 报表配置不存在
3. `mx_data.MXData().query('股票名 今日龙虎榜席位')` → ⚠️ 返回席位名称多为"未披露"，无法核实量化席位

**当所有API均无法核实席位时**：必须在报告中标注"席位风险未知"，控仓≤20%，出现拉萨关键词（团结路/金融城/东环路/山南/娘猜/当雄）立即止损。

## akshare push2 封禁状态

- `akshare.stock_zt_pool_em()` → ✅ 正常（不依赖push2）
- `akshare.stock_individual_fund_flow()` → ❌ 失败（HTTPSConnectionPool / Remote end closed）
- 依赖push2的akshare函数在此环境中全部不可用

## 全市场扫描综合评分体系（非连板股·2026-05-29确认）

| 维度 | 指标 | 评分规则 |
|------|------|---------|
| 成交额 | 5亿+ | 50亿+=20分, 20亿+=15分, 10亿+=10分, 5亿+=5分 |
| RSI安全 | RSI-14 | <40=20分, 40-60=15分, 60-75=10分, 75-80=5分, >80=0分 |
| 涨幅健康度 | 当日涨幅 | 3-7%=15分, 7-9%=10分, >9%=5分 |
| 板块联动 | 同板块有涨停 | 有=+20分, 无=0分（独立股） |

**RSI>80直接排除；RSI=100（非连板）也排除**
**综合评分40+分才有操作建议价值**
