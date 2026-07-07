#!/usr/bin/env python3
"""江波龙 (301308) 综合概率分析 —— 财报 + PE + 机构评级 + 盈利预测 + 技术指标

用法:
    python analyze_stock.py              # 默认江波龙
    python analyze_stock.py 000001       # 其他股票
"""

import argparse
import sys
import os
import json
from datetime import datetime

import numpy as np
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 40)
pd.set_option("display.float_format", lambda x: f"{x:.2f}" if abs(x) < 1e6 else f"{x:.0f}")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_stock_kline import fetch_kline, compute_kdj, compute_macd

import akshare as ak


# ═══════════════════════════════════════════════════════
#  数据采集
# ═══════════════════════════════════════════════════════

def safe_fetch(fn, label: str) -> pd.DataFrame | None:
    """安全抓取，失败时打印原因"""
    try:
        return fn()
    except Exception as e:
        print(f"  ⚠️ {label}: {str(e)[:60]}")
        return None


def fetch_all_data(symbol: str) -> dict:
    """采集所有可用数据"""
    print(f"\n{'='*70}")
    print(f"  🔍 采集 {symbol} 综合数据...")
    print(f"{'='*70}")

    data = {"symbol": symbol}

    # ── K线 + 技术指标 ──
    print("  📈 K线数据...", end=" ")
    df_kline = fetch_kline(symbol)
    df_kline = compute_kdj(df_kline)
    df_kline = compute_macd(df_kline)
    # 均线
    for ma in [5, 10, 20, 60, 120, 250]:
        df_kline[f"MA{ma}"] = df_kline["close"].rolling(ma).mean()
    data["kline"] = df_kline
    print(f"{len(df_kline)} 条")

    # ── 财务摘要 ──
    print("  📊 财务摘要...", end=" ")
    df_fin = safe_fetch(
        lambda: ak.stock_financial_abstract_ths(symbol=symbol, indicator="按报告期"),
        "财务摘要")
    if df_fin is not None:
        # 只保留年报 + 最近季报
        df_fin = df_fin.dropna(subset=["净利润", "营业总收入"], how="all")
        data["financial"] = df_fin
        print(f"{len(df_fin)} 期")
    else:
        data["financial"] = None

    # ── 利润表 ──
    print("  📊 利润表...", end=" ")
    em_code = f"SZ{symbol}" if not symbol.startswith("6") else f"SH{symbol}"
    df_profit = safe_fetch(
        lambda: ak.stock_profit_sheet_by_report_em(symbol=em_code),
        "利润表")
    if df_profit is not None:
        data["profit"] = df_profit
        print(f"{len(df_profit)} 条")
    else:
        data["profit"] = None

    # ── 资产负债表 ──
    print("  📊 资产负债表...", end=" ")
    df_balance = safe_fetch(
        lambda: ak.stock_balance_sheet_by_report_em(symbol=em_code),
        "资产负债表")
    if df_balance is not None:
        data["balance"] = df_balance
        print(f"{len(df_balance)} 条")
    else:
        data["balance"] = None

    # ── 盈利预测 ──
    print("  🔮 盈利预测...", end=" ")
    df_forecast = safe_fetch(
        lambda: ak.stock_profit_forecast_ths(symbol=symbol, indicator="预测年报每股收益"),
        "盈利预测")
    data["forecast"] = df_forecast if df_forecast is not None and len(df_forecast) > 0 else None
    if data["forecast"] is not None:
        print(f"{len(df_forecast)} 年预测")
    else:
        print("无")

    # ── 机构调研 ──
    print("  📋 机构调研...", end=" ")
    df_research = safe_fetch(
        lambda: ak.stock_research_report_em(symbol=symbol),
        "机构调研")
    data["research"] = df_research if df_research is not None and len(df_research) > 0 else None
    if data["research"] is not None:
        print(f"{len(df_research)} 篇")
    else:
        print("无")

    # ── 股东人数变化 ──
    print("  👥 股东人数...", end=" ")
    df_holder_count = safe_fetch(
        lambda: ak.stock_main_stock_holder(stock=symbol),
        "股东人数")
    data["holder_count"] = df_holder_count if df_holder_count is not None and len(df_holder_count) > 0 else None
    if data["holder_count"] is not None:
        # 提取每期股东总数（去重）
        periods = df_holder_count[["截至日期", "股东总数", "平均持股数"]].drop_duplicates(subset=["截至日期"])
        data["holder_count"] = periods.dropna(subset=["股东总数"])
        print(f"{len(data['holder_count'])} 期")
    else:
        print("无")

    # ── 股东增减持 ──
    print("  👤 股东增减持...", end=" ")
    df_holder = safe_fetch(
        lambda: ak.stock_shareholder_change_ths(symbol=symbol),
        "股东增减持")
    data["holder"] = df_holder if df_holder is not None and len(df_holder) > 0 else None
    if data["holder"] is not None:
        print(f"{len(df_holder)} 条")
    else:
        print("无")

    # ── 板块资金排名 ──
    print("  🔥 概念板块资金...", end=" ")
    df_sector_flow = safe_fetch(
        lambda: ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="概念资金流"),
        "板块资金")
    data["sector_flow"] = df_sector_flow if df_sector_flow is not None and len(df_sector_flow) > 0 else None
    if data["sector_flow"] is not None:
        print(f"{len(df_sector_flow)} 个概念")
    else:
        print("无")

    # ── 北向资金 ──
    print("  🌏 北向资金...", end=" ")
    df_north = safe_fetch(
        lambda: ak.stock_hsgt_fund_flow_summary_em(),
        "北向资金")
    data["northbound"] = df_north if df_north is not None and len(df_north) > 0 else None
    if data["northbound"] is not None:
        print(f"{len(df_north)} 条")
    else:
        print("无")

    # ── 行业PE对比 ──
    print("  📊 行业PE...", end=" ")
    df_ind_pe = safe_fetch(
        lambda: ak.stock_industry_pe_ratio_cninfo(symbol="证监会行业分类", date=datetime.now().strftime("%Y%m%d")),
        "行业PE")
    data["industry_pe"] = df_ind_pe if df_ind_pe is not None and len(df_ind_pe) > 0 else None
    if data["industry_pe"] is not None:
        print(f"{len(df_ind_pe)} 个行业")
    else:
        print("无")

    return data


# ═══════════════════════════════════════════════════════
#  分析引擎
# ═══════════════════════════════════════════════════════

