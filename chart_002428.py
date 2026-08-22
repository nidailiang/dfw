#!/usr/bin/env python3
"""生成 002428 云南锗业 K线图 + 机构调研 + 蒙特卡洛股价概率预测"""
import json
import numpy as np
import pandas as pd

df = pd.read_csv("002428_kline.csv")

ohlc, volumes, dates = [], [], []
for _, r in df.iterrows():
    ohlc.append([float(r["open"]), float(r["close"]), float(r["low"]), float(r["high"])])
    volumes.append(int(r["volume"]))
    dates.append(str(r["date"]))

macd_dif = [float(x) if pd.notna(x) else None for x in df["DIF"]]
macd_dea = [float(x) if pd.notna(x) else None for x in df["DEA"]]
macd_bar = [float(x) if pd.notna(x) else None for x in df["MACD"]]

close_s = df["close"].values
ma20 = [float(x) if pd.notna(x) else None for x in pd.Series(close_s).rolling(20).mean()]
ma60 = [float(x) if pd.notna(x) else None for x in pd.Series(close_s).rolling(60).mean()]

latest_close = float(df["close"].iloc[-1])
latest_date = str(df["date"].iloc[-1])
ath = float(df["high"].max())
ath_date = str(df.loc[df["high"].idxmax(), "date"])

# 年内涨幅（2026年首个交易日收盘）
df2026 = df[df["date"] >= "2026-01-01"]
ytd_close = float(df2026["close"].iloc[0])
ytd_ret = (latest_close / ytd_close - 1) * 100

# 高点以来的低点（ATH 之后盘中最低价）
after_ath = df[df["date"] >= ath_date]
trough = float(after_ath["low"].min())
trough_date = str(after_ath.loc[after_ath["low"].idxmin(), "date"])
drawdown = (latest_close / ath - 1) * 100
rebound = (latest_close / trough - 1) * 100
trough_dd = (trough / ath - 1) * 100

# 量能：近20日均量 vs 前100日均量
vol20 = float(df["volume"].tail(20).mean())
vol100 = float(df["volume"].tail(120).head(100).mean())
vol_ratio = vol20 / vol100

# ── 关键事件 ─────────────────────────────────────────────
def find_nearest(target, dates_list):
    for i, d in enumerate(dates_list):
        if d >= target:
            return i
    return len(dates_list) - 1

evt_forecast = find_nearest("2026-07-14", dates)   # 业绩预告
evt_order    = find_nearest("2026-07-24", dates)   # 磷化铟大单公告
evt_risk     = find_nearest("2026-08-06", dates)   # 异动风险提示公告
ath_idx      = dates.index(ath_date)
trough_idx   = dates.index(trough_date)

events = [
    {"label": "历史最高\n132.88\n(6/25)", "date": ath_date, "price": ath, "idx": ath_idx, "color": "#e34948"},
    {"label": "中报预告\n7/14", "date": dates[evt_forecast], "price": float(df.iloc[evt_forecast]["high"]), "idx": evt_forecast, "color": "#4a3aa7"},
    {"label": "InP大单公告\n5.7~8.55亿\n(7/24)", "date": dates[evt_order], "price": float(df.iloc[evt_order]["low"]), "idx": evt_order, "color": "#1baf7a"},
    {"label": f"暴跌低点\n{trough:.0f}\n({trough_date[5:]})", "date": trough_date, "price": trough, "idx": trough_idx, "color": "#1baf7a"},
    {"label": "公司提示\n炒作风险\n(8/6)", "date": dates[evt_risk], "price": float(df.iloc[evt_risk]["high"]), "idx": evt_risk, "color": "#e34948"},
]

# ── 蒙特卡洛概率模拟（漂移=0，历史波动率） ────────────────
rng = np.random.default_rng(42)
rets = np.log(df["close"] / df["close"].shift(1)).dropna().tail(120).values
sigma_d = float(rets.std())
sigma_ann = sigma_d * np.sqrt(252)
N = 10000
for T in (20, 60):
    z = rng.standard_normal(N)
    S = latest_close * np.exp(-0.5 * sigma_d**2 * T + sigma_d * np.sqrt(T) * z)
    if T == 20:
        S20 = S
    else:
        S60 = S

