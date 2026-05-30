# 涨停池扫描工作流（2026-05-28确认）

## 问题
`akshare.stock_zt_pool_em()` 依赖 `push2.eastmoney.com`（端口443），当前环境被防火墙封禁，调用报：
```
HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): 
  Max retries exceeded (Remote end closed connection)
```
`scripts/scan.py` 目前依赖此接口，盘中扫描会失败。

## 解决方案：Sina涨幅排行 + 腾讯K线验证

### Step 1：Sina涨幅排行初筛（盘中最可靠）

```python
import urllib.request, ssl, json
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=50&sort=changepercent&asc=0&node=hs_a'
req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0','Referer':'https://finance.sina.com.cn'})
with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
    raw = r.read().decode('gbk', errors='ignore')
data = json.loads(raw)  # list of dicts: {symbol, name, changepercent, volume, ...}
```

字段说明：
- `symbol`: 股票代码，格式`sh600xxx`或`sz002xxx`
- `changepercent`: 涨幅（%）
- `volume`: 成交量（股）

### Step 2：过滤主板涨停股

```python
def get_prefix(code):
    code = code.zfill(6)
    return f'sz{code}' if code.startswith(('300','002','000','001')) else f'sh{code}'

def is_mainboard_zt(stock):
    sym = stock['symbol']
    name = stock['name']
    chg = float(stock.get('changepercent', 0))
    if name.startswith('ST') or name.startswith('*ST'):
        return False
    if not any(sym.startswith(p) for p in ['sh600','sh601','sh603','sz000','sz001','sz002']):
        return False
    return chg >= 9.7
```

### Step 3：腾讯K线连板检测（收盘后/盘中均可用）

```python
def get_kline(prefix, code, count=20):
    url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayhfq&param={prefix}{code},day,,,{count},qfq'
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        raw = r.read().decode('utf-8')
    # bracket-counting 解析
    start = raw.find('"qfqday":')
    arr_start = raw.find('[', start)
    depth = 0; i = arr_start
    while i < len(raw):
        if raw[i] == '[': depth += 1
        elif raw[i] == ']':
            depth -= 1
            if depth == 0:
                return json.loads(raw[arr_start:i+1])
        i += 1
    return []

def check_limit_ups(klines, days=10):
    """返回近N日涨停日期列表"""
    result = []
    for i in range(max(1, len(klines)-days), len(klines)):
        prev = float(klines[i-1][2])
        curr = float(klines[i][2])
        chg = (curr - prev) / prev * 100
        if chg >= 9.7:
            result.append(klines[i][0])
    return result

def check_consecutive(klines, n=3):
    """检测自然日连续n连板"""
    from datetime import datetime, timedelta
    zt_dates = []
    for i in range(max(1, len(klines)-10), len(klines)):
        prev = float(klines[i-1][2])
        curr = float(klines[i][2])
        if prev > 0 and (curr - prev) / prev * 100 >= 9.7:
            zt_dates.append(datetime.strptime(klines[i][0], '%Y-%m-%d'))
    if len(zt_dates) < n: return False
    zt_dates.sort(reverse=True)
    for i in range(len(zt_dates)-n+1):
        if all((zt_dates[i+j] - zt_dates[i+j+1]).days == 1 for j in range(n-1)):
            return True
    return False
```

## 完整扫描流程

```python
# 1. Sina获取今日涨停池
zt_candidates = [s for s in data if is_mainboard_zt(s)]

# 2. 高成交额过滤（>1亿，筛掉流动性差的）
high_vol = [s for s in zt_candidates if float(s.get('volume',0))/1e8 > 1.0]

# 3. 腾讯K线验证连板结构
results = []
for stock in high_vol:
    sym = stock['symbol']
    code = sym[2:]
    prefix = get_prefix(code)
    klines = get_kline(prefix, code, 20)
    if not klines: continue
    
    zt_dates = check_limit_ups(klines, 10)
    max_consec = max_consecutive_limit_ups(klines)
    
    results.append({
        'name': stock['name'],
        'code': code,
        'sym': sym,
        'vol': float(stock['volume'])/1e8,
        'chg': float(stock['changepercent']),
        'zt_dates': zt_dates,
        'max_consecutive': max_consec,
        'rsi6': calc_rsi6(klines),
    })
```

## 已知局限

- Sina涨幅排行仅返回前250只（5页×50），可能遗漏尾部涨停
- 盘中数据可能有15分钟延迟
- 成交额字段为成交量（股），需除以1e8换算为亿
