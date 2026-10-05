import sqlite3
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect("data/state.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT tender_uid, tender_no, title_ar, sources_json, raw_json FROM tenders WHERE tender_no = 'RFQ/1063414'")
r = cur.fetchone()
if r:
    print(r["tender_uid"], r["tender_no"])
    print("Sources:", r["sources_json"])
    print("Raw:", r["raw_json"][:400])
conn.close()
