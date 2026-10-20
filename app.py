from flask import Flask, render_template_string
import requests
import pandas as pd
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import urllib3
import re
import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

headers = {"User-Agent": "Mozilla/5.0"}
ZODIACS = ["鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬"]
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://lottery_db_ij11_user:JaMLl91GOB9RLE04JfpxD4Cg6fJh1Bof@dpg-dbag28jrjlhs73a4p8n0-a/lottery_db_ij11")
START_DATE = "2026-10-13"

SIMP_TO_TRAD = {"猪": "豬", "鸡": "雞", "马": "馬", "龙": "龍"}

def normalize_zodiac(s):
    if not s: return ""
    s = str(s)
    for simp, trad in SIMP_TO_TRAD.items():
        s = s.replace(simp, trad)
    return re.sub(r"\s+", "", s)

MAP_2025 = {1:"蛇",2:"龍",3:"兔",4:"虎",5:"牛",6:"鼠",7:"豬",8:"狗",9:"雞",10:"猴",11:"羊",12:"馬",13:"蛇",14:"龍",15:"兔",16:"虎",17:"牛",18:"鼠",19:"豬",20:"狗",21:"雞",22:"猴",23:"羊",24:"馬",25:"蛇",26:"龍",27:"兔",28:"虎",29:"牛",30:"鼠",31:"豬",32:"狗",33:"雞",34:"猴",35:"羊",36:"馬",37:"蛇",38:"龍",39:"兔",40:"虎",41:"牛",42:"鼠",43:"豬",44:"狗",45:"雞",46:"猴",47:"羊",48:"馬",49:"蛇"}
MAP_2026 = {1:"馬",2:"蛇",3:"龍",4:"兔",5:"虎",6:"牛",7:"鼠",8:"豬",9:"狗",10:"雞",11:"猴",12:"羊",13:"馬",14:"蛇",15:"龍",16:"兔",17:"虎",18:"牛",19:"鼠",20:"豬",21:"狗",22:"雞",23:"猴",24:"羊",25:"馬",26:"蛇",27:"龍",28:"兔",29:"虎",30:"牛",31:"鼠",32:"豬",33:"狗",34:"雞",35:"猴",36:"羊",37:"馬",38:"蛇",39:"龍",40:"兔",41:"虎",42:"牛",43:"鼠",44:"豬",45:"狗",46:"雞",47:"猴",48:"羊",49:"馬"}
YEAR_MAPS = {2025: MAP_2025, 2026: MAP_2026}

