import os
import sys
import zipfile
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {".git", ".github", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "scratch"}
EXCLUDE_EXTS = {".pyc", ".pyo", ".tmp"}

def deploy():
    zip_path = PROJECT_ROOT / "deploy.zip"
    print("1. Creating deployment zip package...")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            root_p = Path(root)
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for f in files:
                f_p = root_p / f
                rel_p = f_p.relative_to(PROJECT_ROOT)
                
                if f_p.suffix in EXCLUDE_EXTS:
                    continue
                if f == ".env" or f == "deploy.zip":
                    continue
                if "output" in rel_p.parts and "traces" in rel_p.parts:
                    continue
                    
                zf.write(f_p, arcname=str(rel_p))
                
    print(f"Zip created ({zip_path.stat().st_size / (1024*1024):.2f} MB)")
    
    print("2. Deploying to Azure App Service 'kbm-tenderscout'...")
    cmd = [
        "az", "webapp", "deploy",
        "--resource-group", "rg-kbm-platform",
        "--name", "kbm-tenderscout",
        "--src-path", str(zip_path),
        "--type", "zip",
        "--async", "false"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    print("Azure CLI STDOUT:", res.stdout)
    if res.stderr:
        print("Azure CLI STDERR:", res.stderr)
        
    if zip_path.exists():
        zip_path.unlink()
        
    print("Deployment finished!")

if __name__ == "__main__":
    deploy()