def analyze_financial(data: dict) -> dict:
    """财报质量评分 (0-100) —— 从 stock_data dict 提取"""
    result = {"score": 50, "details": [], "warnings": [], "sub_scores": {}}

    fin = data.get("financial")
    if not fin or not fin.get("latest_annual"):
        result["details"].append("财务数据不足")
        return result

    la = fin["latest_annual"]
    pa = fin.get("prev_annual", {})
    lq = fin.get("latest_quarter", {})

    score = 50
    sub = {}
    details = []

    # ─── 因子1: 营收增长率 (权重 20%) ───
    rev = safe_float(la.get("营业总收入"))
    rev_g = safe_float(la.get("营业总收入同比增长率"))
    prev_rev = safe_float(pa.get("营业总收入"))
    if rev_g is not None:
        if rev_g > 30:      s = 20; details.append(f"营收增速优秀 +{rev_g:.1f}%")
        elif rev_g > 15:    s = 14; details.append(f"营收增速良好 +{rev_g:.1f}%")
        elif rev_g > 5:     s = 8;  details.append(f"营收增速尚可 +{rev_g:.1f}%")
        elif rev_g > 0:     s = 3;  details.append(f"营收微增 +{rev_g:.1f}%")
        elif rev_g > -5:    s = -5; details.append(f"⚠️ 营收微降 {rev_g:.1f}%")
        elif rev_g > -15:   s = -10; details.append(f"⚠️ 营收下降 {rev_g:.1f}%")
        else:               s = -15; details.append(f"⚠️ 营收大降 {rev_g:.1f}%")
        sub["营收增长"] = 50 + s * 2.5
        score += s
        if rev_g < 0:
            result["warnings"].append(f"营收同比 {rev_g:.1f}%")

    # ─── 因子2: 净利润增长率 (权重 25%) ───
    profit_g = safe_float(la.get("净利润同比增长率"))
    profit = safe_float(la.get("净利润"))
    if profit_g is not None:
        if profit_g > 80:       s = 25; details.append(f"利润暴增 +{profit_g:.1f}%")
        elif profit_g > 40:     s = 20; details.append(f"利润高增 +{profit_g:.1f}%")
        elif profit_g > 20:     s = 14; details.append(f"利润增长 +{profit_g:.1f}%")
        elif profit_g > 10:     s = 7;  details.append(f"利润稳步增长 +{profit_g:.1f}%")
        elif profit_g > 0:      s = 3;  details.append(f"利润微增 +{profit_g:.1f}%")
        elif profit_g > -10:    s = -5; details.append(f"⚠️ 利润微降 {profit_g:.1f}%")
        elif profit_g > -30:    s = -12; details.append(f"⚠️ 利润下滑 {profit_g:.1f}%")
        else:                   s = -20; details.append(f"⚠️ 利润大降 {profit_g:.1f}%")
        sub["利润增长"] = 50 + s * 2
        score += s
        if profit_g < 0:
            result["warnings"].append(f"净利润同比 {profit_g:.1f}%")
    elif profit is not None and profit > 0:
        details.append("净利润为正(无同比数据)")

    # ─── 因子3: ROE (权重 18%) ───
    roe = safe_float(la.get("净资产收益率"))
    if roe is not None:
        if roe > 25:        s = 18; details.append(f"ROE 卓越 {roe:.1f}%")
        elif roe > 15:      s = 12; details.append(f"ROE 优秀 {roe:.1f}%")
        elif roe > 10:      s = 7;  details.append(f"ROE 良好 {roe:.1f}%")
        elif roe > 5:       s = 2;  details.append(f"ROE 一般 {roe:.1f}%")
        elif roe > 0:       s = -3; details.append(f"ROE 偏低 {roe:.1f}%")
        else:               s = -8; details.append(f"⚠️ ROE 为负 {roe:.1f}%")
        sub["ROE"] = 50 + s * 50/18
        score += s
        if roe < 5:
            result["warnings"].append(f"ROE 偏低 {roe:.1f}%")

    # ─── 因子4: 毛利率 (权重 10%) ───
    gm = safe_float(la.get("销售毛利率"))
    if gm is not None:
        if gm > 35:         s = 10; details.append(f"毛利率优秀 {gm:.1f}%")
        elif gm > 20:       s = 5;  details.append(f"毛利率良好 {gm:.1f}%")
        elif gm > 10:       s = 2;  details.append(f"毛利率一般 {gm:.1f}%")
        else:               s = -5; details.append(f"毛利率偏低 {gm:.1f}%")
        sub["毛利率"] = 50 + s * 5
        score += s

    # ─── 因子5: 净利率 (权重 10%) ───
    nm = safe_float(la.get("销售净利率"))
    if nm is not None:
        if nm > 12:         s = 10; details.append(f"净利率优秀 {nm:.1f}%")
        elif nm > 6:        s = 5;  details.append(f"净利率良好 {nm:.1f}%")
        elif nm > 3:        s = 2;  details.append(f"净利率正常 {nm:.1f}%")
        else:               s = -5; details.append(f"净利率偏薄 {nm:.1f}%")
        sub["净利率"] = 50 + s * 5
        score += s

    # ─── 因子6: 负债率 (权重 7%) ───
    dr = safe_float(la.get("资产负债率"))
    if dr is not None:
        if dr > 70:         s = -7; result["warnings"].append(f"负债率偏高 {dr:.1f}%")
        elif dr > 50:       s = -2; details.append(f"负债率中等 {dr:.1f}%")
        elif dr > 25:       s = 4;  details.append(f"负债率健康 {dr:.1f}%")
        else:               s = 7;  details.append(f"负债率低、杠杆空间大 {dr:.1f}%")
        sub["负债率"] = 50 + s * 50/7
        score += s

    # ─── 因子7: 现金流质量 (权重 5%) ───
    eps_cash = safe_float(la.get("每股经营现金流"))
    eps = safe_float(la.get("基本每股收益"))
    if eps_cash is not None and eps is not None:
        if eps > 0:
            ratio = eps_cash / eps
            if ratio > 1.5:     s = 5; details.append(f"现金流充沛 (经营/EPS={ratio:.1f})")
            elif ratio > 0.7:   s = 3; details.append(f"现金流良好 ({ratio:.1f})")
            elif ratio > 0:     s = 1; details.append(f"现金流一般 ({ratio:.1f})")
            else:               s = -3; details.append(f"经营现金流为负")
            sub["现金流"] = 50 + s * 10
            score += s

    # ─── 因子8: 盈利质量 (权重 5%) ───
    if la.get("deducted_profit") and la.get("profit"):
        deducted_ratio = la["deducted_profit"] / la["profit"] if la["profit"] != 0 else 0
        if deducted_ratio > 0.9:
            s = 5; details.append("扣非利润占比高，盈利质量好")
        elif deducted_ratio > 0.6:
            s = 2; details.append("盈利含部分非经常性收益")
        elif deducted_ratio < 0:
            s = -5; details.append("扣非亏损，盈利依赖非经常性")
        else:
            s = 0
        score += s

    result["score"] = max(0, min(100, score))
    result["details"] = details
    result["sub_scores"] = sub
    return result