def stats(S):
    p = np.percentile(S, [5, 25, 50, 75, 95])
    return {k: round(v, 1) for k, v in zip(["p5", "p25", "p50", "p75", "p95"], p)}

s20, s60 = stats(S20), stats(S60)
p60_ath   = float((S60 > ath).mean() * 100)      # 重上历史高点
p60_120   = float((S60 > 120).mean() * 100)
p60_78    = float((S60 < 78.08).mean() * 100)    # 跌破大单公告日收盘
p60_60    = float((S60 < trough).mean() * 100)    # 跌破阶段低点
p20_120   = float((S20 > 120).mean() * 100)
p20_90    = float((S20 < 90).mean() * 100)

# 60日终值分布直方图（截断到1%~99%）
lo, hi = np.percentile(S60, [1, 99])
hist, edges = np.histogram(np.clip(S60, lo, hi), bins=40)
bin_centers = [round(float((edges[i] + edges[i + 1]) / 2), 1) for i in range(len(edges) - 1)]
hist_counts = [int(x) for x in hist]

# ── 估值 ────────────────────────────────────────────────
total_shares = 510e8 / 78.08          # 7/24 市值510亿@78.08 → 总股本约6.53亿股
mcap = latest_close * total_shares / 1e8
pe26_cons = mcap / 2.65               # 一致预期 2026E 归母2.65亿
pe26_dw   = mcap / 3.34               # 东吴 2026E 3.34亿
pe27_cons = mcap / 6.12               # 一致预期 2027E 6.12亿
pe27_dw   = mcap / 11.17              # 东吴 2027E 11.17亿

k_last, d_last, j_last = float(df["K"].iloc[-1]), float(df["D"].iloc[-1]), float(df["J"].iloc[-1])
dif_last, dea_last = float(df["DIF"].iloc[-1]), float(df["DEA"].iloc[-1])

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>002428 云南锗业 — 多维度分析</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js"></script>
<style>
:root {{
  color-scheme: light;
  --surface-1: #fcfcfb; --surface-page: #f9f9f7;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #898781;
  --gridline: #e1e0d9;
  --candle-up: #d03b3b; --candle-down: #1baf7a;
  --volume-up: rgba(208,59,59,0.40); --volume-down: rgba(27,175,122,0.40);
  --accent: #eb6834; --ma20: #eb6834; --ma60: #4a3aa7;
  --prob-blue: #86b6ef;
}}

@media (prefers-color-scheme: dark) {{
  :root:where(:not([data-theme="light"])) {{
    color-scheme: dark;
    --surface-1: #1a1a19; --surface-page: #0d0d0d;
    --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #898781;
    --gridline: #2c2c2a;
    --candle-up: #e66767; --candle-down: #199e70;
    --volume-up: rgba(230,103,103,0.40); --volume-down: rgba(25,158,112,0.40);
    --accent: #d95926; --ma20: #d95926; --ma60: #9085e9;
    --prob-blue: #3987e5;
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --surface-1: #1a1a19; --surface-page: #0d0d0d;
  --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #898781;
  --gridline: #2c2c2a;
  --candle-up: #e66767; --candle-down: #199e70;
  --volume-up: rgba(230,103,103,0.40); --volume-down: rgba(25,158,112,0.40);
  --accent: #d95926; --ma20: #d95926; --ma60: #9085e9;
  --prob-blue: #3987e5;
}}

* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  background: var(--surface-page); color: var(--text-primary);
  display:flex; flex-direction:column; align-items:center; padding:24px 16px 48px;
}}
.header {{ max-width:1200px; width:100%; margin-bottom:10px; }}
.header h1 {{ font-size:22px; font-weight:600; }}
.header .sub {{ font-size:13px; color:var(--text-secondary); margin-top:2px; }}

