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
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Optionnel pour test en arrière-plan
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(executable_path="/usr/local/bin/chromedriver")  # Chemin vers chromedriver
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login_to_x(driver):
    driver.get("https://x.com/login")  # Anciennement Twitter
    time.sleep(2)

    # Remplir le formulaire de connexion
    driver.find_element(By.NAME, "text").send_keys(X_USER)
    driver.find_element(By.XPATH, "//span[contains(text(), 'Next') or contains(text(),'Suivant')]").click()
    time.sleep(2)

    driver.find_element(By.NAME, "password").send_keys(X_PASS)
    driver.find_element(By.XPATH, "//span[contains(text(), 'Log in') or contains(text(),'Se connecter')]").click()
    time.sleep(5)

def tweet_connected(driver):
    driver.get("https://x.com/compose/tweet")
    time.sleep(3)
    textarea = driver.find_element(By.XPATH, "//div[@data-testid='tweetTextarea_0']")
    textarea.send_keys("connected")
    driver.find_element(By.XPATH, "//div[@data-testid='tweetButton']").click()
    time.sleep(2)

def main():
    driver = init_driver()
    try:
        login_to_x(driver)
        while True:
            tweet_connected(driver)
            print("Tweeted: connected")
            time.sleep(10)
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()

