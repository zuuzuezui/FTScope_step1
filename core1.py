import os
import time
import signal
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Variables d'environnement (configurer X_USER / X_PASS dans Render environment)
X_USER = os.getenv("X_USER") or os.getenv("TWITTER_USER")
X_PASS = os.getenv("X_PASS") or os.getenv("TWITTER_PASS")

if not X_USER or not X_PASS:
    print("ERREUR: variables d'environnement X_USER et X_PASS requises.")
    sys.exit(1)

def init_driver():
    options = Options()
    # 'headless=new' fonctionne mieux sur Chrome/Chromium récents; si pb utilisez '--headless'
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # binaire (Chromium) si présent
    chromium_bin = os.getenv("CHROMIUM_BIN", "/usr/bin/chromium")
    if os.path.exists(chromium_bin):
        options.binary_location = chromium_bin

    driver_path = os.getenv("CHROMEDRIVER", "/usr/bin/chromedriver")
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver

def wait_for_clickable(driver, by, selector, timeout=15):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, selector)))

def wait_for_presence(driver, by, selector, timeout=15):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))

def login_to_x(driver):
    print("Navigation vers la page de login...")
    driver.get("https://x.com/login")
    # Champ username/email/phone (name="text" sur beaucoup de flows)
    try:
        inp = wait_for_presence(driver, By.NAME, "text", timeout=15)
        inp.clear()
        inp.send_keys(X_USER)
        # bouton Next (texte peut varier selon langue)
        btn = wait_for_clickable(driver, By.XPATH, "//span[contains(text(),'Next') or contains(text(),'Suivant')]", timeout=10)
        btn.click()
    except Exception:
        # fallback: essayer un autre selecteur
        print("Hint: champ 'text' non trouvé, tentative alternative...")
    # attendre le champ password
    pwd = wait_for_presence(driver, By.NAME, "password", timeout=15)
    pwd.clear()
    pwd.send_keys(X_PASS)
    # bouton login
    try:
        login_btn = wait_for_clickable(driver, By.XPATH, "//span[contains(text(),'Log in') or contains(text(),'Se connecter') or contains(text(),'Se connecter')]", timeout=10)
        login_btn.click()
    except Exception:
        # essai alternative : bouton role=button with tweet compose maybe accessible after login
        print("Bouton 'Log in' non trouvé via XPath standard, tentative d'envoi via Enter.")
        pwd.submit()

    # attendre un élément qui indique qu'on est connecté (ex: compose tweet)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//a[@href='/home' or contains(@href,'/compose')]"))
        )
        print("Login effectué (ou élément de page attendue présent).")
    except Exception as e:
        print("Attention : échec de détection de connexion complète (captcha/2FA possible).", e)

def tweet_connected(driver):
    try:
        driver.get("https://x.com/compose/tweet")
        textarea = wait_for_presence(driver, By.XPATH, "//div[@data-testid='tweetTextarea_0']", timeout=10)
        # click pour focus
        try:
            textarea.click()
        except Exception:
            pass
        textarea.send_keys("connected")
        tweet_btn = wait_for_clickable(driver, By.XPATH, "//div[@data-testid='tweetButton' or @data-testid='toolBar']/div", timeout=10)
        tweet_btn.click()
        print("Tweet envoyé: connected")
    except Exception as e:
        print("Erreur en postant le tweet:", e)

def graceful_exit(signum, frame):
    print("Signal reçu, arrêt propre...")
    sys.exit(0)

def main():
    signal.signal(signal.SIGTERM, graceful_exit)
    signal.signal(signal.SIGINT, graceful_exit)

    driver = None
    try:
        driver = init_driver()
        login_to_x(driver)
        # boucle d'envoi toutes les 10 secondes
        while True:
            tweet_connected(driver)
            time.sleep(10)
    except Exception as e:
        print("Erreur principale :", e)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        print("Terminé.")

if __name__ == "__main__":
    main()
