import akshare as ak, urllib.request, json, re

zt = ak.stock_zt_pool_em(date='20260527')
zt['代码'] = zt['代码'].astype(str).str.zfill(6)

def ban_score(x):
    if x >= 3: return 10
    elif x == 2: return 7
    else: return 3

def seal_score(x):
    if x == 0: return 10
    elif x <= 3: return 7
    elif x <= 10: return 3
    else: return 0

def mkt_score(x):
    y = x / 1e8
    if 5 <= y <= 50: return 10
    elif (3 <= y < 5) or (50 < y <= 100): return 7
    elif y < 3: return 3
    else: return 5

sector_bonus = {
    '电力': 2, '光学光电': 1, '电网设备': 1,
    '元件': 0, '房地产': -1, '化学制药': 0,
    '化学原料': 0, '光伏设备': 0, '通信设备': 0,
    '其他电子': 0, '小金属': 0, 'IT服务II': 0, '一般零售': -1
}

zt['板分'] = zt['连板数'].apply(ban_score)
zt['封板分'] = zt['炸板次数'].apply(seal_score)
zt['板块分'] = zt['所属行业'].map(lambda x: sector_bonus.get(x, 0))
zt['市值分'] = zt['流通市值'].apply(mkt_score)
zt['综合分'] = zt['板分'] + zt['封板分'] + zt['板块分'] + zt['市值分']

LASA_KW = ['拉萨团结路','拉萨金融城','拉萨东环路','拉萨山南','拉萨娘猜','拉萨当雄','拉萨虎空路','东方财富拉萨']

# 龙虎榜HTML
lhb_url = 'https://data.eastmoney.com/stock/lhb.html'
req = urllib.request.Request(lhb_url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://data.eastmoney.com/'})
lhb_data = []
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        html = r.read().decode('utf-8', errors='ignore')
    m = re.search(r'"pagedata":\s*(\[.*?\])\s*,', html, re.DOTALL)
    if m:
        lhb_data = json.loads(m.group(1))
        print(f'龙虎榜HTML: {len(lhb_data)}只\n')
except Exception as e:
    print(f'龙虎榜HTML: {e}\n')

lhb_seats = {}
for item in lhb_data:
    code = item.get('SCode', '')
    seats = item.get('SeatNames', '') or ''
    seat_list = seats.split(',') if seats else []
    lasa_count = sum(1 for s in seat_list if any(kw in s for kw in LASA_KW))
    lhb_seats[code] = {'seats': seats, 'lasa_count': lasa_count}

print('='*60)
print('  超短线选股结果  5月27日')
print('='*60)

print('\n【3连板核心池】')
print('-'*60)
core3 = zt[zt['连板数'] >= 3].sort_values('综合分', ascending=False)
for _, row in core3.iterrows():
    code = row['代码']
    mkt = row['流通市值']/1e8
    lasa = lhb_seats.get(code, {}).get('lasa_count', -1)
    flag = '❌量化' if lasa >= 2 else ('⚠️1个' if lasa == 1 else '✅干净' if lasa >= 0 else '')
    print(f"  {row['名称']}({code}) | {row['连板数']}板 | 封{int(row['首次封板时间'])} | "
          f"炸{row['炸板次数']}次 | 流通{mkt:.0f}亿 | 综合分{row['综合分']:.0f} {flag}")

print('\n【2连板重点观察】')
print('-'*60)
two = zt[zt['连板数'] == 2].nlargest(5, '综合分')
for _, row in two.iterrows():
    code = row['代码']
    mkt = row['流通市值']/1e8
    lasa = lhb_seats.get(code, {}).get('lasa_count', -1)
    flag = '❌量化' if lasa >= 2 else ('⚠️1个' if lasa == 1 else '✅干净' if lasa >= 0 else '')
    print(f"  {row['名称']}({code}) | {row['连板数']}板 | 封{int(row['首次封板时间'])} | "
          f"炸{row['炸板次数']}次 | 流通{mkt:.0f}亿 | 综合分{row['综合分']:.0f} {flag}")

print('\n【首板高质量候选】（成交额>10亿+炸<=3次）')
print('-'*60)
first = zt[(zt['连板数']==1) & (zt['成交额']>1e9) & (zt['炸板次数']<=3)].nlargest(8, '综合分')
for _, row in first.iterrows():
    code = row['代码']
    mkt = row['流通市值']/1e8
    amt = row['成交额']/1e8
    lasa = lhb_seats.get(code, {}).get('lasa_count', -1)
    flag = '❌量化' if lasa >= 2 else ('⚠️1个' if lasa == 1 else '✅干净' if lasa >= 0 else '')
    print(f"  {row['名称']}({code}) | 封{int(row['首次封板时间'])} | 炸{row['炸板次数']}次 | "
          f"成交{amt:.0f}亿 | 流通{mkt:.0f}亿 | 综合分{row['综合分']:.0f} {flag}")
