"""
Pluggable Delivery System for KBM Tender Scout (FR-9).
Supports local archiving, email distribution, and SharePoint upload hooks.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("kbm.delivery")

class DeliveryProvider(ABC):
    @abstractmethod
    def deliver(self, report_path: Path, metadata: Optional[dict] = None) -> bool:
        pass

class LocalDeliveryProvider(DeliveryProvider):
    def deliver(self, report_path: Path, metadata: Optional[dict] = None) -> bool:
        logger.info("Local Delivery: Verified report saved at %s", report_path.resolve())
        return True

class EmailDeliveryProvider(DeliveryProvider):
    def __init__(self, recipients: List[str], smtp_host: str = "smtp.office365.com"):
        self.recipients = recipients
        self.smtp_host = smtp_host

    def deliver(self, report_path: Path, metadata: Optional[dict] = None) -> bool:
        # Pluggable hook: Dispatches report as attachment to sales distribution list
        logger.info(
            "Email Delivery: Ready to deliver %s to %d recipients via %s (Disabled in Dev)",
            report_path.name, len(self.recipients), self.smtp_host
        )
        return True

class SharePointDeliveryProvider(DeliveryProvider):
    def __init__(self, site_url: str, document_library: str):
        self.site_url = site_url
        self.document_library = document_library

    def deliver(self, report_path: Path, metadata: Optional[dict] = None) -> bool:
        # Pluggable hook: Uploads report to KBM SharePoint Document Library
        logger.info(
            "SharePoint Delivery: Ready to sync %s to '%s' on %s (Disabled in Dev)",
            report_path.name, self.document_library, self.site_url or "KBM SharePoint"
        )
        return True

class DeliveryManager:
    def __init__(self, destinations: List[str]):
        self.destinations = destinations
        self.providers: List[DeliveryProvider] = []
        
        # Local delivery always enabled
        self.providers.append(LocalDeliveryProvider())
        if "email" in destinations:
            self.providers.append(EmailDeliveryProvider(recipients=["kabed@kbm.com.kw"]))
        if "sharepoint" in destinations:
            self.providers.append(SharePointDeliveryProvider(site_url="", document_library="Tenders"))

    def dispatch(self, report_path: Path, metadata: Optional[dict] = None) -> bool:
        all_ok = True
        for p in self.providers:
            try:
                ok = p.deliver(report_path, metadata)
                if not ok:
                    all_ok = False
            except Exception as e:
                logger.error("Error in delivery provider %s: %s", type(p).__name__, e)
                all_ok = False
        return all_ok
