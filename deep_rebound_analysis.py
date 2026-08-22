#!/usr/bin/env python3
"""国际复材 301526 — 超跌反弹深度分析：斐波那契 + 筹码 + 量价"""
import json, sys, os

with open("301526_data.json", "r") as f:
    data = json.load(f)

recent = data["kline"]["recent_100"]

# ── 找关键价位 ──
high_all = max(r["h"] for r in recent)
high_idx = max(range(len(recent)), key=lambda i: recent[i]["h"])
high_date = recent[high_idx]["d"]

# 从最高点之后找最低点
post_high = recent[high_idx:]  # 高点之后的数据
low_after = min(r["l"] for r in post_high)
low_idx = min(range(len(post_high)), key=lambda i: post_high[i]["l"])
low_date = post_high[low_idx]["d"]

# 在最高点之前找启动点（阶段性低点）
pre_high = recent[:high_idx+1]
# 找启动前最后一个明显低点
start_low = min(r["l"] for r in pre_high[-20:])  # 高点前20天的低点

close = recent[-1]["c"]

print("=" * 65)
print("  国际复材 301526 — 超跌反弹深度技术分析")
print("=" * 65)

print(f"""
【关键价位】
  本轮最高点: {high_all} 元 ({high_date})
  高点后最低: {low_after} 元 ({low_date})
  最新收盘:   {close} 元
  高点→低点跌幅: {(low_after/high_all - 1)*100:.1f}%
  低点→最新反弹: {(close/low_after - 1)*100:.1f}%
  距高点仍回撤: {(close/high_all - 1)*100:.1f}%
""")

# ═══════════════════════════════════════════════════════
# 斐波那契回撤分析
# ═══════════════════════════════════════════════════════
print("─" * 65)
print("  📐 一、斐波那契反弹位分析")
print("─" * 65)

low = low_after  # 25.44 (最低点)
high = high_all  # 54.08 (最高点)
diff = high - low

fib_levels = [
    (0.236, "23.6% 弱反弹"),
    (0.382, "38.2% 黄金反弹位"),
    (0.500, "50.0% 半分位"),
    (0.618, "61.8% 黄金分割位"),
    (0.786, "78.6% 强阻力位"),
]

print(f"  从 {low} → {high} 的斐波那契反弹位:")
print(f"  {'─'*50}")
print(f"  {'反弹位':16s} {'价格':>8s}  {'距现价':>8s}  {'状态'}")
print(f"  {'─'*50}")

for ratio, name in fib_levels:
    price = low + diff * ratio
    pct_from_now = (price / close - 1) * 100
    status = "✅ 已突破" if close > price else "⬆️ 待攻克" if pct_from_now > 0 else "—"
    print(f"  {name:16s} {price:>8.2f}  {pct_from_now:>+7.1f}%  {status}")

# 关键：当前处于哪个位置
current_ratio = (close - low) / diff
print(f"""
  当前位置: 反弹了 {current_ratio*100:.1f}% (约 0.{int(current_ratio*100)} 分位)
  刚突破: 23.6% 分位 ({low + diff*0.236:.2f})
  下一目标: 38.2% 分位 ({low + diff*0.382:.2f})，距现价 +{(low+diff*0.382)/close*100-100:.1f}%
""")

# ═══════════════════════════════════════════════════════
# 量价分析
# ═══════════════════════════════════════════════════════
print("─" * 65)
print("  📊 二、量价关系 — 判断反弹性质")
print("─" * 65)

# 下跌阶段量能
drop_phase = [r for r in recent if recent.index(r) >= high_idx and recent.index(r) <= high_idx + low_idx]
drop_vol_avg = sum(r["v"] for r in drop_phase) / len(drop_phase) if drop_phase else 0

# 反弹阶段量能
rebound_idx = high_idx + low_idx
rebound_phase = recent[rebound_idx:]
rebound_vol_avg = sum(r["v"] for r in rebound_phase) / len(rebound_phase) if rebound_phase else 0

# 最近几天
recent_3 = recent[-3:]
recent_3_vol = [r["v"]/1e8 for r in recent_3]
recent_3_price = [r["c"] for r in recent_3]

