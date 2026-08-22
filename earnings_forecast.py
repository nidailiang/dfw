#!/usr/bin/env python3
"""拓荆科技 & 沐曦股份 — Q2业绩概率预测"""
import json

# ═══════════════════════════════════════════
# 拓荆科技 688072
# ═══════════════════════════════════════════

pjtd = {
    "name": "拓荆科技 688072",
    "entry": 627,
    "current": 677.88,
    "report_date": "8月21日",
    "q1_rev": 11.12,  # 亿
    "q1_net": 5.71,   # 亿（含非经常性）
    "q1_recurring": 1.02,  # 亿（扣非）
    "fy_rev_consensus": 87.06,  # 13家机构均值
    "fy_rev_range": [84.5, 90.9],
    "fy_np_consensus": 16.66,
    "fy_np_range": [13.27, 19.44],
    "fy_eps_consensus": 5.90,
    "orders_hand": 110,  # 亿在手订单
    "q2_consensus_rev": 17.2,  # Q2营收共识
    "gross_margin_q1": 41.7,  # %
    "n_analysts": 13,
}

# 沐曦股份 688802
pmx = {
    "name": "沐曦股份 688802",
    "entry": 713,
    "current": 726.03,
    "report_date": "待披露",
    "q1_rev": 5.62,
    "q1_net": -0.99,
    "fy_rev_consensus": 35.16,
    "fy_rev_range": [30.97, 40.79],
    "fy_np_consensus": 0.82,
    "fy_np_range": [0.14, 3.25],
    "fy_eps_consensus": 0.20,
    "gross_margin_q1": 60.0,
    "n_analysts": 6,
    "listed_date": "2025-12-17",
    "ipo_close": 830,
    "target_avg": 892,
}

# ═══════════════════════════════════════════
# 概率模型
# ═══════════════════════════════════════════

def analyze(name, entry, current, q1_rev, q1_net, fy_rev, fy_np, q2_rev_cons, orders, gm,
            n_analysts, is_profitable_q1):
    """生成业绩概率预测"""

    # ── Q2 营收预测 ──
    h1_rev_need = fy_rev * 0.45  # H1通常占全年35-50%, 设备股偏H2

    # Q2 营收情景
    beat_rev = q2_rev_cons * 1.10   # 超预期10%+
    inline_hi = q2_rev_cons * 1.05
    inline_lo = q2_rev_cons * 0.95
    miss_rev = q2_rev_cons * 0.88

    scenarios = [
        {
            "label": "超预期",
            "prob": 25,
            "rev_q2": round(beat_rev, 1),
            "rev_h1": round(q1_rev + beat_rev, 1),
            "h1_pct_of_fy": round((q1_rev + beat_rev) / fy_rev * 100, 1),
            "desc": "交付超预期+新品放量+毛利率提升",
            "price_range": [],
            "action": "",
        },
        {
            "label": "符合预期偏强",
            "prob": 30,
            "rev_q2": round(inline_hi, 1),
            "rev_h1": round(q1_rev + inline_hi, 1),
            "h1_pct_of_fy": round((q1_rev + inline_hi) / fy_rev * 100, 1),
            "desc": "按计划交付，毛利率稳定改善",
            "price_range": [],
            "action": "",
        },
        {
            "label": "符合预期偏弱",
            "prob": 25,
            "rev_q2": round(inline_lo, 1),
            "rev_h1": round(q1_rev + inline_lo, 1),
            "h1_pct_of_fy": round((q1_rev + inline_lo) / fy_rev * 100, 1),
            "desc": "交付略慢但全年目标可维持",
            "price_range": [],
            "action": "",
        },
        {
            "label": "低于预期",
            "prob": 20,
            "rev_q2": round(miss_rev, 1),
            "rev_h1": round(q1_rev + miss_rev, 1),
            "h1_pct_of_fy": round((q1_rev + miss_rev) / fy_rev * 100, 1),
            "desc": "交付延迟或客户验收推迟",
            "price_range": [],
            "action": "",
        },
    ]

    # 价格范围计算 (基于当前价和概率)
    # 超预期: +10%~+20%
    # 符合偏强: +3%~+10%
    # 符合偏弱: -3%~+3%
    # 低于预期: -8%~-15%

    price_scenarios = [
        (25, current * 1.12, current * 1.22, "超预期: +12%~+22%"),
        (30, current * 1.03, current * 1.10, "偏强: +3%~+10%"),
        (25, current * 0.97, current * 1.03, "偏弱: -3%~+3%"),
        (20, current * 0.85, current * 0.92, "低于: -8%~-15%"),
    ]

    for i, s in enumerate(scenarios):
        _, lo, hi, _ = price_scenarios[i]
        s["price_range"] = [round(lo, 0), round(hi, 0)]
        s["entry_pnl"] = [
            round((lo - entry) / entry * 100, 1),
            round((hi - entry) / entry * 100, 1),
        ]

    # ── 期望值计算 ──
    expected_return = sum(
        s["prob"] * (sum(s["price_range"]) / 2 - entry) / entry * 100
        for s in scenarios
    ) / 100

    # 胜率 (盈利概率)
    win_prob = sum(s["prob"] for s in scenarios if s["price_range"][0] > entry)
    # 亏钱概率
    lose_prob = sum(s["prob"] for s in scenarios if s["price_range"][1] < entry)
    # 打平
    flat_prob = 100 - win_prob - lose_prob

    risk_reward = abs(
        (sum(s["prob"] * (s["price_range"][0] - entry) for s in scenarios if s["price_range"][0] > entry) /
         max(sum(s["prob"] * (entry - s["price_range"][1]) for s in scenarios if s["price_range"][1] < entry), 1))
    )

    return {
        "scenarios": scenarios,
        "expected_return": round(expected_return, 1),
        "win_prob": win_prob,
        "lose_prob": lose_prob,
        "flat_prob": flat_prob,
        "price_scenarios": price_scenarios,
    }


