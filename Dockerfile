# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV WDM_LOCAL=1
ENV WDM_LOG_LEVEL=0

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates \
    gosu \
    nano \
    xvfb \
    xauth \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    tesseract-ocr \
    tesseract-ocr-eng \
    # Dependencies for Chrome
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxss1 \
    && rm -rf /var/lib/apt/lists/*

# Download and install Chrome 139
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable=139.* || apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* \
    # Create symlinks for consistent paths
    && ln -s /usr/bin/google-chrome-stable /usr/bin/chromium || true \
    && ln -s /usr/bin/google-chrome-stable /usr/bin/chromium-browser || true

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security (will be updated by entrypoint)
RUN groupadd -g 1000 appuser && useradd -u 1000 -g appuser -m appuser

# Copy application code
COPY . .

# Set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create directories for data persistence and webdriver cache
RUN mkdir -p /app/data /app/logs /app/.wdm

# Set HOME directory for webdriver cache
ENV HOME=/app

# Expose port
EXPOSE 1851

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:1851/api/status || exit 1

# Set entrypoint and default command
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "-m", "gunicorn", "--bind", "0.0.0.0:1851", "--workers", "1", "--timeout", "600", "wsgi:app"]
