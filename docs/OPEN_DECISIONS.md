# Open Decisions Questionnaire (Milestone 0)

**Project:** KBM Tender Monitoring Agent (Phase 1)  
**Product Owner:** Khaled Abed, Digital Solutions Lead, Khorafi Business Machines (KBM), Kuwait  
**Date:** October 2026  
**Status:** ⛔ Human Checkpoint — Pending Owner Approval  

---

## Overview

In accordance with Section 0 and Section 9 of the Build Brief:
- **Do not assume:** All open architectural, functional, and policy decisions are cataloged here with proposed defaults and mapped directly to named keys in `config/config.example.yaml`.
- **Zero hardcoding:** No connector code will be written until Milestone 1 (Recon) produces an approved `PORTAL_MAP.md`, and no assumptions will be baked into code.
- **Human Checkpoints:** This document forms **Milestone 0**. The Lead Orchestrator stops and presents these 18 decisions to the Product Owner for confirmation or adjustment.

---

## Decision Matrix & Proposed Defaults

| # | Decision Topic | Config Key | Proposed Default | Owner Status |
|---|---|---|---|:---:|
| 1 | Automated retrieval compliance | `compliance.automation_permitted` | `false` (until written confirmation in `docs/COMPLIANCE.md`) | ⏳ Pending |
| 2 | OTP/2FA & Dedicated Account | `portals.*.auth` | Phase 1 dev: Shared env vars; Prod: Dedicated agent service account | ⏳ Pending |
| 3 | Notice types to collect | `collect.notice_types` | `["tender", "practice", "prequal", "addendum", "cancellation", "award"]` | ⏳ Pending |
| 4 | Relevance filtering (IT/ICT vs All) | `filter.enabled`, `filter.scope` | Store all in DB; flag/filter in Excel via Arabic/English ICT keywords | ⏳ Pending |
| 5 | First-run backfill window | `run.backfill_days` | `30` days | ⏳ Pending |
| 6 | Sector taxonomy | `sectors` (in `data/sectors.yaml`) | 8 core Kuwait sectors (Banking, Oil & Gas, Gov, Health, etc.) | ⏳ Pending |
| 7 | Client master list & ownership | `data/clients.csv`, `client_master.owner` | Pre-seeded Kuwait public entities; Owner: Khaled Abed / Presales Lead | ⏳ Pending |
| 8 | Output language | `output.translate_titles` | `false` (Arabic original canonical; optional bilingual title column) | ⏳ Pending |
| 9 | Excel structure & columns | `excel.sheets`, `excel.columns` | 7 standard sheets proposed in FR-8 with RTL Arabic formatting | ⏳ Pending |
| 10 | Cumulative vs daily file | `excel.mode` | `daily_timestamped` with `latest` copy (`KBM_Tenders_YYYY-MM-DD.xlsx`) | ⏳ Pending |
| 11 | Tender documents/attachments | `collect.download_attachments` | `false` (Metadata only: name, size, link, fee) | ⏳ Pending |
| 12 | Delivery destination | `delivery.destinations` | `["local"]` (Phase 1 local), extendable to `["email", "sharepoint"]` | ⏳ Pending |
| 13 | Run schedule (Asia/Kuwait) | `schedule.cron`, `schedule.days` | Daily Sun–Thu at 06:00 AM Kuwait time (`0 6 * * 0-4`) | ⏳ Pending |
| 14 | Hosting environment | Deployment Target | Docker container (deployable to Azure VM, KBM on-prem Linux/Windows VM) | ⏳ Pending |
| 15 | Secrets vault | `secrets.provider` | `env` in dev; Azure Key Vault or System Keyring in production | ⏳ Pending |
| 16 | Alert channel & recipients | `notify.channels`, `notify.recipients` | Email / Teams webhook on failure or challenge; Recipient: Khaled Abed | ⏳ Pending |
| 17 | LLM provider & data residency | `llm.provider`, `llm.model` | Google Gemini 2.5 Flash / Azure OpenAI; anonymized tender text only | ⏳ Pending |
| 18 | Expected Phase 2 scope | Architectural hooks | AI Go/No-Go scoring hook + CRM push hook (Dynamics / Salesforce) | ⏳ Pending |

