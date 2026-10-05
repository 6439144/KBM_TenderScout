import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect("data/state.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
    SELECT tender_uid, tender_no, title_ar, client, account_owner, is_kbm_relevant, kbm_fit_score, kbm_bu, kbm_bu_ar, kbm_vendors_json, kbm_rationale, requirements, raw_json
    FROM tenders
    ORDER BY kbm_fit_score DESC
""")
rows = cur.fetchall()

print(f"Total tenders in DB: {len(rows)}")
kbm_rel = [r for r in rows if r["is_kbm_relevant"] or r["kbm_fit_score"] >= 30.0]
print(f"Total KBM Relevant / Fit >= 30%: {len(kbm_rel)}")

print("\n--- Listing Top 30 Tenders ---")
for i, r in enumerate(rows[:30], 1):
    print(f"{i}. [{r['kbm_fit_score']}%] {r['tender_no']} | {r['client']} | {r['account_owner']}")
    print(f"   Title: {r['title_ar']}")
    print(f"   BU: {r['kbm_bu_ar']} ({r['kbm_bu']})")
    print(f"   Rationale: {r['kbm_rationale'][:120]}...")
    print()

conn.close()
