"""
SQLite State Store for KBM Tender Scout.
Persists raw notices, canonical records, and tracks lifecycle changes (NEW, UPDATED, UNCHANGED, CLOSED).
"""

import json
import sqlite3
import hashlib
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from src.models import CanonicalTenderRecord, RawNotice, SourceRef, TenderStatus

DEFAULT_DB_PATH = Path("data/state.db")

class StateStore:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initializes tables for raw notices, canonical tenders, and run logs."""
        with self._connection() as conn:
            cursor = conn.cursor()
            
            # Raw notices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS raw_notices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portal_id TEXT NOT NULL,
                    tender_no TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    scraped_at TEXT NOT NULL
                )
            """)

            # Canonical tenders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tenders (
                    tender_uid TEXT PRIMARY KEY,
                    tender_no TEXT NOT NULL,
                    tender_no_normalized TEXT NOT NULL,
                    title_ar TEXT NOT NULL,
                    title_en TEXT,
                    notice_type TEXT NOT NULL,
                    client_raw TEXT NOT NULL,
                    client TEXT NOT NULL,
                    sector TEXT NOT NULL,
                    account_owner TEXT,
                    publish_date TEXT,
                    closing_date TEXT,
                    pre_bid_date TEXT,
                    bid_bond TEXT,
                    document_fee TEXT,
                    category_code TEXT,
                    sources_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    changes TEXT,
                    classification_confidence REAL,
                    needs_review INTEGER,
                    review_reasons_json TEXT,
                    is_kbm_relevant INTEGER,
                    relevance_keywords_json TEXT,
                    kbm_fit_score REAL DEFAULT 0.0,
                    kbm_bu TEXT DEFAULT 'None',
                    kbm_bu_ar TEXT DEFAULT 'غير محدد',
                    kbm_vendors_json TEXT DEFAULT '[]',
                    kbm_presales_verdict TEXT DEFAULT 'UNRELATED',
                    kbm_presales_verdict_ar TEXT DEFAULT 'غير متوافقة',
                    kbm_rationale TEXT DEFAULT '',
                    raw_json TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    content_hash TEXT NOT NULL
                )
            """)

            # Auto-migrate columns if table already existed without them
            cursor.execute("PRAGMA table_info(tenders)")
            existing_cols = {row["name"] for row in cursor.fetchall()}
            for col, col_def in [
                ("kbm_fit_score", "REAL DEFAULT 0.0"),
                ("kbm_bu", "TEXT DEFAULT 'None'"),
                ("kbm_bu_ar", "TEXT DEFAULT 'غير محدد'"),
                ("kbm_vendors_json", "TEXT DEFAULT '[]'"),
                ("kbm_presales_verdict", "TEXT DEFAULT 'UNRELATED'"),
                ("kbm_presales_verdict_ar", "TEXT DEFAULT 'غير متوافقة'"),
                ("kbm_rationale", "TEXT DEFAULT ''"),
            ]:
                if col not in existing_cols:
                    cursor.execute(f"ALTER TABLE tenders ADD COLUMN {col} {col_def}")

            # Indexing for high-speed queries and deduplication
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_no_norm ON tenders(tender_no_normalized)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_client ON tenders(client)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_closing ON tenders(closing_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_status ON tenders(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_fit ON tenders(kbm_fit_score)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenders_bu ON tenders(kbm_bu)")
            conn.commit()

    @staticmethod
    def _compute_content_hash(record: CanonicalTenderRecord) -> str:
        """Computes a SHA-256 hash of core tender content to detect changes."""
        fields_to_hash = [
            record.tender_no_normalized,
            record.title_ar,
            record.client,
            record.closing_date or "",
            record.publish_date or "",
            record.bid_bond or "",
            record.document_fee or "",
            record.notice_type
        ]
        return hashlib.sha256("||".join(fields_to_hash).encode("utf-8")).hexdigest()

    def save_raw_notice(self, notice: RawNotice) -> None:
        """Persists an unparsed raw notice for auditability."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO raw_notices (portal_id, tender_no, source_url, payload_json, scraped_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                notice.portal_id,
                notice.tender_no,
                notice.source_url,
                notice.model_dump_json(),
                notice.scraped_at
            ))
            conn.commit()

    def upsert_canonical_tender(self, tender: CanonicalTenderRecord) -> CanonicalTenderRecord:
        """
        Inserts or updates a canonical tender record, calculating status:
        NEW, UPDATED (with changes listed), UNCHANGED, or CLOSED.
        """
        now_iso = datetime.now().isoformat()
        today_date = date.today().isoformat()
        new_hash = self._compute_content_hash(tender)

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tenders WHERE tender_uid = ?", (tender.tender_uid,))
            existing = cursor.fetchone()

            if not existing:
                # Brand new tender
                tender.status = TenderStatus.NEW
                tender.changes = None
                
                # Check if already past closing date
                if tender.closing_date and tender.closing_date < today_date:
                    tender.status = TenderStatus.CLOSED

                cursor.execute("""
                    INSERT INTO tenders (
                        tender_uid, tender_no, tender_no_normalized, title_ar, title_en,
                        notice_type, client_raw, client, sector, account_owner,
                        publish_date, closing_date, pre_bid_date, bid_bond, document_fee,
                        category_code, sources_json, status, changes, classification_confidence,
                        needs_review, review_reasons_json, is_kbm_relevant, relevance_keywords_json,
                        kbm_fit_score, kbm_bu, kbm_bu_ar, kbm_vendors_json, kbm_presales_verdict, kbm_presales_verdict_ar, kbm_rationale,
                        raw_json, first_seen, last_seen, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tender.tender_uid, tender.tender_no, tender.tender_no_normalized, tender.title_ar, tender.title_en,
                    tender.notice_type, tender.client_raw, tender.client, tender.sector, tender.account_owner,
                    tender.publish_date, tender.closing_date, tender.pre_bid_date, tender.bid_bond, tender.document_fee,
                    tender.category_code, json.dumps([s.model_dump() for s in tender.sources], ensure_ascii=False),
                    tender.status.value, tender.changes, tender.classification_confidence,
                    1 if tender.needs_review else 0, json.dumps(tender.review_reasons, ensure_ascii=False),
                    1 if tender.is_kbm_relevant else 0, json.dumps(tender.relevance_keywords, ensure_ascii=False),
                    tender.kbm_fit_score, tender.kbm_bu, tender.kbm_bu_ar, json.dumps(tender.kbm_vendors, ensure_ascii=False),
                    tender.kbm_presales_verdict, tender.kbm_presales_verdict_ar, tender.kbm_rationale,
                    json.dumps(tender.raw, ensure_ascii=False), now_iso, now_iso, new_hash
                ))
                conn.commit()
                return tender

            # Tender exists from a previous run: compare content
            old_hash = existing["content_hash"]
            diffs: List[str] = []

            if existing["closing_date"] != tender.closing_date:
                diffs.append(f"Closing date changed from {existing['closing_date']} to {tender.closing_date}")
            if existing["bid_bond"] != tender.bid_bond:
                diffs.append(f"Bid bond changed from {existing['bid_bond']} to {tender.bid_bond}")
            if existing["document_fee"] != tender.document_fee:
                diffs.append(f"Document fee changed from {existing['document_fee']} to {tender.document_fee}")
            if existing["notice_type"] != tender.notice_type:
                diffs.append(f"Notice type changed from {existing['notice_type']} to {tender.notice_type}")

            if old_hash != new_hash or diffs:
                tender.status = TenderStatus.UPDATED
                tender.changes = "; ".join(diffs) if diffs else "Tender content modified"
            else:
                tender.status = TenderStatus.UNCHANGED
                tender.changes = None

            if tender.closing_date and tender.closing_date < today_date:
                tender.status = TenderStatus.CLOSED

            # Merge sources list
            existing_sources = json.loads(existing["sources_json"])
            merged_sources_dict = {s["portal"]: s for s in existing_sources}
            for s in tender.sources:
                merged_sources_dict[s.portal] = s.model_dump()
            merged_sources = list(merged_sources_dict.values())

            cursor.execute("""
                UPDATE tenders SET
                    tender_no = ?, tender_no_normalized = ?, title_ar = ?, title_en = ?,
                    notice_type = ?, client_raw = ?, client = ?, sector = ?, account_owner = ?,
                    publish_date = ?, closing_date = ?, pre_bid_date = ?, bid_bond = ?, document_fee = ?,
                    category_code = ?, sources_json = ?, status = ?, changes = ?,
                    classification_confidence = ?, needs_review = ?, review_reasons_json = ?,
                    is_kbm_relevant = ?, relevance_keywords_json = ?,
                    kbm_fit_score = ?, kbm_bu = ?, kbm_bu_ar = ?, kbm_vendors_json = ?,
                    kbm_presales_verdict = ?, kbm_presales_verdict_ar = ?, kbm_rationale = ?,
                    raw_json = ?, last_seen = ?, content_hash = ?
                WHERE tender_uid = ?
            """, (
                tender.tender_no, tender.tender_no_normalized, tender.title_ar, tender.title_en,
                tender.notice_type, tender.client_raw, tender.client, tender.sector, tender.account_owner,
                tender.publish_date, tender.closing_date, tender.pre_bid_date, tender.bid_bond, tender.document_fee,
                tender.category_code, json.dumps(merged_sources, ensure_ascii=False),
                tender.status.value, tender.changes, tender.classification_confidence,
                1 if tender.needs_review else 0, json.dumps(tender.review_reasons, ensure_ascii=False),
                1 if tender.is_kbm_relevant else 0, json.dumps(tender.relevance_keywords, ensure_ascii=False),
                tender.kbm_fit_score, tender.kbm_bu, tender.kbm_bu_ar, json.dumps(tender.kbm_vendors, ensure_ascii=False),
                tender.kbm_presales_verdict, tender.kbm_presales_verdict_ar, tender.kbm_rationale,
                json.dumps(tender.raw, ensure_ascii=False), now_iso, new_hash, tender.tender_uid
            ))
            conn.commit()
            return tender

    def get_all_open_tenders(self) -> List[CanonicalTenderRecord]:
        """Returns all tenders whose closing date has not passed."""
        today_date = date.today().isoformat()
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tenders 
                WHERE (closing_date >= ? OR closing_date IS NULL)
                AND status != 'CANCELLED'
                ORDER BY closing_date ASC
            """, (today_date,))
            return [self._row_to_canonical(row) for row in cursor.fetchall()]

    def get_all_tenders(self) -> List[CanonicalTenderRecord]:
        """Returns all tenders in the store."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tenders ORDER BY first_seen DESC")
            return [self._row_to_canonical(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        """Returns aggregate metrics across portals and statuses."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM tenders")
            total = cursor.fetchone()["total"]
            
            cursor.execute("SELECT status, COUNT(*) as cnt FROM tenders GROUP BY status")
            by_status = {r["status"]: r["cnt"] for r in cursor.fetchall()}

            cursor.execute("SELECT sector, COUNT(*) as cnt FROM tenders GROUP BY sector")
            by_sector = {r["sector"]: r["cnt"] for r in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) as raw_count FROM raw_notices")
            raw_count = cursor.fetchone()["raw_count"]

            return {
                "total_canonical_tenders": total,
                "total_raw_notices": raw_count,
                "by_status": by_status,
                "by_sector": by_sector
            }

    @staticmethod
    def _row_to_canonical(row: sqlite3.Row) -> CanonicalTenderRecord:
        """Converts an SQLite row into a CanonicalTenderRecord object."""
        sources = [SourceRef(**s) for s in json.loads(row["sources_json"])]
        row_keys = row.keys()
        
        kbm_vendors = []
        if "kbm_vendors_json" in row_keys and row["kbm_vendors_json"]:
            try:
                kbm_vendors = json.loads(row["kbm_vendors_json"])
            except Exception:
                pass

        fit_score = float(row["kbm_fit_score"]) if "kbm_fit_score" in row_keys and row["kbm_fit_score"] is not None else 0.0
        bu = row["kbm_bu"] if "kbm_bu" in row_keys and row["kbm_bu"] else "None"
        bu_ar = row["kbm_bu_ar"] if "kbm_bu_ar" in row_keys and row["kbm_bu_ar"] else "غير محدد"
        verdict = row["kbm_presales_verdict"] if "kbm_presales_verdict" in row_keys and row["kbm_presales_verdict"] else "UNRELATED"
        verdict_ar = row["kbm_presales_verdict_ar"] if "kbm_presales_verdict_ar" in row_keys and row["kbm_presales_verdict_ar"] else "غير متوافقة"
        rationale = row["kbm_rationale"] if "kbm_rationale" in row_keys and row["kbm_rationale"] else ""

        return CanonicalTenderRecord(
            tender_uid=row["tender_uid"],
            tender_no=row["tender_no"],
            tender_no_normalized=row["tender_no_normalized"],
            title_ar=row["title_ar"],
            title_en=row["title_en"],
            notice_type=row["notice_type"],
            client_raw=row["client_raw"],
            client=row["client"],
            sector=row["sector"],
            account_owner=row["account_owner"],
            publish_date=row["publish_date"],
            closing_date=row["closing_date"],
            pre_bid_date=row["pre_bid_date"],
            bid_bond=row["bid_bond"],
            document_fee=row["document_fee"],
            category_code=row["category_code"],
            sources=sources,
            status=TenderStatus(row["status"]),
            changes=row["changes"],
            classification_confidence=row["classification_confidence"],
            needs_review=bool(row["needs_review"]),
            review_reasons=json.loads(row["review_reasons_json"]),
            is_kbm_relevant=bool(row["is_kbm_relevant"]),
            relevance_keywords=json.loads(row["relevance_keywords_json"]),
            kbm_fit_score=fit_score,
            kbm_bu=bu,
            kbm_bu_ar=bu_ar,
            kbm_vendors=kbm_vendors,
            kbm_presales_verdict=verdict,
            kbm_presales_verdict_ar=verdict_ar,
            kbm_rationale=rationale,
            raw=json.loads(row["raw_json"])
        )

    def reclassify_all_with_kbm_profile(self) -> int:
        """
        Re-evaluates every tender in the database against the KBM Company Profile
        and updates its fit score, primary BU, vendors, presales verdict, and Account Manager.
        """
        from src.pipeline.kbm_qualifier import KBMQualifier
        from src.pipeline.account_manager import resolve_account_manager
        tenders = self.get_all_tenders()
        count = 0
        with self._connection() as conn:
            cursor = conn.cursor()
            for t in tenders:
                res = KBMQualifier.evaluate_tender(t.title_ar, t.client)
                am = resolve_account_manager(t.client) or resolve_account_manager(t.client_raw) or t.account_owner or "Unassigned"
                cursor.execute("""
                    UPDATE tenders SET
                        account_owner = ?,
                        kbm_fit_score = ?,
                        kbm_bu = ?,
                        kbm_bu_ar = ?,
                        kbm_vendors_json = ?,
                        kbm_presales_verdict = ?,
                        kbm_presales_verdict_ar = ?,
                        kbm_rationale = ?,
                        is_kbm_relevant = ?
                    WHERE tender_uid = ?
                """, (
                    am,
                    res["fit_score"],
                    res["primary_bu"],
                    res["primary_bu_ar"],
                    json.dumps(res["matched_vendors"], ensure_ascii=False),
                    res["presales_verdict"],
                    res["presales_verdict_ar"],
                    res["rationale"],
                    1 if res["is_kbm_relevant"] else 0,
                    t.tender_uid
                ))
                count += 1
            conn.commit()
        return count