def get_db(): return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, region TEXT, date TEXT, expect TEXT, based_on TEXT, long_miss TEXT, frequent_next TEXT, next_expect TEXT, actual_zodiacs TEXT, hit_long_miss BOOLEAN, hit_frequent BOOLEAN)""")
    conn.commit()
    cur.close()
    conn.close()

def load_records():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM records")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"key": r["key"], "region": r["region"], "date": r["date"], "expect": r["expect"], "based_on": r["based_on"], "long_miss": json.loads(r["long_miss"]) if r["long_miss"] else [], "frequent_next": json.loads(r["frequent_next"]) if r["frequent_next"] else [], "next_expect": r["next_expect"], "actual_zodiacs": json.loads(r["actual_zodiacs"]) if r["actual_zodiacs"] else None, "hit_long_miss": r["hit_long_miss"], "hit_frequent": r["hit_frequent"]} for r in rows]
    except:
        return []

def save_records(records):
    try:
        conn = get_db()
        cur = conn.cursor()
        for rec in records:
            cur.execute("""INSERT INTO records (key, region, date, expect, based_on, long_miss, frequent_next, next_expect, actual_zodiacs, hit_long_miss, hit_frequent) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (key) DO UPDATE SET next_expect=EXCLUDED.next_expect, actual_zodiacs=EXCLUDED.actual_zodiacs, hit_long_miss=EXCLUDED.hit_long_miss, hit_frequent=EXCLUDED.hit_frequent""", (rec.get("key"), rec.get("region"), rec.get("date"), rec.get("expect"), rec.get("based_on"), json.dumps(rec.get("long_miss",[]), ensure_ascii=False), json.dumps(rec.get("frequent_next",[]), ensure_ascii=False), rec.get("next_expect"), json.dumps(rec.get("actual_zodiacs"), ensure_ascii=False) if rec.get("actual_zodiacs") else None, rec.get("hit_long_miss"), rec.get("hit_frequent")))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("save error:", e)

def get_macau_latest():
    try:
        r = requests.get("https://macaumarksix.com/api/macaujc2.com", headers=headers, timeout=10)
        data = r.json()
        return data[0] if isinstance(data, list) and data else None
    except:
        return None

def get_macau_year_history(year):
    try:
        r = requests.get(f"https://history.macaumarksix.com/history/macaujc2/y/{year}", headers=headers, timeout=15)
        data = r.json()
        return data.get("data", []) if data.get("result") else []
    except:
        return []

def get_hk_data():
    try:
        r = requests.get("https://marksix6.net/index.php?api=1", headers=headers, timeout=15, verify=False)
        data = r.json()
        for item in data.get("lottery_data", []):
            if item.get("name") == "香港彩":
                return item
        return None
    except:
        return None

def get_old_macau_data():
    try:
        r = requests.get("https://marksix6.net/index.php?api=1", headers=headers, timeout=15, verify=False)
        data = r.json()
        for item in data.get("lottery_data", []):
            if item.get("name") == "澳门彩":
                return item
        return None
    except:
        return None

def parse_zodiacs(s):
    if not s or pd.isna(s): return set()
    s = normalize_zodiac(str(s))
    return {x for x in [p.strip() for p in s.split(",") if p.strip()] if x in ZODIACS}

def parse_zodiacs_list(s):
    if not s or pd.isna(s): return []
    s = normalize_zodiac(str(s))
    return [x for x in [p.strip() for p in s.split(",") if p.strip()] if x in ZODIACS]

def get_omission_streaks(sets, zodiac):
    streaks, current = [], 0
    for s in sets:
        if zodiac in s:
            if current > 0: streaks.append(current)
            current = 0
        else:
            current += 1
    if current > 0: streaks.append(current)
    return streaks

def build_zodiac_numbers(df):
    mapping = defaultdict(set)
    for _, row in df.tail(100).iterrows():
        codes = str(row.get("openCode", "")).split(",")
        zodiacs = str(row.get("zodiac", "")).split(",")
        for code, zod in zip(codes, zodiacs):
            code, zod = code.strip(), normalize_zodiac(zod.strip())
            if code.isdigit() and zod in ZODIACS:
                mapping[zod].add(int(code))
    return {z: sorted(mapping.get(z, [])) for z in ZODIACS}

def get_next_draw_date(latest, is_hk=False):
    if not latest or not latest.get("openTime"): return ""
    try:
        dt = datetime.strptime(latest["openTime"][:10], "%Y-%m-%d")
        next_dt = dt + timedelta(days=1)
        if is_hk:
            while next_dt.weekday() not in (1, 3, 5):
                next_dt += timedelta(days=1)
        return next_dt.strftime("%Y-%m-%d")
    except:
        return ""

def get_next_expect(latest):
    if not latest or not latest.get("expect"): return ""
    try: return str(int(latest["expect"]) + 1)
    except: return ""

def fill_zodiac_by_year(open_code, expect):
    year = int(str(expect)[:4]) if expect and len(str(expect)) >= 4 else None
    num_to_zod = YEAR_MAPS.get(year)
    if not num_to_zod: return ""
    return ",".join([num_to_zod.get(int(c), "") for c in str(open_code).split(",") if c.strip().isdigit() and num_to_zod.get(int(c))])

def record_recommendation(region, latest, result):
    if not latest or not latest.get("openTime"): return
    next_date = get_next_draw_date(latest, region == "hk")
    if not next_date or next_date < START_DATE: return
    records = load_records()
    try: next_expect = str(int(latest["expect"]) + 1)
    except: next_expect = latest["expect"]
    key = f"{region}_{next_expect}"
    if key in {r.get("key") for r in records}: return
    records.append({"key": key, "region": region, "date": next_date, "expect": next_expect, "based_on": latest["expect"], "long_miss": [item["zodiac"] for item in result.get("long_miss_recs", [])], "frequent_next": [{"zodiac": item["zodiac"], "count": item["count"]} for item in result.get("frequent_next_recs", [])], "next_expect": None, "actual_zodiacs": None, "hit_long_miss": None, "hit_frequent": None})
    save_records(records)

def update_hit_rates(region, latest):
    if not latest or not latest.get("expect"): return
    records = load_records()
    updated = False
    current_expect = str(latest["expect"])
    actual_set = parse_zodiacs(latest.get("zodiac", ""))
    actual_list = parse_zodiacs_list(latest.get("zodiac", ""))
    for rec in records:
        if rec["region"] != region: continue
        if rec.get("next_expect") is None and rec.get("expect") == current_expect:
            rec["next_expect"] = current_expect
            rec["actual_zodiacs"] = actual_list
            long_miss_set = set(rec.get("long_miss", []))
            frequent_set = {x["zodiac"] for x in rec.get("frequent_next", [])}
            rec["hit_long_miss"] = bool(long_miss_set & actual_set) if long_miss_set else None
            rec["hit_frequent"] = bool(frequent_set & actual_set) if frequent_set else None
            updated = True
    if updated: save_records(records)

def get_hot_cold_numbers(df, n=50):
    recent = df.tail(n)
    number_count = Counter()
    for _, row in recent.iterrows():
        for code in str(row.get("openCode", "")).split(","):
            if code.strip().isdigit(): number_count[int(code.strip())] += 1
    hot = [num for num, cnt in number_count.most_common(10)]
    all_nums = set(range(1, 50))
    cold = sorted([n for n in all_nums if number_count.get(n, 0) == 0])[:10]
    if len(cold) < 5: cold = [num for num, cnt in number_count.most_common()[-10:]]
    return hot, cold

def get_top_with_ties(counter, n=3):
    if not counter: return []
    sorted_items = counter.most_common()
    if len(sorted_items) <= n: return sorted_items
    threshold = sorted_items[n - 1][1]
    return [(item, cnt) for item, cnt in sorted_items if cnt >= threshold]

def format_numbers_with_color(num_str, hot_set, cold_set):
    if not num_str: return ""
    parts = []
    for n in num_str.split("、"):
        n = n.strip()
        if n.isdigit():
            num = int(n)
            if num in hot_set: parts.append(f'<span class="num-bg-hot">{n}</span>')
            elif num in cold_set: parts.append(f'<span class="num-bg-cold">{n}</span>')
            else: parts.append(n)
        else: parts.append(n)
    return "、".join(parts)

def build_ball_display(open_code, zodiac, wave):
    if not open_code: return ""
    codes = [c.strip() for c in str(open_code).split(",") if c.strip()]
    zodiacs = [normalize_zodiac(z.strip()) for z in str(zodiac).split(",") if z.strip()] if zodiac else []
    waves = [w.strip().lower() for w in str(wave).split(",") if w.strip()] if wave else []
    html = '<div class="ball-row">'
    for i, code in enumerate(codes):
        w = waves[i] if i < len(waves) else "red"
        z = zodiacs[i] if i < len(zodiacs) else ""
        color_class = {"red": "ball-red", "blue": "ball-blue", "green": "ball-green"}.get(w, "ball-red")
        if i == 6: html += '<span class="ball-plus">+</span>'
        html += f'<div class="ball-item"><div class="ball {color_class}">{code}</div><div class="ball-zodiac">{z}</div></div>'
    return html + '</div>'

HTML = """
<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }}</title>
<link rel="apple-touch-icon" href="https://i.imgur.com/2kwwDW8.jpeg">
<meta property="og:title" content="王大师六预测">
<meta property="og:image" content="https://i.imgur.com/2kwwDW8.jpeg">
<meta property="og:description" content="新澳門、舊澳門、香港六合彩生肖預測">
<meta name="format-detection" content="telephone=no, date=no, address=no, email=no">
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/opencc-js@1.0.5/dist/umd/full.js"></script>
<style>
body { font-family: "Microsoft JhengHei", sans-serif; margin: 10px; background: #f5f5f5; position: relative; color: #222; transition: background 0.3s, color 0.3s; }
body.dark { background: #1a1a1a; color: #e0e0e0; }
.container { max-width: 1200px; margin: auto; }
h1 { color: #222; text-align: left; font-size: 2em; font-weight: 900; margin: 8px 0 12px 0; letter-spacing: 1px; }
body.dark h1 { color: #e0e0e0; }
.nav { margin-bottom: 12px; display: flex; flex-wrap: wrap; gap: 8px; }
.nav a { display: inline-block; padding: 8px 16px; font-size: 0.95em; font-weight: bold; color: white; text-decoration: none; border-radius: 6px; background: #4a90d9; }
.nav a:hover { background: #357abd; }
.nav a.active { background: #e74c3c; }
.card { background: white; padding: 12px; margin: 8px 0; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.1); position: relative; }
body.dark .card { background: #2d2d2d; color: #e0e0e0; box-shadow: 0 1px 3px rgba(0,0,0,.3); }
.top-row { display: flex; gap: 12px; margin: 12px 0; flex-wrap: wrap; }
.top-row .card { flex: 1; min-width: 280px; }
.row { display: flex; gap: 12px; margin: 12px 0; flex-wrap: wrap; }
.row .card { flex: 1; min-width: 200px; }
table { width: 100%; border-collapse: collapse; margin-top: 6px; font-size: 0.9em; }
th, td { border: 1px solid #ddd; padding: 6px; text-align: center; }
body.dark th, body.dark td { border-color: #444; }
th { background: #4a90d9; color: white; }
tr:nth-child(even) { background: #f9f9f9; }
body.dark tr:nth-child(even) { background: #3a3a3a; }
#macau-frame table, #oldmacau-frame table, #hk-frame table { table-layout: fixed; }
#macau-frame th:nth-child(1), #oldmacau-frame th:nth-child(1), #hk-frame th:nth-child(1) { width: 12%; }
#macau-frame th:nth-child(2), #oldmacau-frame th:nth-child(2), #hk-frame th:nth-child(2) { width: 10%; }
#macau-frame th:nth-child(3), #oldmacau-frame th:nth-child(3), #hk-frame th:nth-child(3) { width: 10%; }
#macau-frame th:nth-child(4), #oldmacau-frame th:nth-child(4), #hk-frame th:nth-child(4) { width: 22%; }
#macau-frame th:nth-child(5), #oldmacau-frame th:nth-child(5), #hk-frame th:nth-child(5) { width: 26%; }
#macau-frame th:nth-child(6), #oldmacau-frame th:nth-child(6), #hk-frame th:nth-child(6) { width: 10%; }
#macau-frame th:nth-child(7), #oldmacau-frame th:nth-child(7), #hk-frame th:nth-child(7) { width: 10%; }
.hot { color: #ff1a1a; font-weight: 900; font-size: 1.3em; text-shadow: 0 0 1px #ff1a1a; }
.zodiac-hot { color: #ff1a1a; font-weight: 900; font-size: 1.2em; text-shadow: 0 0 1px #ff1a1a; }
.green-hot { color: #27ae60; font-weight: 900; font-size: 1.2em; text-shadow: 0 0 1px #27ae60; }
.num-hot { color: #ff1a1a; font-weight: 900; font-size: 1.1em; text-shadow: 0 0 1px #ff1a1a; }
.num-green { color: #27ae60; font-weight: 900; font-size: 1.1em; text-shadow: 0 0 1px #27ae60; }
.num-bg-hot { background: #ffe0e0; color: #e74c3c; font-weight: 900; padding: 2px 6px; border-radius: 4px; }
.num-bg-cold { background: #e0f0ff; color: #3498db; font-weight: 900; padding: 2px 6px; border-radius: 4px; }
.recommend { font-size: 1em; line-height: 1.7; }
.recommend .item { margin: 5px 0; }
.recommend h3 { margin: 10px 0 4px 0; font-size: 0.95em; color: #333; }
body.dark .recommend h3 { color: #ccc; }
.note { color: #888; font-size: 0.85em; margin-top: 20px; text-align: center; }
body.dark .note { color: #aaa; }
h2 { margin: 0 0 8px 0; font-size: 1.05em; }
#latest-card h2 { font-size: 1.4em; margin-bottom: 12px; }
.next-date { position: absolute; top: 10px; right: 12px; font-size: 0.9em; font-weight: bold; color: #333; }
body.dark .next-date { color: #ccc; }
.count-summary { position: absolute; top: 10px; right: 12px; font-size: 0.85em; font-weight: bold; color: #333; background: #f0f0f0; padding: 4px 8px; border-radius: 4px; }
body.dark .count-summary { background: #3a3a3a; color: #ccc; }
.count-green { color: #27ae60; font-weight: 900; }
#export-btn { position: fixed; top: 50px; right: 10px; background: #4a90d9; color: white; border: none; padding: 8px 14px; font-size: 0.9em; font-weight: bold; border-radius: 6px; cursor: pointer; z-index: 1000; box-shadow: 0 2px 6px rgba(0,0,0,.2); }
#export-btn:hover { background: #357abd; }
#export-latest-btn { position: fixed; top: 10px; right: 10px; background: #e74c3c; color: white; border: none; padding: 8px 14px; font-size: 0.9em; font-weight: bold; border-radius: 6px; cursor: pointer; z-index: 1000; box-shadow: 0 2px 6px rgba(0,0,0,.2); }
#export-latest-btn:hover { opacity: 0.85; }
#lang-btn { position: fixed; top: 10px; left: 10px; background: #5cb85c; color: white; border: none; padding: 8px 14px; font-size: 0.9em; font-weight: bold; border-radius: 6px; cursor: pointer; z-index: 1000; box-shadow: 0 2px 6px rgba(0,0,0,.2); }
#lang-btn:hover { background: #4cae4c; }
#dark-btn { position: fixed; top: 50px; left: 10px; background: #555; color: white; border: none; padding: 8px 14px; font-size: 0.9em; font-weight: bold; border-radius: 6px; cursor: pointer; z-index: 1000; box-shadow: 0 2px 6px rgba(0,0,0,.2); }
#dark-btn:hover { background: #444; }
body.dark #dark-btn { background: #888; }
#capture-area { background: #f5f5f5; padding: 10px; }
body.dark #capture-area { background: #1a1a1a; }
.transition-table td:first-child { font-weight: bold; width: 60px; }
.match-green { color: #27ae60; font-weight: bold; }
.number-grid { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.number-item { background: #f0f0f0; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.95em; }
body.dark .number-item { background: #3a3a3a; color: #e0e0e0; }
.number-item.hot-num { background: #ffe0e0; color: #e74c3c; }
.number-item.cold-num { background: #e0f0ff; color: #3498db; }
body.dark .number-item.hot-num { background: #5a2a2a; color: #ff6b6b; }
body.dark .number-item.cold-num { background: #2a3a5a; color: #6bb3ff; }
.screenshot-btns { margin-bottom: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
.screenshot-btns button { border: none; padding: 8px 14px; font-size: 0.9em; font-weight: bold; border-radius: 6px; cursor: pointer; color: white; }
.screenshot-btns button:hover { opacity: 0.85; }
.screenshot-btns button:disabled { opacity: 0.6; cursor: not-allowed; }
.ball-row { display: flex; align-items: center; justify-content: flex-start; gap: 10px; flex-wrap: wrap; margin: 15px 0; }
.ball-item { display: flex; flex-direction: column; align-items: center; }
.ball { width: 56px; height: 56px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 1.4em; color: white; }
.ball-red { background: #e74c3c; }
.ball-blue { background: #3498db; }
.ball-green { background: #27ae60; }
.ball-zodiac { font-size: 1em; margin-top: 6px; font-weight: bold; }
.ball-plus { font-size: 2em; font-weight: bold; color: #333; margin: 0 6px; }
body.dark .ball-plus { color: #ccc; }
.latest-info { text-align: left; margin-bottom: 8px; font-size: 1.1em; font-weight: bold; }
.latest-info p { margin: 6px 0; }
a[x-apple-data-detectors] { color: inherit !important; text-decoration: none !important; font-weight: inherit !important; }
@media (max-width: 768px) {
  body { margin: 5px; }
  h1 { font-size: 1.4em; margin-top: 90px; }
  .top-row, .row { flex-direction: column; }
  .top-row .card, .row .card { min-width: 100%; }
  table { font-size: 0.75em; }
  th, td { padding: 3px; }
  #export-btn, #export-latest-btn, #lang-btn, #dark-btn { padding: 6px 10px; font-size: 0.75em; position: static; margin: 4px; }
  #lang-btn { float: left; }
  #dark-btn { float: left; clear: left; }
  #export-latest-btn { float: right; }
  #export-btn { float: right; clear: right; }
  .nav { margin-top: 40px; gap: 4px; }
  .nav a { padding: 6px 10px; font-size: 0.8em; }
  .count-summary { position: static; margin-top: 8px; display: inline-block; }
  .screenshot-btns { margin-top: 8px; }
  .screenshot-btns button { padding: 6px 10px; font-size: 0.8em; }
  .ball { width: 42px; height: 42px; font-size: 1.2em; }
}
</style>
</head>
<body>
<button id="lang-btn" onclick="toggleLang()">繁體</button>
<button id="dark-btn" onclick="toggleDark()">深色</button>
<button id="export-latest-btn" onclick="exportLatest()">複製賽果</button>
<button id="export-btn" onclick="exportImage()">複製預測</button>
<div class="container">
<div id="capture-area">
<div class="nav" id="nav-buttons">
  <a href="/" class="{{ 'active' if region == 'macau' else '' }}">新澳門版</a>
  <a href="/oldmacau" class="{{ 'active' if region == 'oldmacau' else '' }}">舊澳門版</a>
  <a href="/hk" class="{{ 'active' if region == 'hk' else '' }}">香港版</a>
  <a href="/records" class="{{ 'active' if region == 'records' else '' }}">預測記錄</a>
</div>
<h1>{{ title }}</h1>
{% if region != 'records' %}
<div class="top-row">
  <div class="card" id="latest-card">
    <h2>最新一期中獎號碼</h2>
    {% if latest %}
    <div class="latest-info">
      <p><b>期號：{{ latest.expect }}　時間：{{ latest.openTime }}</b></p>
    </div>
    {{ ball_display|safe }}
    {% else %}
    <p>無法取得最新數據</p>
    {% endif %}
  </div>
  <div class="card" id="recommend-card">
    {% if next_expect %}<div class="next-date">期號：{{ next_expect }}　{{ next_date }}</div>{% endif %}
    <h2>王大師預測（{{ '新澳門' if region == 'macau' else '舊澳門' if region == 'oldmacau' else '香港' }}）</h2>
    <div class="recommend">
      <h3>遺漏回補</h3>
      {% if long_miss_recs %}
        {% for item in long_miss_recs %}
        <div class="item"><span class="zodiac-hot">{{ item.zodiac }}</span>：<span class="num-hot">{{ item.numbers_html|safe }}</span></div>
        {% endfor %}
      {% else %}<p style="margin:4px 0;">目前沒有</p>{% endif %}
      <h3>接續熱門</h3>
      {% if frequent_next_recs %}
        {% for item in frequent_next_recs %}
        <div class="item"><span class="green-hot">{{ item.zodiac }}({{ item.count }})</span>：<span class="num-green">{{ item.numbers_html|safe }}</span></div>
        {% endfor %}
      {% else %}<p style="margin:4px 0;">目前沒有</p>{% endif %}
    </div>
    <p style="font-size:0.8em; margin-top:8px;">熱門號碼（紅色）出現次數較多，冷門號碼（藍色）較少出現。</p>
    <p style="font-size:0.8em; margin-top:4px;">數據僅供參考，彩票結果隨機，過往統計不代表未來結果。</p>
  </div>
</div>
<div class="card">
  <h2>近 50 期號碼統計</h2>
  <p style="font-size:0.85em; margin:0 0 6px;">熱門號碼（紅色）出現次數較多，冷門號碼（藍色）較少出現。</p>
  <div class="number-grid">
    {% for num in hot_numbers %}<span class="number-item hot-num">{{ "%02d"|format(num) }}</span>{% endfor %}
    {% for num in cold_numbers %}<span class="number-item cold-num">{{ "%02d"|format(num) }}</span>{% endfor %}
  </div>
</div>
<div class="row">
  <div class="card">
    <h2>2025-2026 出現期數</h2>
    <table><tr><th>生肖</th><th>出現期數</th></tr>
    {% for z, cnt in appear %}<tr><td class="{{ 'zodiac-hot' if z in long_miss_set else '' }}">{{ z }}</td><td class="{{ 'hot' if cnt > full_avg else '' }}">{{ cnt }}</td></tr>{% endfor %}
    </table>
    <p style="font-size:0.8em; color:#666; margin:4px 0 0;">平均：{{ "%.1f"|format(full_avg) }}</p>
  </div>
  <div class="card">
    <h2>近 50 日出現期數</h2>
    <table><tr><th>生肖</th><th>出現期數</th></tr>
    {% for z, cnt in recent %}<tr><td class="{{ 'zodiac-hot' if z in long_miss_set else '' }}">{{ z }}</td><td class="{{ 'hot' if cnt > recent_avg else '' }}">{{ cnt }}</td></tr>{% endfor %}
    </table>
    <p style="font-size:0.8em; color:#666; margin:4px 0 0;">平均：{{ "%.1f"|format(recent_avg) }}</p>
  </div>
  <div class="card">
    <h2>遺漏天數</h2>
    <table><tr><th>生肖</th><th>不見天數</th></tr>
    {% for item in omission %}<tr><td class="{{ 'zodiac-hot' if item.z in long_miss_set else '' }}">{{ item.z }}</td><td class="{{ 'hot' if item.miss >= 3 else '' }}">{{ item.miss }}</td></tr>{% endfor %}
    </table>
  </div>
</div>
<div class="card">
  {% if count_summary %}<div class="count-summary">數量: {{ count_summary|safe }}</div>{% endif %}
  <h2>2025-2026 接續熱門統計（Top 3）</h2>
  <p style="font-size:0.8em; color:#666; margin:0 0 6px;">排序：按下一期 Top 3 次數加總由大到小（相同次數全部顯示）</p>
  <table class="transition-table"><tr><th>上一期</th><th>下一期最常出現</th></tr>
  {% for item in transitions %}
  <tr><td class="{{ 'green-hot' if item.prev in latest_zodiacs else '' }}">{{ item.prev }}</td>
    <td style="text-align:left;">{% for part in item.next_parts %}{% if item.prev in latest_zodiacs %}<span class="{{ 'green-hot' if part.zodiac in green_next else 'zodiac-hot' if part.zodiac in long_miss_set else '' }}">{{ part.text }}</span>{% else %}<span>{{ part.text }}</span>{% endif %}{% if not loop.last %}、{% endif %}{% endfor %}</td></tr>
  {% endfor %}
  </table>
</div>
<div class="card">
  {% if count_summary_2026 %}<div class="count-summary">數量: {{ count_summary_2026|safe }}</div>{% endif %}
  <h2>2026 接續熱門統計（Top 3）</h2>
  <p style="font-size:0.8em; color:#666; margin:0 0 6px;">只使用 2026 年數據計算（相同次數全部顯示）</p>
  <table class="transition-table"><tr><th>上一期</th><th>下一期最常出現</th></tr>
  {% for item in transitions_2026 %}
  <tr><td class="{{ 'green-hot' if item.prev in latest_zodiacs else '' }}">{{ item.prev }}</td>
    <td style="text-align:left;">{% for part in item.next_parts %}{% if item.prev in latest_zodiacs %}<span class="{{ 'green-hot' if part.zodiac in green_next_2026 else '' }}">{{ part.text }}</span>{% else %}<span>{{ part.text }}</span>{% endif %}{% if not loop.last %}、{% endif %}{% endfor %}</td></tr>
  {% endfor %}
  </table>
</div>
<div class="card">
<h2>2025-2026 連續遺漏分布（按平均由大到小）</h2>
<table><tr><th>生肖</th><th>平均遺漏</th><th>最長</th><th>分布</th></tr>
{% for item in streaks %}<tr><td>{{ item.z }}</td><td>{{ "%.1f"|format(item.avg) }}</td><td>{{ item.max }}</td><td style="text-align:left; font-size:0.85em;">{{ item.dist }}</td></tr>{% endfor %}
</table>
</div>
{% else %}
<div class="screenshot-btns">
  <button onclick="exportFrame('macau-frame', this)" style="background:#4a90d9;">截圖新澳門</button>
  <button onclick="exportFrame('oldmacau-frame', this)" style="background:#5cb85c;">截圖舊澳門</button>
  <button onclick="exportFrame('hk-frame', this)" style="background:#f0ad4e;">截圖香港</button>
</div>
<div class="card" id="macau-frame">
<h2>新澳門預測記錄（自 2026-10-13）</h2>
<p style="font-size:0.9em;">總記錄：{{ macau_settled }} 筆　已開獎：{{ macau_settled }} 筆<br>遺漏回補命中率：{{ "%.1f"|format(macau_long_miss_rate) }}%（{{ macau_long_miss_hits }}/{{ macau_long_miss_total }}）<br>接續熱門命中率：{{ "%.1f"|format(macau_frequent_rate) }}%（{{ macau_frequent_hits }}/{{ macau_frequent_total }}）<br>總命中率：{{ "%.1f"|format(macau_total_rate) }}%（{{ macau_total_hits }}/{{ macau_total_predictions }}）<br>1/4 Kelly：{{ "%.1f"|format(macau_kelly) }}%</p>
<table><tr><th>日期</th><th>期號</th><th>遺漏回補</th><th>接續熱門</th><th>中獎生肖</th><th>遺漏回補命中</th><th>接續熱門命中</th></tr>
{% for r in macau_records %}<tr><td>{{ r.date }}</td><td>{{ r.expect }}</td><td>{% if r.long_miss %}{% for z in r.long_miss %}<span class="zodiac-hot">{{ z }}</span>{% if not loop.last %}、{% endif %}{% endfor %}{% else %}/{% endif %}</td><td>{% if r.frequent_next %}{% set actual_set = r.actual_zodiacs | unique | list if r.actual_zodiacs else [] %}{% for item in r.frequent_next %}{% if item.zodiac in actual_set %}<span class="match-green">{{ item.zodiac }}({{ item.count }})</span>{% else %}{{ item.zodiac }}({{ item.count }}){% endif %}{% if not loop.last %}、{% endif %}{% endfor %}{% else %}/{% endif %}</td><td>{% if r.actual_zodiacs %}{% set long_set = r.long_miss | list %}{% set freq_set = r.frequent_next | map(attribute='zodiac') | list %}{% for z in r.actual_zodiacs %}{% if z in long_set %}<span class="zodiac-hot">{{ z }}</span>{% elif z in freq_set %}<span class="match-green">{{ z }}</span>{% else %}{{ z }}{% endif %}{% if not loop.last %}、{% endif %}{% endfor %}{% else %}<span class="zodiac-hot">未開獎</span>{% endif %}</td><td>{{ r.lm_text if r.actual_zodiacs else '/' }}</td><td>{{ r.fn_text if r.actual_zodiacs else '/' }}</td></tr>{% endfor %}
</table></div>
<div class="card" id="oldmacau-frame">
<h2>舊澳門預測記錄（自 2026-10-13）</h2>
<p style="font-size:0.9em;">總記錄：{{ oldmacau_settled }} 筆　已開獎：{{ oldmacau_settled }} 筆<br>遺漏回補命中率：{{ "%.1f"|format(oldmacau_long_miss_rate) }}%（{{ oldmacau_long_miss_hits }}/{{ oldmacau_long_miss_total }}）<br>接續熱門命中率：{{ "%.1f"|format(oldmacau_frequent_rate) }}%（{{ oldmacau_frequent_hits }}/{{ oldmacau_frequent_total }}）<br>總命中率：{{ "%.1f"|format(oldmacau_total_rate) }}%（{{ oldmacau_total_hits }}/{{ oldmacau_total_predictions }}）<br>1/4 Kelly：{{ "%.1f"|format(oldmacau_kelly) }}%</p>
<table><tr><th>日期</th><th>期號</th><th>遺漏回補</th><th>接續熱門</th><th>中獎生肖</th><th>遺漏回補命中</th><th>接續熱門命中</th></tr>
{% for r in oldmacau_records %}<tr><td>{{ r.date }}</td><td>{{ r.expect }}</td><td>{% if r.long_miss %}{% for z in r.long_miss %}<span class="zodiac-hot">{{ z }}</span>{% if not loop.last %}、{% endif %}{% endfor %}{% else %}/{% endif %}</td><td>{% if r.frequent_next %}{% set actual_set = r.actual_zodiacs | unique | list if r.actual_zodiacs else [] %}{% for item in r.frequent_next %}{% if item.zodiac in actual_set %}<span class="match-green">{{ item.zodiac }}({{ item.count }})</span>{% else %}{{ item.zodiac }}({{ item.count }}){% endif %}{% if not loop.last %}、{% endif %}{% endfor %}{% else %}/{% endif %}</td><td>{% if r.actual_zodiacs %}{% set long_set = r.long_miss | list %}{% set freq_set = r.frequent_next | map(attribute='zodiac') | list %}{% for z in r.actual_zodiacs %}{% if z in long_set %}<span class="zodiac-hot">{{ z }}</span>{% elif z in freq_set %}<span class="match-green">{{ z }}</span>{% else %}{{ z }}{% endif %}{% if not loop.last %}、{% endif %}{% endfor %}{% else %}<span class="zodiac-hot">未開獎</span>{% endif %}</td><td>{{ r.lm_text if r.actual_zodiacs else '/' }}</td><td>{{ r.fn_text if r.actual_zodiacs else '/' }}</td></tr>{% endfor %}
</table></div>
<div class="card" id="hk-frame">
<h2>香港預測記錄（自 2026-10-13）</h2>
<p style="font-size:0.9em;">總記錄：{{ hk_settled }} 筆　已開獎：{{ hk_settled }} 筆<br>遺漏回補命中率：{{ "%.1f"|format(hk_long_miss_rate) }}%（{{ hk_long_miss_hits }}/{{ hk_long_miss_total }}）<br>接續熱門命中率：{{ "%.1f"|format(hk_frequent_rate) }}%（{{ hk_frequent_hits }}/{{ hk_frequent_total }}）<br>總命中率：{{ "%.1f"|format(hk_total_rate) }}%（{{ hk_total_hits }}/{{ hk_total_predictions }}）<br>1/4 Kelly：{{ "%.1f"|format(hk_kelly) }}%</p>
<table><tr><th>日期</th><th>期號</th><th>遺漏回補</th><th>接續熱門</th><th>中獎生肖</th><th>遺漏回補命中</th><th>接續熱門命中</th></tr>
{% for r in hk_records %}<tr><td>{{ r.date }}</td><td>{{ r.expect }}</td><td>{% if r.long_miss %}{% for z in r.long_miss %}<span class="zodiac-hot">{{ z }}</span>{% if not loop.last %}、{% endif %}{% endfor %}{% else %}/{% endif %}</td><td>{% if r.frequent_next %}{% set actual_set = r.actual_zodiacs | unique | list if r.actual_zodiacs else [] %}{% for item in r.frequent_next %}{% if item.zodiac in actual_set %}<span class="match-green">{{ item.zodiac }}({{ item.count }})</span>{% else %}{{ item.zodiac }}({{ item.count }}){% endif %}{% if not loop.last %}、{% endif %}{% endfor %}{% else %}/{% endif %}</td><td>{% if r.actual_zodiacs %}{% set long_set = r.long_miss | list %}{% set freq_set = r.frequent_next | map(attribute='zodiac') | list %}{% for z in r.actual_zodiacs %}{% if z in long_set %}<span class="zodiac-hot">{{ z }}</span>{% elif z in freq_set %}<span class="match-green">{{ z }}</span>{% else %}{{ z }}{% endif %}{% if not loop.last %}、{% endif %}{% endfor %}{% else %}<span class="zodiac-hot">未開獎</span>{% endif %}</td><td>{{ r.lm_text if r.actual_zodiacs else '/' }}</td><td>{{ r.fn_text if r.actual_zodiacs else '/' }}</td></tr>{% endfor %}
</table></div>
{% endif %}
<p class="note">數據僅供參考，彩票結果隨機，過往統計不代表未來結果。<br>{{ note_extra }}</p>
</div>
<script>
let isTraditional = false;
let isDark = localStorage.getItem('darkMode') === 'true';
const converter = OpenCC.Converter({ from: 'cn', to: 'tw' });
const converterBack = OpenCC.Converter({ from: 'tw', to: 'cn' });

window.onload = function() {
  if (!isTraditional) walkAndConvert(document.body, converterBack);
  if (isDark) {
    document.body.classList.add('dark');
    document.getElementById('dark-btn').innerText = '淺色';
  }
};

function toggleLang() {
  const btn = document.getElementById('lang-btn');
  if (isTraditional) { walkAndConvert(document.body, converterBack); btn.innerText = '繁體'; isTraditional = false; }
  else { walkAndConvert(document.body, converter); btn.innerText = '簡體'; isTraditional = true; }
}

function toggleDark() {
  const btn = document.getElementById('dark-btn');
  isDark = !isDark;
  if (isDark) {
    document.body.classList.add('dark');
    btn.innerText = '淺色';
  } else {
    document.body.classList.remove('dark');
    btn.innerText = '深色';
  }
  localStorage.setItem('darkMode', isDark);
}

function walkAndConvert(node, converter) {
  if (node.nodeType === 3) node.textContent = converter(node.textContent);
  else for (let child of node.childNodes) walkAndConvert(child, converter);
}
function exportImage() {
  const btn = document.getElementById('export-btn');
  const latestBtn = document.getElementById('export-latest-btn');
  const langBtn = document.getElementById('lang-btn');
  const darkBtn = document.getElementById('dark-btn');
  const navBtns = document.getElementById('nav-buttons');
  const originalText = btn.innerText;
  btn.style.display = 'none'; if (latestBtn) latestBtn.style.display = 'none'; langBtn.style.display = 'none'; if (darkBtn) darkBtn.style.display = 'none'; if (navBtns) navBtns.style.display = 'none'; btn.disabled = true;
  html2canvas(document.getElementById('recommend-card') || document.getElementById('capture-area'), {backgroundColor: isDark ? '#2d2d2d' : '#ffffff', scale: 2, useCORS: true}).then(canvas => {
    btn.style.display = 'block'; if (latestBtn) latestBtn.style.display = 'block'; langBtn.style.display = 'block'; if (darkBtn) darkBtn.style.display = 'block'; if (navBtns) navBtns.style.display = 'block';
    canvas.toBlob(blob => { navigator.clipboard.write([new ClipboardItem({'image/png': blob})]).then(() => { btn.innerText = '已複製！'; setTimeout(() => { btn.innerText = originalText; btn.disabled = false; }, 1500); }).catch(err => { alert('複製失敗'); btn.innerText = originalText; btn.disabled = false; }); }, 'image/png');
  }).catch(err => { btn.style.display = 'block'; if (latestBtn) latestBtn.style.display = 'block'; langBtn.style.display = 'block'; if (darkBtn) darkBtn.style.display = 'block'; if (navBtns) navBtns.style.display = 'block'; alert('截圖失敗'); btn.innerText = originalText; btn.disabled = false; });
}
function exportFrame(frameId, btn) {
  const originalText = btn.innerText; btn.disabled = true; btn.innerText = '截圖中...';
  html2canvas(document.getElementById(frameId), {backgroundColor: isDark ? '#2d2d2d' : '#ffffff', scale: 2, useCORS: true}).then(canvas => {
    canvas.toBlob(blob => { navigator.clipboard.write([new ClipboardItem({'image/png': blob})]).then(() => { btn.innerText = '已複製！'; setTimeout(() => { btn.innerText = originalText; btn.disabled = false; }, 1500); }).catch(err => { alert('複製失敗'); btn.innerText = originalText; btn.disabled = false; }); }, 'image/png');
  }).catch(err => { alert('截圖失敗'); btn.innerText = originalText; btn.disabled = false; });
}
function exportLatest() {
  const btn = document.getElementById('export-latest-btn');
  const exportBtn = document.getElementById('export-btn');
  const langBtn = document.getElementById('lang-btn');
  const darkBtn = document.getElementById('dark-btn');
  const originalText = btn.innerText;
  btn.style.display = 'none'; if (exportBtn) exportBtn.style.display = 'none'; langBtn.style.display = 'none'; if (darkBtn) darkBtn.style.display = 'none'; btn.disabled = true;
  html2canvas(document.getElementById('latest-card'), {backgroundColor: isDark ? '#2d2d2d' : '#ffffff', scale: 2, useCORS: true}).then(canvas => {
    btn.style.display = 'block'; if (exportBtn) exportBtn.style.display = 'block'; langBtn.style.display = 'block'; if (darkBtn) darkBtn.style.display = 'block';
    canvas.toBlob(blob => { navigator.clipboard.write([new ClipboardItem({'image/png': blob})]).then(() => { btn.innerText = '已複製！'; setTimeout(() => { btn.innerText = originalText; btn.disabled = false; }, 1500); }).catch(err => { alert('複製失敗'); btn.innerText = originalText; btn.disabled = false; }); }, 'image/png');
  }).catch(err => { btn.style.display = 'block'; if (exportBtn) exportBtn.style.display = 'block'; langBtn.style.display = 'block'; if (darkBtn) darkBtn.style.display = 'block'; alert('截圖失敗'); btn.innerText = originalText; btn.disabled = false; });
}
setInterval(function() { location.reload(); }, 5 * 60 * 1000);
</script>
</body>
</html>
"""

def calc_transitions(df, latest):
    if df.empty: return [], set(), set(), Counter()
    df = df.drop_duplicates(subset=["expect"], keep="last").sort_values("expect").reset_index(drop=True)
    df["zodiac_set"] = df["zodiac"].apply(parse_zodiacs)
    sets = df["zodiac_set"].tolist()
    transition = defaultdict(Counter)
    for i in range(len(sets) - 1):
        for p in sets[i]:
            if p in ZODIACS: transition[p].update(sets[i + 1])
    transitions = []
    for z in ZODIACS:
        if z not in transition or not transition[z]: continue
        top_items = get_top_with_ties(transition[z], 3)
        transitions.append({"prev": z, "next_parts": [{"zodiac": a, "text": f"{a}({c})"} for a, c in top_items], "total": sum(c for _, c in top_items)})
    transitions.sort(key=lambda x: x["total"], reverse=True)
    latest_zodiacs = parse_zodiacs(latest.get("zodiac")) if latest else set()
    next_counter = Counter()
    for z in latest_zodiacs:
        if z in transition:
            for animal, cnt in get_top_with_ties(transition[z], 3):
                next_counter[animal] += 1
    return transitions, {z for z, cnt in next_counter.items() if cnt >= 3}, latest_zodiacs, next_counter

def make_count_summary(counter):
    return "、".join([f'<span class="count-green">{z} {c}</span>' if c >= 3 else f"{z} {c}" for z, c in counter.most_common()])

def process_data(latest, records_all, records_2026, region):
    if not records_all: return None
    for r in records_all:
        if "zodiac" in r: r["zodiac"] = normalize_zodiac(r["zodiac"])
    for r in records_2026:
        if "zodiac" in r: r["zodiac"] = normalize_zodiac(r["zodiac"])
    if latest and "zodiac" in latest: latest["zodiac"] = normalize_zodiac(latest["zodiac"])
    df_all = pd.DataFrame(records_all).drop_duplicates(subset=["expect"], keep="last").sort_values("expect").reset_index(drop=True)
    df_2026 = pd.DataFrame(records_2026) if records_2026 else pd.DataFrame()
    df_all["zodiac_set"] = df_all["zodiac"].apply(parse_zodiacs)
    sets = df_all["zodiac_set"].tolist()
    zodiac_numbers = build_zodiac_numbers(df_all)
    hot_numbers, cold_numbers = get_hot_cold_numbers(df_all, 50)
    hot_set, cold_set = set(hot_numbers), set(cold_numbers)
    appear = Counter()
    for s in sets: appear.update(s)
    appear_list = appear.most_common()
    full_avg = sum(appear.values()) / len(ZODIACS) if appear else 0
    N = 50
    recent_c = Counter()
    for s in sets[-N:]: recent_c.update(s)
    recent_list = recent_c.most_common()
    recent_avg = sum(recent_c.values()) / len(ZODIACS) if recent_c else 0
    avg_map, streak_info = {}, []
    for z in ZODIACS:
        streaks = get_omission_streaks(sets, z)
        if not streaks: avg_map[z] = 0; continue
        avg = sum(streaks) / len(streaks)
        avg_map[z] = avg
        dist = Counter(streaks)
        streak_info.append({"z": z, "avg": avg, "max": max(streaks), "dist": "、".join([f"{l}期×{c}次" for l, c in sorted(dist.items())])})
    streak_info.sort(key=lambda x: x["avg"], reverse=True)
    omission, current_miss = [], {}
    for z in ZODIACS:
        miss = 0
        for s in reversed(sets):
            if z in s: break
            miss += 1
        current_miss[z] = miss
        omission.append({"z": z, "miss": miss, "avg": avg_map.get(z, 0)})
    omission.sort(key=lambda x: x["miss"], reverse=True)
    long_miss_set = {z for z in ZODIACS if current_miss.get(z, 0) >= 3 and recent_c.get(z, 0) > recent_avg and appear.get(z, 0) > full_avg}
    transitions, green_next, latest_zodiacs, next_counter = calc_transitions(df_all, latest)
    transitions_2026, green_next_2026, _, next_counter_2026 = calc_transitions(df_2026, latest)
    transition_all = defaultdict(Counter)
    for i in range(len(sets) - 1):
        for p in sets[i]:
            if p in ZODIACS: transition_all[p].update(sets[i + 1])
    recommend_strength = Counter()
    for z in latest_zodiacs:
        if z in transition_all:
            for animal, cnt in get_top_with_ties(transition_all[z], 3):
                recommend_strength[animal] += cnt
    long_miss_recs = [{"zodiac": z, "numbers": "、".join(f"{n:02d}" for n in zodiac_numbers.get(z, [])), "numbers_html": format_numbers_with_color("、".join(f"{n:02d}" for n in zodiac_numbers.get(z, [])), hot_set, cold_set)} for z in sorted(long_miss_set, key=lambda x: ZODIACS.index(x))]
    sorted_green = sorted(green_next, key=lambda x: (next_counter[x], recommend_strength.get(x, 0)), reverse=True)
    frequent_next_recs = [{"zodiac": z, "numbers": "、".join(f"{n:02d}" for n in zodiac_numbers.get(z, [])), "numbers_html": format_numbers_with_color("、".join(f"{n:02d}" for n in zodiac_numbers.get(z, [])), hot_set, cold_set), "count": next_counter[z]} for z in sorted_green]
    return {"latest": latest, "next_date": get_next_draw_date(latest, region == "hk"), "next_expect": get_next_expect(latest), "latest_zodiacs": latest_zodiacs, "appear": appear_list, "full_avg": full_avg, "recent": recent_list, "recent_avg": recent_avg, "omission": omission, "streaks": streak_info, "long_miss_set": long_miss_set, "long_miss_recs": long_miss_recs, "frequent_next_recs": frequent_next_recs, "transitions": transitions, "green_next": green_next, "transitions_2026": transitions_2026, "green_next_2026": green_next_2026, "hot_numbers": hot_numbers, "cold_numbers": cold_numbers, "count_summary": make_count_summary(next_counter), "count_summary_2026": make_count_summary(next_counter_2026) if next_counter_2026 else "", "ball_display": build_ball_display(latest.get("openCode", ""), latest.get("zodiac", ""), latest.get("wave", "")) if latest else ""}

@app.route("/")
@app.route("/macau")
def macau():
    latest = get_macau_latest()
    records_all, records_2026 = [], []
    for y in [2025, 2026]:
        data = get_macau_year_history(y)
        records_all.extend(data)
        if y == 2026: records_2026.extend(data)
    result = process_data(latest, records_all, records_2026, "macau")
    if not result: return "無法取得新澳門歷史數據"
    record_recommendation("macau", latest, result)
    update_hit_rates("macau", latest)
    return render_template_string(HTML, title="王大師六合彩預測（新澳門）", region="macau", note_extra="新澳門版顯示 2025-2026 和 2026 接續熱門統計。", **result)

@app.route("/oldmacau")
def old_macau():
    old_item = get_old_macau_data()
    if not old_item: return "無法取得舊澳門數據"
    latest = {"expect": old_item.get("expect"), "openTime": old_item.get("openTime"), "openCode": old_item.get("openCode"), "zodiac": normalize_zodiac(old_item.get("zodiac")), "wave": old_item.get("wave", "")}
    records_all, records_2026 = [], []
    for h in old_item.get("history", []):
        if "期：" in h:
            parts = h.split("期：")
            expect, openCode = parts[0].strip(), parts[1].strip()
            if not (expect.startswith("2025") or expect.startswith("2026")) or expect == str(latest["expect"]): continue
            zodiac_filled = fill_zodiac_by_year(openCode, expect)
            if zodiac_filled:
                rec = {"expect": expect, "openTime": "", "openCode": openCode, "zodiac": zodiac_filled}
                records_all.append(rec)
                if expect.startswith("2026"): records_2026.append(rec)
    latest_rec = {"expect": latest["expect"], "openTime": latest["openTime"], "openCode": latest["openCode"], "zodiac": latest["zodiac"]}
    records_all.append(latest_rec)
    if str(latest["expect"]).startswith("2026"): records_2026.append(latest_rec)
    result = process_data(latest, records_all, records_2026, "oldmacau")
    if not result: return "無法處理舊澳門數據"
    record_recommendation("oldmacau", latest, result)
    update_hit_rates("oldmacau", latest)
    return render_template_string(HTML, title="王大師六合彩預測（舊澳門）", region="oldmacau", note_extra="舊澳門版顯示 2025-2026 和 2026 接續熱門統計。", **result)

@app.route("/hk")
def hk():
    hk_item = get_hk_data()
    if not hk_item: return "無法取得香港數據"
    latest = {"expect": hk_item.get("expect"), "openTime": hk_item.get("openTime"), "openCode": hk_item.get("openCode"), "zodiac": normalize_zodiac(hk_item.get("zodiac")), "wave": hk_item.get("wave", "")}
    records_all, records_2026 = [], []
    for h in hk_item.get("history", []):
        if "期：" in h:
            parts = h.split("期：")
            expect, openCode = parts[0].strip(), parts[1].strip()
            if not (expect.startswith("2025") or expect.startswith("2026")) or expect == str(latest["expect"]): continue
            zodiac_filled = fill_zodiac_by_year(openCode, expect)
            if zodiac_filled:
                rec = {"expect": expect, "openTime": "", "openCode": openCode, "zodiac": zodiac_filled}
                records_all.append(rec)
                if expect.startswith("2026"): records_2026.append(rec)
    latest_rec = {"expect": latest["expect"], "openTime": latest["openTime"], "openCode": latest["openCode"], "zodiac": latest["zodiac"]}
    records_all.append(latest_rec)
    if str(latest["expect"]).startswith("2026"): records_2026.append(latest_rec)
    result = process_data(latest, records_all, records_2026, "hk")
    if not result: return "無法處理香港數據"
    record_recommendation("hk", latest, result)
    update_hit_rates("hk", latest)
    return render_template_string(HTML, title="王大師六合彩預測（香港）", region="hk", note_extra="香港版顯示 2025-2026 和 2026 接續熱門統計。", **result)

@app.route("/records")
def records_page():
    all_records = load_records()
    filtered = [r for r in all_records if r.get("date", "") >= START_DATE]
    macau_records = sorted([r for r in filtered if r.get("region") == "macau"], key=lambda x: x.get("date", ""), reverse=True)
    oldmacau_records = sorted([r for r in filtered if r.get("region") == "oldmacau"], key=lambda x: x.get("date", ""), reverse=True)
    hk_records = sorted([r for r in filtered if r.get("region") == "hk"], key=lambda x: x.get("date", ""), reverse=True)
    def calc_stats(records):
        settled = [r for r in records if r.get("actual_zodiacs") is not None]
        long_miss_total = long_miss_hits = frequent_total = frequent_hits = 0
        for r in records:
            actual = set(r.get("actual_zodiacs") or [])
            lm_list = r.get("long_miss") or []
            if lm_list and actual:
                hit = sum(1 for z in lm_list if z in actual)
                r["lm_text"] = f"{len(lm_list)}中{hit} ({round(hit / len(lm_list) * 100)}%)"
                long_miss_total += len(lm_list)
                long_miss_hits += hit
            else: r["lm_text"] = "/"
            fn_list = r.get("frequent_next") or []
            if fn_list and actual:
                hit = sum(1 for item in fn_list if item["zodiac"] in actual)
                r["fn_text"] = f"{len(fn_list)}中{hit} ({round(hit / len(fn_list) * 100)}%)"
                frequent_total += len(fn_list)
                frequent_hits += hit
            else: r["fn_text"] = "/"
        long_miss_rate = (long_miss_hits / long_miss_total * 100) if long_miss_total else 0
        frequent_rate = (frequent_hits / frequent_total * 100) if frequent_total else 0
        total_hits = long_miss_hits + frequent_hits
        total_predictions = long_miss_total + frequent_total
        total_rate = (total_hits / total_predictions * 100) if total_predictions else 0
        kelly = ((total_rate - (100 - total_rate)) / 4) if total_predictions else 0
        return {"records": records, "settled": len(settled), "long_miss_hits": long_miss_hits, "frequent_hits": frequent_hits, "long_miss_total": long_miss_total, "frequent_total": frequent_total, "long_miss_rate": long_miss_rate, "frequent_rate": frequent_rate, "total_hits": total_hits, "total_predictions": total_predictions, "total_rate": total_rate, "kelly": kelly}
    macau_stats, oldmacau_stats, hk_stats = calc_stats(macau_records), calc_stats(oldmacau_records), calc_stats(hk_records)
    return render_template_string(HTML, title="王大師預測記錄", region="records", note_extra="預測記錄自 2026-10-13 開始自動保存。", macau_records=macau_stats["records"], macau_settled=macau_stats["settled"], macau_long_miss_hits=macau_stats["long_miss_hits"], macau_frequent_hits=macau_stats["frequent_hits"], macau_long_miss_total=macau_stats["long_miss_total"], macau_frequent_total=macau_stats["frequent_total"], macau_long_miss_rate=macau_stats["long_miss_rate"], macau_frequent_rate=macau_stats["frequent_rate"], macau_total_hits=macau_stats["total_hits"], macau_total_predictions=macau_stats["total_predictions"], macau_total_rate=macau_stats["total_rate"], macau_kelly=macau_stats["kelly"], oldmacau_records=oldmacau_stats["records"], oldmacau_settled=oldmacau_stats["settled"], oldmacau_long_miss_hits=oldmacau_stats["long_miss_hits"], oldmacau_frequent_hits=oldmacau_stats["frequent_hits"], oldmacau_long_miss_total=oldmacau_stats["long_miss_total"], oldmacau_frequent_total=oldmacau_stats["frequent_total"], oldmacau_long_miss_rate=oldmacau_stats["long_miss_rate"], oldmacau_frequent_rate=oldmacau_stats["frequent_rate"], oldmacau_total_hits=oldmacau_stats["total_hits"], oldmacau_total_predictions=oldmacau_stats["total_predictions"], oldmacau_total_rate=oldmacau_stats["total_rate"], oldmacau_kelly=oldmacau_stats["kelly"], hk_records=hk_stats["records"], hk_settled=hk_stats["settled"], hk_long_miss_hits=hk_stats["long_miss_hits"], hk_frequent_hits=hk_stats["frequent_hits"], hk_long_miss_total=hk_stats["long_miss_total"], hk_frequent_total=hk_stats["frequent_total"], hk_long_miss_rate=hk_stats["long_miss_rate"], hk_frequent_rate=hk_stats["frequent_rate"], hk_total_hits=hk_stats["total_hits"], hk_total_predictions=hk_stats["total_predictions"], hk_total_rate=hk_stats["total_rate"], hk_kelly=hk_stats["kelly"], latest=None, next_date="", next_expect="", long_miss_recs=[], frequent_next_recs=[], appear=[], full_avg=0, recent=[], recent_avg=0, omission=[], streaks=[], long_miss_set=set(), transitions=[], green_next=set(), transitions_2026=[], green_next_2026=set(), latest_zodiacs=set(), hot_numbers=[], cold_numbers=[], count_summary="", count_summary_2026="", ball_display="")

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)