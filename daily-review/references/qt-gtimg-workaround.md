# Tencent行情API替代方案（push2封禁时）

## 问题背景
当 push2.eastmoney.com 被防火墙封禁时，akshare 的 `stock_zh_a_spot_em()` 等依赖 push2 的函数全部失败：
```
HTTPSConnectionPool(host='82.push2.eastmoney.com', port=443): 
  ProxyError('Unable to connect to proxy', RemoteDisconnected(...))
```

## 解决方案：Tencent qt.gtimg.cn

```bash
# 单票
curl -s "https://qt.gtimg.cn/q=sh600584"

# 多票（逗号分隔，不留空格）
curl -s "https://qt.gtimg.cn/q=sh600584,sh600151,sz002636"
```

## 解析方法（Python 3.14）

```python
import subprocess

result = subprocess.run(
    ['curl', '-s', 'https://qt.gtimg.cn/q=sh600584,sh600151'],
    capture_output=True
)
# 输出是GBK编码，需要转换
raw = result.stdout.decode('gbk')

for line in raw.strip().split('\n'):
    if not line.startswith('v_'): continue
    code_full = line.split('=')[0].replace('v_', '')
    data = line.split('=')[1].rstrip('~').strip('~"').split('~')
    # 字段索引（以6位A股为例）：
    # [1]名称 [3]当前价 [5]今开 [31]涨跌幅% [32]涨跌额 [33]最高 [34]最低 [6]成交量(手)
    name = data[1]
    price = data[3]
    zd_pct = data[31]
    zd_price = data[32]
    open_p = data[5]
    high = data[33]
    low = data[34]
    vol = data[6]
    print(f'{name}: 收盘={price}, 涨跌幅={zd_pct}%, 涨跌={zd_price}元, 今开={open_p}, 最高={high}, 最低={low}')
```

## 字段速查

| 索引 | 字段 | 示例 |
|------|------|------|
| [1] | 股票名称 | 长电科技 |
| [3] | 当前价格 | 82.05 |
| [5] | 今开 | 86.00 |
| [6] | 成交量（手） | 3103586 |
| [31] | 涨跌幅% | -3.17 |
| [32] | 涨跌额（元） | -2.69 |
| [33] | 最高价 | 89.77 |
| [34] | 最低价 | 80.33 |
| [30] | 成交额（元） | 26508349088 |

## 适用场景

- 个股当日行情查询（替代 akshare `stock_zh_a_spot_em`）
- 持仓股盘中/盘后快速检视
- 当 push2 封禁但需要实时价格时

## 重要限制

- **涨跌幅字段（data[31]）对涨停股有系统性偏差** — 2026-05-28实测：全91只实际涨停+10%，但腾讯返回+0.23%~+8.17%等错误值；**持仓分析严禁使用腾讯涨跌幅字段**
- 只能获取当日实时/收盘价，不支持历史数据
- 返回GBK编码，必须转换
- 无单笔成交明细

## 其他备选

- Sina `hq.sinajs.cn`（此环境被封禁，返回403）
- 东方财富行情页 `browser_navigate` + `browser_console`（慢，不推荐）
- MX接口 `{name} 收盘价 涨跌幅`（可用，但返回结构需解析，见 `mx_data` skill）

## 持仓数据源优先级（已验证）

1. MX接口 `{name} 收盘价` / `{name} 涨跌幅` — 格式规范，但字段名有时为`-`
2. Tencent qt.gtimg.cn — 实时价格可靠，**涨跌幅不可信**
3. akshare `stock_zh_a_spot_em` — push2封禁时不可用