def analyze_valuation(data: dict) -> dict:
    """估值分析：从 stock_data dict 提取"""
    result = {"pe": None, "pb": None, "fwd_pe": None, "assessment": "未知",
              "score": 50, "sub_scores": {}}

    kl = data.get("kline", {})
    fc = data.get("forecast", [])
    fin = data.get("financial", {})

    if not kl:
        return result

    latest_price = kl.get("latest", {}).get("close", 0)
    sub = {}

    # ── 静态 PE/PB ──
    la = fin.get("latest_annual", {})
    eps = la.get("eps")
    bvps = la.get("bvps")

    if eps and eps > 0:
        pe = latest_price / eps
        result["pe"] = round(pe, 1)
        s1 = 12 if pe < 20 else 8 if pe < 35 else 5 if pe < 55 else 0 if pe < 80 else -8
        sub["静态PE"] = 50 + s1 * 4

    if bvps and bvps > 0:
        result["pb"] = round(latest_price / bvps, 1)

    # ── 远期 PE ──
    score_val = 0
    if fc and len(fc) > 0:
        fwd_eps = fc[0].get("eps_mean")
        if fwd_eps and fwd_eps > 0:
            fwd_pe = latest_price / fwd_eps
            result["fwd_pe"] = round(fwd_pe, 1)
            result["fwd_eps"] = round(fwd_eps, 2)
            s_val = 20 if fwd_pe < 15 else 14 if fwd_pe < 25 else 8 if fwd_pe < 35 else 3 if fwd_pe < 50 else -5 if fwd_pe < 70 else -12
            sub["远期PE"] = 50 + s_val * 2.5
            score_val = s_val
            result["assessment"] = f"远期PE {fwd_pe:.1f}"

    # ── PEG ──
    if fc and len(fc) >= 2:
        eps_cur = fc[0].get("eps_mean")
        eps_next = fc[1].get("eps_mean")
        if eps_cur and eps_next and eps_next != 0:
            eps_growth = (eps_cur - eps_next) / abs(eps_next) * 100
            sub["EPS增速"] = round(eps_growth, 1)
            if eps_growth > 15: score_val += 3
            elif eps_growth < -10: score_val -= 3

    result["score"] = max(0, min(100, 50 + score_val * 2))
    result["sub_scores"] = sub
    return result


def analyze_institutional(data: dict) -> dict:
    """机构评级分析"""
    result = {"rating_dist": {}, "recent_signal": "无", "score": 50,
              "details": [], "reports": []}

    df_research = data.get("research")
    if df_research is None or len(df_research) == 0:
        result["details"].append("无机构调研数据")
        return result

    # 统计评级分布
    if "东财评级" in df_research.columns:
        ratings = df_research["东财评级"].value_counts().to_dict()
    elif "评级" in df_research.columns:
        ratings = df_research["评级"].value_counts().to_dict()
    else:
        # 从报告名称推断
        ratings = {}
        for _, row in df_research.iterrows():
            name = str(row.get("报告名称", ""))
            if "买入" in name:
                ratings["买入"] = ratings.get("买入", 0) + 1
            elif "增持" in name:
                ratings["增持"] = ratings.get("增持", 0) + 1

    result["rating_dist"] = ratings

    # 评分
    total = sum(ratings.values())
    bullish = ratings.get("买入", 0) + ratings.get("增持", 0)
    if total > 0:
        bull_ratio = bullish / total
        if bull_ratio >= 0.8:
            result["score"] = 75
            result["recent_signal"] = "强烈看多"
        elif bull_ratio >= 0.5:
            result["score"] = 60
            result["recent_signal"] = "偏多"
        elif bull_ratio >= 0.3:
            result["score"] = 45
            result["recent_signal"] = "中性偏谨慎"
        else:
            result["score"] = 30
            result["recent_signal"] = "偏空"
        result["details"].append(f"看多比例 {bull_ratio:.0%} ({bullish}/{total})")

    # 近一月研报数
    recent_month = rs.get("recent_month_count", 0)

    # 列出近3篇
    for _, row in df_research.head(3).iterrows():
        result["reports"].append({
            "date": str(row.get("日期", "")),
            "title": str(row.get("报告名称", "")),
            "rating": str(row.get("东财评级", "")),
            "org": str(row.get("机构", "")),
        })

    return result


def analyze_technical(data: dict) -> dict:
    """技术面分析 —— 从 stock_data dict 提取"""
    kl = data.get("kline", {})
    result = {"score": 50, "signals": [], "warnings": []}

    ind = kl.get("indicators", {})
    lt = kl.get("latest", {})
    ret = kl.get("returns", {})
    close = lt.get("close", 0)
    ma20 = ind.get("ma20", 0)
    ma60 = ind.get("ma60", 0)
    ma120 = ind.get("ma120", 0)
    ma250 = ind.get("ma250", 0)

    # ── 均线 ──
    if ma60 and ma120 and ma250 and all([ma60, ma120, ma250, close]):
        if close > ma60 > ma120 > ma250:
            result["signals"].append("均线多头排列 🟢"); result["score"] += 15
        elif close < ma60 < ma120 < ma250:
            result["signals"].append("均线空头排列 🔴"); result["score"] -= 15
        elif close > ma60:
            result["signals"].append("站上 MA60"); result["score"] += 5
        else:
            result["signals"].append("跌破 MA60"); result["score"] -= 5

    # ── MACD ──
    dif = ind.get("DIF", 0) or 0
    dea = ind.get("DEA", 0) or 0
    macd_bar = ind.get("MACD", 0) or 0
    if dif and dea:
        if dif > 0 and dif > dea:
            result["signals"].append("MACD 零轴上多头"); result["score"] += 8
        elif dif > 0 and dif < dea:
            result["signals"].append("MACD 零轴上回调"); result["score"] -= 3
        elif dif < 0 and dif > dea:
            result["signals"].append("MACD 零轴下反弹"); result["score"] += 3
        else:
            result["signals"].append("MACD 零轴下空头"); result["score"] -= 8

    # ── KDJ ──
    k = ind.get("K", 50) or 50
    d = ind.get("D", 50) or 50
    j = ind.get("J", 50) or 50
    if j > 100:
        result["warnings"].append(f"J>100 短线超买 (J={j:.0f})"); result["score"] -= 8
    elif j < 0:
        result["signals"].append(f"J<0 短线超卖 (J={j:.0f})"); result["score"] += 8
    elif j > 80:
        result["signals"].append(f"KDJ 偏强 J={j:.0f}")
    elif j < 20:
        result["signals"].append(f"KDJ 偏弱 J={j:.0f}")
    else:
        result["signals"].append(f"KDJ 中性 (K={k:.0f} D={d:.0f} J={j:.0f})")

    # ── 涨跌幅 ──
    ret_5d = ret.get("5d", 0) or 0
    ret_20d = ret.get("20d", 0) or 0
    if ret_20d < -20:
        result["signals"].append(f"近20日跌幅 {ret_20d:.1f}% (超跌)"); result["score"] += 8
    elif ret_20d > 30:
        result["warnings"].append(f"近20日涨幅 {ret_20d:.1f}% (过热)"); result["score"] -= 6
    result["ret_5d"] = round(ret_5d, 1)
    result["ret_20d"] = round(ret_20d, 1)

    result["score"] = max(0, min(100, result["score"]))
    return result


