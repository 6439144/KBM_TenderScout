"""
Data Normalization Engine for KBM Tender Scout.
Converts Arabic-Indic digits, normalizes Arabic text for matching, parses Kuwait dates and money.
"""

import re
from datetime import datetime
from typing import Optional, Tuple

# Mapping of Arabic-Indic digits to Western ASCII digits
ARABIC_INDIC_DIGITS = {
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
}

# Arabic Gregorian month names used in Kuwait government notices
ARABIC_MONTHS = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "ابريل": 4,
    "مايو": 5, "يونيو": 6, "يوليو": 7, "أغسطس": 8, "اغسطس": 8,
    "سبتمبر": 9, "أكتوبر": 10, "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12
}

# Hijri month names for detecting Islamic calendar dates
HIJRI_MONTHS = [
    "محرم", "صفر", "ربيع الأول", "ربيع الاول", "ربيع الثاني", "ربيع الاخر",
    "جمادى الأولى", "جمادى الاولى", "جمادى الآخرة", "جمادى الاخرة",
    "رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة"
]

def convert_arabic_digits(text: Optional[str]) -> str:
    """Converts Arabic-Indic numerals (٠-٩) to standard Western numerals (0-9)."""
    if not text:
        return ""
    result = []
    for char in text:
        result.append(ARABIC_INDIC_DIGITS.get(char, char))
    return "".join(result)

def normalize_arabic_text(text: Optional[str]) -> str:
    """
    Normalizes Arabic string for fuzzy and exact matching.
    Removes diacritics (tashkeel), tatweel (kashida), unifies alef, teh marbuta, and alef maqsura.
    Display retains the original string; this is used strictly for comparisons.
    """
    if not text:
        return ""
    s = text.strip()

    # Remove tashkeel (diacritics: fatha, damma, kasra, sukun, shadda, tanwin)
    s = re.sub(r'[\u064B-\u0652\u0670]', '', s)

    # Remove tatweel (kashida)
    s = re.sub(r'\u0640', '', s)

    # Unify Alef forms (أ, إ, آ, ٱ -> ا)
    s = re.sub(r'[إأآٱ]', 'ا', s)

    # Treat Teh Marbuta and Heh consistently (ة -> ه)
    s = re.sub(r'ة', 'ه', s)

    # Treat Alef Maqsura and Yeh consistently (ى -> ي)
    s = re.sub(r'ى', 'ي', s)

    # Remove repeated whitespace and punctuation
    s = re.sub(r'[_\-\.,/\\()\[\]]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s.lower()

def parse_kuwait_date(raw_date_str: Optional[str]) -> Tuple[Optional[str], bool, bool]:
    """
    Parses a Kuwait portal date string into an ISO format (YYYY-MM-DD).
    Returns: (iso_date, is_hijri, needs_review)
    """
    if not raw_date_str:
        return None, False, False

    clean_str = convert_arabic_digits(raw_date_str).strip()

    # Check if date is Hijri
    if any(hm in clean_str for hm in HIJRI_MONTHS):
        return None, True, True  # Keep raw value and flag for review (Rule FR-5)

    # Format 1: Arabic Month Name, e.g. "سبتمبر 27, 2026" or "27 سبتمبر 2026"
    for month_name, month_num in ARABIC_MONTHS.items():
        if month_name in clean_str:
            # Match "سبتمبر 27, 2026"
            m = re.search(r'(?:' + month_name + r')\s+(\d{1,2}),?\s+(\d{4})', clean_str)
            if m:
                day, year = int(m.group(1)), int(m.group(2))
                return f"{year:04d}-{month_num:02d}-{day:02d}", False, False
            # Match "27 سبتمبر 2026"
            m = re.search(r'(\d{1,2})\s+(?:' + month_name + r')\s+(\d{4})', clean_str)
            if m:
                day, year = int(m.group(1)), int(m.group(2))
                return f"{year:04d}-{month_num:02d}-{day:02d}", False, False

    # Format 2: Slash format DD/MM/YYYY or YYYY/MM/DD
    slash_match = re.search(r'(\d{1,4})[/\-](\d{1,2})[/\-](\d{1,4})', clean_str)
    if slash_match:
        p1, p2, p3 = int(slash_match.group(1)), int(slash_match.group(2)), int(slash_match.group(3))
        if p1 > 1900:  # YYYY-MM-DD
            return f"{p1:04d}-{p2:02d}-{p3:02d}", False, False
        if p3 > 1900:  # DD/MM/YYYY
            return f"{p3:04d}-{p2:02d}-{p1:02d}", False, False

    # Format 3: Already ISO format YYYY-MM-DD
    iso_match = re.search(r'^\d{4}-\d{2}-\d{2}$', clean_str)
    if iso_match:
        return clean_str, False, False

    # Unrecognized format: flag for review
    return None, False, True

def parse_money(raw_money_str: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses currency and amounts from Kuwait notices (e.g. '1000.000 د.ك' -> ('1000.000', 'KWD')).
    """
    if not raw_money_str:
        return None, None

    clean = convert_arabic_digits(raw_money_str).strip()
    # Find decimal or integer number with optional commas
    num_match = re.search(r'([\d,]+(?:\.\d+)?)', clean)
    if not num_match:
        return None, None

    amount = num_match.group(1).replace(",", "")
    currency = "KWD"
    if "د.ك" in clean or "دينار" in clean or "kd" in clean.lower() or "kwd" in clean.lower():
        currency = "KWD"
    elif "$" in clean or "usd" in clean.lower() or "دولار" in clean:
        currency = "USD"

    return f"{amount} {currency}", amount
