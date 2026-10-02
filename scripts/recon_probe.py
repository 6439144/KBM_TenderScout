#!/usr/bin/env python3
"""
Reconnaissance Probe for CAPT and Kuwait Al-Yawm Portals
Extracts DOM structure, navigation menus, login forms, tender listing fields,
pagination controls, and anti-bot/challenge signals without submitting actions.
"""

import sys
import os
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
FIXTURES_DIR = Path("tests/fixtures")
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

def probe_capt(page):
    print("--- [RECON] Probing CAPT (https://capt.gov.kw/ar/) ---")
    data = {"portal": "capt", "base_url": "https://capt.gov.kw/ar/"}
    
    # 1. Main landing page
    page.goto("https://capt.gov.kw/ar/", wait_until="networkidle", timeout=45000)
    time.sleep(3)
    data["title"] = page.title()
    print(f"CAPT Title: {data['title']}")

    # Collect nav links
    links = page.eval_on_selector_all("a", """
        elements => elements.map(el => ({
            text: el.innerText.trim(),
            href: el.getAttribute('href') || ''
        })).filter(l => l.text && l.href && !l.href.startsWith('javascript'))
    """)
    data["nav_links"] = links[:40]

    # Look for login / tenders links
    tender_links = [l for l in links if any(k in l['text'] for k in ["مناقص", "ممارس", "تأهيل", "إعلان", "طرح", "شراء"])]
    login_links = [l for l in links if any(k in l['text'] for k in ["دخول", "تسجيل", "حساب", "Login", "Sign"])]
    data["tender_links_found"] = tender_links
    data["login_links_found"] = login_links
    print(f"Found {len(tender_links)} tender-related links and {len(login_links)} login-related links on homepage.")

    # Save homepage HTML (without secrets)
    (RECON_DIR / "capt_home.html").write_text(page.content(), encoding="utf-8")

    # 2. Check login page if link found or try common login URLs
    login_url = None
    if login_links:
        login_url = login_links[0]["href"]
        if login_url.startswith("/"):
            login_url = "https://capt.gov.kw" + login_url
    else:
        login_url = "https://capt.gov.kw/ar/login/"

    print(f"Probing CAPT login URL: {login_url}")
    try:
        page.goto(login_url, wait_until="networkidle", timeout=30000)
        time.sleep(3)
        data["login_page_title"] = page.title()
        data["login_url_actual"] = page.url

        # Inspect form fields
        inputs = page.eval_on_selector_all("input", """
            elements => elements.map(el => ({
                name: el.getAttribute('name') || '',
                id: el.getAttribute('id') || '',
                type: el.getAttribute('type') || '',
                placeholder: el.getAttribute('placeholder') || '',
                autocomplete: el.getAttribute('autocomplete') || ''
            }))
        """)
        data["login_form_inputs"] = inputs
        print(f"CAPT Login inputs detected: {inputs}")

        # Check for captcha / bot challenge signals
        has_recaptcha = page.locator("iframe[src*='recaptcha'], .g-recaptcha").count() > 0
        has_turnstile = page.locator("iframe[src*='cloudflare'], .cf-turnstile").count() > 0
        has_hcaptcha = page.locator("iframe[src*='hcaptcha'], .h-captcha").count() > 0
        data["captcha_detected"] = {
            "recaptcha": has_recaptcha,
            "cloudflare_turnstile": has_turnstile,
            "hcaptcha": has_hcaptcha
        }
        print(f"CAPT Captcha detection: {data['captcha_detected']}")
    except Exception as e:
        data["login_probe_error"] = str(e)
        print(f"Error probing CAPT login: {e}")

    # 3. Explore tender listing pages
    # Check if there are public tender sections
    public_tender_urls = [
        "https://capt.gov.kw/ar/tenders/announcements/",
        "https://capt.gov.kw/ar/tenders/",
        "https://capt.gov.kw/ar/tenders-and-practices/",
    ]
    for url in public_tender_urls:
        try:
            print(f"Checking potential tender list URL: {url}")
            resp = page.goto(url, wait_until="networkidle", timeout=20000)
            if resp and resp.status == 200:
                print(f"Found active tender page at: {url} (Title: {page.title()})")
                data["active_tenders_url"] = url
                data["tenders_page_title"] = page.title()
                
                # Check for table or list structure
                tables = page.locator("table").count()
                cards = page.locator(".tender-item, .card, .tender, tr").count()
                data["listing_elements"] = {"table_count": tables, "row_or_card_count": cards}
                print(f"Listing elements: {data['listing_elements']}")
                
                # Extract headers if table exists
                if tables > 0:
                    headers = page.eval_on_selector_all("table th", "els => els.map(e => e.innerText.trim())")
                    data["table_headers"] = headers
                    print(f"Table headers: {headers}")

                # Save sample HTML
                (RECON_DIR / "capt_tenders_sample.html").write_text(page.content(), encoding="utf-8")
                break
        except Exception as e:
            print(f"Could not load {url}: {e}")

    (RECON_DIR / "capt_recon_data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data

def probe_alyawm(page):
    print("\n--- [RECON] Probing Kuwait Al-Yawm (https://kuwaitalyawm.media.gov.kw/) ---")
    data = {"portal": "kuwait_alyawm", "base_url": "https://kuwaitalyawm.media.gov.kw/"}

    # 1. Main landing page
    page.goto("https://kuwaitalyawm.media.gov.kw/", wait_until="networkidle", timeout=45000)
    time.sleep(3)
    data["title"] = page.title()
    data["url_actual"] = page.url
    print(f"Al-Yawm Title: {data['title']}, URL: {data['url_actual']}")

    # Collect links
    links = page.eval_on_selector_all("a", """
        elements => elements.map(el => ({
            text: el.innerText.trim(),
            href: el.getAttribute('href') || ''
        })).filter(l => l.text && l.href && !l.href.startsWith('javascript'))
    """)
    data["nav_links"] = links[:40]

    # Look for login / issues / search links
    issue_links = [l for l in links if any(k in l['text'] for k in ["عدد", "أعداد", "الجريدة", "بحث", "مناقص", "Issue", "Gazette"])]
    login_links = [l for l in links if any(k in l['text'] for k in ["دخول", "تسجيل", "مشترك", "Login", "Sign"])]
    data["issue_links_found"] = issue_links
    data["login_links_found"] = login_links
    print(f"Al-Yawm: Found {len(issue_links)} issue links and {len(login_links)} login links.")

    # Check for login inputs directly on the page
    inputs = page.eval_on_selector_all("input", """
        elements => elements.map(el => ({
            name: el.getAttribute('name') || '',
            id: el.getAttribute('id') || '',
            type: el.getAttribute('type') || '',
            placeholder: el.getAttribute('placeholder') || ''
        }))
    """)
    data["inputs_on_page"] = inputs
    print(f"Al-Yawm inputs on landing page: {inputs}")

    # Check captcha
    has_recaptcha = page.locator("iframe[src*='recaptcha'], .g-recaptcha").count() > 0
    data["captcha_detected"] = {"recaptcha": has_recaptcha}

    # Check if PDF links exist
    pdf_links = page.eval_on_selector_all("a[href*='.pdf']", """
        elements => elements.map(el => ({
            text: el.innerText.trim(),
            href: el.getAttribute('href') || ''
        }))
    """)
    data["pdf_links_found"] = pdf_links[:10]
    print(f"Al-Yawm PDF links found on landing: {len(pdf_links)}")

    (RECON_DIR / "alyawm_home.html").write_text(page.content(), encoding="utf-8")
    (RECON_DIR / "alyawm_recon_data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data

def main():
    print("Starting Milestone 1 Recon Probe...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--ignore-certificate-errors"]
        )
        context = browser.new_context(
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (KBM-TenderScout-Reader)"
        )
        page = context.new_page()

        try:
            probe_capt(page)
        except Exception as e:
            print(f"Error in CAPT probe: {e}")

        try:
            probe_alyawm(page)
        except Exception as e:
            print(f"Error in Al-Yawm probe: {e}")

        browser.close()
    print("\nRecon probe execution complete. Artifacts saved in docs/recon/.")

if __name__ == "__main__":
    main()
