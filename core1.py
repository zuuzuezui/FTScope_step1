import os
import time
import signal
import sys
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Configuration via env vars ---
X_USER = os.getenv("X_USER") or os.getenv("TWITTER_USER")
X_PASS = os.getenv("X_PASS") or os.getenv("TWITTER_PASS")

if not X_USER or not X_PASS:
    print("ERREUR: X_USER et X_PASS doivent être définis dans les variables d'environnement.")
    sys.exit(1)

CHROMIUM_BIN = os.getenv("CHROMIUM_BIN", "/usr/bin/chromium")
CHROMEDRIVER_BIN = os.getenv("CHROMEDRIVER", "/usr/bin/chromedriver")

# --- Helpers ---
def init_driver():
    options = Options()
    # headless recommended for Render; fallback if not supported
    try:
        options.add_argument("--headless=new")
    except Exception:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--window-size=1920,1080")
    # realistic user agent to help JS render consistently
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    )

    if os.path.exists(CHROMIUM_BIN):
        options.binary_location = CHROMIUM_BIN

    service = Service(executable_path=CHROMEDRIVER_BIN)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver

def wait_presence(driver, by, selector, timeout=15):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))

def wait_clickable(driver, by, selector, timeout=15):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, selector)))

def find_and_click_dynamic_button(driver, texts=("next","suivant","continue","log in","se connecter","connexion","login")):
    # cherche boutons role=button et clique sur celui dont le texte contient l'un des mots
    btns = driver.find_elements(By.XPATH, "//div[@role='button' or button]")
    for btn in btns:
        try:
            txt = (btn.text or "").strip().lower()
            if not txt:
                continue
            for t in texts:
                if t in txt:
                    try:
                        btn.click()
                        return True
                    except Exception:
                        # tentative JS click
                        driver.execute_script("arguments[0].click();", btn)
                        return True
        except Exception:
            continue
    return False

# --- Login & tweet flows ---
def login_flow(driver):
    print("Navigation vers la page de login...")
    # essayer les deux routes possibles
    for url in ("https://x.com/i/flow/login", "https://x.com/login", "https://twitter.com/i/flow/login"):
        try:
            driver.get(url)
            time.sleep(2)
        except Exception:
            continue

        # 1) chercher input username/email générique
        try:
            username_xpath = (
                "//input[@autocomplete='username' or @name='session[username_or_email]' "
                "or @name='text' or contains(@placeholder,'phone') or contains(@placeholder,'email') "
                "or contains(@placeholder,'username')]"
            )
            username_input = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, username_xpath))
            )
            username_input.clear()
            username_input.send_keys(X_USER)
            time.sleep(0.8)
        except Exception:
            # fallback : chercher tout input visible de type text
            try:
                inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='email']")
                for inp in inputs:
                    if inp.is_displayed():
                        inp.clear()
                        inp.send_keys(X_USER)
                        break
            except Exception:
                pass

        # 2) essayer de cliquer next/dynamic button
        clicked = find_and_click_dynamic_button(driver, texts=("next","suivant","continue","suiv","weiter"))
        if clicked:
            time.sleep(2)
        else:
            # pas critique, on continue
            time.sleep(1)

        # 3) chercher password
        try:
            pwd_xpath = "//input[@name='password' or @type='password']"
            password_input = WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, pwd_xpath)))
            password_input.clear()
            password_input.send_keys(X_PASS)
            time.sleep(0.6)
        except Exception:
            # si pas trouvé, peut être déjà sur une page qui demande autre chose
            print("Champ password non détecté immédiatement, tentative alternative...")
            # on retente quelques secondes
            try:
                password_input = WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
                password_input.clear()
                password_input.send_keys(X_PASS)
            except Exception:
                print("Impossible de localiser le champ mot de passe.")
                raise

        # 4) envoyer le formulaire : essayer de cliquer sur bouton de connexion
        clicked_login = find_and_click_dynamic_button(driver, texts=("log in","se connecter","connexion","sign in","log in","login"))
        if not clicked_login:
            try:
                password_input.send_keys(Keys.ENTER)
            except Exception:
                pass

        # 5) attendre indicateur de connexion (timeline/home or compose)
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[@href='/home' or contains(@href,'/compose') or //div[@aria-label='Timeline: Your Home Timeline']]")
                )
            )
            print("Connexion détectée (élément d'interface présent).")
            return True
        except Exception as e:
            # ne pas arrêter tout de suite: peut être challenge/captcha/2FA ou autre
            print("Attention : connexion non-détectée automatiquement (captcha/2FA possible) :", e)
            # on retourne False pour indiquer que le flow n'a pas garanti la connexion
            return False

    # si loop url s'est terminée sans succès
    return False

def post_connected(driver):
    try:
        # ouvrir la composition
        driver.get("https://x.com/compose/tweet")
        # attendre textarea (plusieurs selectors de secours)
        textarea = None
        try:
            textarea = WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, "//div[@data-testid='tweetTextarea_0' or @aria-label='Tweet text' or @role='textbox']")))
        except Exception:
            # fallback: cherche tout role=composition textbox
            els = driver.find_elements(By.XPATH, "//div[@role='textbox']")
            for el in els:
                if el.is_displayed():
                    textarea = el
                    break

        if textarea is None:
            raise Exception("Textarea pour tweet introuvable")

        try:
            textarea.click()
        except Exception:
            pass

        textarea.send_keys("connected")
        time.sleep(0.4)

        # bouton tweet
        tweet_btn = None
        try:
            tweet_btn = WebDriverWait(driver, 6).until(EC.element_to_be_clickable((By.XPATH, "//div[@data-testid='tweetButton']")))
        except Exception:
            # fallback : chercher un bouton affiché contenant 'Tweet' / 'Tweeter'
            btns = driver.find_elements(By.XPATH, "//div[@role='button']")
            for b in btns:
                try:
                    txt = (b.text or "").strip().lower()
                    if "tweet" in txt or "tweeter" in txt or "envoyer" in txt:
                        tweet_btn = b
                        break
                except Exception:
                    continue

        if tweet_btn is None:
            raise Exception("Bouton d'envoi introuvable")

        try:
            tweet_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", tweet_btn)

        print("Tweet envoyé: connected")
    except Exception as e:
        print("Erreur lors de la publication :", e)
        traceback.print_exc()

# --- Graceful shutdown ---
stop_requested = False
def handle_signal(sig, frame):
    global stop_requested
    print("Signal reçu, demande d'arrêt...")
    stop_requested = True

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

# --- Main loop ---
def main():
    driver = None
    try:
        driver = init_driver()
        success = login_flow(driver)
        if not success:
            print("Login non confirmé par détection automatique. Vérifie manuellement si nécessaire.")
        # boucle d'envoi toutes les 10 secondes (contrôlable)
        while not stop_requested:
            try:
                post_connected(driver)
            except Exception as e:
                print("Erreur dans la boucle de publication :", e)
                traceback.print_exc()
            # sleep with early stop
            for _ in range(10):
                if stop_requested:
                    break
                time.sleep(1)
    except Exception as ex:
        print("Erreur critique :", ex)
        traceback.print_exc()
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        print("Arrêt complet.")

if __name__ == "__main__":
    main()
