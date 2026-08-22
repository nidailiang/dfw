#!/usr/bin/env python3
"""按 B1 策略定稿 v1.0 检查个股: python b1_check.py <code> <name> [k_atr]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from fetch_stock_kline import fetch_kline, compute_kdj, compute_macd

CODE = sys.argv[1]
NAME = sys.argv[2] if len(sys.argv) > 2 else CODE
K_ATR = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0

df = fetch_kline(CODE, start="20240101")
df = compute_kdj(df)
df = compute_macd(df)

ema1 = df["close"].ewm(span=10, adjust=False).mean()
df["白线"] = ema1.ewm(span=10, adjust=False).mean()
for n in [14, 28, 57, 114]:
    df[f"MA{n}"] = df["close"].rolling(n).mean()
df["黄线"] = (df["MA14"] + df["MA28"] + df["MA57"] + df["MA114"]) / 4

prev_close = df["close"].shift(1)
df["TR"] = pd.concat([df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()], axis=1).max(axis=1)
df["ATR14"] = df["TR"].rolling(14).mean()
df["ATR14%"] = df["ATR14"] / df["close"] * 100

df["涨跌幅"] = df["close"].pct_change() * 100
df["振幅"] = (df["high"] - df["low"]) / df["close"].shift(1) * 100
df["阳线"] = df["close"] > df["open"]
df["阴线"] = df["close"] < df["open"]
df["量比前日"] = df["volume"] / df["volume"].shift(1)
df["距黄线%"] = (df["close"] / df["黄线"] - 1) * 100

pct_limit = 0.2 if CODE.startswith(("300", "301", "688", "920")) else 0.1
df["前日一字跌停"] = (df["close"].shift(1) <= df["close"].shift(2) * (1 - pct_limit) * 1.005) & \
                     (df["close"].shift(1) >= df["close"].shift(2) * (1 - pct_limit) * 0.995)
df["倍量"] = (~df["前日一字跌停"]) & (df["量比前日"] > 1.8) & (df["涨跌幅"] > 2)

df["前3最大阳量"] = df["volume"].where(df["阳线"]).rolling(3).max().shift(1)
df["前15最大阳量"] = df["volume"].where(df["阳线"]).rolling(15).max().shift(1)
df["前3日有阳线"] = df["阳线"].shift(1).rolling(3).max().fillna(0) > 0
df["出1"] = df["前3日有阳线"] & df["阴线"] & (df["涨跌幅"] < -3) & \
            (df["volume"] > df["前3最大阳量"] * 1.5) & (df["volume"] > df["前15最大阳量"] * 1.1)
df["出2"] = df["前3日有阳线"] & df["阴线"] & (df["涨跌幅"] < -3) & \
            (df["volume"] <= df["前3最大阳量"] * 1.5) & (df["volume"] > df["前15最大阳量"] * 1.2)
df["放量阴线"] = (df["出1"] | df["出2"]) & (df["距黄线%"] > 20)

print("=" * 72)
print(f"  {CODE} {NAME}  |  最新交易日 {df['date'].iloc[-1]} 收盘 {df['close'].iloc[-1]:.2f}")
print("=" * 72)

for i in range(len(df) - 2, len(df)):
    r = df.iloc[i]
    jmin5 = df["J"].iloc[max(0, i-4):i+1].min()
    c3 = (r["J"] <= 16) or (jmin5 <= 13.05 and r["J"] <= 40)
    print(f"  [{r['date']}] 收{r['close']:.2f} 涨跌{r['涨跌幅']:+.2f}% 振幅{r['振幅']:.1f}% 量比{r['量比前日']:.2f} "
          f"J={r['J']:.1f}(5日低{jmin5:.1f}){'🟢买点' if c3 else ''}")
    print(f"      白线{r['白线']:.2f} 黄线{r['黄线']:.2f} {'🟢白>黄' if r['白线']>r['黄线'] else '🔴白<黄'} 距黄线{r['距黄线%']:+.1f}% "
          f"MACD柱{r['MACD']:.2f} ATR14%={r['ATR14%']:.2f}% MA20={df['close'].rolling(20).mean().iloc[i]:.2f} MA60={df['close'].rolling(60).mean().iloc[i]:.2f}")

r = df.iloc[-1]
i = len(df) - 1
jmin5 = df["J"].iloc[-5:].min()
recent30 = df.iloc[-30:-1]
recent10 = df.iloc[-10:-1]
c2 = (-4 <= r["涨跌幅"] <= 3) and r["振幅"] <= 7
c3 = (r["J"] <= 16) or (jmin5 <= 13.05 and r["J"] <= 40)
c4 = r["白线"] > r["黄线"]
c5 = r["距黄线%"] >= -5
c6 = recent30["倍量"].any()
c7 = not recent10["放量阴线"].any()
checks = [
    ("2 窄幅震荡", c2, f"涨跌{r['涨跌幅']:+.2f}% 振幅{r['振幅']:.1f}%"),
    ("3 KDJ买点", c3, f"J={r['J']:.1f} 5日低={jmin5:.1f}"),
    ("4 白线>黄线", c4, f"{r['白线']:.2f} vs {r['黄线']:.2f}"),
    ("5 距黄线≥-5%", c5, f"{r['距黄线%']:+.1f}%"),
    ("6 30日倍量", c6, f"近30日{int(recent30['倍量'].sum())}根"),
    ("7 10日无出货", c7, f"近10日出货{int(recent10['放量阴线'].sum())}根"),
]
ok = True
for name, ok_, detail in checks:
    print(f"  {'✅' if ok_ else '❌'} {name}: {detail}")
    ok = ok and ok_

# 止损
r15 = df.tail(15)
ref_low = min(r15["low"].min(), df["low"].iloc[-1])
stop_pct = max(1.0, K_ATR * r["ATR14%"])
stop = ref_low * (1 - stop_pct / 100)
print(f"\n  参考低点(15日最低)={ref_low:.2f} ATR14%={r['ATR14%']:.2f}% k={K_ATR}")
print(f"  止损位 = {ref_low:.2f}×({1-stop_pct/100:.3f}) = {stop:.2f}")

# 20日明细
print("\n  最近20日: 日期 收盘 涨跌% 量比 J 距黄线% 倍/出")
for _, r2 in df.tail(20).iterrows():
    print(f"  {r2['date']} {r2['close']:9.2f} {r2['涨跌幅']:+6.2f}% {r2['量比前日']:5.2f} {r2['J']:7.1f} {r2['距黄线%']:+7.1f}% "
          f"{'倍' if r2['倍量'] else '·'}{'出' if r2['放量阴线'] else '·'}")
