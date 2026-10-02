#!/usr/bin/env python3
"""
Inspect tender detail link / row click on Kuwait Al-Yawm
"""

import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def inspect_alyawm_row():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors"])
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        page.goto("https://kuwaitalyawm.media.gov.kw/online/AdsCategory/1", wait_until="networkidle", timeout=45000)
        time.sleep(3)

        # Inspect table rows and their links
        rows_info = page.eval_on_selector_all("table tbody tr", """
            rows => rows.slice(0, 5).map(r => {
                const links = Array.from(r.querySelectorAll('a')).map(a => ({
                    text: a.innerText.trim(),
                    href: a.getAttribute('href') || '',
                    onclick: a.getAttribute('onclick') || ''
                }));
                const cells = Array.from(r.querySelectorAll('td')).map(td => td.innerText.trim());
                return { cells, links };
            })
        """)
        print("Al-Yawm Rows Info:")
        print(json.dumps(rows_info, ensure_ascii=False, indent=2))

        # If a link exists, let's click or follow the first one
        if rows_info and rows_info[0]["links"]:
            first_href = rows_info[0]["links"][0]["href"]
            first_onclick = rows_info[0]["links"][0]["onclick"]
            print(f"First link href: {first_href}, onclick: {first_onclick}")

            if first_href and not first_href.startswith("#") and not first_href.startswith("javascript"):
                target = "https://kuwaitalyawm.media.gov.kw" + first_href if first_href.startswith("/") else first_href
                print(f"Navigating to {target}")
                page.goto(target, wait_until="networkidle", timeout=30000)
                time.sleep(2)
                page.screenshot(path="docs/recon/screenshots/alyawm_tender_detail.png")
                print(f"Detail page title: {page.title()}")
                print(f"Detail snippet: {page.locator('body').inner_text()[:600]}")
            else:
                # Try clicking the row link directly
                print("Clicking first link directly on page...")
                page.locator("table tbody tr a").first.click()
                time.sleep(3)
                page.screenshot(path="docs/recon/screenshots/alyawm_after_click.png")
                print(f"After click URL: {page.url}")
                print(f"Modal or new content: {page.locator('body').inner_text()[:600]}")

        browser.close()

if __name__ == "__main__":
    inspect_alyawm_row()
