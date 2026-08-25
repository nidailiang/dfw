#!/usr/bin/env python3
"""生成通达信风格交互K线图 HTML: 多空线/均线组 + 成交量 + KDJ + MACD

用法:
    python chart_html.py 688072 拓荆科技
    python chart_html.py 688072 拓荆科技 -s 20250101

输出:
    stocks/拓荆科技/拓荆科技_k线.html   (自动创建目录)

交互功能(浏览器打开):
    - 多空线(白线=EMA(EMA(C,10),10), 黄线=(MA14+MA28+MA57+MA114)/4) / 均线组 互斥切换
    - 均线参数可自行修改, 改动即时重画
    - 四段联动: K线+线 / 成交量 / KDJ / MACD, 可缩放
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_stock_kline import fetch_kline

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>__NAME__ (__CODE__) — 交互K线</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js"></script>
<style>
:root { color-scheme: dark; }
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
       background:#0d0d0d; color:#fff; padding:16px; }
.controls { display:flex; flex-wrap:wrap; gap:8px 18px; align-items:center;
  background:#1a1a19; border:1px solid #2c2c2a; border-radius:8px;
  padding:10px 14px; margin-bottom:10px; max-width:1200px; }
.controls label { font-size:13px; color:#c3c2b7; display:flex; align-items:center; gap:5px; }
.controls input[type=number] { width:52px; background:#0d0d0d; color:#fff;
  border:1px solid #3a3a38; border-radius:4px; padding:3px 6px; font-size:13px; }
.controls input[type=text] { width:140px; background:#0d0d0d; color:#fff;
  border:1px solid #3a3a38; border-radius:4px; padding:3px 6px; font-size:13px; }
.controls .grp { display:flex; gap:8px; align-items:center;
  border-left:1px solid #2c2c2a; padding-left:14px; }
button { background:#eb6834; color:#fff; border:none; border-radius:4px;
  padding:5px 14px; font-size:13px; cursor:pointer; }
button:hover { filter:brightness(1.1); }
.header { max-width:1200px; font-size:18px; font-weight:600;
  margin-bottom:10px; color:#fff; }
.sw { display:flex; gap:10px; align-items:center; }
#chart { max-width:1200px; width:100%; height:660px; background:#1a1a19;
  border-radius:8px; border:1px solid #2c2c2a; }
</style>
</head>
<body>
<div class="header">__NAME__ (__CODE__) 交互K线图</div>
<div class="controls">
  <div class="sw">
    <label><input type="radio" name="mode" id="modeWY" checked> 多空线</label>
    <label><input type="radio" name="mode" id="modeMA"> 均线组</label>
  </div>
  <div class="grp" id="grpMA" style="display:none">
    <label>均线参数(逗号分隔): <input type="text" id="inpMAs" value="5,10,20,60"></label>
  </div>
</div>
<div id="chart"></div>
<script>
const raw = __DATA__;
const dates = raw.map(r => r[0]);
const closes = raw.map(r => r[2]);
const highs = raw.map(r => r[4]);
const lows = raw.map(r => r[3]);
const ohlc = raw.map(r => [r[1], r[2], r[3], r[4]]);
const vols = raw.map(r => r[5]);

function ma(arr, n) {
  const out = new Array(arr.length).fill(null);
  let sum = 0;
  for (let i = 0; i < arr.length; i++) {
    sum += arr[i];
    if (i >= n) sum -= arr[i - n];
    if (i >= n - 1) out[i] = sum / n;
  }
  return out;
}
// 通达信 EMA 递推式: Y1 = X1; Yt = (2*Xt + (N-1)*Yt-1)/(N+1)
function emaTdx(arr, n) {
  const out = new Array(arr.length).fill(null);
  out[0] = arr[0];
  for (let i = 1; i < arr.length; i++)
    out[i] = (2 * arr[i] + (n - 1) * out[i - 1]) / (n + 1);
  return out;
}
function avgMa(arr, ns) {
  const maxN = Math.max(...ns);
  const lines = ns.map(n => ma(arr, n));
  return arr.map((_, i) => (i < maxN - 1 ? null :
    lines.reduce((s, l) => s + l[i], 0) / lines.length));
}
// MACD(12,26,9): DIF = EMA12-EMA26; DEA = EMA9(DIF); 柱 = 2*(DIF-DEA)
function macd(closes, fast = 12, slow = 26, sig = 9) {
  const eFast = emaTdx(closes, fast), eSlow = emaTdx(closes, slow);
  const dif = closes.map((_, i) => eFast[i] - eSlow[i]);
  const dea = emaTdx(dif, sig);
  const bar = closes.map((_, i) => (dif[i] - dea[i]) * 2);
  return { dif, dea, bar };
}
// 通达信 SMA(X,N,M): Y1 = X1; Yt = (M*Xt + (N-M)*Yt-1)/N  (KDJ 用,非简单平均)
function smaTdx(arr, N, M) {
  const out = new Array(arr.length).fill(null);
  out[0] = arr[0];
  for (let i = 1; i < arr.length; i++)
    out[i] = (M * arr[i] + (N - M) * out[i - 1]) / N;
  return out;
}
// KDJ(9,3,3): RSV → K=SMA(RSV,3,1) → D=SMA(K,3,1) → J=3K-2D
function kdj(highs, lows, closes, n = 9, k = 3, d = 3) {
  const rsv = closes.map((_, i) => {
    const from = Math.max(0, i - n + 1);
    const hh = Math.max(...highs.slice(from, i + 1));
    const ll = Math.min(...lows.slice(from, i + 1));
    return hh === ll ? 50 : ((closes[i] - ll) / (hh - ll)) * 100;
  });
  const K = smaTdx(rsv, k, 1);
  const D = smaTdx(K, d, 1);
  const J = K.map((v, i) => 3 * v - 2 * D[i]);
  return { K, D, J };
}

const chart = echarts.init(document.getElementById('chart'));
const MA_COLORS = ['#4da6ff', '#eb6834', '#c46cff', '#4a3aa7'];

function render() {
  const macdRes = macd(closes);
  const kdjRes = kdj(highs, lows, closes);
  const series = [
    { name:'K线', type:'candlestick', data: ohlc, itemStyle: {
        color:'#e66767', color0:'#199e70', borderColor:'#e66767', borderColor0:'#199e70' } },
    { name:'成交量', type:'bar', xAxisIndex:1, yAxisIndex:1,
      data: vols.map((v, i) => ({ value:v, itemStyle:{
        color: raw[i][2] >= raw[i][1] ? 'rgba(230,103,103,0.45)' : 'rgba(25,158,112,0.45)' } })) },
    { name:'MACD', type:'bar', xAxisIndex:3, yAxisIndex:3,
      data: macdRes.bar.map(v => ({ value:v, itemStyle:{
        color: v >= 0 ? 'rgba(230,103,103,0.55)' : 'rgba(25,158,112,0.55)' } })),
      tooltip:{ valueFormatter: v => v == null ? '-' : v.toFixed(2) } },
    { name:'DIF', type:'line', xAxisIndex:3, yAxisIndex:3, data: macdRes.dif, showSymbol:false,
      lineStyle:{ color:'#4da6ff', width:1 },
      tooltip:{ valueFormatter: v => v == null ? '-' : v.toFixed(2) } },
    { name:'DEA', type:'line', xAxisIndex:3, yAxisIndex:3, data: macdRes.dea, showSymbol:false,
      lineStyle:{ color:'#eb6834', width:1 },
      tooltip:{ valueFormatter: v => v == null ? '-' : v.toFixed(2) } },
    { name:'K', type:'line', xAxisIndex:2, yAxisIndex:2, data: kdjRes.K, showSymbol:false,
      lineStyle:{ color:'#ffffff', width:1 },
      tooltip:{ valueFormatter: v => v == null ? '-' : v.toFixed(2) } },
    { name:'D', type:'line', xAxisIndex:2, yAxisIndex:2, data: kdjRes.D, showSymbol:false,
      lineStyle:{ color:'#ffd700', width:1 },
      tooltip:{ valueFormatter: v => v == null ? '-' : v.toFixed(2) } },
    { name:'J', type:'line', xAxisIndex:2, yAxisIndex:2, data: kdjRes.J, showSymbol:false,
      lineStyle:{ color:'#c46cff', width:1 },
      tooltip:{ valueFormatter: v => v == null ? '-' : v.toFixed(2) } }
  ];
  const mode = document.querySelector('input[name="mode"]:checked').id;
  document.getElementById('grpMA').style.display = mode === 'modeMA' ? 'flex' : 'none';
  if (mode === 'modeWY') {
    // 多空线参数固定: 白线 = EMA(EMA(C,10),10), 黄线 = (MA14+MA28+MA57+MA114)/4
    const white = emaTdx(emaTdx(closes, 10), 10);
    const yellow = avgMa(closes, [14, 28, 57, 114]);
    series.push({ name:'白线', type:'line', data: white, showSymbol:false,
      lineStyle:{ color:'#ffffff', width:1.6 }, z:6,
      tooltip:{ valueFormatter: v => v == null ? '-' : v.toFixed(2) } });
    series.push({ name:'黄线', type:'line', data: yellow, showSymbol:false,
      lineStyle:{ color:'#ffd700', width:1.6 }, z:6,
      tooltip:{ valueFormatter: v => v == null ? '-' : v.toFixed(2) } });
  } else {
    document.getElementById('inpMAs').value.split(',').forEach((s, i) => {
      const n = +s.trim(); if (!n) return;
      series.push({ name:'MA'+n, type:'line', data: ma(closes, n), showSymbol:false,
        lineStyle:{ color: MA_COLORS[i % MA_COLORS.length], width:1.2 }, z:5,
        tooltip:{ valueFormatter: v => v == null ? '-' : v.toFixed(2) } });
    });
  }
  chart.setOption({
    animation:false, backgroundColor:'transparent',
    tooltip:{ trigger:'axis', axisPointer:{ type:'cross' } },
    legend:{ top:0, textStyle:{ color:'#c3c2b7' } },
    axisPointer:{ link:[{xAxisIndex:'all'}] },
    grid:[ {left:60, right:60, top:'5%', height:'40%'},
           {left:60, right:60, top:'49%', height:'13%'},
           {left:60, right:60, top:'66%', height:'14%'},
           {left:60, right:60, top:'84%', height:'12%'} ],
    title:[
      { text:'成交量', left:66, top:'49%', textStyle:{ color:'#b8b7b0', fontSize:11, fontWeight:'normal' } },
      { text:'KDJ',    left:66, top:'66%', textStyle:{ color:'#b8b7b0', fontSize:11, fontWeight:'normal' } },
      { text:'MACD',   left:66, top:'84%', textStyle:{ color:'#b8b7b0', fontSize:11, fontWeight:'normal' } }
    ],
    xAxis:[
      { type:'category', data:dates, gridIndex:0, axisLabel:{color:'#898781', showMaxLabel:true},
        axisLine:{lineStyle:{color:'#2c2c2a'}} },
      { type:'category', data:dates, gridIndex:1, axisLabel:{show:false},
        axisLine:{lineStyle:{color:'#2c2c2a'}} },
      { type:'category', data:dates, gridIndex:2, axisLabel:{show:false},
        axisLine:{lineStyle:{color:'#2c2c2a'}} },
      { type:'category', data:dates, gridIndex:3, axisLabel:{show:false},
        axisLine:{lineStyle:{color:'#2c2c2a'}} }
    ],
    yAxis:[
      { scale:true, gridIndex:0, axisLabel:{color:'#898781'}, splitLine:{lineStyle:{color:'#2c2c2a'}} },
      { gridIndex:1, axisLabel:{show:false}, splitLine:{show:false} },
      { scale:true, gridIndex:2, axisLabel:{color:'#898781'}, splitLine:{lineStyle:{color:'#2c2c2a'}} },
      { scale:true, gridIndex:3, axisLabel:{color:'#898781'}, splitLine:{lineStyle:{color:'#2c2c2a'}} }
    ],
    dataZoom:[ {type:'inside', xAxisIndex:[0,1,2,3], start:35, end:100},
               {type:'slider', xAxisIndex:[0,1,2,3], bottom:0, height:18,
                borderColor:'#2c2c2a', backgroundColor:'#1a1a19',
                fillerColor:'rgba(235,104,52,0.2)', textStyle:{color:'#898781'}} ],
    series
  }, { notMerge:true });
}
// 切换模式 / 修改参数 / 回车 → 自动重画,无需手动
document.querySelectorAll('input').forEach(i => {
  i.addEventListener('change', render);
  i.addEventListener('input', render);
  i.addEventListener('keydown', e => { if (e.key === 'Enter') render(); });
});
render();
</script>
</body></html>"""

