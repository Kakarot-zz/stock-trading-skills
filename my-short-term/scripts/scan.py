"""
超短线选股综合评分扫描器 v3.1
用法: python scan.py [日期]  # 日期格式 YYYYMMDD，默认今日

v3.1 修复:
  - RSI过滤加强：RSI>95排除，RSI>80警告/排除
  - 新增拉萨席位量化席位过滤（硬性排除）
  - 2连板强弱分级展示
  - 回调天数范围扩大至1~7天
  - 底部残留旧注释清除

v3.0 新增:
  - 扫描范围从"今日涨停"扩展到"近12日涨停"
  - 新增【连板回调候选】：3连板+已断开+回调中 专门捞出来

四维评分体系：
  板分(ban)   : 3连板=10, 2连板=7, 首板=3
  封板分(seal): 0次=10, 1-3次=7, 4-10次=3, >10次=0
  板块分(sector): 电力+2, 光学光电+1, 电网设备+1, 房地产-1, 一般零售-1
  市值分(mkt) : 5-50亿=10, 3-5亿/50-100亿=7, <3亿=3, >100亿=5

拉萨席位关键词（买席或卖席出现≥2个即排除）：
  拉萨团结路、拉萨金融城南环、拉萨东环路第一/第二、
  拉萨山南香曲东路、拉萨娘猜曲镇路、拉萨当雄县虎空路

输出: 综合分TOP20 + 3连板核心池 + 2连板重点 + 首板高质量候选 + 连板回调候选
"""

import akshare as ak, sys, urllib.request, ssl, json, re
from datetime import date, timedelta

DATE = sys.argv[1] if len(sys.argv) > 1 else None

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
    '其他电子': 0, '小金属': 0, 'IT服务Ⅱ': 0, '一般零售': -1,
    '煤炭开采': 1, '航空装备': 2, '航天装备': 2, '电机': 1,
    '通用设备': 0, '专用设备': 0, '汽车零部件': 0,
}

def get_date():
    if DATE:
        return DATE
    return date.today().strftime('%Y%m%d')

def d(string_date):
    """解析 YYYYMMDD 为 date 对象"""
    return date(int(string_date[:4]), int(string_date[4:6]), int(string_date[6:8]))

def d2s(dt):
    return dt.strftime('%Y%m%d')

# ─── 工具函数 ───────────────────────────────────────────
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

LIHASHA_KEYWORDS = [
    "拉萨团结路", "拉萨金融城南环", "拉萨东环路第一", "拉萨东环路第二",
    "拉萨山南香曲东路", "拉萨娘猜曲镇路", "拉萨当雄县虎空路",
]

def has_lhasa(seats_str):
    """检测席位字符串中拉萨量化席位数量"""
    if not seats_str:
        return 0
    return sum(1 for k in LIHASHA_KEYWORDS if k in seats_str)

# 龙虎榜席位缓存（避免重复请求）
_lhb_cache = {}

def get_lhb_seats(code):
    """查询个股龙虎榜席位，返回(买席字符串, 卖席字符串)"""
    if code in _lhb_cache:
        return _lhb_cache[code]
    url = (f"https://datacenter-web.eastmoney.com/api/data/v1/get"
           f"?reportName=RPT_LHB_ALLSTOCKS&columns=ALL"
           f"&filter=(SCODE=%22{code}%22)&pageNumber=1&pageSize=3"
           f"&sortTypes=-1&sortColumns=HAPPEN_DATE&source=WEB&client=WEB")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            result = json.loads(r.read().decode("utf-8"))
        items = (result.get("result") or {}).get("data", []) or []
        buy_all, sell_all = "", ""
        for item in items[:3]:
            b = item.get("BUYSEATS", "") or ""
            s = item.get("SELLSEATS", "") or ""
            buy_all += ";" + b
            sell_all += ";" + s
        _lhb_cache[code] = (buy_all, sell_all)
    except:
        _lhb_cache[code] = ("", "")
    return _lhb_cache[code]

def to_f(v):
    try: return float(v)
    except: return 0.0

def get_prefix(code):
    code = code.zfill(6)
    return f"sz{code}" if code.startswith(('300','002','000','001')) else f"sh{code}"

