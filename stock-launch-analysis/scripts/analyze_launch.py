#!/usr/bin/env python3
"""
股票启动形态分析脚本（2026-05-25 修正版）

形态：连续拉升 → 断板 → 大跌 → 昨日大低开承接 → 今日低开反弹

前置条件：
  pip install requests（可选，urllib内置已够用）

用法：
  1. 修改 TODAY 为当前日期
  2. python3 scripts/analyze_launch.py
"""
import urllib.request, ssl, json, time, os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ⚠️ 手动设置今日日期（周一~周五交易日）
TODAY = "2026-05-27"


# ─── 工具函数 ────────────────────────────────────────────────────────────────

def get_mx_api_key():
    """从 ~/.hermes/.env 读取 mx-data API key"""
    return next(
        l.split('"')[1] if '"' in l else l.split("'")[1]
        for l in open(os.path.expanduser("~/.hermes/.env"))
        if 'MX_APIKEY' in l
    )


def mx_stock_screen(keyword, page_size=200, page_no=1):
    """
    mx-data 条件选股接口（claw/stock-screen）
    返回 (data_list, total_count)
    """
    api_key = get_mx_api_key()
    url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/stock-screen"
    payload = {
        "keyword": keyword,
        "pageSize": page_size,
        "pageNo": page_no
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "apikey": api_key},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        result = json.loads(r.read().decode())

    all_results = result.get("data", {}).get("data", {}).get("allResults", {})
    data_list = all_results.get("result", {}).get("dataList", [])
    total = all_results.get("result", {}).get("totalRecordCount", 0)
    return data_list, total


