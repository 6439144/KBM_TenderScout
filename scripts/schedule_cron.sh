#!/usr/bin/env bash
# Crontab configuration for KBM Tender Scout on Linux / Azure VM
# Runs daily Sunday through Thursday at 06:00 AM Kuwait time (UTC+3)

# 0 3 * * 0-4 (03:00 UTC = 06:00 Kuwait Time)
0 3 * * 0-4 cd /app && /usr/local/bin/python src/run.py --portal all >> /app/logs/cron.log 2>&1
