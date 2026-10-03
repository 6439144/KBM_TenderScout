import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
username = os.getenv("ALYAWM_USERNAME")
password = os.getenv("ALYAWM_PASSWORD")

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("Logging into Kuwait Al-Yawm...")
    page.goto("https://kuwaitalyawm.media.gov.kw/", wait_until="networkidle", timeout=30000)
    page.locator('form[action*="LoginOnline"] input#UserName').fill(username)
    page.locator('form[action*="LoginOnline"] input#Password').fill(password)
    page.locator('form[action*="LoginOnline"] button[type="submit"], form[action*="LoginOnline"] input[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=25000)
    print("Logged in. Navigating to flip page...")

    flip_url = "https://kuwaitalyawm.media.gov.kw/flip/index?id=5599&no=228"
    page.goto(flip_url, wait_until="networkidle", timeout=30000)
    print("Page Title:", page.title())

    text = page.locator("body").inner_text()
    print("Body text length:", len(text))
    print("Snippet:")
    print(text[:600])

    # Check images / canvas / text layer
    images = page.locator("img, canvas, svg")
    print("Images/Canvas count:", images.count())
    for i in range(min(5, images.count())):
        img = images.nth(i)
        print(f"Img {i}: tag={img.evaluate('e => e.tagName')} src={img.get_attribute('src')}")

    browser.close()
