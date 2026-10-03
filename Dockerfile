# Official Microsoft Playwright image with Python 3.10+ and all browser dependencies
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Kuwait

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium

# Copy application source code
COPY . .

# Expose Web Dashboard Port
EXPOSE 8000

# Default command: run FastAPI web dashboard
CMD ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