def get_tencent_kline_asc(code, count=30):
    """
    获取腾讯K线，返回时间正序（旧→新）。
    ⚠️ 不带 end_date 参数 → 默认升序（最旧日期在前），不要反转数组！

    返回: [[日期, 开, 收, 高, 低, 量, 涨跌幅], ...]
    """
    prefix = "sh" if code.startswith(("6", "9")) else "sz"
    url = (
        f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        f"?_var=kline_dayhfq&param={prefix}{code},day,,,{count},qfq"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
        text = r.read().decode("utf-8").replace("kline_dayhfq=", "", 1)
    data = json.loads(text)
    klines_raw = data.get("data", {}).get(f"{prefix}{code}", {}).get("qfqday", [])
    if not klines_raw:
        return []

    # 已经是升序，直接使用，不要反转！
    klines_asc = [row[:6] for row in klines_raw]
    closes = [float(d[2]) for d in klines_asc]
    for i, d in enumerate(klines_asc):
        d.append(0.0)
        if i > 0:
            d[-1] = (closes[i] - closes[i-1]) / closes[i-1] * 100
    return klines_asc
    # klines_asc[0] = 最早, klines_asc[-1] = 昨天
    # n = len(klines_asc)
    # 昨天 = klines_asc[n-1], 大跌日 = klines_asc[n-2], 断板日 = klines_asc[n-3]


def analyze_pattern(klines):
    """
    五步形态分析（5分制）。

    K线索引（假设 today=2026-05-25, yesterday=2026-05-22, crash=2026-05-21）：
      klines[-1]  = 今天  (05-25)
      klines[-2]  = 昨天  (05-22)
      klines[-3]  = 大跌日 (05-21)
      klines[-4]  = 断板日 (05-20)

    返回: (score, detail_dict)
    """
    if len(klines) < 10:
        return 0, {"reason": "K线不足10条"}

    n = len(klines)

    def pct(i):
        if i is None or not (0 <= i < n): return None
        return klines[i][-1]

    def cls(i):
        if i is None or not (0 <= i < n): return None
        return float(klines[i][2])

    def opn(i):
        if i is None or not (0 <= i < n): return None
        return float(klines[i][1])

    def dt(i):
        if i is None or not (0 <= i < n): return None
        return klines[i][0]

    # ── ① 连续大涨：近10日找连续上涨段（≥3天） ──────────────────────────
    up_segs = []
    seg_start = None
    for i in range(max(1, n - 10), n):
        p = pct(i)
        if p is not None and p > 0:
            if seg_start is None:
                seg_start = i
        else:
            if seg_start is not None:
                if i - seg_start >= 3:
                    up_segs.append((seg_start, i - 1))
                seg_start = None
    if seg_start is not None and n - seg_start >= 3:
        up_segs.append((seg_start, n - 1))
    has_rise = len(up_segs) > 0

    # ── ② 断板日：连续拉升之后的第一个 0~8% 涨幅日 ───────────────────────
    break_day = None
    if up_segs:
        last_end = up_segs[-1][1]
        for i in range(last_end + 1, min(last_end + 4, n)):
            p = pct(i)
            if p is not None and 0 <= p <= 8:
                break_day = i
                break

    # ── ③ 大跌日：断板后的第一个跌幅 ≥5% ────────────────────────────────
    crash_day = None
    if break_day is not None:
        for i in range(break_day + 1, min(break_day + 4, n)):
            p = pct(i)
            if p is not None and p <= -5:
                crash_day = i
                break

    # ── ④ 昨天大低开承接（昨天 = klines[-2]）────────────────────────────
    # 条件：crash_day 次日 = n-2（昨天），且 开盘相比 crash日收盘 低开≥3%，收盘>开盘
    yesterday_support = False
    yesterday_gap = None
    if crash_day is not None and crash_day + 1 == n - 2:
        gap = (opn(n - 2) - cls(crash_day)) / cls(crash_day) * 100
        yesterday_gap = gap
        if (gap is not None and gap <= -3 and
            cls(n - 2) is not None and opn(n - 2) is not None and
            cls(n - 2) > opn(n - 2)):
            yesterday_support = True

    # ── ⑤ 今天反弹（今天 = klines[-1]）─────────────────────────────────
    # 条件：crash_day 次次日 = n-1（今天），低开≥1% 且 收盘>开盘
    today_rebound = False
    today_gap = None
    if crash_day is not None and crash_day + 2 == n - 1:
        gap_t = (opn(n - 1) - cls(n - 2)) / cls(n - 2) * 100
        today_gap = gap_t
        if (gap_t is not None and gap_t <= -1 and
            cls(n - 1) is not None and opn(n - 1) is not None and
            cls(n - 1) > opn(n - 1)):
            today_rebound = True

    score = (
        (1 if has_rise else 0) +
        (1 if break_day is not None else 0) +
        (1 if crash_day is not None else 0) +
        (1 if yesterday_support else 0) +
        (1 if today_rebound else 0)
    )

    detail = {
        "score": score,
        "has_rise": has_rise,
        "rise_days": [(dt(s), dt(e), e - s + 1) for s, e in up_segs],
        "break_day": dt(break_day),
        "break_pct": pct(break_day),
        "crash_day": dt(crash_day),
        "crash_pct": pct(crash_day),
        "yesterday_support": yesterday_support,
        "yesterday_gap": yesterday_gap,
        "yesterday_dt": dt(n - 2),
        "today_rebound": today_rebound,
        "today_gap": today_gap,
        "today_dt": dt(n - 1),
    }
    return score, detail


def safe_pct(v):
    """安全格式化百分比"""
    return f"{v:+.2f}%" if v is not None else "N/A"


# ─── Step 1: 全市场扫描 ──────────────────────────────────────────────────────

print(f"{'='*65}")
print(f"股票启动形态扫描  TODAY={TODAY}")
print(f"{'='*65}\n")

print("Step 1: 通过 mx-data 扫描主板候选股票...")
data_list, total = mx_stock_screen(
    "涨幅负10%至10% 流通市值20亿至100亿 市盈率大于0 主板 不含ST 不含创业板 不含科创板 不含北交所",
    page_size=300
)

seen = set()
candidates = []
for item in data_list:
    code = item.get("SECURITY_CODE", "")
    if code in seen or not code:
        continue
    seen.add(code)
    name = item.get("SECURITY_SHORT_NAME", "")
    chg_pct = float(item.get("CHG", 0) or 0)
    if chg_pct < -10 or chg_pct > 10:
        continue
    candidates.append({
        "code": code,
        "name": name,
        "chg_pct": chg_pct,
        "price": float(item.get("NEWEST_PRICE", 0) or 0),
        "mkt_cap": item.get("010000_CIRCULATION_MARKET_VALUE<70>{2026-05-22}", ""),
        "pe": item.get("010000_PETTM<70>{2026-05-22}", ""),
    })

print(f"  主板候选股票: {len(candidates)} 只（总计 {total} 条）\n")


# ─── Step 2: K线形态验证 ─────────────────────────────────────────────────────

print(f"Step 2: 开始K线形态验证...\n")

results = []
all_analyzed = []

for i, cand in enumerate(candidates):
    code = cand["code"]
    time.sleep(0.3 + (i % 5) * 0.1)   # 控制请求频率
    klines = get_tencent_kline_asc(code, 30)
    if len(klines) < 10:
        continue
    score, detail = analyze_pattern(klines)
    cand["score"] = score
    cand["detail"] = detail
    cand["klines"] = klines
    all_analyzed.append((score, cand))
    if score >= 3:
        results.append(cand)

    if (i + 1) % 50 == 0:
        print(f"  已扫描 {i+1}/{len(candidates)} 只... 当前≥3分: {len(results)} 只")

print(f"\n扫描完成。≥3分候选: {len(results)} 只")


# ─── Step 3: 输出结果 ─────────────────────────────────────────────────────────

results.sort(key=lambda x: -x["score"])

for r in results:
    d = r["detail"]
    print(f"\n{'='*65}")
    print(f"{r['code']} {r['name']} 今日涨幅:{r['chg_pct']:+.2f}% 得分:{d['score']}/5")
    print(f"  市值:{r['mkt_cap']}亿 PE:{r['pe']}")
    print(f"  拉升段: {d['rise_days']}")
    print(f"  断板: {d['break_day']}({safe_pct(d['break_pct'])}) "
          f"大跌: {d['crash_day']}({safe_pct(d['crash_pct'])})")
    print(f"  昨天({d['yesterday_dt']})大低开gap:{safe_pct(d['yesterday_gap'])} "
          f"承接:{d['yesterday_support']}")
    print(f"  今天({d['today_dt']})反弹gap:{safe_pct(d['today_gap'])} "
          f"rebound:{d['today_rebound']}")
    print(f"  近10日K线:")
    for k in r["klines"][-10:]:
        print(f"    {k[0]} 开:{float(k[1]):.2f} 收:{float(k[2]):.2f} "
              f"涨:{k[-1]:+.2f}%")


# ─── 附加：得分2分但接近3分的候选 ───────────────────────────────────────────

if not results:
    print(f"\n{'='*65}")
    print("得分2/5的候选（接近3分，值得关注）：")
    two_point = sorted([(s, c) for s, c in all_analyzed if s == 2],
                       key=lambda x: -x[0])[:10]
    for score, r in two_point:
        d = r["detail"]
        print(f"\n  {r['code']} {r['name']} 今日:{r['chg_pct']:+.2f}% 得分:{score}/5")
        print(f"    拉升:{d['rise_days']} "
              f"断板:{d['break_day']}({safe_pct(d['break_pct'])}) "
              f"大跌:{d['crash_day']}({safe_pct(d['crash_pct'])})")
        print(f"    昨天大低开gap:{safe_pct(d['yesterday_gap'])} "
              f"承接:{d['yesterday_support']} 今天反弹:{d['today_rebound']}")
        print(f"    近5日K线:")
        for k in r["klines"][-5:]:
            print(f"      {k[0]} 开:{float(k[1]):.2f} 收:{float(k[2]):.2f} "
                  f"涨:{k[-1]:+.2f}%")
