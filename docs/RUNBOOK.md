# KBM Tender Monitoring Agent — Operations Runbook

**Product Owner:** Khaled Abed, Digital Solutions Lead, Khorafi Business Machines (KBM), Kuwait  
**System Version:** 1.0.0 (Phase 1)  
**Classification:** KBM Internal Operations  

---

## 1. System Overview

The KBM Tender Monitoring Agent is an enterprise daily data collection agent that signs in to Kuwait's public tender portals with KBM's existing subscription accounts, ingests and normalizes tender notices, matches client entities, classifies sectors, filters for ICT relevance, deduplicates across portals, and delivers an Excel workbook.

```
+-----------------------------------------------------------------------------------+
|                                  DAILY SCHEDULER                                  |
|                 06:00 AM Sun-Thu (Asia/Kuwait) / Max 1 retry per day               |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                              RUN ORCHESTRATOR (run.py)                            |
|                     Compliance Gate Check (docs/COMPLIANCE.md)                    |
+-----------------------------------------------------------------------------------+
                  |                                               |
                  v                                               v
+---------------------------------------+       +-----------------------------------+
|            CAPT CONNECTOR             |       |       KUWAIT AL-YAWM CONNECTOR    |
|   - Polite delay (3-8s)               |       |   - Polite delay (3-8s)           |
|   - Read-only actions                 |       |   - Category 1 & 18 parsing       |
|   - Single sequential session         |       |   - Flip viewer extraction        |
|   - Clean logout on exit              |       |   - Clean logout on exit          |
+---------------------------------------+       +-----------------------------------+
                  \                                               /
                   \-----------------------------+---------------/
                                                 |
                                                 v
                               +-----------------------------------+
                               |         NORMALIZATION ENGINE      |
                               |   - Arabic digits (٠-٩ -> 0-9)    |
                               |   - Text unification (alef/teh)   |
                               |   - Kuwait dates (ISO YYYY-MM-DD) |
                               |   - Money & currencies (KWD)      |
                               +-----------------------------------+
                                                 |
                                                 v
                               +-----------------------------------+
                               |     CLASSIFICATION & FILTERING    |
                               |   - Client master (clients.csv)   |
                               |   - Sector taxonomy (sectors.yaml)|
                               |   - ICT Keyword relevance filter  |
                               |   - Pending queue (pending.csv)   |
                               +-----------------------------------+
                                                 |
                                                 v
                               +-----------------------------------+
                               |         CROSS-PORTAL DEDUPE       |
                               |   - Match tender no + client      |
                               |   - Fuzzy title similarity        |
                               |   - Unified multi-portal sources  |
                               +-----------------------------------+
                                                 |
                                                 v
                               +-----------------------------------+
                               |         SQLITE STATE STORE        |
                               |   - SHA-256 Content Hash          |
                               |   - NEW / UPDATED / UNCHANGED     |
                               +-----------------------------------+
                                                 |
                                                 v
                               +-----------------------------------+
                               |       EXCEL WORKBOOK WRITER       |
                               |   - 7 RTL Arabic worksheets       |
                               |   - Navy styling / Frozen headers |
                               |   - Closing soon alert highlight  |
                               +-----------------------------------+
                                                 |
                                                 v
                               +-----------------------------------+
                               |        DELIVERY & NOTIFIER        |
                               |   - Local reports archive         |
                               |   - Email & SharePoint hooks      |
                               |   - Operator failure alerts       |
                               +-----------------------------------+
```

---

## 2. Secrets Management & Vault Strategy (Rule 3.1)

Secrets are **never** committed to version control, logged in output files, or embedded in screenshots.

### Runtime Secret Names:
* `CAPT_USERNAME` — KBM Central Agency for Public Tenders login username/email.
* `CAPT_PASSWORD` — KBM Central Agency for Public Tenders password.
* `ALYAWM_USERNAME` — KBM Kuwait Al-Yawm subscription username.
* `ALYAWM_PASSWORD` — KBM Kuwait Al-Yawm subscription password.

