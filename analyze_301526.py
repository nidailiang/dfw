#!/usr/bin/env python3
"""
国际复材 (301526) 综合分析报告
—— 技术面 + 基本面 + 概率预测
"""
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── 加载已采集的数据 ──
with open("301526_data.json", "r") as f:
    data = json.load(f)

kl = data["kline"]
fin = data["financial"]
fc = data.get("forecast", [])
rs = data.get("research", {})
hd = data.get("holders", {})
it_data = data.get("insider_trades", {})
nb = data.get("northbound", {})

lt = kl["latest"]
ind = kl["indicators"]
ret = kl["returns"]
la = fin.get("latest_annual", {})
lq = fin.get("latest_quarter", {})

close = lt["close"]
total_shares = 37.7e8  # 约37.7亿股总股本
market_cap = close * total_shares / 1e8

print("=" * 70)
print("  国际复材 (301526)  —  综合深度分析报告")
print(f"  报告日期: 2026-08-06  |  最新收盘: {close}元  |  市值: {market_cap:.0f}亿")
print("=" * 70)

# ═══════════════════════════════════════════════════════════
# 1. K线走势 + 技术指标
# ═══════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("  📈 一、技术面分析")
print("─" * 60)

# 关键价格位
recent = kl["recent_100"]
high_60d = max(r["h"] for r in recent[-60:])
low_60d = min(r["l"] for r in recent[-60:])
high_all = max(r["h"] for r in recent)
low_all = min(r["l"] for r in recent)

print(f"""
  【价格概览】
  最新收盘: {close} 元
  60日最高: {high_60d} 元  (6/26 盘中最高 54.08)
  60日最低: {low_60d} 元  (3/23 盘中最低 10.16)
  年内振幅: {(high_all/low_all - 1)*100:.0f}%

  【均线系统】
  MA5:   {ind['ma5']:.2f}  {'✅ 站上' if close > ind['ma5'] else '⚠️ 跌破'}
  MA10:  {ind['ma10']:.2f}  {'✅ 站上' if close > ind['ma10'] else '⚠️ 跌破'}
  MA20:  {ind['ma20']:.2f}  {'✅ 站上' if close > ind['ma20'] else '⚠️ 跌破'}
  MA60:  {ind['ma60']:.2f}  {'✅ 站上' if close > ind['ma60'] else '⚠️ 跌破'}
  MA120: {ind['ma120']:.2f}  {'✅ 站上' if close > ind['ma120'] else '⚠️ 跌破'}
  MA250: {ind['ma250']:.2f}  {'✅ 站上' if close > ind['ma250'] else '⚠️ 跌破'}

  均线判定: {'🟢 多头排列，中长期趋势向上' if close > ind['ma5'] > ind['ma10'] > ind['ma20'] > ind['ma60'] else '🟡 短期均线缠绕，方向待确认'}
""")

# ── KDJ 分析 ──
k_val, d_val, j_val = ind["K"], ind["D"], ind["J"]
kdj_signal = ""
if j_val > 100:
    kdj_signal = "🔴 J值>100，超买区域，短线回调风险较大"
elif j_val > 80:
    kdj_signal = "🟡 J值>80，偏强区域，接近超买但尚未极端"
elif j_val < 0:
    kdj_signal = "🟢 J值<0，超卖区域，短线反弹概率大"
elif j_val < 20:
    kdj_signal = "🟢 J值<20，偏弱区域，接近超卖"
else:
    kdj_signal = "⚪ KDJ处于中性区域，无明显极端信号"

# 判断金叉死叉
prev_k = recent[-2]["K"]
prev_d = recent[-2]["D"]
kdj_cross = ""
if prev_k <= prev_d and k_val > d_val:
    kdj_cross = "🟢 KDJ 金叉! (K线上穿D线) —— 短线买入信号"
elif prev_k >= prev_d and k_val < d_val:
    kdj_cross = "🔴 KDJ 死叉! (K线下穿D线) —— 短线卖出信号"
else:
    kdj_cross = "— 无交叉信号"

print(f"""  【KDJ (9,3,3)】
  K={k_val:.2f}  D={d_val:.2f}  J={j_val:.2f}
  {kdj_signal}
  {kdj_cross}""")

# ── MACD 分析 ──
dif_v, dea_v, bar = ind["DIF"], ind["DEA"], ind["MACD"]
prev_dif = recent[-2]["DIF"]
prev_dea = recent[-2]["DEA"]
prev_bar = recent[-2]["MACD"]

macd_pos = ""
if dif_v > 0 and dea_v > 0:
    macd_pos = "🟢 DIF/DEA均在零轴上方 → 多头主导"
