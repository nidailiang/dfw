#!/usr/bin/env python3
"""生成 688072 拓荆科技 K线图 + 多维度分析"""
import json
import pandas as pd

df = pd.read_csv("688072_kline.csv")

ohlc, volumes, dates = [], [], []
for _, r in df.iterrows():
    ohlc.append([float(r["open"]), float(r["close"]), float(r["low"]), float(r["high"])])
    volumes.append(int(r["volume"]))
    dates.append(str(r["date"]))

macd_dif  = [float(x) if pd.notna(x) else None for x in df["DIF"]]
macd_dea  = [float(x) if pd.notna(x) else None for x in df["DEA"]]
macd_bar  = [float(x) if pd.notna(x) else None for x in df["MACD"]]

close_series = df["close"].values
ma20 = [float(x) if pd.notna(x) else None for x in pd.Series(close_series).rolling(20).mean()]
ma60 = [float(x) if pd.notna(x) else None for x in pd.Series(close_series).rolling(60).mean()]

latest_close = float(df["close"].iloc[-1])
latest_date  = str(df["date"].iloc[-1])
start_close  = float(df["close"].iloc[0])
total_ret    = (latest_close - start_close) / start_close * 100
ath          = float(df["high"].max())
ath_date     = str(df.loc[df["high"].idxmax(), "date"])

# ── 关键事件标注 ──
def find_nearest_date(target, dates, df):
    """找到最接近target的实际交易日，返回 (idx, close_price)"""
    if target in dates:
        idx = dates.index(target)
        return idx, float(df.iloc[idx]["close"])
    # 找之前最近的交易日
    prev_dates = [d for d in dates if d < target]
    if prev_dates:
        idx = dates.index(prev_dates[-1])
        return idx, float(df.iloc[idx]["close"])
    return 0, float(df.iloc[0]["close"])

# 先基于实际数据找近似日期
evt_q1_idx, evt_q1_close = find_nearest_date("2026-04-28", dates, df)
evt_dz_idx, evt_dz_close = find_nearest_date("2026-07-08", dates, df)
evt_sp_idx, evt_sp_close = find_nearest_date("2026-06-29", dates, df)
evt_fp_idx, evt_fp_close = find_nearest_date("2026-07-14", dates, df)

events = [
    {"label": "收购尚积停牌", "date": dates[evt_sp_idx], "price": evt_sp_close, "idx": evt_sp_idx, "color": "#4a3aa7"},
    {"label": "复牌冲顶945",  "date": dates[evt_fp_idx], "price": df.iloc[evt_fp_idx]["high"], "idx": evt_fp_idx, "color": "#e34948"},
    {"label": "Q1业绩+488%",  "date": dates[evt_q1_idx], "price": evt_q1_close, "idx": evt_q1_idx, "color": "#1baf7a"},
    {"label": "定增募资45.6亿", "date": dates[evt_dz_idx], "price": evt_dz_close, "idx": evt_dz_idx, "color": "#eb6834"},
]

for e in events:
    e["price"] = float(e["price"])

# ── 估值数据 ──
consensus_eps_2026 = 6.02
consensus_np_2026  = 17.0
current_pe         = latest_close / consensus_eps_2026
analyst_fair_pe    = 75
fair_price_75pe    = consensus_eps_2026 * analyst_fair_pe
avg_target         = 402
highest_target     = 623
lowest_target      = 380

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>688072 拓荆科技 — 多维度分析</title>
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
#main-chart {{ width:100%; height:520px; }}
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
  <h1>拓荆科技 688072 — 多维度分析</h1>
  <div class="sub">{dates[0]} ~ {dates[-1]} · {len(dates)}个交易日 · 总涨幅 <span style="color:var(--candle-up);font-weight:600">+{total_ret:.0f}%</span> · 最新 {latest_close:.2f} · 历史最高 {ath:.0f}</div>
</div>

<div class="chart-wrap">
  <div id="main-chart"></div>
  <div id="vol-chart"></div>
  <div id="macd-chart"></div>
</div>

