"""
Unit Tests for StateStore using Python standard unittest.
Tests tender lifecycle transitions (NEW, UNCHANGED, UPDATED, CLOSED) and source merging.
"""

import sys
import unittest
import tempfile
from datetime import date, timedelta
from pathlib import Path

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import CanonicalTenderRecord, SourceRef, TenderStatus
from src.pipeline.state_store import StateStore

class TestStateStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_state.db"
        self.store = StateStore(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_tender_lifecycle_and_updates(self):
        today = date.today().isoformat()
        future_date = (date.today() + timedelta(days=30)).isoformat()
        extended_date = (date.today() + timedelta(days=45)).isoformat()

        # 1. First run: Insert NEW tender
        t1 = CanonicalTenderRecord(
            tender_uid="capt_12_2025",
            tender_no="12/2025",
            tender_no_normalized="12/2025",
            title_ar="أعمال صيانة المعدات",
            notice_type="tender",
            client_raw="الهيئة العامة للصناعة",
            client="الهيئة العامة للصناعة",
            sector="government",
            closing_date=future_date,
            bid_bond="45,000 KWD",
            document_fee="1,000 KWD",
            sources=[SourceRef(portal="capt", url="https://capt.gov.kw", first_seen=today, last_seen=today)],
            status=TenderStatus.NEW
        )
        res1 = self.store.upsert_canonical_tender(t1)
        self.assertEqual(res1.status, TenderStatus.NEW)
        self.assertIsNone(res1.changes)

        # 2. Second run: Same tender, no changes -> UNCHANGED
        t2 = t1.model_copy()
        res2 = self.store.upsert_canonical_tender(t2)
        self.assertEqual(res2.status, TenderStatus.UNCHANGED)
        self.assertIsNone(res2.changes)

        # 3. Third run: Closing date extended -> UPDATED with diff description
        t3 = t1.model_copy()
        t3.closing_date = extended_date
        res3 = self.store.upsert_canonical_tender(t3)
        self.assertEqual(res3.status, TenderStatus.UPDATED)
        self.assertIn(f"Closing date changed from {future_date} to {extended_date}", res3.changes)

        # 4. Multi-portal source merging
        t4 = t3.model_copy()
        t4.sources = [
            SourceRef(portal="kuwait_alyawm", url="https://kuwaitalyawm.media.gov.kw", issue_no="1810", page="238", first_seen=today, last_seen=today)
        ]
        res4 = self.store.upsert_canonical_tender(t4)
        stats = self.store.get_stats()
        self.assertEqual(stats["total_canonical_tenders"], 1)

        open_tenders = self.store.get_all_open_tenders()
        self.assertEqual(len(open_tenders), 1)
        sources = open_tenders[0].sources
        portals = {s.portal for s in sources}
        self.assertIn("capt", portals)
        self.assertIn("kuwait_alyawm", portals)

    def test_closed_tender_handling(self):
        past_date = (date.today() - timedelta(days=5)).isoformat()
        t_closed = CanonicalTenderRecord(
            tender_uid="capt_past_99",
            tender_no="99/2024",
            tender_no_normalized="99/2024",
            title_ar="توريد قديم",
            notice_type="tender",
            client_raw="وزارة المالية",
            client="وزارة المالية",
            sector="government",
            closing_date=past_date,
            status=TenderStatus.NEW
        )
        res = self.store.upsert_canonical_tender(t_closed)
        self.assertEqual(res.status, TenderStatus.CLOSED)

        open_tenders = self.store.get_all_open_tenders()
        self.assertEqual(len(open_tenders), 0)

if __name__ == "__main__":
    unittest.main()