elif dif_v < 0 and dea_v < 0:
    macd_pos = "🔴 DIF/DEA均在零轴下方 → 空头主导"
elif dif_v > 0 > dea_v:
    macd_pos = "🟡 DIF已上零轴，DEA仍在下方 → 多空转换中，偏多"
else:
    macd_pos = "🟡 DIF下零轴，DEA在上方 → 多空转换中，偏空"

macd_cross = ""
if prev_dif <= prev_dea and dif_v > dea_v:
    macd_cross = "🟢 MACD 金叉! (DIF上穿DEA) —— 中期买入信号"
elif prev_dif >= prev_dea and dif_v < dea_v:
    macd_cross = "🔴 MACD 死叉! (DIF下穿DEA) —— 中期卖出信号"
else:
    macd_cross = "— 无交叉"

bar_status = "红柱扩张 🔥" if bar > 0 and bar > prev_bar else ("红柱收缩 📉" if bar > 0 else ("绿柱扩张 ⚠️" if bar < 0 and bar < prev_bar else "绿柱收缩 🌤️"))

print(f"""
  【MACD (12,26,9)】
  DIF={dif_v:.3f}  DEA={dea_v:.3f}  柱={bar:.3f}
  {macd_pos}
  {macd_cross}
  柱状线: {bar_status}
""")

# ── 成交量分析 ──
vol_5d_avg = sum(r["v"] for r in recent[-6:-1]) / 5
vol_latest = lt["volume"]
vol_ratio = vol_latest / vol_5d_avg
vol_20d_avg = sum(r["v"] for r in recent[-21:-1]) / 20
vol_20d_ratio = vol_latest / vol_20d_avg

# 近期量价关系
recent_5 = recent[-5:]
price_trend_5d = [r["c"] for r in recent_5]
vol_trend_5d = [r["v"] for r in recent_5]

print(f"""  【成交量分析】
  最新成交量: {vol_latest/1e8:.2f}亿手
  近5日均量: {vol_5d_avg/1e8:.2f}亿手
  量比(5日): {vol_ratio:.2f}x {'🔥 放量明显' if vol_ratio > 1.5 else '⚪ 正常' if vol_ratio > 0.7 else '❄️ 缩量'}
  近20日均量: {vol_20d_avg/1e8:.2f}亿手
  量比(20日): {vol_20d_ratio:.2f}x

  【近期量价配合】
  最近5日量价: {'🟢 量价齐升，多头强势' if vol_ratio > 1.2 and ret['5d'] > 5 else '🟡 量价背离，需谨慎' if vol_ratio > 1.2 and ret['5d'] < 0 else '⚪ 正常'}
""")

# ── 走势阶段判断 ──
print(f"""  【走势阶段划分】
  近5日涨幅:  {ret['5d']:+.2f}%
  近10日涨幅: {ret['10d']:+.2f}%
  近20日涨幅: {ret['20d']:+.2f}%
  近60日涨幅: {ret['60d']:+.2f}%
""")

# 判断所处阶段
high_60d_idx = max(range(len(recent)-60, len(recent)), key=lambda i: recent[i]["h"])
high_60d_price = recent[high_60d_idx]["h"]
drawdown_from_high = (close - high_60d_price) / high_60d_price * 100
low_recent_idx = min(range(max(high_60d_idx, len(recent)-30), len(recent)), key=lambda i: recent[i]["l"])
low_recent_price = recent[low_recent_idx]["l"]
rebound_from_low = (close - low_recent_price) / low_recent_price * 100

print(f"""  从60日高点({high_60d_price}): {drawdown_from_high:+.1f}%
  从近期低点({low_recent_price}, {recent[low_recent_idx]['d']}): {rebound_from_low:+.1f}%

  阶段判断: {'🔴 超跌反弹阶段 —— 从高点大幅回落后快速反弹' if drawdown_from_high < -20 and rebound_from_low > 10 else '🟡 高位震荡 —— 从高点回落后企稳' if drawdown_from_high < -10 else '🟢 强势上攻 —— 接近或创出新高'}
""")

# ═══════════════════════════════════════════════════════════
# 2. 基本面分析
# ═══════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("  📊 二、基本面分析")
print("─" * 60)

