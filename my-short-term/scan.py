import akshare as ak

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
    '其他电子': 0, '小金属': 0, 'IT服务Ⅱ': 0, '一般零售': -1
}

zt['板分'] = zt['连板数'].apply(ban_score)
zt['封板分'] = zt['炸板次数'].apply(seal_score)
zt['板块分'] = zt['所属行业'].map(lambda x: sector_bonus.get(x, 0))
zt['市值分'] = zt['流通市值'].apply(mkt_score)
zt['综合分'] = zt['板分'] + zt['封板分'] + zt['板块分'] + zt['市值分']

cols = ['代码','名称','连板数','涨跌幅','首次封板时间','炸板次数','流通市值','成交额','综合分','板分','封板分','板块分','市值分']

print('=== 超短线候选池 TOP20（综合评分）===')
top = zt.nlargest(20, '综合分')[cols]
for _, row in top.iterrows():
    mkt = row['流通市值']/1e8
    amt = row['成交额']/1e8
    print(f"{row['名称']}({row['代码']}) {row['连板数']}板 封{int(row['首次封板时间'])} 炸{row['炸板次数']}次 "
          f"流通{mkt:.0f}亿/成交{amt:.0f}亿 综合分{row['综合分']:.0f} "
          f"[板{row['板分']} 封{row['封板分']} 板{row['板块分']} 市{row['市值分']}]")

print()
print('=== 3连板核心池（最高优先级）===')
core = zt[zt['连板数'] >= 3].sort_values('综合分', ascending=False)
for _, row in core.iterrows():
    mkt = row['流通市值']/1e8
    print(f"  {row['名称']}({row['代码']}) {row['连板数']}板 封{int(row['首次封板时间'])} 炸{row['炸板次数']}次 "
          f"流通{mkt:.0f}亿 综合分{row['综合分']:.0f}")

print()
print('=== 2连板重点观察 ===')
two = zt[zt['连板数'] == 2].nlargest(5, '综合分')
for _, row in two.iterrows():
    mkt = row['流通市值']/1e8
    print(f"  {row['名称']}({row['代码']}) {row['连板数']}板 封{int(row['首次封板时间'])} 炸{row['炸板次数']}次 "
          f"流通{mkt:.0f}亿 综合分{row['综合分']:.0f}")

print()
print('=== 首板高质量候选（成交额>10亿+炸板<=3次）===')
first = zt[(zt['连板数']==1) & (zt['成交额']>1e9) & (zt['炸板次数']<=3)].nlargest(8, '综合分')
for _, row in first.iterrows():
    mkt = row['流通市值']/1e8
    amt = row['成交额']/1e8
    print(f"  {row['名称']}({row['代码']}) 封{int(row['首次封板时间'])} 炸{row['炸板次数']}次 "
          f"成交{amt:.0f}亿 流通{mkt:.0f}亿 综合分{row['综合分']:.0f}")
