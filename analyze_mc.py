#!/usr/bin/env python3
"""技术面 + 蒙特卡洛概率预测(通用脚本)

用法:
    python analyze_mc.py 688072 拓荆科技
    python analyze_mc.py 688072 拓荆科技 --drift 0.02 --vol-window 60

说明:
    - 均线/KDJ/MACD/波动率: 纯公式计算, 无人工因素
    - 蒙特卡洛: 假设(漂移率、波动率窗口)通过参数控制, 默认中性漂移
    - 输出为文字报告; 若需图表请配合 chart_html.py
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_stock_kline import fetch_kline, compute_kdj, compute_macd


def main():
    parser = argparse.ArgumentParser(description="技术面 + 蒙特卡洛概率预测")
    parser.add_argument("code", help="股票代码, 如 688072")
    parser.add_argument("name", help="股票中文名, 如 拓荆科技")
    parser.add_argument("-s", "--start", default="20250801", help="开始日期 (默认 20250801)")
    parser.add_argument("-e", "--end", default=None, help="结束日期 (默认今天)")
    parser.add_argument("--drift", type=float, default=0.0,
                        help="蒙特卡洛年化漂移率 (默认 0=中性, 不假设涨跌)")
    parser.add_argument("--vol-window", type=int, default=120,
                        help="波动率统计窗口(交易日, 默认 120)")
    parser.add_argument("--paths", type=int, default=50000, help="模拟路径数 (默认 50000)")
    args = parser.parse_args()

    df = fetch_kline(args.code, "daily", args.start, args.end)
    df = compute_kdj(df)
    df = compute_macd(df)
    df = df.reset_index(drop=True)

    close = df["close"]
    last = df.iloc[-1]
    n = len(df)

    print(f"══════ {args.name} ({args.code}) 技术面 + 蒙特卡洛 ══════")
    print(f"数据: {n} 条  {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    print(f"最新收盘: {last['close']:.2f}  ({last['date']})")

    # ── 均线 ──
    for win in [5, 10, 20, 60]:
        ma = close.rolling(win).mean().iloc[-1]
        pos = "上方" if last["close"] > ma else "下方"
        print(f"  MA{win}: {ma:.1f}  股价在{pos}")

    # ── 区间统计 ──
    print(f"\n近20日最高: {close.iloc[-20:].max():.2f}  最低: {close.iloc[-20:].min():.2f}")
    print(f"近60日最高: {close.iloc[-60:].max():.2f}  最低: {close.iloc[-60:].min():.2f}")
    peak, peak_idx = close.max(), close.idxmax()
    print(f"区间最高: {peak:.2f} ({df['date'].iloc[peak_idx]})")
    print(f"距高点回撤: {(last['close']-peak)/peak*100:.1f}%")

    # ── 指标 ──
    print(f"\nKDJ: K={last['K']:.1f} D={last['D']:.1f} J={last['J']:.1f}")
    print(f"MACD: DIF={last['DIF']:.1f} DEA={last['DEA']:.1f} 柱={last['MACD']:.1f}")

    # ── 波动率 ──
    ret = close.pct_change().dropna()
    for win, wname in [(20, "近1月"), (60, "近3月"), (120, "近半年")]:
        v = ret.iloc[-win:].std() * np.sqrt(252) * 100
        print(f"\n年化波动率({wname}): {v:.0f}%")

    # ── 蒙特卡洛 ──
    np.random.seed(42)
    S0 = last["close"]
    vol = ret.iloc[-args.vol_window:].std() * np.sqrt(252)
    drift = args.drift
    paths = args.paths
    horizons = {"1个月(21日)": 21, "3个月(63日)": 63, "6个月(126日)": 126}

    print(f"\n{'='*60}")
    print(f"  蒙特卡洛模拟 (漂移 {drift*100:+.0f}%/年, 波动率窗口 {args.vol_window}日, "
          f"年化波动 {vol*100:.0f}%, {paths:,} 条路径)")
    print(f"{'='*60}")

    for hname, days in horizons.items():
        z = np.random.standard_normal((paths, days))
        daily_vol = vol / np.sqrt(252)
        steps = (drift - 0.5 * daily_vol**2) + daily_vol * z
        log_ret = steps.sum(axis=1)
        future = S0 * np.exp(log_ret)
        up = (future > S0).mean() * 100
        p5, p25, p50, p75, p95 = np.percentile(future, [5, 25, 50, 75, 95])
        print(f"\n  【{hname}】上涨概率 {up:.1f}%")
        print(f"    分位价: P5={p5:.0f}  P25={p25:.0f}  P50={p50:.0f}  P75={p75:.0f}  P95={p95:.0f}")
        print(f"    (P5 为最坏 5% 情形的价位, 可作参考止损区; 区间宽度反映波动)")
    print("\n⚠️  蒙特卡洛是基于历史波动率的统计模拟, 不含基本面信息, 仅供参考")


if __name__ == "__main__":
    main()
