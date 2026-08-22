#!/usr/bin/env python3
"""生成 688279 K线图 HTML，标注两轮双顶形态"""
import json
import pandas as pd

df = pd.read_csv("688279_kline.csv")

ohlc = []
volumes = []
dates = []
for _, r in df.iterrows():
    ohlc.append([float(r["open"]), float(r["close"]), float(r["low"]), float(r["high"])])
    volumes.append(int(r["volume"]))
    dates.append(str(r["date"]))

macd_dif = [float(x) if pd.notna(x) else None for x in df["DIF"]]
macd_dea = [float(x) if pd.notna(x) else None for x in df["DEA"]]
macd_bar = [float(x) if pd.notna(x) else None for x in df["MACD"]]

# ── 第一轮双顶 (2025年) ──
dt1_left_idx = dates.index("2025-03-06")
dt1_right_idx = dates.index("2025-09-18")
dt1_left_high = float(df.iloc[dt1_left_idx]["high"])
dt1_right_high = float(df.iloc[dt1_right_idx]["high"])
dt1_trough_slice = df.iloc[dt1_left_idx:dt1_right_idx + 1]
dt1_trough_row = df.loc[dt1_trough_slice["low"].idxmin()]
dt1_trough_low = float(dt1_trough_row["low"])
dt1_trough_date = str(dt1_trough_row["date"])

# ── 第二轮双顶 (2026年近期) ──
dt2_left_idx = dates.index("2026-05-25")
dt2_right_idx = dates.index("2026-07-03")
dt2_left_high = float(df.iloc[dt2_left_idx]["high"])
dt2_right_high = float(df.iloc[dt2_right_idx]["high"])
dt2_trough_slice = df.iloc[dt2_left_idx:dt2_right_idx + 1]
dt2_trough_row = df.loc[dt2_trough_slice["low"].idxmin()]
dt2_trough_low = float(dt2_trough_row["low"])
dt2_trough_date = str(dt2_trough_row["date"])

# 颈线跌破确认点 — 右顶之后首次收盘低于颈线的日期
after_right = df.iloc[dt2_right_idx:]
brk = after_right[after_right["close"] < dt2_trough_low]
dt2_break_date = str(brk.iloc[0]["date"]) if len(brk) > 0 else "—"
dt2_break_price = float(brk.iloc[0]["close"]) if len(brk) > 0 else 0

# 理论目标
target_1 = dt1_trough_low - (dt1_left_high - dt1_trough_low)
target_2 = dt2_trough_low - (dt2_left_high - dt2_trough_low)
latest_close = float(df["close"].iloc[-1])
latest_date = str(df["date"].iloc[-1])

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>688279 峰岹科技 — 双顶形态分析</title>
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
  --volume-up: rgba(208,59,59,0.45);
  --volume-down: rgba(27,175,122,0.45);
  --dt1-color: #898781;
  --dt2-color: #eb6834;
  --neckline: #4a3aa7;
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
    --volume-up: rgba(230,103,103,0.45);
    --volume-down: rgba(25,158,112,0.45);
    --dt1-color: #898781;
    --dt2-color: #d95926;
    --neckline: #9085e9;
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
  --volume-up: rgba(230,103,103,0.45);
  --volume-down: rgba(25,158,112,0.45);
  --dt1-color: #898781;
  --dt2-color: #d95926;
  --neckline: #9085e9;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  background: var(--surface-page);
  color: var(--text-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 16px 48px;
}}

.header {{
  max-width: 1200px;
  width: 100%;
  margin-bottom: 12px;
}}
.header h1 {{ font-size: 22px; font-weight: 600; letter-spacing: -0.01em; }}
.header .sub {{ font-size: 13px; color: var(--text-secondary); margin-top: 2px; }}

.chart-wrap {{
  max-width: 1200px;
  width: 100%;
  background: var(--surface-1);
  border-radius: 8px;
  border: 1px solid rgba(11,11,11,0.08);
}}
#main-chart {{ width: 100%; height: 520px; }}
#vol-chart  {{ width: 100%; height: 140px; }}
#macd-chart {{ width: 100%; height: 150px; }}

.legend-row {{
  max-width: 1200px;
  width: 100%;
  display: flex;
  gap: 20px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}}
.legend-row span {{ display: flex; align-items: center; gap: 6px; }}
.legend-dot {{
  display: inline-block;
  width: 10px; height: 10px;
  border-radius: 50%;
}}

