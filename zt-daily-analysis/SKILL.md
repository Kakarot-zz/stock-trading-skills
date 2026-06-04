---
name: zt-daily-analysis
description: 当日涨停板结构分析。输入任意日期，输出涨停时间结构分类（竞价一字板/5分钟快板/尾盘板）、炸板率、连板股、板块情绪，筛选尾盘涨停中板块未高潮的标的。
category: finance
---

# 当日涨停板结构分析 Skill

## 触发条件
- 用户说"涨停票分析"、"涨停板分析"
- 用户说"帮我分析涨停"、"涨停结构"
- ⚠️ 不包括"今日复盘"/"复盘" — 那是 daily-review skill 的触发词

### 数据源优先级（按可用性）

**第1选择：涨停啦（APP专用，无公开Web/API）**
- ⚠️ **2026年5月实测：ztbang.com域名已被劫持为博彩网站，所有已知域名变体全部失效**
  - `http://ztbang.com` → 200但内容为"爱游戏体育"（域名已出售）
  - `http://zhangtingla.com` → 502
  - `https://ztb.kim` → SSL错误
  - 浏览器直接访问 → 全部失败
- **涨停啦现为APP专用**，无公开Web地址，无官方API
- 如需涨停啦数据，**必须由用户从APP截图或手工提供**
- **当涨停啦可用时，必须用它替换akshare的炸板次数和连板数字段**

**第2选择：MX选股接口（涨停啦不可用时的次选，有局限）**
```bash
cd /c/Users/June/AppData/Local/hermes/skills/dfcf/mx-xuangu
/c/Python314/python mx_xuangu.py "今日涨停 非一字板 非ST 非北交所 主板"
```
- 输出CSV：`C:/root/.openclaw/workspace/mx_data/output/mx_xuangu_今日涨停_非一字板_非ST_非北交所_主板.csv`
- **优点**：包含"涨停方式"字段（自然涨停/回封板/T字涨停），封板时间精确到秒
- **缺点**：
  - 总数与akshare不一致（MX选股91只非一字板主板，akshare总102只，差值为创业板/科创板/北交所/一字板）
  - **没有炸板次数字段**（仅有涨停方式，不能区分"自然涨停封死"和"自然涨停炸过板"）
  - **JSON返回结构特殊**：`data.data.allResults.result.dataList` 数组为空，实际行数在 `totalRecordCount` 字段（显示91），数据可能存储在其他嵌套路径下
- **适用场景**：需要封板时间、涨停方式（非精确炸板次数）时的参考数据

**第3选择：akshare（防火墙封锁涨停啦时的备选）**
```bash
/c/Python314/python -c "import akshare; print(akshare.stock_zt_pool_em(date='YYYYMMDD').to_string())"
```
- **⚠️ 日期格式必须是8位数字字符串**：`'20260527'`，不是`'2026-05-27'`
- **⚠️ 不要用JSONP搜索文章的方式获取涨停数据** — 文章搜索曾报61只，实际只有47只，数据不准确
- **⚠️ 不要用东方财富专题页** — `data.eastmoney.com/stock/zt.html` 已下架（404）
- ⚠️ **akshare炸板次数与涨停啦存在显著差异**（如勘设股份akshare报25次，实际应为少数几次），当涨停啦可用时以其为准

### akshare 返回字段说明
| 字段 | 含义 |
|------|------|
| 代码 | 股票代码，如`002484` |
| 名称 | 股票名称，如`江海股份` |
| 涨跌幅 | 涨幅百分比（**akshare此字段为今日真实涨跌幅，可信**） |
| 首次封板时间 | 整数如`92500`表示09:25:00，**需补零后按小时分段** |
| 最后封板时间 | 如`140949`表示14:09:49 |
| 炸板次数 | 盘中炸板次数（>0=炸板股） |
| 连板数 | 连续涨停板数（>1=连板股） |
| 所属行业 | 申万行业分类 |
| 封板资金 | 封板金额（元） |
| 成交额 | 总成交额（元） |

### 腾讯行情涨跌幅字段不可用（重要陷阱）

**⚠️ 腾讯行情qt.gtimg.cn的涨跌幅字段（data[31]）对涨停股存在系统性失真。**

实证案例（2026-05-28）：
- 002428云南锗业：akshare显示+10.00%（真实涨停），腾讯行情显示+8.17%
- 600151航天机电：akshare显示+10.01%（真实涨停），腾讯行情显示+1.37%
- 600162香江控股：akshare显示+9.96%（真实涨停），腾讯行情显示+0.23%
- 603986兆易创新：akshare显示+10.01%（真实涨停），腾讯行情显示-31.18%（严重错误）
- 002491通鼎互联：真实-3.34%，腾讯行情显示+1.88%（方向错误）

