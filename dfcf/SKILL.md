---
name: dfcf
display_name: 东方财富妙想技能包 (MXSKILLS)
title: 东方财富妙想 DFCSF MX Skills
description: 东方财富妙想金融技能包，包含数据查询(mx-data)、资讯搜索(mx-search)、智能选股(mx-xuangu)、自选股管理(mx-zixuan)、模拟组合管理(mx-moni)五大模块。通过 MX_APIKEY 调用 mkapi2.dfcfs.com 接口获取金融数据。
homepage: https://dl.dfcfs.com/m/itc4
author: 东方财富妙想团队
version: 1.0.0
env:
  - MX_APIKEY: "妙想Skills页面的API密钥"
---

# 东方财富妙想技能包 (DFCSF MX Skills)

本技能包安装于 `~/AppData/Local/hermes/skills/dfcf/`，包含5个技能模块：

## 技能模块

| 模块 | 目录 | 功能 |
|------|------|------|
| mx-data | `dfcf/mx-data/` | 金融数据查询（行情、财务、股东等） |
| mx-search | `dfcf/mx-search/` | 金融资讯搜索（新闻、公告、研报等） |
| mx-xuangu | `dfcf/mx-xuangu/` | 智能选股 |
| mx-zixuan | `dfcf/mx-zixuan/` | 自选股管理 |
| mx-moni | `dfcf/mx-moni/` | 模拟组合管理（持仓、买卖、撤单、委托） |

## 环境变量

```bash
MX_APIKEY=<你的API密钥>   # 必填，从 https://dl.dfcfs.com/m/itc4 获取
MX_API_URL=https://mkapi2.dfcfs.com/finskillshub  # 可选，默认值
```

# 东方财富妙想技能包 — API参考

## MX_APIKEY 端点权限说明

`MX_APIKEY` 对不同端点的可用性不一致，实测结果：

| 端点 | 路径 | 状态 | 备注 |
|------|------|------|------|
| mockTrading/positions | 模拟盘持仓 | ✅ 200 | |
| mockTrading/balance | 模拟盘资金 | ✅ 200 | |
| mockTrading/trade | 模拟盘交易 | ✅ 200 | |
| mockTrading/orders | 委托查询 | ✅ 200 | |
| mockTrading/cancel | 撤单 | ✅ 200 | |
| news-search | 资讯搜索 | ❌ 114 | 需确认 Key 权限 |
| 金融数据查询 | `mx_data.MXData().query()` | ✅ 200 | **推荐方式**，见下方详解 |

**如需资讯搜索/金融数据查询**，需确认 API Key 是否具有对应权限，或联系东方财富妙想支持。

## 已知陷阱

### 1. MX API Key 终端截断问题
在 MSYS/Git-Bash 环境下，使用 `echo $KEY >> file` 或 `echo "KEY=value"` 重定向写入包含特殊字符（如 `-` `_`）的 API Key 时，值可能被截断。

**症状：** API 返回 114，但同一 key 用 curl 直接指定 `-d "key=value"` 可以正常工作。

**解决方法：** 用 Python 写入文件，避免 shell 截断：
```bash
/c/Python314/python -c "open('file','a').write('\nKEY=your_full_key_here\n')"
```

### 2. mx-data Python 模块正确调用方式（关键）
SKILL.md 文档的 CLI 方式 `python mx_data.py "query"` 在某些环境可能失败。更可靠的方式是直接用 Python 导入模块：

```python
import os, sys
sys.path.insert(0, '/c/Users/June/AppData/Local/hermes/skills/dfcf/mx-data')
os.environ['MX_APIKEY'] = 'your_key_here'
import mx_data
result = mx_data.MXData().query('东方财富最新价')
```

**不要**用 `subprocess` 调用 mx_data.py（execute_code sandbox 环境找不到 Python 路径），用 terminal tool 调用。

### 3. mx-data 可以查龙虎榜席位数据
`mx_data.MXData().query('股票名今日龙虎榜席位')` 可以返回营业部席位信息，包含：
- 营业部名称
- 买入/卖出金额
- 量化席位识别关键字：拉萨（东方财富互联网开户量化席位群）

**注意**：部分股票查询返回空（席位=0），不代表数据不存在，可能是个股龙虎榜数据本身未更新。

### 4. mx-data 查询中文股票名返回港股而非A股（重要陷阱）

`mx_data.MXData().query('兆易创新')` 用中文名查询时，**返回的是港股数据**（03986.HK），而不是A股（603986.SH）。实测结果：

```
query('兆易创新') → dataTableDTOList[0].code = '03986.HK'（港股）
query('长电科技') → 同上
```

