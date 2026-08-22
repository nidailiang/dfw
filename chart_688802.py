#!/usr/bin/env python3
"""生成 688802 沐曦股份 K线图 + 多维度分析"""
import json
import pandas as pd

df = pd.read_csv("688802_kline.csv")

ohlc, volumes, dates = [], [], []
for _, r in df.iterrows():
    ohlc.append([float(r["open"]), float(r["close"]), float(r["low"]), float(r["high"])])
    volumes.append(int(r["volume"]))
    dates.append(str(r["date"]))

macd_dif  = [float(x) if pd.notna(x) else None for x in df["DIF"]]
macd_dea  = [float(x) if pd.notna(x) else None for x in df["DEA"]]
macd_bar  = [float(x) if pd.notna(x) else None for x in df["MACD"]]

close_s = df["close"].values
ma20 = [float(x) if pd.notna(x) else None for x in pd.Series(close_s).rolling(20).mean()]
ma60 = [float(x) if pd.notna(x) else None for x in pd.Series(close_s).rolling(60).mean()]

latest_close = float(df["close"].iloc[-1])
latest_date  = str(df["date"].iloc[-1])
ipo_close    = float(df["close"].iloc[0])
ipo_date     = str(df["date"].iloc[0])
ath          = float(df["high"].max())
ath_date     = str(df.loc[df["high"].idxmax(), "date"])

# 关键事件 (上市仅153天，数据很短)
def find_nearest(target, dates_list, df):
    for d in dates_list:
        if d >= target:
            idx = dates_list.index(d)
            return idx, float(df.iloc[idx]["close"])
    return len(dates_list)-1, float(df.iloc[-1]["close"])

evt1_idx, _ = find_nearest("2026-07-09", dates, df)  # 澄清公告
evt2_idx, _ = find_nearest("2026-07-13", dates, df)  # 最高点

events = [
    {"label": "上市首日\n830", "date": dates[0], "price": ipo_close, "idx": 0, "color": "#4a3aa7"},
    {"label": "澄清订单传闻\n→股价见顶", "date": dates[evt1_idx], "price": float(df.iloc[evt1_idx]["high"]), "idx": evt1_idx, "color": "#e34948"},
    {"label": "历史最高\n1033", "date": dates[evt2_idx], "price": ath, "idx": evt2_idx, "color": "#e34948"},
]

# 估值
consensus_rev_2026 = 35.16  # 亿
consensus_np_2026  = 0.82   # 亿
consensus_eps_2026 = 0.20
current_ps = latest_close / (consensus_rev_2026 * 1e8 / 4.0e8)  # 约4亿总股本估算市值/营收
target_avg = 892

# 总股本估算 (基于市值反推)
# 当前市值约2900亿，股价726 → 总股本约4亿
total_shares = 2900e8 / latest_close  # 约4亿

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>688802 沐曦股份 — 多维度分析</title>
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
#main-chart {{ width:100%; height:500px; }}
#vol-chart  {{ width:100%; height:130px; }}
#macd-chart {{ width:100%; height:150px; }}

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
  <h1>沐曦股份 688802 — 国产GPU第二股 · 多维度分析</h1>
  <div class="sub">上市: {ipo_date} · {len(dates)}个交易日 · 发行价104.66 → 首日收{ipo_close:.0f} → 最新 <span style="color:var(--accent);font-weight:600">{latest_close:.2f}</span> · 历史最高 {ath:.0f}</div>
</div>

<div class="chart-wrap">
  <div id="main-chart"></div>
  <div id="vol-chart"></div>
  <div id="macd-chart"></div>
</div>