**正确做法**：用腾讯K线前复权收盘价自行计算涨跌幅：
```python
# 腾讯K线字段[1]=收盘价，[2]=开盘价，[3]=最高，[4]=最低，[5]=成交量(手)
# 涨跌幅 = (今收 - 昨收) / 昨收 * 100
# 成交额 = 成交量(手) * 100 * 收盘价
for k in klines[-2:]:
    close = float(k[1])
    vol_shou = float(k[5])  # 手
    amount_yi = vol_shou * 100 * close / 1e8
```

**结论**：判断股票是否涨停必须用akshare stock_zt_pool_em的涨跌幅字段，或用腾讯K线收盘价自行计算。详见 `references/tencent-kline-pitfall.md`。

---

## 涨停时间结构分类

### 时间段定义
| 类型 | 时间范围 | 判断逻辑 |
|------|---------|---------|
| **一字板** | 09:25~09:30 | `首次封板时间`字符串前2位在`09`，第3-4位在`25~30` |
| **5分钟快板** | 09:31~09:35 | `首次封板时间`字符串前2位在`09`，第3-4位在`31~35` |
| **早盘涨停** | 09:36~13:59 | 其他早板时段 |
| **尾盘涨停** | 14:00起 | `首次封板时间`字符串前2位 `>= '14'` |

### 时间解析方法（已验证）
```python
def to_min(t):
    """将HHMMSS字符串转为当日分钟数，如'095106' -> 596"""
    h = int(t[:2]); m = int(t[2:4]); s = int(t[4:6])
    return h * 60 + m

df['首分'] = df['首次封板时间'].apply(to_min)

yizi  = df[(df['首分'] >= 525) & (df['首分'] <= 530)]   # 09:25~09:30
quick = df[(df['首分'] >= 531) & (df['首分'] <= 535)]   # 09:31~09:35
zaopan= df[(df['首分'] >= 536) & (df['首分'] <= 690)]   # 09:36~11:30
wupan = df[(df['首分'] >= 691) & (df['首分'] <  780)]   # 11:31~13:00
wanpan= df[df['首分'] >= 780]                              # 13:00起
```
> ⚠️ akshare时间格式为字符串HHMMSS（如`'095106'`），需先转换再分段。

---

## 板块情绪评估

统计每只涨停股的所属行业，分类：

| 板块涨停数 | 情绪标注 |
|-----------|---------|
| ≥5只 | 🔥 高潮（板块过热，跟风板次日溢价低） |
| 3~4只 | ⚡ 较多（关注持续性） |
| 1~2只 | ✅ 正常 |
| 0只 | ➖ |

**规则：尾盘涨停 + 板块高潮 → 价值低；尾盘涨停 + 板块正常 → 可关注**

---

## 综合评级规则

| 条件 | 评级 |
|------|------|
| 一字板 + 封死无炸板 + 板块正常 | ⭐⭐⭐ 强烈推荐 |
| 快板 + 封死无炸板 + DDX为正 | ⭐⭐ 推荐 |
| 早盘涨停 + 封死无炸板 + 板块正常 | ⭐ 观察 |
| 连板数≥2（板块高潮除外） | ⭐⭐ 连板价值 |
| 炸板次数≥10 | ⚠️ 封板质量差 |
| 尾盘涨停 + 板块高潮 | ❌ 排除 |
| 一字板 + 炸板>0 | ⚠️ 一字板≠封死，炸板股次 日溢价低，需结合连板数判断 |

## 一字板重要澄清

**一字板不等于封死无炸板**。akshare的`炸板次数`字段记录的是盘中炸板次数，一字板可能炸板后再封回（典型如中京电子一字板炸4次、香江控股一字板炸1次）。

判断逻辑：
- 一字板 + 连板数≥2 + 炸板次数=0：最强格局
- 一字板 + 连板数≥2 + 炸板次数>0：情绪分歧，连板预期降低
- 一字板 + 炸板次数>0 + 次日板块高潮：❌ 排除

## 尾盘涨停的重要澄清

**今日市场（2026-05-27）真实尾盘板数量为0只**。多数14:00后封板的标的实为炸板后的修复封板（如华能蒙电13:02炸板后13:53封回，华电辽能13:02炸板后13:58封回），而非真正的"尾盘情绪板"。

判断标准修正：
- 真正尾盘板：首次封板时间就在14:00后，当日未在更早时段封板
- 修复封板：早盘或午盘曾炸板，尾盘重新封住（不属于尾盘涨停范畴）
- 尾盘涨停 + 板块涨停≤2：✅ 低位尾盘板，关注次日溢价
- 修复封板：按原首次封板时间判断类型（如09:31封板后炸，14:00再封，算5分钟快板非尾盘板）

---

## 操作步骤

### Step 1 — 获取涨停数据
```python
import akshare as ak
df = ak.stock_zt_pool_em(date='YYYYMMDD')  # 8位数字字符串
print(f"总数: {len(df)}")
```

