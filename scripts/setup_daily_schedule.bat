@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ========================================================
echo   KBM Tender Scout - Setup Windows Daily Morning Task
echo ========================================================
echo This script registers a daily task in Windows Task Scheduler
echo to run KBM Tender Scout automatically every morning at 8:00 AM.
echo.

set "SCRIPT_PATH=%~dp0run_daily_morning_scrape.bat"

schtasks /create /tn "KBM_TenderScout_DailyScan" /tr "\"%SCRIPT_PATH%\"" /sc daily /st 08:00 /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Scheduled task "KBM_TenderScout_DailyScan" created successfully!
    echo It will run automatically every morning at 8:00 AM (Kuwait Time).
    echo.
) else (
    echo.
    echo [ERROR] Failed to create scheduled task. Please run this script as Administrator.
    echo.
)

pause