### Development Mode:
Place secrets in a local `.env` file in the project root (automatically excluded via `.gitignore` and enforced by `scripts/secret_scan.py`):
```env
CAPT_USERNAME=presales@kbm.com.kw
CAPT_PASSWORD=secret_password_here
ALYAWM_USERNAME=kbm_subscriber
ALYAWM_PASSWORD=secret_password_here
```

### Production Mode:
Inject environment variables directly via the host OS, Docker runtime environment, or Azure Key Vault secrets provider.

---

## 3. Operator Setup Guide

### 3.1 Prerequisites
* Python 3.12+ (or Docker Engine 24+)
* Git
* Chromium browser dependencies (via Playwright)

### 3.2 Installation
```bash
# 1. Clone repository
git clone <repo_url> KBM_TenderScout
cd KBM_TenderScout

# 2. Create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### 3.3 Verify Pre-Commit Secret Scanner
Always run the secret scanner before any commits:
```bash
python scripts/secret_scan.py
```

---

## 4. Manual Execution Commands (FR-1)

### Run all enabled portals:
```bash
python src/run.py --portal all
```

### Run a specific portal:
```bash
python src/run.py --portal capt
python src/run.py --portal kuwait_alyawm
```

### Run with a custom backfill window:
```bash
python src/run.py --portal all --since 2026-09-01
```

### Run a quick test with notice limits:
```bash
python src/run.py --portal all --limit 5
```

### Regenerate Excel reports without hitting live portals:
```bash
python src/run.py --excel-only
```

---

## 5. Scheduled Production Deployment (Milestone 5)

### Option A: Docker Deployment (Recommended)
```bash
# Build and start container
docker-compose up --build -d

# Check logs
docker-compose logs -f
```

### Option B: Windows Task Scheduler (KBM Windows Server)
Run PowerShell as Administrator:
```powershell
.\scripts\schedule_windows.ps1
```
This registers the scheduled task to execute every Sunday through Thursday at 06:00 AM Kuwait Time.

### Option C: Linux / Azure VM Cron
```bash
crontab scripts/schedule_cron.sh
```

---

## 6. Failure Classifications & Operator Response Matrix

| Failure Code | Observed Cause | Operator Action |
|:---|:---|:---|
| `BAD_CREDENTIALS` | Password rejected by portal. | Verify credentials manually in browser. Update vault / `.env`. |
| `CHALLENGE` | CAPTCHA / OTP / Cloudflare prompt appeared. | **Do NOT attempt to bypass.** Review redacted screenshot in `logs/screenshots/`. Log in once manually to solve challenge if required. |
| `SESSION_CONFLICT` | "Already logged in elsewhere" detected. | **Do NOT terminate staff session.** Agent yields gracefully. Contact presales staff to coordinate logout. |
| `SITE_DOWN` | HTTP 500, 502, 503 or gateway timeout. | Transient error. Agent automatically retries once after 10 minutes. If persistent, check portal maintenance. |
| `LAYOUT_CHANGED` | Required form or listing selectors missing. | Inspect `docs/recon/` HTML dumps. Update selectors in portal connector. |

---

## 7. Master Data Maintenance & Client Queue

### 7.1 Reviewing Unmapped Clients (`data/clients_pending.csv`)
When the agent encounters a tender with an issuing entity not currently in the master index, it automatically logs it into `data/clients_pending.csv` and marks `needs_review = True`.

**Weekly Operator Workflow:**
1. Open `data/clients_pending.csv`.
2. For each pending entity:
   - Identify the canonical Arabic name and English translation.
   - Assign the appropriate sector ID from `data/sectors.yaml`.
   - Add aliases (common acronyms, abbreviations, colloquial names).
3. Append the verified entry to `data/clients.csv`.
4. Re-run `python src/run.py --excel-only` to update existing records with the new mapping.

---

## 8. Compliance Gate Verification (Rule 3.6)

Before scheduled unattended runs may be enabled in production:
1. Product Owner (Khaled Abed) must sign `docs/COMPLIANCE.md`.
2. Set `compliance.automation_permitted: true` in `config/config.yaml`.
3. If this setting remains `false`, `src/scheduler.py` blocks automated executions by design.