---

## Detailed Breakdown & Questions for the Product Owner

### 1. Written Confirmation for Automated Retrieval
- **Brief Reference:** Rule 3.6, Section 9 Item 1
- **Config Key:** `compliance.automation_permitted: false`
- **Context:** CAPT has bot detection for unauthenticated traffic; Kuwait Al-Yawm `robots.txt` disallows automated crawling. Rule 3.6 mandates that before scheduled production runs, the product owner must confirm in writing that KBM's subscription permits automated retrieval.
- **Proposed Default:** `false`. The agent will only run manually with a human present until Khaled signs off in `docs/COMPLIANCE.md`.
- **Question for Khaled:** *Do KBM's subscription agreements for CAPT and Kuwait Al-Yawm permit automated retrieval for internal sales monitoring, and can you confirm sign-off in `docs/COMPLIANCE.md` before we schedule automated production runs?*

---

### 2. OTP/2FA and Dedicated vs Shared Account
- **Brief Reference:** Rule 3.3, 3.5, Section 9 Item 2
- **Config Key:** `portals.capt.auth`, `portals.kuwait_alyawm.auth`
- **Context:** If existing portal accounts are actively used by KBM sales/presales staff, concurrent logins may trigger `SESSION_CONFLICT` or invalidate staff browser sessions. Furthermore, if SMS or email OTP is required on login, automated runs will halt immediately (Rule 3.3 prohibits solving/bypassing challenges).
- **Proposed Default:** 
  1. For Milestone 1 (Recon): Use existing credentials via environment variables during a human-attended session to observe whether OTP/2FA or captcha is triggered.
  2. For Production: Recommend requesting a dedicated automated service account (e.g. `tenderscout@kbm.com.kw`) without OTP, or coordinating run times outside business hours to prevent session conflicts.
- **Question for Khaled:** *Do the current KBM accounts for CAPT and Kuwait Al-Yawm require SMS/Email OTP upon login? Can a dedicated agent account be provisioned for production to avoid displacing staff sessions?*

---

### 3. Notice Types to Collect
- **Brief Reference:** FR-3, Section 9 Item 3
- **Config Key:** `collect.notice_types: ["tender", "practice", "prequal", "addendum", "cancellation", "award"]`
- **Context:** Kuwait public procurement includes:
  - Tenders (مناقصات عامة ومحدودة)
  - Practices / RFPs (ممارسات)
  - Pre-qualifications (تأهيل مسبق)
  - Addenda / Extension / Clarification Circulars (ملاحق وتمديد واستفسارات)
  - Cancellations (إلغاءات)
  - Awards / Recommendations (ترسيات وتوصيات)
  - Auctions / Direct Sale (مزايدات)
- **Proposed Default:** Collect all procurement notices and status changes, but exclude Auctions (`auction`) by default as they represent asset disposal rather than IT procurement opportunities.
- **Question for Khaled:** *Should auctions (`auction`) be excluded, and should tender awards/results (`award`) and pre-bid circulars (`addendum`) be included in the primary workbook sheets?*

---

### 4. Relevance Filter (IT/ICT Focus vs All Tenders)
- **Brief Reference:** FR-7, Section 9 Item 4
- **Config Key:** `filter.enabled: true`, `filter.mode: "tag_only" | "strict_sheet"`, `filter.keywords_ar`, `filter.keywords_en`
- **Context:** KBM is an enterprise IT systems integrator and solution provider (infrastructure, cloud, cybersecurity, software, networking, hardware). Thousands of public tenders cover medical, civil construction, cleaning, security guarding, etc.
- **Proposed Default:**
  - Store **all** collected tenders in the SQLite database so no data is ever permanently lost (`filter.store_unmatched: true`).
  - In Excel: Keep main sheets filtered to KBM-relevant notices using a curated keyword list (Arabic & English), with a separate "All Tenders" or "Non-ICT" sheet/toggle.
  - Initial seed keywords include: شبكات, خوادم, حاسب آلي, برمجيات, أمن سيبراني, مراكز بيانات, تراخيص, صيانة أجهزة, بنية تحتية, تخزين بيانات, Server, Storage, Network, Cyber, Cloud, License, Hardware, Software, Datacenter, ERP, SI, Maintenance.