.chart-wrap {{
  max-width:1200px; width:100%; background:var(--surface-1);
  border-radius:8px; border:1px solid rgba(11,11,11,0.08);
}}
#main-chart {{ width:100%; height:520px; }}
#vol-chart  {{ width:100%; height:130px; }}
#macd-chart {{ width:100%; height:150px; }}
#prob-chart {{ width:100%; height:230px; }}

.analysis {{
  max-width:1200px; width:100%; margin-top:14px;
  display:grid; grid-template-columns:repeat(auto-fit, minmax(280px,1fr)); gap:10px;
}}
.card {{
  background:var(--surface-1); border-radius:8px;
  border:1px solid rgba(11,11,11,0.08); padding:14px 18px;
}}
.card h3 {{ font-size:13px; font-weight:600; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px; }}
.card p  {{ font-size:13px; line-height:1.65; color:var(--text-primary); }}
.up {{ color:var(--candle-up); font-weight:600; }}
.dn {{ color:var(--candle-down); font-weight:600; }}
.hl {{ color:var(--accent); font-weight:600; }}

.verdict {{
  max-width:1200px; width:100%; margin-top:14px;
  background:var(--surface-1); border-radius:8px;
  border:1px solid rgba(11,11,11,0.08); padding:18px 22px;
}}
.verdict h2 {{ font-size:16px; font-weight:600; margin-bottom:10px; }}
.verdict p  {{ font-size:14px; line-height:1.75; }}

.theme-btn {{
  position:fixed; top:16px; right:16px;
  background:var(--surface-1); border:1px solid rgba(11,11,11,0.12);
  border-radius:6px; padding:6px 12px; font-size:12px; cursor:pointer;
  color:var(--text-secondary); font-family:inherit; z-index:99;
}}
</style>
</head>
<body>
<button class="theme-btn" onclick="toggleTheme()">🌓</button>

<div class="header">
  <h1>云南锗业 002428 — 锗业龙头 × 磷化铟衬底 · 多维度分析</h1>
  <div class="sub">数据截至 {latest_date} · {len(dates)}个交易日 · 最新 <span style="color:var(--accent);font-weight:600">{latest_close:.2f}</span> · 年内 <span style="color:var(--candle-up);font-weight:600">{ytd_ret:+.0f}%</span> · 历史最高 {ath:.2f} · 自高点回撤 {drawdown:.1f}%</div>
</div>

<div class="chart-wrap">
  <div id="main-chart"></div>
  <div id="vol-chart"></div>
  <div id="macd-chart"></div>
  <div id="prob-chart"></div>
</div>

