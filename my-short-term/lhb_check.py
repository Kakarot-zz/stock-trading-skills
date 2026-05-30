import urllib.request, json

# Try the LHB list API first
lhb_url = 'https://datacenter-web.eastmoney.com/api/data/v1/get?sortColumns=CHANGE_RATE&sortTypes=-1&pageSize=200&pageNumber=1&reportName=RPT_DRAGON_LIST&columns=ALL&filter=(TRADE_DATE%3D%272026-05-27%27)&source=WEB&client=WEB'
req = urllib.request.Request(lhb_url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    result = data.get('result')
    if result:
        print(f'RPT_DRAGON_LIST: {len(result.get("data",[]))} items')
        for item in result.get('data', [])[:2]:
            print(json.dumps(item, ensure_ascii=False)[:300])
    else:
        print(f'RPT_DRAGON_LIST result: {str(data)[:200]}')
except Exception as e:
    print(f'RPT_DRAGON_LIST error: {e}')

print()

# Also try without filters
simple_url = 'https://datacenter-web.eastmoney.com/api/data/v1/get?sortColumns=CHANGE_RATE&sortTypes=-1&pageSize=5&pageNumber=1&reportName=RPT_DAILYBILLBOARD&source=WEB&client=WEB'
req2 = urllib.request.Request(simple_url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req2, timeout=10) as r:
        data2 = json.loads(r.read())
    result2 = data2.get('result')
    if result2:
        items = result2.get('data', [])
        print(f'RPT_DAILYBILLBOARD (no filter): {len(items)} items')
        for item in items[:2]:
            print(json.dumps(item, ensure_ascii=False)[:300])
    else:
        print(f'RPT_DAILYBILLBOARD (no filter): {str(data2)[:200]}')
except Exception as e:
    print(f'RPT_DAILYBILLBOARD error: {e}')