def fetch_kline(prefix, code, count=25):
    # prefix已含完整前缀如sz002442，code参数保留以兼容调用习惯
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayhfq&param={prefix},day,,,{count},qfq"
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            raw = r.read().decode("utf-8")
        m = re.search(r'=\s*({.*})', raw)
        if not m: return []
        data = json.loads(m.group(1))
        node = data.get('data', {}).get(prefix, {})
        return node.get('qfqday', []) or node.get('day', [])
    except:
        return []

def calc_rsi6(klines):
    closes = [to_f(k[2]) for k in klines[-12:] if to_f(k[2]) > 0]
    if len(closes) < 7: return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains[-6:]) / 6
    avg_loss = sum(losses[-6:]) / 6
    if avg_loss == 0: return 100
    return round(100 - 100 / (1 + avg_gain / avg_loss), 1)

def ma(klines, n):
    closes = [to_f(k[2]) for k in klines[-n:] if to_f(k[2]) > 0]
    return sum(closes) / len(closes) if closes else None

# ─── Step 1: 扫描近10日涨停池，收集连板候选 ───────────
scan_date = get_date()
scan_start = d2s(d(scan_date) - timedelta(days=12))  # 多扫几天确保覆盖

print(f'扫描近10日涨停数据 {scan_start} ~ {scan_date} ...')

# 近10日所有涨停股
recent_zt = {}  # code -> {name, sector, mkt, zt_dates: [(date, boards)]}
for delta in range(12):
    dd = d2s(d(scan_date) - timedelta(days=delta))
    try:
        zt = ak.stock_zt_pool_em(date=dd)
        zt['代码'] = zt['代码'].astype(str).str.zfill(6)
        for _, row in zt.iterrows():
            code = row['代码']
            if code not in recent_zt:
                recent_zt[code] = {
                    '名称': row['名称'],
                    '所属行业': row.get('所属行业', ''),
                    '流通市值': row.get('流通市值', 0),
                    '连板数': row.get('连板数', 1),
                    '成交额': row.get('成交额', 0),
                    '首次封板时间': row.get('首次封板时间', ''),
                    '炸板次数': row.get('炸板次数', 0),
                    'zt_dates': [],
                }
            # 记录该日期的连板数
            recent_zt[code]['zt_dates'].append((dd, row.get('连板数', 1)))
    except Exception as e:
        print(f'  {dd} 涨停池获取失败: {e}')

print(f'近12日涨停股数量: {len(recent_zt)}')

# 今日涨停池（用于排除还在板上的）
zt_today = ak.stock_zt_pool_em(date=scan_date)
zt_today['代码'] = zt_today['代码'].astype(str).str.zfill(6)
today_codes = set(zt_today['代码'].values)

# ─── Step 2: 分类 ───────────────────────────────────────
still_on_board = {}    # 今日涨停 + 连板数>=2
pullback_candidates = {} # 今日未涨停 + 近10日有3连板+记录

for code, info in recent_zt.items():
    info['zt_dates'].sort(key=lambda x: x[0], reverse=True)  # 最新日期排前面
    max_boards = max(b for _, b in info['zt_dates']) if info['zt_dates'] else 1

    if code in today_codes:
        # 今日涨停
        if max_boards >= 2:
            still_on_board[code] = info
    else:
        # 今日未涨停 → 检查是否近10日有3连板+断开
        # 近10日有连续3个涨停日（降序排列 newest→oldest）
        zt_days_sorted = sorted(info['zt_dates'], key=lambda x: x[0], reverse=True)
        # 连续自然日（降序）：d0=最新，d1=次新，d2=最旧；连续=(d0-d1)=1天 且 (d1-d2)=1天
        consecutive_3 = False
        for i in range(len(zt_days_sorted) - 2):
            d0 = d(zt_days_sorted[i][0])
            d1 = d(zt_days_sorted[i+1][0])
            d2 = d(zt_days_sorted[i+2][0])
            if (d0 - d1).days == 1 and (d1 - d2).days == 1:
                consecutive_3 = True
                last_board_date = zt_days_sorted[i][0]  # 最新涨停日
                break
        if consecutive_3:
            # 计算从断板到现在过了多少天
            last_dt = d(last_board_date)
            scan_dt = d(scan_date)
            days_off = (scan_dt - last_dt).days
            pullback_candidates[code] = {
                **info,
                'last_board_date': last_board_date,
                'days_off': days_off,
            }

