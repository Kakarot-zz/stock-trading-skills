# 腾讯K线 RSI计算 — 已验证模式

## URL格式（已验证可用）
```
https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayqfq&param={market}{code},day,,,61,qfq
```

- `market`: `sh`（上证/科创板/沪市主板）或 `sz`（深证/创业板）
- `code`: 6位股票代码
- 返回60条前复权日K线

## JSON解析（已验证）
```python
import urllib.request, ssl, json

def get_rsi6(code, market):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayqfq&param={market}{code},day,,,61,qfq'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        txt = r.read().decode('utf-8')
    # ⚠️ 响应以 "kline_dayqfq=" 开头，必须去掉
    txt = txt.replace('kline_dayqfq=', '', 1)
    data = json.loads(txt)
    stock_data = data['data'][market + code]
    # 前复权K线在 qfqday key
    klines = stock_data.get('qfqday', stock_data.get('day', []))
    if len(klines) < 20:
        return None
    closes = [float(k[1]) for k in klines[-61:]]

    # RSI-6计算
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    if len(gains) < 6:
        return None
    ag = sum(gains[:6]) / 6
    al = sum(losses[:6]) / 6
    for i in range(6, len(gains)):
        ag = (ag * 5 + gains[i]) / 6
        al = (al * 5 + losses[i]) / 6
    if al == 0:
        return 100
    return 100 - 100 / (1 + ag / al)
```

## 关键陷阱
1. **响应前缀** — 腾讯K线返回以 `var kline_dayqfq=` 开头，Python `json.loads` 直接解析会报错 `Expecting value: line 1 column 1`。**必须先去掉前缀**再解析。
2. **前复权数据在 `qfqday`** — 部分股票只有 `day` 无 `qfqday`，需同时兼容两个key。
3. **创业板/科创板数据可能为0** — 部分创业板(300/301)和科创板(688)code前复权数据返回价格为0，需降级使用 `day` 数据或标记为不可用。
4. **RSI-6使用61条K线** — 确保计算精度。

## 市场前缀速查
| 代码前缀 | 市场 | 前缀 |
|---------|------|------|
| 600/601/603/605/688 | 沪市 | `sh` |
| 000/001/002/003/300/301 | 深市 | `sz` |
| 002 | 深市（中小板） | `sz` |
