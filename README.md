# DFW 股票数据分析

A 股个股数据分析,分三层:

- **第 1 层**:行情 + 技术指标(纯机器计算,无人工)
- **第 2 层**:财务基本面(机器采集 + AI 解读)
- **第 3 层**:资金面(数据源受限,暂缓)

## 脚本速查

### 一条龙(推荐)

| 脚本 | 用途 | 用法示例 |
|---|---|---|
| `analyze_one.py` | 全流程:图表 + 蒙特卡洛 + 采集 + AI 报告 | `python analyze_one.py 688072 拓荆科技` |

> 分步执行见下方表格,效果相同。

### 第 1 层:行情与技术指标

| 脚本 | 用途 | 用法示例 |
|---|---|---|
| `fetch_stock_kline.py` | 拉日K线 + 算指标(MA/MACD/KDJ/ATR/波动率),数据基础 | `python fetch_stock_kline.py 600519` |
| `chart_html.py` | 交互式K线图(HTML):白线/黄线或均线组切换 | `python chart_html.py 688072 拓荆科技` |
| `chart_kline.py` | matplotlib 静态K线图(备用) | `python chart_kline.py 600519` |
| `analyze_mc.py` | 蒙特卡洛模拟 1/3/6 个月价格区间(P5 参考止损) | `python analyze_mc.py 688072 拓荆科技` |
| `b1_check.py` | B1 策略止损检查(买入价 − k×ATR) | `python b1_check.py 688318 财富趋势 2.0` |
| `chip_distribution.py` | 筹码分布估算(未固化) | `python chip_distribution.py 688072 拓荆科技` |
| `analyze_688498.py` | 量价背离专项分析(暂留,待通用化) | `python analyze_688498.py` |

### 第 2 层:财务基本面

| 脚本 | 用途 | 用法示例 |
|---|---|---|
| `collect_data.py` | 采集 10 类基本面数据 → `stocks/<名>/<名>_基本面.json` | `python collect_data.py 688072 拓荆科技` |
| `analyze_fundamental.py` | AI 解读 json → 7 章报告 → `stocks/<名>/<名>_分析报告.md` | `python analyze_fundamental.py 688072 拓荆科技` |

> 第 2 层固定顺序:先 `collect_data.py` 采集,再 `analyze_fundamental.py` 解读。
> `stock_data.py` 是采集器实现,被 `collect_data.py` 调用,无需直接运行。

### 个人工具

| 脚本 | 用途 | 用法示例 |
|---|---|---|
| `check_holdings.py` | 检查持仓个股的涨跌/指标 | `python check_holdings.py` |

## 目录结构

```
dfw/
├── fetch_stock_kline.py   第1层: 数据基础
├── chart_html.py          第1层: 交互K线图
├── ...                    脚本见上表
├── stocks/                分析结果, 按股票中文名建子目录
│   └── 拓荆科技/
│       ├── 拓荆科技_k线.html
│       ├── 拓荆科技_基本面.json
│       ├── 拓荆科技_分析报告.md
│       └── 分析笔记.md
├── formulas/              通达信公式(规划合并 1.指标公式/2.选股公式/selection/technical)
├── setup/                 Claude Code 安装配置(与股票无关)
└── README.md
```

## 分析工作流

一条龙: `python analyze_one.py <代码> <中文名>`
(分步 = chart_html 看图 → analyze_mc 看区间 → collect_data 采集 → analyze_fundamental 出报告)

最后把人工判断写进 `stocks/<名>/分析笔记.md`(判断不进脚本)。