print(f"""
  下跌阶段 ({drop_phase[0]['d'] if drop_phase else '?'} → {low_date}):
    天数: {len(drop_phase)}天  跌幅: {(low_after/high_all-1)*100:.1f}%
    日均量: {drop_vol_avg/1e8:.2f}亿手
    特征: {'放量下跌 → 恐慌抛售' if drop_vol_avg > 1.8e8 else '缩量下跌 → 正常调整'}

  反弹阶段 ({rebound_phase[0]['d'] if rebound_phase else '?'} → {recent[-1]['d']}):
    天数: {len(rebound_phase)}天  涨幅: {(close/low_after-1)*100:.1f}%
    日均量: {rebound_vol_avg/1e8:.2f}亿手

  量价研判:
    反弹量 / 下跌量 = {rebound_vol_avg/drop_vol_avg:.2f}x
""")

if rebound_vol_avg > drop_vol_avg * 1.2:
    print("    🟢 反弹放量 > 下跌放量 → 有资金进场，反弹质量较好")
elif rebound_vol_avg > drop_vol_avg * 0.8:
    print("    🟡 反弹量能与下跌量能接近 → 多空博弈均衡")
else:
    print("    🔴 反弹缩量 → 无量反弹，可能是'死猫跳'，需警惕二次探底")

# 最近3天量价配合
vol_3d_trend = recent_3_vol[-1] > recent_3_vol[-2] > recent_3_vol[-3]
price_3d_trend = recent_3_price[-1] > recent_3_price[-2] > recent_3_price[-3]

print(f"""
  近3日量价:
    成交量趋势: {'递增 📈' if vol_3d_trend else '递减 📉' if recent_3_vol[-1] < recent_3_vol[-3] else '波动'}
    收盘价趋势: {'递增 📈' if price_3d_trend else '递减 📉' if recent_3_price[-1] < recent_3_price[-3] else '波动'}
    配合判断: {'🟢 量价齐升，反弹健康' if vol_3d_trend and price_3d_trend else '🟡 量价背离，反弹力度存疑' if not vol_3d_trend and price_3d_trend else '⚪ 正常'}
""")

# ═══════════════════════════════════════════════════════
# 均线阻力分析
# ═══════════════════════════════════════════════════════
print("─" * 65)
print("  📈 三、均线阻力/支撑分析")
print("─" * 65)

ind = data["kline"]["indicators"]
mas = [
    ("MA5", ind["ma5"]),
    ("MA10", ind["ma10"]),
    ("MA20", ind["ma20"]),
    ("MA60", ind["ma60"]),
]

print(f"  {'均线':8s} {'价位':>8s}  {'角色':12s}  {'说明'}")
print(f"  {'─'*50}")
for name, val in mas:
    if close > val:
        role = "🟢 支撑"
        note = f"现价在上方 +{(close/val-1)*100:.1f}%"
    else:
        role = "🔴 阻力"
        note = f"现价在下方 {(close/val-1)*100:.1f}%"
    print(f"  {name:8s} {val:>8.2f}  {role:12s}  {note}")

# ═══════════════════════════════════════════════════════
# 筹码分布估算
# ═══════════════════════════════════════════════════════
print("─" * 65)
print("  🏔️ 四、筹码分布（估算）")
print("─" * 65)

