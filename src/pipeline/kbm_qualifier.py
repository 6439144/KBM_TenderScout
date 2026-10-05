"""
KBM Tender Qualification & Relevance Engine.
Derived directly from KBM Company Profile (KBM_Company_Profile_3.pptx).
Evaluates Kuwait public tenders against KBM's 5 Business Units, Vendor Ecosystem,
and Strategic Target Accounts to compute a presales Fit Score (0-100%) and BU routing.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from src.pipeline.normalizer import normalize_arabic_text

# ==============================================================================
# 1. KBM BUSINESS UNITS ONTOLOGY
# ==============================================================================
KBM_BUSINESS_UNITS = {
    "IBM BU - Systems": {
        "label_ar": "قطاع أنظمة IBM للأجهزة والخوادم",
        "description": "IBM Power, Storage (FlashSystem), IBM Z, LinuxONE, Data Center Sizing, Migration, HW Maintenance",
        "keywords_ar": [
            "خوادم", "أجهزة خوادم", "أجهزة الخوادم", "أنظمة التخزين", "وحدات التخزين", "مصفوفات التخزين",
            "الأجهزة الرئيسية", "مينفريم", "باور", "سيرفرات", "سيرفر", "تخزين البيانات",
            "بنية تحتية للأجهزة", "كمبيوتر مركزي", "أشرطة النسخ الاحتياطي", "سان ستورج"
        ],
        "keywords_en": [
            "ibm power", "aix", "as400", "storage", "flashsystem", "ibm z", "mainframe",
            "linuxone", "san", "storage area network", "tape library", "server sizing",
            "server hardware", "compute", "storage migration", "high availability", "powervm", "powerha"
        ],
        "weight": 35
    },
    "IBM BU - Solutions & Channel": {
        "label_ar": "قطاع برمجيات IBM وحلول الذكاء الاصطناعي وRed Hat",
        "description": "IBM Software, watsonx AI, Red Hat (OpenShift, RHEL, Ansible), Cloud Paks, Integration, Automation",
        "keywords_ar": [
            "برمجيات", "برامج", "ذكاء اصطناعي", "أتمتة", "ريد هات", "أوبن شيفت", "إدارة البيانات",
            "حوكمة البيانات", "تكامل الأنظمة", "وسطاء البرمجيات", "تراخيص البرمجيات", "تحليلات البيانات",
            "قواعد البيانات", "تطوير تطبيقات", "منصة رقمية", "أنظمة الكترونية", "بوابة الكترونية",
            "واجهة برمجة التطبيقات", "أرشفة الكترونية", "إدارة الوثائق"
        ],
        "keywords_en": [
            "ibm software", "watsonx", "watson", "red hat", "openshift", "rhel", "ansible",
            "cloud paks", "integration", "api connect", "mq", "message queue", "datapower",
            "app connect", "mdm", "master data management", "governance", "data fabric",
            "automation", "db2", "filenet", "cognos", "spss", "ela", "license", "ai", "artificial intelligence"
        ],
        "weight": 35
    },
    "Cloud BU": {
        "label_ar": "قطاع الحوسبة السحابية والتحديث الرقمي",
        "description": "Microsoft Azure Landing Zones, Hybrid/Public Cloud, Migration, Modernization, VMware, Nutanix HCI",
        "keywords_ar": [
            "سحابية", "الحوسبة السحابية", "السحابة الهجينة", "مايكروسوفت أزور", "الافتراضية",
            "محاكاة افتراضية", "تحديث الأنظمة", "ترحيل السحابة", "بنية سحابية", "خوادم افتراضية",
            "حاويات رقمية", "ميكروسيرفسز"
        ],
        "keywords_en": [
            "azure", "microsoft azure", "landing zones", "cloud migration", "modernization",
            "hybrid cloud", "public cloud", "private cloud", "iaas", "paas", "saas",
            "vmware", "vsphere", "nutanix", "hyperconverged", "hci", "virtualization",
            "containerization", "kubernetes", "microservices", "devops", "office 365", "m365"
        ],
        "weight": 35
    },
    "Security BU": {
        "label_ar": "قطاع الأمن السيبراني والدفاع الرقمي",
        "description": "Enterprise Cyber Defence, SOC/SIEM, Palo Alto, Fortinet, F5, EDR/XDR, GRC, Firewalls, Threat Detection",
        "keywords_ar": [
            "أمن سيبراني", "الأمن السيبراني", "أمن المعلومات", "جدران نارية", "جدار ناري",
            "مركز العمليات الأمنية", "مكافحة الفيروسات", "حماية البيانات", "اختبار الاختراق",
            "إدارة الهوية والوصول", "الاستجابة للحوادث", "تشفير", "حماية الشبكات", "أمن الاتصالات",
            "مراقبة أمنية", "تقييم الثغرات", "حماية النقاط الطرفية"
        ],
        "keywords_en": [
            "cybersecurity", "cyber defence", "soc", "security operations center", "siem",
            "qradar", "firewall", "ngfw", "palo alto", "fortinet", "fortigate", "f5",
            "f5 networks", "big-ip", "waf", "edr", "xdr", "antivirus", "dlp", "zero trust",
            "grc", "penetration testing", "vulnerability assessment", "iam", "pam",
            "threat detection", "incident response", "ddos"
        ],
        "weight": 40
    },
    "Services BU (MOPS)": {
        "label_ar": "قطاع العمليات المدارة والدعم الفني متعدد الموردين",
        "description": "Managed Operations, Multivendor Support, 24x7 SLA, Disaster Recovery, Networking, Cabling, Data Center",
        "keywords_ar": [
            "عقد صيانة", "اتفاقية مستوى الخدمة", "تشغيل وصيانة", "صيانة أجهزة", "صيانة برمجيات",
            "صيانة أنظمة", "صيانة شبكات", "الدعم الفني", "خدمات مدارة", "استمرارية الأعمال", "التعافي من الكوارث", "توريد عمالة فنية",
            "كوادر متخصصة", "شبكات", "تمديدات شبكية", "أجهزة توجيه", "بدالات", "مركز البيانات",
            "مغذي طاقة غير منقطع", "يو بي إس", "ألياف ضوئية", "أجهزة اتصالات", "أجهزة الاتصالات", "أنظمة الاتصالات", "اتصالات لاسلكية", "اتصالات"
        ],
        "keywords_en": [
            "managed services", "managed operations", "professional services", "sla",
            "annual maintenance", "hardware maintenance", "software support", "multivendor support",
            "disaster recovery", "business continuity", "dr site", "it outsourcing",
            "technical support", "helpdesk", "it manpower", "cabling", "structured cabling",
            "ups", "datacenter facilities", "rack", "cooling", "switching", "routing",
            "cisco", "lan", "wan", "sd-wan", "network", "telecom"
        ],
        "weight": 30
    }
}

# ==============================================================================
# 2. STRATEGIC VENDOR ALLIANCES
# ==============================================================================
KBM_VENDOR_ALLIANCES = {
    "IBM": ["ibm", "آي بي إم", "اي بي ام"],
    "Red Hat": ["red hat", "redhat", "ريد هات", "انسيبل", "ansible", "openshift"],
    "Microsoft": ["microsoft", "مايكروسوفت", "azure", "أزور", "m365", "office 365"],
    "Cisco": ["cisco", "سيسكو"],
    "Palo Alto": ["palo alto", "بالو التو", "paloalto"],
    "Fortinet": ["fortinet", "فورتينت", "fortigate"],
    "F5": ["f5", "f5 networks", "اف فايف"],
    "VMware": ["vmware", "فيموير"],
    "Nutanix": ["nutanix", "نيوتانيكس"],
    "Pure Storage": ["pure storage", "بيور ستورج"],
    "Oracle": ["oracle", "أوراكل", "اوراكل"],
    "SAP": ["sap", "ساب"],
    "Dell": ["dell", "ديل", "emc"],
    "HCL Software": ["hcl", "اتش سي ال"]
}

# Strategic enterprise clients highlighted in Slide 5 of KBM Profile and Technology Forecast
KBM_TARGET_CLIENTS = [
    "وزارة الدفاع", "وزارة الصحة", "وزارة التربية", "وزارة الكهرباء والماء", "وزارة الأشغال العامة",
    "الرئاسة العامة للحرس الوطني", "الإدارة العامة للإطفاء", "وزارة الداخلية",
    "وزارة العدل", "الهيئة العامة للمعلومات المدنية", "المؤسسة العامة للتأمينات الاجتماعية",
    "مجلس الأمة", "شركة نفط الكويت", "شركة البترول الوطنية الكويتية", "الشركة الكويتية للصناعات البترولية المتكاملة",
    "شركة صناعة الكيماويات البترولية", "بنك الكويت الوطني", "بيت التمويل الكويتي", "بنك بوبيان",
    "بنك الخليج", "البنك التجاري الكويتي", "بنك برقان", "بنك وربة", "الشركة الكويتية للمقاصة",
    "وزارة المالية", "وزارة التجارة والصناعة", "جامعة الكويت", "جامعة عبدالله السالم"
]

# Negative non-IT scope keywords that penalize or disqualify fit
NON_IT_DISQUALIFIERS = [
    "نظافة", "تنظيف", "أغذية", "إطعام", "وجبات", "حراسة وأمن", "حراسة بشرية", "أمن وحراسة",
    "زراعة", "تشجير", "حديقة الحيوان", "حفاظات", "أدوية", "مستلزمات طبية",
    "سيارات", "مركبات", "استئجار حافلات", "خرسانة", "أعمال مدنية", "إنشاء مباني",
    "صيانة مصاعد", "مكافحة حشرات", "هدم", "ترميم أسوار"
]

def _contains_word_or_phrase(pattern: str, text: str) -> bool:
    """Checks if a keyword or phrase appears as a distinct word/phrase in text."""
    p_norm = normalize_arabic_text(pattern.strip().lower())
    t_norm = normalize_arabic_text(text.strip().lower())
    if len(p_norm) <= 3:
        # Require word boundary
        return bool(re.search(rf"(?:^|\s){re.escape(p_norm)}(?:\s|$)", t_norm))
    return p_norm in t_norm


class KBMQualifier:
    """Evaluates Kuwait tenders against KBM's corporate capabilities and presales criteria."""

    @classmethod
    def evaluate_tender(cls, title: str, client: str = "", extra_text: str = "") -> Dict[str, Any]:
        """
        Computes the fit score, identifies matching Business Units, partners,
        and provides presales recommendation.
        """
        combined = f"{title} {client} {extra_text}".lower()
        combined_norm = normalize_arabic_text(combined)

        # 1. Check for disqualifying non-IT patterns
        negative_hits = []
        for kw in NON_IT_DISQUALIFIERS:
            if _contains_word_or_phrase(kw, combined):
                negative_hits.append(kw)

        # 2. Check vendor partner mentions
        matched_vendors = []
        for vendor, patterns in KBM_VENDOR_ALLIANCES.items():
            for p in patterns:
                if _contains_word_or_phrase(p, combined):
                    matched_vendors.append(vendor)
                    break

        # 3. Evaluate each Business Unit
        bu_scores = {}
        bu_hits = {}
        for bu_name, bu_info in KBM_BUSINESS_UNITS.items():
            hits = []
            # Arabic check
            for kw in bu_info["keywords_ar"]:
                if _contains_word_or_phrase(kw, combined):
                    hits.append(kw)
            # English check
            for kw in bu_info["keywords_en"]:
                if _contains_word_or_phrase(kw, combined):
                    hits.append(kw)

            if hits:
                bu_hits[bu_name] = hits
                bu_scores[bu_name] = len(hits) * bu_info["weight"]

        # Determine Primary Business Unit
        primary_bu = None
        max_bu_score = 0
        if bu_scores:
            primary_bu = max(bu_scores.items(), key=lambda x: x[1])[0]
            max_bu_score = bu_scores[primary_bu]

        # 4. Check client affinity
        is_strategic_client = any(normalize_arabic_text(tc) in combined_norm for tc in KBM_TARGET_CLIENTS)

        # 5. Calculate Composite Fit Score (0 to 100)
        score = 0.0
        rationale_items = []

        if matched_vendors:
            score += min(len(matched_vendors) * 35.0, 50.0)
            rationale_items.append(f"Matching KBM Vendor Partners: {', '.join(matched_vendors)}")

        if max_bu_score > 0:
            score += min(max_bu_score * 0.8, 45.0)
            rationale_items.append(f"Aligned with {primary_bu} ({len(bu_hits.get(primary_bu, []))} capability matches)")

        # Check if matched BU keyword is in the tender title itself
        has_title_bu_match = False
        if primary_bu and bu_hits.get(primary_bu):
            for kw in bu_hits[primary_bu]:
                if _contains_word_or_phrase(kw, title):
                    has_title_bu_match = True
                    break

        if has_title_bu_match:
            score += 25.0
            rationale_items.append("Core ICT Scope in Tender Title")

        if is_strategic_client:
            score += 15.0
            rationale_items.append("Strategic KBM Account Relationship")

        # Apply penalty if non-IT disqualifiers exist
        if negative_hits:
            if not matched_vendors and not any(k in ["أمن سيبراني", "شبكات", "خوادم", "برمجيات"] for k in bu_hits.get(primary_bu, [])):
                score = max(0.0, score - 60.0)
                rationale_items.append(f"Non-ICT scope markers: {', '.join(negative_hits[:3])}")
            else:
                # Partial non-IT (e.g. facility management that includes network/cabling)
                score = max(10.0, score - 25.0)

        # Cap score between 0 and 100
        final_score = round(min(max(score, 0.0), 100.0), 1)

        # Presales Recommendation Verdict
        if final_score >= 75.0:
            verdict = "HIGH_PRIORITY_BID"
            verdict_ar = "فرصة استراتيجية رئيسية (موصى بالتقديم)"
        elif final_score >= 50.0:
            verdict = "TARGET_OPPORTUNITY"
            verdict_ar = "فرصة ICT متوافقة مع قدرات KBM"
        elif final_score >= 30.0:
            verdict = "PARTNER_OPPORTUNITY"
            verdict_ar = "فرصة تتطلب شراكة أو دراسة نطاق"
        else:
            verdict = "UNRELATED"
            verdict_ar = "غير متوافقة مع اختصاصات KBM"

        all_keywords = []
        for kw_list in bu_hits.values():
            all_keywords.extend(kw_list)

        return {
            "fit_score": final_score,
            "is_kbm_relevant": final_score >= 50.0,
            "primary_bu": primary_bu if final_score >= 30.0 else "None",
            "primary_bu_ar": KBM_BUSINESS_UNITS[primary_bu]["label_ar"] if primary_bu and final_score >= 30.0 else "غير محدد",
            "matched_vendors": matched_vendors,
            "matched_keywords": list(set(all_keywords)),
            "presales_verdict": verdict,
            "presales_verdict_ar": verdict_ar,
            "is_strategic_client": is_strategic_client,
            "rationale": " | ".join(rationale_items) if rationale_items else "No direct KBM capability match"
        }