<div class="analysis">
  <div class="card">
    <h3>🏢 公司做什么的</h3>
    <p>
      国内<span class="hl">最大锗产品生产商</span>，锗矿→冶炼→深加工全产业链。<br>
      五大业务: 材料级锗(锗锭47.6吨/年)、光伏级锗(卫星太阳能电池衬底)、红外级锗(军工红外/热成像)、光纤级四氯化锗(60吨/年，吃AIDC光纤需求)、<span class="hl">化合物半导体(磷化铟InP + 砷化镓)</span>。<br>
      子公司<span class="hl">鑫耀半导体(华为哈勃入股)</span>是国内唯一规模化量产InP衬底的本土企业。<br>
      InP产能15万片/年 → 扩产至<span class="hl">45万片/年</span>(含6英寸6000片)，建设期18个月。
    </p>
  </div>
  <div class="card">
    <h3>📊 业绩状态</h3>
    <p>
      2025年: 营收10.66亿，归母仅2014.6万(扣非亏680万)<br>
      2026H1预告: 归母 <span class="up">5500~8000万</span> (+148%~261%)<br>
      扣非 <span class="up">5200~6700万</span> (+576%~771%)，<span class="hl">首次大幅转正</span><br>
      Q2单季净利环比暴增4~6倍<br>
      <span class="hl">InP大单 5.7~8.55亿</span>(占2025营收53%~80%)，26年8月~27年底交付<br>
      一致预期: 2026E归母2.65亿 → 2027E 6.12亿 → 2028E 9.14亿
    </p>
  </div>
  <div class="card">
    <h3>💰 估值分析</h3>
    <p>
      现价{latest_close:.0f}元 → 市值 <span class="hl">~{mcap:.0f}亿</span>(总股本~6.53亿股)<br>
      PE(2026E一致2.65亿): <span class="up">~{pe26_cons:.0f}倍</span>；东吴口径(3.34亿): ~{pe26_dw:.0f}倍<br>
      PE(2027E一致6.12亿): ~{pe27_cons:.0f}倍；东吴口径(11.17亿): ~{pe27_dw:.0f}倍<br>
      静态PE(2025年微利) 2681倍、PB ~37倍<br>
      → <span class="dn">估值完全锚在2027~2028年</span>，公司8/6自认"估值严重高估"
    </p>
  </div>
  <div class="card">
    <h3>🔬 机构调研与评级</h3>
    <p>
      <span class="hl">7/16 昆明现场调研13家机构</span>: 中信证券、混沌投资、国调基金、东北证券、中航基金等<br>
      要点: InP扩产45万片/年按期推进；认证<span class="hl">基本覆盖国内下游知名厂商</span>；高纯红磷/铟外购供应正常；部分出口许可已获批<br>
      评级: <span class="up">东吴买入</span>(首覆6/9、维持7/15)、东莞买入、东北/华泰增持<br>
      EPS预测: 东吴 0.51/1.71/2.57(26/27/28E)<br>
      主流研报<span class="dn">不给明确目标价</span>；汇总区间: 乐观140~170 / 中性95~115
    </p>
  </div>
  <div class="card">
    <h3>📰 消息面时间线</h3>
    <p>
      ① 6/25 冲高 <span class="up">132.88</span>(年内+300%)<br>
      ② 7/14 业绩预告次日<span class="dn">跌停</span>(利好兑现)<br>
      ③ 7/23晚 <span class="hl">InP大单公告</span>(5.7~8.55亿)<br>
      ④ 7/21 盘中探至 <span class="dn">{trough:.0f}</span>(较前高{trough_dd:.0f}%)<br>
      ⑤ 8/4~8/6 <span class="up">连续3日涨停</span><br>
      ⑥ 8/6 公司公告提示<span class="dn">"非理性炒作风险"</span><br>
      ⑦ 8/14 收 {latest_close:.2f}，较阶段低点反弹 <span class="up">+{rebound:.0f}%</span>
    </p>
  </div>
  <div class="card">
    <h3>🔍 技术面</h3>
    <p>
      KDJ: K={k_last:.0f} D={d_last:.0f} J={j_last:.0f} → <span class="hl">强势区高位钝化</span>(J从122回落至88)<br>
      MACD: DIF={dif_last:.2f} DEA={dea_last:.2f} → <span class="up">DIF已上零轴</span>，DEA逼近零轴，红柱连续但<span class="dn">开始收缩</span><br>
      MA20={ma20[-1]:.1f} / MA60={ma60[-1]:.1f}，现价{('在MA20上方' if latest_close>ma20[-1] else '在MA20下方')}<br>
      量能: 近20日均量≈前100日均量({vol_ratio:.1f}倍)，8/7成交1.19亿股为<span class="hl">阶段天量</span><br>
      支撑: <span class="hl">100整数关 → 90 → 78(大单公告日)</span><br>
      阻力: <span class="hl">108~110(8/12高点) → 132.88(前高)</span>
    </p>
  </div>
  <div class="card">
    <h3>🎲 概率预测(蒙特卡洛)</h3>
    <p>
      方法: 近120日历史波动率(σ年化~{sigma_ann*100:.0f}%)、漂移=0、1万条路径<br>
      <span class="hl">20个交易日后</span>: 中位 {s20['p50']:.0f}，50%区间 [{s20['p25']:.0f}~{s20['p75']:.0f}]，90%区间 [{s20['p5']:.0f}~{s20['p95']:.0f}]<br>
      <span class="hl">60个交易日后(~3个月)</span>: 中位 {s60['p50']:.0f}，50%区间 [{s60['p25']:.0f}~{s60['p75']:.0f}]，90%区间 [{s60['p5']:.0f}~{s60['p95']:.0f}]<br>
      P(60日内重上132.88前高) = <span class="up">{p60_ath:.0f}%</span><br>
      P(60日内破120) = <span class="hl">{p60_120:.0f}%</span><br>
      P(60日内跌破78.08) = <span class="dn">{p60_78:.0f}%</span><br>
      P(60日内跌回{trough:.0f}以下) = <span class="dn">{p60_60:.0f}%</span><br>
      ⚠️ 纯统计口径(几何布朗运动)，不含基本面/消息面信息
    </p>
  </div>
  <div class="card">
    <h3>🎯 后市博弈点</h3>
    <p>
      ① 8月底前<span class="hl">正式中报</span>(预告上限8000万能否兑现)<br>
      ② <span class="hl">InP大单</span>8月起分批交付节奏<br>
      ③ 二期30万片扩产 + <span class="hl">6英寸</span>放量进度<br>
      ④ 锗价能否站稳2.3~2.5万/千克<br>
      ⑤ 出口许可审批节奏<br>
      ⑥ 公司表示在<span class="hl">考虑股权激励</span>计划
    </p>
  </div>
  <div class="card">
    <h3>⚠️ 核心风险</h3>
    <p>
      · 估值严重透支: 公司8/6自认<span class="dn">"非理性炒作"</span>，静态PE 2681倍<br>
      · 化合物半导体2025年收入仅1.38亿(占13%)，<span class="dn">大单为区间金额</span>，受良率/交付影响<br>
      · 锗价强周期属性，出口管制政策存在变数<br>
      · 题材投机盘博弈剧烈: 年内已现<span class="dn">-54%</span>的暴跌回撤<br>
      · 磷化铟全球格局仍由住友(42%)、AXT(36%)主导
    </p>
  </div>
