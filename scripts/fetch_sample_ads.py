import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright
from src.utils.secrets import SecretManager
from src.connectors.kuwait_alyawm import HTMLTextExtractor

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

    for ad_id in ["171724", "171725"]:
        url = f"https://kuwaitalyawm.media.gov.kw/Online/ViewAdsHTML?id={ad_id}&no=1"
        res = context.request.get(url)
        print(f"\n==================== AD ID {ad_id} ====================")
        ext = HTMLTextExtractor()
        ext.feed(res.text())
        print(ext.get_text()[:1000])

    browser.close()
