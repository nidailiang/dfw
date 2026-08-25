#!/usr/bin/env python3
"""基本面 AI 解读报告(第2层, 通用)

用法:
    python collect_data.py 688072 拓荆科技        # 先采集数据
    python analyze_fundamental.py 688072 拓荆科技  # 再 AI 解读

输出:
    stocks/拓荆科技/拓荆科技_分析报告.md

说明:
    - 读取 <中文名>_基本面.json, 组织成提示词, 调用 DeepSeek API(项目已配置)
    - 解读完全由 AI 基于最新数据生成, 无写死判断
    - API 配置来自环境变量 ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN
"""

import argparse
import json
import os
import sys
import urllib.request


# ── 提示词组装 ────────────────────────────────────────────
def _v(v, suffix=""):
    """数值容错: None/False → '—'"""
    if v is None or v is False or (isinstance(v, str) and v == "False"):
        return "—"
    return f"{v}{suffix}"


def build_prompt(data: dict) -> str:
    """把采集的 JSON 数据组织成结构化的提示词"""
    name, code = data.get("symbol", "?"), data.get("symbol", "?")
    kl = data.get("kline", {})
    lt = kl.get("latest", {})
    fin = data.get("financial") or {}
    fc = data.get("forecast") or []
    rs = data.get("research") or {}
    hd = data.get("holders") or {}
    it = data.get("insider_trades") or {}
    ind = data.get("industry_pe") or {}
    ff = data.get("fund_flow") or {}

    la = fin.get("latest_annual") or {}
    lq = fin.get("latest_quarter") or {}
    pa = fin.get("prev_annual") or {}

    # 股东趋势: 最近4期 + 同比
    htrend = (hd.get("trend") or [])[-4:]
    htrend_txt = "\n".join(
        f"  {t['date']}: 股东 {t['total_holders']:,} 户" + (f", 人均 {t['avg_hold']:,} 股" if t.get("avg_hold") else "")
        for t in htrend) or "  —"

    # 增减持: 最近5条
    trades = (it.get("recent_20") or [])[:5]
    trades_txt = "\n".join(
        f"  {t.get('date', '?')} {t.get('holder', '?')} 变动 {_v(t.get('change_qty'))} 股"
        f" (均价 {_v(t.get('avg_price'))}) 剩余 {_v(t.get('remaining'))}"
        for t in trades) or "  —"

    # 研报: 最近5条 + 评级分布
    reports_txt = "\n".join(
        f"  {r.get('date', '?')} {r.get('org', '?')} 评级[{r.get('rating', '?')}] {r.get('title', '')[:40]}"
        for r in (rs.get("recent_reports") or [])) or "  —"

    # 盈利预测
    fc_txt = "\n".join(
        f"  {f.get('year')}年: {f.get('institutions', 0)}家机构  EPS均值 {f.get('eps_mean', '—')}"
        f" (区间 {f.get('eps_min', '—')}~{f.get('eps_max', '—')})  行业平均 {f.get('industry_avg', '—')}"
        for f in fc) or "  —"

    # 资金流(近5日)
    ff_txt = "\n".join(
        f"  {f.get('date', '?')} 主力净流入 {f.get('main_net', '—')}"
        for f in (ff.get("recent_5") or [])) or "  —"

    ind_txt = (f"行业 {ind.get('industry_name', '?')}: 行业PE {ind.get('industry_pe', '—')}"
               if ind else "  —(接口未取到行业PE)")

    p = f"""你是资深 A 股基本面分析师。以下是 {name}({code}) 的客观数据(akshare 公开接口采集), 请给出完整解读报告。

【行情】
最新收盘 {_v(lt.get('close'))} 元 ({_v(lt.get('date'))})
近5/10/20/60日涨跌: {_v(kl.get('returns', {}).get('5d'), '%')} / {_v(kl.get('returns', {}).get('10d'), '%')} / {_v(kl.get('returns', {}).get('20d'), '%')} / {_v(kl.get('returns', {}).get('60d'), '%')}
技术指标 KDJ: K={_v(kl.get('indicators', {}).get('K'))} D={_v(kl.get('indicators', {}).get('D'))} J={_v(kl.get('indicators', {}).get('J'))}
MACD: DIF={_v(kl.get('indicators', {}).get('DIF'))} DEA={_v(kl.get('indicators', {}).get('DEA'))} 柱={_v(kl.get('indicators', {}).get('MACD'))}

【财务·最新年报 {_v(la.get('report_date'))}】
营收 {_v(la.get('revenue'))} (同比 {_v(la.get('rev_growth'), '%')})
净利润 {_v(la.get('profit'))} (同比 {_v(la.get('profit_growth'), '%')})
扣非净利 {_v(la.get('deducted_profit'))} (同比 {_v(la.get('deducted_growth'), '%')})
EPS {_v(la.get('eps'))}  BVPS {_v(la.get('bvps'))}  经营现金流/股 {_v(la.get('cfps'))}
ROE {_v(la.get('roe'), '%')}  毛利率 {_v(la.get('gross_margin'), '%')}  净利率 {_v(la.get('net_margin'), '%')}
资产负债率 {_v(la.get('debt_ratio'), '%')}  流动比率 {_v(la.get('current_ratio'))}  存货周转率 {_v(la.get('inventory_turnover'))}

【财务·上一年度 {_v(pa.get('report_date'))}】
营收 {_v(pa.get('revenue'))}  净利 {_v(pa.get('profit'))}  EPS {_v(pa.get('eps'))}  ROE {_v(pa.get('roe'), '%')}

【财务·最新季度 {_v(lq.get('report_date'))}】
营收 {_v(lq.get('revenue'))} (同比 {_v(lq.get('rev_growth'), '%')})  净利 {_v(lq.get('profit'))} (同比 {_v(lq.get('profit_growth'), '%')})  EPS {_v(lq.get('eps'))}

【机构盈利预测(一致预期)】
{fc_txt}

【机构研报(近5条, 共 {_v(rs.get('total'))} 条, 近一月 {_v(rs.get('recent_month_count'))} 条)】
评级分布: {rs.get('rating_distribution', '—')}
{reports_txt}

【股东结构】
{htrend_txt}
同比变化: {_v(hd.get('yoy_change_pct'), '%')}  (最新 {_v((hd.get('latest') or {}).get('total_holders'))} 户, 去年 {_v((hd.get('year_ago') or {}).get('total_holders'))} 户)

【大股东增减持(近5条)】
{trades_txt}

【资金面(近5日主力净流入)】
{ff_txt}

【行业PE对比】
{ind_txt}

════════════════════════════════════════
请输出 markdown 格式的完整解读报告, 章节:
## 一、盈利质量(利润真实性/含金量: 扣非 vs 净利、现金流、毛利率趋势)
## 二、成长性(营收/利润增速、季度环比、机构一致预期的可信度)
## 三、估值分析(当前价 vs EPS 一致预期 → 动态PE, 对比行业PE, 判断高估/合理/低估)
## 四、机构态度(研报数量/评级分布/近一月热度, 机构预测是否一致)
## 五、股东动向(股东人数变化→筹码集中/分散, 大股东增减持信号)
## 六、风险点(列出最关键的 2-4 个风险, 基于数据, 不要编造)
## 七、综合结论(基本面定性: 强/中/弱 + 一句话总结 + 值得跟踪的关键指标)

规则: 只基于上面给出的数据分析, 严禁编造数据; 缺失的数据写"数据缺失"; 金额单位为亿/万元的原样保留。"""
    return p