</div>

<div class="verdict">
  <h2>综合研判</h2>
  <p>
    云南锗业是<span class="hl">"战略小金属涨价 + 军工红外 + InP衬底国产替代"</span>三重逻辑叠加的标的，基本面拐点是真实的: 扣非净利润五年来首次大幅转正、InP量价齐升、5.7~8.55亿大单锁定未来17个月交付——机构调研(7/16十三家)确认扩产与认证均按计划推进，东吴/东莞给买入。<br><br>
    <strong>但当前价位的核心矛盾是估值:</strong> {mcap:.0f}亿市值对应2026年一致预期净利2.65亿，PE约{pe26_cons:.0f}倍；即便按东吴最乐观的2027年11.17亿净利，PE仍约{pe27_dw:.0f}倍。券商普遍给"买入"评级却<span class="hl">不给目标价</span>，本身就是一种态度——认可逻辑，不认可价格。<br><br>
    <strong>技术面:</strong> 8/4~8/6三连板放量突破后，现价在<span class="hl">100~108箱体</span>内震荡消化，MACD红柱收缩、J值从122回落，短线动能边际减弱；MA20({ma20[-1]:.0f})与100整数关构成第一道支撑，78(大单公告日收盘)是逻辑底线，{trough:.0f}是情绪底线。<br><br>
    <strong>统计模拟(60日，1万条路径):</strong> 按当前历史波动率(年化{sigma_ann*100:.0f}%)，60日后90%区间为[{s60['p5']:.0f}~{s60['p95']:.0f}]，重上132.88前高的概率约{p60_ath:.0f}%，跌破78.08的概率约{p60_78:.0f}%。注意这是<span class="hl">纯统计口径</span>——实际分布由中报和大单交付决定，而非随机游走。<br><br>
    <strong>三情景参考区间:</strong><br>
    ① 乐观(中报顶格+首批交付顺利+锗价续涨): <span class="up">120~140</span>（挑战前高）<br>
    ② 中性(符合预期，箱体震荡): <span class="hl">90~115</span><br>
    ③ 悲观(中报不及预期/题材退潮): <span class="dn">60~80</span><br><br>
    <strong>一句话:</strong> 逻辑最硬的部分(InP衬底国产替代)是真实的，但股价已经在为2027~2028年定价。当前位置适合<span class="hl">跟踪验证而非追高</span>——下一个方向选择点就是8月底的正式中报。
  </p>
