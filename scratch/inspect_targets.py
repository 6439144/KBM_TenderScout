import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def inspect_urls():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (KBM-TenderScout-Reader)")
        page = context.new_page()

        print("=== INSPECTING KUWAIT AL-YAWM ADS CATEGORY 18 ===")
        url_alyawm = "https://kuwaitalyawm.media.gov.kw/online/AdsCategory/18"
        try:
            page.goto(url_alyawm, wait_until="networkidle", timeout=30000)
            print("Title:", page.title())
            h1s = page.locator("h1, h2, h3, h4, .category-title").all_inner_texts()
            print("Headings:", h1s[:5])
            tables = page.locator("table")
            print("Table count:", tables.count())
            if tables.count() > 0:
                headers = [th.inner_text().strip() for th in page.locator("table thead th").all()]
                print("Table headers:", headers)
                rows = page.locator("table tbody tr")
                print("Rows count on page 1:", rows.count())
                if rows.count() > 0:
                    first_row_cells = [td.inner_text().strip() for td in rows.first.locator("td").all()]
                    print("Sample Row 1 cells:", first_row_cells)
        except Exception as e:
            print("Kuwait Al-Yawm Category 18 error:", e)

        print("\n=== INSPECTING CAPT OPENING TENDERS ===")
        url_capt = "https://capt.gov.kw/ar/tenders/opening-tenders/"
        try:
            page.goto(url_capt, wait_until="networkidle", timeout=30000)
            print("CAPT Title:", page.title())
            cards = page.locator(".detail-list, .page-width.detail-list, .table, table")
            print("Matching selectors count:")
            print("  .detail-list:", page.locator(".detail-list").count())
            print("  table:", page.locator("table").count())
            print("  .endless_page_template:", page.locator(".endless_page_template").count())
            
            # Print sample text if found
            if page.locator(".detail-list").count() > 0:
                print("Sample .detail-list text:")
                print(page.locator(".detail-list").first.inner_text()[:300])
            elif page.locator("table").count() > 0:
                print("Sample table headers:", [th.inner_text().strip() for th in page.locator("table thead th").all()])
                print("Sample table row:", [td.inner_text().strip() for td in page.locator("table tbody tr").first.locator("td").all()])
            else:
                body_text = page.locator("body").inner_text()
                print("Body snippet:", body_text[:400])

        except Exception as e:
            print("CAPT opening tenders error:", e)

        browser.close()

if __name__ == "__main__":
    inspect_urls()
