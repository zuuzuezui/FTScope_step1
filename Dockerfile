FROM python:3.12-slim

# Install dependencies for Chrome & Selenium (Debian 12 compatible)
RUN apt-get update && \
    apt-get install -y \
    wget unzip curl xvfb gnupg \
    libnss3 \
    fonts-liberation \
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
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y /tmp/google-chrome.deb && \
    rm /tmp/google-chrome.deb

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip && pip install -r requirements.txt

VOLUME /var/data

CMD ["python", "bot/bot.py"]
v
