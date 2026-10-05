"""
Kuwait Al-Yawm (Official Gazette) Connector.
Implements authenticated subscriber search, notice scraping, PDF download, and rich detail extraction.
"""

import html
import logging
import re
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
from urllib.parse import urljoin
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.config import PortalConfig
from src.connectors.base import PortalConnector
from src.models import FailureReason, NoticeRef, RawNotice, SessionResult
from src.utils.secrets import SecretManager

logger = logging.getLogger("kbm.connectors.kuwait_alyawm")


class HTMLTextExtractor(HTMLParser):
    """Extracts clean text from HTML preserving line structure."""
    def __init__(self):
        super().__init__()
        self.text_parts: List[str] = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip = True
        elif tag in ('p', 'div', 'br', 'tr', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'li'):
            self.text_parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = False
        elif tag in ('p', 'div', 'br', 'tr', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'li'):
            self.text_parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.text_parts.append(data)

    def get_text(self) -> str:
        return "".join(self.text_parts)


class TableExtractor(HTMLParser):
    """Parses HTML tables into rows and cells."""
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.tables = []
        self.current_table = []
        self.current_row = []
        self.current_cell = []

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
            self.current_table = []
        elif tag == 'tr' and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in ('td', 'th') and self.in_row:
            self.in_cell = True
            self.current_cell = []
        elif tag == 'br' and self.in_cell:
            self.current_cell.append(" ")

    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
            if self.current_table:
                self.tables.append(self.current_table)
        elif tag == 'tr' and self.in_table:
            self.in_row = False
            if self.current_row:
                self.current_table.append(self.current_row)
        elif tag in ('td', 'th') and self.in_row:
            self.in_cell = False
            self.current_row.append("".join(self.current_cell).strip())

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)


