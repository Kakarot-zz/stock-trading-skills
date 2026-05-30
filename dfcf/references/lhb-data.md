# 东方财富龙虎榜数据提取

## 背景

东方财富龙虎榜页面 `https://data.eastmoney.com/stock/lhb.html` 的数据以 **embedded JSON** 形式藏在页面 HTML 的 `<script>` 标签中（变量名 `pagedata`），而非通过独立 API 加载。

**已知失效（2026-05-29确认）：**
- `datacenter-web.eastmoney.com` 的龙虎榜报表名（RPT_DRAGON_LIST / RPT_LHB_ALLSTOCKS / RPT_DAILYBILLBOARD / RPT_BILLBOARD_DAILYDETAILSBUY 等）全部返回"报表配置不存在"（错误码9501）
- `push2.eastmoney.com` API 在无浏览器 UA 的情况下返回空
- MX skill 的 `/api/claw/news-search` 接口对龙虎榜返回 114（API key 无效/无权）

**HTML pagedata 提取法**：东方财富个股龙虎榜详情页 `data.eastmoney.com/stock/lhb/<code>.html` 的HTML中是否仍内嵌pagedata JSON，**未经本环境实测确认**（2026-05-29当日未测试）。如遇空结果请改用 mx-data 自然语言查询。

## 提取方法

```bash
curl -s "https://data.eastmoney.com/stock/lhb.html" | python3 -c "
import sys, re, json

html = sys.stdin.read()
m = re.search(r'pagedata=(\{\"sbgg_all.*?\});', html, re.DOTALL)
text = m.group(1)

# Extract data array
start = text.find('\"data\":[') + len('\"data\":[')
depth = 0; i = start
while i < len(text):
    if text[i] == '[': depth += 1
    elif text[i] == ']':
        if depth == 0: break
        depth -= 1
    i += 1

arr_text = text[start:i]
elements = []
depth = 0; start_i = 0
for j, c in enumerate(arr_text):
    if c == '{':
        if depth == 0: start_i = j
        depth += 1
    elif c == '}':
        depth -= 1
        if depth == 0: elements.append(json.loads(arr_text[start_i:j+1]))

# Sort by change rate
elements.sort(key=lambda x: float(x.get('CHANGE_RATE', 0)), reverse=True)
for r in elements:
    print(r.get('SECURITY_NAME_ABBR'), r.get('SECURITY_CODE'),
          r.get('CHANGE_RATE'), r.get('MARKET_SUFFIX'), r.get('ONLIST_NUM'))
"
```

## 数据字段说明

| 字段 | 说明 |
|------|------|
| SECURITY_CODE | 6位股票代码 |
| SECURITY_NAME_ABBR | 股票简称 |
| CHANGE_RATE | 涨跌幅 (%) |
| MARKET_SUFFIX | 市场：SH/SZ/BJ |
| ONLIST_NUM | 上榜次数 |
| BILLBOARD_NET_AMT | 龙虎榜净买卖额 |
| TRADE_DATE | 交易日期 |

**注意：** 基础列表页的 `pagedata` 只含涨跌幅和上榜次数，**不含成交额、买卖席位等详情**。详情需访问个股龙虎榜详情页。