def analyze_sentiment(data: dict) -> dict:
    """股东行为分析 —— 从 stock_data dict 提取"""
    result = {"score": 50, "details": [], "warnings": [],
              "holder_count_trend": None}

    hd = data.get("holders", {})
    if not hd:
        result["details"].append("无股东数据")
        return result

    cur = hd.get("latest", {})
    prev_y = hd.get("year_ago", {})
    yoy = hd.get("yoy_change_pct")
    latest_count = cur.get("total_holders") if cur else None
    avg_hold = cur.get("avg_hold") if cur else None
    score = 50

    if latest_count:
        result["holder_count_trend"] = {
            "current": latest_count,
            "current_date": cur.get("date", ""),
            "avg_hold": avg_hold,
            "prev_year": prev_y.get("total_holders") if prev_y else None,
            "y_change": yoy,
        }

        if yoy is not None:
            if yoy < -20:    score += 15; result["details"].append(f"股东同比大幅减少 ({yoy:+.1f}%)，筹码高度集中 🟢")
            elif yoy < -10:  score += 8;  result["details"].append(f"股东同比减少 ({yoy:+.1f}%)，筹码趋于集中")
            elif yoy < -3:   score += 3;  result["details"].append(f"股东同比小幅减少 ({yoy:+.1f}%)")
            elif yoy > 30:   score -= 15; result["warnings"].append(f"股东同比大幅增加 ({yoy:+.1f}%)，筹码高度分散 🔴")
            elif yoy > 15:   score -= 8;  result["warnings"].append(f"股东同比增加 ({yoy:+.1f}%)，筹码趋于分散")
            elif yoy > 5:    score -= 3;  result["details"].append(f"股东同比小幅增加 ({yoy:+.1f}%)")
            result["holder_y_change"] = round(yoy, 1)

    # ── 增减持 ──
    it = data.get("insider_trades", {})
    if it:
        buys = it.get("buy_count", 0)
        sells = it.get("sell_count", 0)
        signal = it.get("net_signal", "")
        if "增持" in signal:
            score += 10; result["details"].append(f"增减持: {signal} (增{buys} vs 减{sells})")
        elif "减持" in signal:
            score -= 10; result["warnings"].append(f"增减持: {signal} (增{buys} vs 减{sells})")
        else:
            result["details"].append("近期无显著增减持")

    result["score"] = max(0, min(100, score))
    return result


# ── 新增维度: 板块资金 ──────────────────────────────────
def analyze_sector_flow(data: dict) -> dict:
    """板块资金 —— 从 stock_data dict 提取"""
    result = {"score": 50, "details": [], "warnings": [], "sub_scores": {}}

    sf = data.get("sector_flow")
    if not sf:
        result["details"].append("⚠️ 板块资金数据暂不可用 (东方财富源波动)")
        return result

    relevant = sf.get("relevant_sectors", [])
    top5 = sf.get("top5_hot_concepts", [])

    if relevant:
        total_inflow = sum(s.get("main_inflow", 0) or 0 for s in relevant)
        up_count = sum(1 for s in relevant if (s.get("change_pct", 0) or 0) > 0)

        for s in relevant[:5]:
            direction = "流入" if (s.get("main_inflow") or 0) > 0 else "流出"
            result["details"].append(
                f"{s['name']}: {s.get('change_pct'):+.1f}%  主力{方向} {abs(s.get('main_inflow') or 0)/1e8:.1f}亿")

        if up_count >= len(relevant) * 0.7:
            result["score"] += 20
            result["details"].append(f"板块全面走强 ({up_count}/{len(relevant)} 上涨)")
        elif up_count > 0:
            result["score"] += 10
            result["details"].append(f"板块偏强 ({up_count}/{len(relevant)} 上涨)")
        else:
            result["score"] -= 10
            result["warnings"].append("相关板块全面走弱")

        if total_inflow > 1e9:
            result["score"] += 15
            result["details"].append(f"板块主力净流入 {total_inflow/1e8:.0f}亿")
        elif total_inflow < -5e8:
            result["score"] -= 10
            result["warnings"].append(f"板块主力净流出 {abs(total_inflow)/1e8:.0f}亿")

    if top5:
        top_names = ", ".join([t["name"] for t in top5[:5]])
        result["details"].append(f"今日最热概念: {top_names}")

    result["score"] = max(0, min(100, result["score"]))
    return result


# ── 新增维度: 市场趋势 ──────────────────────────────────
def analyze_market_trend(data: dict) -> dict:
    """市场整体趋势 —— 从 stock_data dict 提取"""
    result = {"score": 50, "details": [], "warnings": [], "sub_scores": {}}
    s_nb = s_mkt = 0

    # ── 北向资金 ──
    nb = data.get("northbound", {})
    if nb:
        net_buy = nb.get("net_buy_amount", 0) or 0
        if net_buy > 5e9:      s_nb = 15; detail = f"北向大幅流入 {net_buy/1e8:.0f}亿 🟢"
        elif net_buy > 1e9:    s_nb = 8;  detail = f"北向净流入 {net_buy/1e8:.0f}亿"
        elif net_buy > -1e9:   s_nb = 2;  detail = "北向资金平衡"
        elif net_buy > -5e9:   s_nb = -5; detail = f"北向净流出 {abs(net_buy)/1e8:.0f}亿"
        else:                  s_nb = -12; detail = f"⚠️ 北向大幅流出 {abs(net_buy)/1e8:.0f}亿"
        result["details"].append(detail)

    # ── 大盘趋势 ──
    kl = data.get("kline", {})
    ret = kl.get("returns", {})
    ret_20d = ret.get("20d", 0) or 0
    if ret_20d > 15:      s_mkt = 10; result["details"].append(f"近20日 +{ret_20d:.1f}% 强势")
    elif ret_20d > 5:     s_mkt = 5;  result["details"].append(f"近20日 +{ret_20d:.1f}% 偏强")
    elif ret_20d > -5:    s_mkt = 1;  result["details"].append(f"近20日 {ret_20d:+.1f}% 震荡")
    elif ret_20d > -15:   s_mkt = -5; result["warnings"].append(f"近20日 {ret_20d:.1f}% 走弱")
    else:                 s_mkt = -10; result["warnings"].append(f"近20日 {ret_20d:.1f}% 大跌")

    result["score"] = max(0, min(100, 50 + s_nb + s_mkt))
    return result