class KuwaitAlyawmConnector(PortalConnector):
    """Connector for the Kuwait Al-Yawm Official Gazette portal (kuwaitalyawm.media.gov.kw)."""

    def __init__(self, config: PortalConfig):
        super().__init__(config, portal_id="kuwait_alyawm")
        self.attachments_dir = Path("data/attachments/kuwait_alyawm")
        self.attachments_dir.mkdir(parents=True, exist_ok=True)

    def login(self) -> SessionResult:
        """Authenticates with Kuwait Al-Yawm subscriber account or runs in public mode."""
        username = SecretManager.get_secret(self.config.auth.username_secret)
        password = SecretManager.get_secret(self.config.auth.password_secret)

        if not username or not password:
            logger.info("Kuwait Al-Yawm: No credentials provided in environment. Proceeding in public reader mode.")
            return SessionResult(
                success=True,
                is_authenticated=False,
                portal_id=self.portal_id,
                message="Running in public reader mode (no subscription credentials provided)"
            )

        page = self.init_browser()
        try:
            logger.info("Kuwait Al-Yawm: Navigating to landing page for login...")
            page.goto(self.config.base_url, wait_until="networkidle", timeout=35000)
            self.polite_delay()

            # Check for bot challenge
            if self._check_challenges(page):
                screenshot = self.capture_challenge_screenshot("login_challenge")
                return SessionResult(
                    success=False,
                    is_authenticated=False,
                    error_type=FailureReason.CHALLENGE,
                    portal_id=self.portal_id,
                    message=f"Bot challenge encountered on Kuwait Al-Yawm. Redacted screenshot: {screenshot}"
                )

            # Check if login form is present
            user_input = page.locator('form[action*="LoginOnline"] input#UserName, input#UserName').first
            pass_input = page.locator('form[action*="LoginOnline"] input#Password, input#Password').first
            submit_btn = page.locator('form[action*="LoginOnline"] button[type="submit"], form[action*="LoginOnline"] input[type="submit"], button:has-text("تسجيل الدخول")').first

            if user_input.count() == 0 or pass_input.count() == 0:
                screenshot = self.capture_challenge_screenshot("missing_login_fields")
                return SessionResult(
                    success=False,
                    is_authenticated=False,
                    error_type=FailureReason.LAYOUT_CHANGED,
                    portal_id=self.portal_id,
                    message=f"Login fields not found on Kuwait Al-Yawm. Layout may have changed. Screenshot: {screenshot}"
                )

            # Fill credentials (values never logged)
            user_input.fill(username)
            pass_input.fill(password)
            self.polite_delay()

            submit_btn.click()
            page.wait_for_load_state("networkidle", timeout=25000)
            self.polite_delay()

            # Check for errors
            error_el = page.locator(".validation-summary-errors, .text-danger:visible, .alert-danger")
            if error_el.count() > 0 and error_el.first.is_visible():
                err_text = error_el.first.inner_text().strip()
                if "مسجل" in err_text and "آخر" in err_text:
                    logger.warning("Kuwait Al-Yawm: Concurrent session detected.")
                    return SessionResult(
                        success=False,
                        is_authenticated=False,
                        error_type=FailureReason.SESSION_CONFLICT,
                        portal_id=self.portal_id,
                        message="Kuwait Al-Yawm session conflict: Account already in use elsewhere. Respecting shared account."
                    )
                if err_text:
                    logger.warning("Kuwait Al-Yawm: Login rejected: %s", err_text)
                    return SessionResult(
                        success=False,
                        is_authenticated=False,
                        error_type=FailureReason.BAD_CREDENTIALS,
                        portal_id=self.portal_id,
                        message=f"Kuwait Al-Yawm credentials rejected: {err_text}"
                    )

            # Positive detection of logged-in state
            logged_in_signals = [
                page.locator("a[href*='/online/MyProfile'], a:has-text('بياناتي')").count() > 0,
                page.locator("a[href*='/Account/LogOff'], a[href*='/Logout']").count() > 0,
                page.locator(".subscriber-info, .user-name").count() > 0,
                page.locator('form[action*="LoginOnline"] input#UserName').count() == 0
            ]
            if any(logged_in_signals):
                logger.info("Kuwait Al-Yawm: Positive login confirmation detected.")
                self.is_logged_in = True
                return SessionResult(
                    success=True,
                    is_authenticated=True,
                    portal_id=self.portal_id,
                    message="Authenticated successfully with Kuwait Al-Yawm"
                )

            return SessionResult(
                success=True,
                is_authenticated=False,
                portal_id=self.portal_id,
                message="Session initialized in unauthenticated/public mode"
            )

        except PlaywrightTimeoutError:
            screenshot = self.capture_challenge_screenshot("timeout")
            return SessionResult(
                success=False,
                is_authenticated=False,
                error_type=FailureReason.SITE_DOWN,
                portal_id=self.portal_id,
                message=f"Kuwait Al-Yawm timeout during login. Screenshot: {screenshot}"
            )
        except Exception as e:
            logger.error("Kuwait Al-Yawm login failed: %s", e)
            return SessionResult(
                success=False,
                is_authenticated=False,
                error_type=FailureReason.UNKNOWN,
                portal_id=self.portal_id,
                message=f"Unexpected error on Kuwait Al-Yawm: {str(e)}"
            )

    def _check_challenges(self, page) -> bool:
        """Inspects DOM for anti-bot challenges."""
        signals = [
            page.locator("iframe[src*='recaptcha'], .g-recaptcha").count() > 0,
            page.locator("iframe[src*='cloudflare'], .cf-turnstile").count() > 0,
        ]
        return any(signals)

    def list_notices(self, since: date) -> Iterator[NoticeRef]:
        """
        Collects notice references from Kuwait Al-Yawm.
        Uses authenticated subscriber search for rich metadata and download links.
        Falls back to category public readers if unauthenticated.
        """
        page = self.init_browser()
        max_pages = self.config.rate_limiting.max_pages_per_run

        if self.is_logged_in:
            logger.info("Kuwait Al-Yawm: Using subscriber search portal for full details...")
            categories = [
                ("18", "ممارسات", "practice"),
                ("1", "مناقصات", "tender")
            ]

            for cat_id, cat_name, cat_type in categories:
                logger.info("Kuwait Al-Yawm: Searching Category %s (%s)...", cat_id, cat_name)
                try:
                    search_url = "https://kuwaitalyawm.media.gov.kw/search/customindex?dlg=1"
                    page.goto(search_url, wait_until="networkidle", timeout=35000)
                    self.polite_delay()

                    # Select Category
                    cat_select = page.locator("select#AdsCategoriesID, select[name*='AdsCategoriesID']").first
                    if cat_select.count() > 0:
                        cat_select.select_option(cat_id)
                        self.polite_delay()

                    # Submit search form
                    submit_search = page.locator("form[action*='/search/Get'] button[type='submit'], form[action*='/search/Get'] input[type='submit'], button:has-text('بحث')").first
                    if submit_search.count() > 0:
                        submit_search.click()
                        page.wait_for_load_state("networkidle", timeout=25000)
                        self.polite_delay()

                    # Set 100 rows per page to minimize pagination requests
                    try:
                        len_select = page.locator("select[name*='length']")
                        if len_select.count() > 0:
                            len_select.first.select_option("100")
                            page.wait_for_load_state("networkidle", timeout=10000)
                            self.polite_delay()
                    except Exception:
                        pass

                    current_page = 1
                    while current_page <= max_pages:
                        page.wait_for_selector("table tbody tr", timeout=15000)
                        rows = page.locator("table tbody tr")
                        count = rows.count()
                        logger.info("Kuwait Al-Yawm Cat %s: Found %d notices on page %d", cat_id, count, current_page)

                        page_refs = []
                        for i in range(count):
                            row = rows.nth(i)
                            cells = row.locator("td")
                            if cells.count() < 4:
                                continue

                            tender_no = cells.nth(0).inner_text().strip()
                            if not tender_no or tender_no in ("العنوان", "عنوان المعاملة", "لا توجد بيانات متاحة في الجدول"):
                                continue

                            issue_no = cells.nth(1).inner_text().strip() if cells.count() > 1 else ""
                            client_raw = cells.nth(3).inner_text().strip() if cells.count() > 3 else ""
                            notice_type_raw = cells.nth(4).inner_text().strip() if cells.count() > 4 else cat_name
                            pub_date = cells.nth(5).inner_text().strip() if cells.count() > 5 else ""

                            # Extract Links
                            dl_link = row.locator("a[href*='DownloadPDF']").first
                            html_link = row.locator("a[href*='ViewAdsHTML']").first
                            flip_link = row.locator("a[data-load-url], a.flip").first

                            dl_url = dl_link.get_attribute("href") if dl_link.count() > 0 else None
                            html_url = html_link.get_attribute("href") if html_link.count() > 0 else None
                            flip_url = flip_link.get_attribute("data-load-url") if flip_link.count() > 0 else None

                            ads_id = None
                            if dl_url:
                                m = re.search(r"AdsID=(\d+)", dl_url, re.IGNORECASE)
                                if m:
                                    ads_id = m.group(1)
                            elif html_url:
                                m = re.search(r"id=(\d+)", html_url, re.IGNORECASE)
                                if m:
                                    ads_id = m.group(1)

                            detail_url = urljoin("https://kuwaitalyawm.media.gov.kw", html_url or dl_url or flip_url or search_url)

                            page_refs.append(NoticeRef(
                                portal_id=self.portal_id,
                                tender_no_raw=tender_no,
                                detail_url=detail_url,
                                issue_no=issue_no,
                                page_ref=None,
                                publish_date_hint=pub_date,
                                client_hint=client_raw,
                                notice_type_hint=notice_type_raw,
                                download_url=dl_url,
                                html_url=html_url,
                                ads_id=ads_id
                            ))

                        for ref in page_refs:
                            yield ref

                        # Pagination
                        next_btn = page.locator(".dataTables_paginate a.next, .paginate_button.next, a:has-text('التالي')").first
                        if next_btn.count() > 0 and next_btn.is_visible() and "disabled" not in (next_btn.get_attribute("class") or ""):
                            logger.info("Kuwait Al-Yawm: Paginating to page %d...", current_page + 1)
                            self.polite_delay()
                            next_btn.click()
                            page.wait_for_load_state("networkidle", timeout=20000)
                            current_page += 1
                        else:
                            break

                except Exception as e:
                    logger.error("Error searching Kuwait Al-Yawm Category %s: %s", cat_id, e)

        else:
            # Fallback public reader mode
            categories_public = [
                ("18", "https://kuwaitalyawm.media.gov.kw/online/AdsCategory/18"),
                ("1", "https://kuwaitalyawm.media.gov.kw/online/AdsCategory/1")
            ]
            for cat_id, cat_url in categories_public:
                logger.info("Kuwait Al-Yawm Public: Loading notices from category %s...", cat_id)
                page.goto(cat_url, wait_until="networkidle", timeout=45000)
                self.polite_delay()

                current_page = 1
                while current_page <= max_pages:
                    page.wait_for_selector("table tbody tr", timeout=15000)
                    rows = page.locator("table tbody tr")
                    count = rows.count()
                    for i in range(count):
                        row = rows.nth(i)
                        cells = row.locator("td")
                        if cells.count() < 5:
                            continue
                        tender_no = cells.nth(0).inner_text().strip()
                        if not tender_no or tender_no == "العنوان":
                            continue

                        flip_link = row.locator("a[data-load-url], a.flip").first
                        data_load_url = flip_link.get_attribute("data-load-url") if flip_link.count() > 0 else ""
                        issue_no = cells.nth(2).inner_text().strip() if cells.count() > 2 else ""
                        pub_date_greg = cells.nth(4).inner_text().strip() if cells.count() > 4 else ""

                        full_detail_url = urljoin("https://kuwaitalyawm.media.gov.kw", data_load_url) if data_load_url else cat_url

                        yield NoticeRef(
                            portal_id=self.portal_id,
                            tender_no_raw=tender_no,
                            detail_url=full_detail_url,
                            issue_no=issue_no,
                            page_ref=None,
                            publish_date_hint=pub_date_greg,
                            client_hint=None,
                            notice_type_hint="ممارسات" if cat_id == "18" else "مناقصات"
                        )

                    next_btn = page.locator(".dataTables_paginate a.next, ul.pagination li.next a, a:has-text('التالي')").first
                    if next_btn.count() > 0 and next_btn.is_visible() and "disabled" not in (next_btn.get_attribute("class") or ""):
                        self.polite_delay()
                        next_btn.click()
                        page.wait_for_load_state("networkidle", timeout=25000)
                        current_page += 1
                    else:
                        break

    def fetch_detail(self, ref: NoticeRef) -> RawNotice:
        """
        Extracts tender notice announcement content, downloads official PDF,
        and parses rich details (Client, Exact Subject, Requirements, Closing Date, Fees, Guarantees).
        Strictly rejects any 'LOADING PAGES' or placeholder text.
        """
        announcement_content = ""
        extracted_title = None
        extracted_closing_date = None
        extracted_pre_bid = None
        extracted_fee = None
        extracted_bond = None
        extracted_reqs: List[str] = []
        attachments: List[Dict[str, Any]] = []

        # 1. Download official Gazette PDF announcement if available
        if ref.download_url and self._context:
            try:
                full_dl_url = urljoin("https://kuwaitalyawm.media.gov.kw", ref.download_url)
                logger.info("Kuwait Al-Yawm: Downloading PDF for %s...", ref.tender_no_raw)
                res_pdf = self._context.request.get(full_dl_url)
                # Note: Reject 33805-byte warning PDF ("يرجى تحميل الملف من الموقع مباشرة")
                if res_pdf.status == 200 and len(res_pdf.body()) > 500 and len(res_pdf.body()) != 33805:
                    safe_no = re.sub(r"[^\w\-.]", "_", ref.tender_no_raw)
                    pdf_filename = f"ads_{ref.ads_id or safe_no}.pdf"
                    pdf_path = self.attachments_dir / pdf_filename
                    with open(pdf_path, "wb") as f:
                        f.write(res_pdf.body())
                    
                    attachments.append({
                        "filename": pdf_filename,
                        "path": str(pdf_path),
                        "size_bytes": len(res_pdf.body()),
                        "mime_type": "application/pdf"
                    })
                    logger.info("Kuwait Al-Yawm: Saved PDF (%d bytes) to %s", len(res_pdf.body()), pdf_path)
            except Exception as e:
                logger.debug("Kuwait Al-Yawm: Could not download PDF for %s: %s", ref.tender_no_raw, e)

        # 2. Fetch ViewAdsHTML for rich announcement text
        if ref.html_url and self._context:
            try:
                full_html_url = urljoin("https://kuwaitalyawm.media.gov.kw", ref.html_url)
                res_html = self._context.request.get(full_html_url)
                if res_html.status == 200:
                    parsed = self._parse_announcement_html(res_html.text())
                    announcement_content = parsed["full_text"]
                    extracted_title = parsed["title"]
                    extracted_closing_date = parsed["closing_date"]
                    extracted_pre_bid = parsed["pre_bid_date"]
                    extracted_fee = str(parsed["fee"]) if parsed["fee"] is not None else None
                    extracted_bond = str(parsed["bond"]) if parsed["bond"] is not None else None
                    extracted_reqs = parsed["requirements"]
            except Exception as e:
                logger.debug("Kuwait Al-Yawm: Could not fetch ViewAdsHTML for %s: %s", ref.tender_no_raw, e)

        # Clean any accidental 'LOADING PAGES' placeholder text
        if announcement_content and ("LOADING PAGES" in announcement_content or "LOADING" in announcement_content):
            announcement_content = ""

        # Parse publication date (format DD/MM/YYYY)
        pub_iso = None
        if ref.publish_date_hint:
            try:
                clean_date = re.sub(r"^[A-Za-z]+\s+", "", ref.publish_date_hint.strip())
                parts = clean_date.split("/")
                if len(parts) == 3:
                    pub_iso = f"{parts[2]}-{parts[1]}-{parts[0]}"
            except Exception:
                pub_iso = ref.publish_date_hint

        # Client detection: prefer explicit client from subscriber table
        client_detected = ref.client_hint or None
        t_upper = ref.tender_no_raw.upper()
        notice_type = "practice" if ("ممارس" in (ref.notice_type_hint or "") or "RFQ" in t_upper or "RFP" in t_upper) else "tender"

        if not client_detected:
            if "RFQ" in t_upper or "RFP" in t_upper or "P&MAB" in t_upper or "P&M" in t_upper:
                client_detected = "شركة البترول الوطنية الكويتية"

        # Build clean title display
        type_prefix = "ممارسة" if notice_type == "practice" else "مناقصة"
        if extracted_title and "LOADING" not in extracted_title:
            title_display = f"{type_prefix} رقم {ref.tender_no_raw}: {extracted_title}"
        elif client_detected == "شركة البترول الوطنية الكويتية" and ("RFQ" in t_upper or "RFP" in t_upper):
            title_display = f"طلب عروض أسعار رقم {ref.tender_no_raw} - شركة البترول الوطنية الكويتية (العدد {ref.issue_no or ''})"
        elif client_detected:
            title_display = f"{type_prefix} رقم {ref.tender_no_raw} - {client_detected} (العدد {ref.issue_no or ''})"
        else:
            title_display = f"{type_prefix} رقم {ref.tender_no_raw} - الجريدة الرسمية (العدد {ref.issue_no or ''})"

        return RawNotice(
            portal_id=self.portal_id,
            tender_no=ref.tender_no_raw,
            title_raw=title_display,
            client_raw=client_detected,
            publish_date_raw=pub_iso or ref.publish_date_hint,
            closing_date_raw=extracted_closing_date,
            pre_bid_raw=extracted_pre_bid,
            notice_type_raw=notice_type,
            bid_bond_raw=extracted_bond,
            document_fee_raw=extracted_fee,
            attachments=attachments,
            extra_fields={
                "issue_no": ref.issue_no,
                "page_no": ref.page_ref,
                "ads_id": ref.ads_id,
                "requirements": extracted_reqs,
                "announcement_snippet": announcement_content[:1500] if announcement_content else "",
                "download_url": ref.download_url,
                "html_url": ref.html_url
            },
            source_url=ref.detail_url
        )

    def _parse_announcement_html(self, html_text: str) -> Dict[str, Any]:
        """
        Parses announcement HTML into structured subject, requirements, closing date,
        pre-bid date, fees, and bond. Handles both prose and embedded HTML tables.
        """
        ext = HTMLTextExtractor()
        ext.feed(html_text)
        raw = html.unescape(ext.get_text())
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        full_text = "\n".join(lines)

        subject = None

        # Strategy 1: Look for line immediately following tender number
        for i, line in enumerate(lines):
            clean_l = line.strip()
            if re.search(r"^(?:الممارسة|المناقصة)\s*(?:رقم|رقـم)\s*:", clean_l):
                if i + 1 < len(lines):
                    next_l = lines[i + 1].strip()
                    if not next_l.startswith("تعلن") and not next_l.startswith("إع") and len(next_l) > 8:
                        subject = next_l
                        break

        # Strategy 2: Keyword search for action phrases in early lines
        if not subject:
            subject_keywords = [
                "توريد", "خوادم", "أجهزة", "نظام", "أنظمة", "برمجيات", "برامج", "شبكات",
                "صيانة", "أعمال", "مشروع", "تقديم", "تطوير", "شراء", "إنشاء", "إعداد",
                "تفعيل", "استئجار", "نظافة", "حراسة", "أمن", "تراخيص", "كيبلات", "حاجة", "بشأن"
            ]
            for line in lines[:10]:
                clean_l = line.strip()
                if re.search(r"^(?:وزارة|الهيئة|بلدية|مجلس|ديوان|إدارة|مؤسسة|شركة|جامعة|الرئاسة|إعلان|تنويه|الممارسة|المناقصة)\b", clean_l) and len(clean_l) < 45:
                    continue
                if clean_l.startswith("تعلن") or "المذكورة أعلاه" in clean_l:
                    continue
                if any(kw in clean_l for kw in subject_keywords) and len(clean_l) > 10:
                    subject = clean_l
                    break

        # Clean subject prefixes
        if subject:
            subject = re.sub(r"^(?:لطلب|بشأن|عن|موضوع الممارسة|موضوع المناقصة)\s*:\s*", "", subject).strip()
            if subject.startswith("لطلب "):
                subject = subject[5:].strip()

        # Strategy 3: Extract Requirements
        requirements = []
        in_reqs = False
        for line in lines:
            clean_l = line.strip()
            if any(w in clean_l for w in ["ويشترط", "الشروط المطلوبة", "المستندات المطلوبة", "إرشادات عامة", "شروط المشاركة"]):
                in_reqs = True
                continue
            if in_reqs:
                if clean_l.startswith("للاستفسار") or "هاتف:" in clean_l or len(clean_l) > 300:
                    in_reqs = False
                    continue
                if len(clean_l) > 12:
                    requirements.append(clean_l)

        # Strategy 4: Table parsing for structured dates and money
        tbl_extractor = TableExtractor()
        tbl_extractor.feed(html_text)

        closing_date = None
        publish_date = None
        pre_bid_date = None
        fee = None
        bond = None

        for tbl in tbl_extractor.tables:
            if len(tbl) >= 2:
                headers = tbl[0]
                values = tbl[1]
                for h, v in zip(headers, values):
                    clean_h = h.replace("\n", " ").strip()
                    clean_v = v.replace("\n", " ").strip()

                    m_date = re.search(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})", clean_v)
                    date_val = m_date.group(1) if m_date else None

                    nums = re.findall(r"[\d,]+(?:\.\d+)?", clean_v)
                    money_val = None
                    if nums:
                        try:
                            money_val = float(nums[0].replace(",", ""))
                        except ValueError:
                            pass

                    if "إغلاق" in clean_h or "إقفال" in clean_h or "تقديم" in clean_h:
                        if date_val: closing_date = date_val
                    elif "طرح" in clean_h or "نشر" in clean_h:
                        if date_val: publish_date = date_val
                    elif "تمهيدي" in clean_h:
                        if date_val: pre_bid_date = date_val
                    elif "تأمين" in clean_h or "كفالة" in clean_h or "ضمان" in clean_h:
                        if money_val: bond = money_val
                    elif "مقابل" in clean_h or "رسوم" in clean_h or "كراسة" in clean_h or "سعر" in clean_h:
                        if money_val: fee = money_val

        # Prose regex fallback for dates if table not found
        if not closing_date:
            m_close = re.search(r"(?:تاريخ الإغلاق|موعد الإغلاق|آخر موعد|اخر موعد|تاريخ الإقفال)[^\d]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})", full_text)
            if m_close:
                closing_date = m_close.group(1)

        if not pre_bid_date:
            m_pre = re.search(r"(?:الاجتماع التمهيدي|اجتماع تمهيدي)[^\d]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})", full_text)
            if m_pre:
                pre_bid_date = m_pre.group(1)

        if fee is None or bond is None:
            money_matches = re.findall(r"\(?\-?\/?\s*([\d,]+(?:\.\d+)?)\s*\)?\s*(?:د\.ك|دينار|KD)", full_text)
            for m in money_matches:
                try:
                    val = float(m.replace(",", ""))
                    if val <= 300 and fee is None:
                        fee = val
                    elif val > 300 and bond is None:
                        bond = val
                except ValueError:
                    pass

        return {
            "title": subject,
            "requirements": requirements,
            "closing_date": closing_date,
            "publish_date": publish_date,
            "pre_bid_date": pre_bid_date,
            "fee": fee,
            "bond": bond,
            "full_text": full_text
        }

    def logout(self) -> None:
        """Performs clean logout to release shared subscriber sessions."""
        if not self._page or not self.is_logged_in:
            return
        try:
            logger.info("Kuwait Al-Yawm: Logging out cleanly...")
            self._page.goto("https://kuwaitalyawm.media.gov.kw/Account/LogOffOnline", wait_until="networkidle", timeout=15000)
            self.is_logged_in = False
            logger.info("Kuwait Al-Yawm: Clean logout complete.")
        except Exception as e:
            logger.warning("Kuwait Al-Yawm: Logout notice: %s", e)
