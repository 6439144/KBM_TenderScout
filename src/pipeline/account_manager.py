"""
KBM Tender Scout - Account Manager Resolution Engine
Official Hierarchy:
Marketing Manager for Government & Oil Sector: Eiman Ashkanani

Government Team:
- Jana Al-Obaid: PIFSS, PADA, Nazaha, MOH
- Raed Obeid: MEW, PACI
- Khaled Alabdallah: MOI

Oil Team:
- Ahmed Habib: KOC, KOTC
- Abrar Al-Qallaf: KNPC, PIC

Any other accounts assign to Eiman Ashkanani herself.
"""

import re
from typing import Optional
from src.pipeline.normalizer import normalize_arabic_text

# Direct mapping from Client Identifiers & Aliases to Designated Team Member
CLIENT_ID_TO_AM = {
    # Government: Jana Al-Obaid
    "pifss": "Jana Al-Obaid",        # PIFSS - Public Institution for Social Security
    "the_23": "Jana Al-Obaid",       # المؤسسة العامة للتأمينات الاجتماعية
    "pada": "Jana Al-Obaid",         # PADA - Public Authority for Disability Affairs
    "cpa": "Jana Al-Obaid",          # Nazaha - Public Authority for Anti-Corruption
    "moh": "Jana Al-Obaid",          # MOH - Ministry of Health

    # Government: Raed Obeid
    "mew": "Raed Obeid",             # MEW - Ministry of Electricity & Water
    "paci": "Raed Obeid",            # PACI - Public Authority for Civil Information

    # Government: Khaled Alabdallah
    "moi": "Khaled Alabdallah",      # MOI - Ministry of Interior

    # Oil: Ahmed Habib
    "koc": "Ahmed Habib",            # KOC - Kuwait Oil Company
    "kotc": "Ahmed Habib",           # KOTC - Kuwait Oil Tanker Company

    # Oil: Abrar Al-Qallaf
    "knpc": "Abrar Al-Qallaf",       # KNPC - Kuwait National Petroleum Company
    "pic": "Abrar Al-Qallaf",        # PIC - Petrochemical Industries Company

    # All other accounts assigned directly to Eiman Ashkanani (Marketing Manager)
    "kpc": "Eiman Ashkanani",        # KPC - Kuwait Petroleum Corporation
    "kipic": "Eiman Ashkanani",      # KIPIC - Kuwait Integrated Petroleum Industries
    "kufpec": "Eiman Ashkanani",     # KUFPEC - Kuwait Foreign Petroleum Exploration
    "kuwait_17": "Eiman Ashkanani",  # KUFPEC Arabic alias
    "kuwait_19": "Eiman Ashkanani",  # KGOC - Kuwait Gulf Oil Company
    "mod": "Eiman Ashkanani",        # MOD - Ministry of Defense
    "mpw": "Eiman Ashkanani",        # MPW - Ministry of Public Works
    "km": "Eiman Ashkanani",         # KM - Kuwait Municipality
    "mof": "Eiman Ashkanani",        # MOF - Ministry of Finance
    "moe": "Eiman Ashkanani",        # MOE - Ministry of Education
    "mohe": "Eiman Ashkanani",       # MOHE - Ministry of Higher Education
    "ku": "Eiman Ashkanani",         # KU - Kuwait University
    "paaet": "Eiman Ashkanani",      # PAAET - Applied Education
    "csc": "Eiman Ashkanani",        # CSC - Civil Service Commission
    "customs": "Eiman Ashkanani",    # Customs - General Administration of Customs
    "dgca": "Eiman Ashkanani",       # DGCA - Directorate General of Civil Aviation
    "general_3": "Eiman Ashkanani",  # KFF - Kuwait Fire Force
    "ncsc": "Eiman Ashkanani",       # NCSC - National Cyber Security Center
    "abdullah_salem": "Eiman Ashkanani", # Abdullah Al-Salem University
    "pahw": "Eiman Ashkanani",       # PAHW - Housing Welfare
    "paht": "Eiman Ashkanani",       # الرعاية السكنية
    "pai": "Eiman Ashkanani",        # PAI - Industry
    "public_26": "Eiman Ashkanani",  # الهيئة العامة للصناعة
    "moci": "Eiman Ashkanani",       # MOCI - Commerce and Industry
    "paf": "Eiman Ashkanani",        # PAAAFR - Agriculture
    "mosa": "Eiman Ashkanani",       # MOSA - Social Affairs
    "general_5": "Eiman Ashkanani",  # الأوقاف
    "pafn": "Eiman Ashkanani",       # Food & Nutrition
    "kng": "Eiman Ashkanani",        # KNG - Kuwait National Guard
    "kuwait_13": "Eiman Ashkanani",  # الرئاسة العامة للحرس الوطني
    "kfas": "Eiman Ashkanani",       # KFAS - Foundation for Advancement of Sciences
    "kisr": "Eiman Ashkanani",       # KISR - Institute for Scientific Research
}