# ── 新增维度: 行业对比 ──────────────────────────────────
def analyze_industry_compare(data: dict) -> dict:
    """行业PE对比 —— 从 stock_data dict 提取"""
    result = {"score": 50, "details": [], "sub_scores": {}}

    ip = data.get("industry_pe")
    if not ip:
        result["details"].append("无行业PE数据")
        return result

    mi = ip.get("matched_industry")
    if mi:
        result["details"].append(f"行业: {mi.get('industry_name', '')}")
        wpe = mi.get("pe_weighted")
        mpe = mi.get("pe_median")
        if wpe:
            result["details"].append(f"行业加权PE: {wpe:.1f}")
        if mpe:
            result["details"].append(f"行业中位数PE: {mpe:.1f}")

        # 估值水位判断
        val = data.get("details", {}).get("valuation", {})
        fwd_pe = val.get("fwd_pe") if val else None
        if fwd_pe and mpe:
            ratio = fwd_pe / mpe
            if ratio < 0.4:
                result["details"].append(f"远期PE仅为行业中位数的 {ratio:.0%} → 显著低估")
                result["score"] = 75
            elif ratio < 0.7:
                result["details"].append(f"远期PE为行业中位数的 {ratio:.0%} → 偏低")
                result["score"] = 60
            elif ratio < 1.2:
                result["details"].append("估值与行业持平")
                result["score"] = 50
            else:
                result["details"].append(f"远期PE高于行业中位数 → 偏贵")
                result["score"] = 35

    top3 = ip.get("top3_pe_industries", [])
    bot3 = ip.get("bottom3_pe_industries", [])
    if top3:
        result["details"].append(f"PE最高: {', '.join([x['name'] for x in top3])}")
    if bot3:
        result["details"].append(f"PE最低: {', '.join([x['name'] for x in bot3])}")

    return result


# ═══════════════════════════════════════════════════════
#  综合概率模型
# ═══════════════════════════════════════════════════════

def analyze_super_cycle(data: dict) -> dict:
    """超级周期深度分析 —— 存储行业供需格局、周期位置判断"""
    result = {"score": 50, "details": [], "warnings": [], "cycle_position": "未知"}

    fin = data.get("financial", {})
    la = fin.get("latest_annual", {}) if fin else {}
    lq = fin.get("latest_quarter", {}) if fin else {}
    pa = fin.get("prev_annual", {}) if fin else {}

    # ── 周期位置判断（基于毛利率和营收趋势） ──
    # 存储行业特征：谷底毛利率 10-15%，景气期 25-35%，过热期 >35%
    gm = la.get("gross_margin", 0) or 0
    rev_g = la.get("rev_growth", 0) or 0
    profit_g = la.get("profit_growth", 0) or 0

    if gm < 15 and rev_g < 10:
        result["cycle_position"] = "周期谷底 ⬇️"
        result["details"].append("毛利率低位、营收低增 → 典型周期底部特征")
        result["details"].append("存储颗粒价格处于低位，等待供需反转")
        result["score"] = 35
    elif gm < 20 and rev_g > 15:
        result["cycle_position"] = "景气复苏初期 ↗️"
        result["details"].append(f"毛利率 {gm:.1f}% 仍偏低但营收增长 {rev_g:.1f}% → 量升价稳阶段")
        result["details"].append("下游需求回暖，库存去化接近尾声")
        result["score"] = 55
    elif 20 <= gm < 28 and rev_g > 20:
        result["cycle_position"] = "景气上行中期 🔺"
        result["details"].append(f"毛利率 {gm:.1f}% 突破20%、营收增速 {rev_g:.1f}% → 量价齐升")
        result["details"].append("存储涨价周期确认，产能利用率提升")
        result["score"] = 75
    elif gm >= 28 and profit_g > 50:
        result["cycle_position"] = "景气高峰期 🔴"
        result["details"].append(f"毛利率 {gm:.1f}% 高位、利润暴增 {profit_g:.1f}%")
        result["details"].append("⚠️ 关注产能扩张信号，警惕周期拐点")
        result["score"] = 65
        result["warnings"].append("景气高位，需关注供给端扩产节奏")
    elif gm >= 20 and rev_g < 5:
        result["cycle_position"] = "景气见顶回落 ⬇️"
        result["details"].append(f"毛利率仍高但营收增速骤降 → 可能进入下行通道")
        result["score"] = 30
        result["warnings"].append("警惕周期下行风险")

    # ── 供需分析（基于财务数据推断） ──
    if la:
        inventory_ratio = la.get("inventory_turnover", 0) or 0
        if inventory_ratio < 1.5:
            result["details"].append(f"存货周转率低 ({inventory_ratio:.1f}) → 可能库存积压")
        elif inventory_ratio > 3:
            result["details"].append(f"存货周转快 ({inventory_ratio:.1f}) → 产品供不应求")

        debt = la.get("debt_ratio", 0) or 0
        if debt > 60:
            result["details"].append(f"负债率 {debt:.0f}% → 扩产期特征，资本开支大")

    # ── Q1爆发分析 ──
    if lq and lq.get("profit_growth") and lq["profit_growth"] > 1000:
        result["details"].append("⚠️ Q1利润增速异常 (>1000%) → 可能含一次性收益，需确认持续性")
        result["warnings"].append("剔除一次性因素后重新评估利润质量")

    return result


def analyze_quarterly_forecast(data: dict) -> dict:
    """季度业绩预测 —— 基于历史季节性 + 行业趋势外推"""
    result = {"score": 50, "details": [], "forecast": {}}

    fin = data.get("financial", {})
    fc = data.get("forecast", [])
    la = fin.get("latest_annual", {}) if fin else {}
    lq = fin.get("latest_quarter", {}) if fin else {}

    # ── 全年预测 vs 当前进度 ──
    if fc and la:
        fwd_eps = fc[0].get("eps_mean", 0) if len(fc) > 0 else 0
        latest_eps = la.get("eps", 0) or 0
        if fwd_eps and latest_eps:
            growth_implied = (fwd_eps / latest_eps - 1) * 100
            result["details"].append(f"2026E EPS {fwd_eps} vs 2025 {latest_eps} → 隐含增速 {growth_implied:.0f}%")
            result["forecast"]["eps_growth_implied"] = round(growth_implied, 1)

    # ── Q1已完成进度 ──
    if lq and fc:
        q1_eps = lq.get("eps", 0) or 0
        fwd_eps = fc[0].get("eps_mean", 0) if len(fc) > 0 else 0
        if q1_eps and fwd_eps:
            q1_completion = q1_eps / fwd_eps * 100
            result["details"].append(f"Q1 EPS {q1_eps} → 完成全年预测 {q1_completion:.0f}%")
            result["forecast"]["q1_completion_pct"] = round(q1_completion, 1)
            if q1_completion > 35:
                result["details"].append("⚠️ Q1占比过高，全年预测可能大幅上修")
                result["score"] = 75
            elif q1_completion > 25:
                result["details"].append("Q1进度正常偏快")
                result["score"] = 60
            else:
                result["score"] = 45

    # ── 机构盈利预测变化趋势 ──
    if fc and len(fc) >= 2:
        eps_cur = fc[0].get("eps_mean", 0)
        eps_prev = fc[1].get("eps_mean", 0)
        if eps_cur and eps_prev and eps_prev != 0:
            trend = (eps_cur / eps_prev - 1) * 100
            direction = "上调" if trend > 0 else "下调"
            result["details"].append(f"EPS预测趋势: {direction} {abs(trend):.0f}% (今年vs明年)")
            result["forecast"]["eps_trend_pct"] = round(trend, 1)
            if trend > 10: result["score"] += 15
            elif trend < -10: result["score"] -= 10

    result["score"] = max(0, min(100, result["score"]))
    return result