td = analyze("拓荆科技", 627, 677.88, 11.12, 5.71, 87.06, 16.66, 17.2, 110, 41.7, 13, True)
mx = analyze("沐曦股份", 713, 726.03, 5.62, -0.99, 35.16, 0.82, 9.0, None, 60.0, 6, False)

# ═══════════════════════════════════════════
# 输出
# ═══════════════════════════════════════════

print("""
╔══════════════════════════════════════════════════════════════╗
║           Q2 业绩概率预测 — 拓荆科技 vs 沐曦股份              ║
╚══════════════════════════════════════════════════════════════╝
""")

for stock, data, result in [("拓荆科技 688072", pjtd, td), ("沐曦股份 688802", pmx, mx)]:
    print(f"""
┌─────────────────────────────────────────────────────────────┐
│  {stock}                                        │
│  买入价: {data['entry']}  当前: {data['current']}  浮盈: {round((data['current']-data['entry'])/data['entry']*100,1)}%            │
│  Q1营收: {data['q1_rev']}亿  Q1净利: {data['q1_net']}亿  全年营收共识: {data['fy_rev_consensus']}亿    │
│  覆盖机构: {data['n_analysts']}家  披露日: {data.get('report_date', '待定')}                                │
├─────────────────────────────────────────────────────────────┤
│  情景          概率    Q2营收    你的盈亏区间    操作建议     │
├─────────────────────────────────────────────────────────────┤""")

    for s in result["scenarios"]:
        bar = "█" * (s["prob"] // 5) + "▌" if s["prob"] % 5 >= 2 else "█" * (s["prob"] // 5)
        pnl = s["entry_pnl"]
        print(f"│  {s['label']:10s}  {s['prob']}% {bar:6s}  {s['rev_q2']}亿     {pnl[0]:+5.1f}%~{pnl[1]:+5.1f}%    {s['desc'][:30]}│")

    print(f"""├─────────────────────────────────────────────────────────────┤
│  📊 期望收益: {result['expected_return']:+5.1f}%   胜率(盈利): {result['win_prob']}%   亏钱概率: {result['lose_prob']}%   打平: {result['flat_prob']}% │
└─────────────────────────────────────────────────────────────┘""")

# 对比总结
print("""
╔══════════════════════════════════════════════════════════════╗
║                    持仓组合对比                              ║
╠══════════════════════════════════════════════════════════════╣
║                      拓荆科技        沐曦股份                 ║
╠══════════════════════════════════════════════════════════════╣""")

print(f"║  确定性    │      ★★★★☆          ★★★☆☆                ║")
print(f"║  弹性空间  │      ★★★☆☆          ★★★★☆                ║")
print(f"║  下行保护  │      ★★★★☆          ★★☆☆☆                ║")
print(f"║  估值安全  │      ★★★☆☆          ★★☆☆☆                ║")
print(f"╚══════════════════════════════════════════════════════════╝")

print("""
📌 拓荆科技: 110亿在手订单=最强确定性，Q2营收大概率16-19亿。
   胜率高但弹性有限（已是明牌），627的成本位置很好。

📌 沐曦股份: C600量产+扭亏拐点=弹性最大但确定性最低。
   713买入在超跌反弹中段，Q2能否扭亏是关键变量。
   胜率较低但一旦成功回报可观。

⚠️ 核心建议:
   拓荆 → 627成本好，Q2大概率安全，拿到8/21财报
   沐曦 → 713成本还行，但不确定性大，建议财报前设好止损(665下方)
""")

# 导出JSON给HTML
export = {
    "pjtd": {"data": pjtd, "result": {k: str(v) if isinstance(v, float) else v for k, v in td.items()}},
    "pmx": {"data": pmx, "result": {k: str(v) if isinstance(v, float) else v for k, v in mx.items()}},
}
# 处理scenarios中的numpy类型
for stock_result in [td, mx]:
    for s in stock_result["scenarios"]:
        for k in s:
            if isinstance(s[k], list):
                s[k] = [round(x, 1) if isinstance(x, float) else x for x in s[k]]

with open("earnings_data.json", "w", encoding="utf-8") as f:
    json.dump(export, f, ensure_ascii=False, indent=2, default=str)

print("✅ 数据已导出到 earnings_data.json")
