FROM python:3.12-slim

# Set timezone and UTF-8 environment
ENV TZ=Asia/Kuwait \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Install system dependencies, Arabic fonts, and Playwright Chromium requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    fonts-noto-core \
    fonts-noto-cjk \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    curl \
    ca-certificates \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium

# Create directories
RUN mkdir -p config data logs output/reports docs

# Copy application source code
COPY src/ src/
COPY data/ data/
COPY config/ config/
COPY scripts/ scripts/

# Create a non-root user for secure operations
RUN useradd -m kbmuser && chown -R kbmuser:kbmuser /app
USER kbmuser

# Default command runs the orchestrator in manual or scheduled mode
CMD ["python", "src/run.py", "--portal", "all"]