def main():
    parser = argparse.ArgumentParser(description="生成通达信风格交互K线图 HTML")
    parser.add_argument("code", help="股票代码, 如 688072")
    parser.add_argument("name", help="股票中文名, 如 拓荆科技")
    parser.add_argument("-s", "--start", default="20250101", help="开始日期 (默认 20250101)")
    parser.add_argument("-e", "--end", default=None, help="结束日期 (默认今天)")
    parser.add_argument("-o", "--out", default=None, help="输出HTML路径 (默认 stocks/<name>/<name>_k线.html)")
    args = parser.parse_args()

    df = fetch_kline(args.code, "daily", args.start, args.end)
    rows = [[str(r["date"]), float(r["open"]), float(r["close"]),
             float(r["low"]), float(r["high"]), int(r["volume"])]
            for _, r in df.iterrows()]
    html = (TEMPLATE.replace("__DATA__", json.dumps(rows, ensure_ascii=False))
                    .replace("__NAME__", args.name)
                    .replace("__CODE__", args.code))
    out = args.out or os.path.join("stocks", args.name, f"{args.name}_k线.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 已生成: {out}  ({len(rows)} 条K线, {df['date'].iloc[0]} ~ {df['date'].iloc[-1]})")

if __name__ == "__main__":
    main()