### Step 2 — 时间结构分类
```python
df = df.reset_index(drop=True)  # 必须重置索引，否则后续index操作报错
df['首次HHMM'] = df['首次封板时间'].astype(str).str.zfill(6).str[:4].astype(int)

# 一字板：09:25~09:30
yzb = df[(df['首次HHMM'] >= 925) & (df['首次HHMM'] <= 930)]
# 5分钟快板：09:31~09:35
kb = df[(df['首次HHMM'] >= 931) & (df['首次HHMM'] <= 935)]
# 尾盘涨停：14:00起（真正尾盘板，首次封板时间即在14:00后）
wb = df[df['首次HHMM'] >= 1400]
# 早盘涨停：其余所有非尾盘的涨停
is_yzb_or_kb_or_wb = ((df['首次HHMM'] >= 925) & (df['首次HHMM'] <= 930) | 
                      (df['首次HHMM'] >= 931) & (df['首次HHMM'] <= 935) | 
                      (df['首次HHMM'] >= 1400))
db = df[~is_yzb_or_kb_or_wb]
```

> ⚠️ **pandas index OR (`|`) 陷阱**：`yzb.index | kb.index | wb.index` 当三个Series长度不同时会报`ValueError: operands could not be broadcast together with shapes (8,) (12,)`。**必须用布尔Series代替index做逻辑运算**，如上使用`is_yzb_or_kb_or_wb`布尔Series再取反。

**⚠️ 修复封板判断**：如果`炸板次数>0`且`最后封板时间`在14:00后，但`首次封板时间`在早盘（如华能蒙电首次09:31，尾盘13:53封回），这种"修复封板"应按`首次封板时间`分类，不算尾盘涨停。

### Step 3 — 板块情绪统计
```python
bk = df.groupby('所属行业').size().sort_values(ascending=False)
high_sectors = set(bk[bk >= 5].index)  # 高潮板块
normal_sectors = set(bk[(bk >= 1) & (bk < 5)].index)
```

### Step 4 — 综合筛选（尾盘涨停 + 板块非高潮）
```python
# 尾盘涨停中板块未高潮的标的
for _, row in wb.iterrows():
    sector = row['所属行业']
    if sector not in high_sectors:
        print(f"可关注: {row['名称']}({row['代码']}) {row['所属行业']}")
```

### Step 5 — 连板股输出（⚠️ 必须使用交叉验证后的连板数）
```python
lb = df[df['连板数'] > 1].sort_values('连板数', ascending=False)
for _, r in lb.iterrows():
    zb_flag = f"炸板{r['炸板次数']}次" if r['炸板次数'] > 0 else "封死"
    # ⚠️ 使用 verified_lb_map 中已验证的连板数，不直接用 r['连板数']
    verified = verified_lb_map.get(r['代码'], r['连板数'])
    print(f"{r['名称']}({r['代码']}) {verified}连板 {zb_flag}")
```

### Step 5b — 连板数交叉验证（强制步骤，⚠️ 必须先于此步骤再进行其他所有操作）

> **2026-06-03 新增，2026-06-04 实战修正：此步骤是所有后续报告数据的基础。必须在输出任何连板相关信息（连板股表格/尾盘涨停分类/预期差逆势股等）之前完成。**

**执行时机**：获取涨停池后，**第一步**就做交叉验证，用验证后的真实连板数替代akshare原始字段，再进行后续所有分析。

**交叉验证方法**：

```python
import akshare as ak
yesterday = '20260602'  # 当前日期的上一交易日
zt_y = ak.stock_zt_pool_em(date=yesterday)
yesterday_zt_codes = set(zt_y['代码'].astype(str).tolist())

# 对每只连板股验证昨日是否在涨停池中
# 昨日涨停池无此股 → 当日是首板（连板数必须=1）
# 昨日涨停池有且连板数=x → 今日连板数=x+1
for _, r in lb.iterrows():
    code = str(r['代码'])
    if code in yesterday_zt_codes:
        yz = zt_y[zt_y['代码'].astype(str) == code].iloc[0]
        print(f"{r['名称']}: 昨日连板={yz['连板数']} → 今日应为{yz['连板数']+1}连板, 实际={r['连板数']}")
    else:
        print(f"{r['名称']}: 昨日未涨停, 当日应为首板, 实际={r['连板数']} ← 异常!")
```

**常见错误案例（2026-06-02教训）**：
- 东杰智能被写成"2连板创业板"→ 核实：东杰智能06-01无涨停记录，06-02为首板炸48次，非连板
- 郑州煤电被写成"一字板封死"→ 核实：首次封板09:31（非09:25~09:30竞价），炸板2次，实为首板非一字板

**此步骤不能跳过**：akshare连板数字段来自当日行情系统，非历史推算，必须交叉验证才能排除异常值。