<div class="analysis">
  <div class="card">
    <h3>📊 Q2 业绩预测</h3>
    <p>
      营收预测: <span class="hl">15~17亿</span>（Q1=11.1亿）<br>
      EPS预测: <span class="hl">~1.00元/股</span><br>
      全年营收共识: <span class="hl">85~91亿</span><br>
      全年净利共识: <span class="hl">16.7~17.4亿</span> (+85% YoY)<br>
      关键看点: 毛利率能否继续提升（Q1=41.7%）<br>
      预约披露: <span class="hl">8月21日</span>
    </p>
  </div>
  <div class="card">
    <h3>🏢 公司做什么的</h3>
    <p>
      国产<span class="hl">薄膜沉积设备龙头</span>，覆盖PECVD/ALD/SACVD/HDPCVD。<br>
      核心叙事: <span class="hl">存储扩产 + 混合键合 + 三维集成</span><br>
      长江存储PECVD份额约55%，在手订单<span class="hl">~110亿</span>。<br>
      刚收购无锡尚积→补齐PVD+刻蚀产品线。
    </p>
  </div>
  <div class="card">
    <h3>💰 估值分析</h3>
    <p>
      当前PE (2026E): <span class="up">{current_pe:.0f}倍</span>（基于EPS {consensus_eps_2026}）<br>
      分析师合理PE: <span class="hl">70-85倍</span> → 对应 {fair_price_75pe:.0f}~{consensus_eps_2026*85:.0f}元<br>
      机构目标均价: <span class="dn">{avg_target:.0f}元</span>（已被大幅超越）<br>
      最高目标: <span class="up">{highest_target:.0f}</span>（招商），最低: <span class="dn">{lowest_target:.0f}</span><br>
      <span class="up">市场给的溢价远超分析师框架</span>
    </p>
  </div>
  <div class="card">
    <h3>📰 重大消息面</h3>
    <p>
      ① <span class="hl">收购尚积半导体</span>：6/29停牌→7/13复牌<br>
      ② <span class="hl">定增45.6亿</span>：576元/股，用于产业化基地<br>
      ③ 复牌后冲<span class="up">945</span>→急跌至<span class="dn">570</span>（-40%），典型"买预期卖事实"<br>
      ④ 两融余额19.2亿，融资买入活跃
    </p>
  </div>
  <div class="card">
    <h3>📈 机构调研与评级</h3>
    <p>
      近6月: <span class="hl">17家机构覆盖</span>（买入11/增持5/强推1）<br>
      招商证券 6月调高至<span class="up">"强烈推荐"</span>，目标623<br>
      核心逻辑: 存储扩产+键合放量+毛利率改善<br>
      分歧点: <span class="hl">2027年放量节奏和竞争格局</span>
    </p>
  </div>
  <div class="card">
    <h3>🔍 技术面</h3>
    <p>
      KDJ: K={df["K"].iloc[-1]:.0f} D={df["D"].iloc[-1]:.0f} J={df["J"].iloc[-1]:.0f} → <span class="hl">超卖区反弹中</span><br>
      MACD: DIF={df["DIF"].iloc[-1]:.1f} DEA={df["DEA"].iloc[-1]:.1f} → <span class="dn">零轴死叉</span>，但<span class="hl">绿柱收缩</span><br>
      从945跌到570: <span class="dn">-39.7%</span><br>
      昨日从570反弹到678: <span class="up">+12.1%</span><br>
      关键支撑: <span class="hl">548</span>（6月前低）、<span class="hl">570</span>（8/4低点）<br>
      关键阻力: <span class="hl">MA20 ~730</span>、<span class="hl">MA60 ~650</span>
    </p>
  </div>
  <div class="card">
    <h3>🎯 Q2 博弈关键</h3>
    <p>
      ① 营收是否超<span class="hl">17亿</span>？（超预期=利好）<br>
      ② 毛利率是否超<span class="hl">42%</span>？（趋势确认）<br>
      ③ 在手订单是否从<span class="hl">110亿</span>继续增长？<br>
      ④ 尚积收购进展更新<br>
      ⑤ 混合键合设备订单披露
    </p>
  </div>
  <div class="card">
    <h3>⚠️ 风险提示</h3>
    <p>
      · 估值已反映较多乐观预期，<span class="dn">不及预期杀伤力大</span><br>
      · 存储资本开支周期拐点风险<br>
      · 竞争加剧（中微、北方华创也在做薄膜）<br>
      · 收购整合不确定性<br>
      · 解禁压力（科创板大量解禁）
    </p>
  </div>