print(f"""
  【财务数据】
  最新年报 (2025): 营收 {la.get('revenue',0)/1e8:.1f}亿 (+{la.get('rev_growth',0)}%)
                    净利 {la.get('profit',0)/1e8:.2f}亿 (+{la.get('profit_growth',0)}%)
                    EPS {la.get('eps')}  毛利率 {la.get('gross_margin')}%  ROE {la.get('roe')}%

  最新季报 (2026Q1): 营收 {lq.get('revenue',0)/1e8:.1f}亿 (+{lq.get('rev_growth',0)}%)
                    净利 {lq.get('profit',0)/1e8:.2f}亿 (+{lq.get('profit_growth',0)}%)
                    单季EPS {lq.get('eps')} 已超越2025全年EPS({la.get('eps')})!

  ⚡ 关键亮点: Q1单季净利润2.7亿，已超过2025全年2.72亿的99%！

  【财务健康度】
  资产负债率: {la.get('debt_ratio')}%  {'⚠️ 偏高' if la.get('debt_ratio',0) > 60 else '⚪ 中等' if la.get('debt_ratio',0) > 40 else '✅ 健康'}
  流动比率:   {la.get('current_ratio')}  {'⚠️ <1，短期偿债压力' if la.get('current_ratio',0) < 1 else '✅ 正常'}
  速动比率:   {la.get('quick_ratio')}  {'⚠️ <1' if la.get('quick_ratio',0) < 1 else '✅'}
  经营现金流/EPS: {la.get('cfps')}/{la.get('eps')}  {'✅ 现金流健康' if la.get('cfps',0) > la.get('eps',0) else '⚠️ 现金流弱于利润'}
""")

# ── PE 估值 ──
print("  【估值分析 (盈利预测来自5家机构)】")
for f in fc:
    yr = f["year"]
    eps = f["eps_mean"]
    pe = close / eps if eps else 0
    eps_range = f"({f['eps_min']}~{f['eps_max']})"
    print(f"  {yr}E: EPS均值 {eps} {eps_range} | 远期PE: {pe:.1f}x | {f['institutions']}家机构")

# 行业对比
print(f"""
  当前静态PE (基于2025EPS 0.07): {close/0.07:.1f}x  ← 极高，因为2025基数低
  2026年动态PE: {close/0.42:.1f}x  (基于EPS 0.42)
  2027年动态PE: {close/0.64:.1f}x  (基于EPS 0.64)

  估值判断: 2026年PE {close/0.42:.1f}x 对于一家增速400%+的化工企业，
  若行业平均PE约30-40x，则当前估值{'🟡 偏高' if close/0.42 > 50 else '⚪ 合理偏高' if close/0.42 > 30 else '✅ 合理'}
""")

# ═══════════════════════════════════════════════════════════
# 3. 机构调研
# ═══════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("  📋 三、机构调研 & 评级")
print("─" * 60)

print(f"""
  研报总数: {rs.get('total', 0)}篇
  近一月研报: {rs.get('recent_month_count', 0)}篇

  最近研报:""")
for r in rs.get("recent_reports", [])[:5]:
    print(f"    [{r['date']}] {r['org']}: {r['title'][:50]}")

print(f"""
  机构覆盖: 5家给出2026盈利预测，覆盖度{'一般' if fc[0]['institutions'] < 10 else '较好'}
  行业平均EPS: {fc[0].get('industry_avg', 'N/A')}
  个股EPS vs 行业: 0.42 vs {fc[0].get('industry_avg', 'N/A')} (仅为行业均值的{0.42/fc[0].get('industry_avg',1)*100:.0f}%)
""")

# ═══════════════════════════════════════════════════════════
# 4. 股东结构
# ═══════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("  👥 四、股东结构 & 筹码分布")
print("─" * 60)

cur_holders = hd.get("latest", {})
yoy_change = hd.get("yoy_change_pct", 0)

print(f"""
  最新股东人数: {cur_holders.get('total_holders', '?'):,}户 (2026-03-31)
  人均持股: {cur_holders.get('avg_hold', '?'):,}股
  同比变化: {yoy_change:+.1f}% {'🔴 筹码大幅分散！散户大量涌入' if yoy_change > 50 else '⚠️ 筹码分散' if yoy_change > 20 else '✅ 筹码集中' if yoy_change < -10 else '⚪ 变化不大'}

  【大股东增减持】""")

# 大股东减持分析
trades = it_data.get("recent_20", [])
if trades:
    first_holding = trades[0].get("remaining", 0) if trades else 0
    last_holding = trades[-1].get("remaining", 0) if trades else 0
    if first_holding and last_holding:
        reduction = (first_holding - last_holding) / 1e8
        print(f"""  主要减持方: 上海某投资管理公司 (PE基金)
  累计减持: 从{first_holding/1e8:.2f}亿股 → {last_holding/1e8:.2f}亿股
  减持 {reduction:.2f}亿股 🔴 大幅减持！""")

