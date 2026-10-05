"""
Apply updated account management structure across all tenders in data/state.db
and clients in data/clients.csv.

Marketing Manager for Government and Oil: Eiman Ashkanani
- Jana Al-Obaid: PIFSS, PADA, Nazaha, MOH
- Raed Obeid: MEW, PACI
- Khaled Alabdallah: MOI
- Ahmed Habib: KOC, KOTC
- Abrar Al-Qallaf: KNPC, PIC
- Any other accounts -> Eiman Ashkanani herself.
"""

import sys
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.account_manager import resolve_account_manager
from scripts.update_account_owners import update_clients_csv
DB_PATH = PROJECT_ROOT / "data" / "state.db"

def reassign_all_tenders():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    rows = cursor.execute("SELECT tender_uid, client, tender_no, title_ar FROM tenders").fetchall()
    print(f"Found {len(rows)} tenders to re-evaluate.")

    updated_count = 0
    owner_distribution = {}

    for uid, client, t_no, title in rows:
        new_am = resolve_account_manager(client)
        owner_distribution[new_am] = owner_distribution.get(new_am, 0) + 1
        cursor.execute("UPDATE tenders SET account_owner = ? WHERE tender_uid = ?", (new_am, uid))
        updated_count += 1

    conn.commit()
    conn.close()

    print(f"\nSuccessfully re-evaluated {updated_count} tenders.")
    print("New Account Manager Distribution:")
    for owner, count in sorted(owner_distribution.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {owner}: {count} tenders")

    print("\nUpdating data/clients.csv...")
    update_clients_csv()
    print("All clients and tenders successfully synchronized!")

if __name__ == "__main__":
    reassign_all_tenders()