### Step 6 — 炸板股TOP10
```python
zb = df[df['炸板次数'] > 0].sort_values('炸板次数', ascending=False)
for _, r in zb.head(10).iterrows():
    t_first = str(r['首次封板时间']).zfill(6)
    t_last = str(r['最后封板时间']).zfill(6)
    print(f"{r['名称']} 炸板{r['炸板次数']}次 首次:{t_first[:2]}:{t_first[2:4]} 最后封板:{t_last[:2]}:{t_last[2:4]}")
```

### Step 6 — 炸板股TOP10
```python
zb = df[df['炸板次数'] > 0].sort_values('炸板次数', ascending=False)
for _, r in zb.head(10).iterrows():
    t_first = str(r['首次封板时间']).zfill(6)
    t_last = str(r['最后封板时间']).zfill(6)
    print(f"{r['名称']} 炸板{r['炸板次数']}次 首次:{t_first[:2]}:{t_first[2:4]} 最后封板:{t_last[:2]}:{t_last[2:4]}")
```

---

## DDX数据（可选补充）

如需DDX数据，通过mx_data查询（注意频率限制，间隔≥3秒）：

```python
import sys, time
sys.path.insert(0, 'C:/Users/June/AppData/Local/hermes/skills/dfcf/mx-data')
import mx_data
with open('C:/Users/June/AppData/Local/hermes/.env') as f:
    for line in f:
        if line.startswith('MX_APIKEY'):
            api_key = line.strip().split('=',1)[1].strip()
            break
client = mx_data.MXData(api_key=api_key)

def get_ddx(code_or_name, periods=['DDX', '5日DDX', '10日DDX', 'DDY']):
    """查询指定周期的DDX/DDY/DDZ数据。

    MX返回格式：每个dataTableDTOList项的table是一个dict，
    key是行索引字符串，value是对应行所有列值组成的列表。
    headName是单元素数组如['2026-06-03 18:25']，不是标准列名。

    返回格式：{period: value}，value为字符串如'-1.951'，'-'表示无数据
    """
    result = {}
    for period in periods:
        r = client.query(f'{code_or_name} {period}')
        dt = r.get('data',{}).get('data',{}).get('searchDataResultDTO',{}).get('dataTableDTOList',[])
        if not dt:
            result[period] = '-'
            continue
        table = dt[0].get('table', {})
        # 遍历table，取第一行数据（row[0]）
        for idx, row in table.items():
            if idx == 'headName' or not isinstance(row, list):
                continue
            result[period] = row[0] if row else '-'
            break
        else:
            result[period] = '-'
        time.sleep(3)
    return result

# 示例输出：
# get_ddx('002491')
# {'DDX': '-1.951', '5日DDX': '1.721', '10日DDX': '-1.303', 'DDY': '0.622'}
```

**关键解析规则（已验证 2026-06-03）**：
- MX DDX返回的table key是行号（如'0','1','2'），**不是**f88/f89/f90
- `headName`是单元素数组如`['2026-06-03 18:25']`，不是标准列名
- 每行数据直接用`row[0]`取值（第一个列值=DDX/DDY/DDZ的值）
- 5日DDX/10日DDX/DDY需要单独查询，字段名格式：`'5日DDX'`, `'10日DDX'`, `'5日DDY'`, `'10日DDY'`

**⚠️ 频率限制：每次查询间隔≥3秒，否则返回空数据。5日/10日DDX间隔也需≥3秒。**

**⚠️ DDX值含义**：
- DDX < 0：主力净流出
- DDX > 0：主力净流入
- DDZ < -20：特大单深度流出（高度警惕）
- DDY > 0：散户短线活跃（可能是主力洗盘）

---

### 涨停啦不可用时的处理流程（更新版）

当涨停啦APP数据无法通过接口获取时：

1. **先试MX选股接口**：`mx_xuangu.py "今日涨停 非一字板 非ST"` 获取91只详细封板数据（含涨停方式字段）
2. **用akshare作为炸板/连板数据的唯一来源**（技术限制，无其他渠道）
3. **在报告开头注明**：涨停啦不可访问，数据以akshare为准，炸板次数仅供参考
4. **告知用户**：如有涨停啦APP截图可手工提供用于核对

### 常见陷阱

