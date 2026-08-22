#!/usr/bin/env python3
"""获取板块资金流数据 - 使用多个备用API"""
import requests
import json
import time
import sys

# 增加重试和备用域名
ENDPOINTS = [
    "https://push2.eastmoney.com/api/qt/clist/get",
    "https://push2his.eastmoney.com/api/qt/clist/get",
    "https://79.push2.eastmoney.com/api/qt/clist/get",
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://data.eastmoney.com/',
    'Accept': '*/*',
}

def try_fetch(fs, label, max_retries=3):
    """尝试多个endpoint获取数据"""
    params = {
        'pn': '1', 'pz': '20', 'po': '1', 'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2', 'invt': '2',
        'fid': 'f62',
        'fs': fs,
        'fields': 'f12,f14,f2,f3,f62,f184,f66,f69',
    }

    for endpoint in ENDPOINTS:
        for attempt in range(max_retries):
            try:
                r = requests.get(endpoint, params=params, headers=HEADERS, timeout=10)
                data = r.json()
                if data.get('data') and data['data'].get('diff'):
                    return data['data']['diff']
            except Exception:
                time.sleep(0.5)
                continue
        time.sleep(0.5)
    return None

# ── 1. 行业板块 ──
print("正在获取行业板块资金流...", file=sys.stderr)
items = try_fetch('m:90+t:2', '行业板块')
if items:
    print('=== 行业板块 主力资金净流入 TOP20 (2026-08-05) ===')
    print(f'{"排名":4s} {"行业名称":14s} {"涨跌幅":>8s} {"主力净流入":>10s} {"主力占比":>8s}')
    print('-' * 55)
    for i, item in enumerate(items[:20], 1):
        name = item.get('f14', '')
        pct_chg = item.get('f3', 0) or 0
        main_in = (item.get('f62', 0) or 0) / 1e8
        main_pct = (item.get('f184', 0) or 0)
        sign = '+' if main_in > 0 else ''
        print(f'{i:4d} {name:14s} {pct_chg:>+7.2f}% {sign}{main_in:>9.2f}亿 {main_pct:>+7.2f}%')
else:
    print("行业板块数据获取失败")

time.sleep(1)
print()

# ── 2. 概念板块（全量拉取后筛选相关） ──
print("正在获取概念板块资金流...", file=sys.stderr)
params2 = {
    'pn': '1', 'pz': '300', 'po': '1', 'np': '1',
    'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
    'fltt': '2', 'invt': '2',
    'fid': 'f62',
    'fs': 'm:90+t:3',
    'fields': 'f12,f14,f2,f3,f62,f184,f66,f69',
}

concepts = None
for endpoint in ENDPOINTS:
    try:
        r = requests.get(endpoint, params=params2, headers=HEADERS, timeout=10)
        data = r.json()
        if data.get('data') and data['data'].get('diff'):
            concepts = data['data']['diff']
            break
    except Exception:
        continue

if concepts:
    keywords = ['复合材料', '风电', '碳纤维', '玻纤', '化工', '新材料', '航天', '航空',
                '新能源', '军工', '大飞机', '叶片', '化纤', '树脂', '环氧', '高端装备',
                '专精特新', '创业板', '小盘']
    found = []
    for item in concepts:
        name = str(item.get('f14', ''))
        for kw in keywords:
            if kw in name:
                found.append(item)
                break

    found.sort(key=lambda x: x.get('f62', 0) or 0, reverse=True)

    print('=== 与 301526(国际复材) 相关板块资金流 ===')
    print(f'{"板块名称":20s} {"涨跌幅":>8s} {"主力净流入":>10s} {"超大单":>10s}')
    print('-' * 55)
    for item in found:
        name = item.get('f14', '')
        pct_chg = item.get('f3', 0) or 0
        main_in = (item.get('f62', 0) or 0) / 1e8
        super_large = (item.get('f66', 0) or 0) / 1e8
        sign = '+' if main_in > 0 else ''
        arrow = '🟢' if main_in > 1 else '🟡' if main_in > 0 else '🔴' if main_in < -1 else '⚪'
        print(f'{arrow} {name:18s} {pct_chg:>+7.2f}% {sign}{main_in:>9.2f}亿 {sign}{super_large:>9.2f}亿')

    # 再输出主力净流入最大的 TOP10 概念（不筛选）
    print()
    print('=== 概念板块 主力净流入 TOP15 (全部) ===')
    top = sorted(concepts, key=lambda x: x.get('f62', 0) or 0, reverse=True)[:15]
    print(f'{"排名":4s} {"板块名称":18s} {"涨跌幅":>8s} {"主力净流入":>10s}')
    print('-' * 50)
    for i, item in enumerate(top, 1):
        name = item.get('f14', '')
        pct_chg = item.get('f3', 0) or 0
        main_in = (item.get('f62', 0) or 0) / 1e8
        sign = '+' if main_in > 0 else ''
        print(f'{i:4d} {name:18s} {pct_chg:>+7.2f}% {sign}{main_in:>9.2f}亿')
else:
    print("概念板块数据获取失败")

time.sleep(1)
print()

# ── 3. 资金流出最多的概念板块 ──
print("正在获取资金流出板块...", file=sys.stderr)
if concepts:
    bottom = sorted(concepts, key=lambda x: x.get('f62', 0) or 0)[:10]
    print('=== 概念板块 主力净流出 TOP10 ===')
    print(f'{"排名":4s} {"板块名称":18s} {"涨跌幅":>8s} {"主力净流出":>10s}')
    print('-' * 50)
    for i, item in enumerate(bottom, 1):
        name = item.get('f14', '')
        pct_chg = item.get('f3', 0) or 0
        main_out = (item.get('f62', 0) or 0) / 1e8
        print(f'{i:4d} {name:18s} {pct_chg:>+7.2f}% {main_out:>9.2f}亿')
