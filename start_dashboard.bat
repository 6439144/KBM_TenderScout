@echo off
title KBM Tender Scout Web Dashboard
echo ====================================================
echo  Starting KBM Tender Scout Interactive Web Portal...
echo ====================================================
echo.
echo Dashboard URL: http://127.0.0.1:8000
echo Offline HTML:  output\reports\KBM_Tender_Dashboard.html
echo.
start http://127.0.0.1:8000
python -m uvicorn src.web.app:app --host 127.0.0.1 --port 8000
pause
