#!/bin/bash
echo "Starting KBM Tender Scout Web Application on Azure App Service..."
gunicorn -w 2 -k uvicorn.workers.UvicornWorker src.web.app:app --bind 0.0.0.0:8000 --timeout 120
