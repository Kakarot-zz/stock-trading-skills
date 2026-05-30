# 龙虎榜API状态 — 2026-05-28

## 接口状态

**URL**: `https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_DAILYBILLBOARD`

**结果**: 401 Unauthorized

**原因**: 需要认证凭据，当前环境无法提供

**影响**: 量化席位（拉萨系）过滤无法执行

## 临时替代方案

无可靠替代。龙虎榜席位查询依赖东财认证接口，暂无其他可用数据源。

## 待解决

- 寻找可用的免费龙虎榜数据源（不需认证）
- 或解决东财API认证问题