def analyze_institutional_deep(data: dict) -> dict:
    """机构调研深度分析 —— 调研时点、核心关注、公司态度"""
    result = {"score": 50, "details": [], "key_topics": [], "recent_activity": "无"}

    rs = data.get("research", {})
    if not rs:
        result["details"].append("无机构调研数据")
        return result

    reports = rs.get("recent_reports", [])
    total = rs.get("total", 0)
    recent_month = rs.get("recent_month_count", 0)

    # ── 调研活跃度 ──
    if recent_month >= 5:
        result["recent_activity"] = "密集调研 🔥"
        result["score"] += 15
        result["details"].append(f"近一月 {recent_month} 篇研报 → 机构高度关注")
    elif recent_month >= 2:
        result["recent_activity"] = "正常关注"
        result["score"] += 5
        result["details"].append(f"近一月 {recent_month} 篇研报 → 机构正常关注")
    else:
        result["recent_activity"] = "关注度低"
        result["details"].append("近一月研报较少 → 市场关注度偏低")

    # ── 评级分布 ──
    rating_dist = rs.get("rating_distribution", {})
    total_rated = sum(rating_dist.values())
    if total_rated > 0:
        bull_ratio = (rating_dist.get("买入", 0) + rating_dist.get("增持", 0)) / total_rated
        if bull_ratio >= 0.9:
            result["score"] += 15
            result["details"].append(f"一致看多 (买入+增持 {bull_ratio:.0%})")
        elif bull_ratio >= 0.6:
            result["score"] += 8
            result["details"].append(f"偏乐观 (看多 {bull_ratio:.0%})")

    # ── 从研报标题提取核心议题 ──
    topic_keywords = {
        "存储涨价": ["涨价", "价格", "景气", "上行"],
        "企业级业务": ["企业级", "服务器", "数据中心"],
        "自研芯片": ["自研", "芯片", "主控"],
        "全球布局": ["全球", "海外", "出海", "国际化"],
        "业绩爆发": ["爆发", "高增", "加速", "拐点"],
        "端侧AI": ["端侧", "AI", "智能", "应用"],
    }
    topic_count = {}
    for report in reports:
        title = report.get("title", "")
        for topic, kws in topic_keywords.items():
            if any(kw in title for kw in kws):
                topic_count[topic] = topic_count.get(topic, 0) + 1

    result["key_topics"] = sorted(topic_count.items(), key=lambda x: -x[1])
    if result["key_topics"]:
        top_topics = ", ".join([f"{t}({c}次)" for t, c in result["key_topics"][:5]])
        result["details"].append(f"核心议题: {top_topics}")

    result["score"] = max(0, min(100, result["score"]))
    return result


# ═══════════════════════════════════════════════════════
#  综合概率模型 (新权重体系)
# ═══════════════════════════════════════════════════════

def comprehensive_probability(data: dict) -> dict:
    """综合评估 —— 5 大维度新权重:

    业绩基本面    35%  |  营收/利润/ROE/毛利/现金流/超级周期/季度预测/估值匹配
    板块热度      25%  |  半导体/存储板块资金+涨幅排名
    大资金/机构   15%  |  北向资金+机构评级+调研深度+股东筹码
    技术B1策略    15%  |  均线+MACD+KDJ (策略匹配待用户定义)
    大盘/估值     10%  |  市场环境+行业PE对比+远期估值
    """

    print(f"\n{'='*70}")
    print(f"  📐 5 维度分析中...")
    print(f"{'='*70}")

    results = {}

    # ── 维度1: 业绩基本面 (35%) ──
    results["financial"]        = analyze_financial(data)
    results["super_cycle"]      = analyze_super_cycle(data)
    results["quarterly_fcast"]  = analyze_quarterly_forecast(data)

    # 基本面综合 = 财报×0.5 + 超级周期×0.3 + 季度预测×0.2
    fundamental_score = (
        results["financial"]["score"] * 0.50 +
        results["super_cycle"]["score"] * 0.30 +
        results["quarterly_fcast"]["score"] * 0.20
    )
    results["fundamental_composite"] = {"score": round(fundamental_score, 1)}

    # ── 维度2: 板块热度 (25%) ──
    results["sector_flow"]      = analyze_sector_flow(data)

    # ── 维度3: 大资金/机构动向 (15%) ──
    results["market_trend"]     = analyze_market_trend(data)
    results["institutional"]    = analyze_institutional_deep(data)
    results["sentiment"]        = analyze_sentiment(data)

    # 大资金综合 = 北向×0.3 + 机构深度×0.3 + 筹码×0.4
    capital_score = (
        results["market_trend"]["score"] * 0.30 +
        results["institutional"]["score"] * 0.30 +
        results["sentiment"]["score"] * 0.40
    )
    results["capital_composite"] = {"score": round(capital_score, 1)}

    # ── 维度4: 技术B1策略 (15%) ──
    results["technical"]        = analyze_technical(data)

    # ── 维度5: 大盘/估值 (10%) ──
    results["valuation"]        = analyze_valuation(data)
    results["industry_compare"] = analyze_industry_compare(data)

    # 估值综合 = 个股估值×0.6 + 行业对比×0.4
    val_score = (
        results["valuation"]["score"] * 0.60 +
        results["industry_compare"]["score"] * 0.40
    )
    results["valuation_composite"] = {"score": round(val_score, 1)}

    # ── 加权汇总 ──
    weights = {
        "fundamental":    0.35,   # 业绩基本面
        "sector_heat":    0.25,   # 板块热度
        "capital_flow":   0.15,   # 大资金/机构
        "technical_b1":   0.15,   # 技术B1策略
        "market_val":     0.10,   # 大盘/估值
    }

    dim_scores = {
        "fundamental":    fundamental_score,
        "sector_heat":    results["sector_flow"]["score"],
        "capital_flow":   capital_score,
        "technical_b1":   results["technical"]["score"],
        "market_val":     val_score,
    }

    total_score = sum(dim_scores[k] * weights[k] for k in weights)

    # ── 概率映射 ──
    up_prob_base = 25 + total_score * 0.55

    targets = {
        "短期 (1-2周)": {
            "up": round(up_prob_base * 0.75 + dim_scores["technical_b1"] * 0.15 + dim_scores["sector_heat"] * 0.10, 1),
            "note": "板块热度+技术面驱动"
        },
        "中期 (1-3月)": {
            "up": round(up_prob_base * 0.85 + dim_scores["capital_flow"] * 0.10 + dim_scores["sector_heat"] * 0.05, 1),
            "note": "资金+板块驱动"
        },
        "长期 (6-12月)": {
            "up": round(up_prob_base * 0.6 + dim_scores["fundamental"] * 0.35 + dim_scores["market_val"] * 0.05, 1),
            "note": "基本面驱动为主"
        },
    }
    for t in targets:
        targets[t]["up"] = min(90, max(10, targets[t]["up"]))

    # ── 评级 ──
    if total_score >= 78:    rating = "强烈推荐"; stars = "★★★★★"
    elif total_score >= 65:  rating = "推荐"; stars = "★★★★"
    elif total_score >= 55:  rating = "谨慎推荐"; stars = "★★★"
    elif total_score >= 45:  rating = "中性观望"; stars = "★★"
    elif total_score >= 35:  rating = "谨慎回避"; stars = "★"
    else:                    rating = "回避"; stars = "☆"

    # ── 趋势票自动调整 ──
    # 如果基本面得分 > 75 且板块热度 > 65 → 趋势票，上调基本面权重
    if fundamental_score > 75 and results["sector_flow"]["score"] > 65:
        total_score_adjusted = total_score * 1.05  # 趋势票加成 5%
        note_trend = "检测到趋势票特征 → 基本面上调"
    else:
        total_score_adjusted = total_score
        note_trend = ""

    return {
        "total_score": round(total_score_adjusted, 1),
        "raw_score": round(total_score, 1),
        "rating": rating, "stars": stars,
        "trend_boost": note_trend,
        "dimension_scores": {k: round(v, 1) for k, v in dim_scores.items()},
        "weights": weights,
        "probabilities": targets,
        "details": results,
        "sub_details": {
            "fundamental_breakdown": {
                "financial": results["financial"]["score"],
                "super_cycle": results["super_cycle"]["score"],
                "quarterly_fcast": results["quarterly_fcast"]["score"],
                "cycle_position": results["super_cycle"].get("cycle_position", ""),
            },
            "capital_breakdown": {
                "northbound": results["market_trend"]["score"],
                "institutional": results["institutional"]["score"],
                "holders": results["sentiment"]["score"],
            },
        },
    }


