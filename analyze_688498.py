#!/usr/bin/env python3
"""源杰科技(688498) 量价背离专项分析"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from fetch_stock_kline import fetch_kline, compute_kdj, compute_macd

df = fetch_kline("688498", "daily", "20250601", "20260825")
df = compute_kdj(df)
df = compute_macd(df)
df = df.reset_index(drop=True)
df["date"] = pd.to_datetime(df["date"])

close = df["close"]
vol = df["volume"]
last = df.iloc[-1]
n = len(df)

print(f"数据: {n} 条  {df['date'].iloc[0].date()} ~ {df['date'].iloc[-1].date()}")
print(f"最新收盘: {last['close']:.2f}  ({last['date'].date()})")

# ── 1. 量价基础: 近期价格 vs 成交量 ──────────────────────
print(f"\n{'='*64}")
print(f"  1️⃣ 近期量价对照 (近15日)")
print(f"{'='*64}")
print(f"  {'日期':<12} {'收盘':>8} {'涨跌%':>7} {'量(万手)':>9} {'量比MA5':>8}")
vma5 = vol.rolling(5).mean()
vma20 = vol.rolling(20).mean()
for i in range(max(0, n - 15), n):
    r = df.iloc[i]
    pct = (r["close"] / df.iloc[i - 1]["close"] - 1) * 100 if i > 0 else 0
    qb = r["volume"] / vma5.iloc[i] if not np.isnan(vma5.iloc[i]) else 1
    print(f"  {r['date'].strftime('%m-%d'):<12} {r['close']:>8.2f} {pct:>6.2f}% {r['volume']/1e4:>9.1f} {qb:>8.2f}")

# ── 2. 量价背离检测 ─────────────────────────────────────
print(f"\n{'='*64}")
print(f"  2️⃣ 量价背离检测")
print(f"{'='*64}")

# 近60日找价格高点序列
win = 60
seg = df.iloc[-win:].reset_index(drop=True)
peaks = []
for i in range(3, len(seg) - 3):
    if seg["high"].iloc[i] == seg["high"].iloc[i - 3:i + 4].max():
        peaks.append(i)
peaks = [i for i in peaks if i >= 5]  # 过滤太靠近开头的

def find_major_highs(idx_list, min_gap=5):
    """取局部显著高点: 每 min_gap 内只保留最高的"""
    out = []
    for i in idx_list:
        if not out or i - out[-1] >= min_gap:
            out.append(i)
        else:
            if seg["close"].iloc[i] > seg["close"].iloc[out[-1]]:
                out[-1] = i
    return out

majors = find_major_highs(peaks)

print(f"\n  🔹 近期显著高点 (近{win}日, 前高→后高):")
for a, b in zip(majors, majors[1:]):
    pa, pb = seg["close"].iloc[a], seg["close"].iloc[b]
    va, vb = seg["volume"].iloc[a], seg["volume"].iloc[b]
    da, db = seg["date"].iloc[a], seg["date"].iloc[b]
    price_dir = "新高" if pb > pa else "回落"
    vol_cmp = vb / va
    tag = ""
    if pb > pa and vol_cmp < 0.8:
        tag = " ⚠️ 顶背离: 价新高 + 量萎缩"
    elif pb > pa and vol_cmp > 1.2:
        tag = " ✅ 量价齐升, 健康"
    elif pb <= pa and vol_cmp > 1.3:
        tag = " ⚠️ 放量下跌, 抛压重"
    print(f"    {da.strftime('%m-%d')}: {pa:>7.2f} (量{va/1e4:>6.1f}万手)")
    print(f"    {db.strftime('%m-%d')}: {pb:>7.2f} (量{vb/1e4:>6.1f}万手)   量能比 {vol_cmp:.2f}{tag}")

# 近10日 vs 前10日 成交量对比
v_recent = vol.iloc[-10:].mean()
v_prev = vol.iloc[-30:-10].mean()
print(f"\n  🔹 量能趋势: 近10日均量 {v_recent/1e4:.0f}万手 vs 前20日均量 {v_prev/1e4:.0f}万手")
print(f"     比值 {v_recent/v_prev:.2f}  ({'缩量' if v_recent < v_prev else '放量'})")
print(f"     近10日价格变化: {close.iloc[-10]:.2f} → {close.iloc[-1]:.2f}  = {(close.iloc[-1]/close.iloc[-10]-1)*100:+.1f}%")

# OBV 趋势 vs 价格趋势
obv = (np.sign(close.diff()) * vol).fillna(0).cumsum()
obv_10ago = obv.iloc[-11]
obv_now = obv.iloc[-1]
print(f"\n  🔹 OBV(能量潮): 10日前 {obv_10ago/1e4:.0f}万手 → 现在 {obv_now/1e4:.0f}万手")
print(f"     OBV 变化 {np.sign(obv_now-obv_10ago)*1} ({'上升' if obv_now > obv_10ago else '下降'})")
print(f"     同期价格 {'上涨' if close.iloc[-1] > close.iloc[-11] else '下跌'} {(close.iloc[-1]/close.iloc[-11]-1)*100:+.1f}%")
if obv_now < obv_10ago and close.iloc[-1] > close.iloc[-11]:
    print("     ⚠️ 价涨量落: OBV 与价格方向背离 → 上涨缺资金承接")
elif obv_now > obv_10ago and close.iloc[-1] < close.iloc[-11]:
    print("     ⚠️ 价跌量增: OBV 上升但价格下跌 → 有资金低吸")

# ── 3. MACD 顶/底背离 ───────────────────────────────────
print(f"\n{'='*64}")
print(f"  3️⃣ MACD 背离检测")
print(f"{'='*64}")

seg2 = df.iloc[-80:].reset_index(drop=True)

# 找MACD柱(红柱高点/绿柱低点)的极值
def find_extrema(arr, order=2):
    out = []
    for i in range(order, len(arr) - order):
        win_slice = arr[i - order:i + order + 1]
        if arr[i] == win_slice.max() or arr[i] == win_slice.min():
            out.append(i)
    return out

def detect_divergence(price_col, macd_col, ext_type, label):
    """ext_type: 'top' 找价格高点处的MACD比较, 'bottom' 找低点"""
    found = []
    pts = find_extrema(price_col.values if False else price_col, 2)
    # 用局部极值点: 价格局部高点/低点
    extremes = []
    for i in range(2, len(price_col) - 2):
        w = price_col.iloc[i - 2:i + 3]
        if ext_type == "top" and price_col.iloc[i] == w.max():
            extremes.append(i)
        elif ext_type == "bottom" and price_col.iloc[i] == w.min():
            extremes.append(i)
    # 相邻两个同类型极值比较
    for a, b in zip(extremes, extremes[1:]):
        if b - a < 4:
            continue
        pa, pb = price_col.iloc[a], price_col.iloc[b]
        ma, mb = macd_col.iloc[a], macd_col.iloc[b]
        if ext_type == "top" and pb > pa and mb < ma:
            found.append((seg2["date"].iloc[a], pa, ma, seg2["date"].iloc[b], pb, mb))
        if ext_type == "bottom" and pb < pa and mb > ma:
            found.append((seg2["date"].iloc[a], pa, ma, seg2["date"].iloc[b], pb, mb))
    return found

diver = detect_divergence(seg2["close"], seg2["MACD"], "top", "顶")
if diver:
    for d in diver:
        print(f"  ⚠️ MACD 顶背离: {d[0].strftime('%m-%d')} 价{d[1]:.1f}(柱{d[2]:.1f})"
              f" → {d[3].strftime('%m-%d')} 价{d[4]:.1f}(柱{d[5]:.1f})  价格新高但动能减弱")
else:
    print(f"  — 近80日未检出 MACD 顶背离")

diver_b = detect_divergence(seg2["close"], seg2["MACD"], "bottom", "底")
if diver_b:
    for d in diver_b:
        print(f"  🟢 MACD 底背离: {d[0].strftime('%m-%d')} 价{d[1]:.1f}(柱{d[2]:.1f})"
              f" → {d[3].strftime('%m-%d')} 价{d[4]:.1f}(柱{d[5]:.1f})  价格新低但动能衰竭")
else:
    print(f"  — 近80日未检出 MACD 底背离")

# ── 4. 其他关键位 ───────────────────────────────────────
print(f"\n{'='*64}")
print(f"  4️⃣ 位置与指标")
print(f"{'='*64}")
for w in [5, 10, 20, 60]:
    ma = close.rolling(w).mean().iloc[-1]
    pos = "上方" if last["close"] > ma else "下方"
    print(f"  MA{w}: {ma:.1f}  股价在{pos}")

peak, peak_idx = close.max(), close.idxmax()
print(f"  区间最高: {peak:.2f} ({df['date'].iloc[peak_idx].date()})  距高点 {(last['close']-peak)/peak*100:+.1f}%")
print(f"  KDJ: K={last['K']:.1f} D={last['D']:.1f} J={last['J']:.1f}")
print(f"  MACD: DIF={last['DIF']:.2f} DEA={last['DEA']:.2f} 柱={last['MACD']:.2f}")
print(f"  换手参考: 近5日均量 {vol.iloc[-5:].mean()/1e4:.0f}万手 vs 近60日均量 {vol.iloc[-60:].mean()/1e4:.0f}万手")

# ── 汇总 ────────────────────────────────────────────────
print(f"\n{'='*64}")
print(f"  📋 量价背离结论")
print(f"{'='*64}")
