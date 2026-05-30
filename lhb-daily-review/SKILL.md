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
   - ✅ **此API可用**（2026-05-29验证：返回94条记录）
   - ⚠️ **无 `OPERATEDEPT_NAME` 字段**，无法做量化席位过滤
   - 返回：`代码`、`名称`、`上榜日`、`解读`、`收盘价`、`涨跌幅`、`龙虎榜净买额`、`龙虎榜买入额`、`龙虎榜卖出额`、`上榜原因`

2. **龙虎榜明细 datacenter API（⚠️ 2026-05-29失效）** — `https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_BILLBOARD_DAILYDETAILSBUY`
   - ❌ **2026-05-29实测：返回 code=9501（报表配置不存在）**
   - 曾经可用字段：`SECURITY_CODE`、`SECURITY_NAME`、`NET`（净买额/元）、`OPERATEDEPT_NAME`（营业部名称）
   - **当此API失效时，无法通过API核实拉萨量化席位**，龙虎榜筛选结果需标注"席位风险未知"
   ```
   https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_BILLBOARD_DAILYDETAILSBUY&columns=ALL&filter=(TRADE_DATE='YYYY-MM-DD')&pageNumber=1&pageSize=300&sortTypes=-1&sortColumns=NET&source=WEB&client=WEB
   ```
   - 字段：`SECURITY_CODE`（代码）、`SECURITY_NAME`（名称）、`NET`（净买额/元）、`BUY`（买入额/元）、`OPERATEDEPT_NAME`（营业部名称）、`EXPLANATION`（上榜原因）
   - ✅ **此API可访问**，字段完整（含营业部名称，可做量化席位过滤）
   - ⚠️ **pageSize=300 不能保证返回300条**：实际数量由服务器决定（实测有时只返回28条）
   - **同一只股票可能有多行记录**（不同营业部席位），每行是一个营业部的买卖记录
   - **正确流程**：先收集全部 rows → 按 `SECURITY_CODE` 分组合并 `NET` → 排序
   - **名称获取**：腾讯行情API（不依赖push2），批量获取：`https://qt.gtimg.cn/q=sh600330,sz000063`

2. **龙虎榜基础列表（akshare备用）** — `akshare.stock_lhb_detail_em(start_date='YYYYMMDD', end_date='YYYYMMDD')`
   - 返回：`代码`、`名称`、`上榜日`、`解读`、`收盘价`、`涨跌幅`、`龙虎榜净买额`、`龙虎榜买入额`、`龙虎榜卖出额`、`上榜原因`
   - ⚠️ **无 `OPERATEDEPT_NAME` 字段**，无法做量化席位过滤
   - 适用场景：只需净买额排名，不需要席位明细时

3. **涨停板结构** — **akshare `stock_zt_pool_em(date='YYYYMMDD')`**（最准确）
   - ⚠️ 日期格式为 `20260527`（8位数字字符串，不是`2026-05-27`）
   - 字段：代码/名称/涨跌幅/首次封板时间/最后封板时间/炸板次数/连板数/所属行业/成交额/流通市值

4. **龙虎榜席位数据** — `mx_data.py`（⚠️ push2.eastmoney.com被封禁，此路不通）

5. **DDX大单动向** — `mx_data.py` 的 `MXData().query('{name}DDX')`

6. **模拟持仓** — `mx_data.py` 的 `MXData().query('模拟持仓')`

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

### Step 1 — 获取当日龙虎榜基础列表

从东方财富龙虎榜页面 HTML 中提取 `<script>pagedata=...</script>` 内嵌数据：

**⚠️ 陷阱：HTML 中的 JSON 结构是 `data['sbgg_all']['result']['data']`，不是 `data['sbgg_all']['data']`**

```python
import urllib.request, re, json

url = 'https://data.eastmoney.com/stock/lhb.html'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')

# 正确方式：用正则直接提取 "data":[...] 数组段，再 json.loads
m = re.search(r'"data":(\[\{[^ \]][^\]]*\])', html)
if m:
    rows = json.loads(m.group(1))
    # 字段: SECURITY_CODE, SECURITY_NAME_ABBR, CHANGE_RATE, BILLBOARD_NET_AMT 等
    rows.sort(key=lambda x: float(x['CHANGE_RATE']), reverse=True)
    # rows[0] -> {'SECUCODE': '000010.SZ', 'SECURITY_CODE': '000010', 'SECURITY_NAME_ABBR': '*ST美丽', 'CHANGE_RATE': -4.9751, ...}
```

### Step 2 — 量化席位过滤（拉萨席位≥2排除）

**⚠️ 陷阱：`searchDataResultDTO` 是 dict（含 `dataTableDTOList`），不是 list。席位数据在 `dataTableDTOList[0]`，`rawTable` 用数字 key 存席位，`nameMap` 是席位名映射。`MXData()` 每次查询需间隔 ≥2.5秒防频率限制。**

```python
import sys, os, time
sys.path.insert(0, 'C:/Users/June/AppData/Local/hermes/skills/dfcf/mx-data')
os.environ['MX_APIKEY'] = '你的MX_APIKEY'
import mx_data

拉萨_KEYWORDS = ['拉萨团结路','拉萨金融城','拉萨东环路','拉萨山南','拉萨娘猜','拉萨当雄','拉萨虎空路','东方财富拉萨']

def filter_quant(name):
    """返回 (拉萨席位列表, 全部席位列表)"""
    time.sleep(2.5)  # 防频率限制
    r = mx_data.MXData().query(f'{name}今日龙虎榜席位')
    if not r or not r.get('success'):
        return [], []
    dto_dict = r['data']['data'].get('searchDataResultDTO', {})
    dto_list = dto_dict.get('dataTableDTOList', [])
    if not dto_list:
        return [], []
    dto = dto_list[0]  # 第一个 table 是龙虎榜席位
    name_map = dto.get('nameMap', {})
    raw = dto.get('rawTable', {})
    all_seats, lasa_seats = [], []
    for k, v in raw.items():
        if k == 'headName' or not isinstance(v, list):
            continue
        seat_name = name_map.get(k, '')
        if seat_name:
            all_seats.append(seat_name)
            if any(lk in seat_name for lk in 拉萨_KEYWORDS):
                lasa_seats.append(seat_name)
    return lasa_seats, all_seats
```

### Step 3 — 查询DDX大单动向

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
6. **模拟账户下单** —— 用 `mx_data.py` 的 `MXData().query('模拟下单', code, volume)` 接口（见 mx-moni skill）。

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
