#!/usr/bin/env python3
"""精确获取用户持仓 + 关注的PCB标的 最新技术数据"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_stock_kline import fetch_kline, compute_kdj, compute_macd

STOCKS = {
    "688072": "拓荆科技",
    "688802": "沐曦股份",
    "301200": "大族数控",
    "600183": "生益科技",
    "301217": "铜冠铜箔",
}

for code, name in STOCKS.items():
    try:
        # 统一用长历史保证MACD计算准确
        df = fetch_kline(code, start="20250101")
        df = compute_kdj(df)
        df = compute_macd(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]
        close = last["close"]

        # 均线
        for ma in [5, 10, 20, 60]:
            df[f"MA{ma}"] = df["close"].rolling(ma).mean()

        # 涨跌幅: n日涨幅 = 今收 / n个交易日前收 - 1
        def ret(n):
            if len(df) <= n: return None
            return round((close / df["close"].iloc[-n-1] - 1) * 100, 2)

        # 20日高低
        r20 = df.tail(20)
        h20, l20 = r20["high"].max(), r20["low"].min()

        # 成交量
        vol5 = df["volume"].tail(6).iloc[:5].mean()
        vol_ratio = last["volume"] / vol5 if vol5 > 0 else 0

        # KDJ/MACD信号
        kdj_golden = prev["K"] <= prev["D"] and last["K"] > last["D"]
        kdj_dead = prev["K"] >= prev["D"] and last["K"] < last["D"]
        macd_golden = prev["DIF"] <= prev["DEA"] and last["DIF"] > last["DEA"]
        macd_dead = prev["DIF"] >= prev["DEA"] and last["DIF"] < last["DEA"]

        # 连续涨跌天数
        up_days = 0
        for i in range(len(df)-1, 0, -1):
            if df["close"].iloc[i] > df["close"].iloc[i-1]:
                up_days += 1
            else:
                break

        print(f"{'='*60}")
        print(f"  {code} {name}  |  {last['date']}  收盘: {close}")
        print(f"{'='*60}")
        print(f"  涨跌: 1日 {ret(1):+}% | 3日 {ret(3):+}% | 5日 {ret(5):+}% | 10日 {ret(10):+}% | 20日 {ret(20):+}%")
        print(f"  连续: {'🟢' if up_days>0 else '🔴'} {abs(up_days)}天{'阳线' if up_days>0 else '阴线'}")
        print(f"  振幅: 20日 {h20}~{l20} ({(h20/l20-1)*100:.0f}%)  距20高 {(close/h20-1)*100:+.1f}%")
        print(f"  均线: MA5={last['MA5']:.1f} MA10={last['MA10']:.1f} MA20={last['MA20']:.1f} MA60={last['MA60']:.1f}")
        print(f"  量比: {vol_ratio:.2f}x | 量 {last['volume']/1e8:.2f}亿手")
        print(f"  KDJ:  K={last['K']:.1f}  D={last['D']:.1f}  J={last['J']:.1f}  |  "
              f"{'🟢金叉' if kdj_golden else '🔴死叉' if kdj_dead else '—'}")
        print(f"  MACD: DIF={last['DIF']:.2f}  DEA={last['DEA']:.2f}  柱={last['MACD']:.2f}  |  "
              f"{'🟢金叉' if macd_golden else '🔴死叉' if macd_dead else '—'}  "
              f"{'红柱' if last['MACD']>0 else '绿柱'}{'扩张' if abs(last['MACD'])>abs(prev['MACD']) else '收缩'}")
        print()

    except Exception as e:
        print(f"{code} {name}: 获取失败 - {e}\n")