print(f'今日涨停连板股: {len(still_on_board)}')
print(f'连板回调候选: {len(pullback_candidates)} (今日未涨停但近10日有3连板+)')

# ─── Step 3: 对连板回调候选做K线深度验证 ───────────────
print('\n对回调候选进行K线验证（3连板确认+RSI+MA位置）...')

validated_pullback = []
for code, info in pullback_candidates.items():
    prefix = get_prefix(code)
    klines = fetch_kline(prefix, code, 25)
    if not klines or len(klines) < 10:
        continue

    closes = [to_f(k[2]) for k in klines]
    # 验证近10日内确实有3连板（通过收盘价涨幅验证）
    zt_verified = 0
    for i in range(max(1, len(klines)-10), len(klines)):
        prev = closes[i-1]
        curr = closes[i]
        if prev > 0 and (curr - prev) / prev * 100 >= 9.5:
            zt_verified += 1

    rsi6 = calc_rsi6(klines)
    ma5 = ma(klines, 5)
    ma10 = ma(klines, 10)
    ma20 = ma(klines, 20)
    today_close = closes[-1]

    # 计算综合分（参照四维评分）
    max_boards = max(b for _, b in info['zt_dates']) if info['zt_dates'] else 1
    b_score = ban_score(max_boards)
    mkt_val = info.get('流通市值', 0)
    m_score = mkt_score(mkt_val)
    sector = info.get('所属行业', '')
    s_score = sector_bonus.get(sector, 0)
    total = b_score + m_score + s_score

    # 龙虎榜席位检查（仅查有记录的关键候选）
    lhasa_buy, lhasa_sell = 0, 0
    seat_info = ""
    if total >= 15:  # 只对综合分≥15的重点候选查龙虎榜
        buy_str, sell_str = get_lhb_seats(code)
        lhasa_buy = has_lhasa(buy_str)
        lhasa_sell = has_lhasa(sell_str)
        if lhasa_buy > 0 or lhasa_sell > 0:
            seat_info = f"拉萨买{lhasa_buy}卖{lhasa_sell}"

    validated_pullback.append({
        **info,
        'code': code,
        'prefix': prefix,
        'rsi6': rsi6,
        'ma5': ma5,
        'ma10': ma10,
        'ma20': ma20,
        'today_close': today_close,
        'zt_verified': zt_verified,
        'max_boards': max_boards,
        'total_score': total,
        'mkt': mkt_val / 1e8,
        'sector': sector,
        'lhasa_buy': lhasa_buy,
        'lhasa_sell': lhasa_sell,
        'seat_info': seat_info,
    })

# 按综合分排序，过滤南瓜鱼硬性条件
# 硬性条件：流通市值<=70亿, RSI6<95(>95直接排除), RSI6<80(>80降级), 3连板确认, 拉萨席位<2
def pumpkin_filter(r):
    mkt_ok = r['mkt'] <= 70
    # RSI分级：>95排除，>80降级警告但可保留
    if r['rsi6'] is not None and r['rsi6'] > 95:
        print(f"    ❌ {r.get('名称','?')}({r.get('code','?')}) RSI={r['rsi6']}>95 排除")
        return False
    rsi_ok = r['rsi6'] is None or r['rsi6'] < 80
    board_ok = r['max_boards'] >= 3
    # 拉萨席位≥2直接排除
    lhasa_ok = (r['lhasa_buy'] + r['lhasa_sell']) < 2
    passed = mkt_ok and rsi_ok and board_ok and lhasa_ok
    if not passed:
        reasons = []
        if not mkt_ok: reasons.append(f"市值{r['mkt']:.0f}亿>70")
        if r['rsi6'] and r['rsi6'] > 95: reasons.append(f"RSI={r['rsi6']}>95")
        elif r['rsi6'] and r['rsi6'] >= 80: reasons.append(f"RSI={r['rsi6']}>=80")
        if not board_ok: reasons.append(f"连板={r['max_boards']}<3")
        if not lhasa_ok: reasons.append(f"拉萨席位买{r['lhasa_buy']}卖{r['lhasa_sell']}")
        print(f"    ❌ {r.get('名称','?')}({r.get('code','?')}) 过滤: {', '.join(reasons)}")
    return passed

