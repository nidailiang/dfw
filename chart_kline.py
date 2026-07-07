#!/usr/bin/env python3
"""画出类似同花顺/通达信的日K线图 —— K线 + 均线 + 成交量 + MACD + KDJ

用法:
    python chart_kline.py                    # 默认江波龙，近 120 天
    python chart_kline.py 000001 -d 180      # 平安银行，近 180 天
    python chart_kline.py -s 20250101        # 从指定日期开始
"""

import argparse
import os
import sys
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # 无头环境
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

# ── 复用 fetch_stock_kline 的数据拉取和指标计算 ─────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_stock_kline import fetch_kline, compute_kdj, compute_macd


# ── 全局配置 ────────────────────────────────────────────
plt.rcParams["font.family"] = "WenQuanYi Zen Hei"
plt.rcParams["axes.unicode_minus"] = False

# A 股配色: 红涨绿跌
COLOR_UP = "#e83929"       # 红
COLOR_DOWN = "#009944"     # 绿
COLOR_BG = "#121212"       # 深色背景
COLOR_GRID = "#2a2a2a"
COLOR_TEXT = "#cccccc"
COLOR_WICK = "#888888"

# 均线颜色
LINE_WHITE = {"color": "#ffffff", "label": "EMA(EMA(C,10),10)", "width": 1.0}
LINE_YELLOW = {"color": "#ffcc00", "label": "(MA14+MA28+MA57+MA114)/4", "width": 1.0}

# KDJ 颜色
KDJ_COLORS = {"K": "#ffffff", "D": "#ffcc00", "J": "#ff66cc"}

# MACD 颜色
MACD_COLORS = {"DIF": "#ffffff", "DEA": "#ffcc00"}


def make_ohlc_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """将 date/open/high/low/close/volume 转为 mplfinance 可用的 OHLC DataFrame"""
    ohlc = df[["date", "open", "high", "low", "close", "volume"]].copy()
    ohlc["date"] = pd.to_datetime(ohlc["date"])
    ohlc = ohlc.set_index("date")
    return ohlc


