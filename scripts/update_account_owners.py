"""
KBM Tender Scout - Account Owner Synchronizer
Hierarchy:
Marketing Manager for Government and Oil Sector: Eiman Ashkanani
- Jana Al-Obaid: PIFSS, PADA, Nazaha, MOH
- Raed Obeid: MEW, PACI
- Khaled Alabdallah: MOI
- Ahmed Habib: KOC, KOTC
- Abrar Al-Qallaf: KNPC, PIC
- Any other accounts -> Eiman Ashkanani herself.
"""

import csv
import json
from pathlib import Path
from src.pipeline.account_manager import resolve_account_manager, DEFAULT_OWNER

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def update_clients_csv():
    csv_path = PROJECT_ROOT / "data" / "clients.csv"
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        return

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for r in reader:
            cid = r.get("client_id", "").strip()
            cname = r.get("client_name_ar", "").strip()
            
            # Resolve AM
            am = resolve_account_manager(cname, cid)
            r["account_owner"] = am
            rows.append(r)

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Successfully updated {len(rows)} clients in data/clients.csv with official KBM Account Managers!")

if __name__ == "__main__":
    update_clients_csv()
