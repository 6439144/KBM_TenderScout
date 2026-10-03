"""
KBM Tender Scout - Interactive Web Dashboard & REST API
Provides a rich presales dashboard for KBM presales and sales leadership to explore,
filter, and qualify Kuwait public tender notices according to KBM's 5 Business Units
and Technology Alliances (derived from KBM Company Profile).
"""

import sys
import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Query, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import load_config
from src.pipeline.state_store import StateStore
from src.pipeline.kbm_qualifier import KBM_BUSINESS_UNITS, KBM_VENDOR_ALLIANCES, KBMQualifier

app = FastAPI(
    title="KBM Tender Scout Portal",
    description="Intelligent Public Tender Monitoring & Qualification Engine for Khorafi Business Machines (KBM)",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("kbm.web")
state_store = StateStore()

# Track background run status
_CURRENT_RUN_STATE = {
    "is_running": False,
    "last_run_time": None,
    "last_run_status": "IDLE",
    "last_run_message": "Ready"
}

def execute_background_collection(portal: str = "all", limit: Optional[int] = None):
    """Executes live collection in background thread."""
    global _CURRENT_RUN_STATE
    _CURRENT_RUN_STATE["is_running"] = True
    _CURRENT_RUN_STATE["last_run_status"] = "RUNNING"
    _CURRENT_RUN_STATE["last_run_message"] = f"Running collection for {portal}..."
    try:
        from src.run import run_portal
        from src.connectors.capt import CaptConnector
        from src.connectors.kuwait_alyawm import KuwaitAlyawmConnector
        from src.pipeline.processor import TenderProcessor
        from src.output.excel import ExcelReportGenerator
        from src.output.delivery import DeliveryManager

        config = load_config()
        processor = TenderProcessor(config=config, state_store=state_store)
        excel_gen = ExcelReportGenerator(config=config.excel, state_store=state_store)
        delivery_mgr = DeliveryManager(destinations=config.delivery.destinations)

        portals_to_run = []
        if portal in ("capt", "all") and config.portals.get("capt", {}).enabled:
            portals_to_run.append(CaptConnector(config.portals["capt"]))
        if portal in ("kuwait_alyawm", "all") and config.portals.get("kuwait_alyawm", {}).enabled:
            portals_to_run.append(KuwaitAlyawmConnector(config.portals["kuwait_alyawm"]))

        total = 0
        since_date = date.today()
        for conn in portals_to_run:
            count = run_portal(conn, since=since_date, processor=processor, state_store=state_store, limit=limit)
            total += count

        # Generate Excel
        report_path = excel_gen.generate_report()
        delivery_mgr.dispatch(report_path)

        # Generate Standalone HTML Dashboard
        try:
            from src.output.html_dashboard import generate_standalone_dashboard
            generate_standalone_dashboard()
        except Exception as e:
            logger.warning("Could not update HTML dashboard: %s", e)

        _CURRENT_RUN_STATE["is_running"] = False
        _CURRENT_RUN_STATE["last_run_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _CURRENT_RUN_STATE["last_run_status"] = "SUCCESS"
        _CURRENT_RUN_STATE["last_run_message"] = f"Successfully processed {total} notices. Excel updated."
    except Exception as e:
        _CURRENT_RUN_STATE["is_running"] = False
        _CURRENT_RUN_STATE["last_run_status"] = "ERROR"
        _CURRENT_RUN_STATE["last_run_message"] = f"Error during run: {str(e)}"
        logger.error("Background run failed: %s", e)


@app.get("/api/tenders")
def get_tenders(
    bu: Optional[str] = None,
    min_score: Optional[float] = None,
    vendor: Optional[str] = None,
    sector: Optional[str] = None,
    portal: Optional[str] = None,
    status: Optional[str] = None,
    am: Optional[str] = None,
    search: Optional[str] = None
):
    """Returns tenders filtered by KBM presales criteria and metadata."""
    tenders = state_store.get_all_tenders()
    res = []

    for t in tenders:
        # BU filter
        if bu and bu != "all" and t.kbm_bu != bu:
            continue

        # Min Fit Score
        if min_score is not None and t.kbm_fit_score < min_score:
            continue

        # Vendor filter
        if vendor and vendor != "all" and vendor not in (t.kbm_vendors or []):
            continue

        # Sector filter
        if sector and sector != "all" and t.sector != sector:
            continue

        # Account Manager filter
        if am and am != "all" and t.account_owner != am:
            continue

        # Status filter
        if status and status != "all" and t.status.value != status:
            continue

        # Portal filter
        if portal and portal != "all":
            portals = [s.portal for s in t.sources]
            if portal not in portals:
                continue

        # Search filter
        if search:
            query = search.strip().lower()
            match_txt = f"{t.tender_no} {t.title_ar} {t.client} {t.kbm_bu or ''} {' '.join(t.kbm_vendors or [])}".lower()
            if query not in match_txt:
                continue

        res.append(t.model_dump())

    # Sort by fit score descending, then publish date
    res.sort(key=lambda x: (x.get("kbm_fit_score", 0), x.get("publish_date") or ""), reverse=True)
    return {"total": len(res), "tenders": res}


@app.get("/api/stats")
def get_stats():
    """Returns high-level KPI metrics and distributions."""
    tenders = state_store.get_all_tenders()
    
    total = len(tenders)
    high_priority = sum(1 for t in tenders if t.kbm_fit_score >= 70.0)
    target_opps = sum(1 for t in tenders if 40.0 <= t.kbm_fit_score < 70.0)
    unrelated = sum(1 for t in tenders if t.kbm_fit_score < 40.0)
    
    today_iso = date.today().isoformat()
    closing_soon = sum(
        1 for t in tenders 
        if t.closing_date and today_iso <= t.closing_date <= (date.today().replace(day=min(date.today().day+7, 28))).isoformat()
    )

    by_bu = {}
    for bu_name in KBM_BUSINESS_UNITS.keys():
        by_bu[bu_name] = sum(1 for t in tenders if t.kbm_bu == bu_name)

    by_sector = {}
    for t in tenders:
        sec = t.sector or "other"
        by_sector[sec] = by_sector.get(sec, 0) + 1

    by_status = {}
    for t in tenders:
        st = t.status.value
        by_status[st] = by_status.get(st, 0) + 1

    return {
        "total_tenders": total,
        "high_priority_bids": high_priority,
        "target_opportunities": target_opps,
        "unrelated": unrelated,
        "closing_soon": closing_soon,
        "by_bu": by_bu,
        "by_sector": by_sector,
        "by_status": by_status,
        "bu_metadata": {k: {"label_ar": v["label_ar"], "description": v["description"]} for k, v in KBM_BUSINESS_UNITS.items()}
    }


@app.post("/api/run")
def trigger_run(background_tasks: BackgroundTasks, portal: str = "all", limit: Optional[int] = 5):
    """Triggers an automated background ingestion run."""
    global _CURRENT_RUN_STATE
    if _CURRENT_RUN_STATE["is_running"]:
        return JSONResponse(status_code=400, content={"message": "A run is already in progress"})
    
    background_tasks.add_task(execute_background_collection, portal=portal, limit=limit)
    return {"message": "Run initiated successfully", "state": _CURRENT_RUN_STATE}


@app.get("/api/run-status")
def get_run_status():
    """Returns current execution status of background runs."""
    return _CURRENT_RUN_STATE


@app.post("/api/reclassify")
def reclassify_all():
    """Re-scores all database tenders against the KBM Company Profile."""
    count = state_store.reclassify_all_with_kbm_profile()
    try:
        from src.output.excel import ExcelReportGenerator
        config = load_config()
        excel_gen = ExcelReportGenerator(config=config.excel, state_store=state_store)
        excel_gen.generate_report()
        from src.output.html_dashboard import generate_standalone_dashboard
        generate_standalone_dashboard()
    except Exception as e:
        logger.warning("Error regenerating reports on reclassify: %s", e)
    return {"message": f"Successfully reclassified {count} tenders against KBM Company Profile", "count": count}


@app.get("/api/export")
def download_excel():
    """Downloads the latest compiled Excel workbook."""
    latest_path = PROJECT_ROOT / "output" / "reports" / "KBM_Tenders_Latest.xlsx"
    if not latest_path.exists():
        # Fallback to date file
        files = list((PROJECT_ROOT / "output" / "reports").glob("KBM_Tenders_*.xlsx"))
        if files:
            latest_path = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
        else:
            raise HTTPException(status_code=404, detail="No Excel report generated yet")
    return FileResponse(
        path=str(latest_path),
        filename="KBM_Tenders_Qualified_Latest.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/", response_class=HTMLResponse)
def index():
    """Serves the full interactive Arabic/English KBM presales dashboard."""
    html_file = Path(__file__).parent / "templates" / "index.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return "<h1>KBM Tender Scout Dashboard</h1>"


if __name__ == "__main__":
    uvicorn.run("src.web.app:app", host="127.0.0.1", port=8000, reload=False)
