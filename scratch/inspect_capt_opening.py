import sys
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://capt.gov.kw/ar/tenders/opening-tenders/", wait_until="networkidle", timeout=30000)
    
    cards = page.locator(".detail-list")
    print(f"Total cards on page: {cards.count()}")
    for i in range(min(3, cards.count())):
        card = cards.nth(i)
        print(f"--- CARD {i} ---")
        print(card.inner_text().strip())
        print("Links:", [a.get_attribute("href") for a in card.locator("a").all()])

    browser.close()
