# 东方财富快讯API（实时资讯）

## 概述

东方财富快讯API（`newsapi.eastmoney.com/kuaixun`）是获取实时市场资讯的可靠数据源，返回最新市场新闻、财经快讯。相比MX API的资讯搜索端点（常返回114），快讯API稳定可用，适合快速了解当日市场热点和主题炒作线索。

## 端点

```
https://newsapi.eastmoney.com/kuaixun/v1/getlist_101_ajaxResult_50_1_.html
```

**参数说明**：
- `50` = 每页条数（可调）
- `1` = 页码

**返回格式**：JSONP，包装在 `var ajaxResult={...}` 中。

## 解析方法

```python
import requests, json, re

url = 'https://newsapi.eastmoney.com/kuaixun/v1/getlist_101_ajaxResult_50_1_.html'
headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.eastmoney.com'}
r = requests.get(url, headers=headers, timeout=10)
text = r.text
if text.startswith('var ajaxResult='):
    text = text[len('var ajaxResult='):]
data = json.loads(text)
lives = data.get('LivesList', [])
print(f'Total items: {len(lives)}')
for item in lives:
    print(item.get('title', ''))
    print(item.get('digest', '')[:200])
    print(item.get('url_w', ''))   # PC版链接
    print()
```

## 关键字段

| 字段 | 含义 |
|------|------|
| `title` | 新闻标题 |
| `digest` | 新闻摘要/导语 |
| `url_w` | PC版链接（东方财富网） |
| `url_m` | 移动版链接 |
| `newsid` | 新闻ID |
| `sort` | 时间戳（降序排列，最新在前） |

## 实用查询模式

### 1. 查找特定主题快讯

```python
for item in lives:
    title = item.get('title', '')
    if '无人机' in title or '特朗普' in title:
        print(f'Title: {title}')
        print(f'URL: {item.get("url_w", "")}')
        print(f'Digest: {item.get("digest", "")[:200]}')
        print()
```

### 2. 获取新闻正文

```python
import requests, re

# 从快讯item获取url_w
url = item['url_w']
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r = requests.get(url, headers=headers, timeout=10)
# 提取正文段落
texts = re.findall(r'<p[^>]*>(.*?)</p>', r.text, re.S)
for t in texts:
    t = re.sub(r'<[^>]+>', '', t).strip()
    if len(t) > 30:
        print(t[:300])
        print('---')
```

### 3. 搜索多个主题（多页）

```python
import requests, json

all_lives = []
for page in range(1, 4):  # 前3页
    url = f'https://newsapi.eastmoney.com/kuaixun/v1/getlist_101_ajaxResult_50_{page}_.html'
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.eastmoney.com'}, timeout=10)
    text = r.text
    if text.startswith('var ajaxResult='):
        text = text[len('var ajaxResult='):]
    data = json.loads(text)
    all_lives.extend(data.get('LivesList', []))
```

## 已知限制

1. **需要 Referer header**：不带 `Referer: https://www.eastmoney.com` 可能返回非200状态
2. **返回中文乱码**：若页面编码问题，使用 `r.text`（requests自动处理UTF-8）
3. **快讯排序**：按时间倒序，每页50条，第一页即当日最新
4. **新闻正文提取**：东方财富文章页结构复杂，建议用正则提取 `<p>` 标签再strip HTML
5. **不可用于资讯搜索**：该API只返回快讯列表，不支持关键词搜索；搜索需用MX API的 `news-search` 端点（但已知不稳定，返回114）

## 应用场景

- **盘前/盘中热点挖掘**：快速了解当日市场主线
- **主题投资研究**：如"特朗普投资无人机"事件→先快讯确认新闻→再查相关板块
- **涨停板归因**：复盘时确认某股涨停是否与突发新闻相关
- **板块轮动验证**：跟踪某主题快讯出现频率判断情绪热度
