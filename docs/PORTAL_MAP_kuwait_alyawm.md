# Portal Map: Kuwait Al-Yawm Official Gazette

**Portal Identifier:** `kuwait_alyawm`  
**Base URL:** `https://kuwaitalyawm.media.gov.kw/`  
**Host Framework:** ASP.NET MVC / Razor with Bootstrap & jQuery DataTables  
**Recon Status:** Completed (Milestone 1)  
**Human Checkpoint:** ⛔ Pending Product Owner Approval  

---

## 1. Authentication Architecture & Session Flow

### 1.1 Entry Point & Form Location
- **Home URL:** `https://kuwaitalyawm.media.gov.kw/`
- **Login Form Location:** Embedded directly on the home page and in `/online` sidebar.
- **Form Action:** `/Account/LoginOnline` (`POST`)

### 1.2 Form Fields & DOM Selectors

| Field Purpose | Selector / Attribute | Element Type | Notes |
|:---|:---|:---|:---|
| **Anti-Forgery Token** | `input[name="__RequestVerificationToken"]` | `hidden` | ASP.NET verification token generated per request |
| **Username** | `input#UserName`, `input[name="UserName"]` | `text` | KBM subscription username |
| **Password** | `input#Password`, `input[name="Password"]` | `password` | KBM subscription password |
| **Remember Me** | `input#RememberMe`, `input[name="RememberMe"]` | `checkbox` | Persistent cookie option |
| **Submit Button** | `form[action*="LoginOnline"] input[type="submit"]` | `submit` | Text: `تسجيل الدخول` |
| **Error Feedback** | `.text-danger`, `.validation-summary-errors` | `div` / `span` | Displays invalid credentials messages |

### 1.3 Positive Session Detection & Logout
- **Logged-in Indicator:** Display of subscriber account name, subscription expiry date, or logout link `a[href*="/Account/LogOff"]` or `a[href*="/Logout"]`.
- **Subscriber Verification:** Access to `/flip/index?id=...&no=...` loads viewer content rather than the restriction notice `خدمة تصفح الإصدار متاحة فقط للمشتركين`.
- **Logout Endpoint:** Direct invocation of `/Account/LogOff` to release shared subscription session cleanly.

### 1.4 Failure Classification Matrix

| Observed Signal | Error Classification | Alert / Action |
|:---|:---|:---|
| `.validation-summary-errors` or invalid credentials message | `BAD_CREDENTIALS` | Alert operator to check vault credentials. Halt Al-Yawm run. |
| Text contains "تم تسجيل الدخول من جهاز آخر" (Concurrent session) | `SESSION_CONFLICT` | Do NOT terminate other session. Halt Al-Yawm run and alert. |
| Bot challenge or CAPTCHA prompt | `CHALLENGE` | Capture redacted screenshot, alert operator. Halt Al-Yawm run. |
| SSL handshake failure, 500/503 error, or gateway timeout | `SITE_DOWN` | Retry once after 10 min. If down, alert and proceed with other portals. |
| Missing `/online/AdsCategory/1` table or changed column headers | `LAYOUT_CHANGED` | Alert operator with HTML diff. |

---

## 2. Navigation Architecture to Tender Notices

The official gazette categorizes public notices under `/online/AdsCategory/{id}`:

| Category ID | URL Path | Category Name (Arabic) | Category Name (English) | Scope for KBM |
|:---:|:---|:---|:---|:---:|
| **1** | `/online/AdsCategory/1` | المناقصات | Public Tenders | **Primary In-Scope** |
| **18** | `/online/AdsCategory/18` | الممارسات | Practices / RFPs | **Primary In-Scope** |
| **6** | `/online/AdsCategory/6` | الاستدراكات | Addenda / Clarifications | **Primary In-Scope** |
| **2** | `/online/AdsCategory/2` | المزايدات | Auctions / Asset Sales | Excluded by default |
| **8** | `/online/AdsCategory/8` | القرارات | Ministerial Resolutions | Reference |
| **9** | `/online/AdsCategory/9` | القوانين | State Laws & Decrees | Reference |
| **Current Issue** | `/online/MainEditions` | الاصدار الحالي | Current Gazette Issue | Active monitoring |
| **All Issues** | `/online/editions` | الاصدارات السابقة | Historical Gazette Archive | Backfill source |

