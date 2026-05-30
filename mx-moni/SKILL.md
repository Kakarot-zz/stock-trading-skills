---
name: mx-moni
description: 妙想A股模拟组合管理：持仓/资金查询、买卖下单、撤单、委托记录
tags: ["模拟炒股", "A股", "投资练手", "策略验证"]
use_when:
  - 用户需要模拟炒股练手、验证交易策略
  - 用户需要进行模拟交易操作（买卖/撤单）
  - 用户需要查询模拟账户的持仓、资金、委托、历史成交记录
not_for:
  - 真实资金交易、投资建议生成、交易决策指引
  - 非A股类投资模拟（期货、外汇、港股、美股等）
  - 商业用途、代他人操作、非法交易演示
---

# mx_moni 妙想模拟组合管理 skill

本 Skill 由妙想提供一个股票模拟组合管理系统，支持股票组合持仓查询、买卖操作、撤单、委托查询、历史成交查询和资金查询等功能。

## 环境变量配置

| 变量 | 必填 | 说明 |
|------|------|------|
| `MX_APIKEY` | 是 | 妙想Skills页面获取的API密钥 |
| `MX_API_URL` | 否 | 默认为 `https://mkapi2.dfcfs.com/finskillshub` |

> **API Key 权限说明**：同一个 Key 有只读和交易两种权限层级。`code=114` 说明 Key 只有查询权限没有交易权限，需在妙想页面确认交易权限已开启。持仓查询成功但交易失败时，首先检查此问题。

## 交易 API 字段映射

```
POST https://mkapi2.dfcfs.com/finskillshub/api/claw/mockTrading/trade
```

| 字段 | 说明 | 示例 |
|------|------|------|
| `type` | `buy` 或 `sell` | `"sell"` |
| `stockCode` | 6位股票代码 | `"002380"` |
| `quantity` | 股数（整数，100的整数倍） | `10000` |
| `useMarketPrice` | 是否市价 | `false` |
| `price` | 价格（放大取整） | `40500` |

**price 放大规则**：上交所（6/9开头）×100；深交所（0/3开头）×1000

**常见报错**：
- `code=100 "输入价格不合理，超过限价"` — 价格超出涨跌停限制，或精度错误
- `code=501 "可用余额不足"` — 账户可用资金不够
- `code=114 "API密钥不存在或已失效"` — Key 无交易权限

## push2 被封时的备选：新浪实时行情

当 `push2.eastmoney.com` 被防火墙封堵时：

```python
import urllib.request
url = 'https://hq.sinajs.cn/list=sz002380,sz301591'
req = urllib.request.Request(url, headers={'Referer': 'https://finance.sina.com.cn'})
with urllib.request.urlopen(req, timeout=8) as r:
    data = r.read().decode('gbk')  # 深市=sz，沪市=sh，北交所=bj
```

## 快速调用

```bash
# 查询持仓/资金
python mx_moni.py "我的持仓"
python mx_moni.py "我的资金"

# 卖出（price 关键词必须，否则数量被误解析为价格）
python mx_moni.py "卖出 002380 价格 41.00 10000股"

# 市价买入
python mx_moni.py "市价买入 000002 1000"

# 撤单
python mx_moni.py "一键撤单"
```

## 调试参考

遇到 API 问题（114 权限错误、100 价格超限等）时，参考：
`references/mock-trading-api-notes.md`
