import sqlite3
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect("data/state.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT tender_uid, raw_json, title_ar FROM tenders WHERE raw_json LIKE '%LOADING%'")
rows = cur.fetchall()
print(f"Found {len(rows)} tenders with LOADING in raw_json")

for r in rows:
    uid = r["tender_uid"]
    raw_str = r["raw_json"]
    title = r["title_ar"]
    try:
        data = json.loads(raw_str)
        if "title_raw" in data and "LOADING" in str(data["title_raw"]):
            data["title_raw"] = title
        if "extra_fields" in data and isinstance(data["extra_fields"], dict):
            if "announcement_snippet" in data["extra_fields"] and "LOADING" in str(data["extra_fields"]["announcement_snippet"]):
                data["extra_fields"]["announcement_snippet"] = title
        clean_json = json.dumps(data, ensure_ascii=False)
        cur.execute("UPDATE tenders SET raw_json = ? WHERE tender_uid = ?", (clean_json, uid))
    except Exception as e:
        print("JSON parse error:", e)

conn.commit()

# Verify
cur.execute("SELECT COUNT(*) FROM tenders WHERE raw_json LIKE '%LOADING%'")
rem = cur.fetchone()[0]
print(f"Remaining tenders with LOADING in raw_json: {rem}")
conn.close()
