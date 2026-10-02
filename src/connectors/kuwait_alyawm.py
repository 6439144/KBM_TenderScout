"""
Kuwait Al-Yawm (Official Gazette) Connector.
Implements authentication, category scraping, flip viewer extraction, and polite session management.
"""

import logging
import re
from datetime import date, datetime
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urljoin
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.config import PortalConfig
from src.connectors.base import PortalConnector
from src.models import FailureReason, NoticeRef, RawNotice, SessionResult
from src.utils.secrets import SecretManager

logger = logging.getLogger("kbm.connectors.kuwait_alyawm")

class KuwaitAlyawmConnector(PortalConnector):
    """Connector for the Kuwait Al-Yawm Official Gazette portal (kuwaitalyawm.media.gov.kw)."""

    def __init__(self, config: PortalConfig):
        super().__init__(config, portal_id="kuwait_alyawm")

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
            user_input = page.locator('input#UserName, input[name="UserName"]').first
            pass_input = page.locator('input#Password, input[name="Password"]').first
            submit_btn = page.locator('form[action*="LoginOnline"] input[type="submit"], button[type="submit"]').first

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
            error_el = page.locator(".validation-summary-errors, .text-danger:visible")
            if error_el.count() > 0:
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
                page.locator("a[href*='/Account/LogOff'], a[href*='/Logout']").count() > 0,
                page.locator(".subscriber-info, .user-name").count() > 0,
                page.locator('input#UserName').count() == 0
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
        """Collects notice references from Kuwait Al-Yawm Category 1 (Tenders) and 18 (Practices)."""
        page = self.init_browser()
        categories = [
            ("1", "https://kuwaitalyawm.media.gov.kw/online/AdsCategory/1"),
            ("18", "https://kuwaitalyawm.media.gov.kw/online/AdsCategory/18")
        ]

        max_pages = self.config.rate_limiting.max_pages_per_run

        for cat_id, cat_url in categories:
            logger.info("Kuwait Al-Yawm: Loading notices from category %s (%s)...", cat_id, cat_url)
            page.goto(cat_url, wait_until="networkidle", timeout=45000)
            self.polite_delay()

            # Set length dropdown to 100 entries if present to minimize paging round trips
            try:
                length_select = page.locator("select[name*='length']")
                if length_select.count() > 0:
                    length_select.select_option("100")
                    page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass

            current_page = 1
            while current_page <= max_pages:
                logger.info("Kuwait Al-Yawm Cat %s: Scraping page %d...", cat_id, current_page)
                page.wait_for_selector("table tbody tr", timeout=15000)
                rows = page.locator("table tbody tr")
                count = rows.count()
                logger.info("Kuwait Al-Yawm Cat %s: Found %d table rows on page %d", cat_id, count, current_page)

                for i in range(count):
                    row = rows.nth(i)
                    cells = row.locator("td")
                    if cells.count() < 5:
                        continue

                    tender_no = cells.nth(0).inner_text().strip()
                    if not tender_no or tender_no == "العنوان":
                        continue

                    # Extract flip URL if document icon present
                    flip_link = row.locator("a[data-load-url], a.flip").first
                    data_load_url = flip_link.get_attribute("data-load-url") if flip_link.count() > 0 else ""

                    issue_no = cells.nth(2).inner_text().strip() if cells.count() > 2 else ""
                    pub_date_greg = cells.nth(4).inner_text().strip() if cells.count() > 4 else ""

                    # Parse page reference from data-load-url e.g. /flip/index?id=5599&no=238
                    page_no = None
                    if data_load_url:
                        m = re.search(r"no=(\d+)", data_load_url)
                        if m:
                            page_no = m.group(1)

                    full_detail_url = urljoin("https://kuwaitalyawm.media.gov.kw", data_load_url) if data_load_url else cat_url

                    yield NoticeRef(
                        portal_id=self.portal_id,
                        tender_no_raw=tender_no,
                        detail_url=full_detail_url,
                        issue_no=issue_no,
                        page_ref=page_no,
                        publish_date_hint=pub_date_greg
                    )

                # Pagination handling
                next_btn = page.locator(".dataTables_paginate a.next, ul.pagination li.next a, a:has-text('التالي')").first
                if next_btn.count() > 0 and next_btn.is_visible() and "disabled" not in (next_btn.get_attribute("class") or ""):
                    logger.info("Kuwait Al-Yawm: Navigating to page %d...", current_page + 1)
                    self.polite_delay()
                    next_btn.click()
                    page.wait_for_load_state("networkidle", timeout=25000)
                    current_page += 1
                else:
                    logger.info("Kuwait Al-Yawm: Reached last page for category %s.", cat_id)
                    break

    def fetch_detail(self, ref: NoticeRef) -> RawNotice:
        """
        Extracts tender notice announcement content.
        Uses flip viewer content if authenticated, or structured table metadata.
        """
        page = self.init_browser()
        full_text = ""
        announcement_content = ""

        # If data-load-url flip viewer is available, attempt to load announcement page
        if "/flip/index" in ref.detail_url:
            try:
                page.goto(ref.detail_url, wait_until="networkidle", timeout=25000)
                page_body = page.locator("body").inner_text()
                
                # Check subscriber restriction
                if "خدمة تصفح الإصدار متاحة فقط للمشتركين" in page_body:
                    logger.debug("Kuwait Al-Yawm: Flip page locked behind subscriber gate. Using table metadata.")
                else:
                    announcement_content = page_body.strip()
            except Exception as e:
                logger.debug("Could not load flip viewer for %s: %s", ref.tender_no_raw, e)

        # Parse date from hint (format DD/MM/YYYY)
        pub_iso = None
        if ref.publish_date_hint:
            try:
                parts = ref.publish_date_hint.split("/")
                if len(parts) == 3:
                    pub_iso = f"{parts[2]}-{parts[1]}-{parts[0]}"
            except Exception:
                pub_iso = ref.publish_date_hint

        return RawNotice(
            portal_id=self.portal_id,
            tender_no=ref.tender_no_raw,
            title_raw=announcement_content[:200] if announcement_content else f"مناقصة رقم {ref.tender_no_raw} - الجريدة الرسمية",
            client_raw=None, # Client determined during normalization or from full announcement
            publish_date_raw=pub_iso or ref.publish_date_hint,
            closing_date_raw=None,
            pre_bid_raw=None,
            notice_type_raw="tender",
            attachments=[],
            extra_fields={
                "issue_no": ref.issue_no,
                "page_no": ref.page_ref,
                "announcement_snippet": announcement_content[:500] if announcement_content else ""
            },
            source_url=ref.detail_url
        )

    def logout(self) -> None:
        """Performs clean logout to release shared subscriber sessions."""
        if not self._page or not self.is_logged_in:
            return
        try:
            logger.info("Kuwait Al-Yawm: Logging out cleanly...")
            self._page.goto("https://kuwaitalyawm.media.gov.kw/Account/LogOff", wait_until="networkidle", timeout=15000)
            self.is_logged_in = False
            logger.info("Kuwait Al-Yawm: Clean logout complete.")
        except Exception as e:
            logger.warning("Kuwait Al-Yawm: Logout notice: %s", e)