---

## 3. Listing Page Structure & DOM Selectors

- **URL:** `https://kuwaitalyawm.media.gov.kw/online/AdsCategory/1`
- **Container:** Standard HTML `table` styled with Bootstrap / jQuery DataTables.
- **Table Headers:**
  1. `العنوان` (Title / Tender No - e.g. `RFP/2165997`, `RFQ/2167837`)
  2. `تصفح الإعلان` (Browse Notice - Icon with `data-load-url`)
  3. `رقم الإصدار` (Gazette Issue Number - e.g. `1810`, `1809`)
  4. `نوع الإصدار` (Issue Type - `إصدار رئيسي` / `ملحق`)
  5. `التاريخ الميلادي` (Gregorian Date - e.g. `27/09/2026`)
  6. `التاريخ الهجري` (Hijri Date - e.g. `16/ربيع الثاني/1448`)
- **Row Selector:** `table tbody tr`
- **Page Length Selector:** Dropdown for 10, 25, 50, 100 entries per page. Setting to 100 minimizes round trips.
- **Pagination Controls:** `.dataTables_paginate`, `ul.pagination li a` (Page numbers, Next, Previous).

---

## 4. The Gazette Reader & Announcement Extraction Strategy

### 4.1 Discovery: The Flip Viewer Modal
During reconnaissance, inspecting row cells revealed that the notice text is viewed via a modal flipbook triggered by:
```html
<a data-load-url="/flip/index?id={issue_id}&no={page_no}" 
   data-toggle="modal" 
   data-target="#ModalNewAct" 
   class="flip">
   <i class="fas fa-file"></i>
</a>
```
- `issue_id` represents the gazette issue number in the CMS (e.g. `5599` for Issue #1810).
- `page_no` represents the exact page number of the tender notice within the issue (e.g. `238`).

### 4.2 Subscriber Gate
- **Unauthenticated:** Requesting `/flip/index?id=...&no=...` returns HTTP 200 with an HTML lock screen:
  `<div style="font-size:30px;font-weight:bold;color:blue">خدمة تصفح الإصدار متاحة فقط للمشتركين</div>`
- **Authenticated:** Returns the gazette page viewer containing the full tender announcement, issuing ministry, scope of work, closing date, and bond requirements.

### 4.3 Extraction Pipeline (Dual Layer)
1. **Metadata Tier (Instant):** Captured directly from the category table:
   - `tender_no`: Extracted from column 1 (`td.wrapok`).
   - `issue_no`: Extracted from column 3.
   - `publish_date`: Gregorian date parsed from column 5 (`DD/MM/YYYY` -> `YYYY-MM-DD`).
   - `hijri_date`: Stored in `raw["hijri_date"]` for audit trail.
   - `page_ref`: Parsed from `data-load-url` (`no` parameter).
2. **Detail Content Tier (Full Text):**
   - For notices passing the backfill/since window, fetch the authenticated flip page `/flip/index?id={id}&no={page}`.
   - **Text Layer Extraction (First Preference):** Extract selectable HTML/SVG/PDF text layer.
   - **Arabic OCR Fallback:** If page is rendered as an image/canvas, pass through Tesseract Arabic (`lang="ara"`) with preprocessing (contrast normalization).
   - Parse: Issuing entity (`client_raw`), tender title/description (`title_ar`), closing date (`closing_date`), document price, and bid bond.

---

## 5. Security, Polite Access & Compliance Guardrails

1. **Sequential Polite Timing:** 3.0 to 8.0 seconds delay between category page requests and flip viewer loads.
2. **Session Release:** Explicit logout via `/Account/LogOff` at script end to ensure KBM staff accounts are never locked.
3. **Redaction:** Mask `UserName` and `Password` values in any error logs or diagnostic DOM dumps.
4. **Read-Only Behaviour:** Strictly read category pages and viewer pages. Never submit any contact or inquiry forms.
