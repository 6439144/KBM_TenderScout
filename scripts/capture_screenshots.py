import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "docs" / "screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

URL = "http://127.0.0.1:8000"

def capture_all():
    print(f"Connecting to {URL}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1.5,
            locale="ar-KW"
        )
        page = context.new_page()
        
        # 1. Main Dashboard Overview
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUTPUT_DIR / "01_dashboard_overview.png"), full_page=False)
        print("Captured: 01_dashboard_overview.png")

        # 2. Filter Bar & KPI Cards focused view
        page.screenshot(path=str(OUTPUT_DIR / "02_kpi_and_filters.png"), clip={"x": 100, "y": 80, "width": 1240, "height": 450})
        print("Captured: 02_kpi_and_filters.png")

        # 3. Strategic Tenders List (Showing MNA-19 and MNA-24 with Scope badges)
        page.evaluate("window.scrollTo(0, 420)")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUTPUT_DIR / "03_strategic_tenders_list.png"), clip={"x": 100, "y": 100, "width": 1240, "height": 650})
        print("Captured: 03_strategic_tenders_list.png")

        # 4. Open Modal for MNA/19/2026 (Cisco Managed Support)
        page.evaluate("openDetailModal(allTenders[0])")
        page.wait_for_timeout(800)
        modal = page.locator("#detail-modal > div").first
        modal.screenshot(path=str(OUTPUT_DIR / "04_modal_mna19_cisco.png"))
        print("Captured: 04_modal_mna19_cisco.png")
        page.evaluate("closeDetailModal()")
        page.wait_for_timeout(500)

        # 5. Open Modal for MNA/24/2026 (IBM Maximo)
        page.evaluate("openDetailModal(allTenders[1])")
        page.wait_for_timeout(800)
        modal.screenshot(path=str(OUTPUT_DIR / "05_modal_mna24_ibm.png"))
        print("Captured: 05_modal_mna24_ibm.png")
        page.evaluate("closeDetailModal()")
        page.wait_for_timeout(500)

        # 6. Open Modal for 24181118110 (MOD Enterprise Servers)
        page.evaluate("const modT = allTenders.find(t => t.tender_no.includes('18110')); if (modT) openDetailModal(modT);")
        page.wait_for_timeout(800)
        modal.screenshot(path=str(OUTPUT_DIR / "06_modal_mod_servers.png"))
        print("Captured: 06_modal_mod_servers.png")
        page.evaluate("closeDetailModal()")
        page.wait_for_timeout(500)

        # 7. Filter by Account Manager (Abrar Al-Qallaf)
        page.evaluate("""() => {
            document.getElementById('am-select').value = 'Abrar Al-Qallaf';
            applyFilters();
            window.scrollTo(0, 280);
        }""")
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUTPUT_DIR / "07_filtered_by_account_manager.png"), clip={"x": 100, "y": 100, "width": 1240, "height": 650})
        print("Captured: 07_filtered_by_account_manager.png")

        # 8. Reset filters
        page.evaluate("resetFilters()")
        page.wait_for_timeout(500)

        browser.close()
        print("All 7 screenshots successfully captured!")

if __name__ == "__main__":
    capture_all()
