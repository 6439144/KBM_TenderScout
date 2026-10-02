"""
Base Connector Framework for KBM Tender Scout.
Defines PortalConnector protocol, politeness throttling, redaction, and failure handling.
"""

import time
import random
import logging
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import Iterator, Optional
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from src.config import PortalConfig
from src.models import FailureReason, NoticeRef, RawNotice, SessionResult
from src.utils.secrets import SecretManager

logger = logging.getLogger("kbm.connectors")

class PortalConnector(ABC):
    """Abstract base connector for Kuwait tender portals."""

    def __init__(self, config: PortalConfig, portal_id: str):
        self.config = config
        self.portal_id = portal_id
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self.is_logged_in: bool = False

    def init_browser(self) -> Page:
        """Launches Chromium context with polite headers and configured timeout."""
        if not self._page:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self.config.browser.headless,
                args=["--ignore-certificate-errors"]
            )
            self._context = self._browser.new_context(
                ignore_https_errors=True,
                viewport={"width": 1440, "height": 900},
                user_agent=self.config.browser.user_agent
            )
            self._page = self._context.new_page()
            self._page.set_default_timeout(self.config.browser.timeout_ms)
        return self._page

    def polite_delay(self) -> None:
        """Applies randomized polite access delay (Rule 3.4)."""
        min_d = self.config.rate_limiting.min_delay_seconds
        max_d = self.config.rate_limiting.max_delay_seconds
        delay = random.uniform(min_d, max_d)
        time.sleep(delay)

    def capture_challenge_screenshot(self, name_prefix: str = "challenge") -> Path:
        """Saves a screenshot when a challenge or error occurs with redaction (Rule 3.7)."""
        screenshots_dir = Path("logs/screenshots")
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        screenshot_path = screenshots_dir / f"{self.portal_id}_{name_prefix}_{ts}.png"
        
        if self._page:
            try:
                # Mask sensitive input fields if on login screen
                self._page.evaluate("""
                    () => {
                        const inputs = document.querySelectorAll('input[type="password"], input[name*="user"], input[name*="email"]');
                        inputs.forEach(el => { el.value = '***REDACTED***'; });
                    }
                """)
                self._page.screenshot(path=str(screenshot_path), full_page=False)
            except Exception as e:
                logger.warning("Could not capture challenge screenshot: %s", e)
        return screenshot_path

    @abstractmethod
    def login(self) -> SessionResult:
        """Authenticates with the portal using runtime secrets."""
        pass

    @abstractmethod
    def list_notices(self, since: date) -> Iterator[NoticeRef]:
        """Lists tender notice references published since the given date."""
        pass

    @abstractmethod
    def fetch_detail(self, ref: NoticeRef) -> RawNotice:
        """Fetches complete notice details for a given notice reference."""
        pass

    @abstractmethod
    def logout(self) -> None:
        """Performs clean logout to release shared staff sessions."""
        pass

    def close(self) -> None:
        """Closes browser session and releases resources."""
        try:
            if self.is_logged_in:
                self.logout()
        except Exception as e:
            logger.warning("Error during logout on close: %s", e)

        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.warning("Error closing browser resources: %s", e)
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            self.is_logged_in = False
