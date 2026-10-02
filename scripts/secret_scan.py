#!/usr/bin/env python3
"""
Pre-commit Secret Scanner for KBM Tender Scout
Strictly enforces Rule 3.1: Never put credentials in code, config, commits, logs,
screenshots, traces, test fixtures, LLM prompts, or error messages.
"""

import sys
import re
import subprocess
from pathlib import Path

# Ensure UTF-8 output even on Windows consoles with cp1252
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Forbidden patterns that indicate hardcoded secrets or sensitive tokens
SECRET_PATTERNS = [
    (r'(?i)(capt|alyawm|kbm|portal)[_-]?(password|secret|pwd)\s*[:=]\s*["\']([^"\'\s]{3,})["\']', "Hardcoded portal password"),
    (r'(?i)(api[_-]?key|access[_-]?token|bearer[_-]?token)\s*[:=]\s*["\']([^"\'\s]{8,})["\']', "Potential hardcoded API token"),
    (r'(?i)ai_zaSy[0-9A-Za-z_-]{35}', "Google Gemini API key pattern"),
    (r'(?i)sk-[a-zA-Z0-9]{32,}', "OpenAI secret key pattern"),
    (r'-----BEGIN\s+(RSA|OPENSSH|DSA|EC|PGP)?\s*PRIVATE KEY-----', "Private cryptographic key"),
    (r'(?i)password\s*[:=]\s*["\'](?![$%{\[])[a-zA-Z0-9@#$%^&*!]{6,}["\']', "Generic hardcoded password assignment"),
]

# Files or patterns allowed to be skipped
EXCLUDED_PATHS = [
    Path(".git"),
    Path(".venv"),
    Path("venv"),
    Path("__pycache__"),
    Path(".env.example"),  # template file
]

def get_tracked_or_staged_files():
    """Returns a list of files that are staged or tracked by git."""
    try:
        # Check staged files first
        res = subprocess.run(["git", "diff", "--name-only", "--cached"], capture_output=True, text=True, check=True)
        files = [Path(f.strip()) for f in res.stdout.splitlines() if f.strip()]
        if not files:
            # If nothing staged, check all git tracked files
            res = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
            files = [Path(f.strip()) for f in res.stdout.splitlines() if f.strip()]
        return files
    except Exception:
        # Fallback to walking workspace if git fails
        return [p for p in Path(".").rglob("*") if p.is_file()]

def scan_file(file_path: Path):
    """Scans an individual file for prohibited secret patterns."""
    if any(excluded in file_path.parents or file_path == excluded for excluded in EXCLUDED_PATHS):
        return []

    # Block committing real .env files
    if file_path.name.startswith(".env") and file_path.name != ".env.example":
        return [(0, "Attempted commit of active .env file", "CRITICAL")]

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return [(0, f"Could not read file: {e}", "WARNING")]

    findings = []
    lines = content.splitlines()
    for line_num, line in enumerate(lines, start=1):
        for pattern, desc in SECRET_PATTERNS:
            if re.search(pattern, line):
                # Avoid flagging benign references in open decisions doc or comments explaining keys
                if "CAPT_PASSWORD" in line and ("secret name" in line.lower() or "secret_secret" in line.lower() or "secret names:" in line.lower() or line.strip().startswith("#")):
                    continue
                findings.append((line_num, desc, line.strip()[:80]))
    return findings

def main():
    files = get_tracked_or_staged_files()
    total_violations = 0

    print("🔍 Running KBM Pre-Commit Secret Scanner...")
    for f in files:
        if not f.is_file():
            continue
        findings = scan_file(f)
        if findings:
            for line_no, desc, snippet in findings:
                print(f"❌ [SECRET VIOLATION] {f}:{line_no} - {desc}")
                print(f"   Snippet: {snippet}")
                total_violations += 1

    if total_violations > 0:
        print(f"\n🚨 Secret Scan Failed: Found {total_violations} potential secret leakage(s).")
        print("Action required: Remove all hardcoded credentials. Use environment variables or a vault.")
        sys.exit(1)
    else:
        print("✅ Secret Scan Passed: No credentials or sensitive tokens detected.")
        sys.exit(0)

if __name__ == "__main__":
    main()
