# KBM Tender Scout (مرصاد المناقصات لمجموعة الخرافي)

> **Intelligent Public Tender Monitoring & Qualification Engine for Khorafi Business Machines (KBM)**  
> Bilingual Arabic/English platform that continuously scans Kuwait public procurement portals (**CAPT** & **Kuwait Al-Yawm**), qualifies opportunities against KBM's 5 Business Units & Technology Vendor Alliances, maps Account Managers, details exact required scopes & equipment, and delivers actionable presales intelligence via Web, Excel, and automated daily email reports.

[![GitHub Repo](https://img.shields.io/badge/GitHub-6439144%2FKBM__TenderScout-blue?logo=github)](https://github.com/6439144/KBM_TenderScout)
[![Azure App Service](https://img.shields.io/badge/Azure%20Hosting-Free%20Tier%20(F1)-0078D4?logo=microsoftazure)](https://kbm-tenderscout.azurewebsites.net)
[![Daily Morning Scan](https://img.shields.io/badge/Daily%20Scan-08%3A00%20AM%20Kuwait-success?logo=githubactions)](https://github.com/6439144/KBM_TenderScout/actions)
[![License](https://img.shields.io/badge/License-Proprietary%20KBM-darkred)]()

---

## 🌟 Key Capabilities

1. **Dual Portal Automated Discovery**:
   - **CAPT (الجهاز المركزي للمناقصات العامة)**: Scrapes bid openings, closing dates, bonds, and technical subjects.
   - **Kuwait Al-Yawm (جريدة كويت اليوم الرسمية)**: Connects to the official subscriber portal (Categories 18 & 1) and extracts exact practice/tender details, RFP/RFQ titles, fees, bank guarantees, and full requirements. Zero `LOADING PAGES` artifacts.
2. **KBM Company Profile Presales Qualification**:
   - Scores every tender from **0% to 100%** based on alignment with KBM's 5 core Business Units:
     - `IBM BU - Systems` (Power Systems, Storage, Enterprise Servers, Infrastructure)
     - `IBM BU - Solutions & Channel` (Maximo MAS, watsonx AI, Cloud Pak, Red Hat, Oracle)
     - `Services BU (MOPS)` (Managed Services, Cisco Gold Networking, Maintenance, SLA 24x7)
     - `Security BU` (Cyber SOC, Managed Security, CCTV Surveillance, Firewalls)
     - `Cloud BU` (Hybrid Cloud, OpenShift, Virtualization, Containers)
   - Evaluates technology partner alliances (Cisco, IBM, Lenovo, Palo Alto, Fortinet, Oracle, etc.).
3. **Exact Scope & Equipment Extraction**:
   - Dissects what equipment and services are explicitly required (e.g. Cisco switches/routers, IBM Maximo licenses, enterprise servers, CCTV cameras, UPS power units).
   - Articulates a rich presales rationale explaining exactly how KBM matches the requirements.
4. **Account Manager Mapping & Live Reassignment**:
   - Automatically maps tenders to designated KBM Account Managers (e.g. Abrar Al-Qallaf for PIC, KUFPEC, KGOC, KOTC, MPW; Jana Al-Obaid for MOD, MOH, PIFSS; Raed Obeid for MEW, CAIT, MOF; Fahad Al-Roumi for MOI, KNG; Eiman Ashkanani for KPC, KNPC, KOC).
   - Allows users to change the assigned Account Manager dynamically on the fly from the web interface, persisting changes immediately to the database.
5. **Multi-Channel Delivery**:
   - **Live Web Dashboard**: Interactive Tailwind + Lucide web interface with search, filters, and modal view.
   - **Standalone Offline HTML**: Zero-dependency single-file HTML report (`KBM_Tender_Dashboard.html`) that opens anywhere with full search & filters.
   - **Formatted Multi-Sheet Excel**: Color-coded RTL workbook (`KBM_Tenders_Latest.xlsx`) with dedicated KBM Opportunities presales prioritization.

---

## ☁️ Azure Free Hosting Architecture

The simplest, zero-cost architecture on Microsoft Azure:

- **Service**: Azure App Service (Linux)
- **SKU / Pricing Tier**: **F1 (Free Tier - $0.00/month forever)**
- **Resource Group**: `rg-kbm-platform`
- **App Service Plan**: `kbm-bootstrap-asp` (Linux F1)
- **Live URL**: **[https://kbm-tenderscout.azurewebsites.net](https://kbm-tenderscout.azurewebsites.net)**
- **Startup Command**:
  ```bash
  gunicorn -w 2 -k uvicorn.workers.UvicornWorker src.web.app:app --bind 0.0.0.0:8000 --timeout 120
  ```

---

## ⏰ Daily Morning Scan (Every Day at 8:00 AM)

### Option 1: Automated in the Cloud (GitHub Actions)
The repository includes a pre-configured scheduled workflow [`.github/workflows/daily_scan.yml`](.github/workflows/daily_scan.yml):
- **Schedule**: Every day at `05:00 UTC` (**08:00 AM Kuwait Time**).
- **Execution**: Runs in a free GitHub Actions Ubuntu runner with Playwright & Chromium.
- **Actions**:
  1. Scrapes fresh tenders from CAPT & Kuwait Al-Yawm.
  2. Qualifies all notices against the KBM Company Profile.
  3. Populates required equipment scopes and presales rationales.
  4. Generates updated Excel reports and Standalone HTML dashboard.
  5. Commits and pushes the updated data back to GitHub.
- **Manual Trigger**: Can also be run manually anytime by clicking **Actions > Daily Morning Tender Scan > Run workflow**.

> **Note on Secrets**: To enable Kuwait Al-Yawm subscriber scraping in GitHub Actions, add these two secrets under **GitHub Repo > Settings > Secrets and variables > Actions**:
> - `ALYAWM_USERNAME`: Your Kuwait Al-Yawm subscriber username
> - `ALYAWM_PASSWORD`: Your Kuwait Al-Yawm subscriber password

### Option 2: Automated on Local Windows (Task Scheduler)
To run the scan automatically on your local machine every morning at 8:00 AM:
1. Open the project folder in Windows Explorer.
2. Right-click [`scripts/setup_daily_schedule.bat`](scripts/setup_daily_schedule.bat) and select **"Run as Administrator"**.
3. A Windows scheduled task named `KBM_TenderScout_DailyScan` will be created to run [`scripts/run_daily_morning_scrape.bat`](scripts/run_daily_morning_scrape.bat) every day at 8:00 AM.

---

## 🚀 Local Quick Start

### 1. Prerequisites
- Python 3.10+ (Python 3.11 or 3.12 recommended)
- Git

### 2. Setup
```bash
# Clone the repository
git clone https://github.com/6439144/KBM_TenderScout.git
cd KBM_TenderScout

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies & Playwright browsers
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure Credentials (Local)
Copy `.env.example` to `.env` and fill in credentials:
```bash
cp .env.example .env
```

### 4. Run the Web Application
```bash
python -m uvicorn src.web.app:app --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

### 5. Run Live Scraper Manually
```bash
python -m src.main --portal all
```

---

## 📁 Repository Structure

```
KBM_TenderScout/
├── .github/workflows/
│   ├── daily_scan.yml           # Automated daily 8:00 AM scraper & qualification
│   └── azure_webapp.yml         # CI/CD deployment to Azure App Service
├── data/
│   ├── state.db                 # Canonical SQLite database (231+ verified tenders)
│   ├── clients.csv              # Kuwait government & oil clients and AM mapping
│   └── sectors.yaml             # Industry sector taxonomies
├── output/reports/
│   ├── KBM_Tenders_Latest.xlsx  # Formatted multi-sheet Excel report
│   └── KBM_Tender_Dashboard.html# Zero-dependency offline interactive dashboard
├── scripts/
│   ├── run_daily_morning_scrape.bat # One-click daily runner for Windows
│   ├── setup_daily_schedule.bat     # One-click Windows Task Scheduler setup
│   ├── reprocess_all_scopes_and_titles.py # Technical scope & rationale enricher
│   ├── generate_all_reports.py      # Excel & HTML report regenerator
│   └── deploy_to_azure.py           # Azure App Service direct deployer
├── src/
│   ├── connectors/              # CAPT and Kuwait Al-Yawm scrapers
│   ├── pipeline/                # Qualifier, Account Manager, State Store
│   ├── output/                  # Excel, HTML Dashboard, Delivery dispatch
│   └── web/                     # FastAPI web server, REST API, Tailwind templates
├── startup.sh                   # Azure App Service Linux startup script
└── requirements.txt             # Python runtime dependencies
```

---

## 🔒 Security & Data Integrity

- Live credentials (`.env`) are strictly excluded via `.gitignore` and never committed.
- Public procurement announcements contain no confidential pricing or proprietary bid data.
- Built for **Khorafi Business Machines (KBM) W.L.L.**
