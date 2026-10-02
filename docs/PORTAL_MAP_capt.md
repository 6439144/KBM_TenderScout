# Portal Map: Central Agency for Public Tenders (CAPT / CTC)

**Portal Identifier:** `capt`  
**Base URL:** `https://capt.gov.kw/ar/`  
**Host Framework:** Django (Python) with Bootstrap & jQuery / Angular frontend  
**Recon Status:** Completed (Milestone 1)  
**Human Checkpoint:** ⛔ Pending Product Owner Approval  

---

## 1. Authentication Architecture & Session Flow

### 1.1 Entry Point & Form Trigger
- **Home URL:** `https://capt.gov.kw/ar/`
- **Login Trigger Element:** `<a href="#" class="log-in user-login">` or `<a class="user-login" href="javascript:void(0);" data-next-url="...">`
- **Login Modal Container:** Form `#loginForm` in modal popup.

### 1.2 Form Fields & DOM Selectors

| Field Purpose | Selector / Attribute | Element Type | Notes |
|:---|:---|:---|:---|
| **CSRF Token** | `input[name="csrfmiddlewaretoken"]` | `hidden` | Django CSRF token generated per session |
| **Username / Email** | `input[name="username"]` | `text` | Placeholder: `البريد الإليكتروني` |
| **Password** | `input[name="password"]` | `password` | Placeholder: `كلمة المرور` |
| **Next Redirect** | `input[name="next"]` | `hidden` | Optional target URL after login |
| **Submit Button** | `button.btnLogin` or `#loginForm button` | `button` | Text: `تسجيل الدخول` |
| **Error Feedback** | `ul.loginErrors`, `h3.popupText` | `ul` / `h3` | Populated dynamically on failure |

### 1.3 Positive Session Detection & Logout
- **Logged-in Indicator:** Presence of user profile dropdown or logout link: `a[href*="/logout/"]`, `.user-profile`, or disappearance of `.user-login`.
- **Logout Endpoint:** `https://capt.gov.kw/ar/logout/` (or profile menu trigger). Must be called cleanly at the conclusion of every run to release shared session.

### 1.4 Failure Classification Matrix

| Observed Signal | Error Classification | Alert / Action |
|:---|:---|:---|
| `ul.loginErrors:visible` contains invalid user/pass | `BAD_CREDENTIALS` | Alert operator to check vault credentials. Halt CAPT run. |
| Text contains "مستخدم مسجل دخول بالفعل" (Session active) | `SESSION_CONFLICT` | Do NOT force session out. Halt and alert operator. |
| CAPTCHA iframe or Cloudflare challenge appears | `CHALLENGE` | Capture redacted screenshot, alert operator. Halt CAPT run. |
| HTTP 500, 502, 503 or connection timeout | `SITE_DOWN` | Retry once after 10 min. If still down, alert and proceed. |
| Missing `#loginForm` or selectors changed | `LAYOUT_CHANGED` | Alert operator with DOM diff. Halt connector. |

---

## 2. Navigation Architecture to Tender Notices

The CAPT portal structures notices into clear functional categories under `/ar/tenders/`:

| Notice Category | URL Path | Business Purpose | Notice Type Mapped |
|:---|:---|:---|:---|
| **Open Tenders (مناقصات مطروحة)** | `/ar/tenders/opening-tenders/` | Active tenders currently accepting bids | `tender` / `practice` |
| **Pre-Tenders (الطرح المسبق)** | `/ar/tenders/pre-tenders/` | Upcoming tenders announced before formal launch | `prequal` / `tender` |
| **Closing / Bid Opening (فض العطاءات)** | `/ar/tenders/closing-tenders/` | Tenders past closing date where bids are unsealed | `closing` |
| **Extensions (تأجيل المناقصات)** | `/ar/tenders/postponement/` | Tenders with extended submission deadlines | `addendum` |
| **Awards (الترسيات)** | `/ar/tenders/winning-bids/` | Winning bidder announcements and contract awards | `award` |
| **Pre-Qualification (التأهيل المسبق)** | `/ar/tenders/qualifications/` | Contractor / supplier pre-qualification calls | `prequal` |
| **Initial Guarantees (التأمين الأولي)** | `/ar/tenders/warranties/` | Bid bond details and bank guarantee specifications | Reference |

---

## 3. Listing Page Structure & DOM Selectors

- **Container:** `.endless_page_template.ajax-response.tenderadvertising`
- **Notice Cards:** Rendered as alternating expandable cards `.page-width.detail-list` with header rows `.page-width`.
- **Pagination Mechanism:**
  - Django Endless Pagination with AJAX navigation.
  - Page links: `ul.pagination li a` or `div.endless_page_template a.endless_page_link` (e.g. `1`, `2`, `3`, `4`, `5`, `>`).
  - Cap per run: Configurable via `portals.capt.rate_limiting.max_pages_per_run` (default: 20 pages).

---

## 4. Field Mapping Schema (Canonical Tender Record)

Every notice card on `/ar/tenders/opening-tenders/` exposes detailed structured metadata in `.page-width.detail-list`:

| Source Label (Arabic) | Selector / Extraction Pattern | Canonical Field (FR-5) | Example Value |
|:---|:---|:---|:---|
| **الرقم** | Text following `الرقم` label | `tender_no` | `12/2025`, `CZ/LNGI/MP/012` |
| **الجهة** | Text following `الجهة` label | `client_raw` | `الهيئة العامة للصناعة` |
| **الموضوع** | Text following `الموضوع` label | `title_ar` | `أعمال صيانة المعدات وصيانة الميكانيكية...` |
| **تاريخ الطلب** | Text following `تاريخ الطلب` | `publish_date` | `سبتمبر 27, 2026` -> `2026-09-27` |
| **اخر موعد للعطاء** | Text following `اخر موعد للعطاء` | `closing_date` | `ديسمبر 22, 2026` -> `2026-12-22` |
| **الاجتماع التمهيدي** | Text / link under `الاجتماع التمهيدي` | `pre_bid_date` | `الاجتماع التمهيدي` / date |
| **النوع** | Badge under `النوع` | `notice_type` | `عامة` (General), `محدودة` (Limited) |
| **السعر** | Text following `السعر` | `document_fee` | `1000.000 د.ك` -> `1000.000 KWD` |
| **التأمين** | Text following `التأمين` | `bid_bond` | `45,000.000 د.ك` -> `45000.000 KWD` |
| **العروض البديلة** | Text following `العروض البديلة` | `raw["alternative_bids"]` | `لا يقبل عروض بديلة` |
| **التجزئة** | Text following `التجزئة` | `raw["divisible"]` | `غير قابلة للتجزئة` |
| **ملفات** | File list container under `ملفات` | `sources[].attachments` | `كراسة الشروط` (Metadata only) |
| **رابط الإعلان** | Detail URL / card reference | `sources[].url` | Direct tender page URL |

---

## 5. Security, Polite Access & Compliance Guardrails

1. **Polite Timing:** 3.0 to 8.0 seconds randomized delay between card expansions and pagination clicks.
2. **Read-Only Enforcement:**
   - **CRITICAL:** Do NOT click `شراء المناقصة` (`Buy Tender`) or any transaction button.
   - Ignore all purchasing elements.
3. **Redaction:** Any debug snapshots must mask input fields `#loginForm input`.
4. **Session Politeness:** Single session only. Explicit logout on script exit.
