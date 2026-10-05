import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright
from src.utils.secrets import SecretManager

username = SecretManager.get_secret("ALYAWM_USERNAME")
password = SecretManager.get_secret("ALYAWM_PASSWORD")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.goto("https://kuwaitalyawm.media.gov.kw/", timeout=40000)
    page.locator('form[action*="LoginOnline"] input#UserName, input#UserName').first.fill(username)
    page.locator('form[action*="LoginOnline"] input#Password, input#Password').first.fill(password)
    page.locator('form[action*="LoginOnline"] button[type="submit"], form[action*="LoginOnline"] input[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=30000)

    # Search for 1063414
    page.goto("https://kuwaitalyawm.media.gov.kw/search/customindex?dlg=1", timeout=30000)
    page.wait_for_load_state("networkidle")
    page.locator("input#KeyWords").fill("1063414")
    page.locator("form[action*='/search/Get'] button[type='submit']").first.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    rows = page.locator("table tbody tr")
    print(f"Results for 1063414: {rows.count()}")
    for i in range(rows.count()):
        print([td.inner_text().strip() for td in rows.nth(i).locator("td").all()])
        links = rows.nth(i).locator("a").all()
        for l in links:
            print("Link:", l.get_attribute("href"))

    browser.close()
