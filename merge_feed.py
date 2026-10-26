#!/usr/bin/env python3
"""يبني feed.json = آخر تقرير (من tax.json) + أرشيف التقارير السابقة بدون تكرار.
يُشغَّل تلقائياً عند كل تغيير في tax.json (انظر .github/workflows/build-feed.yml)."""
import json, os, sys

MAX_REPORTS = 12      # أقصى عدد تقارير سابقة نحتفظ بها
MAX_ARTICLES = 60     # أقصى عدد أخبار في الأرشيف

def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def title(a):
    return (a.get("title") or a.get("text") or a.get("TitleAR") or "").strip()

def day(d):
    return str(d or "")[:10]

cur = load("tax.json")
if not cur or not cur.get("data"):
    print("tax.json فارغ أو غير صالح — لا تغيير"); sys.exit(0)

old = load("feed.json") or {}
cur_date = cur.get("updatedAt") or ""

# كل التقارير المعروفة: الجديد أولاً، ثم آخر تقرير سابق، ثم الأرشيف
reports = [{"date": cur_date, "data": cur["data"]}]
if old.get("data"):
    reports.append({"date": old.get("updatedAt", ""), "data": old["data"]})
reports += old.get("history", [])

# تقرير واحد لكل يوم (الأحدث يغلب)، وبدون تكرار أي خبر
by_day, order = {}, []
for r in reports:
    k = day(r.get("date"))
    if not k or k in by_day:
        continue
    by_day[k] = r; order.append(k)
order.sort(reverse=True)

seen = set(title(a) for a in cur["data"])
history, count = [], 0
for k in order:
    r = by_day[k]
    if r is by_day.get(day(cur_date)) and r["date"] == cur_date:
        continue                                   # هذا هو التقرير الحالي
    items = []
    for a in r.get("data", []):
        t = title(a)
        if t and t not in seen:
            seen.add(t); items.append(a)
    if items:
        history.append({"date": r["date"], "data": items}); count += len(items)
    if len(history) >= MAX_REPORTS or count >= MAX_ARTICLES:
        break

feed = {"data": cur["data"], "updatedAt": cur_date,
        "source": cur.get("source", "GTA DailyReportAR"), "history": history}
out = json.dumps(feed, ensure_ascii=False, indent=1)
if os.path.exists("feed.json") and open("feed.json", encoding="utf-8").read() == out:
    print("لا تغيير في feed.json"); sys.exit(0)
open("feed.json", "w", encoding="utf-8").write(out)
print("تم بناء feed.json:", len(cur["data"]), "خبر حالي +", count, "في الأرشيف")
