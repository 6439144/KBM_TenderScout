#!/usr/bin/env python3
"""
CLI Runner and Execution Orchestrator for KBM Tender Scout.
Supports manual runs: python src/run.py --portal capt|kuwait_alyawm|all [--since YYYY-MM-DD] [--limit N]
"""

import sys
import argparse
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional

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
from src.connectors.base import PortalConnector
from src.connectors.capt import CaptConnector
from src.connectors.kuwait_alyawm import KuwaitAlyawmConnector
from src.output.delivery import DeliveryManager
from src.output.excel import ExcelReportGenerator
from src.output.notify import NotificationManager
from src.pipeline.processor import TenderProcessor
from src.pipeline.state_store import StateStore
from src.utils.secrets import SecretManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/run.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("kbm.orchestrator")

def run_portal(
    connector: PortalConnector,
    since: date,
    processor: TenderProcessor,
    state_store: StateStore,
    limit: Optional[int] = None
) -> int:
    """Executes a single portal run sequentially with polite handling and state persistence."""
    logger.info("==================================================")
    logger.info("Starting run for portal: %s", connector.portal_id.upper())
    logger.info("==================================================")

    # 1. Login phase
    session_result: SessionResult = connector.login()
    if not session_result.success:
        logger.error(
            "Portal %s run halted: %s (Type: %s)",
            connector.portal_id, session_result.message, session_result.error_type
        )
        return 0

    logger.info("Portal %s session ready: %s", connector.portal_id, session_result.message)

    # 2. Listing & Extraction Phase
    collected_count = 0
    try:
        notices_iter = connector.list_notices(since=since)
        for ref in notices_iter:
            if limit and collected_count >= limit:
                logger.info("Reached limit of %d notices for portal %s.", limit, connector.portal_id)
                break

            logger.info("[%s] Fetching detail for tender: %s", connector.portal_id, ref.tender_no_raw)
            raw_notice: RawNotice = connector.fetch_detail(ref)
            
            # Persist raw notice to SQLite
            state_store.save_raw_notice(raw_notice)

            # Process through full normalization, classification, and dedupe pipeline
            canonical = processor.process_raw_notice(raw_notice)
            logger.info(
                "[%s] Processed: %s | Client: %s | Sector: %s | Status: %s | Review: %s",
                connector.portal_id, canonical.tender_no, canonical.client, canonical.sector,
                canonical.status.value, canonical.needs_review
            )

            collected_count += 1
            connector.polite_delay()

    except Exception as e:
        logger.error("Error during listing/detail extraction for %s: %s", connector.portal_id, e)
    finally:
        # 3. Clean Logout & Browser Release Phase (Rule 3.5)
        connector.close()
        logger.info("Portal %s run concluded. %d notices processed.", connector.portal_id, collected_count)

    return collected_count

def main():
    parser = argparse.ArgumentParser(description="KBM Tender Scout Orchestrator")
    parser.add_argument(
        "--portal",
        choices=["capt", "kuwait_alyawm", "all"],
        default="all",
        help="Target portal(s) to collect from"
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Collect notices published since date (YYYY-MM-DD). Defaults to backfill_days."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of notices to process per portal"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to YAML configuration file"
    )
    parser.add_argument(
        "--excel-only",
        action="store_true",
        help="Skip portal collection and regenerate Excel workbook from current database state"
    )
    args = parser.parse_args()

    # Load system configuration
    config: RootConfig = load_config(args.config)
    Path("logs").mkdir(exist_ok=True)
    Path("output/reports").mkdir(parents=True, exist_ok=True)

    # Initialize State Store, Processor, and Managers
    state_store = StateStore()
    processor = TenderProcessor(config=config, state_store=state_store)
    excel_generator = ExcelReportGenerator(config=config.excel, state_store=state_store)
    delivery_manager = DeliveryManager(destinations=config.delivery.destinations)
    notification_manager = NotificationManager(
        recipients=config.notify.recipients,
        channels=config.notify.channels
    )

    run_logs: List[dict] = []

    if not args.excel_only:
        # Determine collection since date
        if args.since:
            since_date = date.fromisoformat(args.since)
        else:
            since_date = date.today() - timedelta(days=config.collect.backfill_days)

        logger.info("KBM Tender Scout Orchestrator initialized.")
        logger.info("Target: %s | Since: %s | Limit: %s", args.portal, since_date, args.limit)

        portals_to_run = []
        if args.portal in ("capt", "all") and config.portals.get("capt", {}).enabled:
            portals_to_run.append(CaptConnector(config.portals["capt"]))
        if args.portal in ("kuwait_alyawm", "all") and config.portals.get("kuwait_alyawm", {}).enabled:
            portals_to_run.append(KuwaitAlyawmConnector(config.portals["kuwait_alyawm"]))

        total_processed = 0
        for connector in portals_to_run:
            # Sequential execution with 1 session per portal (Rule 3.4)
            count = run_portal(
                connector=connector,
                since=since_date,
                processor=processor,
                state_store=state_store,
                limit=args.limit
            )
            total_processed += count
            run_logs.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "portal": connector.portal_id,
                "status": "SUCCESS",
                "count": count,
                "message": f"Processed {count} notices cleanly."
            })

    # Generate Excel Workbook (FR-8)
    logger.info("Generating Excel Report with 8 sheets...")
    report_path = excel_generator.generate_report(run_logs=run_logs)
    logger.info("Excel Report generated successfully: %s", report_path.resolve())

    # Generate Standalone Interactive HTML Dashboard
    try:
        from src.output.html_dashboard import generate_standalone_dashboard
        html_dashboard_path = generate_standalone_dashboard()
        logger.info("Interactive HTML Dashboard generated: %s", html_dashboard_path.resolve())
    except Exception as e:
        logger.warning("Could not generate HTML dashboard: %s", e)

    # Dispatch Delivery (FR-9)
    delivery_manager.dispatch(report_path)

    # Print summary metrics & notifications (FR-10)
    stats = state_store.get_stats()
    notification_manager.send_daily_summary(stats, report_path.name)

    logger.info("==================================================")
    logger.info("RUN SUMMARY:")
    logger.info("Excel Output: %s", report_path)
    logger.info("Latest Output: %s", config.excel.output_dir + "/" + config.excel.latest_filename)
    logger.info("Total Raw Notices in SQLite: %d", stats["total_raw_notices"])
    logger.info("Total Canonical Records in Store: %d", stats["total_canonical_tenders"])
    logger.info("Records by Status: %s", stats["by_status"])
    logger.info("Records by Sector: %s", stats["by_sector"])
    logger.info("==================================================")

if __name__ == "__main__":
    main()
