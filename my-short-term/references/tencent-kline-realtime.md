# 腾讯K线 + 实时行情 复用代码段

## 腾讯K线（前复权日线）解析

```python
import urllib.request, ssl, json, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get_kline(prefix, code, count=30):
    """腾讯前复权日K线。prefix如'sz'/'sh'，code如'002442'/'603779'"""
    url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayhfq&param={prefix}{code},day,,,{count},qfq'
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        raw = r.read().decode('utf-8')
    # bracket-counting 解析（防json.loads因格式问题报错）
    start = raw.find('"qfqday":')
    if start == -1:
        return []
    arr_start = raw.find('[', start)
    depth = 0
    i = arr_start
    while i < len(raw):
        if raw[i] == '[': depth += 1
        elif raw[i] == ']':
            depth -= 1
            if depth == 0:
                return json.loads(raw[arr_start:i+1])
        i += 1
    return []

# 使用示例
klines = get_kline('sh', '603779', 30)  # 威龙股份
klines = get_kline('sz', '002442', 30)  # 龙星科技
# 每条: [日期, 开, 收, 高, 低, 量(手)]
```

## Sina实时行情（竞价/当前价）

```python
def get_sina_quote(code):
    """返回{name, open, close, current, high, low, vol, amount}"""
    prefix = 'sz' if code.startswith(('300','002','000','001')) else 'sh'
    url = f'https://hq.sinajs.cn/list={prefix}{code}'
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0','Referer':'https://finance.sina.com.cn'})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        raw = r.read().decode('gbk', errors='ignore')
    parts = raw.strip().split('"')[1].split(',')
    return {
        'name':   parts[0],
        'open':   float(parts[1]) if parts[1]  else 0,
        'close':  float(parts[2]) if parts[2]  else 0,   # 昨收
        'current':float(parts[3]) if parts[3]  else 0,
        'high':   float(parts[4]) if parts[4]  else 0,
        'low':    float(parts[5]) if parts[5]  else 0,
        'vol':    float(parts[8]) if parts[8]  else 0,
        'amount': float(parts[9]) if parts[9]  else 0,
    }

# 注意：若current=0说明当日休市或Sina数据源失效，改用腾讯K线最后一根收盘价
```

## 东方财富龙虎榜席位查询

```python
def query_lhb(code):
    """返回近5条龙虎榜记录，每条含BUYSEATS/SELLSEATS/BUYAMOUNT/SELLAMOUNT/HAPPEN_DATE"""
    url = (f'https://datacenter-web.eastmoney.com/api/data/v1/get'
           f'?reportName=RPT_DAILYBILLBOARD'
           f'&columns=ALL'
           f'&filter=(SCODE=%22{code}%22)'
           f'&pageNumber=1&pageSize=5'
           f'&sortTypes=-1&sortColumns=HAPPEN_DATE'
           f'&source=WEB&client=WEB')
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        data = json.loads(r.read())
    result = data.get('result', {})
    return result.get('data', []) if result else []
```

## RSI计算（标准Wilder平滑法）

```python
def calc_rsi(prices, period=6):
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0: return 100
    return round(100 - 100/(1 + avg_gain/avg_loss), 1)
```

## 涨停检测

```python
def detect_limit_ups(klines):
    """检测近10日所有涨停日，返回[(日期, 涨幅%)]。klines为腾讯K线get_kline()返回"""
    result = []
    for i in range(1, len(klines)):
        prev = float(klines[i-1][2])
        cur  = float(klines[i][2])
        chg  = (cur - prev) / prev * 100
        if chg >= 9.7:
            result.append((klines[i][0], round(chg, 1)))
    return result
```

## 股票名称→代码 搜索（东方财富）

```python
from urllib.parse import quote

def search_code(name):
    """返回[{Name, Code, MktNum}]列表，取第一个结果的Code即正确代码"""
    encoded = quote(name)
    url = f'https://searchapi.eastmoney.com/api/suggest/get?input={encoded}&type=14&token=***&count=5'
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        data = json.loads(r.read())
    return data.get('QuotationCodeTable', {}).get('Data', [])
```

## 典型分析流程（代码确认后）

```
1. search_code(名称) → 确认代码 + 前缀
2. get_kline(prefix, code, 30) → K线数组
3. calc_rsi([float(k[2]) for k in klines], 6) → RSI6/14
4. detect_limit_ups(klines) → 涨停日列表
5. get_sina_quote(code) → 今日竞价/当前价/成交量
6. query_lhb(code) → 龙虎榜席位（如有）
```
