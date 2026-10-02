"""
Alert and Notification Engine for KBM Tender Scout (FR-10).
Dispatches operator alerts on CHALLENGE, SESSION_CONFLICT, or portal failure, and posts daily summaries.
"""

import logging
from typing import Any, Dict, List, Optional
from src.models import FailureReason

logger = logging.getLogger("kbm.notify")

class NotificationManager:
    def __init__(self, recipients: List[str], channels: Optional[List[str]] = None):
        self.recipients = recipients
        self.channels = channels or ["console", "log"]

    def alert_failure(
        self,
        portal_id: str,
        reason: FailureReason,
        message: str,
        screenshot_path: Optional[str] = None
    ) -> None:
        """Dispatches an urgent alert to the operator on failure or challenge."""
        alert_body = [
            f"🚨 [KBM TENDER ALERT] Portal Run Interrupted: {portal_id.upper()}",
            f"Classification: {reason.value}",
            f"Diagnostic Message: {message}",
            f"Recipients: {', '.join(self.recipients)}"
        ]
        if screenshot_path:
            alert_body.append(f"Redacted Evidence Snapshot: {screenshot_path}")

        formatted = "\n".join(alert_body)
        logger.error("\n%s\n", formatted)

    def send_daily_summary(self, stats: Dict[str, Any], report_file: str) -> None:
        """Sends a high-level summary of the day's run to sales/presales stakeholders."""
        summary = (
            f"📢 KBM Daily Tender Scout Run Complete\n"
            f"Report Generated: {report_file}\n"
            f"Total Tenders Monitored: {stats.get('total_canonical_tenders', 0)}\n"
            f"Status Breakdown: {stats.get('by_status', {})}\n"
            f"Sector Breakdown: {stats.get('by_sector', {})}"
        )
        logger.info("\n%s\n", summary)