.analysis {{
  max-width: 1200px;
  width: 100%;
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(270px, 1fr));
  gap: 10px;
}}
.card {{
  background: var(--surface-1);
  border-radius: 8px;
  border: 1px solid rgba(11,11,11,0.08);
  padding: 14px 18px;
}}
.card h3 {{ font-size: 13px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px; }}
.card p  {{ font-size: 13px; line-height: 1.65; color: var(--text-primary); }}
.card .hl {{ font-weight: 600; color: var(--dt2-color); }}
.card .warn {{ color: var(--candle-up); font-weight: 600; }}

.theme-btn {{
  position: fixed; top: 16px; right: 16px;
  background: var(--surface-1);
  border: 1px solid rgba(11,11,11,0.12);
  border-radius: 6px; padding: 6px 12px;
  font-size: 12px; cursor: pointer;
  color: var(--text-secondary); font-family: inherit;
  z-index: 99;
}}
.theme-btn:hover {{ opacity: 0.8; }}
</style>
</head>
<body>

<button class="theme-btn" onclick="toggleTheme()">🌓</button>

<div class="header">
  <h1>峰岹科技 688279 — 日K线双顶分析</h1>
  <div class="sub">{dates[0]} ~ {dates[-1]} · 共 {len(dates)} 个交易日 · 最新收盘 {latest_close:.2f}</div>
</div>

<div class="chart-wrap">
  <div id="main-chart"></div>
  <div id="vol-chart"></div>
  <div id="macd-chart"></div>
</div>

<div class="legend-row">
  <span><span class="legend-dot" style="background:var(--dt2-color)"></span> 近期双顶 (2026.05–07) — 重点关注</span>
  <span><span class="legend-dot" style="background:var(--dt1-color)"></span> 前一轮双顶 (2025.03–09)</span>
</div>

<div class="analysis">
  <div class="card">
    <h3>🔴 近期双顶 (2026.05–07)</h3>
    <p>
      左顶: <span class="hl">{dates[dt2_left_idx]} 最高 {dt2_left_high:.2f}</span><br>
      右顶: <span class="hl">{dates[dt2_right_idx]} 最高 {dt2_right_high:.2f}</span><br>
      两顶仅差 <span class="hl">{abs(dt2_left_high-dt2_right_high):.2f}</span> 元 (<span class="hl">{abs(dt2_left_high-dt2_right_high)/dt2_left_high*100:.1f}%</span>)，
      相隔 <span class="hl">5.5 周</span><br>
      右顶量能 <span class="warn">4.2M 爆量</span>后急速崩塌
    </p>
  </div>
  <div class="card">
    <h3>📐 颈线 (2026年双顶)</h3>
    <p>
      谷底: <span class="hl">{dt2_trough_date} 最低 {dt2_trough_low:.2f}</span><br>
      颈线被跌破确认: <span class="warn">{dt2_break_date} 收盘 {dt2_break_price:.2f}</span><br>
      理论跌幅目标 ≈ <span class="warn">{target_2:.1f}</span><br>
      当前已跌至 <span class="warn">{latest_close:.2f}</span>，
      {("已低于颈线理论目标" if latest_close < target_2 else "距理论目标还有{:.1f}".format(target_2 - latest_close))}
    </p>
  </div>
  <div class="card">
    <h3>📉 下跌力度</h3>
    <p>
      右顶 → 当前: <span class="warn">{(latest_close-dt2_right_high)/dt2_right_high*100:.1f}%</span>（仅1个月）<br>
      颈线 → 当前: <span class="warn">{(latest_close-dt2_trough_low)/dt2_trough_low*100:.1f}%</span><br>
      已跌破远一轮双顶的颈线 <span class="hl">({dt1_trough_low:.0f})</span><br>
      DIF/DEA 零轴下方，空头主导
    </p>
  </div>
  <div class="card">
    <h3>⚠️ 综合判断</h3>
    <p>
      这是<span class="warn">第二轮标准双顶</span>，级别虽小于第一轮，
      但<span class="warn">破位速度更快、跌幅更猛</span>。<br>
      短线 KDJ 低位（J={df["J"].iloc[-1]:.0f}）可能技术反弹，
      但<span class="warn">双顶结构已确认，中期空头趋势明确</span>。<br>
      反弹至颈线附近（~{dt2_trough_low:.0f}）可能是减仓机会。
    </p>
  </div>
</div>

<script>
const dates = {json.dumps(dates, ensure_ascii=False)};
const ohlc = {json.dumps(ohlc)};
const volumes = {json.dumps(volumes)};
const macdDIF = {json.dumps(macd_dif)};
const macdDEA = {json.dumps(macd_dea)};
const macdBar = {json.dumps(macd_bar)};

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

function getCSS(name) {{
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}}

