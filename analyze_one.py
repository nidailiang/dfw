#!/usr/bin/env python3
"""一条龙分析脚本(第1层 + 第2层)

用法:
    python analyze_one.py 688072 拓荆科技          # 全流程: 图表 + 蒙特卡洛 + 采集 + AI报告
    python analyze_one.py 688072 拓荆科技 --no-ai  # 跳过 AI 解读(只采集)
    python analyze_one.py 688072 拓荆科技 --no-chart --no-mc  # 只做基本面

流程 = chart_html(K线图) → analyze_mc(价格区间) → collect_data(采集) → analyze_fundamental(AI解读)
产物都在 stocks/<中文名>/ 下
"""

import argparse
import os
import subprocess
import sys

PY = sys.executable
STEPS = [
    ("chart_html",     "📊 第1层: 交互K线图",      lambda c, n, o: [PY, "chart_html.py", c, n]),
    ("mc",             "🎲 第1层: 蒙特卡洛价格区间", lambda c, n, o: [PY, "analyze_mc.py", c, n]),
    ("collect",        "📥 第2层: 采集基本面数据",  lambda c, n, o: [PY, "collect_data.py", c, n]),
    ("ai",             "🤖 第2层: AI 解读报告",    lambda c, n, o: [PY, "analyze_fundamental.py", c, n]),
]


def main():
    parser = argparse.ArgumentParser(description="一条龙: 第1层技术面 + 第2层基本面")
    parser.add_argument("code", help="股票代码, 如 688072")
    parser.add_argument("name", help="股票中文名, 如 拓荆科技")
    parser.add_argument("--no-chart", action="store_true", help="跳过K线图")
    parser.add_argument("--no-mc", action="store_true", help="跳过蒙特卡洛")
    parser.add_argument("--no-ai", action="store_true", help="跳过AI解读(只采集数据)")
    args = parser.parse_args()

    skips = {"chart_html": args.no_chart, "mc": args.no_mc, "ai": args.no_ai}
    out_dir = os.path.join("stocks", args.name)

    print(f"🔍 开始分析 {args.name} ({args.code})")
    print(f"   产物目录: {out_dir}/\n")

    for key, title, cmd in STEPS:
        if skips.get(key):
            print(f"⏭️  {title} — 已跳过")
            continue
        print(f"\n{'='*56}\n  {title}\n{'='*56}")
        r = subprocess.run(cmd(args.code, args.name, None), cwd=os.path.dirname(os.path.abspath(__file__)))
        if r.returncode != 0:
            print(f"⚠️  {title} 退出码 {r.returncode}, 继续下一步")

    print(f"\n{'='*56}\n✅ 分析完成, 产物:\n{'='*56}")
    for f in sorted(os.listdir(out_dir)) if os.path.isdir(out_dir) else []:
        print(f"   {out_dir}/{f}")


if __name__ == "__main__":
    main()
