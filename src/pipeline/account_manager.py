"""
KBM Tender Scout - Account Manager Resolution Engine
Maps clients and tender issuing entities directly to their designated
KBM Account Manager based on the official Technology Pipeline Review:
'2026-Q3-28th-Sep-Tech Pipeline Review-ver1.1.xlsx'
"""

import re
from typing import Optional
from src.pipeline.normalizer import normalize_arabic_text

# Direct mapping from Client Identifiers & Aliases to Canonical Account Managers
CLIENT_ID_TO_AM = {
    "mew": "Raed Obeid",             # MEW - Ministry of Electricity & Water
    "mof": "Raed Obeid",             # MOF - Ministry of Finance
    "moj": "Raed Obeid",             # MOJ - Ministry of Justice
    "moe": "Raed Obeid",             # MOE - Ministry of Education
    "mohe": "Raed Obeid",            # MOHE - Ministry of Higher Education
    "ku": "Raed Obeid",              # KU - Kuwait University
    "paci": "Raed Obeid",            # PACI - Public Authority for Civil Information
    "csc": "Raed Obeid",             # CSC - Civil Service Commission
    "customs": "Raed Obeid",         # Customs - General Administration of Customs
    "dgca": "Raed Obeid",            # DGCA - Directorate General of Civil Aviation
    "general_3": "Raed Obeid",       # KFF - Kuwait Fire Force (الإدارة العامة للإطفاء)
    "ncsc": "Raed Obeid",            # NCSC - National Cyber Security Center
    "abdullah_salem": "Raed Obeid",  # Abdullah Al-Salem University

    "moi": "Fahad Al-Roumi",         # MOI - Ministry of Interior
    "kng": "Fahad Al-Roumi",         # KNG - Kuwait National Guard
    "kuwait_13": "Fahad Al-Roumi",   # الرئاسة العامة للحرس الوطني

    "pifss": "Jana Al-Obaid",        # PIFSS - Public Institution for Social Security
    "the_23": "Jana Al-Obaid",       # المؤسسة العامة للتأمينات الاجتماعية
    "mod": "Jana Al-Obaid",          # MOD - Ministry of Defense
    "moh": "Jana Al-Obaid",          # MOH - Ministry of Health
    "pahw": "Jana Al-Obaid",         # PAHW - Public Authority for Housing Welfare
    "paht": "Jana Al-Obaid",         # المؤسسة العامة للرعاية السكنية
    "pai": "Jana Al-Obaid",          # PAI - Public Authority for Industry
    "public_26": "Jana Al-Obaid",    # الهيئة العامة للصناعة
    "moci": "Jana Al-Obaid",         # MOCI - Ministry of Commerce and Industry
    "paf": "Jana Al-Obaid",          # PAAAFR - Agriculture (الهيئة العامة لشؤون الزراعة)
    "mosa": "Jana Al-Obaid",         # MOSA - Ministry of Social Affairs (وزارة الشئون الاجتماعية)
    "general_5": "Jana Al-Obaid",    # الأمانة العامة للأوقاف
    "pafn": "Jana Al-Obaid",         # الهيئة العامة للغذاء والتغذية
    "pada": "Jana Al-Obaid",         # شؤون ذوي الإعاقة

    "mpw": "Abrar Al-Qallaf",        # MPW - Ministry of Public Works (الأشغال العامة)
    "km": "Abrar Al-Qallaf",         # KM - Kuwait Municipality (بلدية الكويت)
    "kna": "Abrar Al-Qallaf",        # KNA - National Assembly (مجلس الأمة)
    "paaet": "Abrar Al-Qallaf",      # PAAET - Applied Education (التعليم التطبيقي)
    "cpa": "Abrar Al-Qallaf",        # Nazaha - Anti-Corruption (نزاهة)

    "kpc": "Eiman Ashkanani",       # KPC - Kuwait Petroleum Corporation
    "knpc": "Eiman Ashkanani",      # KNPC - Kuwait National Petroleum Company
    "kipic": "Eiman Ashkanani",     # KIPIC - Petrochemical Industries

    "koc": "Eiman Ashkanani",       # KOC - Kuwait Oil Company

    "kotc": "Wajih Fahad",           # KOTC - Kuwait Oil Tanker Company
    "pic": "Wajih Fahad",            # PIC - Petrochemical Industries Company
    "kufpec": "Wajih Fahad",         # KUFPEC - Foreign Petroleum Exploration
    "kuwait_17": "Wajih Fahad",      # الشركة الكويتية للاستكشافات البترولية الخارجية
    "kuwait_19": "Wajih Fahad",      # الشركة الكويتية لنفط الخليج (KGOC/WJO)

    "kfas": "Eiman Ashkanani",       # KFAS - Foundation for Advancement of Sciences
    "kisr": "Eiman Ashkanani",       # KISR - Institute for Scientific Research

    "nbk": "Ahmad Abu Jrab",         # NBK - National Bank of Kuwait
    "kfh": "Ahmad Abu Jrab",         # KFH - Kuwait Finance House

    "cbk": "Saleem Dalwai",          # CBK - Commercial Bank / Central Bank
    "abk": "Saleem Dalwai",          # ABK - Al Ahli Bank of Kuwait
    "burgan": "Saleem Dalwai",       # Burgan Bank
    "kia": "Saleem Dalwai",          # KIA - Kuwait Investment Authority

    "warba": "Usama Badra",          # Warba Bank
    "kib": "Usama Badra",            # KIB - Kuwait International Bank
    "knet": "Usama Badra",           # KNET - Shared Electronic Banking

    "moc": "Ehtisham Boota",         # MOC - Ministry of Communications
    "citra": "Ehtisham Boota",       # CITRA - Telecom Regulatory Authority
    "zain": "Ehtisham Boota",        # Zain Kuwait
    "media": "Ehtisham Boota",       # Ministry of Information (وزارة الإعلام)
    "ooredoo": "Tariq Al-Souqi",     # Ooredoo Kuwait
    "stc": "Tariq Al-Souqi",         # STC Kuwait
}

