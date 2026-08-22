#!/usr/bin/env python3
"""生成 688702 盛科通信 K线图 HTML — N型上涨分析"""
import json
import pandas as pd

df = pd.read_csv("688702_kline.csv")

ohlc, volumes, dates = [], [], []
for _, r in df.iterrows():
    ohlc.append([float(r["open"]), float(r["close"]), float(r["low"]), float(r["high"])])
    volumes.append(int(r["volume"]))
    dates.append(str(r["date"]))

macd_dif  = [float(x) if pd.notna(x) else None for x in df["DIF"]]
macd_dea  = [float(x) if pd.notna(x) else None for x in df["DEA"]]
macd_bar  = [float(x) if pd.notna(x) else None for x in df["MACD"]]

# ── N型波段关键转折点 ──
waves = [
    {"label": "起涨",  "date": "2025-06-23", "price": 55.00,  "color": "#1baf7a"},
    {"label": "顶①",  "date": "2025-09-18", "price": 154.88, "color": "#e34948"},
    {"label": "底①",  "date": "2025-11-05", "price": 108.90, "color": "#1baf7a"},
    {"label": "顶②",  "date": "2025-12-11", "price": 149.80, "color": "#e34948"},
    {"label": "底②",  "date": "2026-01-15", "price": 126.00, "color": "#1baf7a"},
    {"label": "顶③",  "date": "2026-03-11", "price": 218.88, "color": "#e34948"},
    {"label": "底③",  "date": "2026-03-24", "price": 154.95, "color": "#1baf7a"},
    {"label": "顶④",  "date": "2026-04-30", "price": 368.88, "color": "#e34948"},
    {"label": "底④",  "date": "2026-06-08", "price": 248.12, "color": "#1baf7a"},
]

# 验证数据存在
for w in waves:
    w["idx"] = dates.index(w["date"])

# 当前数据
latest_close = float(df["close"].iloc[-1])
latest_date  = str(df["date"].iloc[-1])
start_close  = float(df["close"].iloc[0])
total_ret    = (latest_close - start_close) / start_close * 100

# 各波段涨幅
wave_returns = []
for i in range(0, len(waves) - 1, 1):
    if waves[i]["label"].startswith("底") and waves[i+1]["label"].startswith("顶"):
        ret = (waves[i+1]["price"] - waves[i]["price"]) / waves[i]["price"] * 100
        wave_returns.append(f"底→顶: {waves[i]['price']:.0f}→{waves[i+1]['price']:.0f} (+{ret:.0f}%)")

# MA 数据
close_series = df["close"].values
ma20 = pd.Series(close_series).rolling(20).mean().tolist()
ma60 = pd.Series(close_series).rolling(60).mean().tolist()
ma20 = [float(x) if pd.notna(x) else None for x in ma20]
ma60 = [float(x) if pd.notna(x) else None for x in ma60]

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>688702 盛科通信 — N型上涨分析</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js"></script>
<style>
:root {{
  color-scheme: light;
  --surface-1: #fcfcfb;
  --surface-page: #f9f9f7;
  --text-primary: #0b0b0b;
  --text-secondary: #52514e;
  --text-muted: #898781;
  --gridline: #e1e0d9;
  --candle-up: #d03b3b;
  --candle-down: #1baf7a;
  --volume-up: rgba(208,59,59,0.40);
  --volume-down: rgba(27,175,122,0.40);
  --accent: #eb6834;
  --ma20: #eb6834;
  --ma60: #4a3aa7;
  --wave-up: #1baf7a;
  --wave-top: #e34948;
}}

