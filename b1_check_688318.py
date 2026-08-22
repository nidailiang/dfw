#!/usr/bin/env python3
"""按 B1 策略定稿 v1.0 检查个股: 688318 财富趋势 (用户买入价 75.63)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from fetch_stock_kline import fetch_kline, compute_kdj, compute_macd

CODE = "688318"
BUY_PRICE = 75.63
K_ATR = 2.0  # 止损系数 k

df = fetch_kline(CODE, start="20240101")
df = compute_kdj(df)
df = compute_macd(df)

# ── 白线/黄线 (通达信: ewm adjust=False 等价) ──
ema1 = df["close"].ewm(span=10, adjust=False).mean()
df["白线"] = ema1.ewm(span=10, adjust=False).mean()
for n in [14, 28, 57, 114]:
    df[f"MA{n}"] = df["close"].rolling(n).mean()
df["黄线"] = (df["MA14"] + df["MA28"] + df["MA57"] + df["MA114"]) / 4

# ── ATR14 ──
prev_close = df["close"].shift(1)
df["TR"] = pd.concat([df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()], axis=1).max(axis=1)
df["ATR14"] = df["TR"].rolling(14).mean()
df["ATR14%"] = df["ATR14"] / df["close"] * 100

# ── 均量 ──
df["MAV5"] = df["volume"].rolling(5).mean()
df["MAV10"] = df["volume"].rolling(10).mean()

# ── 辅助序列 ──
df["涨跌幅"] = df["close"].pct_change() * 100
df["振幅"] = (df["high"] - df["low"]) / df["close"].shift(1) * 100
df["阳线"] = df["close"] > df["open"]
df["阴线"] = df["close"] < df["open"]
df["量比前日"] = df["volume"] / df["volume"].shift(1)
df["距黄线%"] = (df["close"] / df["黄线"] - 1) * 100

# ── 倍量条件: 量>前日×1.8 且 涨>2% 且 前日非一字跌停 ──
pct_limit = 0.2  # 科创板20%
df["前日一字跌停"] = (df["close"].shift(1) <= df["close"].shift(2) * (1 - pct_limit) * 1.005) & \
                     (df["close"].shift(1) >= df["close"].shift(2) * (1 - pct_limit) * 0.995)
df["倍量"] = (~df["前日一字跌停"]) & (df["量比前日"] > 1.8) & (df["涨跌幅"] > 2)

# ── 出货形态 出1/出2 (高位才计入: 距黄线>20%) ──
df["前3最大阳量"] = df["volume"].where(df["阳线"]).rolling(3).max().shift(1)
df["前15最大阳量"] = df["volume"].where(df["阳线"]).rolling(15).max().shift(1)
df["前3日有阳线"] = df["阳线"].shift(1).rolling(3).max().fillna(0) > 0
df["出1"] = df["前3日有阳线"] & df["阴线"] & (df["涨跌幅"] < -3) & \
            (df["volume"] > df["前3最大阳量"] * 1.5) & (df["volume"] > df["前15最大阳量"] * 1.1)
df["出2"] = df["前3日有阳线"] & df["阴线"] & (df["涨跌幅"] < -3) & \
            (df["volume"] <= df["前3最大阳量"] * 1.5) & (df["volume"] > df["前15最大阳量"] * 1.2)
df["放量阴线"] = (df["出1"] | df["出2"]) & (df["距黄线%"] > 20)

# ── N型结构粗判: 近40日 一波上涨≥15% → 回调≥30%不破前低 → 再上涨 ──
def n_type_ok(row_idx):
    win = df.iloc[max(0, row_idx-45):row_idx+1]
    if len(win) < 20:
        return None
    lows = win["low"]
    seg2 = win.tail(15)  # 最近15日(回调段+新低确认段)
    seg1 = win.iloc[:-15]
    if len(seg1) < 5:
        return None
    up_lo = seg1["low"].min()
    up_hi = seg1["high"].max()
    if up_hi / up_lo - 1 < 0.15:
        return None
    pull_lo = seg2["low"].min()
    if pull_lo >= up_lo * 0.995 and pull_lo > up_lo * 0.85:
        return True
    return False

# ── 输出: 最近3日检查 ──
print("=" * 72)
print(f"  {CODE} 财富趋势  | 买入价 {BUY_PRICE}  |  最新交易日 {df['date'].iloc[-1]}")
print("=" * 72)

for i in range(len(df) - 3, len(df)):
    r = df.iloc[i]
    date = r["date"]
    j = r["J"]
    jmin5 = df["J"].iloc[max(0, i-4):i+1].min()
    c3 = (j <= 16) or (jmin5 <= 13.05 and j <= 40)
    c5 = r["距黄线%"] >= -5
    print(f"\n【{date}】 收盘 {r['close']:.2f}  涨跌 {r['涨跌幅']:+.2f}%  振幅 {r['振幅']:.1f}%  量比前日 {r['量比前日']:.2f}")
    print(f"  白线 {r['白线']:.2f}  黄线 {r['黄线']:.2f}  {'🟢白>黄' if r['白线']>r['黄线'] else '🔴白<黄'}   距黄线 {r['距黄线%']:+.1f}%")
    print(f"  KDJ: K={r['K']:.1f} D={r['D']:.1f} J={r['J']:.1f}  (5日J最低 {jmin5:.1f})  {'🟢买点档' if c3 else '—'}")
    print(f"  MACD: DIF={r['DIF']:.2f} DEA={r['DEA']:.2f} 柱={r['MACD']:.2f}  {'红' if r['MACD']>0 else '绿'}柱")
    print(f"  ATR14={r['ATR14']:.2f} ({r['ATR14%']:.2f}%)   止损位=参考低点-{K_ATR}×ATR14")

# ── B1 条件逐项 (最新日) ──
r = df.iloc[-1]
i = len(df) - 1
jmin5 = df["J"].iloc[-5:].min()
recent30 = df.iloc[-30:-1]  # 不含今日(REF语义)
recent10 = df.iloc[-10:-1]

c1 = True  # 板块黑名单: 软件属"软件开发"不在黑名单, 人工核对
c2 = (-4 <= r["涨跌幅"] <= 3) and r["振幅"] <= 7
c3 = (r["J"] <= 16) or (jmin5 <= 13.05 and r["J"] <= 40)
c4 = r["白线"] > r["黄线"]
c5 = r["距黄线%"] >= -5
c6 = recent30["倍量"].any()
c7 = not recent10["放量阴线"].any()

print("\n" + "=" * 72)
print("  B1 七条件逐项检查（最新日）")
print("=" * 72)
checks = [
    ("1 非黑名单板块", c1, "软件开发不在黑名单"),
    ("2 当日窄幅震荡", c2, f"涨跌{r['涨跌幅']:+.2f}% 振幅{r['振幅']:.1f}% (需[-4,+3] 振幅≤7)"),
    ("3 KDJ买点", c3, f"J={r['J']:.1f} 5日最低={jmin5:.1f}"),
    ("4 白线>黄线", c4, f"{r['白线']:.2f} vs {r['黄线']:.2f}"),
    ("5 距黄线≥-5%", c5, f"{r['距黄线%']:+.1f}%"),
    ("6 30日有倍量", c6, f"近30日倍量天数={int(recent30['倍量'].sum())}"),
    ("7 10日无出货", c7, f"近10日出货天数={int(recent10['放量阴线'].sum())}"),
]
for name, ok, detail in checks:
    print(f"  {'✅' if ok else '❌'} {name}: {detail}")
print(f"  → B1买点条件 {'全部满足 🟢' if all(c[1] for c in checks) else '未全满足 🔴'}")

# ── 止损位 ──
print("\n" + "=" * 72)
print("  止损位（ATR自适应）")
print("=" * 72)
r15 = df.tail(15)
ref_low = min(r15["low"].min(), df["low"].iloc[-1])  # 前低/当日低点
stop = ref_low - max(1, K_ATR * r["ATR14%"])
print(f"  参考低点(15日最低)={ref_low:.2f}   ATR14%={r['ATR14%']:.2f}%")
print(f"  止损位 = {ref_low:.2f} - max(1%, {K_ATR}×{r['ATR14%']:.2f}%) = {stop:.2f}")
print(f"  买入价 {BUY_PRICE} 距止损 {(BUY_PRICE/stop-1)*100:.1f}%")

# ── 最近20日明细 ──
print("\n" + "=" * 72)
print("  最近20日明细（日期 收盘 涨跌% 振幅% 量比 J 距黄线% 倍量 出货）")
print("=" * 72)
for _, r2 in df.tail(20).iterrows():
    print(f"  {r2['date']} {r2['close']:8.2f} {r2['涨跌幅']:+.2f}% {r2['振幅']:5.1f}% "
          f"{r2['量比前日']:4.2f} {r2['J']:6.1f} {r2['距黄线%']:+6.1f}% "
          f"{'倍' if r2['倍量'] else '·'} {'出' if r2['放量阴线'] else '·'}")