# Arabic normalized substring keywords
ARABIC_RULES = [
    # Defense & Interior
    ("الحرس الوطني", "Fahad Al-Roumi"),
    ("حرس وطني", "Fahad Al-Roumi"),
    ("حرس", "Fahad Al-Roumi"),
    ("داخليه", "Fahad Al-Roumi"),
    ("داخلية", "Fahad Al-Roumi"),

    # Oil & Gas (Assigned to Eiman Ashkanani)
    ("نفط الكويت", "Eiman Ashkanani"),
    ("koc", "Eiman Ashkanani"),
    ("البترول الوطنية", "Eiman Ashkanani"),
    ("البترول الوطنيه", "Eiman Ashkanani"),
    ("بترول وطنيه", "Eiman Ashkanani"),
    ("بترول وطنية", "Eiman Ashkanani"),
    ("مؤسسه البترول", "Eiman Ashkanani"),
    ("مؤسسة البترول", "Eiman Ashkanani"),
    ("متكامله", "Eiman Ashkanani"),
    ("متكاملة", "Eiman Ashkanani"),
    ("كيبيك", "Eiman Ashkanani"),
    ("kipic", "Eiman Ashkanani"),
    ("knpc", "Eiman Ashkanani"),
    ("kpc", "Eiman Ashkanani"),
    ("البترول", "Eiman Ashkanani"),
    ("ناقلات", "Wajih Fahad"),
    ("كيماويات", "Wajih Fahad"),
    ("كوفبيك", "Wajih Fahad"),
    ("kufpec", "Wajih Fahad"),
    ("نفط الخليج", "Wajih Fahad"),

    # Public Authorities (Jana Al-Obaid)
    ("تامينات", "Jana Al-Obaid"),
    ("تأمينات", "Jana Al-Obaid"),
    ("pifss", "Jana Al-Obaid"),
    ("دفاع", "Jana Al-Obaid"),
    ("صحه", "Jana Al-Obaid"),
    ("صحة", "Jana Al-Obaid"),
    ("سكنيه", "Jana Al-Obaid"),
    ("سكنية", "Jana Al-Obaid"),
    ("صناعه", "Jana Al-Obaid"),
    ("صناعة", "Jana Al-Obaid"),
    ("تجاره", "Jana Al-Obaid"),
    ("تجارة", "Jana Al-Obaid"),
    ("زراعه", "Jana Al-Obaid"),
    ("زراعة", "Jana Al-Obaid"),
    ("شئون", "Jana Al-Obaid"),
    ("شؤون", "Jana Al-Obaid"),
    ("اوقاف", "Jana Al-Obaid"),
    ("أوقاف", "Jana Al-Obaid"),
    ("تغذيه", "Jana Al-Obaid"),
    ("تغذية", "Jana Al-Obaid"),
    ("اعاقه", "Jana Al-Obaid"),
    ("إعاقة", "Jana Al-Obaid"),

    # Infrastructure & Parliament (Abrar Al-Qallaf)
    ("اشغال", "Abrar Al-Qallaf"),
    ("أشغال", "Abrar Al-Qallaf"),
    ("بلديه", "Abrar Al-Qallaf"),
    ("بلدية", "Abrar Al-Qallaf"),
    ("مجلس الامه", "Abrar Al-Qallaf"),
    ("مجلس الأمة", "Abrar Al-Qallaf"),
    ("تطبيقي", "Abrar Al-Qallaf"),
    ("نزاهه", "Abrar Al-Qallaf"),
    ("نزاهة", "Abrar Al-Qallaf"),

    # Utilities, Fire & Government (Raed Obeid)
    ("اطفاء", "Raed Obeid"),
    ("إطفاء", "Raed Obeid"),
    ("كهرباء", "Raed Obeid"),
    ("ماليه", "Raed Obeid"),
    ("مالية", "Raed Obeid"),
    ("عدل", "Raed Obeid"),
    ("تربيه", "Raed Obeid"),
    ("تربية", "Raed Obeid"),
    ("جامعه", "Raed Obeid"),
    ("جامعة", "Raed Obeid"),
    ("مدنيه", "Raed Obeid"),
    ("مدنية", "Raed Obeid"),
    ("جمارك", "Raed Obeid"),
    ("طيران مدني", "Raed Obeid"),
    ("سيبراني", "Raed Obeid"),
    ("فتوى", "Raed Obeid"),

    # Research (Eiman Ashkanani)
    ("ابحاث", "Eiman Ashkanani"),
    ("أبحاث", "Eiman Ashkanani"),
    ("تقدم علمي", "Eiman Ashkanani"),

    # Banking & Finance
    ("بنك الكويت الوطني", "Ahmad Abu Jrab"),
    ("البنك الوطني", "Ahmad Abu Jrab"),
    ("nbk", "Ahmad Abu Jrab"),
    ("بيت التمويل", "Ahmad Abu Jrab"),
    ("kfh", "Ahmad Abu Jrab"),
    ("بيتك", "Ahmad Abu Jrab"),
    ("اهلي", "Saleem Dalwai"),
    ("أهلي", "Saleem Dalwai"),
    ("تجاري", "Saleem Dalwai"),
    ("برقان", "Saleem Dalwai"),
    ("استثمار", "Saleem Dalwai"),
    ("وربه", "Usama Badra"),
    ("وربة", "Usama Badra"),
    ("دولي", "Usama Badra"),
    ("كي نت", "Usama Badra"),

    # Telecom & Media
    ("اعلام", "Ehtisham Boota"),
    ("إعلام", "Ehtisham Boota"),
    ("مواصلات", "Ehtisham Boota"),
    ("سيترا", "Ehtisham Boota"),
    ("citra", "Ehtisham Boota"),
    ("زين", "Ehtisham Boota"),
    ("اوريدو", "Tariq Al-Souqi"),
    ("أوريدو", "Tariq Al-Souqi")
]

def resolve_account_manager(client_name: Optional[str], client_id: Optional[str] = "") -> Optional[str]:
    """
    Resolves the official KBM Account Manager for any client name or ID.
    Returns canonical Account Manager name or None if unassigned.
    """
    if not client_name or client_name.strip() in ("", "غير محدد", "None"):
        return None

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

    return None