**已确认的中文名→A股代码映射**（用于持仓分析）：
| 中文名 | A股代码 | 备注 |
|--------|---------|------|
| 兆易创新 | 603986.SH | 半导体 |
| 长电科技 | 600584.SH | 半导体封测 |
| 合百集团 | 000501.SZ | 实为武商集团 |
| 四环生物 | 000518.SZ | 生物医药 |
| 工业富联 | 601138.SH | AI算力 |

**正确做法**：
1. 实时价格 → 用腾讯行情API `qt.gtimg.cn`（见下方"实时行情"章节）
2. DDX/资金流向 → 用腾讯历史K线接口 `push2.eastmoney.com/api/qt/stock/fflow/daykline/get`（若被封则用mx_data，需用代码而非中文名查询）
3. 龙虎榜席位 → `mx_data.MXData().query('股票名今日龙虎榜席位')`（可接受中文名）

### 5. 腾讯行情API — 可用字段与致命禁区

当 push2.eastmoney.com 被封禁时，腾讯行情接口部分可用，但**有致命禁区**：

```bash
# 批量查询（上海sh/深圳sz/北交所bj）
curl -s "https://qt.gtimg.cn/q=sh603986,sh600584,sz000518,sh601138,sz000501" \
  | python3 -c "
import sys, re
raw = sys.stdin.buffer.read().decode('gbk', errors='replace')
for m in re.finditer(r'v_(\w+)=\"(.*?)\"', raw):
    f = m.group(2).split('~')
    print(f'{f[1]}({m.group(1)}): 现价={f[3]} 涨跌={f[31]}({f[32]}%) '
          f'最高={f[33]} 最低={f[34]} 成交额(万)={f[37]}')
"
```

**字段索引速查**（`~`分隔，0-indexed）：
| 索引 | 字段 | 示例 | 可用性 |
|------|------|------|--------|
| f[1] | 名称 | 兆易创新 | ✅ 可用 |
| f[3] | 最新价 | 514.18 | ✅ 可用 |
| f[4] | 昨收 | 526.22 | ✅ 可用 |
| f[5] | 今开 | 541.00 | ✅ 可用 |
| f[6] | 成交量(手) | 667260 | ✅ 可用 |
| f[31] | 涨跌额 | -12.04 | ⚠️ 盘中可用，收盘后偏差 |
| f[32] | 涨跌幅% | -2.29 | ❌ **禁止使用**（见下方说明）|
| f[33] | 最高 | 552.82 | ✅ 可用 |
| f[34] | 最低 | 500.00 | ✅ 可用 |
| f[37] | 成交额（万元） | 3534122 | ✅ 可用 |

**市场前缀**：上海A股→`sh`，深圳A股（含创业板）→`sz`，北交所→`bj`。

#### 🔴 致命禁区：腾讯行情涨跌幅字段（f[32]）收盘后严重失真

**已知失真案例（2026-05-28 实测）：**

| 股票 | MX实际收盘 | MX实际涨跌幅 | 腾讯行情字段(f[32]) | 偏差 |
|------|-----------|------------|-------------------|------|
| 通鼎互联 | 23.12 | +8.85% | +1.88% | 偏差-7% |
| 香江控股 | 2.54 | +9.96% | +0.23% | 偏差-9.7% |
| 达实智能 | 4.57 | -0.22% | -0.01% | 绝对值错误 |
| 四环生物 | 3.56 | -9.42% | +1.88% | 完全相反方向 |
| 航天机电 | 15.05 | +10.01% | +1.37% | 偏差-8.6% |

**失真原因**：腾讯行情的涨跌幅字段在收盘后存在除权/复权计算错误，导致数据完全不可信。

**数据源优先级（强制规则）：**
1. **MX接口 `{name} 收盘价` / `{name} 涨跌幅`** — 最可靠，直接来自东方财富底层 ✅
2. **akshare** `stock_zt_pool_em(date)` — 涨停池涨跌幅可靠
3. **腾讯K线前复权收盘价** — 可用，但复权因子可能有小数偏差（如通鼎互联差9.5%）
4. **腾讯实时行情涨跌幅字段（f[32]）** — ❌ **严禁使用，无论任何情况**

#### MX接口有效query格式（已验证）

```python
# ✅ 有效关键词
mx_data.MXData().query('长电科技 收盘价')   # 返回6日历史收盘，key='325898'
mx_data.MXData().query('长电科技 涨跌幅')   # 返回涨跌幅，key='326865'
mx_data.MXData().query('长电科技 成交额')   # 返回成交额
mx_data.MXData().query('长电科技 股价')     # 同收盘价

# ❌ 无效关键词（返回空）
'今日收盘价'、'今日涨跌'、'今日涨跌幅'、'涨停'、'龙虎榜'
```

