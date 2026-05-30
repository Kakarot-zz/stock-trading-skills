import os, sys, json, urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open('C:/Users/June/AppData/Local/hermes/.env', 'r') as f:
    for line in f:
        if 'MX_APIKEY' in line and not line.startswith('#'):
            APIKEY = line.strip().split('=', 1)[1].strip()
            break

BASE_URL = 'https://mkapi2.dfcfs.com/finskillshub/api/claw/news-search'

names = {'002995':'天地在线','603324':'盛剑科技','001259':'利仁科技','000509':'华塑控股','300069':'金利华电'}

LIHASHA_KEYWORDS = [
    "拉萨团结路", "拉萨金融城南环", "拉萨东环路第一", "拉萨东环路第二",
    "拉萨山南香曲东路", "拉萨娘猜曲镇路", "拉萨当雄县虎空路",
]

def count_lhasa(text):
    if not text:
        return 0
    return sum(1 for k in LIHASHA_KEYWORDS if k in text)

for code in ['002995','603324','001259','000509','300069']:
    name = names.get(code, code)
    print(f'=== {name}({code}) ===')
    payload = json.dumps({'query': name + ' 2026-05-29 龙虎榜 席位 买卖明细', 'size': 3}).encode()
    req = urllib.request.Request(BASE_URL,
        data=payload,
        headers={'Content-Type': 'application/json', 'apikey': APIKEY},
        method='POST')
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            result = json.loads(r.read().decode())
        items = result.get('data', {}).get('data', {}).get('llmSearchResponse', {}).get('data', [])
        for item in items[:3]:
            content = item.get('content', '').replace('\\n', '\n')
            date = item.get('date', '')
            print(f'  [{date}] {item.get("title", "")}')
            lhasa_count = count_lhasa(content)
            if lhasa_count > 0:
                print(f' 拉萨席位命中: {lhasa_count}处')
            print(f'  内容: {content[:500]}')
            print()
    except Exception as e:
        print(f'  Error: {e}')
        print()
