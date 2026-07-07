#!/usr/bin/env python3
"""拉取 A 股 K 线数据，计算 KDJ / MACD，输出 CSV 并打印信号摘要

默认分析江波龙(301308)"""

import argparse
from datetime import datetime

import numpy as np
import pandas as pd

# ── 数据源 ──────────────────────────────────────────────
# 东方财富 akshare 接口在此环境被墙，改用新浪源
try:
    import akshare as ak
    _HAS_AK = True
except ImportError:
    _HAS_AK = False


def fetch_kline(symbol: str, period: str = "daily",
                start: str = "20250101", end: str = None) -> pd.DataFrame:
    """拉取日线（新浪源只支持日线）"""
    if end is None:
        end = datetime.now().strftime("%Y%m%d")

    # 新浪格式: sz301308 / sh600519
    code = symbol.zfill(6)
    prefix = "sh" if code.startswith(("6", "9")) else "sz"
    full = f"{prefix}{code}"

    df = ak.stock_zh_a_daily(symbol=full, start_date=start, end_date=end, adjust="qfq")
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ── KDJ ─────────────────────────────────────────────────
def compute_kdj(df: pd.DataFrame, n: int = 9) -> pd.DataFrame:
    """计算 KDJ(9,3,3)，直接在 df 上增加 K/D/J 三列"""
    low_n = df["low"].rolling(window=n, min_periods=1).min()
    high_n = df["high"].rolling(window=n, min_periods=1).max()

    rsv = (df["close"] - low_n) / (high_n - low_n) * 100
    rsv = rsv.fillna(50)  # 首日无法除时取中性值

    k = np.zeros(len(df))
    d = np.zeros(len(df))
    for i in range(len(df)):
        if i == 0:
            k[i] = 50.0
            d[i] = 50.0
        else:
            k[i] = 2 / 3 * k[i - 1] + 1 / 3 * rsv.iloc[i]
            d[i] = 2 / 3 * d[i - 1] + 1 / 3 * k[i]
    j = 3 * k - 2 * d

    df["K"] = np.round(k, 2)
    df["D"] = np.round(d, 2)
    df["J"] = np.round(j, 2)
    return df


# ── MACD ────────────────────────────────────────────────
def compute_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26,
                 signal: int = 9) -> pd.DataFrame:
    """计算 MACD(12,26,9)，直接在 df 上增加 DIF/DEA/MACD 三列"""
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_bar = 2 * (dif - dea)

    df["DIF"] = np.round(dif, 3)
    df["DEA"] = np.round(dea, 3)
    df["MACD"] = np.round(macd_bar, 3)
    return df


# ── 信号分析 ────────────────────────────────────────────
def print_signals(df: pd.DataFrame) -> None:
    """打印最近行情的 KDJ/MACD 信号"""
    last = df.iloc[-1]
    prev = df.iloc[-2]
    close = last["close"]

    print(f"\n{'='*60}")
    print(f"  📊 江波龙 (301308)  最新: {last['date']}  收盘: {close}")
    print(f"{'='*60}")

    # ── KDJ ──
    k_val, d_val, j_val = last["K"], last["D"], last["J"]
    print(f"\n🔵 KDJ (9,3,3)")
    print(f"   K={k_val:.2f}   D={d_val:.2f}   J={j_val:.2f}")

    if j_val > 100:
        print("   ⚠️  J > 100  超买区域，短线注意回调风险")
    elif j_val < 0:
        print("   ⚠️  J < 0   超卖区域，短线可能有反弹")
    elif j_val > 80:
        print("   📌 J > 80  偏强，但尚未极端")
    elif j_val < 20:
        print("   📌 J < 20  偏弱，但尚未极端")
    else:
        print("   — 正常区间")

    if prev["K"] <= prev["D"] and last["K"] > last["D"]:
        print("   🟢 KDJ 金叉! (K 上穿 D)")
    elif prev["K"] >= prev["D"] and last["K"] < last["D"]:
        print("   🔴 KDJ 死叉! (K 下穿 D)")

    # ── MACD ──
    dif_v, dea_v, bar = last["DIF"], last["DEA"], last["MACD"]
    print(f"\n🟠 MACD (12,26,9)")
    print(f"   DIF={dif_v:.3f}   DEA={dea_v:.3f}   柱={bar:.3f}")

    if dif_v > 0 > dea_v:
        print("   📌 DIF 已上零轴，多头占优；DEA 尚在零轴下方")
    elif dif_v > 0 and dea_v > 0:
        print("   🟢 DIF/DEA 均在零轴上方，多头主导")
    elif dif_v < 0 and dea_v < 0:
        print("   🔴 DIF/DEA 均在零轴下方，空头主导")
    elif dif_v < 0 < dea_v:
        print("   📌 DIF 已下零轴，空头占优；DEA 尚在零轴上方")

    if bar > 0:
        print(f"   红柱({'扩张' if bar > prev['MACD'] else '收缩'})")
    else:
        print(f"   绿柱({'扩张' if bar < prev['MACD'] else '收缩'})")

    if prev["DIF"] <= prev["DEA"] and last["DIF"] > last["DEA"]:
        print("   🟢 MACD 金叉! (DIF 上穿 DEA)")
    elif prev["DIF"] >= prev["DEA"] and last["DIF"] < last["DEA"]:
        print("   🔴 MACD 死叉! (DIF 下穿 DEA)")


# ── CLI ─────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="拉取 A 股 K 线数据，计算 KDJ/MACD，默认分析江波龙(301308)")
    parser.add_argument("symbol", nargs="?", default="301308",
                        help="股票代码（默认 301308 江波龙）")
    parser.add_argument("-s", "--start", default="20250101")
    parser.add_argument("-e", "--end", default=None)
    parser.add_argument("-o", "--output", default=None,
                        help="输出 CSV 文件路径")
    parser.add_argument("--no-kdj", action="store_true",
                        help="不计算 KDJ")
    parser.add_argument("--no-macd", action="store_true",
                        help="不计算 MACD")
    parser.add_argument("--raw", action="store_true",
                        help="只拉数据不计算指标")
    args = parser.parse_args()

    # 拉取
    df = fetch_kline(args.symbol, "daily", args.start, args.end)
    print(f"✅ 拉取成功: {len(df)} 条  ({df['date'].iloc[0]} ~ {df['date'].iloc[-1]})")

    # 计算指标
    if not args.raw:
        if not args.no_kdj:
            df = compute_kdj(df)
        if not args.no_macd:
            df = compute_macd(df)

    # 保存
    if args.output:
        df.to_csv(args.output, index=False)
        print(f"📁 已保存到 {args.output}")

    # 打印尾部 + 信号
    show_cols = ["date", "close", "high", "low"]
    if "K" in df.columns:
        show_cols += ["K", "D", "J"]
    if "DIF" in df.columns:
        show_cols += ["DIF", "DEA", "MACD"]
    show_cols += ["volume"]

    print(f"\n{'  '.join(show_cols)}")
    print(df[show_cols].tail(10).to_string(index=False))

    # 信号摘要
    if not args.raw and "K" in df.columns and "DIF" in df.columns:
        print_signals(df)
    elif not args.raw:
        print("\n⚠️  部分指标未计算，无法输出信号")