@media (prefers-color-scheme: dark) {{
  :root:where(:not([data-theme="light"])) {{
    color-scheme: dark;
    --surface-1: #1a1a19;
    --surface-page: #0d0d0d;
    --text-primary: #ffffff;
    --text-secondary: #c3c2b7;
    --text-muted: #898781;
    --gridline: #2c2c2a;
    --candle-up: #e66767;
    --candle-down: #199e70;
    --volume-up: rgba(230,103,103,0.40);
    --volume-down: rgba(25,158,112,0.40);
    --accent: #d95926;
    --ma20: #d95926;
    --ma60: #9085e9;
    --wave-up: #199e70;
    --wave-top: #e66767;
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --surface-1: #1a1a19;
  --surface-page: #0d0d0d;
  --text-primary: #ffffff;
  --text-secondary: #c3c2b7;
  --text-muted: #898781;
  --gridline: #2c2c2a;
  --candle-up: #e66767;
  --candle-down: #199e70;
  --volume-up: rgba(230,103,103,0.40);
  --volume-down: rgba(25,158,112,0.40);
  --accent: #d95926;
  --ma20: #d95926;
  --ma60: #9085e9;
  --wave-up: #199e70;
  --wave-top: #e66767;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  background: var(--surface-page); color: var(--text-primary);
  display: flex; flex-direction: column; align-items: center;
  padding: 24px 16px 48px;
}}
.header {{ max-width: 1200px; width: 100%; margin-bottom: 12px; }}
.header h1 {{ font-size: 22px; font-weight: 600; }}
.header .sub {{ font-size: 13px; color: var(--text-secondary); margin-top: 2px; }}

.chart-wrap {{
  max-width: 1200px; width: 100%;
  background: var(--surface-1); border-radius: 8px;
  border: 1px solid rgba(11,11,11,0.08);
}}
#main-chart {{ width: 100%; height: 520px; }}
#vol-chart  {{ width: 100%; height: 140px; }}
#macd-chart {{ width: 100%; height: 150px; }}

.analysis {{
  max-width: 1200px; width: 100%; margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 10px;
}}
.card {{
  background: var(--surface-1); border-radius: 8px;
  border: 1px solid rgba(11,11,11,0.08); padding: 14px 18px;
}}
.card h3 {{ font-size: 13px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px; }}
.card p  {{ font-size: 13px; line-height: 1.65; }}
.card .up {{ color: var(--candle-up); font-weight: 600; }}
.card .dn {{ color: var(--candle-down); font-weight: 600; }}
.card .hl {{ color: var(--accent); font-weight: 600; }}

.wave-table {{
  max-width: 1200px; width: 100%; margin-top: 12px;
  background: var(--surface-1); border-radius: 8px;
  border: 1px solid rgba(11,11,11,0.08); padding: 14px 18px;
}}
.wave-table h3 {{ font-size: 13px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 10px; }}
.wave-table table {{ width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }}
.wave-table th {{ text-align: left; color: var(--text-secondary); font-weight: 500; padding: 6px 8px; border-bottom: 1px solid var(--gridline); }}
.wave-table td {{ padding: 6px 8px; border-bottom: 1px solid var(--gridline); }}
.wave-table .up {{ color: var(--candle-up); font-weight: 600; }}
.wave-table .dn {{ color: var(--candle-down); font-weight: 600; }}

.theme-btn {{
  position: fixed; top: 16px; right: 16px;
  background: var(--surface-1); border: 1px solid rgba(11,11,11,0.12);
  border-radius: 6px; padding: 6px 12px; font-size: 12px; cursor: pointer;
  color: var(--text-secondary); font-family: inherit; z-index: 99;
}}
</style>
</head>
<body>
<button class="theme-btn" onclick="toggleTheme()">🌓</button>

<div class="header">
  <h1>盛科通信 688702 — N型上涨分析</h1>
  <div class="sub">{dates[0]} ~ {dates[-1]} · {len(dates)}个交易日 · 总涨幅 <span style="color:var(--candle-up);font-weight:600">+{total_ret:.0f}%</span> · 最新 {latest_close:.2f}</div>
</div>

<div class="chart-wrap">
  <div id="main-chart"></div>
  <div id="vol-chart"></div>
  <div id="macd-chart"></div>
</div>

<div class="wave-table">
  <h3>📐 N型波段拆解 — 一轮比一轮高</h3>
  <table>
    <tr><th>波段</th><th>起涨点</th><th>顶点</th><th>涨幅</th><th>回调底</th><th>回调幅度</th><th>底抬高</th></tr>
    <tr>
      <td>第①浪</td>
      <td>2025-06-23 <span class="dn">55.00</span></td>
      <td>2025-09-18 <span class="up">154.88</span></td>
      <td class="up">+182%</td>
      <td>2025-11-05 <span class="dn">108.90</span></td>
      <td class="dn">-29.7%</td>
      <td>—</td>
    </tr>
    <tr>
      <td>第②浪</td>
      <td>2025-11-05 <span class="dn">108.90</span></td>
      <td>2025-12-11 <span class="up">149.80</span></td>
      <td class="up">+38%</td>
      <td>2026-01-15 <span class="dn">126.00</span></td>
      <td class="dn">-15.9%</td>
      <td class="up">+15.7%</td>
    </tr>
    <tr>
      <td>第③浪</td>
      <td>2026-01-15 <span class="dn">126.00</span></td>
      <td>2026-03-11 <span class="up">218.88</span></td>
      <td class="up">+74%</td>
      <td>2026-03-24 <span class="dn">154.95</span></td>
      <td class="dn">-29.2%</td>
      <td class="up">+23.0%</td>
    </tr>
    <tr>
      <td>第④浪</td>
      <td>2026-03-24 <span class="dn">154.95</span></td>
      <td>2026-04-30 <span class="up">368.88</span></td>
      <td class="up">+138%</td>
      <td>2026-06-08 <span class="dn">248.12</span></td>
      <td class="dn">-32.7%</td>
      <td class="up">+60.1%</td>
    </tr>
    <tr style="font-weight:600">
      <td>当前</td>
      <td>2026-06-08 <span class="dn">248.12</span></td>
      <td>—</td>
      <td class="up">+41% (进行中)</td>
      <td>—</td>
      <td>—</td>
      <td>—</td>
    </tr>
  </table>
</div>

<div class="analysis">
  <div class="card">
    <h3>🏢 公司是干什么的</h3>
    <p>
      国产<span class="hl">以太网交换芯片龙头</span>，主营交换芯片（占营收72%）。<br>
      产品覆盖接入层→核心层，最高支持800G端口。<br>
      核心叙事：<span class="hl">国产替代 + AI超节点(Scale-Up)网络</span>。
    </p>
  </div>
  <div class="card">
    <h3>📊 业绩真的不行吗</h3>
    <p>
      2025年营收 11.5亿（+6.4%），但<span class="up">净亏损 1.5亿（亏损扩大120%）</span>。<br>
      根源：研发费用 <span class="hl">6.79亿，占营收59%</span>！<br>
      418名研发人员占全员76%，全在搞12.8T/25.6T高端芯片。<br>
      毛利率在改善（49.2%，+9pct），但研发"吃掉"了所有利润。
    </p>
  </div>
  <div class="card">
    <h3>💡 那为什么还涨</h3>
    <p>
      市场买的不是现在的利润，是<span class="hl">高端芯片放量后的弹性</span>：<br>
      · AI数据中心需要海量高速交换芯片<br>
      · 国产替代是确定性方向（博通/美满的替代）<br>
      · 2026Q1预付款环比+82%，说明订单在路上了<br>
      · 25.6T旗舰芯片已进入客户推广阶段
    </p>
  </div>
  <div class="card">
    <h3>⚠️ N型上涨的本质</h3>
    <p>
      每一浪都是<span class="hl">"拉估值→消化→再拉"</span>的循环：<br>
      上涨靠叙事和预期，回调靠估值压力释放。<br>
      关键是<span class="hl">每次回调底部都在抬高</span>：<br>
      55→109→126→155→248，这是最强势的牛市结构。<br>
      只要这个"底逐级抬高"的节奏不破，趋势就在。
    </p>
  </div>
  <div class="card">
    <h3>🎯 核心矛盾</h3>
    <p>
      <span class="up">多头逻辑</span>：2027年高端芯片放量→营收爆发→扭亏<br>
      <span class="dn">空头逻辑</span>：当前估值靠信仰，亏损扩大，研发投入是无底洞<br>
      机构预测2027年净利润0.3~4.2亿（分歧极大），<br>
      说明这件事<span class="hl">确定性并不高</span>，但一旦成功弹性巨大。
    </p>
  </div>
  <div class="card">
    <h3>🔍 当前状态</h3>
    <p>
      最新: <span class="hl">{latest_close:.2f}</span> ({latest_date})<br>
      距④浪顶 369: <span class="dn">-5.0%</span><br>
      KDJ: K={df["K"].iloc[-1]:.0f} D={df["D"].iloc[-1]:.0f} J={df["J"].iloc[-1]:.0f}，<span class="hl">刚金叉</span><br>
      MACD: DIF/DEA 零轴附近纠缠，绿柱收缩中<br>
      如果在 248 附近止跌回升破前高 369，N型结构延续；<br>
      如果跌破 248，则④浪的回调级别可能加大。
    </p>
  </div>
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

const wavePoints = {json.dumps(waves, ensure_ascii=False)};

function getTheme() {{
  return document.documentElement.getAttribute("data-theme") ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}}
function toggleTheme() {{
  const cur = getTheme();
  document.documentElement.setAttribute("data-theme", cur === "dark" ? "light" : "dark");
  [chartMain, chartVol, chartMacd].forEach(c => c && c.dispose());
  initCharts();
}}
function getCSS(n) {{
  return getComputedStyle(document.documentElement).getPropertyValue(n).trim();
}}

let chartMain, chartVol, chartMacd;

function initCharts() {{
  const upColor = getCSS("--candle-up");
  const downColor = getCSS("--candle-down");
  const volUp = getCSS("--volume-up");
  const volDown = getCSS("--volume-down");
  const textSec = getCSS("--text-secondary");
  const textMuted = getCSS("--text-muted");
  const gridline = getCSS("--gridline");
  const ma20c = getCSS("--ma20");
  const ma60c = getCSS("--ma60");
  const waveUpC = getCSS("--wave-up");
  const waveTopC = getCSS("--wave-top");

  // ── 波段标注数据 ──
  const markPoints = wavePoints.map(w => ({{
    name: w.label,
    coord: [dates[w.idx], w.price],
    itemStyle: {{ color: w.color }},
    label: {{
      formatter: w.label + "\\n" + w.price,
      color: "#fff",
      fontSize: 10,
      fontWeight: 600,
    }},
    symbol: w.label.includes("顶") ? "pin" : "triangle",
    symbolSize: w.label.includes("顶") ? 36 : 28,
    symbolOffset: w.label.includes("顶") ? [0, -10] : [0, 8],
    symbolRotate: w.label.includes("顶") ? 0 : 180,
  }}));

  // ── 主图 ──
  chartMain = echarts.init(document.getElementById("main-chart"));
  chartMain.setOption({{
    tooltip: {{
      trigger: "axis", axisPointer: {{ type: "cross" }},
      valueFormatter: v => v == null ? "-" : v.toFixed(2),
    }},
    grid: [{{ left: "10%", right: "2%", top: "6%", height: "68%" }}],
    xAxis: {{
      type: "category", data: dates,
      axisLine: {{ lineStyle: {{ color: gridline }} }},
      axisLabel: {{ color: textMuted, fontSize: 10 }},
      axisTick: {{ show: false }}, splitLine: {{ show: false }},
    }},
    yAxis: {{
      type: "value", scale: true,
      axisLine: {{ show: false }}, axisTick: {{ show: false }},
      axisLabel: {{ color: textMuted, fontSize: 10 }},
      splitLine: {{ lineStyle: {{ color: gridline, width: 1 }} }},
      position: "right",
    }},
    series: [
      {{
        name: "K线", type: "candlestick", data: ohlc,
        itemStyle: {{ color: upColor, color0: downColor, borderColor: upColor, borderColor0: downColor }},
        markPoint: {{ silent: true, data: markPoints }},
        z: 3,
      }},
      {{
        name: "MA20", type: "line", data: ma20,
        symbol: "none", lineStyle: {{ width: 1.5, color: ma20c, opacity: 0.8 }},
        z: 4,
      }},
      {{
        name: "MA60", type: "line", data: ma60,
        symbol: "none", lineStyle: {{ width: 1.5, color: ma60c, opacity: 0.8 }},
        z: 4,
      }},
    ],
  }});

  // ── 成交量 ──
  chartVol = echarts.init(document.getElementById("vol-chart"));
  const volData = ohlc.map((d, i) => ({{
    value: volumes[i],
    itemStyle: {{ color: d[1] >= d[0] ? volUp : volDown }},
  }}));
  chartVol.setOption({{
    tooltip: {{
      trigger: "axis", axisPointer: {{ type: "shadow" }},
      valueFormatter: v => {{
        if (v == null) return "-";
        if (v >= 1e8) return (v/1e8).toFixed(2)+"亿";
        if (v >= 1e4) return (v/1e4).toFixed(0)+"万";
        return v;
      }},
    }},
    grid: [{{ left: "10%", right: "2%", top: "2%", height: "70%" }}],
    xAxis: {{ type: "category", data: dates, axisLine: {{ show: false }}, axisLabel: {{ show: false }}, axisTick: {{ show: false }}, splitLine: {{ show: false }} }},
    yAxis: {{ type: "value", axisLine: {{ show: false }}, axisTick: {{ show: false }}, axisLabel: {{ color: textMuted, fontSize: 9, formatter: v => v>=1e6 ? (v/1e6).toFixed(0)+"M" : v }}, splitLine: {{ lineStyle: {{ color: gridline, width: 1 }} }}, position: "right" }},
    series: [{{ name: "成交量", type: "bar", data: volData, barWidth: "60%" }}],
  }});

  // ── MACD ──
  chartMacd = echarts.init(document.getElementById("macd-chart"));
  const macdBarData = macdBar.map(v => v == null ? null : {{ value: v, itemStyle: {{ color: v >= 0 ? upColor : downColor }} }});
  chartMacd.setOption({{
    tooltip: {{ trigger: "axis", valueFormatter: v => v == null ? "-" : v.toFixed(3) }},
    grid: [{{ left: "10%", right: "2%", top: "4%", height: "72%" }}],
    legend: {{ data: ["DIF","DEA","MACD柱"], bottom: 0, textStyle: {{ color: textSec, fontSize: 10 }}, itemWidth: 18, itemHeight: 2 }},
    xAxis: {{ type: "category", data: dates, axisLine: {{ show: false }}, axisLabel: {{ color: textMuted, fontSize: 10 }}, axisTick: {{ show: false }}, splitLine: {{ show: false }} }},
    yAxis: {{ type: "value", axisLine: {{ show: false }}, axisTick: {{ show: false }}, axisLabel: {{ color: textMuted, fontSize: 9 }}, splitLine: {{ lineStyle: {{ color: gridline, width: 1 }} }}, position: "right" }},
    series: [
      {{ name: "DIF", type: "line", data: macdDIF, symbol: "none", lineStyle: {{ width: 1.5, color: ma20c }} }},
      {{ name: "DEA", type: "line", data: macdDEA, symbol: "none", lineStyle: {{ width: 1.5, color: ma60c }} }},
      {{ name: "MACD柱", type: "bar", data: macdBarData, barWidth: "60%" }},
    ],
  }});

  [chartMain, chartVol, chartMacd].forEach(c => {{
    c.group = "688702";
    c.on("updateAxisPointer", e => {{
      [chartMain, chartVol, chartMacd].forEach(cc => {{
        if (cc !== c) cc.dispatchAction({{ type: "updateAxisPointer", axesInfo: e.axesInfo }});
      }});
    }});
  }});
  echarts.connect("688702");
}}

initCharts();
window.addEventListener("resize", () => [chartMain, chartVol, chartMacd].forEach(c => c && c.resize()));
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {{
  [chartMain, chartVol, chartMacd].forEach(c => c && c.dispose());
  initCharts();
}});
</script>
</body>
</html>"""

with open("chart_688702.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ chart_688702.html 已生成")
print(f"总涨幅: +{total_ret:.0f}% ({start_close:.2f} → {latest_close:.2f})")
for wr in wave_returns:
    print(f"  {wr}")