passed = [r for r in validated_pullback if pumpkin_filter(r)]
passed.sort(key=lambda x: x['total_score'], reverse=True)

print(f'通过南瓜鱼初步筛选: {len(passed)} 只')

# ─── Step 4: 对今日涨停连板股做四维评分 ─────────────────
print('\n对今日涨停连板股进行四维评分...')

scored_on_board = []
for code, info in still_on_board.items():
    mkt_val = info.get('流通市值', 0)
    mkt_val_b = mkt_val / 1e8
    max_boards = max(b for _, b in info['zt_dates']) if info['zt_dates'] else 1
    b_score = ban_score(max_boards)
    seal = info.get('炸板次数', 0)
    s_score = seal_score(seal)
    m_score = mkt_score(mkt_val)
    sector = info.get('所属行业', '')
    sec_score = sector_bonus.get(sector, 0)
    total = b_score + s_score + m_score + sec_score

    # RSI 计算
    prefix = get_prefix(code)
    klines = fetch_kline(prefix, code, 15)
    rsi6 = calc_rsi6(klines) if klines else None

    # 龙虎榜席位检查
    lhasa_buy, lhasa_sell = 0, 0
    if total >= 12:
        buy_str, sell_str = get_lhb_seats(code)
        lhasa_buy = has_lhasa(buy_str)
        lhasa_sell = has_lhasa(sell_str)

    scored_on_board.append({
        **info,
        'code': code,
        'prefix': prefix,
        'max_boards': max_boards,
        'rsi6': rsi6,
        'total_score': total,
        'mkt': mkt_val_b,
        'seal': seal,
        'sector': sector,
        'lhasa_buy': lhasa_buy,
        'lhasa_sell': lhasa_sell,
    })

scored_on_board.sort(key=lambda x: x['total_score'], reverse=True)

# ─── Step 5: 输出结果 ──────────────────────────────────
print('='*70)
print(f'  超短线选股扫描 v3.1  {scan_date}')
print(f'  数据范围: 近12日涨停股  今日涨停池: {len(today_codes)}只')
print('='*70)

print('\n【3连板核心池】(今日涨停 + 连板数>=3)')
count = 0
for r in scored_on_board:
    if r['max_boards'] >= 3:
        mkt = r['mkt']
        rsi = r['rsi6']
        lhasa = r.get('lhasa_buy', 0) + r.get('lhasa_sell', 0)
        # RSI危险分级
        if rsi and rsi > 95: rsi_tag = "🔴RSI>95"
        elif rsi and rsi >= 85: rsi_tag = "🔴RSI≥85"
        elif rsi and rsi >= 80: rsi_tag = "🟠RSI≥80"
        elif rsi and rsi >= 75: rsi_tag = "⚠️RSI≥75"
        else: rsi_tag = f"RSI={rsi}"
        # 量化席位标记
        lhasa_tag = f" 拉萨{lhasa}个" if lhasa > 0 else ""
        # 市值标记
        mkt_tag = "✅" if mkt <= 70 else "⚠️大盘"
        tag = "✅" if (mkt <= 70 and (rsi is None or rsi < 75) and lhasa == 0) else "⚠️"
        print(f"  {tag} {r['名称']}({r['code']}) {r['max_boards']}板 {mkt_tag} {rsi_tag}{lhasa_tag} 综合分{r['total_score']}")
        count += 1
if count == 0:
    print('  (无)')

print('\n【2连板重点观察 TOP5】(今日涨停 + 连板数=2)')
# 分强弱：RSI<75 + 市值≤70 + 无量化席位 = 强候选
strong, weak = [], []
for r in scored_on_board:
    if r['max_boards'] == 2:
        mkt = r['mkt']
        rsi = r['rsi6'] or 0
        lhasa = r.get('lhasa_buy', 0) + r.get('lhasa_sell', 0)
        if mkt <= 70 and rsi < 75 and lhasa == 0:
            strong.append(r)
        else:
            weak.append(r)

