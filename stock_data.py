#!/usr/bin/env python3
"""股票数据采集器 —— 一键拉取 K线/财报/PE/机构/板块/资金/股东 全维度数据

用法:
    python stock_data.py                # 默认江波龙，打印摘要
    python stock_data.py 000001         # 其他股票
    python stock_data.py --json         # 输出 JSON 供 AI 深度分析
    python stock_data.py -o data.json   # 保存到文件
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_stock_kline import fetch_kline, compute_kdj, compute_macd

try:
    import akshare as ak
except ImportError:
    print("❌ 需要安装 akshare: pip install akshare")
    sys.exit(1)


# ═══════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════

def sf(val):
    """安全转 float，处理 %/亿/万 后缀"""
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            return float(val) if not (np.isnan(val) or np.isinf(val)) else None
        s = str(val).strip()
        if not s or s.lower() in ("false", "true", "none", "nan", ""):
            return None
        if s.endswith("%"):
            return float(s[:-1])
        mult = 1
        if "亿" in s: mult = 1e8; s = s.replace("亿", "")
        elif "万" in s: mult = 1e4; s = s.replace("万", "")
        v = float(s) * mult
        return v if not (np.isnan(v) or np.isinf(v)) else None
    except (ValueError, TypeError):
        return None


def safe_fetch(fn, label):
    try:
        return fn()
    except Exception as e:
        print(f"  ⚠️ {label}: {str(e)[:60]}", file=sys.stderr)
        return None


# ═══════════════════════════════════════════════════════
#  数据采集
# ═══════════════════════════════════════════════════════

def collect(symbol: str) -> dict:
    """采集所有可用数据，返回结构化字典"""
    t0 = datetime.now()
    data = {"symbol": symbol, "fetch_time": t0.isoformat()}

    em_code = f"SZ{symbol}" if not symbol.startswith("6") else f"SH{symbol}"
    sina_code = f"sz{symbol}" if not symbol.startswith("6") else f"sh{symbol}"

    # ── 1. K线 + 技术指标 ──
    print("📈 K线...", end=" ", flush=True)
    df = fetch_kline(symbol)
    df = compute_kdj(df)
    df = compute_macd(df)
    for ma in [5, 10, 20, 60, 120, 250]:
        df[f"MA{ma}"] = df["close"].rolling(ma).mean()
    data["kline"] = _kline_summary(df)

    # ── 2. 财务摘要 ──
    print("📊 财报...", end=" ", flush=True)
    df_fin = safe_fetch(
        lambda: ak.stock_financial_abstract_ths(symbol=symbol, indicator="按报告期"),
        "财务摘要")
    data["financial"] = _financial_summary(df_fin) if df_fin is not None else None

    # ── 3. 盈利预测 ──
    print("🔮 预测...", end=" ", flush=True)
    df_fc = safe_fetch(
        lambda: ak.stock_profit_forecast_ths(symbol=symbol, indicator="预测年报每股收益"),
        "盈利预测")
    data["forecast"] = _forecast_summary(df_fc) if df_fc is not None else None

    # ── 4. 机构调研 ──
    print("📋 机构...", end=" ", flush=True)
    df_r = safe_fetch(lambda: ak.stock_research_report_em(symbol=symbol), "机构调研")
    data["research"] = _research_summary(df_r) if df_r is not None else None

    # ── 5. 股东人数 ──
    print("👥 股东...", end=" ", flush=True)
    df_h = safe_fetch(lambda: ak.stock_main_stock_holder(stock=symbol), "股东人数")
    data["holders"] = _holder_summary(df_h) if df_h is not None else None

    # ── 6. 股东增减持 ──
    df_hc = safe_fetch(lambda: ak.stock_shareholder_change_ths(symbol=symbol), "增减持")
    data["insider_trades"] = _insider_summary(df_hc) if df_hc is not None else None

    # ── 7. 概念板块资金 ──
    print("🔥 板块...", end=" ", flush=True)
    df_sf = safe_fetch(
        lambda: ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="概念资金流"),
        "板块资金")
    data["sector_flow"] = _sector_summary(df_sf) if df_sf is not None else None

    # ── 8. 北向资金 ──
    print("🌏 北向...", end=" ", flush=True)
    df_nb = safe_fetch(lambda: ak.stock_hsgt_fund_flow_summary_em(), "北向资金")
    data["northbound"] = _northbound_summary(df_nb) if df_nb is not None else None

    # ── 9. 行业PE ──
    print("📊 行业...", end=" ", flush=True)
    today = datetime.now().strftime("%Y%m%d")
    df_ip = safe_fetch(
        lambda: ak.stock_industry_pe_ratio_cninfo(symbol="证监会行业分类", date=today),
        "行业PE")
    data["industry_pe"] = _industry_pe_summary(df_ip) if df_ip is not None else None

    # ── 10. 资金流向(个股) ──
    print("💰 资金...", end=" ", flush=True)
    try:
        df_ff = ak.stock_individual_fund_flow(stock=symbol, market="sz" if not symbol.startswith("6") else "sh")
        data["fund_flow"] = _fund_flow_summary(df_ff)
    except Exception:
        data["fund_flow"] = None

    elapsed = (datetime.now() - t0).total_seconds()
    data["elapsed_sec"] = round(elapsed, 1)
    print(f"✅ {elapsed:.0f}s", flush=True)
    return data


# ═══════════════════════════════════════════════════════
#  各维度摘要提取
# ═══════════════════════════════════════════════════════

def _kline_summary(df: pd.DataFrame) -> dict:
    """K线数据摘要 + 最近100条用于画图"""
    last = df.iloc[-1]
    n = len(df)
    return {
        "count": n,
        "date_range": [str(df["date"].iloc[0])[:10], str(df["date"].iloc[-1])[:10]],
        "latest": {
            "date": str(last["date"])[:10],
            "open": sf(last["open"]), "high": sf(last["high"]),
            "low": sf(last["low"]), "close": sf(last["close"]),
            "volume": sf(last["volume"]),
        },
        "indicators": {
            "ma5": sf(last.get("MA5")), "ma10": sf(last.get("MA10")),
            "ma20": sf(last.get("MA20")), "ma60": sf(last.get("MA60")),
            "ma120": sf(last.get("MA120")), "ma250": sf(last.get("MA250")),
            "K": sf(last.get("K")), "D": sf(last.get("D")), "J": sf(last.get("J")),
            "DIF": sf(last.get("DIF")), "DEA": sf(last.get("DEA")), "MACD": sf(last.get("MACD")),
        },
        "returns": {
            "5d": _calc_return(df, -6, -1),
            "10d": _calc_return(df, -11, -1),
            "20d": _calc_return(df, -21, -1),
            "60d": _calc_return(df, -61, -1),
        },
        # 最近100天精简数据供画图
        "recent_100": [
            {
                "d": str(r["date"])[:10],
                "o": sf(r["open"]), "c": sf(r["close"]),
                "h": sf(r["high"]), "l": sf(r["low"]),
                "v": sf(r["volume"]),
                "K": sf(r.get("K")), "D": sf(r.get("D")), "J": sf(r.get("J")),
                "DIF": sf(r.get("DIF")), "DEA": sf(r.get("DEA")), "MACD": sf(r.get("MACD")),
            }
            for _, r in df.tail(100).iterrows()
        ],
    }


def _calc_return(df, start_offset, end_offset):
    """计算区间收益率"""
    if len(df) < abs(start_offset):
        return None
    c0 = df["close"].iloc[start_offset]
    c1 = df["close"].iloc[end_offset]
    return round((c1 / c0 - 1) * 100, 2) if c0 and c0 > 0 else None


def _financial_summary(df: pd.DataFrame) -> dict:
    """提取财报关键指标"""
    df = df.copy()
    df["dt"] = pd.to_datetime(df["报告期"], errors="coerce")
    df = df.sort_values("dt", ascending=False).reset_index(drop=True)

    annual = df[df["报告期"].str.contains("-12-31", na=False)]
    latest_annual = annual.iloc[0] if len(annual) > 0 else None
    prev_annual = annual.iloc[1] if len(annual) > 1 else None

    # 最新季报（可能是Q1/Q2/Q3）
    latest_q = df.iloc[0] if not df.iloc[0]["报告期"].endswith("12-31") else None

    result = {"report_count": len(df)}

    if latest_annual is not None:
        la = latest_annual
        eps = sf(la.get("基本每股收益"))
        result["latest_annual"] = {
            "report_date": str(la["报告期"])[:10],
            "revenue": sf(la.get("营业总收入")),
            "rev_growth": sf(la.get("营业总收入同比增长率")),
            "profit": sf(la.get("净利润")),
            "profit_growth": sf(la.get("净利润同比增长率")),
            "deducted_profit": sf(la.get("扣非净利润")),
            "deducted_growth": sf(la.get("扣非净利润同比增长率")),
            "eps": eps,
            "bvps": sf(la.get("每股净资产")),
            "cfps": sf(la.get("每股经营现金流")),
            "roe": sf(la.get("净资产收益率")),
            "gross_margin": sf(la.get("销售毛利率")),
            "net_margin": sf(la.get("销售净利率")),
            "debt_ratio": sf(la.get("资产负债率")),
            "current_ratio": sf(la.get("流动比率")),
            "quick_ratio": sf(la.get("速动比率")),
            "inventory_turnover": sf(la.get("存货周转率")),
            "receivable_turnover_days": sf(la.get("应收账款周转天数")),
        }

    if prev_annual is not None:
        result["prev_annual"] = {
            "report_date": str(prev_annual["报告期"])[:10],
            "revenue": sf(prev_annual.get("营业总收入")),
            "profit": sf(prev_annual.get("净利润")),
            "eps": sf(prev_annual.get("基本每股收益")),
            "roe": sf(prev_annual.get("净资产收益率")),
        }

    if latest_q is not None:
        lq = latest_q
        result["latest_quarter"] = {
            "report_date": str(lq["报告期"])[:10],
            "revenue": sf(lq.get("营业总收入")),
            "rev_growth": sf(lq.get("营业总收入同比增长率")),
            "profit": sf(lq.get("净利润")),
            "profit_growth": sf(lq.get("净利润同比增长率")),
            "eps": sf(lq.get("基本每股收益")),
            "roe": sf(lq.get("净资产收益率")),
        }

    return result


def _forecast_summary(df: pd.DataFrame) -> list:
    """盈利预测"""
    result = []
    for _, row in df.iterrows():
        result.append({
            "year": str(row.get("年度", "")),
            "institutions": int(row.get("预测机构数", 0)),
            "eps_min": sf(row.get("最小值")),
            "eps_mean": sf(row.get("均值")),
            "eps_max": sf(row.get("最大值")),
            "industry_avg": sf(row.get("行业平均数")),
        })
    return result


def _research_summary(df: pd.DataFrame) -> dict:
    """机构调研报告摘要"""
    ratings = {}
    if "东财评级" in df.columns:
        ratings = df["东财评级"].value_counts().to_dict()
    reports = []
    for _, row in df.head(10).iterrows():
        reports.append({
            "date": str(row.get("日期", "")),
            "title": str(row.get("报告名称", "")),
            "rating": str(row.get("东财评级", "")),
            "org": str(row.get("机构", "")),
        })
    return {
        "total": len(df),
        "recent_month_count": int(df["近一月个股研报数"].iloc[0]) if "近一月个股研报数" in df.columns and len(df) > 0 else 0,
        "rating_distribution": ratings,
        "recent_reports": reports[:5],
    }


def _holder_summary(df: pd.DataFrame) -> dict:
    """股东人数趋势"""
    df = df.copy()
    df["dt"] = pd.to_datetime(df["截至日期"], errors="coerce")
    periods = df[["dt", "股东总数", "平均持股数"]].dropna(subset=["股东总数"]).drop_duplicates(subset=["dt"])
    periods = periods.sort_values("dt")

    if len(periods) == 0:
        return {"trend": []}

    trend = []
    for _, row in periods.iterrows():
        trend.append({
            "date": str(row["dt"].date()),
            "total_holders": int(sf(row["股东总数"])),
            "avg_hold": int(sf(row["平均持股数"])) if sf(row.get("平均持股数")) else None,
        })

    # 计算集中度变化
    cur = trend[-1] if trend else None
    prev_y = None
    if cur and len(trend) >= 5:
        cur_date = periods["dt"].iloc[-1]
        year_ago = cur_date - pd.DateOffset(years=1)
        candidates = periods[periods["dt"] <= year_ago]
        if len(candidates) > 0:
            py = candidates.iloc[-1]
            prev_y = {
                "date": str(py["dt"].date()),
                "total_holders": int(sf(py["股东总数"])),
            }

    return {
        "trend": trend,
        "latest": cur,
        "year_ago": prev_y,
        "yoy_change_pct": round((cur["total_holders"] - prev_y["total_holders"]) / prev_y["total_holders"] * 100, 1) if cur and prev_y else None,
    }


def _insider_summary(df: pd.DataFrame) -> dict:
    """股东增减持"""
    recent = df.head(20)
    buys = sells = 0
    trades = []
    for _, row in recent.iterrows():
        qty = sf(row.get("变动数量"))
        if qty and qty > 0:
            buys += 1
        elif qty and qty < 0:
            sells += 1
        trades.append({
            "date": str(row.get("公告日期", "")),
            "holder": str(row.get("变动股东", "")),
            "change_qty": qty,
            "avg_price": sf(row.get("交易均价")),
            "remaining": sf(row.get("剩余股份总数")),
        })

    return {
        "total_records": len(df),
        "recent_20": trades[:10],
        "buy_count": buys,
        "sell_count": sells,
        "net_signal": "增持为主" if buys > sells else "减持为主" if sells > buys else "均衡",
    }


def _sector_summary(df: pd.DataFrame) -> dict:
    """板块资金 —— 筛选与存储/半导体相关的概念"""
    keywords = ["半导体", "存储", "芯片", "内存", "闪存", "SSD", "DRAM", "NAND"]
    matched = []
    seen = set()
    for kw in keywords:
        mask = df["名称"].str.contains(kw, na=False)
        for _, row in df[mask].iterrows():
            name = str(row["名称"])
            if name not in seen:
                seen.add(name)
                matched.append({
                    "name": name,
                    "change_pct": sf(row.get("今日涨跌幅")),
                    "main_inflow": sf(row.get("今日主力净流入-净额")),
                    "main_inflow_pct": sf(row.get("今日主力净流入-净占比")),
                    "super_large_inflow": sf(row.get("今日超大单净流入-净额")),
                })

    # Top 5 热门概念
    top5 = df.head(5)
    top_list = [{"name": str(r["名称"]), "change": sf(r.get("今日涨跌幅")),
                 "inflow": sf(r.get("今日主力净流入-净额"))} for _, r in top5.iterrows()]

    return {
        "concept_count": len(df),
        "relevant_sectors": matched[:8],
        "top5_hot_concepts": top_list,
    }


def _northbound_summary(df: pd.DataFrame) -> dict:
    """北向资金"""
    latest = df.iloc[0] if "交易日" in df.columns else df.iloc[-1]
    return {
        "trade_date": str(latest.get("交易日", "")),
        "net_buy_amount": sf(latest.get("成交净买额")),
        "net_inflow": sf(latest.get("资金净流入")),
        "market_index": str(latest.get("相关指数", "")),
        "index_change": sf(latest.get("指数涨跌幅")),
    }


def _industry_pe_summary(df: pd.DataFrame) -> dict:
    """行业PE对比"""
    # 江波龙所在行业: 计算机、通信和其他电子设备制造业
    target = df[df["行业名称"].str.contains("计算机|通信|电子", na=False)]
    matched = None
    if len(target) > 0:
        row = target.iloc[0]
        matched = {
            "industry_name": str(row["行业名称"]),
            "company_count": int(row["公司数量"]),
            "pe_weighted": sf(row.get("静态市盈率-加权平均")),
            "pe_median": sf(row.get("静态市盈率-中位数")),
            "pe_average": sf(row.get("静态市盈率-算术平均")),
            "total_market_cap": sf(row.get("总市值-静态")),
        }

    # PE 最高/最低行业
    df_valid = df.dropna(subset=["静态市盈率-加权平均"])
    top3 = df_valid.nlargest(3, "静态市盈率-加权平均")
    bottom3 = df_valid.nsmallest(3, "静态市盈率-加权平均")

    return {
        "matched_industry": matched,
        "top3_pe_industries": [{"name": str(r["行业名称"]), "pe": sf(r["静态市盈率-加权平均"])} for _, r in top3.iterrows()],
        "bottom3_pe_industries": [{"name": str(r["行业名称"]), "pe": sf(r["静态市盈率-加权平均"])} for _, r in bottom3.iterrows()],
    }


def _fund_flow_summary(df: pd.DataFrame) -> dict:
    """个股资金流向"""
    if df is None or len(df) == 0:
        return None
    latest = df.iloc[-1] if "日期" in df.columns else df.iloc[0]
    recent = df.tail(5)

    return {
        "latest": {
            "date": str(latest.get("日期", "")),
            "close": sf(latest.get("收盘价")),
            "change_pct": sf(latest.get("涨跌幅")),
            "main_net_inflow": sf(latest.get("主力净流入-净额")),
            "main_net_pct": sf(latest.get("主力净流入-净占比")),
            "super_large_net": sf(latest.get("超大单净流入-净额")),
            "large_net": sf(latest.get("大单净流入-净额")),
        },
        "recent_5d": [
            {
                "date": str(r.get("日期", "")),
                "main_net": sf(r.get("主力净流入-净额")),
                "main_pct": sf(r.get("主力净流入-净占比")),
            }
            for _, r in recent.iterrows()
        ],
    }


# ═══════════════════════════════════════════════════════
#  打印可读摘要
# ═══════════════════════════════════════════════════════

def print_summary(data: dict):
    """终端友好摘要"""
    print(f"\n{'='*60}")
    print(f"  📊 江波龙 (301308) 数据摘要")
    print(f"  🕐 采集时间: {data['fetch_time']}  ({data['elapsed_sec']}s)")
    print(f"{'='*60}")

    # K线
    kl = data.get("kline", {})
    lt = kl.get("latest", {})
    ind = kl.get("indicators", {})
    ret = kl.get("returns", {})
    print(f"\n📈 K线 ({kl.get('count')}条  {kl.get('date_range', ['?','?'])[0]}~{kl.get('date_range', ['?','?'])[1]})")
    print(f"   收盘: {lt.get('close')}  |  近5日: {ret.get('5d'):+}%  近20日: {ret.get('20d'):+}%")
    print(f"   MA5: {ind.get('ma5')}  MA20: {ind.get('ma20')}  MA60: {ind.get('ma60')}")
    print(f"   KDJ: K={ind.get('K')} D={ind.get('D')} J={ind.get('J')}")
    print(f"   MACD: DIF={ind.get('DIF')} DEA={ind.get('DEA')} BAR={ind.get('MACD')}")

    # 财报
    fin = data.get("financial", {})
    la = fin.get("latest_annual", {})
    if la:
        print(f"\n📊 最近年报 ({la.get('report_date')})")
        print(f"   营收: {la.get('revenue')/1e8:.1f}亿 ({la.get('rev_growth'):+}%)")
        print(f"   净利: {la.get('profit')/1e8:.1f}亿 ({la.get('profit_growth'):+}%)")
        print(f"   EPS: {la.get('eps')}  ROE: {la.get('roe')}%  毛利率: {la.get('gross_margin')}%")
        print(f"   负债率: {la.get('debt_ratio')}%  经营现金流/EPS: {la.get('cfps')}/{la.get('eps')}")

    lq = fin.get("latest_quarter", {})
    if lq:
        print(f"\n📊 最新季报 ({lq.get('report_date')})")
        print(f"   营收: {lq.get('revenue')/1e8 if lq.get('revenue') else '?'}亿  "
              f"净利: {lq.get('profit')/1e8 if lq.get('profit') else '?'}亿  "
              f"增速: {lq.get('profit_growth'):+}%")

    # 盈利预测
    fc = data.get("forecast", [])
    if fc:
        print(f"\n🔮 盈利预测")
        for f in fc:
            price = lt.get("close", 0)
            fwd_pe = price / f["eps_mean"] if f["eps_mean"] and price else 0
            print(f"   {f['year']}: EPS {f['eps_mean']} ({f['eps_min']}~{f['eps_max']}) "
                  f"| {f['institutions']}家机构 | 远期PE: {fwd_pe:.1f}")

    # 机构
    rs = data.get("research", {})
    if rs:
        print(f"\n📋 机构调研 ({rs.get('total')}篇)")
        print(f"   评级: {rs.get('rating_distribution', {})}")
        for r in rs.get("recent_reports", [])[:3]:
            print(f"   [{r['date']}] {r['org']}: {r['title'][:40]} ({r['rating']})")

    # 股东
    hd = data.get("holders", {})
    if hd:
        cur = hd.get("latest", {})
        yoy = hd.get("yoy_change_pct")
        print(f"\n👥 股东人数")
        print(f"   当前: {cur.get('total_holders'):,}户  人均: {cur.get('avg_hold'):,}股")
        if yoy is not None:
            print(f"   同比: {'↑' if yoy>0 else '↓'}{abs(yoy):.1f}%  {'⚠️筹码分散' if yoy>20 else '✅筹码集中' if yoy<-10 else ''}")

    # 板块
    sf_data = data.get("sector_flow", {})
    if sf_data:
        print(f"\n🔥 相关板块资金")
        for s in sf_data.get("relevant_sectors", [])[:5]:
            sign = "+" if (s.get("main_inflow") or 0) > 0 else ""
            print(f"   {s['name']}: {s.get('change_pct'):+}%  "
                  f"主力{sign}{s.get('main_inflow')/1e8:.1f}亿")

    # 北向
    nb = data.get("northbound", {})
    if nb:
        nb_amt = nb.get("net_buy_amount", 0) or 0
        print(f"\n🌏 北向资金 ({nb.get('trade_date', '')})")
        print(f"   净买额: {nb_amt/1e8:.1f}亿  |  {nb.get('market_index', '')}: {nb.get('index_change'):+}%")

    # 行业
    ip = data.get("industry_pe", {})
    mi = ip.get("matched_industry", {})
    if mi:
        print(f"\n📊 行业PE: {mi.get('industry_name', '')}")
        print(f"   行业加权PE: {mi.get('pe_weighted')}  中位数PE: {mi.get('pe_median')}")
        print(f"   PE最高行业: {', '.join([x['name'] for x in ip.get('top3_pe_industries', [])])}")
        print(f"   PE最低行业: {', '.join([x['name'] for x in ip.get('bottom3_pe_industries', [])])}")

    # 个股资金
    ff = data.get("fund_flow")
    if ff and ff.get("latest"):
        lf = ff["latest"]
        print(f"\n💰 个股资金 ({lf.get('date', '')})")
        print(f"   主力净流入: {lf.get('main_net_inflow')/1e8:.1f}亿 ({lf.get('main_net_pct'):+}%)")

    print(f"\n{'='*60}")


# ═══════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="股票全维度数据采集器")
    parser.add_argument("symbol", nargs="?", default="301308", help="股票代码（默认 301308 江波龙）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式（供 AI 分析）")
    parser.add_argument("-o", "--output", default=None, help="保存 JSON 到文件")
    parser.add_argument("--compact", action="store_true", help="JSON 不带 recent_100 画图数据")
    args = parser.parse_args()

    data = collect(args.symbol)

    if args.compact and "kline" in data:
        data["kline"].pop("recent_100", None)

    if args.json or args.output:
        json_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        if args.output:
            with open(args.output, "w") as f:
                f.write(json_str)
            print(f"📁 已保存: {args.output}")
        else:
            print(json_str)
    else:
        print_summary(data)