</div>

<script>
const dates = {json.dumps(dates, ensure_ascii=False)};
const ohlc  = {json.dumps(ohlc)};
const volumes = {json.dumps(volumes)};
const macdDIF  = {json.dumps(macd_dif)};
const macdDEA  = {json.dumps(macd_dea)};
const macdBar  = {json.dumps(macd_bar)};
const ma20 = {json.dumps(ma20)};
const ma60 = {json.dumps(ma60)};
const eventData = {json.dumps(events, ensure_ascii=False)};
const probBins = {json.dumps(bin_centers)};
const probCounts = {json.dumps(hist_counts)};
const CUR_PRICE = {latest_close};
const ATH_PRICE = {ath};

function getTheme() {{
  return document.documentElement.getAttribute("data-theme") ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}}
function toggleTheme() {{
  const cur = getTheme();
  document.documentElement.setAttribute("data-theme", cur === "dark" ? "light" : "dark");
  [chartMain, chartVol, chartMacd, chartProb].forEach(c => c && c.dispose());
  initCharts();
}}
function getCSS(n) {{ return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }}

let chartMain, chartVol, chartMacd, chartProb;

function initCharts() {{
  const upColor = getCSS("--candle-up"), downColor = getCSS("--candle-down");
  const volUp = getCSS("--volume-up"), volDown = getCSS("--volume-down");
  const textMuted = getCSS("--text-muted"), textSec = getCSS("--text-secondary");
  const gridline = getCSS("--gridline"), ma20c = getCSS("--ma20"), ma60c = getCSS("--ma60");
  const probBlue = getCSS("--prob-blue"), accent = getCSS("--accent");

  const markPoints = eventData.map(e => ({{
    name: e.label, coord: [dates[e.idx], e.price],
    symbol: "pin", symbolSize: 44,
    itemStyle: {{ color: e.color }},
    label: {{ formatter: e.label.replace(/\\n/g,"\\n"), color: "#fff", fontSize: 9, fontWeight: 600 }},
    symbolOffset: [0, -14],
  }}));

  chartMain = echarts.init(document.getElementById("main-chart"));
  chartMain.setOption({{
    tooltip: {{ trigger:"axis", axisPointer:{{ type:"cross" }}, valueFormatter:v=>v==null?"-":v.toFixed(2) }},
    legend: {{ data:["MA20","MA60"], top:6, left:"12%", textStyle:{{ color:textSec, fontSize:11 }}, itemWidth:18, itemHeight:2 }},
    grid: [{{ left:"10%", right:"2%", top:"10%", height:"66%" }}],
    xAxis: {{ type:"category", data:dates, axisLine:{{ lineStyle:{{ color:gridline }} }}, axisLabel:{{ color:textMuted,fontSize:10 }}, axisTick:{{ show:false }}, splitLine:{{ show:false }} }},
    yAxis: {{ type:"value", scale:true, axisLine:{{ show:false }}, axisTick:{{ show:false }}, axisLabel:{{ color:textMuted,fontSize:10 }}, splitLine:{{ lineStyle:{{ color:gridline,width:1 }} }}, position:"right" }},
    series: [
      {{ name:"K线", type:"candlestick", data:ohlc, itemStyle:{{ color:upColor,color0:downColor,borderColor:upColor,borderColor0:downColor }}, markPoint:{{ silent:true, data:markPoints }}, z:3 }},
      {{ name:"MA20", type:"line", data:ma20, symbol:"none", lineStyle:{{ width:1.5,color:ma20c,opacity:0.85 }}, z:4 }},
      {{ name:"MA60", type:"line", data:ma60, symbol:"none", lineStyle:{{ width:1.5,color:ma60c,opacity:0.85 }}, z:4 }},
    ],
  }});

  chartVol = echarts.init(document.getElementById("vol-chart"));
  chartVol.setOption({{
    tooltip: {{ trigger:"axis", axisPointer:{{ type:"shadow" }}, valueFormatter:v=>{{ if(v==null)return"-"; if(v>=1e8)return (v/1e8).toFixed(2)+"亿"; if(v>=1e4)return (v/1e4).toFixed(0)+"万"; return v; }} }},
    grid: [{{ left:"10%", right:"2%", top:"2%", height:"70%" }}],
    xAxis: {{ type:"category", data:dates, axisLine:{{ show:false }}, axisLabel:{{ show:false }}, axisTick:{{ show:false }}, splitLine:{{ show:false }} }},
    yAxis: {{ type:"value", axisLine:{{ show:false }}, axisTick:{{ show:false }}, axisLabel:{{ color:textMuted,fontSize:9,formatter:v=>v>=1e6?(v/1e6).toFixed(0)+"M":v }}, splitLine:{{ lineStyle:{{ color:gridline,width:1 }} }}, position:"right" }},
    series: [{{ name:"成交量", type:"bar", data:ohlc.map((d,i)=>({{ value:volumes[i], itemStyle:{{ color:d[1]>=d[0]?volUp:volDown }} }})), barWidth:"60%" }}],
  }});

  chartMacd = echarts.init(document.getElementById("macd-chart"));
  chartMacd.setOption({{
    tooltip: {{ trigger:"axis", valueFormatter:v=>v==null?"-":v.toFixed(3) }},
    grid: [{{ left:"10%", right:"2%", top:"4%", height:"72%" }}],
    legend: {{ data:["DIF","DEA","MACD柱"], bottom:0, textStyle:{{ color:textSec,fontSize:10 }}, itemWidth:18, itemHeight:2 }},
    xAxis: {{ type:"category", data:dates, axisLine:{{ show:false }}, axisLabel:{{ color:textMuted,fontSize:10 }}, axisTick:{{ show:false }}, splitLine:{{ show:false }} }},
    yAxis: {{ type:"value", axisLine:{{ show:false }}, axisTick:{{ show:false }}, axisLabel:{{ color:textMuted,fontSize:9 }}, splitLine:{{ lineStyle:{{ color:gridline,width:1 }} }}, position:"right" }},
    series: [
      {{ name:"DIF", type:"line", data:macdDIF, symbol:"none", lineStyle:{{ width:1.5,color:ma20c }} }},
      {{ name:"DEA", type:"line", data:macdDEA, symbol:"none", lineStyle:{{ width:1.5,color:ma60c }} }},
      {{ name:"MACD柱", type:"bar", data:macdBar.map(v=>v==null?null:{{ value:v, itemStyle:{{ color:v>=0?upColor:downColor }} }}), barWidth:"60%" }},
    ],
  }});

  chartProb = echarts.init(document.getElementById("prob-chart"));
  chartProb.setOption({{
    tooltip: {{ trigger:"axis", axisPointer:{{ type:"shadow" }}, formatter:ps=>{{
      const d = ps[0]; return "60日终值区间 " + d.name + " 元<br>" + "路径数: " + d.value + " (" + (d.value/100).toFixed(1) + "%)";
    }} }},
    title: {{ text:"蒙特卡洛模拟 · 60个交易日后收盘价分布(1万条路径)", left:12, top:6, textStyle:{{ color:textSec, fontSize:11, fontWeight:500 }} }},
    grid: [{{ left:"10%", right:"2%", top:"16%", height:"62%" }}],
    xAxis: {{ type:"category", data:probBins, axisLine:{{ show:false }}, axisLabel:{{ color:textMuted,fontSize:9, interval:7 }}, axisTick:{{ show:false }}, splitLine:{{ show:false }} }},
    yAxis: {{ type:"value", axisLine:{{ show:false }}, axisTick:{{ show:false }}, axisLabel:{{ color:textMuted,fontSize:9 }}, splitLine:{{ lineStyle:{{ color:gridline,width:1 }} }} }},
    series: [
      {{ name:"路径分布", type:"bar", data:probCounts, barWidth:"92%", itemStyle:{{ color:probBlue, borderColor:probBlue, borderWidth:0.5 }},
        markLine: {{
          silent:true, symbol:"none",
          label:{{ fontSize:10, color:textSec, position:"insideEndTop" }},
          lineStyle:{{ width:1.5, type:"dashed" }},
          data:[
            {{ xAxis: probBins.reduce((a,b,i)=>Math.abs(b-CUR_PRICE)<Math.abs(probBins[a]-CUR_PRICE)?i:a, 0), name:"现价 " + CUR_PRICE.toFixed(0), lineStyle:{{ color:accent }} }},
            {{ xAxis: probBins.reduce((a,b,i)=>Math.abs(b-ATH_PRICE)<Math.abs(probBins[a]-ATH_PRICE)?i:a, 0), name:"前高 " + ATH_PRICE.toFixed(0), lineStyle:{{ color:upColor }} }},
          ]
        }}
      }},
    ],
  }});

  [chartMain,chartVol,chartMacd].forEach(c=>{{ c.group="002428"; c.on("updateAxisPointer",e=>{{ [chartMain,chartVol,chartMacd].forEach(cc=>{{ if(cc!==c)cc.dispatchAction({{ type:"updateAxisPointer",axesInfo:e.axesInfo }}); }}); }}); }});
  echarts.connect("002428");
}}

