import sys
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://kuwaitalyawm.media.gov.kw/online/AdsCategory/18", wait_until="networkidle", timeout=30000)
    
    rows = page.locator("table tbody tr")
    print(f"Total rows on page: {rows.count()}")
    for i in range(min(5, rows.count())):
        row = rows.nth(i)
        tds = row.locator("td")
        texts = [td.inner_text().strip() for td in tds.all()]
        html_links = [a.get_attribute("href") or a.get_attribute("data-load-url") for a in row.locator("a").all()]
        print(f"Row {i}: Texts={texts} | Links={html_links}")

    browser.close()
