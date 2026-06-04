---
name: lhb-daily-review
description: 东方财富龙虎榜量化席位过滤 + DDX大单动向分析 + 综合复盘。输入任意日期，输出当日龙虎榜可关注标的。
category: finance
---

# 当日龙虎榜复盘 Skill

## 触发条件
- 用户说"龙虎榜复盘"、"分析龙虎榜"、"今日龙虎榜"
- 用户说"帮我复盘"

## 数据来源
1. **龙虎榜明细（akshare推荐）** — `akshare.stock_lhb_detail_em(start_date='YYYYMMDD', end_date='YYYYMMDD')`
   - ✅ **此API可用**（2026-06-04验证：返回上榜日/收盘价/涨跌幅/净买额/买卖额/换手率/上榜原因/上榜后涨跌幅）
   - ⚠️ **无席位名称字段**，无法做量化席位过滤
   - 返回：`代码`、`名称`、`上榜日`、`解读`、`收盘价`、`涨跌幅`、`龙虎榜净买额`、`龙虎榜买入额`、`龙虎榜卖出额`、`上榜原因`

2. **龙虎榜基础列表（东方财富HTML pagedata — 2026-05-30实测验证）**
   - ✅ 主页 `https://data.eastmoney.com/stock/lhb.html` HTML 中内嵌 `pagedata` JSON
   - ✅ `data['sbgg_all']['result']['data']` 路径已验证有效
   - ✅ 正确正则：`re.search(r'pagedata\s*=\s*(\{.*?\});', html, re.DOTALL)`
   - ❌ 旧正则 `re.search(r'"data":\(\{\\\[', html)` 从未匹配成功过，不要用
   - 字段含：涨跌幅(CHANGE_RATE)、上榜次数(ONLIST_NUM)、代码、名称

3. **龙虎榜明细 datacenter API（⚠️ 2026-06-04全线失效）**
   - ❌ `RPT_BILLBOARD_DAILYDETAILSBUY` — 返回9501，接口已下线
   - ❌ `RPT_DAILYBILLBOARD` — 返回9501，接口已下线
   - ❌ `RPT_LHB_ALLSTOCKS` — 返回9501，接口已下线
   - **结论**：datacenter API 所有龙虎榜报表全部不可用

4. **龙虎榜席位数据** — `mx_data.py`（✅ 2026-06-04实测验证成功）
   - `mx_data.MXData().query('{name}今日龙虎榜席位')` **可以获取席位名称列表**
   - 返回格式：`rawTable` 用数字key('0','1','2'...), `nameMap` 映射到席位名字符串
   - 拉萨量化席位识别：遍历所有席位名，关键词含"拉萨"即计数
   - ⚠️ **查询间隔需≥3秒**，否则频率限制返回空
   - ⚠️ **2026-06-04实测：datacenter API全部9501失效，MX席位查询是当前唯一可用的席位数据源**

---

## 量化席位识别规则

### 4个层级识别量化席位

**1. 席位名字（最简单，准确率80%+）**
拉萨天团 = 东方财富互联网开户量化席位群，同一只股票出现 ≥2个拉萨席位 = 量化确认：
- 东方财富拉萨团结路第一/第二
- 东方财富拉萨金融城南环
- 东方财富拉萨东环路第一/第二
- 东方财富拉萨山南香曲东路
- 东方财富拉萨娘猜曲镇路
- 东方财富拉萨当雄县虎空路

**规则：龙虎榜上拉萨席位≥2个 → 量化，直接排除**

**2. 行为模式（准确率70%）**
- 一日游：今天买明天卖（对比连续2天龙虎榜）
- 多席位协同：3-5个陌生营业部同日买入
- 金额均匀：买1=买2=买3≈相同金额（分仓策略）

**3. DDX数据辅助判断**
- DDX5大幅为负 + 股价连板 = 量化出货
- DDX持续微正微负 = 量化对倒
- DDX突然大幅为正 + 放量 = 量化进场信号

**4. 分时图形态（盘中识别）**
- 锯齿形：1分钟内频繁上下0.1-0.3%
- 精准挂单：整数位密集挂单
- 秒级封板/炸板：14:57:58封板或14:59:59炸板

### 实战口诀
- 拉萨席位≥2个 → 量化，直接排除
- 同日多陌生营业部 → 可能量化分仓，警惕
- DDX连负+股价连板 → 量化出货，不碰
- 分时锯齿+秒级封板 → 量化操盘，远离

### 龙虎榜筛选规则
1. 量化席位≥2 → 排除
2. 重点关注：机构主封/主买、章盟主等知名游资重仓
3. 量化不锁仓，次日大概率卖出，所以量化主导的票没有"格局"

---

## 操作步骤

### Step 1 — 获取当日龙虎榜明细（akshare，基础列表）

**⚠️ 关键规则：同一只股票可能有多行记录（不同营业部席位），每行是一个营业部的买卖记录。必须先收集全部 rows → 按 `代码` 分组合并 `龙虎榜净买额` → 排序。禁止用单行NET直接做判断。**

