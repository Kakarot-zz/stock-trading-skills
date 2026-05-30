# mx-xuangu 响应格式详解

## 实际返回路径（2026-05 确认）

`raw.json` 顶层结构：
```
success / status / code / message / data / requestId
```

数据在 `data.data.allResults.result` 下：
```
data.data.allResults.result.columns[]   — 列定义
data.data.allResults.result.dataList[]  — 行数据（90条/次查询上限）
data.data.allResults.result.total       — 命中总数
```

**不是**文档中描述的 `data.dataTableDTOList`，这是旧版路径。

## 列名映射（动态 key 格式）

返回的 `key` 形如：`010000_LIANGBI<70>{2026-05-28}`

这类复合 key 需在行数据中用字符串匹配（如 `'LIMIT_UP_FLT' in k`）取值，不能直接用列标题查。

核心列 key：
| 实际含义 | key 特征 |
|---------|---------|
| 股票代码 | `SECURITY_CODE` |
| 股票简称 | `SECURITY_SHORT_NAME` |
| 市场简称 | `MARKET_SHORT_NAME` |
| 最新价 | 含 `NEWEST_PRICE` 或数值型 |
| 涨跌幅 | `CHG` |
| 成交额 | 含 `TURNOVER` / `TRADING_VOLU` |
| 流通市值 | 含 `CIRCULATION_MARKET` |
| 涨停首次封板时间 | 含 `LIMIT_UP_FLT` 或 `封板` |

## CSV 导出失败原因（已确认，永远为空）

`mx_xuangu.py` 导出的 CSV **永远全为空行**——因为 `build_column_map` 用的映射 key（如 `NEWEST_PRICE`）在 `dataList` 行数据中不存在，实际 key 是复合格式如 `010000_LIANGBI<70>{2026-05-28}`。**永远不要等 CSV 文件，必须直接解析 raw JSON。**

**正确路径**：
```
raw_json['data']['data']['allResults']['result']['columns']   — 列定义（title→key映射）
raw_json['data']['data']['allResults']['result']['dataList']  — 行数据（复合格式key）
raw_json['data']['data']['allResults']['result']['total']    — 命中总数
```

**解析模板**：
```python
import json
with open('mx_xuangu_..._raw.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)

result = raw['data']['data']['allResults']['result']
rows = result['dataList']
total = result['total']

# 复合格式key用字符串匹配取值
for r in rows:
    code = r.get('SECURITY_CODE', '')
    for k, v in r.items():
        if 'SECURITY_SHORT_NAME' in k:
            name = v
        if 'CHG' in k and isinstance(v, (int, float)):
            chg = v
        if 'LIMIT_UP_FLT' in k:  # 封板时间
            flt_time = v
```

## 腾讯行情替代方案（更可靠）

当 mx-xuangu CSV 解析失败时，用腾讯行情批量接口替代：

```bash
curl -s "https://qt.gtimg.cn/q=sh605589,sz002585,sh603083" \
  -H "Referer: https://finance.sina.com.cn" \
  | python3 -c "
import sys, re
raw = sys.stdin.buffer.read().decode('gbk', errors='replace')
for m in re.finditer(r'v_(\w+)=\\\"(.*?)\\\"', raw):
    f = m.group(2).split('~')
    print(f'{f[1]}({m.group(1)}): 现价={f[3]} 涨幅={f[32]}% 成交额={f[37]}万')
"
```

字段索引：f[1]=名称 f[3]=现价 f[4]=昨收 f[5]=今开 f[32]=涨跌幅% f[37]=成交额(万元)
