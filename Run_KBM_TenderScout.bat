@echo off
setlocal EnableDelayedExpansion
title KBM Tender Scout - One-Click Launcher

echo ======================================================================
echo           KBM Tender Scout - Public Tender Monitoring Engine
echo                   Khorafi Business Machines (KBM)
echo ======================================================================
echo.

:: 1. Check for Python installation
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    where py >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Python is not detected on this machine.
        echo.
        echo To run KBM Tender Scout, please install Python 3.10 or newer:
        echo   Option A: Run this command in PowerShell:
        echo             winget install Python.Python.3.11
        echo   Option B: Download installer from:
        echo             https://www.python.org/downloads/
        echo.
        echo (Make sure to check "Add Python to PATH" during installation)
        echo.
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py
    )
) else (
    set PYTHON_CMD=python
)

echo [OK] Python detected:
!PYTHON_CMD! --version
echo.

:: 2. Setup Virtual Environment (.venv)
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating isolated virtual environment in .venv...
    !PYTHON_CMD! -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
    echo.
)

set VENV_PYTHON=.venv\Scripts\python.exe

:: 3. Run Environment & Prerequisite Setup Script
echo [INFO] Verifying and installing required packages and Playwright browser...
!VENV_PYTHON! scripts\setup_environment.py
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Some prerequisites may have had warnings. Proceeding with launch...
)

echo.
echo ======================================================================
echo  Launching KBM Tender Scout Web Portal at http://127.0.0.1:8000
echo ======================================================================
echo.

:: 4. Open default web browser after 2 seconds
start "" http://127.0.0.1:8000

:: 5. Start FastAPI / Uvicorn server
!VENV_PYTHON! -m uvicorn src.web.app:app --host 127.0.0.1 --port 8000

pause