# ── API 调用 ─────────────────────────────────────────────
def call_ai(prompt: str) -> str:
    base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic").rstrip("/")
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    model = (os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL")
             or os.environ.get("ANTHROPIC_MODEL") or "deepseek-chat")
    if not token:
        raise SystemExit("❌ 未找到 ANTHROPIC_AUTH_TOKEN 环境变量")

    body = {
        "model": model,
        "max_tokens": 8000,
        "system": "你是资深 A 股基本面分析师, 输出严谨、客观、基于数据的中文分析报告。",
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        base + "/v1/messages",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "x-api-key": token,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        },
    )
    print(f"🤖 正在调用 AI 解读 ({model}) ...")
    with urllib.request.urlopen(req, timeout=300) as r:
        resp = json.load(r)
    # DeepSeek 兼容端点会在 text 前返回 thinking 块, 只取 text
    text = "\n".join(b.get("text", "") for b in resp.get("content", [])
                     if b.get("type") == "text").strip()
    if not text:
        raise RuntimeError(f"AI 响应无文本: {json.dumps(resp, ensure_ascii=False)[:300]}")
    return text


def main():
    parser = argparse.ArgumentParser(description="基本面 AI 解读报告")
    parser.add_argument("code", help="股票代码, 如 688072")
    parser.add_argument("name", help="股票中文名, 如 拓荆科技")
    args = parser.parse_args()

    json_path = os.path.join("stocks", args.name, f"{args.name}_基本面.json")
    if not os.path.exists(json_path):
        raise SystemExit(f"❌ 未找到 {json_path}\n   请先运行: python collect_data.py {args.code} {args.name}")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    prompt = build_prompt(data)
    report = call_ai(prompt)

    out = os.path.join("stocks", args.name, f"{args.name}_分析报告.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# {args.name} ({args.code}) 基本面分析报告\n\n")
        f.write(f"> 数据采集: {data.get('fetch_time', '?')} | AI 解读生成\n\n---\n\n")
        f.write(report)
    print(f"\n✅ 已保存: {out}")
    print("── 报告预览 ──")
    print(report[:2000])


if __name__ == "__main__":
    main()