```python
import akshare as ak, json
from collections import defaultdict

date = '20260601'  # 8位数字，非 '2026-06-01'
df = ak.stock_lhb_detail_em(start_date=date, end_date=date)
# 返回列: 代码/名称/上榜日/解读/收盘价/涨跌幅/龙虎榜净买额/龙虎榜买入额/龙虎榜卖出额/上榜原因
# ⚠️ 注意：df['龙虎榜净买额'] 可能是 Str 带万/亿单位，需转换

# 合并同股票多席位数据
net_by_code = defaultdict(float)
buy_by_code = defaultdict(float)
sell_by_code = defaultdict(float)
reason_by_code = {}  # 上榜原因，保留第一个即可

for _, row in df.iterrows():
    code = row['代码']
    net = row['龙虎榜净买额']
    buy = row['龙虎榜买入额']
    sell = row['龙虎榜卖出额']
    def to_float(v):
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).replace(' ', '')
        if '亿' in s:
            return float(s.replace('亿', '').replace(',', '')) * 1e8
        if '万' in s:
            return float(s.replace('万', '').replace(',', '')) * 1e4
        return float(s.replace(',', ''))
    net_by_code[code] += to_float(net)
    buy_by_code[code] += to_float(buy)
    sell_by_code[code] += to_float(sell)
    if code not in reason_by_code:
        reason_by_code[code] = row.get('上榜原因', '')

# 排序（按净买额绝对值降序）
sorted_codes = sorted(net_by_code.keys(), key=lambda c: abs(net_by_code[c]), reverse=True)
print('净买额TOP10:')
for code in sorted_codes[:10]:
    name = df[df['代码']==code]['名称'].iloc[0]
    reason = reason_by_code.get(code, '')
    print(f"  {name}({code}) 净买{net_by_code[code]/1e8:.2f}亿 原因:{reason}")
```

### Step 2 — 量化席位过滤（MX席位查询，已验证可用）

> ✅ **2026-06-04验证：mx_data龙虎榜席位查询成功返回席位名称，datacenter API全部9501失效。**
> **席位名称查询必须走MX接口**，不能用datacenter API。

```python
import sys, time, os
sys.path.insert(0, 'C:/Users/June/AppData/Local/hermes/skills/dfcf/mx-data')
lines = open('C:/Users/June/AppData/Local/hermes/.env').readlines()
os.environ['MX_APIKEY'] = lines[485].split('=',1)[1].strip()
import mx_data

LASA_KW = ['拉萨', '量化基金', '量化打板', 'T王']

def get_lasa_count(name):
    """查询某股票今日龙虎榜席位数，返回拉萨量化席位数量"""
    time.sleep(3.5)
    try:
        r = mx_data.MXData().query(f'{name}今日龙虎榜席位')
        if not r or not r.get('success'):
            return -1  # 查询失败
        dto_list = r.get('data',{}).get('data',{}).get('searchDataResultDTO',{}).get('dataTableDTOList',[])
        seats = []
        for dto in dto_list:
            raw = dto.get('rawTable', {})
            nm = dto.get('nameMap', {})
            for k, v in raw.items():
                if k == 'headName' or not isinstance(v, list): continue
                seat = nm.get(k, k)
                seats.append(seat)
        lasa = sum(1 for s in seats if any(kw in s for kw in LASA_KW))
        return lasa, seats
    except Exception as e:
        return -1, []

# 使用示例
lasa, seats = get_lasa_count('通鼎互联')
print(f'拉萨席位数={lasa}, 全部席位={seats}')
# lasa >= 2 → 量化嫌疑，排除
# lasa == 1 → 降仓，快进快出
# lasa == 0 → 正常
```

**已知关键规则**：
- `dataTableDTOList` 中每个元素是一个席位（一个dict）
- `rawTable` 的key是'0','1','2'...（行号），**不是**f88/f89等
- `nameMap` 映射 key → 席位中文名
- ⚠️ 查询间隔必须≥3秒，否则返回空（频率限制）

### Step 3 — 查询DDX大单动向

> ⚠️ **datacenter API 已下线，席位名称无法获取。DDX数据从 mx_data.MXData().query() 获取（见下方）。**

**⚠️ 陷阱：DDX 数据路径是 `data['data']['searchDataResultDTO']['dataTableDTOList'][0]['table']`，其中 f88=当日DDX、f89=当日DDY、f90=当日DDZ。查询间隔需 ≥3秒防频率限制。**

```python
def get_ddx(name):
    """返回 {当日DDX, 5日DDX, 10日DDX}"""
    d = {}
    for period in ['当日DDX', '5日DDX', '10日DDX']:
        time.sleep(2.5)
        try:
            r = mx_data.MXData().query(f'{name}{period}')
            if not r or not r.get('success'):
                continue
            dto_dict = r['data']['data'].get('searchDataResultDTO', {})
            for dto in dto_dict.get('dataTableDTOList', []):
                raw = dto.get('rawTable', {})
                nm = dto.get('nameMap', {})
                for k, v in raw.items():
                    if k == 'headName' or not isinstance(v, list):
                        continue
                    col = nm.get(k, '')
                    if 'DDX' in col and v and v[0] != '-':
                        d[col] = float(v[0])
        except:
            pass
    return d
```