</div>

<div class="verdict">
  <h2>综合研判</h2>
  <p>
    拓荆科技处于<span class="hl">"高景气赛道 + 高估值 + 高波动"</span>三重叠加状态。<br><br>
    <strong>业绩面：</strong>Q2大概率延续高增（+50%以上营收增速），全年17亿净利润是市场共识。110亿在手订单提供了2年的业绩能见度，这是最大的确定性。<br><br>
    <strong>估值面：</strong>当前{current_pe:.0f}倍PE显著高于分析师给出的70-85倍合理区间，但市场愿意给溢价的原因在于：① 2027年增速仍然可观（+50%）；② 混合键合是AI芯片封装的核心设备，空间极大；③ 收购尚积打开了第二增长曲线。如果按2027年EPS ~8-9元算，前瞻PE约75-85倍，<span class="hl">估值刚好落在合理区间上沿</span>。<br><br>
    <strong>技术面：</strong>945→570的急跌（-40%）已释放了相当部分的获利盘和重组炒作泡沫。570的低点与6月前低548形成<span class="hl">双底雏形</span>，KDJ超卖+MACD绿柱收缩配合反弹。但这个位置很关键——如果Q2业绩超预期，可能走出"W底"向上；如果业绩miss，548的支撑可能被击穿。<br><br>
    <strong>股价预测区间：</strong>
    ① 乐观（Q2超预期，突破MA20）: <span class="up">750~850</span><br>
    ② 中性（Q2符合预期，震荡筑底）: <span class="hl">570~730</span><br>
    ③ 悲观（Q2 miss + 大盘情绪差）: <span class="dn">450~550</span><br><br>
    <strong>一句话：</strong>基本面很强，但股价已经price in了很多。Q2财报（8/21前后）是近期最关键的催化剂，<span class="hl">超预期=W底确认，miss=调整深化</span>。这个位置追高风险收益比不划算，等Q2落地后再做方向判断更稳妥。
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
  const textSec = getCSS("--text-secondary"), textMuted = getCSS("--text-muted");
  const gridline = getCSS("--gridline"), ma20c = getCSS("--ma20"), ma60c = getCSS("--ma60");

  const markPoints = eventData.map(e => ({{
    name: e.label, coord: [dates[e.idx], e.price],
    symbol: "pin", symbolSize: 42,
    itemStyle: {{ color: e.color }},
    label: {{ formatter: e.label + "\\n" + e.price, color: "#fff", fontSize: 10, fontWeight: 600 }},
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
      {{ name:"MA60", type:"line", data:ma60, symbol:"none", lineStyle:{{ width:1.5,color:ma60c,opacity:0.8 }}, z:4 }},
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

  [chartMain,chartVol,chartMacd].forEach(c=>{{ c.group="688072"; c.on("updateAxisPointer",e=>{{ [chartMain,chartVol,chartMacd].forEach(cc=>{{ if(cc!==c)cc.dispatchAction({{ type:"updateAxisPointer",axesInfo:e.axesInfo }}); }}); }}); }});
  echarts.connect("688072");
}}

initCharts();
window.addEventListener("resize",()=>[chartMain,chartVol,chartMacd].forEach(c=>c&&c.resize()));
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change",()=>{{ [chartMain,chartVol,chartMacd].forEach(c=>c&&c.dispose()); initCharts(); }});
</script>
</body>
</html>"""

with open("chart_688072.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ chart_688072.html 已生成")
print(f"总涨幅: +{total_ret:.0f}%")
print(f"当前PE(2026E): {current_pe:.0f}倍")
print(f"分析师合理PE: 70-85倍 → 对应价格 {fair_price_75pe:.0f}-{consensus_eps_2026*85:.0f}")
print(f"机构目标均价: {avg_target}")
print(f"ATR回撤: {(latest_close-ath)/ath*100:.1f}%")