# ═══════════════════════════════════════════════════════
#  输出
# ═══════════════════════════════════════════════════════

def safe_float(val) -> float | None:
    """安全转 float，自动处理 百分比/亿/万 等后缀"""
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            if np.isnan(val) or np.isinf(val):
                return None
            return float(val)
        s = str(val).strip()
        if not s or s.lower() in ("false", "true", "none", "nan", ""):
            return None
        # 处理百分比
        if s.endswith("%"):
            return float(s[:-1])
        # 处理单位
        multiplier = 1
        if "亿" in s:
            multiplier = 1e8
            s = s.replace("亿", "")
        elif "万" in s:
            multiplier = 1e4
            s = s.replace("万", "")
        v = float(s) * multiplier
        if np.isnan(v) or np.isinf(v):
            return None
        return v
    except (ValueError, TypeError):
        return None


def print_report(result: dict, data: dict) -> None:
    """打印综合分析报告"""
    d = result["details"]

    # ═══ 头部 ═══
    kl = data.get("kline", {})
    lt = kl.get("latest", {})
    ind = kl.get("indicators", {})
    price = lt.get("close", 0)
    ma20 = ind.get("ma20", "N/A") or 0
    ma60 = ind.get("ma60", "N/A") or 0

    print(f"\n{'='*70}")
    print(f"  📊 江波龙 (301308) 综合量化分析报告")
    ma20_str = f"MA20: {ma20:.2f}" if ma20 else ""
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  收盘: {price:.2f}  |  {ma20_str}")
    print(f"{'='*70}")

    # ═══ 综合评等 ═══
    stars = result.get("stars", "")
    rating = result.get("rating", "")
    boost = result.get("trend_boost", "")
    print(f"\n  🎯 综合评分: {result['total_score']:.1f}/100  {stars}  {rating}")
    if boost:
        print(f"     {boost}")
    print(f"  ┌{'─'*64}┐")

    dims = result["dimension_scores"]
    wts = result["weights"]
    labels_config = {
        "fundamental":    ("📊 业绩基本面",    "财报+超级周期+季度预测+估值匹配"),
        "sector_heat":    ("🔥 板块热度",      "半导体/存储板块资金+涨幅"),
        "capital_flow":   ("💰 大资金/机构",   "北向+机构评级+筹码集中度"),
        "technical_b1":   ("📈 技术B1策略",    "均线/MACD/KDJ (策略待定义)"),
        "market_val":     ("🌏 大盘/估值",     "市场环境+行业PE+远期估值"),
    }
    for key, (label, subs) in labels_config.items():
        score = dims[key]
        bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
        w = wts[key]
        contrib = score * w
        print(f"  │ {label:<10} {bar} {score:3.0f} ×{w:.0%} = {contrib:4.1f}  ({subs})")
    print(f"  ├{'─'*64}┤")
    total_check = sum(dims[k] * wts[k] for k in wts)
    print(f"  │ {'合计':>10}                         = {total_check:4.1f} / 100")
    print(f"  └{'─'*64}┘")

    # ═══ 分维度细节 ═══
    # ═══ 维度1: 业绩基本面 ═══
    fin = d["financial"]
    sc = d.get("super_cycle", {})
    qf = d.get("quarterly_fcast", {})
    fc = data.get("forecast", [])

    print(f"\n{'─'*70}")
    print(f"  📊 业绩基本面 (得分: {d['fundamental_composite']['score']:.0f})")
    print(f"     财报:{fin['score']}  超级周期:{sc.get('score',50)}  季度预测:{qf.get('score',50)}")
    print(f"     周期位置: {sc.get('cycle_position', '未知')}")
    for item in fin["details"]:
        print(f"     ✓ {item}")
    for item in sc.get("details", []):
        print(f"     🔄 {item}")
    for item in qf.get("details", []):
        print(f"     🔮 {item}")
    for w in fin["warnings"]:
        print(f"     ⚠ {w}")
    for w in sc.get("warnings", []):
        print(f"     ⚠ {w}")
    if fc:
        print(f"\n  🔮 盈利预测 (EPS)")
        for row in fc:
            yr = row.get("年度", "")
            lo = safe_float(row.get("最小值"))
            avg = safe_float(row.get("均值"))
            hi = safe_float(row.get("最大值"))
            n = row.get("预测机构数", "?")
            if avg:
                fwd_pe_yr = round(price / avg, 1) if avg > 0 else "N/A"
                print(f"     {yr}: 均值 {avg:.2f}  ({lo:.2f}~{hi:.2f})  |  {n}家机构  |  对应PE: {fwd_pe_yr}")

    # ═══ 维度2: 板块热度 ═══
    sflow = d.get("sector_flow", {})
    print(f"\n{'─'*70}")
    print(f"  🔥 板块热度 (得分: {sflow.get('score', 50)})")
    for item in sflow.get("details", []):
        print(f"     {item}")
    for w in sflow.get("warnings", []):
        print(f"     ⚠ {w}")

    # ═══ 维度3: 大资金/机构 ═══
    cap = d.get("capital_composite", {})
    inst = d.get("institutional", {})
    mkt = d.get("market_trend", {})
    sent = d.get("sentiment", {})

    print(f"\n{'─'*70}")
    print(f"  💰 大资金/机构动向 (得分: {cap.get('score', 50):.0f})")
    print(f"     北向:{mkt.get('score', 50)}  机构:{inst.get('score', 50)}  筹码:{sent.get('score', 50)}")
    for item in mkt.get("details", []):
        print(f"     🌏 {item}")
    for item in inst.get("details", []):
        print(f"     📋 {item}")
    if inst.get("key_topics"):
        topics = ", ".join([f"{t}({c})" for t, c in inst["key_topics"][:5]])
        print(f"     核心议题: {topics}")
    if inst.get("reports"):
        for r in inst["reports"][:3]:
            print(f"     [{r['date']}] {r['org']}: {r['title'][:45]} ({r['rating']})")
    for item in sent.get("details", []):
        print(f"     👥 {item}")
    for w in sent.get("warnings", []):
        print(f"     ⚠ {w}")
    trend = sent.get("holder_count_trend")
    if trend and trend.get("current"):
        y_c = trend.get("y_change", 0)
        print(f"     股东: {trend['current']:,}户  同比{'↑' if y_c>0 else '↓'}{abs(y_c):.1f}%")

    # ═══ 维度4: 技术B1 ═══
    tech = d["technical"]
    print(f"\n{'─'*70}")
    print(f"  📈 技术B1策略 (得分: {tech['score']})  ⚙️ 策略待定义")
    for s in tech.get("signals", []):
        print(f"     • {s}")
    for w in tech.get("warnings", []):
        print(f"     ⚠ {w}")
    if "ret_5d" in tech:
        print(f"     近5日: {tech['ret_5d']:+.1f}%  近20日: {tech['ret_20d']:+.1f}%")

    # ═══ 维度5: 大盘/估值 ═══
    val = d["valuation"]
    ind_cmp = d.get("industry_compare", {})
    print(f"\n{'─'*70}")
    print(f"  🌏 大盘/估值 (得分: {d['valuation_composite']['score']:.0f})")
    print(f"     估值:{val['score']}  行业:{ind_cmp.get('score', 50)}")
    price_str = f"当前价: {price:.2f}"
    if val.get("pe"):   price_str += f"  |  静态PE: {val['pe']:.1f}"
    if val.get("fwd_pe"): price_str += f"  |  远期PE: {val['fwd_pe']:.1f}"
    if val.get("pb"):   price_str += f"  |  PB: {val['pb']:.1f}"
    print(f"     {price_str}")
    print(f"     评估: {val.get('assessment', 'N/A')}")
    for item in ind_cmp.get("details", []):
        print(f"     📊 {item}")

    # ═══ 概率预测 ═══
    print(f"\n{'='*70}")
    print(f"  🎲 未来股价走势概率预测")
    print(f"{'='*70}")
    print(f"  ┌{'─'*55}┐")
    for period, prob in result["probabilities"].items():
        up = prob["up"]
        down = 100 - up
        up_bar = "🟢" * int(up / 10) + "⚪" * (10 - int(up / 10))
        print(f"  │ {period:<15}  上涨 {up:4.1f}%  │  {up_bar}  │  ({prob['note']})")
    print(f"  └{'─'*55}┘")

    print(f"\n  ⚠️ 免责声明: 以上分析仅基于公开数据的量化模型，不构成投资建议。")


