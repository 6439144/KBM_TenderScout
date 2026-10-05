import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect("data/state.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT COUNT(*) as c FROM tenders")
print(f"Total tenders: {cur.fetchone()['c']}")

cur.execute("SELECT COUNT(*) as c FROM tenders WHERE scope_required IS NOT NULL AND scope_required != ''")
print(f"Tenders with scope_required: {cur.fetchone()['c']}")

cur.execute("SELECT COUNT(*) as c FROM tenders WHERE requirements IS NOT NULL AND requirements != ''")
print(f"Tenders with requirements: {cur.fetchone()['c']}")

cur.execute("SELECT COUNT(*) as c FROM tenders WHERE account_owner LIKE '%Wajih%'")
print(f"Tenders with Wajih: {cur.fetchone()['c']}")

cur.execute("SELECT COUNT(*) as c FROM tenders WHERE title_ar LIKE '%LOADING%'")
print(f"Tenders with LOADING: {cur.fetchone()['c']}")

print("\n--- Sample of Top KBM Qualified Tenders (Fit >= 70%) ---")
cur.execute("""
    SELECT tender_no, client, account_owner, kbm_fit_score, kbm_bu, title_ar, scope_required 
    FROM tenders 
    WHERE kbm_fit_score >= 70
    ORDER BY kbm_fit_score DESC
""")
for r in cur.fetchall():
    print(f"[{r['kbm_fit_score']}%] {r['tender_no']} | {r['client']} | {r['account_owner']} | {r['title_ar']}")
    print(f"   Scope: {r['scope_required'] or 'EMPTY'}")

conn.close()