- **Question for Khaled:** *Do you prefer the main sheets to contain ONLY KBM-relevant (IT/ICT) tenders, or ALL tenders with a 'Relevance' column tag? Who will review/expand the seed keyword list?*

---

### 5. First-Run Backfill Window
- **Brief Reference:** FR-1, Section 9 Item 5
- **Config Key:** `run.backfill_days: 30`
- **Context:** On the first execution, scraping the entire historical archive could trigger rate limits or bot detection. Typical tender submission windows in Kuwait span 30 to 45 days.
- **Proposed Default:** `30` days back from initial execution date. This ensures all currently active/open tenders are captured into the baseline database without overloading portal servers.
- **Question for Khaled:** *Is 30 days sufficient for the initial backfill, or should we target 45 or 60 days?*

---

### 6. Sector Taxonomy
- **Brief Reference:** FR-6, Section 9 Item 6
- **Config Key:** `sectors` (stored in `data/sectors.yaml`)
- **Context:** FR-6 suggests sectors such as Banking & Finance, Oil & Gas, Government, Other/Cross-sector.
- **Proposed Default:** A tailored 8-sector taxonomy aligned with KBM's Kuwait business units:
  1. `Oil & Gas / Energy` (KPC, KNPC, KOC, KIPIC, MEW)
  2. `Banking & Financial Services` (CBK, KFH, NBK, KIA, KSE)
  3. `Government & Public Sector` (Ministries, Authorities, Civil Service)
  4. `Telecom & Media` (CITRA, Zain, Ooredoo, stc, MOI media)
  5. `Healthcare` (Ministry of Health, KCCC, Dasman)
  6. `Education & Research` (Kuwait University, PAAET, KFAS, KISR)
  7. `Defense & Security` (MOD, MOI, KNG)
  8. `Other / Cross-Sector`
- **Question for Khaled:** *Does this 8-sector taxonomy match KBM's sales organization and reporting lines?*

---

### 7. Client Master List & Ongoing Ownership
- **Brief Reference:** FR-6, Section 9 Item 7
- **Config Key:** `data/clients.csv`, `client_master.owner: "Khaled Abed"`
- **Context:** Tenders publish client names in varying Arabic formats (e.g. "وزارة المواصلات", "المواصلات", "MOC"). FR-6 specifies mapping `client_raw` -> `client` via `data/clients.csv`. Unmatched clients are logged to `data/clients_pending.csv`.
- **Proposed Default:**
  - We deliver a starter `data/clients.csv` pre-populated with ~60 major Kuwait ministries, authorities, and state-owned enterprises with alias mapping and account owner placeholders.
  - Ongoing ownership: The KBM Presales / Solutions team reviews `data/clients_pending.csv` periodically to add new clients and assign account owners.
- **Question for Khaled:** *Do you have an existing KBM client master list or CRM export (names, sectors, account managers) that we can import into `data/clients.csv`?*

---

### 8. Output Language: Arabic vs Bilingual
- **Brief Reference:** FR-5, FR-8, Section 9 Item 8
- **Config Key:** `output.translate_titles: false`
- **Context:** Original notices are Arabic. KBM account managers and vendor partners may include English speakers.
- **Proposed Default:** Arabic as canonical original (`title_ar`). In Phase 1, keep `output.translate_titles: false` by default to avoid translation latency and LLM costs, but architect a clean column `title_en` that can be toggled on when an LLM provider is connected.
- **Question for Khaled:** *Is Arabic-only sufficient for Phase 1 Excel sheets, or do you require English title translations from Day 1?*

---

