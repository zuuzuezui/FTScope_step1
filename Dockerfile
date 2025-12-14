# Dockerfile compatible Debian 12 (python:3.12-slim) — Selenium + Chrome
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies required for Chrome + Selenium (no recommends to keep image small)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    curl \
    xvfb \
    gnupg \
    ca-certificates \
    lsb-release \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-noto-color-emoji \
    libnss3 \
    libxss1 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libasound2 \
    xdg-utils \
    libxrandr2 \
    libxrender1 \
    libglib2.0-0 \
    libfreetype6 \
 && rm -rf /var/lib/apt/lists/*

# Install stable Google Chrome
RUN wget -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
 && apt-get update \
 && apt-get install -y --no-install-recommends /tmp/google-chrome.deb \
 && rm -f /tmp/google-chrome.deb \
 && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Copy repo
COPY . /app

# Install Python deps
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Mount point for persistent data (Render persistent disk or other)
VOLUME /var/data

# Default command
CMD ["python", "bot/bot.py"]
