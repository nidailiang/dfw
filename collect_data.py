#!/usr/bin/env python3
"""采集 A 股基本面数据(第2层, 通用)

用法:
    python collect_data.py 688072 拓荆科技

输出:
    stocks/拓荆科技/拓荆科技_基本面.json   (10 类数据一次采集, 可被 analyze_fundamental 反复解读)

说明:
    采集本身是纯机器操作(akshare 公开接口), 不含任何分析判断
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_data import collect


def main():
    parser = argparse.ArgumentParser(description="采集 A 股基本面数据")
    parser.add_argument("code", help="股票代码, 如 688072")
    parser.add_argument("name", help="股票中文名, 如 拓荆科技")
    args = parser.parse_args()

    data = collect(args.code)  # 采集过程中会打印各类进度

    out = os.path.join("stocks", args.name, f"{args.name}_基本面.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✅ 已保存: {out}  耗时 {data.get('elapsed_sec')}s")
    print("下一步: python analyze_fundamental.py {} {}  (AI 解读)".format(args.code, args.name))


if __name__ == "__main__":
    main()
