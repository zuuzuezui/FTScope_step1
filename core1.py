import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Variables d'environnement
TWITTER_USER = os.getenv("TWITTER_USER")
TWITTER_PASS = os.getenv("TWITTER_PASS")

def init_driver():
    """Initialise Chrome en mode headless."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Supprime si tu veux voir le navigateur
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = "/usr/bin/google-chrome"

    service = Service(executable_path="/usr/local/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login_to_twitter(driver):
    """Connexion à Twitter."""
    driver.get("https://twitter.com/login")
    time.sleep(2)

    # Remplir le formulaire
    driver.find_element(By.NAME, "text").send_keys(TWITTER_USER)
    driver.find_element(By.XPATH, "//span[contains(text(), 'Suivant')]").click()
    time.sleep(2)

    driver.find_element(By.NAME, "password").send_keys(TWITTER_PASS)
    driver.find_element(By.XPATH, "//span[contains(text(), 'Se connecter')]").click()
    time.sleep(5)

def publish_tweet(driver, text):
    """Publie un tweet."""
    driver.get("https://twitter.com/compose/tweet")
    time.sleep(3)

    textarea = driver.find_element(By.XPATH, "//div[@data-testid='tweetTextarea_0']")
    textarea.send_keys(text)
    time.sleep(1)

    driver.find_element(By.XPATH, "//div[@data-testid='tweetButton']").click()
    time.sleep(5)

def main():
    driver = init_driver()
    try:
        login_to_twitter(driver)
        publish_tweet(driver, "connected")
        print("Tweet publié avec succès !")
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