1. **日期格式错误** — `stock_zt_pool_em(date='2026-05-27')` 返回空，必须用`'20260527'`
2. **⚠️ 连板数字段系统性bug**：当股票昨日为首板但今日再次涨停时会错误显示为2连板。**必须用昨日涨停池交叉验证**：昨日不在涨停池→今日连板数=1（首板）。实测通鼎互联(002491)、双星新材(002585)均因此bug被错误标记。**此步骤是所有后续分析的第一步，必须先完成。**
3. **首板完整列表**：用户明确要求列出全部70只首板股，格式为（股票/代码/行业/换手/炸板/封板时间/备注），不可省略
4. **⚠️ 混淆"某股在某天涨停"和"某天哪些股涨停" — 最常见 factual error**：
   - `stock_zt_pool_em(date='20260529')` 的含义：**当天（5/29）有哪些股票涨停**，返回49只股票列表
   - **不要**把一只股票的涨停历史（如05-28涨停）错误安在另一日期（05-29）上
   - **正确流程**：先确认目标日期涨停池（`stock_zt_pool_em(date='YYYYMMDD')`），逐只检查持仓股是否在列
   - **如果持仓股不在当天涨停池**：它当天**没有涨停**，用MX接口日线数据（收盘价/涨跌幅）描述走势
   - **实证教训（2026-06-02）**：华塑控股+4.67%和通鼎互联+8.15%被错误描述为"今日涨停"——两只均不在06-02涨停池67只中，实为非涨停跟风股
3. **连板数判断必须交叉验证（2026-06-02新增）**：
   - 判断"连板数"之前，必须先用`stock_zt_pool_em(date='yesterday')`确认昨日涨停池中有没有这只
   - 昨日涨停池无记录 → 当日是首板（连板数=1），不可能是连板
   - **实证**：东杰智能06-02涨停被写成"2连板创业板"——错误。核实：东杰智能06-01无涨停记录，06-02为首板炸48次，非连板
   - **实证**：郑州煤电06-02被写成"一字板封死"——错误。核实：首次封板09:31（非09:25~09:30竞价），炸板2次，实为首板非一字板
4. **一字板判断：首次封板时间必须在09:25~09:30**：
   - 09:31封板 = 5分钟快板，不是竞价一字板
   - 09:25~09:30 = 竞价封板（一字板），无论后续是否炸板
5. **一字板=封死是误解** — 一字板完全可能炸板（如中京电子炸4次），需同时看炸板次数和连板数

### push2封禁时的实时行情查询

> ⚠️ 当 push2.eastmoney.com 被封禁导致 akshare `stock_zh_a_spot_em` 等函数失败时，使用 Tencent `qt.gtimg.cn` 替代方案，详见 `references/qt-gtimg-workaround.md`。
>
> **注意**：腾讯行情的涨跌幅字段（data[31]）对涨停股有系统性偏差，但**现价/成交量/今开/最高/最低**等字段正常。涨停判断用akshare，其余字段可用腾讯。

---

## 综合复盘报告格式（与历史报告保持一致）

涨停板结构是综合复盘报告（`YYYYMMDD_综合复盘报告.md`）的一部分，位于 **资金面** 章节内。完整报告节构：

```
## 资金面
### 龙虎榜 — 涨幅前15名（量化过滤后）
### 涨停板结构
#### 一字板（09:25~09:30 竞价封板）N只
#### 5分钟快板（09:31~09:35）N只
#### 尾盘板（14:00之后）N只
#### 连板股一览（N只）
### 首板完整列表（70只）

> ⚠️ 用户明确要求：首板股票需列出完整列表，格式与其他表格一致（股票/代码/行业/换手/炸板/封板时间/备注）

| 股票 | 代码 | 行业 | 换手 | 炸板 | 封板时间 | 备注 |
|------|------|------|------|------|---------|------|
| （70条完整记录） | — | — | — | — | — | — |

### 预期差逆势股
### 炸板关注
### 创业板 + 北交所
### 主流板块确认
### 预期管理
```

### 涨停板结构表格格式规范

**连板股表格列**：
```
| 股票 | 代码 | 连板 | 首次封板 | 炸板 | 行业 | 涨停原因 |
```
- 涨停原因：来自龙虎榜上榜原因（`stock_lhb_detail_em`）或强势股入选理由（`stock_zt_pool_strong_em`），见下方"涨停原因3-tier获取方法"

**首板完整列表表格列**：
```
| 股票 | 代码 | 行业 | 换手 | 炸板 | 封板时间 | 涨停原因 |
```
- **必须包含涨停原因列**，不可省略
- 按换手率降序排列
- 涨停原因3-tier获取方法见下方专门章节

**尾盘涨停表格列**：
```
| 股票 | 代码 | 行业 | 封板时间 | 涨停原因 |
```

**一字板 / 5分钟快板表格列**：
```
| 股票 | 行业 | 封板状态 | 连板 |
```
- 封板状态：`封死 ✅` 或 `炸N次 ⚠️`

---

## 涨停原因3-tier获取方法（2026-06-04更新）

> ⚠️ **必须执行此步骤**。涨停原因列不能留空，必须通过以下3层方法全部填充。

### Tier流程

