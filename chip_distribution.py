#!/usr/bin/env python3
"""筹码分布计算 —— 基于换手率衰减的移动筹码算法

参考: 陈浩《筹码分布》+ 指南针核心逻辑
用法:
    python chip_distribution.py 301308       # 江波龙最新筹码分布
    python chip_distribution.py 688525 -d 120  # 近120天
"""

import argparse
import sys
import os
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_stock_kline import fetch_kline, compute_kdj, compute_macd

plt.rcParams["font.family"] = "WenQuanYi Zen Hei"
plt.rcParams["axes.unicode_minus"] = False

# 配色 (A股红涨绿跌)
COLOR_UP = "#e83929"
COLOR_DOWN = "#009944"
COLOR_BG = "#121212"
COLOR_GRID = "#2a2a2a"
COLOR_TEXT = "#cccccc"


def compute_chip_distribution(df: pd.DataFrame, bins: int = 200,
                               decay_coef: float = 0.85) -> dict:
    """
    筹码分布核心算法

    参数:
        df: 包含 open/high/low/close/volume 的 DataFrame (按日期升序)
        bins: 价格分档数
        decay_coef: 衰减系数 (0~1), 越大衰减越慢, 筹码越"顽固"

    返回:
        {prices, chips, peak_price, profit_ratio, avg_cost, ...}
    """
    n = len(df)
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    volume = df["volume"].values
    date = df["date"].values

    # ── 价格区间 ──
    price_min = np.min(low)
    price_max = np.max(high)
    price_range = np.linspace(price_min, price_max, bins)
    bin_width = price_range[1] - price_range[0]

    # ── 累计筹码数组 ──
    total_chips = np.zeros(bins)

    # ── 获取换手率(如果有) ──
    # akshare 日线数据不一定有换手率，没有就估算
    if "turnover" in df.columns:
        turnover = df["turnover"].values / 100.0  # 百分比转小数
    else:
        # 用成交量/流通股本估算 (流通股本取一个常数)
        # 粗略估算: 日均换手 ~3-5%
        # 这里用成交量相对变化来近似
        avg_vol = np.mean(volume)
        turnover = np.clip(volume / (avg_vol * 30), 0.005, 0.15)

    # ── 逐日累积 ──
    for i in range(n):
        day_vol = volume[i]
        day_high = high[i]
        day_low = low[i]
        day_close = close[i]
        day_turnover = turnover[i]

        if day_vol <= 0 or day_high <= day_low:
            continue

        # 1) 衰减旧筹码
        #    换手率越高 → 旧筹码被换走的比例越大
        transfer_rate = min(day_turnover * decay_coef, 0.95)
        total_chips *= (1 - transfer_rate)

        # 2) 当日筹码分布 (三角形分布, 峰值在收盘价)
        day_chips = np.zeros(bins)

        for j in range(bins):
            price_j = price_range[j]
            if price_j < day_low or price_j > day_high:
                continue

            # 三角形分布: 收盘价处最高, 向高低点线性递减
            if price_j <= day_close:
                dist_to_peak = (day_close - price_j) / max(day_close - day_low, 0.001)
            else:
                dist_to_peak = (price_j - day_close) / max(day_high - day_close, 0.001)

            weight = max(0, 1.0 - dist_to_peak)
            day_chips[j] = weight

        # 归一化
        day_sum = np.sum(day_chips)
        if day_sum > 0:
            day_chips = day_chips / day_sum * day_vol

        # 3) 累加
        total_chips += day_chips

    # ── 找到筹码峰 ──
    # 用滑动窗口找局部最大值
    window = max(3, bins // 20)
    peak_indices = []
    for i in range(window, bins - window):
        if total_chips[i] == np.max(total_chips[i - window:i + window + 1]):
            if total_chips[i] > np.max(total_chips) * 0.1:  # 过滤小峰
                peak_indices.append(i)

    peaks = sorted(peak_indices, key=lambda i: total_chips[i], reverse=True)
    peak_price = price_range[peaks[0]] if peaks else day_close

    # ── 获利盘比例 ──
    latest_close = close[-1]
    profit_mask = price_range <= latest_close
    profit_chips = np.sum(total_chips[profit_mask])
    total = np.sum(total_chips)
    profit_ratio = profit_chips / total * 100 if total > 0 else 50

    # ── 平均成本 ──
    if total > 0:
        avg_cost = np.sum(price_range * total_chips) / total
    else:
        avg_cost = latest_close

    return {
        "prices": price_range.tolist(),
        "chips": (total_chips / np.max(total_chips) * 100).tolist(),  # 归一化到 0-100
        "raw_chips": total_chips.tolist(),
        "peak_price": round(float(peak_price), 2),
        "profit_ratio": round(float(profit_ratio), 1),
        "avg_cost": round(float(avg_cost), 2),
        "latest_close": float(latest_close),
        "all_peaks": [round(float(price_range[p]), 2) for p in peaks[:5]],
    }


def draw_chip_chart(df: pd.DataFrame, chip_result: dict, symbol: str,
                    save_path: str = None, dpi: int = 150):
    """绘制带筹码分布的主图"""
    n = len(df)

    # 计算指标
    df = compute_kdj(df)
    df = compute_macd(df)

    # 自定均线
    df["ema_double"] = df["close"].ewm(span=10, adjust=False).mean().ewm(span=10, adjust=False).mean()
    df["ma_avg"] = (
        df["close"].rolling(14).mean() +
        df["close"].rolling(28).mean() +
        df["close"].rolling(57).mean() +
        df["close"].rolling(114).mean()
    ) / 4

    up_mask = df["close"] >= df["open"]
    down_mask = df["close"] < df["open"]

    # ── 画布: K线 + Vol + MACD + KDJ, 主图右侧留筹码区 ──
    fig = plt.figure(figsize=(18, 10), facecolor=COLOR_BG)
    gs = fig.add_gridspec(4, 2, height_ratios=[4, 1.3, 1.5, 1.5],
                          width_ratios=[4, 1], hspace=0.05, wspace=0.02,
                          left=0.02, right=0.98, top=0.96, bottom=0.03)

    ax_kline = fig.add_subplot(gs[0, 0])
    ax_chip = fig.add_subplot(gs[0, 1])  # 不 sharey，手动同步范围
    ax_vol = fig.add_subplot(gs[1, 0], sharex=ax_kline)
    ax_macd = fig.add_subplot(gs[2, 0], sharex=ax_kline)
    ax_kdj = fig.add_subplot(gs[3, 0], sharex=ax_kline)

    for ax in [ax_kline, ax_vol, ax_macd, ax_kdj, ax_chip]:
        ax.set_facecolor(COLOR_BG)
        if ax != ax_chip:
            ax.tick_params(colors=COLOR_TEXT, labelsize=7)
        else:
            ax.tick_params(colors=COLOR_TEXT, labelsize=7, left=False, right=False)
        ax.grid(True, color=COLOR_GRID, linewidth=0.5, alpha=0.6)

    # ━━ 面板 0: K线 ━━
    body_width = 0.6
    for i in range(n):
        op, hi, lo, cl = df["open"].iloc[i], df["high"].iloc[i], df["low"].iloc[i], df["close"].iloc[i]
        color = COLOR_UP if cl >= op else COLOR_DOWN
        ax_kline.plot([i, i], [lo, hi], color=color, linewidth=0.8)
        body_h = max(abs(cl - op), 0.001)
        rect = Rectangle((i - body_width / 2, min(op, cl)), body_width, body_h,
                         facecolor=color, edgecolor=color, linewidth=0.5)
        ax_kline.add_patch(rect)

    # 均线
    ax_kline.plot(range(n), df["ema_double"], color="#ffffff", linewidth=1.0, label="EMA(EMA(C,10),10)")
    ax_kline.plot(range(n), df["ma_avg"], color="#ffcc00", linewidth=1.0, label="(MA14+28+57+114)/4")
    ax_kline.legend(loc="upper left", fontsize=7, facecolor=COLOR_BG, edgecolor=COLOR_GRID, labelcolor=COLOR_TEXT)

    # ━━ 面板 0 右侧: 筹码分布 ━━
    prices = np.array(chip_result["prices"])
    chips = np.array(chip_result["chips"])
    peak_price = chip_result["peak_price"]
    avg_cost = chip_result["avg_cost"]
    profit_ratio = chip_result["profit_ratio"]
    latest_close = chip_result["latest_close"]

    # 筹码柱状图 (水平方向)
    ax_chip.fill_betweenx(prices, 0, chips, alpha=0.7, color="#4488cc", linewidth=0)
    ax_chip.fill_betweenx(prices, 0, chips, alpha=0.4, color="#88bbee", linewidth=0)

    # 获利/套牢分界线 (当前价)
    ax_chip.axhline(y=latest_close, color="#ffffff", linewidth=0.8, linestyle="--", alpha=0.6)

    # 筹码峰标记
    ax_chip.axhline(y=peak_price, color="#ffcc00", linewidth=0.8, linestyle=":", alpha=0.7)
    ax_chip.text(95, peak_price, f" 峰{peak_price:.1f}", color="#ffcc00", fontsize=7, va="center")

    # 平均成本
    ax_chip.axhline(y=avg_cost, color="#ff6600", linewidth=0.6, linestyle=":", alpha=0.5)

    # 获利比例标注
    ax_chip.text(50, latest_close * 1.005, f"获利{profit_ratio:.0f}%", color="#ffffff", fontsize=8, va="bottom", ha="center")
    ax_chip.set_xlim(0, 110)

    # 筹码峰值线(垂直)
    ax_chip.text(5, peak_price, f"{peak_price:.1f}", color="#ffcc00", fontsize=7, va="bottom")

    # ━━ 面板 1: 成交量 ━━
    vol_up = np.where(up_mask, df["volume"].values, 0)
    vol_down = np.where(down_mask, df["volume"].values, 0)
    ax_vol.bar(range(n), vol_up, width=0.7, color=COLOR_UP, linewidth=0)
    ax_vol.bar(range(n), vol_down, width=0.7, color=COLOR_DOWN, linewidth=0)

    # 量均线
    vol_ma5 = df["volume"].rolling(5).mean()
    ax_vol.plot(range(n), vol_ma5, color="#ffffff", linewidth=0.6, alpha=0.5, label="VOL5")
    ax_vol.legend(loc="upper left", fontsize=6, facecolor=COLOR_BG, edgecolor=COLOR_GRID, labelcolor=COLOR_TEXT)
    ax_vol.yaxis.tick_right()

    # ━━ 面板 2: MACD ━━
    macd_vals = df["MACD"].values
    colors_macd = np.where(macd_vals >= 0, COLOR_UP, COLOR_DOWN)
    ax_macd.bar(range(n), macd_vals, width=0.7, color=colors_macd, linewidth=0)
    ax_macd.plot(range(n), df["DIF"], color="#ffffff", linewidth=0.8, label="DIF")
    ax_macd.plot(range(n), df["DEA"], color="#ffcc00", linewidth=0.8, label="DEA")
    ax_macd.axhline(y=0, color="#666666", linewidth=0.5)
    ax_macd.legend(loc="upper left", fontsize=7, facecolor=COLOR_BG, edgecolor=COLOR_GRID, labelcolor=COLOR_TEXT)
    ax_macd.yaxis.tick_right()

    # ━━ 面板 3: KDJ ━━
    ax_kdj.plot(range(n), df["K"], color="#ffffff", linewidth=0.8, label="K")
    ax_kdj.plot(range(n), df["D"], color="#ffcc00", linewidth=0.8, label="D")
    ax_kdj.plot(range(n), df["J"], color="#ff66cc", linewidth=0.8, label="J")
    for level, ls in [(20, "--"), (50, "-"), (80, "--")]:
        ax_kdj.axhline(y=level, color="#666666", linewidth=0.5, linestyle=ls, alpha=0.6)
    ax_kdj.set_ylim(-5, 105)
    ax_kdj.legend(loc="upper left", fontsize=7, facecolor=COLOR_BG, edgecolor=COLOR_GRID, labelcolor=COLOR_TEXT)
    ax_kdj.yaxis.tick_right()

    # ━━ X轴 ━━
    tick_step = max(n // 10, 1)
    tick_pos = list(range(0, n, tick_step))
    tick_labels = [str(df["date"].iloc[i])[:10] for i in tick_pos]
    ax_kdj.set_xticks(tick_pos)
    ax_kdj.set_xticklabels(tick_labels, rotation=30, fontsize=7, color=COLOR_TEXT)
    for ax in [ax_kline, ax_vol, ax_macd]:
        ax.tick_params(labelbottom=False)

    # ━━ 标题 ━━
    price = df["close"].iloc[-1]
    stock_names = {"301308": "江波龙", "688525": "佰维存储", "300308": "中际旭创"}
    name = stock_names.get(symbol, symbol)
    fig.suptitle(
        f"{name} ({symbol})  收盘:{price:.2f}  获利盘:{profit_ratio:.0f}%  "
        f"筹码峰:{peak_price:.1f}  平均成本:{avg_cost:.1f}",
        color=COLOR_TEXT, fontsize=12, fontweight="bold", y=0.98)

    # ━━ 保存 ━━
    if save_path is None:
        save_path = f"chip_{symbol}_{datetime.now().strftime('%Y%m%d')}.png"
    fig.savefig(save_path, dpi=dpi, facecolor=COLOR_BG, edgecolor="none")
    print(f"📊 筹码分布图已保存: {save_path}")
    return save_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="筹码分布计算 + 图表")
    parser.add_argument("symbol", nargs="?", default="301308", help="股票代码")
    parser.add_argument("-d", "--days", type=int, default=250, help="计算周期(默认250天)")
    parser.add_argument("--decay", type=float, default=0.85, help="衰减系数(默认0.85)")
    parser.add_argument("--bins", type=int, default=200, help="价格分档数(默认200)")
    parser.add_argument("-o", "--output", default=None, help="图片路径")
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()

    from datetime import timedelta
    start = (datetime.now() - timedelta(days=args.days * 2)).strftime("%Y%m%d")
    end = datetime.now().strftime("%Y%m%d")

    print(f"⏳ 拉取 {args.symbol} 数据...")
    df = fetch_kline(args.symbol, "daily", start, end)
    print(f"✅ {len(df)} 条, 计算筹码分布...")

    chip = compute_chip_distribution(df, bins=args.bins, decay_coef=args.decay)
    print(f"   筹码峰: {chip['peak_price']}  获利盘: {chip['profit_ratio']}%  平均成本: {chip['avg_cost']}")
    if chip["all_peaks"]:
        print(f"   所有峰: {chip['all_peaks']}")

    draw_chip_chart(df, chip, args.symbol, save_path=args.output, dpi=args.dpi)