<div class="analysis">
  <div class="card">
    <h3>🏢 公司做什么的</h3>
    <p>
      国产<span class="hl">高性能通用GPU</span>龙头（国产GPU第二股）。<br>
      三大产品线: <span class="hl">曦思N</span>（推理）、<span class="hl">曦云C</span>（训推一体）、<span class="hl">曦彩G</span>（渲染）。<br>
      旗舰芯片C600用全国产工艺，支持FP8+HBM3e。<br>
      自研MXMACA软件栈，兼容CUDA生态。<br>
      累计出货超2.5万颗，部署10+个千卡集群。
    </p>
  </div>
  <div class="card">
    <h3>📊 业绩状态</h3>
    <p>
      2026Q1: 营收 <span class="hl">5.62亿</span> (+75%)，净亏 <span class="dn">-0.99亿</span> (减亏57%)<br>
      2025全年: 营收16.44亿 (+121%)，净亏-7.89亿<br>
      2026E全年: 营收 <span class="hl">~35亿</span> (+114%)，<span class="up">有望首次盈利 ~0.8亿</span><br>
      关键驱动: C600量产 + 互联网客户导入<br>
      毛利率: <span class="hl">60%</span>，负债率仅3.4%
    </p>
  </div>
  <div class="card">
    <h3>💰 估值分析</h3>
    <p>
      当前市值: <span class="hl">~2900亿</span> (股价726)<br>
      2026E PS: <span class="hl">~83倍</span>（营收35亿）<br>
      PE无意义（刚扭亏，EPS仅0.2元）<br>
      机构用<span class="hl">PS估值</span>: 华泰给2027年58xPS → 目标899<br>
      国泰海通给2026年100xPS → 目标885<br>
      <span class="up">机构目标均价 892，较当前+23%</span>
    </p>
  </div>
  <div class="card">
    <h3>📰 关键消息面</h3>
    <p>
      ① <span class="hl">7/9 澄清公告</span>: 公司否认"订单排到明年"传闻<br>
      ② 当天股价仍在1005高位，<span class="dn">此后一路暴跌至665</span><br>
      ③ 7/13 触顶1033后急转直下，<span class="dn">34天跌36%</span><br>
      ④ 公司明确: 无未披露重大事项<br>
      ⑤ <span class="hl">IPO投资者已浮亏</span>（首日收830 vs 现价726）
    </p>
  </div>
  <div class="card">
    <h3>📈 机构调研与评级</h3>
    <p>
      近90天: <span class="hl">5家机构</span>（4买入/1增持）<br>
      目标均价: <span class="hl">892元</span> (华泰899, 国泰海通885)<br>
      核心逻辑: <span class="hl">AI推理爆发+C600全国产+互联网客户突破</span><br>
      担忧: 亏损何时真正扭转，竞争格局<br>
      机构覆盖仍偏少（上市仅8个月）
    </p>
  </div>
  <div class="card">
    <h3>🔍 技术面</h3>
    <p>
      KDJ: K={df["K"].iloc[-1]:.0f} D={df["D"].iloc[-1]:.0f} J={df["J"].iloc[-1]:.0f} → <span class="hl">超卖区金叉在即</span><br>
      MACD: DIF={df["DIF"].iloc[-1]:.0f} DEA={df["DEA"].iloc[-1]:.0f} → <span class="dn">零轴下方死叉</span>，绿柱收缩<br>
      从1033跌到665: <span class="dn">-35.6%</span><br>
      近3天反弹: 665→696→726 (<span class="up">+9.2%</span>)<br>
      关键位: 支撑 <span class="hl">665/634</span>，阻力 <span class="hl">MA20~780, 830(IPO首日收盘)</span>
    </p>
  </div>
  <div class="card">
    <h3>🎯 Q2业绩博弈点</h3>
    <p>
      ① C600量产进度和出货量<br>
      ② 互联网大客户是否正式导入<br>
      ③ 营收是否环比加速（Q1=5.6亿）<br>
      ④ 亏损是否进一步收窄<br>
      ⑤ 下半年订单能见度<br>
      ⑥ 运营商集采进展
    </p>
  </div>
  <div class="card">
    <h3>⚠️ 核心风险</h3>
    <p>
      · <span class="dn">尚未盈利</span>，2026年全年盈利预测仅0.8亿（极脆弱）<br>
      · 估值靠PS支撑，没有PE锚<br>
      · 华为昇腾、寒武纪竞争激烈<br>
      · 全国产工艺良率/产能不确定<br>
      · <span class="hl">IPO投资者仍在水下</span>（首日收盘830）<br>
      · 流通市值仅135亿，波动极大
    </p>
  </div>
</div>