def draw_chart(df: pd.DataFrame, symbol: str, title: str = None,
               save_path: str = None, dpi: int = 150):
    """绘制 A 股风格 K 线图：主图 + 量 + MACD + KDJ"""

    n = len(df)

    # ── 计算自定均线 ─────────────────────────────────────
    # 白线: EMA(EMA(C,10),10)
    df["ema_double"] = df["close"].ewm(span=10, adjust=False).mean().ewm(span=10, adjust=False).mean()
    # 黄线: (MA14+MA28+MA57+MA114)/4
    df["ma_avg"] = (
        df["close"].rolling(14).mean() +
        df["close"].rolling(28).mean() +
        df["close"].rolling(57).mean() +
        df["close"].rolling(114).mean()
    ) / 4

    # ── 计算指标 ────────────────────────────────────────
    df = compute_kdj(df)
    df = compute_macd(df)

    # ── 颜色数据 ────────────────────────────────────────
    up_mask   = df["close"] >= df["open"]
    down_mask = df["close"] < df["open"]

    # ── 创建画布 ────────────────────────────────────────
    # 4 个面板，高度比: K线:量:MACD:KDJ = 4 : 1.3 : 1.5 : 1.5
    fig = plt.figure(figsize=(16, 10), facecolor=COLOR_BG)
    gs = fig.add_gridspec(
        4, 1, height_ratios=[4, 1.3, 1.5, 1.5], hspace=0.05,
        left=0.02, right=0.98, top=0.96, bottom=0.03)

    ax_kline  = fig.add_subplot(gs[0])   # K线 + 均线
    ax_vol    = fig.add_subplot(gs[1], sharex=ax_kline)   # 成交量
    ax_macd   = fig.add_subplot(gs[2], sharex=ax_kline)   # MACD
    ax_kdj    = fig.add_subplot(gs[3], sharex=ax_kline)   # KDJ

    # 公共设置
    for ax in [ax_kline, ax_vol, ax_macd, ax_kdj]:
        ax.set_facecolor(COLOR_BG)
        ax.tick_params(colors=COLOR_TEXT, labelsize=7)
        ax.grid(True, color=COLOR_GRID, linewidth=0.5, alpha=0.6)

    # ━━━━━━━━━━ 面板 0: K 线 + 均线 ━━━━━━━━━━━━━━━━━
    body_width = 0.6
    for i in range(n):
        op, hi, lo, cl = df["open"].iloc[i], df["high"].iloc[i], \
                         df["low"].iloc[i], df["close"].iloc[i]
        color = COLOR_UP if cl >= op else COLOR_DOWN

        # 影线
        ax_kline.plot([i, i], [lo, hi], color=color, linewidth=0.8)

        # 实体
        body_h = abs(cl - op)
        body_bottom = min(op, cl)
        rect = Rectangle((i - body_width / 2, body_bottom), body_width, max(body_h, 0.001),
                          facecolor=color, edgecolor=color, linewidth=0.5)
        ax_kline.add_patch(rect)

    # 自定均线
    ax_kline.plot(range(n), df["ema_double"], color=LINE_WHITE["color"],
                  linewidth=LINE_WHITE["width"], label=LINE_WHITE["label"])
    ax_kline.plot(range(n), df["ma_avg"], color=LINE_YELLOW["color"],
                  linewidth=LINE_YELLOW["width"], label=LINE_YELLOW["label"])

    ax_kline.legend(loc="upper left", fontsize=7, facecolor=COLOR_BG,
                    edgecolor=COLOR_GRID, labelcolor=COLOR_TEXT, ncol=2)

    # Y 轴
    ax_kline.yaxis.tick_right()
    ax_kline.yaxis.set_label_position("right")

    # ━━━━━━━━━━ 面板 1: 成交量 ━━━━━━━━━━━━━━━━━━━━━━
    vol_up   = np.where(up_mask,   df["volume"].values, 0)
    vol_down = np.where(down_mask, df["volume"].values, 0)
    bar_width_vol = 0.7
    ax_vol.bar(range(n), vol_up,   width=bar_width_vol, color=COLOR_UP,   linewidth=0)
    ax_vol.bar(range(n), vol_down, width=bar_width_vol, color=COLOR_DOWN, linewidth=0)

    # MA5 / MA10 量均线
    vol_ma5  = df["volume"].rolling(5).mean()
    vol_ma10 = df["volume"].rolling(10).mean()
    ax_vol.plot(range(n), vol_ma5,  color="#ffffff", linewidth=0.6, alpha=0.5, label="VOL5")
    ax_vol.plot(range(n), vol_ma10, color="#ffcc00", linewidth=0.6, alpha=0.5, label="VOL10")
    ax_vol.legend(loc="upper left", fontsize=6, facecolor=COLOR_BG,
                  edgecolor=COLOR_GRID, labelcolor=COLOR_TEXT)

    ax_vol.yaxis.tick_right()
    ax_vol.yaxis.set_label_position("right")
    # 格式化大数字
    ax_vol.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{x/1e6:.0f}M" if x >= 1e6 else f"{x/1e4:.0f}万"))

    # ━━━━━━━━━━ 面板 2: MACD ━━━━━━━━━━━━━━━━━━━━━━
    # 柱状图
    macd_vals = df["MACD"].values
    colors_macd = np.where(macd_vals >= 0, COLOR_UP, COLOR_DOWN)
    # 对连续段画柱
    ax_macd.bar(range(n), macd_vals, width=bar_width_vol, color=colors_macd, linewidth=0)

    # DIF / DEA 线
    ax_macd.plot(range(n), df["DIF"], color=MACD_COLORS["DIF"], linewidth=0.8, label="DIF")
    ax_macd.plot(range(n), df["DEA"], color=MACD_COLORS["DEA"], linewidth=0.8, label="DEA")
    ax_macd.axhline(y=0, color="#666666", linewidth=0.5)

    ax_macd.legend(loc="upper left", fontsize=7, facecolor=COLOR_BG,
                   edgecolor=COLOR_GRID, labelcolor=COLOR_TEXT)
    ax_macd.yaxis.tick_right()
    ax_macd.yaxis.set_label_position("right")

    # ━━━━━━━━━━ 面板 3: KDJ ━━━━━━━━━━━━━━━━━━━━━━
    ax_kdj.plot(range(n), df["K"], color=KDJ_COLORS["K"], linewidth=0.8, label="K")
    ax_kdj.plot(range(n), df["D"], color=KDJ_COLORS["D"], linewidth=0.8, label="D")
    ax_kdj.plot(range(n), df["J"], color=KDJ_COLORS["J"], linewidth=0.8, label="J")

    # 参考线
    for level, ls in [(20, "--"), (50, "-"), (80, "--")]:
        ax_kdj.axhline(y=level, color="#666666", linewidth=0.5, linestyle=ls, alpha=0.6)

    # 超买/超卖填充
    ax_kdj.axhspan(80, 110, alpha=0.05, color=COLOR_UP)
    ax_kdj.axhspan(-10, 20, alpha=0.05, color=COLOR_DOWN)

    ax_kdj.set_ylim(-5, 105)
    ax_kdj.legend(loc="upper left", fontsize=7, facecolor=COLOR_BG,
                  edgecolor=COLOR_GRID, labelcolor=COLOR_TEXT)
    ax_kdj.yaxis.tick_right()
    ax_kdj.yaxis.set_label_position("right")

    # ━━━━━━━━━━ X 轴标签 ━━━━━━━━━━━━━━━━━━━━━━━━
    # 只在最底部面板显示日期
    tick_step = max(n // 10, 1)
    tick_positions = list(range(0, n, tick_step))
    tick_labels = [df["date"].iloc[i] for i in tick_positions]
    ax_kdj.set_xticks(tick_positions)
    ax_kdj.set_xticklabels(tick_labels, rotation=30, fontsize=7, color=COLOR_TEXT)

    # 隐藏其他面板的 x 轴标签
    for ax in [ax_kline, ax_vol, ax_macd]:
        ax.tick_params(labelbottom=False)

    # ━━━━━━━━━━ 标题 ━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if title is None:
        stock_name = {"301308": "江波龙"}.get(symbol, symbol)
        title = f"{stock_name} ({symbol}) 日K线"
    fig.suptitle(title, color=COLOR_TEXT, fontsize=14, fontweight="bold", y=0.98)

    # ━━━━━━━━━━ 价格标注（右侧最新价） ━━━━━━━━━━━━
    last_close = df["close"].iloc[-1]
    last_date  = df["date"].iloc[-1]
    ax_kline.text(n - 1, last_close, f" {last_close}",
                  color=COLOR_TEXT, fontsize=8, va="center", fontweight="bold")

    # ━━━━━━━━━━ 保存 ━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if save_path is None:
        save_path = f"chart_{symbol}_{datetime.now().strftime('%Y%m%d')}.png"
    fig.savefig(save_path, dpi=dpi, facecolor=COLOR_BG, edgecolor="none")
    print(f"📊 图表已保存: {save_path}")
    return save_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="画出 A 股 K 线图（K线+量+MACD+KDJ）")
    parser.add_argument("symbol", nargs="?", default="301308", help="股票代码（默认 301308 江波龙）")
    parser.add_argument("-d", "--days", type=int, default=180,
                        help="拉取近多少天的数据（默认 180）")
    parser.add_argument("-s", "--start", default=None,
                        help="起始日期 YYYYMMDD（与 -d 互斥，优先用 -d）")
    parser.add_argument("-o", "--output", default=None, help="图片保存路径")
    parser.add_argument("--dpi", type=int, default=150, help="图片分辨率（默认 150）")
    args = parser.parse_args()

    # 计算日期范围
    if args.start:
        start = args.start
    else:
        from datetime import timedelta
        start = (datetime.now() - timedelta(days=args.days * 2)).strftime("%Y%m%d")

    end = datetime.now().strftime("%Y%m%d")

    print(f"⏳ 拉取 {args.symbol} 数据...")
    df = fetch_kline(args.symbol, "daily", start, end)
    print(f"✅ 共 {len(df)} 条")

    draw_chart(df, args.symbol, save_path=args.output, dpi=args.dpi)