# Arabic normalized substring keywords
ARABIC_RULES = [
    # 1. Jana Al-Obaid (PIFSS, PADA, Nazaha, MOH)
    ("تامينات", "Jana Al-Obaid"),
    ("تأمينات", "Jana Al-Obaid"),
    ("pifss", "Jana Al-Obaid"),
    ("اعاقه", "Jana Al-Obaid"),
    ("إعاقة", "Jana Al-Obaid"),
    ("ذوي الاعاقة", "Jana Al-Obaid"),
    ("ذوي الإعاقة", "Jana Al-Obaid"),
    ("pada", "Jana Al-Obaid"),
    ("نزاهه", "Jana Al-Obaid"),
    ("نزاهة", "Jana Al-Obaid"),
    ("مكافحة الفساد", "Jana Al-Obaid"),
    ("cpa", "Jana Al-Obaid"),
    ("صحه", "Jana Al-Obaid"),
    ("صحة", "Jana Al-Obaid"),
    ("moh", "Jana Al-Obaid"),

    # 2. Raed Obeid (MEW, PACI)
    ("كهرباء", "Raed Obeid"),
    ("mew", "Raed Obeid"),
    ("معلومات مدنيه", "Raed Obeid"),
    ("معلومات مدنية", "Raed Obeid"),
    ("مدنيه", "Raed Obeid"),
    ("مدنية", "Raed Obeid"),
    ("paci", "Raed Obeid"),

    # 3. Khaled Alabdallah (MOI)
    ("داخليه", "Khaled Alabdallah"),
    ("داخلية", "Khaled Alabdallah"),
    ("الداخلية", "Khaled Alabdallah"),
    ("الداخليه", "Khaled Alabdallah"),
    ("moi", "Khaled Alabdallah"),

    # 4. Ahmed Habib (Oil: KOC, KOTC)
    ("نفط الكويت", "Ahmed Habib"),
    ("koc", "Ahmed Habib"),
    ("ناقلات النفط", "Ahmed Habib"),
    ("ناقلات", "Ahmed Habib"),
    ("kotc", "Ahmed Habib"),

    # 5. Abrar Al-Qallaf (Oil: KNPC, PIC)
    ("البترول الوطنية", "Abrar Al-Qallaf"),
    ("البترول الوطنيه", "Abrar Al-Qallaf"),
    ("بترول وطنية", "Abrar Al-Qallaf"),
    ("بترول وطنيه", "Abrar Al-Qallaf"),
    ("knpc", "Abrar Al-Qallaf"),
    ("كيماويات بترولية", "Abrar Al-Qallaf"),
    ("كيماويات", "Abrar Al-Qallaf"),
    ("صناعة الكيماويات", "Abrar Al-Qallaf"),
    ("pic", "Abrar Al-Qallaf"),
]

DEFAULT_OWNER = "Eiman Ashkanani"

def resolve_account_manager(client_name: Optional[str], client_id: Optional[str] = "") -> str:
    """
    Resolves the official KBM Account Manager according to the organizational hierarchy:
    - Marketing Manager: Eiman Ashkanani
    - Gov: Jana Al-Obaid (PIFSS, PADA, Nazaha, MOH)
    - Gov: Raed Obeid (MEW, PACI)
    - Gov: Khaled Alabdallah (MOI)
    - Oil: Ahmed Habib (KOC, KOTC)
    - Oil: Abrar Al-Qallaf (KNPC, PIC)
    - Any other accounts assign to Eiman Ashkanani herself.
    """
    if not client_name or client_name.strip() in ("", "غير محدد", "None"):
        return DEFAULT_OWNER

    # 1. Match by client_id
    if client_id and client_id.lower().strip() in CLIENT_ID_TO_AM:
        return CLIENT_ID_TO_AM[client_id.lower().strip()]

    raw_clean = client_name.lower().strip()
    norm = normalize_arabic_text(client_name).lower()

    # 2. Match by Arabic rules (longest pattern first)
    sorted_rules = sorted(ARABIC_RULES, key=lambda x: len(x[0]), reverse=True)
    for pattern, am in sorted_rules:
        pat_norm = normalize_arabic_text(pattern).lower()
        if pattern in raw_clean or pat_norm in norm:
            return am

    # 3. Default fallback for any other account: Eiman Ashkanani
    return DEFAULT_OWNER