### 9. Final Excel Columns and Sheets
- **Brief Reference:** FR-8, Section 9 Item 9
- **Config Key:** `excel.sheets`, `excel.columns`
- **Context:** Proposed sheets:
  1. `Summary` (KPI cards, run date, counts by status/sector/client, system alerts)
  2. `New Today` (`NEW` and `UPDATED` notices from the current run)
  3. `All Open` (All tenders not yet closed)
  4. `By Sector` (Grouped hierarchically by Sector -> Client)
  5. `By Client` (Alphabetical/Grouped by Client)
  6. `Needs Review` (Low confidence classifications, unparsed dates, pending clients)
  7. `Run Log` (Audit trail, pages visited, portal status, classified errors)
- **Proposed Default:** Approve the proposed 7 sheets and canonical column set with RTL support, auto-filtered headers, and closing date conditional formatting (e.g. closing in ≤ 7 days highlighted red/amber).
- **Question for Khaled:** *Are there specific additional columns (e.g. KBM Account Manager, Partner/Vendor alignment, Estimated Budget) required in the sheets?*

---

### 10. Cumulative Workbook vs Daily Timestamped Files
- **Brief Reference:** FR-8, Section 9 Item 10
- **Config Key:** `excel.mode: "daily_timestamped"`
- **Context:** A single overwritten master file vs a daily archive file `KBM_Tenders_YYYY-MM-DD.xlsx`.
- **Proposed Default:** Daily timestamped files stored in `output/reports/KBM_Tenders_YYYY-MM-DD.xlsx`, plus an automatically updated symlink or copy `output/reports/KBM_Tenders_Latest.xlsx`. This provides complete historical auditing while offering a fixed link for sales teams.
- **Question for Khaled:** *Do you prefer daily timestamped files, a single cumulative master file, or the proposed hybrid (daily file + `Latest` copy)?*

---

### 11. Tender Attachments: Download vs Metadata Only
- **Brief Reference:** FR-3, Rule 3.2, Section 9 Item 11
- **Config Key:** `collect.download_attachments: false`
- **Context:** Rule 3.2 strictly forbids purchasing tender documents. Many notices offer free public annexes (e.g. extension circulars, pre-bid meeting notes).
- **Proposed Default:** `metadata_only` (`collect.download_attachments: false`). Capture attachment file name, download link, and fee (if any). Do not download files to disk in Phase 1 to conserve bandwidth and storage.
- **Question for Khaled:** *Should free public tender circulars/annexes (PDFs) be downloaded locally, or is capturing their links and metadata sufficient?*

---

### 12. Delivery Destination(s) & Recipients
- **Brief Reference:** FR-9, Section 9 Item 12
- **Config Key:** `delivery.destinations: ["local"]`, `delivery.email.*`, `delivery.sharepoint.*`
- **Context:** Where should the agent drop the Excel workbook upon run completion?
- **Proposed Default:**
  - Local dev / testing: `output/reports/`.
  - Production recommendation: Email distribution to KBM presales list (via Office 365 / SMTP) AND upload to a designated KBM SharePoint / Teams document library.
- **Question for Khaled:** *Which delivery channel is preferred for Phase 1: SharePoint library sync, Email attachment, or Teams channel post? What are the destination email addresses or SharePoint site URLs?*

---

### 13. Run Schedule & Active Days
- **Brief Reference:** FR-1, Section 9 Item 13
- **Config Key:** `schedule.cron: "0 6 * * 0-4"`, `schedule.timezone: "Asia/Kuwait"`
- **Context:** Kuwait working days are Sunday through Thursday. Kuwait Al-Yawm gazette issues weekly on Sundays; CAPT updates throughout the week.
- **Proposed Default:** Run once daily Sunday through Thursday at 06:00 AM Kuwait time (UTC+3), ensuring presales teams have the latest report at the start of business.
- **Question for Khaled:** *Is 06:00 AM Kuwait time Sunday–Thursday the ideal schedule, or should we include a weekend run (e.g. Saturday afternoon)?*

---

