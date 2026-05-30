# 龙虎榜数据获取 — 验证通过的脚本

## 核心陷阱（SKILL.md已记录，此处提供已验证代码）

**东方财富LHB API返回的是「每个营业部的买卖记录」，同一只股票可能有多行。必须先聚合再排序，绝不能直接去重取第一条。**

## 已验证的完整脚本（2026-05-28实测通过）

```python
import requests

url = 'https://datacenter-web.eastmoney.com/api/data/v1/get'
params = {
    'reportName': 'RPT_BILLBOARD_DAILYDETAILSBUY',
    'columns': 'ALL',
    'filter': "(TRADE_DATE='2026-05-28')",
    'pageNumber': '1',
    'pageSize': '300',        # 必须300，不要用100（会漏大单）
    'sortTypes': '-1',
    'sortColumns': 'NET',      # 按净买额降序
    'source': 'WEB',
    'client': 'WEB',
}
r = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'})
rows = r.json()['result']['data']

# ========== 正确做法：先聚合再排序 ==========
lhasa_kw = ['拉萨金融城南环路', '拉萨东环路', '拉萨团结路',
            '拉萨娘猜曲镇路', '拉萨当雄县', '拉萨山南香曲东路']

stock_map = {}
for row in rows:
    code = row['SECURITY_CODE']
    if code not in stock_map:
        stock_map[code] = {'net': 0, 'buy': 0, 'lhasa_n': 0, 'depts': []}
    stock_map[code]['net'] += float(row['NET'] or 0)
    stock_map[code]['buy'] += float(row['BUY'] or 0)
    if any(kw in row['OPERATEDEPT_NAME'] for kw in lhasa_kw):
        stock_map[code]['lhasa_n'] += 1
    stock_map[code]['depts'].append((float(row['BUY'] or 0), row['OPERATEDEPT_NAME']))

sorted_stocks = sorted(stock_map.items(), key=lambda x: x[1]['net'], reverse=True)

# 输出
for i, (code, info) in enumerate(sorted_stocks, 1):
    tag = '⚠️量化' if info['lhasa_n'] >= 2 else ('⚡拉萨'+str(info['lhasa_n']) if info['lhasa_n'] >= 1 else '✅')
    print(f'{i:2d}. {tag} {code} 净买:{info["net"]/10000:8.0f}万 拉萨:{info["lhasa_n"]}')

# ========== 错误做法（不要用）==========
# 错误1: 直接用rows[0]按NET排序后取前N
# 错误2: 用set去重SECURITY_CODE再查
# 错误3: pageSize=100（会漏掉排在大买额股票后面的标的）
```

## 名称获取（腾讯行情，push2被墙时可用）

```python
import requests

headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.qq.com'}
codes = [('600330','sh'), ('688172','sh'), ('000063','sz')]
codes_str = ','.join([f'{mkt}{code}' for code, mkt in codes])
url = f'https://qt.gtimg.cn/q={codes_str}'
req = requests.get(url, headers=headers, timeout=10)
# 输出格式: v_sh600330="1~天通股份~600330~..."
# 按~分割后: parts[1]=名称, parts[2]=代码
```

## DDX获取（MXData）

```python
import sys, time
sys.path.insert(0, 'C:/Users/June/AppData/Local/hermes/skills/dfcf/mx-data')
import mx_data
client = mx_data.MXData(api_key='YOUR_KEY')

def get_ddx(name):
    r = client.query(f'{name}DDX')
    dt = r.get('data',{}).get('data',{}).get('searchDataResultDTO',{}).get('dataTableDTOList',[])
    if not dt:
        return {}
    table = dt[0].get('table', {})
    return {
        'DDX': table.get('f88', ['-'])[0],
        'DDY': table.get('f89', ['-'])[0],
        'DDZ': table.get('f90', ['-'])[0]
    }

# ⚠️ 每次查询间隔≥3秒，否则返回空数据
for name in names:
    d = get_ddx(name)
    print(f'{name}: {d}')
    time.sleep(3.2)  # 3.0秒可能仍触发限制，用3.2+
```
