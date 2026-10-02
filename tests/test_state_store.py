"""
Unit Tests for SQLite State Store (FR-4 & Acceptance Criteria).
Tests lifecycle states (NEW, UNCHANGED, UPDATED, CLOSED) and multi-portal source merging.
"""

from datetime import date, timedelta
from pathlib import Path
import pytest

from src.models import CanonicalTenderRecord, SourceRef, TenderStatus
from src.pipeline.state_store import StateStore

@pytest.fixture
def temp_store(tmp_path):
    db_file = tmp_path / "test_state.db"
    return StateStore(db_path=db_file)

def test_tender_lifecycle_and_updates(temp_store):
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
    res1 = temp_store.upsert_canonical_tender(t1)
    assert res1.status == TenderStatus.NEW
    assert res1.changes is None

    # 2. Second run: Same tender, no changes -> UNCHANGED
    t2 = t1.model_copy()
    res2 = temp_store.upsert_canonical_tender(t2)
    assert res2.status == TenderStatus.UNCHANGED
    assert res2.changes is None

    # 3. Third run: Closing date extended -> UPDATED with diff description
    t3 = t1.model_copy()
    t3.closing_date = extended_date
    res3 = temp_store.upsert_canonical_tender(t3)
    assert res3.status == TenderStatus.UPDATED
    assert f"Closing date changed from {future_date} to {extended_date}" in res3.changes

    # 4. Multi-portal source merging: Kuwait Al-Yawm also discovers the tender
    t4 = t3.model_copy()
    t4.sources = [
        SourceRef(portal="kuwait_alyawm", url="https://kuwaitalyawm.media.gov.kw", issue_no="1810", page="238", first_seen=today, last_seen=today)
    ]
    res4 = temp_store.upsert_canonical_tender(t4)
    # Total canonical tenders remains 1
    stats = temp_store.get_stats()
    assert stats["total_canonical_tenders"] == 1
    
    # Retrieve all open
    open_tenders = temp_store.get_all_open_tenders()
    assert len(open_tenders) == 1
    sources = open_tenders[0].sources
    portals = {s.portal for s in sources}
    assert "capt" in portals
    assert "kuwait_alyawm" in portals

def test_closed_tender_handling(temp_store):
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
    res = temp_store.upsert_canonical_tender(t_closed)
    assert res.status == TenderStatus.CLOSED

    open_tenders = temp_store.get_all_open_tenders()
    assert len(open_tenders) == 0
