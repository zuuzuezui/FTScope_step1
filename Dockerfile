# Dockerfile optimisé pour exécuter une app Selenium/Chromium en container
FROM python:3.11-slim


ENV DEBIAN_FRONTEND=noninteractive


# Installer chromium + dépendances minimales et utilitaires (iproute2 pour ss)
RUN apt-get update \
&& apt-get install -y --no-install-recommends \
chromium \
fonts-liberation \
iproute2 \
ca-certificates \
libnss3 \
libatk1.0-0 \
libatk-bridge2.0-0 \
libxss1 \
libasound2 \
libgtk-3-0 \
&& rm -rf /var/lib/apt/lists/*


# Définit le binaire Chromium system-wide
ENV CHROME_BIN=/usr/bin/chromium
ENV PATH="/root/.local/bin:$PATH"


WORKDIR /app


# Copier et installer requirements (assure-toi d'avoir requirements.txt dans ton repo)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


# Copier le reste de l'app
COPY . .


# Permissions
RUN chmod +x start.sh


# Démarrage
CMD ["./start.sh"]