**返回数据路径**：`result['data']['data']['searchDataResultDTO']['dataTableDTOList'][0]['table']`
**历史收盘价key**：`'325898'`
**涨跌幅key**：`'326865'`

### 6. mx-data 查询资金流向数据（DDX/DDY/主力净额）【重要更新】

`mx_data.MXData().query()` 可以直接返回丰富的资金流向数据，包括：

**可用字段（通过 rawTable 返回）：**
- `f62` 主力净额（元）
- `f66` 超大单净额，`f65` 超大单流出，`f64` 超大单流入
- `f72` 大单净额，`f71` 大单流出，`f70` 大单流入
- `f78` 中单净额，`f77` 中单流出，`f76` 中单流入
- `f84` 小单净额，`f83` 小单流出，`f82` 小单流入
- `f88` 当日DDX，`f89` 当日DDY，`f90` 当日DDZ
- `f396` 3日DDX，`f397` 3日DDY
- `f91` 5日DDX，`f92` 5日DDY
- `f94` 10日DDX，`f95` 10日DDY
- `f6` 成交额，`f5` 成交量，`f8` 换手率
- `f2` 最新价，`f17` 开盘价，`f15` 最高价，`f16` 最低价

**调用示例（Python）：**
```python
import os, sys
sys.path.insert(0, '/c/Users/June/AppData/Local/hermes/skills/dfcf/mx-data')
with open('C:/Users/June/AppData/Local/hermes/.env', 'r') as f:
    for line in f:
        if 'MX_APIKEY' in line and not line.startswith('#'):
            APIKEY = line.strip().split('=', 1)[1].strip()
            break
os.environ['MX_APIKEY'] = APIKEY

import mx_data
result = mx_data.MXData().query('长电科技')
# 返回 rawTable 中含 f62(主力净额)、f88(DDX) 等字段
```

**返回结构示例（主力净额）：**
```json
{
  "rawTable": {
    "f62": ["-3460978176.00"],   // 主力净额 = -34.61亿
    "f66": ["-2923361280.00"],   // 超大单净额 = -29.23亿
    "f88": ["-2.141"],           // 当日DDX
    "f89": ["-3.099"],           // 当日DDY
    "f90": ["-30.51"],           // 当日DDZ
    "f91": ["-3.541"],           // 5日DDX
    "f92": ["-6.369"]            // 5日DDY
  }
}
```

**DDX/DDY 解读规则：**
- DDX > 0：主力买入；DDX < 0：主力卖出
- |DDX| > 2 = 强烈信号
- DDZ > 0 且大 = 资金强势；DDZ < -20 = 资金极弱
- 多周期（3日/5日/10日）同时为负 = 持续出货，不是单日行为

## MX Data 自然语言查询板块概念（实测有效）

MX Data 的 `query()` 方法支持自然语言查询板块概念股，**有效关键词**：

```python
result = client.query('无人机概念')   # ✅ 返回板块代码 90.BK0704
result = client.query('无人机板块')   # ✅ 同上
result = client.query('无人机龙头')   # ✅ 返回成分个数等数据
result = client.query('大疆无人机概念') # ✅ 返回公司基本信息

# ❌ 返回空
result = client.query('90.BK0704 成分股')  # 板块代码+成分股 → 空
result = client.query('无人机概念股')       # → 空
```

返回路径：`result['data']['data']['searchDataResultDTO']['dataTableDTOList'][0]`

**注意**：中文名查询板块/概念是有效的，但中文名查询个股**返回港股而非A股**（见上方陷阱4）。

### 7. 龙虎榜基础数据获取
东方财富龙虎榜页面 HTML 内嵌 JSON `pagedata`，可直接 curl 提取77条龙虎榜基础数据（涨跌幅、上榜次数等），无需 API 认证。详见 `references/lhb-data.md`。

## 龙虎榜数据提取

详见 `references/lhb-data.md`

## 龙虎榜量化席位过滤

详见 `references/lhb-quant-filter.md`

## 东方财富快讯API

实时市场热点资讯，稳定可用。详见 `references/kuaixun-api.md`。

## 快速调用示例

```bash
# 模拟盘持仓查询（curl直接调用）
curl -X POST "https://mkapi2.dfcfs.com/finskillshub/api/claw/mockTrading/positions" \
  -H "apikey: $MX_APIKEY" \
  -H "Content-Type: application/json" \
  -d '{"moneyUnit": 1}'

# 模拟盘资金查询
curl -X POST "https://mkapi2.dfcfs.com/finskillshub/api/claw/mockTrading/balance" \
  -H "apikey: $MX_APIKEY" \
  -H "Content-Type: application/json" \
  -d '{"moneyUnit": 1}'
```