```python
import akshare as ak

# ========== Tier 1: 获取基础数据 ==========
zt = ak.stock_zt_pool_em(date='YYYYMMDD')
zt['代码'] = zt['代码'].astype(str).str.zfill(6)

lhb = ak.stock_lhb_detail_em(start_date='YYYYMMDD', end_date='YYYYMMDD')
lhb['代码'] = lhb['代码'].astype(str).str.zfill(6)

strong = ak.stock_zt_pool_strong_em(date='YYYYMMDD')
strong['代码'] = strong['代码'].astype(str).str.zfill(6)

# ========== Tier 2: 构建原因字典 ==========
lhb_reason = dict(zip(lhb['代码'], lhb['上榜原因']))
strong_reason = dict(zip(strong['代码'], strong['入选理由']))
all_reasons = {**strong_reason, **lhb_reason}  # 合并，lhb优先

# ========== Tier 3: 填充涨停原因 ==========
def get_reason(code):
    if code in all_reasons:
        return all_reasons[code]
    # 手动补充（板块/题材关键词）
    manual = {
        '603500': '超级电容概念',
        '002213': '存储芯片概念',
        '003043': '光刻机概念',
        '000536': '股东持股司法处置',
        '001376': '定增审核通过',
        '600868': '电力板块首板',
        '600828': '零售板块首板',
        '002590': '汽车零部首板',
        '000670': '其他电子首板',
        '600703': '光学光电首板',
        '000520': '航运港口首板',
        '002931': '通用设备首板',
        '002051': '专业工程首板',
        '603090': '通用设备首板',
        '002824': '工业金属首板',
        '002520': '通用设备首板',
        '002733': '军工电子首板',
        '603950': '汽车零部首板',
        '601666': '煤炭板块首板',
        '603286': '汽车零部首板',
        '002395': '塑料板块首板',
        '603903': '环境治理首板',
        '605060': '通用设备首板',
        '603005': '半导体封测',
        '603067': '化学原料首板',
        '603989': '电子元件首板',
        '603210': '汽车零部首板',
        '002570': '饮料乳品首板',
        '002981': '消费电子首板',
    }
    return manual.get(code, '首板')

zt['涨停原因'] = zt['代码'].apply(get_reason)
```

### 各数据源覆盖能力

| 数据源 | 覆盖涨停股 | 说明 |
|--------|-----------|------|
| `stock_lhb_detail_em` | ~47只 | 有上榜原因的标准文本 |
| `stock_zt_pool_strong_em` | ~29只首板 | 入选理由=涨停原因 |
| 手动补充 | ~33只 | 板块/题材关键词 |

### 上榜原因关键词分类

| 关键词 | 含义 |
|--------|------|
| 连续3日涨幅偏离20% | 主板连续3日异动 |
| 日涨幅偏离值达到7% | 单日10cm涨幅异常 |
| 日涨幅达到15% | 创业板涨停（20cm） |
| 科创板涨幅达到15% | 科创板20cm涨停 |
| 日换手率达到20% | 高换手率上榜 |
| 日价格振幅达到15% | 日内振幅大 |
| 连续3日涨幅偏离30% | 科创/创业连续3日涨30% |
| 北交所3日涨跌幅累计达±40% | 北交所特规 |
| 60日新高 | 强势股突破新高 |
| 近期多次涨停 | 强势股反复涨停 |
| 日收盘价涨幅偏离7% | 主板日涨幅偏离7% |

---

## Beta + 抗跌-修复分析（2026-06-04新增）

> 通过对比近13个交易日个股与上证指数的Beta，识别"个股跑输大盘但3日内完全收复"的刻意压盘模式，筛选有主力控盘迹象的首板股。

### 数据源
- 腾讯K线 `web.ifzq.gtimg.cn`（前复权日K）
- 上证指数K线同步获取

### 筛选标准

```
纳入条件：
  Beta 0.5~2.5 + 抗跌-修复次数≥2（稳健型）
  或 Beta>2.5 + 抗跌-修复次数≥2（高弹性激进型）

排除条件：
  RSI>85（超买区）
  市值>70亿（盘子太大）
```

### 抗跌-修复判断标准

当日个股满足以下全部条件=1次"抗跌"：
1. 上证指数当日涨幅 < -0.3%（大盘明显下跌）
2. 个股跌幅 < 上证跌幅的50%（跑赢大盘）
3. 随后3个交易日内，个股收复全部失地（回到压盘前价格）

```python
# 抗跌事件伪代码
for i in range(len(klines)-3):
    today = klines[i]
    index_today = index_klines[i]
    if index_today['change'] < -0.3:  # 大盘下跌
        if today['change'] < index_today['change'] * 0.5:  # 个股跑赢
            # 检查随后3日内是否收复
            low_after = min(k['low'] for k in klines[i:i+3])
            if low_after >= today['close']:  # 未跌破压盘价
                anti_count += 1
```

### Beta计算方法

