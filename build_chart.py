#!/usr/bin/env python3
"""Inject data from 301526_data.json into chart HTML template."""
import json

with open("301526_data.json", "r") as f:
    data = json.load(f)

recent = data["kline"]["recent_100"]

with open("chart_301526.html", "r", encoding="utf-8") as f:
    html = f.read()

# Inject data as JS array
js_data = json.dumps(recent, ensure_ascii=False)
html = html.replace("const raw = /* INJECT */;", f"const raw = {js_data};")

with open("chart_301526.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Injected {len(recent)} data points into chart_301526.html")