# 按价格区间估算成交量分布
price_buckets = {}
for r in recent:
    bucket = int(r["c"] // 5) * 5
    label = f"{bucket}-{bucket+5}元"
    if label not in price_buckets:
        price_buckets[label] = 0
    price_buckets[label] += r["v"]

total_vol = sum(price_buckets.values())
print(f"\n  {'价格区间':12s}  {'换手占比':>8s}  {'特征'}")
print(f"  {'─'*45}")
for label in sorted(price_buckets.keys(), key=lambda x: int(x.split('-')[0])):
    pct = price_buckets[label] / total_vol * 100
    bar = "█" * int(pct // 2)
    marker = ""
    lo = int(label.split('-')[0])
    hi = int(label.split('-')[1].replace('元',''))
    if lo <= close <= hi:
        marker = " ← 当前价"
    print(f"  {label:12s}  {bar:12s} {pct:5.1f}%{marker}")

# 套牢盘估算
above_close = sum(v for k, v in price_buckets.items()
                  if int(k.split('-')[0]) >= 35)
below_close = sum(v for k, v in price_buckets.items()
                  if int(k.split('-')[1].replace('元','')) <= 30)

print(f"""
  套牢盘(>35元区间): {above_close/total_vol*100:.1f}%  ← 反弹至此将遇强阻力
  获利盘(<30元区间): {below_close/total_vol*100:.1f}%
""")

# ═══════════════════════════════════════════════════════
# 反弹情景推演
# ═══════════════════════════════════════════════════════
print("─" * 65)
print("  🎯 五、反弹路径情景推演")
print("─" * 65)

# 路径1: V型反转
# 路径2: 反弹→横盘→再探
# 路径3: 反弹→遇阻→二次探底
# 路径4: 继续下跌

scenarios_rebound = [
    {
        "name": "🟢 V型反转 (最乐观)",
        "prob": 10,
        "path": f"{close} → 突破38.2%({low+diff*0.382:.1f}) → 50%({low+diff*0.5:.1f}) → 61.8%({low+diff*0.618:.1f})",
        "target": f"{low+diff*0.618:.1f} 元 (+{(low+diff*0.618)/close*100-100:.1f}%)",
        "condition": "Q2业绩超预期 + 大盘走强 + 北向资金流入",
    },
    {
        "name": "🟡 反弹→遇阻回落 (最可能)",
        "prob": 40,
        "path": f"{close} → 38.2%({low+diff*0.382:.1f})遇阻 → 回踩30元 → 横盘整理",
        "target": f"30-36元 区间震荡",
        "condition": "Q2符合预期，存量博弈，主力继续出货",
    },
    {
        "name": "🟡 二次探底 (较可能)",
        "prob": 30,
        "path": f"{close} → 反弹至35-38 → 再次跌破30 → 测试25元支撑",
        "target": f"25-30元",
        "condition": "Q2低于预期 + 大盘走弱 + 大股东加速减持",
    },
    {
        "name": "🔴 继续新低 (最悲观)",
        "prob": 20,
        "path": f"{close} → 跌破30 → 跌破25.44前低 → 测试20元",
        "target": f"20-25元 ({(20/close-1)*100:.0f}%)",
        "condition": "业绩暴雷或系统性风险",
    },
]

print(f"  {'情景':20s} {'概率':6s}  {'目标区':12s}  {'路径'}")
print(f"  {'─'*72}")
for s in scenarios_rebound:
    bar = "█" * (s["prob"] // 5)
    print(f"  {s['name']:20s} {s['prob']}% {bar:8s} {s['target']:12s}")
    print(f"    → {s['path']}")
    print(f"    条件: {s['condition']}")
    print()

# 期望值
exp_rebound = sum(s["prob"] for s in scenarios_rebound if "反转" in s["name"])  # V型概率
exp_range = sum(s["prob"] for s in scenarios_rebound if "遇阻" in s["name"] or "二次" in s["name"])  # 震荡概率
exp_down = sum(s["prob"] for s in scenarios_rebound if "新低" in s["name"])  # 下跌概率

print(f"""  📊 反弹路径概率总结:
  🟢 V型反转: {exp_rebound}%
  🟡 反弹遇阻/二次探底: {exp_range}%
  🔴 继续新低: {exp_down}%

  最可能路径: 反弹至 38.2%({low+diff*0.382:.1f}元)附近遇阻，然后回踩 30 元支撑
""")

# ═══════════════════════════════════════════════════════
# 关键价位汇总
# ═══════════════════════════════════════════════════════
print("─" * 65)
print("  ⚡ 六、关键价位作战图")
print("─" * 65)

print(f"""
  🔴 强阻力: 49-54元  (前高区域，巨量套牢盘)
  🟠 中等阻力: 42元    (61.8%反弹位)
  🟡 弱阻力: 38元      (38.2%反弹位 + 6月中旬整理平台)
  ────────────────────  当前价 34.19 ───
  🟢 第一支撑: 30元    (整数关口 + 近期整理平台)
  🟢 第二支撑: 25.4元  (前低，跌破将确认下跌趋势)
  🟢 极限支撑: 20元    (MA120附近 + 5月平台)
""")

# ═══════════════════════════════════════════════════════
# 形态识别
# ═══════════════════════════════════════════════════════
print("─" * 65)
print("  📐 七、K线形态识别")
print("─" * 65)

# 检查最近几天的组合形态
last5 = recent[-5:]
bodies = [(r["c"]-r["o"])/r["o"]*100 for r in last5]
ranges = [(r["h"]-r["l"])/r["o"]*100 for r in last5]

print(f"""
  近5日K线特征:
  日期        开盘    收盘    实体%    振幅%
  {'─'*45}""")
for i, r in enumerate(last5):
    body_pct = (r["c"] - r["o"]) / r["o"] * 100
    range_pct = (r["h"] - r["l"]) / r["o"] * 100
    bar = "🟢" if r["c"] > r["o"] else "🔴"
    print(f"  {bar} {r['d']}  {r['o']:>6.2f}  {r['c']:>6.2f}  {body_pct:>+5.1f}%  {range_pct:>5.1f}%")

# 判断锤子线/倒锤子等
last = recent[-1]
body = abs(last["c"] - last["o"])
lower_shadow = min(last["c"], last["o"]) - last["l"]
upper_shadow = last["h"] - max(last["c"], last["o"])
total_range = last["h"] - last["l"]

# 8/5 大阳线分析
print(f"""
  昨日(8/5)K线分析:
    实体: {body:.2f} ({(last['c']/last['o']-1)*100:+.1f}%)
    下影线: {lower_shadow:.2f} ({lower_shadow/total_range*100:.0f}% of range)
    上影线: {upper_shadow:.2f} ({upper_shadow/total_range*100:.0f}% of range)
    形态: {'🟢 光头大阳线 → 强势信号' if upper_shadow/total_range < 0.1 and body/total_range > 0.6 else '🟢 大阳线 → 多头主导' if last['c'] > last['o'] and body/total_range > 0.5 else '锤子线 → 底部反转' if lower_shadow > body*2 and last['c'] > last['o'] else '普通K线'}
""")

# ═══════════════════════════════════════════════════════
# 结论
# ═══════════════════════════════════════════════════════
print("─" * 65)
print("  💡 八、综合结论")
print("─" * 65)

print(f"""
  会反弹吗？ —— 已经在反弹了！从 {low_after} 弹到 {close}（+{(close/low_after-1)*100:.0f}%）

  但关键是：这是反转还是反弹？

  🟢 支持继续反弹的因素:
    ① MACD 刚金叉，历史上金叉后通常有 2-3 周的惯性上涨
    ② KDJ 从超卖区(-17)回升到 70，还有上行空间
    ③ 8/5 放量大阳线(+14%)，短线多头气势强
    ④ 距 38.2% 反弹位({low+diff*0.382:.1f})仅 +{(low+diff*0.382)/close*100-100:.1f}%，空间存在

  🔴 制约反弹高度的因素:
    ① {above_close/total_vol*100:.0f}% 的筹码在 35+元区间 → 越往上套牢盘越重
    ② 大股东持续减持(2.65亿股) → 每次反弹都是出货窗口
    ③ 股东人数暴增 82% → 散户接盘，主力撤退
    ④ 成交量递减 → 若反弹缩量，高度受限
    ⑤ 从 54 跌到 25 的杀伤力太大 → V型反转概率极低

  🎯 概率判断:
    ┌────────────────────────────────────────────┐
    │  反弹至 38-42元 (38.2%-50%分位):  70%     │
    │  反弹至 42-50元 (50%-61.8%分位):  30%     │
    │  突破前高 54元 (V型反转):          10%     │
    │  跌破 25元 (二次探底失败):         20%     │
    └────────────────────────────────────────────┘

  ⚠️ 操作建议:
    如果你持有: 利用反弹在 38-42 区间逐步减仓，别指望回到 54
    如果你想买: 等回调到 28-30 再考虑，当前位置(34)追高风险收益比不佳
    止损线: 跌破 28 元应果断离场（反弹失败信号）

  核心矛盾: 基本面在好转(Q1超2025全年)，但筹码面在恶化(主力出货)
           技术面短期偏多，但中期压力巨大
           这是一场"业绩反转"vs"主力出货"的博弈
""")

print("=" * 65)
print("  免责声明: 以上分析仅供学习参考，不构成投资建议。")
print("=" * 65)
