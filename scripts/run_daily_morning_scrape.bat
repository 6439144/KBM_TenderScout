@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ========================================================
echo   KBM Tender Scout - Daily Morning Scan (CAPT & Al-Yawm)
echo ========================================================
echo Date: %date% Time: %time%

cd /d "%~dp0\.."

:: Check if virtualenv exists
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [1/3] Running Live Portal Scraper (CAPT and Kuwait Al-Yawm)...
"%PYTHON_EXE%" -m src.main --portal all

echo [2/3] Reprocessing Scope & Presales Fit Qualification...
"%PYTHON_EXE%" scripts/reprocess_all_scopes_and_titles.py

echo [3/3] Regenerating Excel Reports & HTML Dashboard...
"%PYTHON_EXE%" scripts/generate_all_reports.py

echo ========================================================
echo   Daily Morning Scan Completed Successfully!
echo   Output Excel: output\reports\KBM_Tenders_Latest.xlsx
echo   Output HTML:  output\reports\KBM_Tender_Dashboard.html
echo ========================================================
timeout /t 5 > nul