let chartMain, chartVol, chartMacd;

function makeMarkArea(name, leftIdx, rightIdx, color) {{
  return [
    [
      {{ xAxis: dates[leftIdx], yAxis: 0, itemStyle: {{ color: "transparent" }} }},
      {{ xAxis: dates[leftIdx], yAxis: 400, itemStyle: {{ color: "transparent" }} }},
    ],
    [
      {{ xAxis: dates[rightIdx], yAxis: 0, itemStyle: {{ color: "transparent" }} }},
      {{ xAxis: dates[rightIdx], yAxis: 400, itemStyle: {{ color: "transparent" }} }},
    ],
  ];
}}

function initCharts() {{
  const upColor = getCSS("--candle-up");
  const downColor = getCSS("--candle-down");
  const volUp = getCSS("--volume-up");
  const volDown = getCSS("--volume-down");
  const textSecondary = getCSS("--text-secondary");
  const textMuted = getCSS("--text-muted");
  const gridline = getCSS("--gridline");
  const dt1Color = getCSS("--dt1-color");
  const dt2Color = getCSS("--dt2-color");
  const neckColor = getCSS("--neckline");

  // ── 主图 K线 ──
  chartMain = echarts.init(document.getElementById("main-chart"));
  chartMain.setOption({{
    tooltip: {{
      trigger: "axis",
      axisPointer: {{ type: "cross" }},
      valueFormatter: v => v == null ? "-" : v.toFixed(2),
    }},
    grid: [{{ left: "10%", right: "2%", top: "6%", height: "68%" }}],
    xAxis: {{
      type: "category", data: dates,
      axisLine: {{ lineStyle: {{ color: gridline }} }},
      axisLabel: {{ color: textMuted, fontSize: 10 }},
      axisTick: {{ show: false }},
      splitLine: {{ show: false }},
    }},
    yAxis: {{
      type: "value", scale: true,
      axisLine: {{ show: false }}, axisTick: {{ show: false }},
      axisLabel: {{ color: textMuted, fontSize: 10 }},
      splitLine: {{ lineStyle: {{ color: gridline, width: 1 }} }},
      position: "right",
    }},
    series: [{{
      name: "K线",
      type: "candlestick",
      data: ohlc,
      itemStyle: {{
        color: upColor, color0: downColor,
        borderColor: upColor, borderColor0: downColor,
      }},
      // ── 第一轮双顶 (灰色，历史参考) ──
      markPoint: {{
        silent: true, symbol: "pin", symbolSize: 30,
        data: [
          {{
            name: "顶1A", coord: [dates[{dt1_left_idx}], {dt1_left_high}],
            itemStyle: {{ color: dt1Color, opacity: 0.5 }},
            label: {{ formatter: "M", color: "#fff", fontSize: 9 }},
            symbolOffset: [0, -8],
          }},
          {{
            name: "顶1B", coord: [dates[{dt1_right_idx}], {dt1_right_high}],
            itemStyle: {{ color: dt1Color, opacity: 0.5 }},
            label: {{ formatter: "M", color: "#fff", fontSize: 9 }},
            symbolOffset: [0, -8],
          }},
          // ── 第二轮双顶 (橙色，重点关注) ──
          {{
            name: "顶2A", coord: [dates[{dt2_left_idx}], {dt2_left_high}],
            itemStyle: {{ color: dt2Color }},
            label: {{ formatter: "M1\\n{dt2_left_high}", color: "#fff", fontSize: 10, fontWeight: 600 }},
            symbolOffset: [0, -10], symbolSize: 40,
          }},
          {{
            name: "顶2B", coord: [dates[{dt2_right_idx}], {dt2_right_high}],
            itemStyle: {{ color: dt2Color }},
            label: {{ formatter: "M2\\n{dt2_right_high}", color: "#fff", fontSize: 10, fontWeight: 600 }},
            symbolOffset: [0, -10], symbolSize: 40,
          }},
        ],
      }},
      // ── 水平参考线 ──
      markLine: {{
        silent: true, symbol: "none",
        data: [
          // 近期双顶颈线 (紫色虚线)
          {{
            yAxis: {dt2_trough_low},
            lineStyle: {{ color: neckColor, width: 1.5, type: "dashed" }},
            label: {{ formatter: "颈线 {dt2_trough_low}", color: neckColor, fontSize: 10, position: "start" }},
          }},
          // 近期左顶水平线 (橙色)
          {{
            yAxis: {dt2_left_high},
            lineStyle: {{ color: dt2Color, width: 0.8, type: "dotted", opacity: 0.5 }},
            label: {{ show: false }},
          }},
          // 近期理论目标 (红色虚线)
          {{
            yAxis: {target_2},
            lineStyle: {{ color: downColor, width: 1, type: "dashed", opacity: 0.7 }},
            label: {{ formatter: "目标 {target_2:.0f}", color: downColor, fontSize: 10, position: "start" }},
          }},
        ],
      }},
    }}],
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
    xAxis: {{
      type: "category", data: dates,
      axisLine: {{ show: false }}, axisLabel: {{ show: false }},
      axisTick: {{ show: false }}, splitLine: {{ show: false }},
    }},
    yAxis: {{
      type: "value",
      axisLine: {{ show: false }}, axisTick: {{ show: false }},
      axisLabel: {{ color: textMuted, fontSize: 9, formatter: v => v>=1e6 ? (v/1e6).toFixed(0)+"M" : v }},
      splitLine: {{ lineStyle: {{ color: gridline, width: 1 }} }},
      position: "right",
    }},
    series: [{{ name: "成交量", type: "bar", data: volData, barWidth: "60%" }}],
  }});

  // ── MACD ──
  chartMacd = echarts.init(document.getElementById("macd-chart"));
  const macdBarData = macdBar.map(v => {{
    if (v == null) return null;
    return {{ value: v, itemStyle: {{ color: v >= 0 ? upColor : downColor }} }};
  }});
  chartMacd.setOption({{
    tooltip: {{ trigger: "axis", valueFormatter: v => v == null ? "-" : v.toFixed(3) }},
    grid: [{{ left: "10%", right: "2%", top: "4%", height: "72%" }}],
    legend: {{
      data: ["DIF", "DEA", "MACD柱"], bottom: 0,
      textStyle: {{ color: textSecondary, fontSize: 10 }},
      itemWidth: 18, itemHeight: 2,
    }},
    xAxis: {{
      type: "category", data: dates,
      axisLine: {{ show: false }}, axisLabel: {{ color: textMuted, fontSize: 10 }},
      axisTick: {{ show: false }}, splitLine: {{ show: false }},
    }},
    yAxis: {{
      type: "value",
      axisLine: {{ show: false }}, axisTick: {{ show: false }},
      axisLabel: {{ color: textMuted, fontSize: 9 }},
      splitLine: {{ lineStyle: {{ color: gridline, width: 1 }} }},
      position: "right",
    }},
    series: [
      {{ name: "DIF", type: "line", data: macdDIF, symbol: "none", lineStyle: {{ width: 1.5, color: dt2Color }} }},
      {{ name: "DEA", type: "line", data: macdDEA, symbol: "none", lineStyle: {{ width: 1.5, color: neckColor }} }},
      {{ name: "MACD柱", type: "bar", data: macdBarData, barWidth: "60%" }},
    ],
  }});

  // 联动
  [chartMain, chartVol, chartMacd].forEach(c => {{
    c.group = "688279";
    c.on("updateAxisPointer", e => {{
      [chartMain, chartVol, chartMacd].forEach(cc => {{
        if (cc !== c) cc.dispatchAction({{ type: "updateAxisPointer", axesInfo: e.axesInfo }});
      }});
    }});
  }});
  echarts.connect("688279");
}}

