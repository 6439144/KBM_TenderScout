import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect("data/state.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
    SELECT tender_uid, tender_no, title_ar, client, account_owner, kbm_fit_score, kbm_bu, kbm_rationale, scope_required, requirements 
    FROM tenders 
    WHERE tender_uid IN ('kuwait_alyawm_MNA192026', 'kuwait_alyawm_MNA242026', 'kuwait_alyawm_24181118110')
""")
rows = cur.fetchall()
for r in rows:
    print("=" * 60)
    print(f"UID: {r['tender_uid']}")
    print(f"No: {r['tender_no']}")
    print(f"Title: {r['title_ar']}")
    print(f"Client: {r['client']}")
    print(f"Owner: {r['account_owner']}")
    print(f"Fit: {r['kbm_fit_score']}% | BU: {r['kbm_bu']}")
    print(f"Scope: {r['scope_required']}")
    print(f"Rationale: {r['kbm_rationale']}")
    print(f"Reqs:\n{r['requirements']}")
conn.close()
