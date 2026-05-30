import os, sys, json
with open('C:/Users/June/AppData/Local/hermes/.env', 'r') as f:
    for line in f:
        if 'MX_APIKEY' in line and not line.startswith('#'):
            APIKEY=line.strip().split('=', 1)[1].strip()
            break
os.environ['MX_APIKEY'] = APIKEY
import mx_data

LIHASHA_KEYWORDS = [
    "拉萨团结路", "拉萨金融城南环", "拉萨东环路第一", "拉萨东环路第二",
    "拉萨山南香曲东路", "拉萨娘猜曲镇路", "拉萨当雄县虎空路",
]

def count_lhasa(seats_str):
    if not seats_str:
        return 0
    return sum(1 for k in LIHASHA_KEYWORDS if k in seats_str)

codes = ['002995','603324','001259','000509','300069']
names = {'002995':'天地在线','603324':'盛剑科技','001259':'利仁科技','000509':'华塑控股','300069':'金利华电'}

for code in codes:
    name = names.get(code, code)
    print(f'=== {name}({code}) ===')
    try:
        result = mx_data.MXData().query(name + ' 今日龙虎榜席位')
        dtl = result['data']['data']['searchDataResultDTO']['dataTableDTOList']
        print(f'  tables: {len(dtl)}')
        for i, t in enumerate(dtl[:3]):
            raw = t.get('rawTable', {})
            for k, v in raw.items():
                if isinstance(v, list) and len(v) > 0:
                    print(f'  [{k}]: {str(v)[:200]}')
                elif v and str(v).strip():
                    print(f'  [{k}]: {str(v)[:200]}')
        print()
    except Exception as e:
        print(f'  Error: {e}')
        print()
