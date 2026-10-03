"""
KBM Tender Scout - Account Owner Synchronizer
Maps KBM Account Managers from the official Technology Pipeline Review workbook:
'2026-Q3-28th-Sep-Tech Pipeline Review-ver1.1.xlsx'
into data/clients.csv and provides fuzzy resolution for tender clients.
"""

import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Canonical Account Manager Name normalization
AM_NORMALIZATION = {
    "RAED OBEID": "Raed Obeid",
    "JANA ALOBAID": "Jana Al-Obaid",
    "Jana": "Jana Al-Obaid",
    "FAHAD ALROUMI": "Fahad Al-Roumi",
    "ABRAR AlQALLAF": "Abrar Al-Qallaf",
    "ABRAR QALAF": "Abrar Al-Qallaf",
    "MOHAMMAD GHALOUM": "Mohammad Ghaloum",
    "WAJIH FAHAD": "Wajih Fahad",
    "AHMAD ABUJRAB": "Ahmad Abu Jrab",
    "Ahmed Abujurab": "Ahmad Abu Jrab",
    "Abu Jrab": "Ahmad Abu Jrab",
    "Abu Grab": "Ahmad Abu Jrab",
    "SALEEM DALWAI": "Saleem Dalwai",
    "EHTISHAM BOOTA": "Ehtisham Boota",
    "Ehtisham Boota": "Ehtisham Boota",
    "Ethisham": "Ehtisham Boota",
    "TARIQ AL SOUQI": "Tariq Al-Souqi",
    "Tareq Al Souqi": "Tariq Al-Souqi",
    "USAMA BADRA": "Usama Badra",
    "Usama Badra": "Usama Badra",
    "EIMAN ASHKANANI": "Eiman Ashkanani",
    "AHMED ISMAIL": "Ahmed Ismail",
    "Ahmed": "Ahmed Ismail",
    "SAAD ALMAZROUEI": "Saad Al-Mazrouei",
    "Oumayma": "Oumayma",
    "Omayma": "Oumayma",
    "Oumaima": "Oumayma",
    "ABDULMUNIM ABDULSALAM": "Abdulmunim Abdulsalam"
}

# Direct Mapping from Client ID / Aliases to Account Manager
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

    "kpc": "Mohammad Ghaloum",       # KPC - Kuwait Petroleum Corporation
    "knpc": "Mohammad Ghaloum",      # KNPC - Kuwait National Petroleum Company
    "kipic": "Mohammad Ghaloum",     # KIPIC - Petrochemical Industries

    "koc": "Ahmed Ismail",           # KOC - Kuwait Oil Company

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

