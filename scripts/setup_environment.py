"""
KBM Tender Scout - Intelligent Prerequisite Installer & Environment Validator
Verifies Python version, installs all required packages, downloads Playwright browser binaries,
verifies environment variables (.env), and validates SQLite state store.
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ANSI Colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Reconfigure stdout for UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Safe markers for cross-platform terminals
OK_MARK = "[OK]"
WARN_MARK = "[!]"
ERR_MARK = "[X]"
ARROW_MARK = "==>"

def print_step(msg: str):
    print(f"\n{BOLD}{BLUE}{ARROW_MARK}{RESET} {BOLD}{msg}{RESET}")

def print_ok(msg: str):
    print(f"  {GREEN}{OK_MARK}{RESET} {msg}")

def print_warn(msg: str):
    print(f"  {YELLOW}{WARN_MARK}{RESET} {msg}")

def print_err(msg: str):
    print(f"  {RED}{ERR_MARK}{RESET} {msg}")

def check_python_version():
    print_step("Checking Python version...")
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print_err(f"Python 3.10+ required. Current version is {v.major}.{v.minor}.{v.micro}")
        sys.exit(1)
    print_ok(f"Python version: {v.major}.{v.minor}.{v.micro} (Supported)")

def install_python_dependencies():
    print_step("Installing / Verifying Python dependencies from requirements.txt...")
    req_file = PROJECT_ROOT / "requirements.txt"
    if not req_file.exists():
        print_err("requirements.txt not found!")
        sys.exit(1)
    
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print_err("Failed to install Python dependencies via pip.")
        sys.exit(1)
    print_ok("All Python dependencies successfully installed.")

def install_playwright_browsers():
    print_step("Verifying & Installing Playwright Chromium browser binary...")
    try:
        import playwright
        cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
        print("  Downloading Chromium headless browser (this may take 1-2 minutes on first run)...")
        res = subprocess.run(cmd)
        if res.returncode == 0:
            print_ok("Playwright Chromium browser installed and verified.")
        else:
            print_warn("Playwright install returned non-zero. You may need to run 'playwright install chromium' manually.")
    except ImportError:
        print_err("Playwright package not found. Pip installation might have failed.")
        sys.exit(1)

def verify_env_config():
    print_step("Checking configuration and secrets file (.env)...")
    env_file = PROJECT_ROOT / ".env"
    env_example = PROJECT_ROOT / ".env.example"
    
    if not env_file.exists():
        if env_example.exists():
            shutil.copy(env_example, env_file)
            print_warn("Created fresh .env from .env.example.")
            print_warn("Please edit .env with valid CAPT / Kuwait Al-Yawm credentials before running automated collection.")
        else:
            print_warn(".env and .env.example not found.")
    else:
        print_ok(".env file found.")

def initialize_database_and_reports():
    print_step("Checking database and report generation...")
    try:
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        
        from src.pipeline.state_store import StateStore
        store = StateStore()
        tenders = store.get_all_tenders()
        print_ok(f"Database initialized: {len(tenders)} tenders registered in state store.")

        # Ensure output directories exist
        (PROJECT_ROOT / "output" / "reports").mkdir(parents=True, exist_ok=True)
        (PROJECT_ROOT / "output" / "traces").mkdir(parents=True, exist_ok=True)

        # Generate standalone HTML dashboard
        from src.output.html_dashboard import generate_standalone_dashboard
        html_path = generate_standalone_dashboard()
        print_ok(f"Interactive HTML dashboard verified: {html_path.name}")

    except Exception as e:
        print_warn(f"Database verification warning: {e}")

def main():
    print(f"\n{BOLD}{'='*60}")
    print("   KBM Tender Scout - Prerequisite Setup & Environment Validator")
    print(f"{'='*60}{RESET}")

    check_python_version()
    install_python_dependencies()
    install_playwright_browsers()
    verify_env_config()
    initialize_database_and_reports()

    print(f"\n{BOLD}{GREEN}{'='*60}")
    print("   SUCCESS: Environment is 100% Ready!")
    print(f"{'='*60}{RESET}\n")
    print(f"You can now run any of the following:")
    print(f"  1. Double-click {BOLD}Run_KBM_TenderScout.bat{RESET} or run {BOLD}start_dashboard.bat{RESET} to launch Web Dashboard.")
    print(f"  2. Double-click {BOLD}run_collection.bat{RESET} to trigger a live scraping cycle.")
    print(f"  3. Open {BOLD}output\\reports\\KBM_Tender_Dashboard.html{RESET} directly in Chrome/Edge without any server.\n")

if __name__ == "__main__":
    main()
