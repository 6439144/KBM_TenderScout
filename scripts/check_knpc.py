import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect("data/state.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT tender_uid, tender_no, title_ar, client, account_owner, scope_required, requirements FROM tenders WHERE client LIKE '%البترول الوطنية%' LIMIT 10")
for r in cur.fetchall():
    print(r["tender_no"], "|", r["account_owner"], "|", r["title_ar"])
    print("  Scope:", r["scope_required"] or "EMPTY")
    print("  Reqs:", r["requirements"][:60] if r["requirements"] else "None")
conn.close()
