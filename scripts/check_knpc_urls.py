import sqlite3
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect("data/state.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT tender_uid, tender_no, raw_json FROM tenders WHERE tender_no IN ('RFQ/1063414', 'RFQ/1063554', 'RFQ/1063825')")
for r in cur.fetchall():
    print(r["tender_no"])
    try:
        data = json.loads(r["raw_json"])
        print("URL:", data.get("full_html_url"))
    except:
        pass
conn.close()