# ═══════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="股票综合概率分析")
    parser.add_argument("symbol", nargs="?", default="301308", help="股票代码（默认 301308 江波龙）")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    # 使用 stock_data 采集器获取结构化数据
    from stock_data import collect as collect_data
    data = collect_data(args.symbol)
    result = comprehensive_probability(data)

    if args.json:
        # 输出结构化 JSON 供后续分析
        out = {
            "symbol": args.symbol,
            "date": datetime.now().isoformat(),
            "price": float(data["kline"]["latest"]["close"]),
            "total_score": result["total_score"],
            "rating": result.get("rating", ""),
            "stars": result.get("stars", ""),
            "dimension_scores": result["dimension_scores"],
            "weights": {k: round(v, 2) for k, v in result["weights"].items()},
            "probabilities": result["probabilities"],
            "details": {
                "financial": {
                    "score": result["details"]["financial"]["score"],
                    "sub_scores": result["details"]["financial"].get("sub_scores", {}),
                    "details": result["details"]["financial"]["details"],
                    "warnings": result["details"]["financial"]["warnings"],
                },
                "valuation": {
                    "score": result["details"]["valuation"]["score"],
                    "pe": result["details"]["valuation"].get("pe"),
                    "fwd_pe": result["details"]["valuation"].get("fwd_pe"),
                    "pb": result["details"]["valuation"].get("pb"),
                    "assessment": result["details"]["valuation"].get("assessment"),
                    "sub_scores": {str(k): v for k, v in result["details"]["valuation"].get("sub_scores", {}).items()},
                },
                "institutional": {
                    "score": result["details"]["institutional"]["score"],
                    "rating_dist": result["details"]["institutional"]["rating_dist"],
                    "recent_signal": result["details"]["institutional"]["recent_signal"],
                    "reports": result["details"]["institutional"]["reports"],
                },
                "technical": {
                    "score": result["details"]["technical"]["score"],
                    "signals": result["details"]["technical"]["signals"],
                    "warnings": result["details"]["technical"]["warnings"],
                },
                "sentiment": {
                    "score": result["details"]["sentiment"]["score"],
                    "holder_count_trend": result["details"]["sentiment"].get("holder_count_trend"),
                    "details": result["details"]["sentiment"]["details"],
                    "warnings": result["details"]["sentiment"]["warnings"],
                },
            },
            # 原始关键数据供参考
            "raw_summary": {
                "latest_annual_eps": _get_latest_eps(data),
                "forecast": _get_forecast_summary(data),
            }
        }
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    else:
        print_report(result, data)


def _get_latest_eps(data: dict) -> dict | None:
    """提取最近年报关键数据"""
    df = data.get("financial")
    if df is None:
        return None
    df = df.copy()
    df["报告期_dt"] = pd.to_datetime(df["报告期"], errors="coerce")
    df = df.sort_values("报告期_dt", ascending=False)
    annual = df[df["报告期"].str.contains("-12-31", na=False)]
    if len(annual) == 0:
        return None
    latest = annual.iloc[0]
    return {
        "report_date": str(la.get("报告期", "")),
        "revenue": safe_float(la.get("营业总收入")),
        "rev_growth": safe_float(la.get("营业总收入同比增长率")),
        "profit": safe_float(la.get("净利润")),
        "profit_growth": safe_float(la.get("净利润同比增长率")),
        "eps": safe_float(la.get("基本每股收益")),
        "roe": safe_float(la.get("净资产收益率")),
        "gross_margin": safe_float(la.get("销售毛利率")),
        "debt_ratio": safe_float(la.get("资产负债率")),
    }


def _get_forecast_summary(data: dict) -> list | None:
    """盈利预测摘要"""
    fc = data.get("forecast")
    if fc is None:
        return None
    result = []
    for _, row in fc.iterrows():
        result.append({
            "year": str(row.get("年度", "")),
            "min": safe_float(row.get("最小值")),
            "mean": safe_float(row.get("均值")),
            "max": safe_float(row.get("最大值")),
            "institutions": row.get("预测机构数", 0),
        })
    return result
