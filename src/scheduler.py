"""
Scheduler Daemon for KBM Tender Scout (FR-1 & Milestone 5).
Coordinates daily scheduled executions at 06:00 AM Asia/Kuwait, enforces compliance gates,
and applies retry policies (max 1 retry per day for transient errors).
"""

import sys
import time
import subprocess
import logging
from datetime import datetime, date
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8 console output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from src.config import load_config, RootConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/scheduler.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("kbm.scheduler")

class TenderScoutScheduler:
    def __init__(self, config_path: Path = Path("config/config.yaml")):
        self.config = load_config(config_path if config_path.exists() else None)
        self.last_run_date: str = ""
        self.retries_today: int = 0

    def check_compliance_gate(self) -> bool:
        """Enforces Rule 3.6 compliance gate before any scheduled automated runs."""
        if not self.config.compliance.automation_permitted:
            logger.critical(
                "⛔ COMPLIANCE GATE ENFORCED (Rule 3.6):\n"
                "Automated scheduled runs are BLOCKED until the product owner (Khaled Abed)\n"
                "confirms in writing in docs/COMPLIANCE.md that KBM's subscriptions permit\n"
                "automated retrieval, and sets compliance.automation_permitted: true.\n"
                "The agent may currently only be executed manually with a human present."
            )
            return False
        return True

    def run_job(self) -> bool:
        """Executes the orchestrator subprocess and returns success status."""
        cmd = [sys.executable, "src/run.py", "--portal", "all"]
        logger.info("Executing scheduled tender collection: %s", " ".join(cmd))
        try:
            res = subprocess.run(cmd, capture_output=False, check=False)
            if res.returncode == 0:
                logger.info("Scheduled run completed successfully.")
                return True
            else:
                logger.error("Scheduled run exited with failure code %d.", res.returncode)
                return False
        except Exception as e:
            logger.error("Failed to execute scheduled run: %s", e)
            return False

    def start_loop(self) -> None:
        """Runs the monitoring loop checking for the 06:00 AM Kuwait window."""
        logger.info("Starting KBM Tender Scout Scheduler Daemon...")
        logger.info(
            "Schedule: 06:00 AM Asia/Kuwait | Active Days: %s",
            ", ".join(self.config.schedule.active_days)
        )

        # Check compliance gate
        if not self.check_compliance_gate():
            sys.exit(1)

        while True:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            day_name = now.strftime("%A")

            # Check if today is a scheduled active day (Sun - Thu)
            if day_name in self.config.schedule.active_days:
                # Check target hour: 06:00 AM window
                if now.hour == 6 and self.last_run_date != today_str:
                    logger.info("Target execution window reached (06:00 AM %s).", day_name)
                    success = self.run_job()
                    self.last_run_date = today_str
                    self.retries_today = 0

                    if not success and self.retries_today < self.config.portals["capt"].rate_limiting.max_retries_per_day:
                        logger.info("Scheduling single transient failure retry in 10 minutes (Rule 3.4)...")
                        time.sleep(600)
                        self.retries_today += 1
                        self.run_job()

            # Sleep 30 seconds between checks
            time.sleep(30)

def main():
    scheduler = TenderScoutScheduler()
    scheduler.start_loop()

if __name__ == "__main__":
    main()
