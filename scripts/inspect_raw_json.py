import sqlite3
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect("data/state.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
    SELECT tender_no, client, raw_json 
    FROM tenders 
    WHERE tender_no IN ('2027/2026/40', '2027/2026/38', '370-278', '72-516', '33/32')
""")
for r in cur.fetchall():
    print("====================")
    print(r["tender_no"], r["client"])
    try:
        data = json.loads(r["raw_json"])
        print("Keys:", data.keys())
        if "full_html_url" in data:
            print("URL:", data["full_html_url"])
        if "raw_text" in data:
            print("Raw text:", data["raw_text"][:300])
    except Exception as e:
        print("Error:", e)
conn.close()