```python
# 20日窗口收益率回归
import numpy as np

def calc_beta(stock_klines, index_klines, window=20):
    """计算相对上证指数的beta系数"""
    stock_ret = []
    index_ret = []
    for i in range(1, min(window+1, len(stock_klines))):
        s_close = float(stock_klines[-i][1])
        s_prev = float(stock_klines[-i-1][1])
        i_close = float(index_klines[-i][1])
        i_prev = float(index_klines[-i-1][1])
        stock_ret.append((s_close - s_prev) / s_prev)
        index_ret.append((i_close - i_prev) / i_prev)
    
    if len(stock_ret) < 10:
        return None
    # 线性回归: stock_ret = alpha + beta * index_ret
    beta = np.polyfit(index_ret, stock_ret, 1)[0]
    return beta
```

### 分析脚本参考

```bash
# beta_analysis2.py — 多前缀K线抓取+beta/anti计算
# 使用腾讯ifzq API，多前缀重试机制处理部分代码不稳定问题
# 存储结果到 beta_anti.pkl
```

### 综合评级输出格式

```
| 股票 | 代码 | 板块 | Beta | 抗跌次数 | RSI | 今日封板 | 连板概率 | 综合评级 |
|------|------|------|------|---------|-----|---------|---------|---------|
```

### 连板概率评级说明

| 评级 | 含义 |
|------|------|
| ⭐⭐⭐ 强烈推荐 | Beta 0.5~2.0 + 抗跌≥2 + 封板质量好 + 板块高潮 |
| ⭐⭐⭐ 推荐 | Beta 0.5~2.5 + 抗跌≥2 + 封板0炸板 |
| ⭐⭐ 观察 | Beta>2.5 或 抗跌≥3，但换手偏高/市值偏大 |
| ⭐ 谨慎 | 抗跌特征存在，但板块/封板质量一般 |

---

## 龙虎榜数据获取

### 方法1（推荐）：MX龙虎榜接口 + akshare汇总

**步骤1**：用akshare获取龙虎榜汇总（含上榜原因）
```python
import akshare as ak
lhb = ak.stock_lhb_detail_em(start_date='YYYYMMDD', end_date='YYYYMMDD')
# 返回列：代码、名称、上榜日、解读、收盘价、涨跌幅、龙虎榜净买额、上榜原因 等
```

**步骤2**：对重点股票，用MX接口查询席位明细（含牛散标签）
```python
import sys, time
sys.path.insert(0, 'C:/Users/June/AppData/Local/hermes/skills/dfcf/mx-data')
import mx_data
api_key = open('C:/Users/June/AppData/Local/hermes/.env').readlines()[485].strip().split('=',1)[1].strip()
client = mx_data.MXData(api_key=api_key)

r = client.query(f'{代码} 龙虎榜')
d = r['data']['data']['searchDataResultDTO']
for tbl in d.get('dataTableDTOList', []):
    table = tbl.get('table', {})
    head = table.get('headName', [])
    for idx, row in table.items():
        if idx == 'headName' or not isinstance(row, list): continue
        bull_tag = row[0] if '牛散标签' in head else '-'
        amount = row[1] if len(row) > 1 else '-'
        print(f'席位={bull_tag} 金额={amount}万')
    time.sleep(2)  # 间隔≥2秒
```

**MX接口返回字段**：
- `headName` 包含：买入金额(万元)、近三月买入次数、历史买入后上涨概率(%)
- 如果有 `牛散标签` 列：标签含"量化基金"/"量化打板"/"T王"/"拉萨"等 = 量化席位嫌疑
- 如果有 `卖出金额` 列：说明该席位于卖出方向

**量化席位判断规则**：
| 标签关键词 | 风险等级 |
|-----------|---------|
| 量化基金、量化打板、拉萨 | ⚠️ 量化席位（≥1个即需关注） |
| T王、互联网营业部 | 🟡 互联网量化（激进） |
| 温州帮、成都系、佛山系 | 🟠 短线游资 |
| 炒股养家、章盟主、中山东路 | ✅ 价值游资 |
| 无标签 | ✅ 正常席位 |

**⚠️ 已知陷阱**：
1. MX接口是搜索API，同一股票可能返回多个`entityName`段（不同上榜日的汇总），需结合日期筛选
2. 频率限制：每次查询间隔≥2秒，否则返回空
3. `stock_lhb_detail_em` 返回的上榜原因是标准格式化文本（如"日涨幅偏离值达到7%的前5只证券"），可直接使用

### 方法2（备选）：akshare stock_lhb_detail_em（仅汇总，无席位明细）

```python
import akshare as ak
lhb = ak.stock_lhb_detail_em(start_date='YYYYMMDD', end_date='YYYYMMDD')
# 返回列：代码、名称、上榜日、解读、收盘价、涨跌幅、龙虎榜净买额、上榜原因
# ⚠️ 注意：是start_date/end_date，不是date
```

### 方法3（已废弃）：东方财富datacenter API

**⚠️ 2026-05-29确认：datacenter API（RPT_BILLBOARD_DAILYDETAILSBUY等）全部返回 code=9501，已完全失效，勿用。**

