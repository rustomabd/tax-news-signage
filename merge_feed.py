#!/usr/bin/env python3
"""يبني feed.json = أحدث تقرير + أرشيف التقارير السابقة (بترتيب التاريخ، بدون تكرار).
يُشغَّل تلقائياً عند كل تغيير في tax.json (انظر .github/workflows/build-feed.yml).

tax.json يحمل:
  data      = أخبار أحدث تقرير            updatedAt = تاريخه
  reports   = آخر عدة تقارير من البوابة   (تشمل التقارير التي اعتُمدت متأخرة)
قواعد الدمج:
  - أيام موجودة في reports تُؤخذ من tax.json كما هي (فيعكس أي حذف/تعديل على البوابة).
  - أيام أقدم من نافذة reports تُحفظ من الأرشيف القديم.
  - عدة تقارير في اليوم نفسه تُجمع أخبارها بدون تكرار العنوان."""
import json, os, sys

MAX_REPORTS = 6       # أقصى عدد أيام سابقة نحتفظ بها
MAX_ARTICLES = 10     # أقصى عدد أخبار في الأرشيف (الشاشة تحتاج 4–5 فقط)
MAX_CURRENT = 6       # أقصى عدد أخبار من أحدث تقرير (الشاشة تعرض 5 كحد أقصى)
MAX_DESC = 520        # أقصى طول للوصف (الصفحة تقتطع الوصف الطويل على أي حال)

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

def slim(a):
    """نسخة أخف من الخبر: نفس الحقول، ووصف مقتطع عند حدّ كلمة. يصغّر feed.json لأن كل شاشة تحمّله باستمرار."""
    b = dict(a)
    for k in ("DescAR", "description", "desc"):
        v = b.get(k)
        if isinstance(v, str) and len(v) > MAX_DESC:
            cut = v[:MAX_DESC].rsplit(" ", 1)[0].rstrip(" ,.;:،؛")
            b[k] = cut + " [...]"
    return b

cur = load("tax.json")
if not cur or not cur.get("data"):
    print("tax.json فارغ أو غير صالح — لا تغيير"); sys.exit(0)
old = load("feed.json") or {}

# 1) أيام من tax.json (الأحدث والأدق): نجمع أخبار اليوم الواحد من كل تقاريره
fresh = {}   # day -> {"date":..., "data":[...]}
def add_fresh(date, data):
    k = day(date)
    if not k or not data:
        return
    e = fresh.setdefault(k, {"date": date, "data": [], "seen": set()})
    if str(date) > str(e["date"]):
        e["date"] = date
    for a in data:
        t = title(a)
        if t and t not in e["seen"]:
            e["seen"].add(t); e["data"].append(a)

add_fresh(cur.get("updatedAt"), cur["data"])
for r in (cur.get("reports") or []):
    if isinstance(r, dict):
        add_fresh(r.get("date"), r.get("data"))

# 2) أيام قديمة من الأرشيف السابق (لم تعد ضمن نافذة reports)
archived = {}
old_reports = []
if old.get("data"):
    old_reports.append({"date": old.get("updatedAt", ""), "data": old["data"]})
old_reports += old.get("history", [])
for r in old_reports:
    k = day(r.get("date"))
    if k and k not in fresh and k not in archived:
        archived[k] = {"date": r.get("date"), "data": r.get("data", [])}

days = {}
days.update(archived)
for k, v in fresh.items():
    days[k] = {"date": v["date"], "data": v["data"]}
order = sorted(days.keys(), reverse=True)
if not order:
    print("لا تقارير"); sys.exit(0)

# 3) الأحدث = الحالي، والبقية أرشيف (بدون تكرار أي عنوان بين الأيام)
latest = days[order[0]]
seen = set(title(a) for a in latest["data"])
history, count = [], 0
for k in order[1:]:
    items = []
    for a in days[k]["data"]:
        t = title(a)
        if t and t not in seen:
            seen.add(t); items.append(a)
    items = items[:max(0, MAX_ARTICLES - count)]
    if items:
        history.append({"date": days[k]["date"], "data": items}); count += len(items)
    if len(history) >= MAX_REPORTS or count >= MAX_ARTICLES:
        break

latest_data = [slim(a) for a in latest["data"][:MAX_CURRENT]]
history = [{"date": h["date"], "data": [slim(a) for a in h["data"]]} for h in history]
feed = {"data": latest_data, "updatedAt": latest["date"],
        "source": cur.get("source", "GTA DailyReportAR"), "history": history}
out = json.dumps(feed, ensure_ascii=False, indent=1)
if os.path.exists("feed.json") and open("feed.json", encoding="utf-8").read() == out:
    print("لا تغيير في feed.json"); sys.exit(0)
open("feed.json", "w", encoding="utf-8").write(out)
print("تم بناء feed.json:", len(latest_data), "خبر حالي +", count, "في الأرشيف")