### 14. Hosting Environment & Deployment Target
- **Brief Reference:** Section 5, Section 9 Item 14
- **Config Key:** Deployment target (`docker` container)
- **Context:** The solution must run unattended. Options include an on-premises VM (Windows or Linux), an Azure VM / Container App, or an internal KBM server.
- **Proposed Default:** Docker container (`python:3.12-slim` + Playwright Chromium dependencies) orchestrated via `docker-compose` or cron. Fully portable to Azure or on-premises KBM infrastructure.
- **Question for Khaled:** *Where will the agent run in production: a KBM on-prem Linux/Windows VM, or an Azure cloud subscription?*

---

### 15. Secrets Vault Strategy
- **Brief Reference:** Rule 3.1, Section 9 Item 15
- **Config Key:** `secrets.provider: "env"` (dev) / `"azure_keyvault"` | `"keyring"` (prod)
- **Context:** Credential names: `CAPT_USERNAME`, `CAPT_PASSWORD`, `ALYAWM_USERNAME`, `ALYAWM_PASSWORD`.
- **Proposed Default:**
  - Development / Recon: Local environment variables loaded from `.env` (strictly git-ignored and secret-scanned).
  - Production: Azure Key Vault (if hosted in Azure) or Windows Credential Manager / Linux Keyring (if hosted on a dedicated VM).
- **Question for Khaled:** *Which vault service does KBM IT approve for storing production credentials (e.g. Azure Key Vault, HashiCorp Vault, or local OS Keyring)?*

---

### 16. Alert Recipients and Notification Channels
- **Brief Reference:** FR-10, Rule 3.3, Section 9 Item 16
- **Config Key:** `notify.channels: ["email"]`, `notify.recipients: ["kabed@kbm.com.kw"]`
- **Context:** Immediate alerts required on `CHALLENGE` (CAPTCHA/OTP), `SESSION_CONFLICT`, `BAD_CREDENTIALS`, or site downtime.
- **Proposed Default:** Direct email notification to Khaled Abed with failure classification, diagnostic timestamp, and masked error message. Optional webhook to a KBM IT Alerts Teams channel.
- **Question for Khaled:** *Who should receive urgent operational alerts, and should notifications be sent via Email, Microsoft Teams webhook, or both?*

---

### 17. LLM Provider, Model, and Data Residency
- **Brief Reference:** FR-6, Rule 3, Section 9 Item 17
- **Config Key:** `llm.provider: "gemini"`, `llm.model: "gemini-2.5-flash"`
- **Context:** Used strictly as a tertiary fallback for classifying unknown clients and sectors. Only public tender titles and scope snippets are passed.
- **Proposed Default:** Google Gemini 2.5 Flash (high speed, exceptional Arabic nuance) or Azure OpenAI (Kuwait / UAE regional tenant). Encapsulated in an abstract `LLMClassifier` interface so providers can be swapped instantly via config without code changes.
- **Question for Khaled:** *Does KBM have a preferred enterprise LLM provider (Azure OpenAI vs Google Gemini) and are there any corporate data-residency restrictions for public tender text?*

---

### 18. Expected Phase 2 Scope & Extension Points
- **Brief Reference:** Section 1, Section 9 Item 18
- **Context:** Designing Phase 1 cleanly so future capabilities integrate without refactoring.
- **Proposed Default:** Provide modular extension hooks in the architecture:
  1. `scoring_hook`: AI-driven qualification / Go-No-Go scoring based on KBM vendor matrix (IBM, Cisco, Dell, Microsoft).
  2. `crm_export_hook`: Automated deal/lead creation in KBM CRM (Microsoft Dynamics / Salesforce).
  3. `instant_alert_hook`: Real-time WhatsApp or Teams notifications for high-priority tenders.
- **Question for Khaled:** *Which Phase 2 capabilities are highest priority for KBM sales, and are there specific CRM or vendor systems we should prepare integration interfaces for?*

---

## Next Steps

1. **Owner Review:** Khaled Abed reviews the 18 proposed defaults above.
2. **Approval Checkpoint (⛔ Milestone 0):** Provide approval or edits to these items.
3. **Transition to Milestone 1:** Upon approval, launch human-attended Portal Recon for CAPT and Kuwait Al-Yawm to generate `docs/PORTAL_MAP_capt.md` and `docs/PORTAL_MAP_kuwait_alyawm.md`.
