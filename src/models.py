"""
Core Domain Models and Schemas for KBM Tender Scout.
Defines canonical tender representations, connector interfaces, and failure classifications.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class FailureReason(str, Enum):
    BAD_CREDENTIALS = "BAD_CREDENTIALS"
    CHALLENGE = "CHALLENGE"
    SESSION_CONFLICT = "SESSION_CONFLICT"
    SITE_DOWN = "SITE_DOWN"
    LAYOUT_CHANGED = "LAYOUT_CHANGED"
    UNKNOWN = "UNKNOWN"

class SessionResult(BaseModel):
    success: bool
    is_authenticated: bool = False
    error_type: Optional[FailureReason] = None
    message: str = ""
    portal_id: str

class NoticeRef(BaseModel):
    portal_id: str
    tender_no_raw: str
    detail_url: str
    issue_no: Optional[str] = None
    page_ref: Optional[str] = None
    publish_date_hint: Optional[str] = None
    client_hint: Optional[str] = None
    notice_type_hint: Optional[str] = None
    download_url: Optional[str] = None
    html_url: Optional[str] = None
    ads_id: Optional[str] = None

class RawNotice(BaseModel):
    portal_id: str
    tender_no: str
    title_raw: str
    client_raw: Optional[str] = None
    publish_date_raw: Optional[str] = None
    closing_date_raw: Optional[str] = None
    pre_bid_raw: Optional[str] = None
    notice_type_raw: Optional[str] = None
    bid_bond_raw: Optional[str] = None
    document_fee_raw: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    extra_fields: Dict[str, Any] = Field(default_factory=dict)
    source_url: str
    scraped_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class TenderStatus(str, Enum):
    NEW = "NEW"
    UPDATED = "UPDATED"
    UNCHANGED = "UNCHANGED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class SourceRef(BaseModel):
    portal: str
    url: str
    issue_no: Optional[str] = None
    page: Optional[str] = None
    first_seen: str
    last_seen: str

class CanonicalTenderRecord(BaseModel):
    tender_uid: str
    tender_no: str
    tender_no_normalized: str
    title_ar: str
    title_en: Optional[str] = None
    notice_type: str = "tender"
    client_raw: str
    client: str
    sector: str
    account_owner: Optional[str] = None
    publish_date: Optional[str] = None
    closing_date: Optional[str] = None
    pre_bid_date: Optional[str] = None
    bid_bond: Optional[str] = None
    document_fee: Optional[str] = None
    category_code: Optional[str] = None
    sources: List[SourceRef] = Field(default_factory=list)
    status: TenderStatus = TenderStatus.NEW
    changes: Optional[str] = None
    classification_confidence: float = 1.0
    needs_review: bool = False
    review_reasons: List[str] = Field(default_factory=list)
    is_kbm_relevant: bool = True
    relevance_keywords: List[str] = Field(default_factory=list)
    kbm_fit_score: float = 0.0
    kbm_bu: Optional[str] = "None"
    kbm_bu_ar: Optional[str] = "غير محدد"
    kbm_vendors: List[str] = Field(default_factory=list)
    kbm_presales_verdict: str = "UNRELATED"
    kbm_presales_verdict_ar: str = "غير متوافقة"
    kbm_rationale: str = ""
    raw: Dict[str, Any] = Field(default_factory=dict)