print(f"""
  ⚠️ 风险提示: 股东人数同比暴增81.8%，叠加PE基金持续大幅减持，
  筹码从集中走向分散，这是典型的'拉升出货'信号。""")

# ═══════════════════════════════════════════════════════════
# 5. Q2 业绩概率预测
# ═══════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("  🔮 五、Q2业绩概率预测")
print("─" * 60)

# Q1已知: 营收22.15亿, 净利2.7亿
# 全年共识: EPS 0.42 → 净利约 0.42*37.7 = 15.8亿
# 假设H1占全年40-50%

q1_rev = 22.15
q1_profit = 2.70
fy_profit_consensus = 0.42 * 37.7  # 约15.83亿

# Q2情景分析
scenarios = [
    {
        "label": "🔥 大超预期",
        "prob": 15,
        "q2_rev": 28.0,
        "q2_profit": 4.5,
        "h1_profit": q1_profit + 4.5,
        "desc": "产品涨价+新产能释放+下游风电/航空需求爆发",
        "price_impact": "+15%~+30%",
        "target": (38, 44),
    },
    {
        "label": "✅ 符合预期偏强",
        "prob": 30,
        "q2_rev": 25.0,
        "q2_profit": 3.5,
        "h1_profit": q1_profit + 3.5,
        "desc": "景气维持，量价齐稳，新产能按计划爬坡",
        "price_impact": "+5%~+15%",
        "target": (36, 39),
    },
    {
        "label": "⚪ 符合预期",
        "prob": 30,
        "q2_rev": 23.0,
        "q2_profit": 3.0,
        "h1_profit": q1_profit + 3.0,
        "desc": "经营平稳，略有季节性波动",
        "price_impact": "-5%~+5%",
        "target": (32, 36),
    },
    {
        "label": "⚠️ 低于预期",
        "prob": 15,
        "q2_rev": 20.0,
        "q2_profit": 2.0,
        "h1_profit": q1_profit + 2.0,
        "desc": "原材料涨价侵蚀利润，订单交付延迟",
        "price_impact": "-10%~-20%",
        "target": (27, 31),
    },
    {
        "label": "💀 大幅低于预期",
        "prob": 10,
        "q2_rev": 17.0,
        "q2_profit": 1.0,
        "h1_profit": q1_profit + 1.0,
        "desc": "行业需求骤降或公司经营出现重大问题",
        "price_impact": "-20%~-35%",
        "target": (22, 27),
    },
]

print(f"""
  Q1已知: 营收{q1_rev}亿, 净利{q1_profit}亿
  全年净利共识: {fy_profit_consensus:.1f}亿 (基于EPS 0.42)

  {"情景":12s}  {"概率":6s}  {"Q2营收":8s}  {"Q2净利":8s}  {"H1净利":8s}  {"股价区间":14s}
  {"─"*60}""")

