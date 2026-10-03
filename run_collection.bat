@echo off
setlocal EnableDelayedExpansion
title KBM Tender Scout - Scraper Execution

echo ======================================================================
echo              KBM Tender Scout - Manual Collection Run
echo ======================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set PYTHON_CMD=.venv\Scripts\python.exe
) else (
    set PYTHON_CMD=python
)

echo [INFO] Running daily collection for CAPT and Kuwait Al-Yawm...
!PYTHON_CMD! src\run.py --portal all

echo.
echo [INFO] Collection complete. Check output\reports\ for the latest Excel and HTML files.
echo.
pause