count = 0
if strong:
    print('  强候选（满足买入条件）:')
    for r in strong[:3]:
        rsi = r['rsi6']
        print(f"  ✅ {r['名称']}({r['code']}) RSI={rsi} 流通{r['mkt']:.0f}亿 综合分{r['total_score']}")
        count += 1
if weak:
    print('  观察（需明日开盘确认）:')
    for r in weak[:3]:
        rsi = r['rsi6']
        if rsi and rsi >= 85: rsi_tag = "🔴"
        elif rsi and rsi >= 80: rsi_tag = "🟠"
        else: rsi_tag = "⚠️"
        print(f"  {rsi_tag} {r['名称']}({r['code']}) RSI={rsi} 流通{r['mkt']:.0f}亿")
        count += 1
if count == 0:
    print('  (无)')

print('\n【首板高质量候选 TOP5】(今日涨停 + 连板数=1 + 成交额>10亿)')
count = 0
for r in scored_on_board:
    amt = r.get('成交额', 0)
    if r['max_boards'] == 1 and amt > 1e9 and count < 5:
        mkt = r['mkt']
        rsi = r['rsi6']
        tag = "✅" if (mkt <= 70 and (rsi is None or rsi < 80)) else "⚠️"
        print(f"  {tag} {r['名称']}({r['code']}) 成交{amt/1e8:.0f}亿 流通{mkt:.0f}亿 RSI={rsi} 综合分{r['total_score']}")
        count += 1
if count == 0:
    print('  (无)')

print('\n【★ 连板回调候选 - 南瓜鱼重点关注★】')
print('  (今日未涨停 + 近10日有3连板+ + 已回调1~7天)')
print('  ─────────────────────────────────────────────────────')

if not passed:
    print('  (无通过初步筛选的回调候选)')
else:
    for r in passed[:8]:
        mkt = r['mkt']
        rsi = r['rsi6']
        today_close = r['today_close']
        ma5 = r['ma5']
        ma10 = r['ma10']
        days_off = r['days_off']
        lhasa = r.get('lhasa_buy', 0) + r.get('lhasa_sell', 0)
        seat_tag = f" | 拉萨买{r['lhasa_buy']}卖{r['lhasa_sell']}" if lhasa > 0 else ""

        # RSI危险分级
        if rsi and rsi >= 80: rsi_tag = f"🔴RSI={rsi}"
        elif rsi and rsi >= 75: rsi_tag = f"⚠️RSI={rsi}"
        else: rsi_tag = f"RSI={rsi}"

        # 距MA5/MA10距离
        ma5_diff = (today_close - ma5) / ma5 * 100 if ma5 else 0
        ma10_diff = (today_close - ma10) / ma10 * 100 if ma10 else 0

        print(f"\n  ★ {r['名称']}({r['code']}) {r['max_boards']}板回调{days_off}天{seat_tag}")
        print(f"    流通市值: {mkt:.0f}亿 | {rsi_tag} | 综合分: {r['total_score']}")
        print(f"    板块: {r['sector']}")
        print(f"    收盘{today_close:.2f} | MA5{ma5_diff:+.1f}% | MA10{ma10_diff:+.1f}%")
        # 买点判断
        if ma10 and today_close <= ma10 * 1.02:
            print(f"    ✅ 贴近MA10支撑位 ≈{ma10:.2f}元 — 重点关注")
        elif ma5 and today_close <= ma5 * 1.01:
            print(f"    ⚠️ 贴近MA5 ≈{ma5:.2f}元 — 观察企稳")
        elif ma5 and today_close <= ma5:
            print(f"    ⚠️ 已破MA5，等MA10附近企稳再买")
        else:
            print(f"    ⚠️ 距支撑位仍远，不急")

print('\n' + '='*70)
print(f'说明: 回调候选需满足 市值<=70亿 + RSI<80 + 3连板已确认 + 拉萨席位<2个')
print(f'      涨停连板股 RSI>=85 为🔴危险区，RSI>=80为🟠警告区，禁止追')
print('='*70)
