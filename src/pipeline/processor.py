"""
Pipeline Processor for KBM Tender Scout.
Orchestrates normalization, client/sector classification, relevance filtering, and deduplication.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.config import RootConfig
from src.models import CanonicalTenderRecord, RawNotice, SourceRef, TenderStatus
from src.pipeline.classifier import ClientSectorClassifier
from src.pipeline.dedupe import Deduplicator
from src.pipeline.filter import RelevanceFilter
from src.pipeline.kbm_qualifier import KBMQualifier
from src.pipeline.normalizer import (
    convert_arabic_digits,
    normalize_arabic_text,
    parse_kuwait_date,
    parse_money
)
from src.pipeline.state_store import StateStore

class TenderProcessor:
    def __init__(self, config: RootConfig, state_store: StateStore):
        self.config = config
        self.state_store = state_store
        self.classifier = ClientSectorClassifier(
            clients_csv_path=Path(config.classification.clients_master_file),
            sectors_yaml_path=Path(config.classification.sectors_file),
            pending_csv_path=Path(config.classification.clients_pending_file),
            confidence_threshold=config.classification.confidence_threshold
        )
        self.filter = RelevanceFilter(config.filter)

    def process_raw_notice(self, raw: RawNotice) -> CanonicalTenderRecord:
        """Processes a single raw notice through the full Milestone 3 pipeline."""
        now_iso = datetime.now().isoformat()
        review_reasons: List[str] = []

        # 1. Normalize dates
        closing_iso, is_closing_hijri, closing_needs_review = parse_kuwait_date(raw.closing_date_raw)
        if closing_needs_review:
            review_reasons.append(f"UNPARSED_CLOSING_DATE: '{raw.closing_date_raw}'")

        publish_iso, is_pub_hijri, pub_needs_review = parse_kuwait_date(raw.publish_date_raw)
        if pub_needs_review:
            review_reasons.append(f"UNPARSED_PUBLISH_DATE: '{raw.publish_date_raw}'")

        # 2. Normalize money
        doc_fee_clean, _ = parse_money(raw.document_fee_raw)
        bond_clean, _ = parse_money(raw.bid_bond_raw)

        # 3. Clean tender number and title
        tender_no_norm = Deduplicator.normalize_tender_number(raw.tender_no)
        uid = f"{raw.portal_id}_{tender_no_norm}"

        # 4. Classify Client & Sector
        canonical_client, sector, account_owner, confidence, client_needs_review, client_reasons = (
            self.classifier.classify_client_and_sector(raw.client_raw, uid, raw.portal_id)
        )
        review_reasons.extend(client_reasons)

        # 5. Evaluate KBM Profile Alignment & Presales Qualification
        extra_scope = raw.extra_fields.get("announcement_snippet", "")
        kbm_eval = KBMQualifier.evaluate_tender(raw.title_raw, canonical_client, extra_scope)
        is_relevant, matched_kws = self.filter.evaluate_relevance(raw.title_raw, extra_scope)
        all_keywords = list(set(matched_kws + kbm_eval["matched_keywords"]))
        is_kbm_fit = is_relevant or kbm_eval["is_kbm_relevant"]

        # 6. Build Source Reference
        source = SourceRef(
            portal=raw.portal_id,
            url=raw.source_url,
            issue_no=raw.extra_fields.get("issue_no"),
            page=raw.extra_fields.get("page_no"),
            first_seen=now_iso,
            last_seen=now_iso
        )

        needs_review = len(review_reasons) > 0 or client_needs_review or (confidence < self.config.classification.confidence_threshold)

        # 7. Construct Canonical Record
        # Extract requirements
        reqs_raw = raw.extra_fields.get("requirements", [])
        if isinstance(reqs_raw, list):
            reqs_str = "\n".join(f"• {r}" for r in reqs_raw if r)
        else:
            reqs_str = str(reqs_raw or "")

        record = CanonicalTenderRecord(
            tender_uid=uid,
            tender_no=raw.tender_no,
            tender_no_normalized=tender_no_norm,
            title_ar=raw.title_raw,
            notice_type=raw.notice_type_raw or "tender",
            client_raw=raw.client_raw or "غير محدد",
            client=canonical_client,
            sector=sector,
            account_owner=account_owner,
            publish_date=publish_iso,
            closing_date=closing_iso,
            pre_bid_date=raw.pre_bid_raw,
            bid_bond=bond_clean,
            document_fee=doc_fee_clean,
            sources=[source],
            status=TenderStatus.NEW,
            classification_confidence=confidence,
            needs_review=needs_review,
            review_reasons=review_reasons,
            is_kbm_relevant=is_kbm_fit,
            relevance_keywords=all_keywords,
            kbm_fit_score=kbm_eval["fit_score"],
            kbm_bu=kbm_eval["primary_bu"],
            kbm_bu_ar=kbm_eval["primary_bu_ar"],
            kbm_vendors=kbm_eval["matched_vendors"],
            kbm_presales_verdict=kbm_eval["presales_verdict"],
            kbm_presales_verdict_ar=kbm_eval["presales_verdict_ar"],
            kbm_rationale=kbm_eval["rationale"],
            requirements=reqs_str,
            raw=raw.model_dump()
        )

        # 8. Cross-Portal Deduplication check
        existing_tenders = self.state_store.get_all_tenders()
        matched_existing, is_uncertain, match_reason = Deduplicator.match_records(record, existing_tenders)

        if matched_existing and not is_uncertain:
            # High-confidence cross-portal merge
            Deduplicator.merge_sources(matched_existing, record)

            # Update title: replace placeholder or LOADING titles with rich subject
            is_loading_title = bool(matched_existing.title_ar and ("LOADING" in matched_existing.title_ar or "LOADING PAGES" in matched_existing.title_ar))
            is_generic_title = bool(not matched_existing.title_ar or "الجريدة الرسمية" in matched_existing.title_ar or ":" not in matched_existing.title_ar)
            has_rich_title = bool(record.title_ar and "LOADING" not in record.title_ar and "الجريدة الرسمية" not in record.title_ar)

            if (is_loading_title or is_generic_title) and has_rich_title:
                matched_existing.title_ar = record.title_ar
            elif is_loading_title and record.title_ar and "LOADING" not in record.title_ar:
                matched_existing.title_ar = record.title_ar

            # Update client and sector
            if record.client and record.client != "غير محدد":
                matched_existing.client = record.client
                matched_existing.sector = record.sector
                if record.account_owner:
                    matched_existing.account_owner = record.account_owner

            # Update dates and financials
            if record.closing_date:
                matched_existing.closing_date = record.closing_date
            if record.pre_bid_date:
                matched_existing.pre_bid_date = record.pre_bid_date
            if record.bid_bond:
                matched_existing.bid_bond = record.bid_bond
            if record.document_fee:
                matched_existing.document_fee = record.document_fee
            if record.requirements:
                matched_existing.requirements = record.requirements

            # Update KBM presales evaluation
            if record.kbm_fit_score > (matched_existing.kbm_fit_score or 0) or (record.is_kbm_relevant and not matched_existing.is_kbm_relevant):
                matched_existing.kbm_fit_score = record.kbm_fit_score
                matched_existing.kbm_bu = record.kbm_bu
                matched_existing.kbm_bu_ar = record.kbm_bu_ar
                matched_existing.kbm_vendors = record.kbm_vendors
                matched_existing.kbm_presales_verdict = record.kbm_presales_verdict
                matched_existing.kbm_presales_verdict_ar = record.kbm_presales_verdict_ar
                matched_existing.kbm_rationale = record.kbm_rationale
                matched_existing.is_kbm_relevant = record.is_kbm_relevant
                matched_existing.relevance_keywords = list(set(matched_existing.relevance_keywords + record.relevance_keywords))

            return self.state_store.upsert_canonical_tender(matched_existing)

        elif matched_existing and is_uncertain:
            record.needs_review = True
            record.review_reasons.append(f"UNCERTAIN_DUPLICATE: {match_reason}")

        # 9. Save to State Store
        return self.state_store.upsert_canonical_tender(record)
