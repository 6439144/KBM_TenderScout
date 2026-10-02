"""
Relevance Filter for KBM Tender Scout.
Identifies tenders matching KBM's ICT solution competencies (systems integration, infrastructure, software).
"""

from typing import List, Tuple
from src.config import FilterConfig
from src.pipeline.normalizer import normalize_arabic_text

class RelevanceFilter:
    def __init__(self, config: FilterConfig):
        self.config = config
        self.keywords_ar_norm = [normalize_arabic_text(kw) for kw in config.keywords_ar]
        self.keywords_en_lower = [kw.lower() for kw in config.keywords_en]

    def evaluate_relevance(self, title: str, extra_text: str = "") -> Tuple[bool, List[str]]:
        """
        Determines if a tender notice matches KBM ICT competencies.
        Returns (is_relevant, matched_keywords_list).
        """
        if not self.config.enabled:
            return True, ["FILTER_DISABLED"]

        combined_text = f"{title} {extra_text}"
        norm_ar = normalize_arabic_text(combined_text)
        lower_en = combined_text.lower()

        matched: List[str] = []

        # Check Arabic ICT keywords
        for kw_orig, kw_norm in zip(self.config.keywords_ar, self.keywords_ar_norm):
            if kw_norm in norm_ar:
                matched.append(kw_orig)

        # Check English ICT keywords
        for kw_orig, kw_lower in zip(self.config.keywords_en, self.keywords_en_lower):
            if kw_lower in lower_en:
                matched.append(kw_orig)

        is_relevant = len(matched) > 0
        return is_relevant, matched
