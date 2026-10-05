import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect("data/state.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT tender_uid, tender_no, title_ar, client, account_owner, scope_required, requirements FROM tenders WHERE sources_json LIKE '%capt%' LIMIT 10")
for r in cur.fetchall():
    print("--------------------------------------------------")
    print(r["tender_no"], "|", r["client"], "|", r["account_owner"])
    print("Title:", r["title_ar"])
conn.close()