initCharts();
window.addEventListener("resize", () => {{
  [chartMain, chartVol, chartMacd].forEach(c => c && c.resize());
}});
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {{
  [chartMain, chartVol, chartMacd].forEach(c => c && c.dispose());
  initCharts();
}});
</script>
</body>
</html>"""

with open("chart_688279.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ 图表已生成: chart_688279.html")
print()
print("═══ 第一轮双顶 (2025年) ═══")
print(f"  左顶: {dt1_left_high} ({dates[dt1_left_idx]})")
print(f"  右顶: {dt1_right_high} ({dates[dt1_right_idx]})")
print(f"  颈线: {dt1_trough_low} ({dt1_trough_date})")
print(f"  理论目标: {target_1:.1f}")
print()
print("═══ 第二轮双顶 (2026年近期) ═══")
print(f"  左顶: {dt2_left_high} ({dates[dt2_left_idx]})")
print(f"  右顶: {dt2_right_high} ({dates[dt2_right_idx]})")
print(f"  颈线: {dt2_trough_low} ({dt2_trough_date})")
print(f"  跌破日: {dt2_break_date} (收盘 {dt2_break_price:.2f})")
print(f"  理论目标: {target_2:.1f}")
print(f"  当前: {latest_close} ({latest_date})")
print(f"  右顶→当前跌幅: {(latest_close-dt2_right_high)/dt2_right_high*100:.1f}%")
