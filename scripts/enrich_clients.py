import csv
import re
from pathlib import Path

# Load existing clients
existing_clients = []
existing_names = set()
clients_csv_path = Path("data/clients.csv")

if clients_csv_path.exists():
    with open(clients_csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            existing_clients.append(r)
            existing_names.add(r["client_name_ar"].strip())

# Entities discovered from CAPT and Al-Yawm official dropdowns
discovered = [
    ("إدارة الفتوى والتشريع", "Fatwa and Legislation Department", "government", "الفتوى والتشريع"),
    ("إدارة نزع الملكية للمنفعة العامة", "Expropriation Public Benefit Department", "government", "نزع الملكية"),
    ("الإدارة العامة للإطفاء", "General Fire Force", "defense_and_security", "الإدارة العامة للاطفاء;قوة الإطفاء;قوة الاطفاء العام"),
    ("الإدارة العامة للجمارك", "General Administration of Customs", "government", "الجمارك;جمارك الكويت"),
    ("الإدارة المركزية للإحصاء", "Central Statistical Bureau", "government", "المركزية للإحصاء;الإحصاء"),
    ("الأمانة العامة للأوقاف", "General Secretariat of Awqaf", "government", "أمانة الأوقاف;الأوقاف"),
    ("الادارة العامة للطيران المدني", "Directorate General of Civil Aviation", "government", "الطيران المدني;DGCA"),
    ("الجهاز الفني لدراسة المشروعات التنموية والمبادرات", "Partnerships Technical Bureau", "government", "المشروعات التنموية;PTB"),
    ("الجهاز المركزي لتكنولوجيا المعلومات", "Central Agency for Information Technology", "government", "تكنولوجيا المعلومات;CAIT"),
    ("الجهاز المركزي للمناقصات العامة", "Central Agency for Public Tenders", "government", "المناقصات العامة;الجهاز المركزي;CAPT;CTC"),
    ("الجهاز الوطني للاعتماد الأكاديمي وضمان جودة التعليم", "National Bureau for Academic Accreditation", "education_and_research", "الاعتماد الأكاديمي;NBAQ"),
    ("الديوان الأميري", "Amiri Diwan", "government", "الديوان الاميري"),
    ("الديوان الوطني لحقوق الإنسان", "National Bureau for Human Rights", "government", "حقوق الانسان"),
    ("الرئاسة العامة للحرس الوطني", "Kuwait National Guard", "defense_and_security", "الحرس الوطني;KNG"),
    ("الشركة الكويتية لتزويد الطائرات بالوقود", "Kuwait Aviation Fuelling Company", "oil_and_gas", "كافكو;KAFCO"),
    ("الشركة الكويتية لخدمات الطيران", "Kuwait Aviation Services Company", "government", "كاسكو;KASCO"),
    ("الشركة الكويتية للاستثمار", "Kuwait Investment Company", "banking_and_finance", "الكويتية للاستثمار;KIC"),
    ("الشركة الكويتية للاستكشافات البترولية الخارجية", "Kuwait Foreign Petroleum Exploration Company", "oil_and_gas", "كوفبيك;KUFPEC"),
    ("الشركة الكويتية للتموين", "Kuwait Supply Company", "government", "التموين"),
    ("الشركة الكويتية للصناعات البترولية المتكاملة", "Kuwait Integrated Petroleum Industries Company", "oil_and_gas", "كيبيك;KIPIC"),
    ("الشركة الكويتية لنفط الخليج", "Kuwait Gulf Oil Company", "oil_and_gas", "نفط الخليج;KGOC"),
    ("الشركة الوطنية لمشاريع التكنولوجيا", "National Technology Enterprises Company", "telecom_and_media", "مشاريع التكنولوجيا;NTEC"),
    ("الصندوق الكويتي للتنمية الاقتصادية العربية", "Kuwait Fund for Arab Economic Development", "banking_and_finance", "الصندوق الكويتي;KFAED"),
    ("الصندوق الوطني لرعاية وتنمية المشروعات الصغيرة والمتوسطة", "National Fund for SME Development", "government", "المشروعات الصغيرة;SME Fund"),
    ("المؤسسة العامة للتأمينات الاجتماعية", "The Public Institution for Social Security", "banking_and_finance", "التأمينات الاجتماعية;التأمينات;PIFSS"),
    ("المؤسسة العامة للرعاية السكنية", "Public Authority for Housing Welfare", "government", "الرعاية السكنية;السكنية;PAHW"),
    ("الهيئة العامة للاتصالات وتقنية المعلومات", "Communication and Information Technology Regulatory Authority", "telecom_and_media", "هيئة الاتصالات;الاتصالات;CITRA"),
    ("الهيئة العامة للاستثمار", "Kuwait Investment Authority", "banking_and_finance", "هيئة الاستثمار;KIA"),
    ("الهيئة العامة للبيئة", "Environment Public Authority", "government", "هيئة البيئة;البيئة;EPA"),
    ("الهيئة العامة للتعليم التطبيقي والتدريب", "Public Authority for Applied Education and Training", "education_and_research", "التعليم التطبيقي;التطبيقي;PAAET"),
    ("الهيئة العامة للرياضة", "Public Authority for Sport", "government", "هيئة الرياضة;الرياضة;PAS"),
    ("الهيئة العامة للشباب", "Public Authority for Youth", "government", "هيئة الشباب;الشباب"),
    ("الهيئة العامة للصناعة", "Public Authority for Industry", "government", "هيئة الصناعة;الصناعة;PAI"),
    ("الهيئة العامة للطرق والنقل البري", "Public Authority for Roads and Transportation", "government", "هيئة الطرق;PART"),
    ("الهيئة العامة للغذاء والتغذية", "Public Authority for Food and Nutrition", "healthcare", "الغذاء والتغذية;PAFN"),
    ("الهيئة العامة للقوى العاملة", "Public Authority of Manpower", "government", "القوى العاملة;PAM"),
    ("الهيئة العامة للمعلومات المدنية", "Public Authority for Civil Information", "government", "المعلومات المدنية;المدنية;PACI"),
    ("الهيئة العامة لمكافحة الفساد (نزاهة)", "Kuwait Anti-Corruption Authority", "government", "نزاهة;مكافحة الفساد;NAZAHA"),
    ("بلدية الكويت", "Kuwait Municipality", "government", "البلدية;بلدية الكويت"),
    ("بنك الائتمان الكويتي", "Kuwait Credit Bank", "banking_and_finance", "بنك الائتمان;الائتمان;KCB"),
    ("بنك الكويت المركزي", "Central Bank of Kuwait", "banking_and_finance", "البنك المركزي;المركزي;CBK"),
    ("بيت الزكاة", "Zakat House", "government", "بيت الزكاة"),
    ("جامعة الكويت", "Kuwait University", "education_and_research", "جامعة الكويت;KU"),
    ("جامعة عبدالله السالم", "Abdullah Al-Salem University", "education_and_research", "جامعة عبدالله السالم;AASU"),
    ("ديوان الخدمة المدنية", "Civil Service Commission", "government", "الخدمة المدنية;CSC"),
    ("ديوان المحاسبة", "State Audit Bureau", "government", "ديوان المحاسبة;المحاسبة;SAB"),
    ("شركة البترول الوطنية الكويتية", "Kuwait National Petroleum Company", "oil_and_gas", "البترول الوطنية;KNPC"),
    ("شركة الخطوط الجوية الكويتية", "Kuwait Airways", "government", "الكويتية;الخطوط الجوية;KAC"),
    ("شركة المشروعات السياحية", "Touristic Enterprises Company", "government", "المشروعات السياحية;TEC"),
    ("شركة النقل العام الكويتية", "Kuwait Public Transport Company", "government", "النقل العام;KPTC"),
    ("شركة نفط الكويت", "Kuwait Oil Company", "oil_and_gas", "نفط الكويت;KOC"),
    ("مؤسسة البترول الكويتية", "Kuwait Petroleum Corporation", "oil_and_gas", "مؤسسة البترول;KPC"),
    ("مؤسسة الكويت للتقدم العلمي", "Kuwait Foundation for the Advancement of Sciences", "education_and_research", "مؤسسة التقدم العلمي;KFAS"),
    ("مؤسسة الموانئ الكويتية", "Kuwait Ports Authority", "government", "الموانئ الكويتية;مؤسسة الموانئ;KPA"),
    ("معهد الكويت للأبحاث العلمية", "Kuwait Institute for Scientific Research", "education_and_research", "معهد الأبحاث;KISR"),
    ("هيئة أسواق المال", "Capital Markets Authority", "banking_and_finance", "أسواق المال;CMA"),
    ("هيئة تشجيع الاستثمار المباشر", "Kuwait Direct Investment Promotion Authority", "government", "تشجيع الاستثمار;KDIPA"),
    ("هيئة مشروعات الشراكة بين القطاعين العام والخاص", "Kuwait Authority for Partnership Projects", "government", "مشروعات الشراكة;KAPP"),
    ("وزارة الأشغال العامة", "Ministry of Public Works", "government", "الأشغال العامة;الأشغال;MPW"),
    ("وزارة الأوقاف والشئون الإسلامية", "Ministry of Awqaf and Islamic Affairs", "government", "الأوقاف والشئون الإسلامية;وزارة الأوقاف;الأوقاف"),
    ("وزارة الاعلام", "Ministry of Information", "telecom_and_media", "وزارة الإعلام;الإعلام;MOI Media"),
    ("وزارة التجارة والصناعة", "Ministry of Commerce and Industry", "government", "التجارة والصناعة;التجارة;MOCI"),
    ("وزارة التربية", "Ministry of Education", "education_and_research", "وزارة التربية;التربية;MOE"),
    ("وزارة التعليم العالي", "Ministry of Higher Education", "education_and_research", "وزارة التعليم العالي;التعليم العالي;MOHE"),
    ("وزارة الخارجية", "Ministry of Foreign Affairs", "government", "وزارة الخارجية;الخارجية;MOFA"),
    ("وزارة الداخلية", "Ministry of Interior", "defense_and_security", "وزارة الداخلية;الداخلية;MOI"),
    ("وزارة الدفاع", "Ministry of Defense", "defense_and_security", "وزارة الدفاع;الدفاع;MOD"),
    ("وزارة الدولة لشئون الاتصالات وتكنولوجيا المعلومات", "Minister of State for Communications and IT", "telecom_and_media", "شئون الاتصالات;تكنولوجيا المعلومات"),
    ("وزارة الدولة لشئون البلدية", "Minister of State for Municipal Affairs", "government", "شئون البلدية"),
    ("وزارة الشئون الاجتماعية", "Ministry of Social Affairs", "government", "الشئون الاجتماعية;الشئون;MOSA"),
    ("وزارة الصحة", "Ministry of Health", "healthcare", "وزارة الصحة;الصحة;MOH"),
    ("وزارة العدل", "Ministry of Justice", "government", "وزارة العدل;العدل;MOJ"),
    ("وزارة الكهرباء والماء والطاقة المتجددة", "Ministry of Electricity, Water and Renewable Energy", "oil_and_gas", "الكهرباء والماء;وزارة الكهرباء;MEW"),
    ("وزارة المالية", "Ministry of Finance", "government", "وزارة المالية;المالية;MOF"),
    ("وزارة المواصلات", "Ministry of Communications", "telecom_and_media", "وزارة المواصلات;المواصلات;MOC"),
    ("وزارة النفط", "Ministry of Oil", "oil_and_gas", "وزارة النفط;النفط;MOO")
]

new_rows = []
for name_ar, name_en, sector, aliases in discovered:
    # generate a short client id
    clean_id = re.sub(r'[^a-zA-Z0-9]', '', name_en.split()[0].lower()) + "_" + str(len(new_rows) + 1)
    
    # check if already in existing
    matched = False
    for ex in existing_clients:
        if ex["client_name_ar"].strip() == name_ar.strip():
            matched = True
            break
    if not matched:
        new_rows.append({
            "client_id": clean_id,
            "client_name_ar": name_ar,
            "client_name_en": name_en,
            "aliases": aliases,
            "sector_id": sector,
            "account_owner": "",
            "notes": "Verified from portal discovery"
        })

fieldnames = ["client_id", "client_name_ar", "client_name_en", "aliases", "sector_id", "account_owner", "notes"]
all_clients = existing_clients + new_rows

with open(clients_csv_path, mode="w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_clients)

print(f"Updated data/clients.csv with {len(all_clients)} total verified entities.")