# Arabic substring keywords for automatic resolution
ARABIC_KEYWORD_TO_AM = [
    ("إطفاء", "Raed Obeid"),
    ("اطفاء", "Raed Obeid"),
    ("كهرباء", "Raed Obeid"),
    ("مالية", "Raed Obeid"),
    ("ماليه", "Raed Obeid"),
    ("عدل", "Raed Obeid"),
    ("تربية", "Raed Obeid"),
    ("تربيه", "Raed Obeid"),
    ("تعليم عالي", "Raed Obeid"),
    ("جامعة الكويت", "Raed Obeid"),
    ("جامعة عبدالله السالم", "Raed Obeid"),
    ("معلومات مدنية", "Raed Obeid"),
    ("جمارك", "Raed Obeid"),
    ("طيران مدني", "Raed Obeid"),
    ("خدمة مدنية", "Raed Obeid"),
    ("سيبراني", "Raed Obeid"),
    ("فتوى وتشريع", "Raed Obeid"),

    ("داخلية", "Fahad Al-Roumi"),
    ("داخليه", "Fahad Al-Roumi"),
    ("حرس وطني", "Fahad Al-Roumi"),

    ("تأمينات", "Jana Al-Obaid"),
    ("تامينات", "Jana Al-Obaid"),
    ("دفاع", "Jana Al-Obaid"),
    ("صحة", "Jana Al-Obaid"),
    ("صحه", "Jana Al-Obaid"),
    ("رعاية سكنية", "Jana Al-Obaid"),
    ("سكنية", "Jana Al-Obaid"),
    ("صناعة", "Jana Al-Obaid"),
    ("صناعه", "Jana Al-Obaid"),
    ("تجارة", "Jana Al-Obaid"),
    ("تجاره", "Jana Al-Obaid"),
    ("زراعة", "Jana Al-Obaid"),
    ("زراعه", "Jana Al-Obaid"),
    ("شئون اجتماعية", "Jana Al-Obaid"),
    ("شؤون اجتماعية", "Jana Al-Obaid"),
    ("أوقاف", "Jana Al-Obaid"),
    ("غذاء وتغذية", "Jana Al-Obaid"),
    ("إعاقة", "Jana Al-Obaid"),

    ("أشغال", "Abrar Al-Qallaf"),
    ("اشغال", "Abrar Al-Qallaf"),
    ("بلدية", "Abrar Al-Qallaf"),
    ("بلديه", "Abrar Al-Qallaf"),
    ("مجلس أمة", "Abrar Al-Qallaf"),
    ("مجلس الامة", "Abrar Al-Qallaf"),
    ("تطبيقي", "Abrar Al-Qallaf"),
    ("نزاهة", "Abrar Al-Qallaf"),
    ("مكافحة الفساد", "Abrar Al-Qallaf"),

    ("نفط الكويت", "Ahmed Ismail"),
    ("koc", "Ahmed Ismail"),

    ("بترول وطنية", "Mohammad Ghaloum"),
    ("مؤسسة البترول", "Mohammad Ghaloum"),
    ("صناعات بترولية متكاملة", "Mohammad Ghaloum"),
    ("كيبيك", "Mohammad Ghaloum"),
    ("knpc", "Mohammad Ghaloum"),
    ("kpc", "Mohammad Ghaloum"),
    ("kipic", "Mohammad Ghaloum"),

    ("ناقلات", "Wajih Fahad"),
    ("كيماويات", "Wajih Fahad"),
    ("استكشافات بترولية", "Wajih Fahad"),
    ("كوفبيك", "Wajih Fahad"),
    ("نفط الخليج", "Wajih Fahad"),

    ("أبحاث", "Eiman Ashkanani"),
    ("تقدم علمي", "Eiman Ashkanani"),

    ("وطني", "Ahmad Abu Jrab"),
    ("تمويل كويتي", "Ahmad Abu Jrab"),
    ("بيتك", "Ahmad Abu Jrab"),

    ("أهلي كويتي", "Saleem Dalwai"),
    ("تجاري كويتي", "Saleem Dalwai"),
    ("برقان", "Saleem Dalwai"),
    ("بنك مركزي", "Saleem Dalwai"),
    ("هيئة الاستثمار", "Saleem Dalwai"),

    ("وربة", "Usama Badra"),
    ("دولي", "Usama Badra"),
    ("كي نت", "Usama Badra"),

    ("إعلام", "Ehtisham Boota"),
    ("اعلام", "Ehtisham Boota"),
    ("مواصلات", "Ehtisham Boota"),
    ("اتصالات وتقنية", "Ehtisham Boota"),
    ("سيترا", "Ehtisham Boota"),
    ("زين", "Ehtisham Boota"),
    ("أوريدو", "Tariq Al-Souqi")
]

def resolve_account_manager(client_name: str, client_id: str = "") -> str:
    """Intelligently resolves Account Manager for any given client name."""
    if not client_name:
        return "Unassigned"
    
    # Check client_id direct match
    if client_id and client_id.lower() in CLIENT_ID_TO_AM:
        return CLIENT_ID_TO_AM[client_id.lower()]

    name_lower = client_name.lower().strip()

    # Direct keyword matches
    for kw, am in ARABIC_KEYWORD_TO_AM:
        if kw in name_lower:
            return am

    return "Unassigned"

def update_clients_csv():
    csv_path = PROJECT_ROOT / "data" / "clients.csv"
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        return

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for r in reader:
            cid = r.get("client_id", "").strip()
            cname = r.get("client_name_ar", "").strip()
            
            # Resolve AM
            am = resolve_account_manager(cname, cid)
            if am != "Unassigned":
                r["account_owner"] = am
            elif not r.get("account_owner"):
                r["account_owner"] = "Unassigned"
            
            rows.append(r)

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Successfully updated {len(rows)} clients in data/clients.csv with official KBM Account Managers!")

if __name__ == "__main__":
    update_clients_csv()