### 涨停股完整列表（含上榜原因）

获取全部涨停股的上榜原因，用于判断每只涨停股的驱动逻辑：

```python
import akshare as ak
lhb = ak.stock_lhb_detail_em(start_date='YYYYMMDD', end_date='YYYYMMDD')
zt = ak.stock_zt_pool_em(date='YYYYMMDD')

zt_codes = set(zt['代码'].astype(str).tolist())
lhb_zt = lhb[lhb['代码'].astype(str).isin(zt_codes)].sort_values('龙虎榜净买额', ascending=False)

for _, r in lhb_zt.iterrows():
    net_yi = r['龙虎榜净买额'] / 1e8
    reason = r['上榜原因']
    print(f"{r['名称']}({r['代码']}) 净买{net_yi:.2f}亿 原因:{reason}")
```

**上榜原因分类**：
| 上榜原因关键词 | 含义 |
|--------------|------|
| 日涨幅偏离值达到7% | 单日涨幅异常，需出龙虎榜 |
| 连续三个交易日内，涨幅偏离值累计达到20% | 连续3日异动 |
| 日涨幅达到15% | 创业板/科创板20cm涨停 |
| 日换手率达到20% | 高换手率 |
| 日价格振幅达到15% | 日内振幅大 |
| 连续三个交易日内收盘价格涨幅偏离值累计达到30% | 3日涨30%异常 |

### 量化席位过滤

**（已更新：2026-05-29 MX龙虎榜接口验证成功，datacenter API已废弃）**

量化席位标签规则（MX接口返回的牛散标签）：
| 标签关键词 | 风险等级 |
|-----------|---------|
| 量化基金、量化打板、拉萨 | ⚠️ 量化席位（≥1个即需警惕） |
| T王、互联网营业部 | 🟡 互联网量化（激进） |
| 温州帮、成都系、佛山系 | 🟠 短线游资 |
| 炒股养家、章盟主、中山东路 | ✅ 价值游资 |
| 无标签 | ✅ 正常席位 |

拉萨席位关键词（含量化/T王/拉萨字样=量化嫌疑，直接排除）：
- 拉萨金融城南环路、拉萨东环路第一/第二、拉萨团结路第一/第二
- 拉萨娘猜曲镇路、拉萨当雄县虎空路、拉萨山南香曲东路
- 量化基金、量化打板、T王（互联网营业部）

**⚠️ 重要判断逻辑澄清（2026-05-29修订）：**

"连板股高开要卖"的决策依据**不是RSI等技术指标，而是席位属性**。

- **量化席位**（量化基金/量化打板/拉萨）：无格局资金，今日买明日必卖，连板越高砸盘越狠
- **价值游资**（炒股养家/章盟主/中山东路）：有格局，可以持有等高位
- **技术指标高位**（RSI等）：是结果不是原因，高RSI≠必然下跌

**实证**：香江控股5连板，RSI持续高位，但量化打板席位操盘才是"高开即走"的判断依据，5连板后今日清仓正确。单纯看RSI会得出错误结论（"RSI高所以要卖"——但如果板块情绪强，量化游资可以继续拉板）。

---

- RSI计算参考：`references/rsi-tencent-kline.md`（腾讯K线RSI-6计算已验证模式，含JSON解析陷阱和创业板/科创板降级处理）
- 腾讯K线volume字段解析：`references/tencent-kline-volume.md`（k[5]是浮点数字符串，非整数字符串）
- MX Search类调用方式：`references/mx-search-usage.md`（import MXSearch类而非走CLI脚本）

## 成交额/换手率数据源

akshare `stock_zt_pool_em` **不提供换手率字段**，成交额字段为元需要手动换算。

**推荐：腾讯行情 `qt.gtimg.cn`**（收盘后仍可用，Sina收盘后数据异常不可用）

```python
import urllib.request, ssl
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

codes = ['002428','000063','600330']  # 示例
syms = ','.join(('sz'+c if c.startswith(('300','002','000','001')) else 'sh'+c) for c in codes)
url = f'https://qt.gtimg.cn/q={syms}'
req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
    raw = r.read().decode('gbk', errors='ignore')
# 解析：data[1]=名称, data[3]=现价, data[31]=涨跌幅%, data[37]=成交额(万元), data[38]=换手率%
for line in raw.split('\n'):
    if '=\"' not in line: continue
    sym = line.split('=')[0].split('_')[-1]
    d = line.split('=\"')[1].strip('\";').split('~')
    if len(d) < 39: continue
    amt_yi = int(d[37]) / 10000 if d[37].isdigit() else 0
    print(f'{d[1]} 成交额{amt_yi:.1f}亿 换手率{d[38]}%')
```

> ⚠️ Sina `hq.sinajs.cn` 收盘后字段错位，数据不可用，**禁止用于收盘后复盘**

