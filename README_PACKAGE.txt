======================================================================
     KBM Tender Scout - Public Tender Monitoring & Qualification
              Khorafi Business Machines (KBM) W.L.L.
======================================================================

مرحباً بك في منظومة راصد مناقصات الخرافي (KBM Tender Scout)
Welcome to the KBM Tender Scout System.

This package allows anyone at KBM to run the tender monitoring portal,
view qualified opportunities matching KBM's 5 Business Units, trigger live
scrapes, and export formatted Excel workbooks.

----------------------------------------------------------------------
1. QUICK START OPTIONS / خيارات التشغيل السريع
----------------------------------------------------------------------

OPTION A: [Recommended] Automated One-Click Setup & Launch
----------------------------------------------------------
Double-click:  Run_KBM_TenderScout.bat
- Checks if Python is installed on your computer.
- Automatically creates an isolated virtual environment (.venv).
- Automatically installs all required Python packages.
- Automatically installs Playwright Chromium browser engine.
- Automatically launches the Web Portal at http://127.0.0.1:8000
- Opens your default web browser directly to the dashboard!

OPTION B: Offline HTML Dashboard (Zero Setup / بدون أي تثبيت)
-------------------------------------------------------------
Double-click:  open_offline_dashboard.bat
OR directly open:  output\reports\KBM_Tender_Dashboard.html
- Opens instantly in Google Chrome, Microsoft Edge, or Firefox.
- Works 100% offline with zero dependencies and no Python required.
- Includes all pre-analyzed tenders, KBM fit scores, Business Unit filters,
  and presales evaluation rationales.

OPTION C: Manual Live Scraping Run
-----------------------------------
Double-click:  run_collection.bat
- Connects securely to Central Agency for Public Tenders (CAPT) and
  Kuwait Al-Yawm Official Gazette.
- Extracts all active notices, normalizes, deduplicates, and re-scores.
- Generates updated Excel reports in output\reports\

OPTION D: Docker (Server / Linux / Cross-Platform)
--------------------------------------------------
Run:  docker compose up -d
- Access portal at http://localhost:8000

----------------------------------------------------------------------
2. PREREQUISITES / المتطلبات الأساسية
----------------------------------------------------------------------
- Operating System: Windows 10/11, macOS, or Linux
- Python: Version 3.10 or newer (if running the live server or scrapers).
  If Python is not installed, download it from:
  https://www.python.org/downloads/
  (Remember to check "Add Python to PATH" during installation)

----------------------------------------------------------------------
3. CREDENTIALS & SECRETS CONFIGURATION / بيانات الدخول
----------------------------------------------------------------------
For security and compliance:
- Credentials must NEVER be committed to Git or shared publicly.
- Copy .env.example to .env (the setup script does this automatically).
- Edit .env with your assigned portal credentials:
    CAPT_USERNAME=siddiq@kbm-kw.com
    CAPT_PASSWORD=...
    ALYAWM_USERNAME=Gbmme
    ALYAWM_PASSWORD=...

----------------------------------------------------------------------
4. SUPPORT & CONTACT / الدعم الفني
----------------------------------------------------------------------
Digital Solutions & AI Practice
Khorafi Business Machines (KBM) W.L.L.
Kuwait
======================================================================
