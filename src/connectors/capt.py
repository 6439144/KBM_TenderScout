"""
CAPT (Central Agency for Public Tenders) Connector.
Implements authentication, polite listing, and field extraction as approved in PORTAL_MAP_capt.md.
"""

import logging
import re
from datetime import date, datetime
from typing import Any, Dict, Iterator, List, Optional
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.config import PortalConfig
from src.connectors.base import PortalConnector
from src.models import FailureReason, NoticeRef, RawNotice, SessionResult
from src.utils.secrets import SecretManager

logger = logging.getLogger("kbm.connectors.capt")

class CaptConnector(PortalConnector):
    """Connector for the Kuwait Central Agency for Public Tenders (capt.gov.kw)."""

    def __init__(self, config: PortalConfig):
        super().__init__(config, portal_id="capt")

    def login(self) -> SessionResult:
        """Authenticates with CAPT account or proceeds in public reading mode."""
        username = SecretManager.get_secret(self.config.auth.username_secret)
        password = SecretManager.get_secret(self.config.auth.password_secret)

        if not username or not password:
            logger.info("CAPT: No credentials provided in environment. Proceeding in public reader mode.")
            return SessionResult(
                success=True,
                is_authenticated=False,
                portal_id=self.portal_id,
                message="Running in public reader mode (no credentials provided)"
            )

        page = self.init_browser()
        try:
            logger.info("CAPT: Navigating to landing page for login...")
            page.goto(self.config.base_url, wait_until="networkidle", timeout=35000)
            self.polite_delay()

            # Check for bot challenge immediately
            if self._check_challenges(page):
                screenshot = self.capture_challenge_screenshot("login_challenge")
                return SessionResult(
                    success=False,
                    is_authenticated=False,
                    error_type=FailureReason.CHALLENGE,
                    portal_id=self.portal_id,
                    message=f"Bot challenge or CAPTCHA encountered on CAPT. Redacted screenshot: {screenshot}"
                )

            # Trigger login modal
            login_trigger = page.locator("a.user-login, a.log-in").first
            if login_trigger.count() > 0 and login_trigger.is_visible():
                login_trigger.click()
                page.wait_for_selector("#loginForm", state="visible", timeout=10000)
            elif page.locator("#loginForm").count() == 0:
                # Try direct company rules page which embeds login
                page.goto("https://capt.gov.kw/ar/company/rules/", wait_until="networkidle", timeout=20000)

            # Check if login form is present
            login_form = page.locator("#loginForm")
            if login_form.count() == 0:
                screenshot = self.capture_challenge_screenshot("missing_login_form")
                return SessionResult(
                    success=False,
                    is_authenticated=False,
                    error_type=FailureReason.LAYOUT_CHANGED,
                    portal_id=self.portal_id,
                    message=f"Login form not found on CAPT. Layout may have changed. Screenshot: {screenshot}"
                )

            # Fill credentials (values never logged)
            user_input = login_form.locator('input[name="username"]')
            pass_input = login_form.locator('input[name="password"]')
            submit_btn = login_form.locator('button.btnLogin, button[type="submit"]')

            user_input.fill(username)
            pass_input.fill(password)
            self.polite_delay()

            submit_btn.click()
            page.wait_for_load_state("networkidle", timeout=20000)
            self.polite_delay()

            # Check for error messages
            error_el = page.locator("ul.loginErrors, .loginErrors, .popupText")
            if error_el.count() > 0 and error_el.first.is_visible():
                err_text = error_el.first.inner_text().strip()
                if "مسجل دخول بالفعل" in err_text or "already logged in" in err_text.lower():
                    logger.warning("CAPT: Concurrent session detected.")
                    return SessionResult(
                        success=False,
                        is_authenticated=False,
                        error_type=FailureReason.SESSION_CONFLICT,
                        portal_id=self.portal_id,
                        message="CAPT login blocked: Concurrent session already active. Respecting shared account."
                    )
                if err_text:
                    logger.warning("CAPT: Login rejected with error: %s", err_text)
                    return SessionResult(
                        success=False,
                        is_authenticated=False,
                        error_type=FailureReason.BAD_CREDENTIALS,
                        portal_id=self.portal_id,
                        message=f"CAPT rejected credentials: {err_text}"
                    )

            # Positive detection of logged in session
            logged_in_signals = [
                page.locator("a[href*='/logout/']").count() > 0,
                page.locator(".user-profile, .profile-name").count() > 0,
                page.locator("a.user-login").count() == 0
            ]
            if any(logged_in_signals):
                logger.info("CAPT: Positive login confirmation detected.")
                self.is_logged_in = True
                return SessionResult(
                    success=True,
                    is_authenticated=True,
                    portal_id=self.portal_id,
                    message="Authenticated successfully with CAPT"
                )

            # If not detected positively, verify state
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
                message=f"CAPT timeout during login. Screenshot: {screenshot}"
            )
        except Exception as e:
            logger.error("CAPT login failed with unexpected exception: %s", e)
            return SessionResult(
                success=False,
                is_authenticated=False,
                error_type=FailureReason.UNKNOWN,
                portal_id=self.portal_id,
                message=f"Unexpected error on CAPT: {str(e)}"
            )

    def _check_challenges(self, page) -> bool:
        """Inspects DOM for known anti-bot / captcha challenges."""
        signals = [
            page.locator("iframe[src*='recaptcha'], .g-recaptcha").count() > 0,
            page.locator("iframe[src*='cloudflare'], .cf-turnstile").count() > 0,
            page.locator("iframe[src*='hcaptcha'], .h-captcha").count() > 0,
            "Attention Required! | Cloudflare" in page.title()
        ]
        return any(signals)

    def list_notices(self, since: date) -> Iterator[NoticeRef]:
        """Collects notice references from CAPT open tenders listing."""
        page = self.init_browser()
        tenders_url = "https://capt.gov.kw/ar/tenders/opening-tenders/"
        logger.info("CAPT: Loading tenders list from %s", tenders_url)
        page.goto(tenders_url, wait_until="networkidle", timeout=45000)
        self.polite_delay()

        max_pages = self.config.rate_limiting.max_pages_per_run
        current_page = 1

        while current_page <= max_pages:
            logger.info("CAPT: Scraping page %d of tenders list...", current_page)
            # Find all tender card elements
            cards = page.locator(".endless_page_template .page-width.detail-list, .detail-list")
            count = cards.count()
            logger.info("CAPT: Found %d tender cards on page %d", count, current_page)

            for i in range(count):
                card = cards.nth(i)
                text = card.inner_text()
                
                # Extract tender number
                tender_no = self._extract_field(text, r"الرقم\s*([^\n\r]+)")
                if not tender_no:
                    continue

                pub_date_str = self._extract_field(text, r"تاريخ الطلب\s*([^\n\r]+)")
                
                yield NoticeRef(
                    portal_id=self.portal_id,
                    tender_no_raw=tender_no.strip(),
                    detail_url=f"{tenders_url}#card-{i}",
                    publish_date_hint=pub_date_str
                )

            # Pagination handling
            current_page += 1
            if current_page <= max_pages:
                logger.info("CAPT: Moving to page %d via direct URL...", current_page)
                self.polite_delay()
                page.goto(f"{tenders_url}?page={current_page}", wait_until="networkidle", timeout=30000)
                # Check if new cards exist on this page
                if page.locator(".detail-list").count() == 0:
                    logger.info("CAPT: No more cards found on page %d. Ending listing.", current_page)
                    break
            else:
                break

    def fetch_detail(self, ref: NoticeRef) -> RawNotice:
        """
        Extracts structured raw tender fields from the tender card or detail page.
        Never executes any form of purchase (Rule 3.2).
        """
        page = self.init_browser()
        card_text = ""

        # Locate the card matching tender_no on the current page
        target_card = page.locator(f".detail-list:has-text('{ref.tender_no_raw}')")
        if target_card.count() > 0:
            card_text = target_card.first.inner_text()
        else:
            # Fallback to ref detail URL if direct link
            if not ref.detail_url.startswith("https://capt.gov.kw/ar/tenders/opening-tenders/#card-"):
                page.goto(ref.detail_url, wait_until="networkidle", timeout=30000)
                card_text = page.locator("body").inner_text()

        # Extract structured fields
        title = self._extract_field(card_text, r"الموضوع\s*([^\n\r]+)")
        client = self._extract_field(card_text, r"الجهة\s*([^\n\r]+)")
        pub_date = self._extract_field(card_text, r"تاريخ الطلب\s*([^\n\r]+)")
        closing_date = self._extract_field(card_text, r"اخر موعد للعطاء\s*([^\n\r]+)")
        pre_bid = self._extract_field(card_text, r"الاجتماع التمهيدي\s*([^\n\r]+)")
        notice_type = self._extract_field(card_text, r"النوع\s*([^\n\r]+)")
        price = self._extract_field(card_text, r"السعر\s*([^\n\r]+)")
        bond = self._extract_field(card_text, r"التأمين\s*([^\n\r]+)")

        # Collect attachments metadata only (never purchase documents)
        attachments = []
        if "كراسة الشروط" in card_text:
            attachments.append({
                "name": "كراسة الشروط",
                "fee": price,
                "url": ref.detail_url
            })

        extra_fields = {
            "alternative_bids": self._extract_field(card_text, r"العروض البديلة\s*([^\n\r]+)"),
            "divisible": self._extract_field(card_text, r"التجزئة\s*([^\n\r]+)"),
        }

        return RawNotice(
            portal_id=self.portal_id,
            tender_no=ref.tender_no_raw,
            title_raw=title or ref.tender_no_raw,
            client_raw=client,
            publish_date_raw=pub_date,
            closing_date_raw=closing_date,
            pre_bid_raw=pre_bid,
            notice_type_raw=notice_type,
            bid_bond_raw=bond,
            document_fee_raw=price,
            attachments=attachments,
            extra_fields=extra_fields,
            source_url=ref.detail_url
        )

    def logout(self) -> None:
        """Performs clean logout to release any shared session."""
        if not self._page or not self.is_logged_in:
            return
        try:
            logger.info("CAPT: Logging out cleanly...")
            self._page.goto("https://capt.gov.kw/ar/logout/", wait_until="networkidle", timeout=15000)
            self.is_logged_in = False
            logger.info("CAPT: Clean logout complete.")
        except Exception as e:
            logger.warning("CAPT: Notice during logout: %s", e)

    @staticmethod
    def _extract_field(text: str, pattern: str) -> Optional[str]:
        m = re.search(pattern, text)
        return m.group(1).strip() if m else None