<div class="verdict">
  <h2>综合研判</h2>
  <p>
    沐曦是<span class="hl">"国产GPU第二股"</span>，质地比寒武纪更纯（真正做通用GPU而非只是AI加速卡），但目前还在<span class="dn">用亏损换规模</span>的阶段。<br><br>
    <strong>基本面：</strong>营收增速很快（+75%~+114%），毛利率60%很健康。但全年盈利预测仅0.8亿——这是<span class="hl">刚好跨过盈亏线</span>的水平，一个季度miss就可能打回亏损。C600的量产和互联网客户导入是2026年最关键的催化剂。<br><br>
    <strong>估值：</strong>2900亿市值对应35亿营收=83倍PS，这个估值放在全球半导体都是<span class="up">极贵的</span>。英伟达历史上最高PS也就40-50倍。市场在为2027-2028年买单（2027E营收61亿→PS 48倍，才算合理一些）。机构目标892元也就是+23%的空间，<span class="hl">性价比并不突出</span>。<br><br>
    <strong>技术面：</strong>上市仅8个月，历史太短，图形参考价值有限。但1033→665的暴跌（-36%）发生在公司辟谣之后，说明之前是被<span class="dn">虚假传闻推上去的</span>。现在从665反弹到726，更像超跌修复而非趋势反转。关键是<span class="hl">830（IPO首日收盘）</span>——这是大量IPO打新投资者的成本线，突破此处才有真正的趋势行情。<br><br>
    <strong>股价预测区间：</strong><br>
    ① 乐观（C600超预期放量+Q2扭亏）: <span class="up">830~900</span>（突破IPO首日线）<br>
    ② 中性（符合预期，震荡筑底）: <span class="hl">665~780</span><br>
    ③ 悲观（Q2继续亏损+市场风格切换）: <span class="dn">550~650</span><br><br>
    <strong>一句话：</strong>国产GPU赛道是最确定的方向之一，沐曦是稀缺标的。但2900亿市值已经把2027年的预期都定价了。短期看超跌反弹（665→780），中期看830（IPO成本线）能否突破。<span class="hl">如果Q2能扭亏，这个位置是合理的买入点；如果继续亏损，下跌空间还不小</span>。
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
function getCSS(n) {{ return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }}

let chartMain, chartVol, chartMacd;

function initCharts() {{
  const upColor = getCSS("--candle-up"), downColor = getCSS("--candle-down");
  const volUp = getCSS("--volume-up"), volDown = getCSS("--volume-down");
  const textMuted = getCSS("--text-muted"), textSec = getCSS("--text-secondary");
  const gridline = getCSS("--gridline"), ma20c = getCSS("--ma20"), ma60c = getCSS("--ma60");

  const markPoints = eventData.map(e => ({{
    name: e.label, coord: [dates[e.idx], e.price],
    symbol: "pin", symbolSize: e.idx === 0 ? 36 : 42,
    itemStyle: {{ color: e.color }},
    label: {{ formatter: e.label.replace("\\n","\\n"), color: "#fff", fontSize: 10, fontWeight: 600 }},
    symbolOffset: [0, -12],
  }}));

  chartMain = echarts.init(document.getElementById("main-chart"));
  chartMain.setOption({{
    tooltip: {{ trigger:"axis", axisPointer:{{ type:"cross" }}, valueFormatter:v=>v==null?"-":v.toFixed(2) }},
    grid: [{{ left:"10%", right:"2%", top:"6%", height:"68%" }}],
    xAxis: {{ type:"category", data:dates, axisLine:{{ lineStyle:{{ color:gridline }} }}, axisLabel:{{ color:textMuted,fontSize:10 }}, axisTick:{{ show:false }}, splitLine:{{ show:false }} }},
    yAxis: {{ type:"value", scale:true, axisLine:{{ show:false }}, axisTick:{{ show:false }}, axisLabel:{{ color:textMuted,fontSize:10 }}, splitLine:{{ lineStyle:{{ color:gridline,width:1 }} }}, position:"right" }},
    series: [
      {{ name:"K线", type:"candlestick", data:ohlc, itemStyle:{{ color:upColor,color0:downColor,borderColor:upColor,borderColor0:downColor }}, markPoint:{{ silent:true, data:markPoints }}, z:3 }},
      {{ name:"MA20", type:"line", data:ma20, symbol:"none", lineStyle:{{ width:1.5,color:ma20c,opacity:0.8 }}, z:4 }},
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

  [chartMain,chartVol,chartMacd].forEach(c=>{{ c.group="688802"; c.on("updateAxisPointer",e=>{{ [chartMain,chartVol,chartMacd].forEach(cc=>{{ if(cc!==c)cc.dispatchAction({{ type:"updateAxisPointer",axesInfo:e.axesInfo }}); }}); }}); }});
  echarts.connect("688802");
}}

initCharts();
window.addEventListener("resize",()=>[chartMain,chartVol,chartMacd].forEach(c=>c&&c.resize()));
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change",()=>{{ [chartMain,chartVol,chartMacd].forEach(c=>c&&c.dispose()); initCharts(); }});
</script>
</body>
</html>"""

with open("chart_688802.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ chart_688802.html 已生成")
print(f"上市: {ipo_date} 首日收{ipo_close:.0f} → 现价{latest_close:.0f} (IPO投资者{'浮亏' if latest_close < ipo_close else '浮盈'})")
print(f"历史最高: {ath:.0f} ({ath_date})")
print(f"回撤: {(latest_close-ath)/ath*100:.1f}%")
print(f"机构目标均价: {target_avg}元 (+{(target_avg-latest_close)/latest_close*100:.1f}%)")
print(f"2026E PS: ~{latest_close * total_shares / (consensus_rev_2026 * 1e8):.0f}倍")
