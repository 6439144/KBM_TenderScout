"""
Client and Sector Classification Engine for KBM Tender Scout.
Implements Rule FR-6: exact/alias matching against master list, rule keywords, and pending queue.
"""

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml

from src.pipeline.normalizer import normalize_arabic_text
from src.pipeline.account_manager import resolve_account_manager

logger = logging.getLogger("kbm.classifier")

class ClientSectorClassifier:
    def __init__(
        self,
        clients_csv_path: Path = Path("data/clients.csv"),
        sectors_yaml_path: Path = Path("data/sectors.yaml"),
        pending_csv_path: Path = Path("data/clients_pending.csv"),
        confidence_threshold: float = 0.75
    ):
        self.clients_csv_path = clients_csv_path
        self.sectors_yaml_path = sectors_yaml_path
        self.pending_csv_path = pending_csv_path
        self.confidence_threshold = confidence_threshold

        self.clients: List[Dict[str, Any]] = []
        self.client_lookup: Dict[str, Dict[str, Any]] = {}
        self.sectors: Dict[str, Dict[str, Any]] = {}

        self._load_sectors()
        self._load_clients()
        self._init_pending_file()

    def _load_sectors(self) -> None:
        """Loads sector taxonomy from YAML."""
        if not self.sectors_yaml_path.exists():
            logger.warning("Sectors YAML file not found: %s", self.sectors_yaml_path)
            return

        with open(self.sectors_yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            for s in data.get("sectors", []):
                self.sectors[s["id"]] = s

    def _load_clients(self) -> None:
        """Loads client master list and builds normalized alias index."""
        if not self.clients_csv_path.exists():
            logger.warning("Clients master CSV not found: %s", self.clients_csv_path)
            return

        with open(self.clients_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.clients.append(row)
                
                # Index by normalized Arabic name
                norm_ar = normalize_arabic_text(row["client_name_ar"])
                self.client_lookup[norm_ar] = row

                # Index by normalized English name
                if row.get("client_name_en"):
                    self.client_lookup[row["client_name_en"].strip().lower()] = row

                # Index by each alias
                aliases = [a.strip() for a in row.get("aliases", "").split(";") if a.strip()]
                for alias in aliases:
                    norm_alias = normalize_arabic_text(alias)
                    self.client_lookup[norm_alias] = row
                    self.client_lookup[alias.lower()] = row

    def _init_pending_file(self) -> None:
        """Ensures clients_pending.csv exists with headers."""
        if not self.pending_csv_path.exists():
            self.pending_csv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.pending_csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "client_raw", "first_seen_tender_uid", "first_seen_portal",
                    "first_seen_date", "status", "assigned_client_id", "reviewed_by", "review_date"
                ])

    def classify_client_and_sector(
        self,
        client_raw: Optional[str],
        tender_uid: str,
        portal_id: str
    ) -> Tuple[str, str, Optional[str], float, bool, List[str]]:
        """
        Maps client_raw to master client record, returns:
        (canonical_client_name, sector, account_owner, confidence, needs_review, review_reasons)
        """
        review_reasons = []

        if not client_raw or client_raw.strip() in ("", "غير محدد", "None"):
            return "غير محدد", "other", None, 0.0, True, ["MISSING_CLIENT_NAME"]

        norm_raw = normalize_arabic_text(client_raw)

        # 1. Exact or Alias Match in Master Index
        if norm_raw in self.client_lookup:
            matched = self.client_lookup[norm_raw]
            sector = matched.get("sector_id", "other")
            owner = matched.get("account_owner") or resolve_account_manager(matched["client_name_ar"], matched.get("client_id"))
            return matched["client_name_ar"], sector, owner, 1.0, False, []

        # 2. Substring / Partial Alias Match
        for key, entry in self.client_lookup.items():
            if len(key) >= 4 and (key in norm_raw or norm_raw in key):
                sector = entry.get("sector_id", "other")
                owner = entry.get("account_owner") or resolve_account_manager(entry["client_name_ar"], entry.get("client_id"))
                return entry["client_name_ar"], sector, owner, 0.85, False, []

        # 3. Rule / Keyword matching against sectors
        matched_sector = "other"
        highest_keyword_score = 0
        for sector_id, s_data in self.sectors.items():
            for kw in s_data.get("keywords", []):
                if kw in norm_raw:
                    matched_sector = sector_id
                    highest_keyword_score = 0.5
                    break

        # Attempt to resolve account manager even for unrecognized clients
        resolved_am = resolve_account_manager(client_raw)

        # Record unmapped client in clients_pending.csv
        self._record_pending_client(client_raw, tender_uid, portal_id)
        review_reasons.append(f"UNRECOGNIZED_CLIENT: '{client_raw}' not in master list")

        return client_raw, matched_sector, resolved_am, highest_keyword_score, True, review_reasons

    def _record_pending_client(self, client_raw: str, tender_uid: str, portal_id: str) -> None:
        """Appends unrecognized client to data/clients_pending.csv for operator review."""
        try:
            # Check if already logged
            already_logged = False
            if self.pending_csv_path.exists():
                with open(self.pending_csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get("client_raw", "").strip() == client_raw.strip():
                            already_logged = True
                            break

            if not already_logged:
                from datetime import date
                with open(self.pending_csv_path, "a", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        client_raw.strip(),
                        tender_uid,
                        portal_id,
                        date.today().isoformat(),
                        "PENDING",
                        "",
                        "",
                        ""
                    ])
        except Exception as e:
            logger.warning("Could not write to clients_pending.csv: %s", e)
