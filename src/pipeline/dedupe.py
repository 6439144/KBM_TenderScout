"""
Cross-Portal Deduplication Engine for KBM Tender Scout.
Matches tenders across CAPT and Kuwait Al-Yawm, merging multiple sources into unified records (FR-4).
"""

import re
import difflib
from typing import List, Optional, Tuple

def string_similarity(s1: str, s2: str) -> float:
    """Computes similarity ratio (0 - 100) between two strings using difflib or rapidfuzz."""
    try:
        from rapidfuzz import fuzz
        return float(fuzz.ratio(s1, s2))
    except ImportError:
        return difflib.SequenceMatcher(None, s1, s2).ratio() * 100.0

from src.models import CanonicalTenderRecord, SourceRef
from src.pipeline.normalizer import normalize_arabic_text

class Deduplicator:
    @staticmethod
    def normalize_tender_number(tender_no: str) -> str:
        """
        Normalizes tender number for cross-portal matching.
        E.g. 'RFP/2162140' -> 'RFP2162140', '12 / 2025' -> '122025'.
        """
        if not tender_no:
            return ""
        # Remove whitespace, hyphens, slashes, and periods
        cleaned = re.sub(r'[\s\-/\.]', '', tender_no).upper()
        return cleaned

    @classmethod
    def match_records(
        cls,
        new_record: CanonicalTenderRecord,
        existing_records: List[CanonicalTenderRecord]
    ) -> Tuple[Optional[CanonicalTenderRecord], bool, Optional[str]]:
        """
        Finds a matching existing tender record.
        Returns (matched_record, is_uncertain, reason).
        """
        new_no_clean = cls.normalize_tender_number(new_record.tender_no)
        new_client_norm = normalize_arabic_text(new_record.client)

        for candidate in existing_records:
            cand_no_clean = cls.normalize_tender_number(candidate.tender_no)
            cand_client_norm = normalize_arabic_text(candidate.client)

            # Match 1: Exact normalized tender number match
            if new_no_clean and new_no_clean == cand_no_clean:
                # Compare client and title
                client_match = (
                    new_client_norm == cand_client_norm or
                    new_client_norm in cand_client_norm or
                    cand_client_norm in new_client_norm or
                    new_record.client == "غير محدد" or
                    candidate.client == "غير محدد"
                )
                title_sim = string_similarity(
                    normalize_arabic_text(new_record.title_ar),
                    normalize_arabic_text(candidate.title_ar)
                )

                if client_match or title_sim > 65:
                    return candidate, False, "Exact tender number and client/title alignment"
                else:
                    return candidate, True, f"Tender number matches '{candidate.tender_no}' but client or title differs significantly"

            # Match 2: Fuzzy title similarity for notices without structured tender numbers
            if len(new_record.title_ar) > 20 and len(candidate.title_ar) > 20:
                title_sim = string_similarity(
                    normalize_arabic_text(new_record.title_ar),
                    normalize_arabic_text(candidate.title_ar)
                )
                if title_sim > 88 and new_client_norm == cand_client_norm:
                    return candidate, True, f"High title similarity ({title_sim}%) across portals"

        return None, False, None

    @staticmethod
    def merge_sources(target: CanonicalTenderRecord, incoming: CanonicalTenderRecord) -> None:
        """Merges incoming source references into the target record."""
        existing_portals = {s.portal: s for s in target.sources}
        for inc_s in incoming.sources:
            if inc_s.portal not in existing_portals:
                target.sources.append(inc_s)
            else:
                existing_portals[inc_s.portal].last_seen = inc_s.last_seen