for s in scenarios:
    bar = "█" * (s["prob"] // 5)
    print(f"  {s['label']:12s}  {s['prob']}%{bar:5s}  {s['q2_rev']}亿{'':4s}  {s['q2_profit']}亿{'':4s}  {s['h1_profit']}亿{'':4s}  {s['target'][0]}-{s['target'][1]}元")

# 期望值
exp_return = sum(s["prob"] * (sum(s["target"])/2 - close) / close * 100 for s in scenarios) / 100
win_prob = sum(s["prob"] for s in scenarios if s["target"][0] > close)
lose_prob = sum(s["prob"] for s in scenarios if s["target"][1] < close)

print(f"""
  📊 概率加权期望收益: {exp_return:+.1f}%
  🟢 盈利概率 (股价>={close}): {win_prob}%
  🔴 亏损概率: {lose_prob}%

  Q2业绩核心假设:
  - 公司主营复合材料(风电叶片+航空材料+汽车轻量化)
  - Q1已展现强劲反转(Q1 EPS超2025全年)
  - 但Q2通常为风电淡季，需关注订单持续性
  - H1利润约5.7-7.2亿，全年15.8亿目标需H2更强表现
""")

# ═══════════════════════════════════════════════════════════
# 6. 多维度综合研判
# ═══════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("  🌍 六、宏观 & 行业环境")
print("─" * 60)

print("""
  【A股大盘环境】(2026年8月)
  - 上证指数近期小幅反弹，8/5涨+1.47%
  - 市场整体处于震荡修复阶段，成交量温和
  - 创业板指表现分化，题材股活跃度提升

  【美国/外围环境】
  - 美联储降息预期反复，全球风险偏好波动
  - 中美贸易摩擦持续，复合材料出口可能受限
  - 全球风电装机需求增长，利好上游材料企业

  【行业政策】
  - 🟢 利好: 新能源/风电行业政策持续支持
  - 🟢 利好: 航空复合材料国产替代加速
  - 🟢 利好: 汽车轻量化趋势
  - ⚠️  风险: 碳纤维等原材料价格波动
  - ⚠️  风险: 行业产能扩张导致竞争加剧

  【消息面评估】
  - 近期无明显负面新闻
  - 公司处于业绩反转期，市场关注度提升
  - 但大股东持续减持构成最大利空信号
  - Q2业绩(预计8月下旬披露)是关键催化剂
""")

# ═══════════════════════════════════════════════════════════
# 7. 综合评分
# ═══════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("  ⭐ 七、综合评分卡")
print("─" * 60)

scores = [
    ("技术面 (MACD金叉+KDJ中性+均线多头)", 7.5, "短期偏多但波动大"),
    ("基本面 (Q1超预期反转+全年高增长)", 8.0, "业绩拐点明确"),
    ("估值 (2026PE ~81x, 相对成长性尚可)", 5.5, "估值偏高但增长可消化"),
    ("筹码面 (股东暴增+大股东减持)", 3.0, "严重利空信号"),
    ("机构关注 (5家覆盖, 研报偏少)", 5.0, "关注度一般"),
    ("行业前景 (风电+航空+轻量化)", 7.5, "赛道中长期向好"),
    ("大盘环境 (震荡修复)", 6.0, "中性"),
    ("资金面 (近期放量反弹)", 6.5, "短线资金活跃"),
]

total_score = sum(s[1] * w for s, w in zip(scores, [2, 2, 1.5, 1.5, 1, 1.5, 1, 1.5]))
max_score = sum(w for _, w in zip(scores, [2, 2, 1.5, 1.5, 1, 1.5, 1, 1.5]))
pct = total_score / max_score * 100

print(f"  {'维度':20s}  {'评分':6s}  {'说明'}")
print(f"  {'─'*50}")
for name, sc, note in scores:
    bar = "🟢" if sc >= 7 else "🟡" if sc >= 5 else "🔴"
    print(f"  {bar} {name:18s}  {sc:.1f}/10  {note}")

print(f"""
  🎯 综合评分: {pct:.0f}/100  (加权)

  操作建议:
  ┌────────────────────────────────────────────────────────┐
  |  📌 短线: 技术面偏多(MACD刚金叉+KDJ触底回升)，          |
  |     但股价弹性极大(60日振幅超400%)，追高风险巨大        |
  |                                                        |
  |  📌 中线: 基本面反转逻辑成立(Q1超2025全年)，             |
  |     但Q2是关键验证点，估值偏高需业绩兑现                |
  |                                                        |
  |  📌 长线: 赛道逻辑好(风电+航空)，但筹码分散+减持        |
  |     构成重大隐患，不适合重仓长持                        |
  |                                                        |
  |  ⚠️  最大风险: 大股东持续减持 + 散户大量涌入              |
  |     这是典型的"主力出货"特征，需高度警惕                |
  └────────────────────────────────────────────────────────┘
""")

# ═══════════════════════════════════════════════════════════
# 8. 股价概率分布
# ═══════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("  🎲 八、3个月股价概率分布")
print("─" * 60)

price_scenarios_3m = [
    (5,  ">50元  (突破前高)", 45, 55, "业绩持续超预期+牛市环境"),
    (15, "40-50元 (挑战前高)", 40, 50, "Q2符合/略超预期+题材活跃"),
    (25, "35-40元 (温和上涨)", 35, 40, "Q2符合预期+估值消化"),
    (25, "28-35元 (横盘震荡)", 28, 35, "多空博弈+等待方向"),
    (20, "22-28元 (回落调整)", 22, 28, "Q2低于预期或大盘走弱"),
    (10, "<22元  (深度回调)", 15, 22, "业绩大幅miss+系统性风险"),
]

print(f"  {'概率':6s}  {'情景':20s}  {'价格区间':14s}")
print(f"  {'─'*45}")
for prob, label, lo, hi, desc in price_scenarios_3m:
    bar = "█" * (prob // 5)
    print(f"  {prob}% {bar:5s}  {label:20s}  {lo}-{hi}元")

exp_3m = sum(p * (lo+hi)/2 for p, _, lo, hi, _ in price_scenarios_3m) / 100
print(f"""
  3个月期望价格: {exp_3m:.1f}元 (当前{close}元, 预期收益 {(exp_3m/close-1)*100:+.1f}%)
""")

print("\n" + "=" * 70)
print("  免责声明: 以上分析仅基于公开数据和模型推演，不构成投资建议。")
print("  股市有风险，投资需谨慎。")
print("=" * 70)
