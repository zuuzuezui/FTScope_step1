# Dockerfile léger pour exécuter core1.py avec Chrome/Chromedriver
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies for Chromium + fonts + utils
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    unzip \
    wget \
    fonts-liberation \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libxrandr2 \
    libasound2 \
    libgbm1 \
    libgtk-3-0 \
    xvfb \
  && rm -rf /var/lib/apt/lists/*

# Install Chromium (the Debian chromium package)
RUN apt-get update && apt-get install -y --no-install-recommends chromium \
  && rm -rf /var/lib/apt/lists/*

# On Debian images chromedriver is not always packaged, but webdriver-manager will
# download a matching chromedriver at runtime. To help selenium find chrome binary:
ENV CHROME_BIN=/usr/bin/chromium
# If you prefer to install chromedriver system-wide, add installation steps here
# or set CHROMEDRIVER_PATH env var.

# Create app directory
WORKDIR /app
COPY . /app

# Install python deps
RUN pip install --no-cache-dir -r requirements.txt

# Make start script executable
RUN chmod +x /app/start.sh

# Expose default port (Render will set $PORT)
EXPOSE 10000

# Use start.sh as entrypoint
CMD ["/app/start.sh"]
