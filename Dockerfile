# Image Python
FROM python:3.11-slim

# Installer Chrome
RUN apt-get update && apt-get install -y wget unzip curl gnupg \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update && apt-get install -y google-chrome-stable

# Installer Chromedriver (compatible avec ta version de Chrome)
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+') \
    && wget -q "https://chromedriver.storage.googleapis.com/$CHROME_VERSION/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip -d /usr/local/bin/ \
    && rm chromedriver_linux64.zip

# Copier les fichiers du projet
WORKDIR /app
COPY . /app

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Définir le point d'entrée
CMD ["bash", "start.sh"]
