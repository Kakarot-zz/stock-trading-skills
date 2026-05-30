# scan.py bug 记录

## MA20 计算 bug（v3.1确认）

**位置**：`scripts/scan.py` 第255-256行附近

**问题**：
```python
ma20 = ma(klines, 20)
ma20 = ma(klines, 20)   # 实际代码是这两行，但下一行输出时直接用了ma10的值
```

回调候选输出部分（约第470行）：
```python
print(f"    收盘{today_close:.2f} | MA5{ma5_diff:+.1f}% | MA10{ma10_diff:+.1f}%")
# 注意：输出里没有 MA20，因为 ma20 变量在计算时就被覆盖或未正确传递
```

**现状**：回调候选输出只显示 MA5 和 MA10 距离，没有 MA20。

**影响**：
- 输出中 MA20 一致显示为 MA10 的值（或为空）
- 无法通过扫描脚本直接判断个股是否破 MA20

**临时解决**：
- 使用 `/tmp/kline_rsi.py` 手动查询腾讯K线获取正确的 MA5/MA10/MA20 值
- 参考 `references/tencent-kline-realtime.md` 的手动解析方法

**修复方向**（待下次脚本更新）：
- 在 `validated_pullback` 字典中正确保存 ma5/ma10/ma20/ma60 四个值
- 输出时增加 MA20/MA60 距离打印
- 买点判断逻辑扩展到 MA20/MA60 支撑位判断