### Step 4 — 综合评级输出

按以下规则输出推荐等级：

| 条件 | 评级 |
|------|------|
| 无量化席位 + DDX三周期全正 | ⭐⭐⭐ 强烈推荐 |
| 无量化席位 + DDX当日>1.5 + 5日正向 | ⭐⭐ 推荐 |
| 无量化席位 + DDX当日>0.5 | ⭐ 观察 |
| 量化席位≥2 | ⚠️ 排除 |

**注意：今日（2026-05-27）龙虎榜无一只达到拉萨席位≥2标准，所有票均通过量化过滤。此时评级以DDX三周期为主要依据。**

---

## 常见陷阱

1. **execute_code 中 import mx_data 失败**（`No module named 'pandas'`）——mx_data 依赖 pandas，但沙盒环境的 Python 无 pandas。**必须用 terminal 调用 `/c/Python314/python`** 执行含 mx_data 的脚本。
2. **频率限制**（status=112 "请求频率过高"）——`MXData()` 查询间隔需 ≥2.5秒，否则被限速。
3. **席位数据 `rawTable` 用数字 key**（'0','1','2'...）——不是字符串席位名，席位名在同级的 `nameMap` 中映射。
4. **北交所股票代码**（920012等）——`mx_data.py` 查询时需用**完整名称**（如"创达新材"），不能用纯数字代码。
5. **DDX数据缺失**——部分股票（如固德电材、族兴新材、步步高）在妙想库中无DDX数据，输出"无DDX数据"而非报错。
6. **龙虎榜数据方向判断**——**禁止用单行买入/卖出绝对值判断净买净卖**。同一只股票有多个席位时，必须先 `net_by_code[code]` 聚合所有席位的NET字段，再判断正负。**2026-06-01京能电力教训**：买2.52亿/卖2.30亿 → 合并NET=+0.22亿（不是-2.16亿）。

---

## 关键文件路径
- mx_data.py: `C:/Users/June/AppData/Local/hermes/skills/dfcf/mx-data/mx_data.py`
- .env: `C:/Users/June/AppData/Local/hermes/.env`（MX_APIKEY 在第486行）

## 参考数据
- `references/2026-05-27-lhb-review.md` — 2026-05-27 复盘完整结果，可作为输出格式参考
- `references/20260527_综合复盘报告_示例.md` — 综合复盘Markdown格式示例（资金面+逻辑面完整结构）

## mx_data 查询能力边界（重要）

以下字段**不存在**于妙想库，查了返回空或失败：
- ❌ `涨停原因` — 返回支撑/压力位，非文本原因
- ❌ `一字板`、`一字涨停`、`秒涨停`、`秒板` — 全部返回空
- ❌ `5分钟涨停`、`盘中涨停`、`尾盘涨停`、`涨停时间`、`涨停封板时间` — 全部返回空
- ❌ `板块涨停`、`热点板块`、`板块涨停家数` — 全部返回空
- ❌ `连板股`、`连续涨停`、`昨日涨停今日表现` — 全部返回空
- ⚠️ `昨日涨停` — 有数据，但只返回"涨停家数"数字，非明细

**涨停板结构必须用 akshare `stock_zt_pool_em()`**，不能用 mx_data 或 JSONP 搜索。

**龙虎榜数据优先用 datacenter API**：`RPT_DAILYBILLBOARD` 接口无需token，比HTML解析更可靠。

## 环境说明

- **akshare 已安装**：`/c/Python314/python -m pip install akshare`
- **涨停数据函数**：`akshare.stock_zt_pool_em(date='YYYYMMDD')` — 参数是8位数字字符串如 `'20260527'`
- ⚠️ execute_code 沙盒没有 pandas，无法 import mx_data；**必须用 terminal + `/c/Python314/python`**
- ⚠️ push2.eastmoney.com 被防火墙封锁，所有 `akshare.stock_individual_fund_flow` 等依赖 push2his 的函数会失败，换用 akshare 的其他接口绕过
- ✅ `创业板涨停` — 返回创业板涨停家数

如需**个股涨停时间、一字板识别、尾盘涨停筛选**，当前 mx_data 无法支持，需要：
1. 浏览器逐个打开个股分时详情页肉眼识别
2. 或通过聚宽/同花顺/通达信等平台分钟级 API 批量获取

## 东方财富涨停专题页变更

⚠️ `https://data.eastmoney.com/stock/zt.html` 已下架（返回404），**暂无可直接访问的涨停专题页URL**，数据需通过行情 API 或个股分时页面获取。

## 注意事项
- 拉萨席位关键词：拉萨团结路、拉萨金融城、拉萨东环路、拉萨山南、拉萨娘猜、拉萨当雄、拉萨虎空路、东方财富拉萨
- DDX当日为正=主力当日净买入；DDX为负=主力当日净卖出
- 5日/10日DDX连续为正=主力持续买入，中期强势
- 量化席位股票次日大概率低开或砸盘，不值得格局
