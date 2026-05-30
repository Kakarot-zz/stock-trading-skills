# 资金流向数据提取（DDX/DDY/主力净额）

## 数据源对比

| 方式 | 可用性 | 备注 |
|------|--------|------|
| `mx_data.MXData().query()` | ✅ 推荐（需注意：中文名返回港股） | 返回完整的DDX/DDY/主力资金分层数据 |
| 腾讯行情 `qt.gtimg.cn` | ✅ 实时价格 | 可获取最新价/涨跌幅/成交额，字段f62等需另查 |
| akshare `stock_individual_fund_flow` | ❌ push2 被封禁 | `RemoteDisconnected: ProxyError` |
| EastMoney push2 API (urllib) | ❌ 被封禁 | `RemoteDisconnected` |
| EastMoney push2his DDX kline API | ❌ 被封禁 | 同上 |

## MX Data 查询法（推荐）

### 正确的 import 模式（关键）

> ⚠️ `sys.path.insert` 从其他目录调用时**不会自动找到** mx_data 模块。必须先 `cd` 到 mx-data 目录，或在脚本所在目录内调用。

**推荐**：把脚本放在 `mx-data/` 目录下，从该目录运行：
```bash
cd /c/Users/June/AppData/Local/hermes/skills/dfcf/mx-data
/c/Python314/python your_script.py
```

**备选**：在脚本内用绝对路径 sys.path，但需要确保工作目录正确。

```python
import os, sys, json
# 读取 APIKEY（从不写在代码里，从 .env 读取）
with open('C:/Users/June/AppData/Local/hermes/.env', 'r') as f:
    for line in f:
        if 'MX_APIKEY' in line and not line.startswith('#'):
            APIKEY=line.s...'=', 1)[1].strip()
            break
os.environ['MX_APIKEY'] = APIKEY

import mx_data
result = mx_data.MXData().query('四川长虹 主力资金流向')
```

### 如何找到正确的 table（不要用硬索引！）

> `dataTableDTOList` 的索引是**不固定**的——公司基本信息表和资金流向表的排列顺序因查询词而异。**永远不要写死 `[0]` 或 `[1]`**，而是用 `title` 字段匹配。

```python
dtl = result['data']['data']['searchDataResultDTO']['dataTableDTOList']
for i, t in enumerate(dtl):
    title = t.get('title', '')
    raw = t.get('rawTable', {})
    head = raw.get('headName', ['N/A'])[0]
    print(f'Table {i}: {title} | 时间: {head}')
    # 打印所有包含 f62/f88 等资金字段的 table
    if 'f62' in raw or 'f88' in raw:
        print('  → 资金流向表，打印字段:')
        for k in ['f62','f66','f72','f88','f89','f90']:
            if k in raw:
                v = raw[k][0] if isinstance(raw[k], list) else raw[k]
                print(f'    {k}: {v}')
```

### 实际返回结构（四川长虹 2026-05-29 实测）

| Table index | title 关键词 | headName(数据时间) | 内容 |
|------------|-------------|-------------------|------|
| 0 | 超大单净额、超大单流出 | 2026-05-29 10:55 | **资金流向表**（DDX/主力净额/各档单据） |
| 1 | 主力流出、主力流入 | 2026-05-29 10:55 | 空（返回空数据） |
| 2 | 大单流出资金、小单流出资金 | 2026-05-28 | 前一交易日快照 |

**结论**：始终遍历 dtl 用 title 过滤，匹配 `超大单净额` 或 `主力流出` 的 table 即为资金数据。

### 关键字段速查

| 字段码 | 含义 | 单位 | 解读 |
|--------|------|------|------|
| f62 | 主力净额 | 元 | 负=主力卖出，正=主力买入 |
| f66 | 超大单净额 | 元 | 机构大资金 |
| f72 | 大单净额 | 元 | 中大户 |
| f78 | 中单净额 | 元 | 中户 |
| f84 | 小单净额 | 元 | 散户 |
| f88 | 当日DDX | — | 主力买入强度，<0=出货 |
| f89 | 当日DDY | — | 主力卖出强度，<0=出货 |
| f90 | 当日DDZ | — | 资金强弱，<-20=极弱 |
| f396/f397 | 3日DDX/DDY | — | 连续信号 |
| f91/f92 | 5日DDX/DDY | — | 中期趋势 |
| f94/f95 | 10日DDX/DDY | — | 长期趋势 |

### 数值转换示例

```python
# 主力净额（元 → 亿）
main_net = float(raw['f62'][0]) / 1e8   # -34.61亿

# 超大单净额
super_net = float(raw['f66'][0]) / 1e8  # -29.23亿

# DDX（直接是浮点数）
ddx = float(raw['f88'][0])   # -2.141
ddy = float(raw['f89'][0])   # -3.099
ddz = float(raw['f90'][0])   # -30.51
```

## DDX 指标解读规则

### 信号强度
- |DDX| < 0.5：中性
- 0.5 < |DDX| < 1.5：偏弱/偏强
- 1.5 < |DDX| < 2.5：**强烈信号**
- |DDX| > 2.5：极强信号

### 多周期一致性原则
- 单日DDX负 ≠ 看空（可能是盘中对倒）
- 3日/5日/10日 **同时为负** = 持续出货，是真正的减仓信号
- 多周期负值 + 换手率高 = 筹码换手/主力派发

### DDZ 解读
- DDZ > 0：主力资金整体买入
- DDZ < -20：主力资金博弈极端偏向卖出

### 资金分层结构（出货 vs 接盘）
```
机构出货形态：
  超大单净额 → 负（大单卖出）
  大单净额 → 负
  中单净额 → 正（回补）
  小单净额 → 正（接盘）
  换手率 → 高（高位巨量换手）
```

## 已知限制

1. MX Data API 返回的成交额是今日收盘后更新数据，非实时
2. 港股/美股行情不支持 DDX/DDY
3. `mx_data.MXData().query('股票名')` 返回多个 dataTableDTOList，资金数据在 index=1 的那个
