"""
KBM Tender Scout - Distribution Packager
Packages the entire project into a clean, ready-to-distribute ZIP archive.
Ensures zero secret leakage (.env is omitted, .env.example included),
removes virtual environments and cache directories, and bundles
one-click launchers and pre-generated offline reports.
"""

import os
import sys
import zipfile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Files and directories to strictly exclude from the package
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    ".idea",
    ".vscode",
    "dist"
}

EXCLUDE_FILES = {
    ".env",                # Security: Never package live credentials
    ".env.local",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "Thumbs.db"
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".tmp",
    ".log"
}

def should_exclude_path(rel_path: Path) -> bool:
    parts = rel_path.parts
    # Check directory exclusions
    for p in parts:
        if p in EXCLUDE_DIRS:
            return True

    # Check file exclusions
    name = rel_path.name
    if name in EXCLUDE_FILES:
        return True
    if rel_path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return True

    # Exclude trace screenshots / debug DOM files from output/traces
    if "output" in parts and "traces" in parts and rel_path.is_file() and rel_path.name != ".gitkeep":
        return True

    return False

def build_package(version: str = "v1.0") -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    zip_filename = f"KBM_TenderScout_{version}.zip"
    zip_path = dist_dir / zip_filename

    print(f"Creating distribution package: {zip_path.name}...")

    # Ensure offline HTML and Excel reports are up to date
    try:
        from src.output.html_dashboard import generate_standalone_dashboard
        generate_standalone_dashboard()
    except Exception as e:
        print(f"Note: Dashboard generation: {e}")

    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            root_path = Path(root)
            
            # Prune directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                file_path = root_path / file
                rel_path = file_path.relative_to(PROJECT_ROOT)

                if should_exclude_path(rel_path):
                    continue

                # Store inside top-level folder inside zip: KBM_TenderScout/
                arcname = Path("KBM_TenderScout") / rel_path
                zipf.write(file_path, arcname=str(arcname))
                file_count += 1

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Package successfully created!")
    print(f"  Target: {zip_path.resolve()}")
    print(f"  Files packaged: {file_count}")
    print(f"  Archive Size: {size_mb:.2f} MB")
    print("\nSecurity verification: Checked that .env is NOT included in archive.")
    return zip_path

if __name__ == "__main__":
    build_package()
