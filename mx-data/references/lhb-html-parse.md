# 龙虎榜数据获取（2026年5月环境）

## 优先级

1. **~~东方财富 datacenter API~~** — ❌ **2026-05-29全线失效**（`RPT_LHB_ALLSTOCKS`、`RPT_DAILYBILLBOARD`、`RPT_BILLBOARD_DAILYDETAILSBUY`全部返回code=9501）
2. **MXData.query('{code}今日龙虎榜席位')** — MX_APIKEY有效时可用（自然语言查询）
3. ~~龙虎榜HTML解析~~ — `data.eastmoney.com/stock/lhb.html` 页面已不返回pagedata，**禁止使用正则提取**

> 📅 **2026-05-29 实测确认**：本次会话直接调用 `datacenter-web.eastmoney.com` 全部 reportName，返回统一错误 `code=9501`。**datacenter API 全线失效**。

## datacenter API（正确接口）

```python
import urllib.request, json

code = "000509"  # 华塑控股示例
url = (
    "https://datacenter-web.eastmoney.com/api/data/v1/get"
    "?reportName=RPT_DAILYBILLBOARD"
    "&columns=ALL"
    f"&filter=(SCODE=%22{code}%22)"
    "&pageNumber=1&pageSize=5"
    "&sortTypes=-1&sortColumns=HAPPEN_DATE"
    "&source=WEB&client=WEB"
)
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as r:
    result = json.loads(r.read().decode("utf-8"))

# 关键字段：
#   BUYSEATS / SELLSEATS — 分号分隔的营业部名称字符串
#   BUYAMOUNT / SELLAMOUNT — 买卖总金额（元）
#   HAPPEN_DATE — 上榜日期
```

## MXData 自然语言查询

```python
import sys
sys.path.insert(0, 'C:/Users/June/AppData/Local/hermes/skills/dfcf/mx-data')
from mx_data import MXData
# MX_APIKEY 在 ~/.env 第485行（注意：第484行是注释行）
lines = open('C:/Users/June/AppData/Local/hermes/.env').readlines()
key = lines[485].split('=')[1].strip()  # 不要用 enumerate，直接行号
m = MXData(api_key=key)
r = m.query('000509今日龙虎榜席位')
# 返回: dataTableDTOList 为空不一定代表无数据，可能是自然语言未匹配到结构化数据
```

> ⚠️ MXData.query() 是自然语言接口，不是直接字段查询。`dataTableDTOList` 为空不代表股票未上榜。

## 拉萨席位过滤规则

```python
LASA_KW = ['拉萨团结路','拉萨金融城','拉萨东环路','拉萨山南',
           '拉萨娘猜','拉萨当雄','拉萨虎空路','东方财富拉萨']
# 拉萨席位>=2 → 量化，直接排除
```

## MX_APIKEY状态判断

| 响应 | 含义 |
|------|------|
| `success: false, status: 114` | Key无效或已过期 |
| `success: true, data.dataTableDTOList: []` | 正常但无龙虎榜数据或未匹配 |
| 超时/连接拒绝 | 网络问题或push2被封 |
