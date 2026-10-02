#!/usr/bin/env python3
"""
Deep-dive Reconnaissance Probe for CAPT and Kuwait Al-Yawm
Inspects tender listings, detail pages, table columns, pagination, and PDF/HTML formats.
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

RECON_DIR = Path("docs/recon")
RECON_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR = Path("docs/recon/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def deep_probe_capt(page):
    print("=== Deep Probing CAPT Open Tenders ===")
    url = "https://capt.gov.kw/ar/tenders/opening-tenders/"
    page.goto(url, wait_until="networkidle", timeout=45000)
    time.sleep(3)

    capt_data = {
        "url": url,
        "title": page.title(),
    }

    # Screenshot
    page.screenshot(path=str(SCREENSHOTS_DIR / "capt_opening_tenders.png"), full_page=False)

    # Inspect table structure
    tables = page.locator("table")
    capt_data["table_count"] = tables.count()

    if tables.count() > 0:
        # Headers
        headers = page.eval_on_selector_all("table thead th, table tr th", "els => els.map(e => e.innerText.trim()).filter(Boolean)")
        capt_data["headers"] = headers
        print(f"CAPT Headers ({len(headers)}): {headers}")

        # Rows
        rows = page.eval_on_selector_all("table tbody tr", """
            rows => rows.slice(0, 5).map(r => {
                const cells = Array.from(r.querySelectorAll('td')).map(c => c.innerText.trim());
                const links = Array.from(r.querySelectorAll('a')).map(a => ({
                    text: a.innerText.trim(),
                    href: a.getAttribute('href')
                }));
                return { cells, links };
            })
        """)
        capt_data["sample_rows"] = rows
        print(f"CAPT Extracted {len(rows)} sample rows from table.")

        # Pagination controls
        pagination = page.eval_on_selector_all(".pagination, .pager, ul.pagination li, [class*='page']", """
            els => els.map(e => ({
                tag: e.tagName,
                text: e.innerText.trim(),
                className: e.className,
                href: e.getAttribute('href')
            })).filter(e => e.text)
        """)
        capt_data["pagination_controls"] = pagination[:15]
        print(f"CAPT Pagination controls: {len(pagination)} items found.")

        # Inspect first detail link if available
        first_detail_link = None
        for r in rows:
            for l in r["links"]:
                if l["href"] and ("detail" in l["href"] or "tenders" in l["href"]):
                    first_detail_link = l["href"]
                    break
            if first_detail_link:
                break

        if first_detail_link:
            if first_detail_link.startswith("/"):
                first_detail_link = "https://capt.gov.kw" + first_detail_link
            print(f"Probing CAPT detail page: {first_detail_link}")
            try:
                page.goto(first_detail_link, wait_until="networkidle", timeout=30000)
                time.sleep(3)
                page.screenshot(path=str(SCREENSHOTS_DIR / "capt_detail_page.png"), full_page=False)
                capt_data["detail_page"] = {
                    "url": page.url,
                    "title": page.title(),
                    "labels": page.eval_on_selector_all("label, th, dt, strong, .label", "els => els.map(e => e.innerText.trim()).filter(Boolean)"),
                    "text_sample": page.locator("body").inner_text()[:1500]
                }
                print(f"CAPT Detail page labels found: {len(capt_data['detail_page']['labels'])}")
            except Exception as e:
                print(f"Could not load detail page: {e}")

    (RECON_DIR / "capt_deep_data.json").write_text(json.dumps(capt_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return capt_data

def deep_probe_alyawm(page):
    print("\n=== Deep Probing Kuwait Al-Yawm Categories ===")
    url = "https://kuwaitalyawm.media.gov.kw/online/AdsCategory/1"
    page.goto(url, wait_until="networkidle", timeout=45000)
    time.sleep(3)

    alyawm_data = {
        "url": url,
        "title": page.title(),
    }
    page.screenshot(path=str(SCREENSHOTS_DIR / "alyawm_category_1.png"), full_page=False)

    # Check if page requires login or displays notices publicly
    body_text = page.locator("body").inner_text()
    alyawm_data["requires_login"] = "تسجيل الدخول" in body_text and ("غير مصرح" in body_text or "اشتراك" in body_text or "Login" in body_text)
    alyawm_data["body_snippet"] = body_text[:1200]
    print(f"Al-Yawm AdsCategory/1 Title: {page.title()}")

    # Check for tables, items, or PDF links
    tables = page.locator("table")
    alyawm_data["table_count"] = tables.count()
    if tables.count() > 0:
        headers = page.eval_on_selector_all("table th", "els => els.map(e => e.innerText.trim()).filter(Boolean)")
        alyawm_data["headers"] = headers
        rows = page.eval_on_selector_all("table tr", "els => els.slice(0, 5).map(e => e.innerText.trim())")
        alyawm_data["rows"] = rows
        print(f"Al-Yawm Table headers: {headers}")

    # Check editions page: https://kuwaitalyawm.media.gov.kw/online/editions
    print("Checking Al-Yawm Editions Page: https://kuwaitalyawm.media.gov.kw/online/editions")
    try:
        page.goto("https://kuwaitalyawm.media.gov.kw/online/editions", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        page.screenshot(path=str(SCREENSHOTS_DIR / "alyawm_editions.png"), full_page=False)
        alyawm_data["editions_page"] = {
            "title": page.title(),
            "url": page.url,
            "pdf_links": page.eval_on_selector_all("a[href*='.pdf'], a[href*='download'], a[href*='Download']", """
                els => els.map(e => ({
                    text: e.innerText.trim(),
                    href: e.getAttribute('href')
                }))
            """),
            "items": page.eval_on_selector_all(".edition, .item, .card, tr", """
                els => els.slice(0, 8).map(e => e.innerText.trim()).filter(Boolean)
            """)
        }
        print(f"Al-Yawm Editions found: {len(alyawm_data['editions_page']['pdf_links'])} PDF/download links, {len(alyawm_data['editions_page']['items'])} items.")
    except Exception as e:
        print(f"Could not load Al-Yawm editions: {e}")

    (RECON_DIR / "alyawm_deep_data.json").write_text(json.dumps(alyawm_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return alyawm_data

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--ignore-certificate-errors"]
        )
        context = browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (KBM-TenderScout-Reader)"
        )
        page = context.new_page()

        try:
            deep_probe_capt(page)
        except Exception as e:
            print(f"CAPT deep probe failed: {e}")

        try:
            deep_probe_alyawm(page)
        except Exception as e:
            print(f"Al-Yawm deep probe failed: {e}")

        browser.close()
    print("Deep reconnaissance probe completed.")

if __name__ == "__main__":
    main()
