import os, sys, json
sys.path.insert(0, '/c/Users/June/AppData/Local/hermes/skills/dfcf/mx-data')
with open('C:/Users/June/AppData/Local/hermes/.env', 'r') as f:
    for line in f:
        if 'MX_APIKEY' in line and not line.startswith('#'):
            parts = line.strip().split('=', 1)
            APIKEY = parts[1].strip()
            break
os.environ['MX_APIKEY'] = APIKEY
import mx_data

# 查询四川长虹主力资金流向
for q in ['四川长虹 主力资金流向', '四川长虹 资金流向', '四川长虹 DDX']:
    result = mx_data.MXData().query(q)
    dtl = result['data']['data']['searchDataResultDTO']['dataTableDTOList']
    print(f'Query: {q} => {len(dtl)} tables, first title: {dtl[0]["title"] if dtl else "empty"}')
    if dtl:
        raw = dtl[0].get('rawTable', {})
        print(f'  rawTable keys: {list(raw.keys())[:20]}')
        for k, v in raw.items():
            if isinstance(v, list) and len(v) > 0:
                print(f'  {k}: {v[0]}')
            else:
                print(f'  {k}: {v}')
    print()