initCharts();
window.addEventListener("resize",()=>[chartMain,chartVol,chartMacd,chartProb].forEach(c=>c&&c.resize()));
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change",()=>{{ [chartMain,chartVol,chartMacd,chartProb].forEach(c=>c&&c.dispose()); initCharts(); }});
</script>
</body>
</html>"""

with open("chart_002428.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ chart_002428.html 已生成")
print(f"现价 {latest_close:.2f} ({latest_date}) | 年内 {ytd_ret:+.1f}%")
print(f"历史最高 {ath:.2f} ({ath_date}) | 回撤 {drawdown:.1f}% | 自低点反弹 {rebound:.1f}%")
print(f"MA20={ma20[-1]:.1f} MA60={ma60[-1]:.1f} | 量能比 {vol_ratio:.1f}倍")
print(f"日波动率 {sigma_d*100:.2f}% (年化 {sigma_ann*100:.0f}%)")
print(f"20日: 中位{s20['p50']:.0f} 50%区间[{s20['p25']:.0f},{s20['p75']:.0f}] 90%区间[{s20['p5']:.0f},{s20['p95']:.0f}]")
print(f"60日: 中位{s60['p50']:.0f} 50%区间[{s60['p25']:.0f},{s60['p75']:.0f}] 90%区间[{s60['p5']:.0f},{s60['p95']:.0f}]")
print(f"P(60日>132.88)={p60_ath:.0f}% P(60日>120)={p60_120:.0f}% P(60日<78.08)={p60_78:.0f}% P(60日<60.83)={p60_60:.0f}%")
print(f"P(20日>120)={p20_120:.0f}% P(20日<90)={p20_90:.0f}%")
print(f"市值 ~{mcap:.0f}亿 | PE26E(一致)={pe26_cons:.0f} PE27E(东吴)={pe27_dw:.0f}")
