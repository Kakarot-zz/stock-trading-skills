import os, sys, json
sys.path.insert(0, '/c/Users/June/AppData/Local/hermes/skills/dfcf/mx-data')
with open('C:/Users/June/AppData/Local/hermes/.env', 'r') as f:
    for line in f:
        if 'MX_APIKEY' in line and not line.startswith('#'):
            APIKEY=line.s...'=', 1)[1].strip()
            break
os.environ['MX_APIKEY'] = APIKEY
import mx_data

codes = ['002995','603324','000518','002442','603779','001259','000509','300069']
names = {'002995':'天地在线','603324':'盛剑科技','000518':'四环生物','002442':'龙星科技','603779':'威龙股份','001259':'利仁科技','000509':'华塑控股','300069':'金利华电'}
for code in codes:
    try:
        result = mx_data.MXData().query(code + ' 主力资金流向')
        dtl = result['data']['data']['searchDataResultDTO']['dataTableDTOList']
        if dtl:
            raw = dtl[0].get('rawTable', {})
            f62 = float(raw.get('f62', ['0'])[0])
            f88 = raw.get('f88', ['0'])[0]
            f91 = raw.get('f91', ['0'])[0]
            f94 = raw.get('f94', ['0'])[0]
            print(f"{names.get(code,code)}({code}) 主力净额={f62/1e4:.0f}万 DDX当日={f88} DDX5日={f91} DDX10日={f94}")
        else:
            print(f"{names.get(code,code)}({code}) 无数据")
    except Exception as e:
        print(f"{names.get(code,code)}({code}) Error: {e}")
