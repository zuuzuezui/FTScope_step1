#!/usr/bin/env python3
"""
core1.py - version Docker-friendly avec retry Chrome et login flow
"""

import os
import sys
import time
import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Logging simple
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Config depuis env
LOGIN_URL = os.environ.get("LOGIN_URL", "https://x.com/login")
DEBUG_DUMP_DIR = os.environ.get("DEBUG_DUMP_DIR", "/tmp")
USERNAME = os.environ.get("X_USERNAME", "")
PASSWORD = os.environ.get("X_PASSWORD", "")

HEADLESS = os.environ.get("HEADLESS", "1") not in ("0", "false", "False")

# Timeouts
SHORT_WAIT = 6
MEDIUM_WAIT = 12
LONG_WAIT = 25

PASSWORD_LOCATORS = [
    (By.XPATH, "//input[@type='password']"),
    (By.XPATH, "//input[@name='session[password]']"),
    (By.XPATH, "//input[@autocomplete='current-password']"),
    (By.XPATH, "//input[contains(@aria-label, 'mot de passe') or contains(@aria-label,'Password') or contains(@aria-label,'password')]"),
    (By.CSS_SELECTOR, "input[type='password']"),
]

def build_driver() -> webdriver.Chrome:
    """Crée et retourne un Chrome WebDriver configuré avec retry."""
    chrome_bin = os.environ.get('CHROME_BIN', '/usr/bin/chromium')
    headless = os.environ.get('HEADLESS', '1') in ['1', 'true', 'True']

    options = Options()
    options.binary_location = chrome_bin

    # Flags Docker / headless
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-background-networking')
    options.add_argument('--disable-sync')
    options.add_argument('--disable-translate')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--window-size=1920,1080')
    if headless:
        options.add_argument('--headless=new')

    # Retry WebDriver en cas d'échec
    for attempt in range(3):
        try:
            driver_path = ChromeDriverManager().install()
            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=options)
            logger.info("Chrome WebDriver ready (attempt %d)", attempt+1)
            return driver
        except Exception as e:
            logger.warning("WebDriver failed to start, retry %d/3: %s", attempt+1, e)
            time.sleep(2)
    raise RuntimeError("Chrome WebDriver failed to start after 3 attempts")

def try_find_password_input(driver, timeout=SHORT_WAIT) -> Optional[webdriver.remote.webelement.WebElement]:
    """Recherche le champ mot de passe avec plusieurs stratégies."""
    logger.info("Searching for password input (timeout=%s)", timeout)
    for by, expr in PASSWORD_LOCATORS:
        try:
            el = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, expr)))
            if el:
                logger.info("Found password input using %s %s", by, expr)
                return el
        except TimeoutException:
            continue
        except Exception:
            logger.exception("Error while trying locator %s %s", by, expr)

    # fallback: scan all inputs
    try:
        for i in driver.find_elements(By.TAG_NAME, "input"):
            if (i.get_attribute("type") or "").lower() == "password":
                logger.info("Found password input by scanning inputs")
                return i
    except Exception:
        pass

    logger.warning("Password input NOT found")
    return None

def dump_page_for_debug(driver, prefix="dump"):
    """Sauvegarde page HTML et screenshot pour debug."""
    ts = int(time.time())
    dump_dir = DEBUG_DUMP_DIR
    os.makedirs(dump_dir, exist_ok=True)

    html_path = os.path.join(dump_dir, f"{prefix}_{ts}.html")
    png_path = os.path.join(dump_dir, f"{prefix}_{ts}.png")
    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot(png_path)
        logger.info("Dumped HTML -> %s and screenshot -> %s", html_path, png_path)
    except Exception:
        logger.exception("Failed to dump page for debug")

def login_flow(driver) -> bool:
    """Navigue vers login page et tente login."""
    logger.info("Navigation vers la page de login...")
    try:
        driver.get(LOGIN_URL)
        time.sleep(2)
    except WebDriverException as e:
        logger.exception("Error loading login url: %s", e)
        return False

    # Detect JS disabled / <noscript>
    try:
        if driver.find_elements(By.TAG_NAME, "noscript"):
            logger.warning("<noscript> detected, refreshing page")
            driver.refresh()
            time.sleep(3)
    except Exception:
        pass

    password_input = try_find_password_input(driver, timeout=MEDIUM_WAIT)
    if not password_input:
        logger.info("Fallback scroll and wait longer")
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except Exception:
            pass
        password_input = try_find_password_input(driver, timeout=LONG_WAIT)

    if not password_input:
        logger.error("Password field not found")
        dump_page_for_debug(driver, prefix="no_password_field")
        return False

    # Fill username
    try:
        username_selectors = [
            (By.XPATH, "//input[@name='session[username]']"),
            (By.XPATH, "//input[@type='text']"),
            (By.XPATH, "//input[contains(@aria-label,'ident') or contains(@aria-label,'Username') or contains(@aria-label,'email')]"),
        ]
        for by, expr in username_selectors:
            try:
                username_el = WebDriverWait(driver, 1).until(EC.presence_of_element_located((by, expr)))
                if username_el and USERNAME:
                    username_el.clear()
                    username_el.send_keys(USERNAME)
                    logger.info("Filled username field")
                    break
            except TimeoutException:
                continue
    except Exception:
        logger.debug("Could not fill username (non fatal)")

    # Fill password and submit
    try:
        password_input.clear()
        if PASSWORD:
            password_input.send_keys(PASSWORD)
            logger.info("Password filled")

        # Submit: button or ENTER
        submit_candidates = [
            (By.XPATH, "//div[@role='button' and (./descendant::span[contains(text(),'Se connecter') or contains(text(),'Log in') or contains(text(),'Sign in')]) ]"),
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//div[@data-testid='LoginForm_Login_Button']"),
            (By.XPATH, "//div[@role='button' and contains(., 'Connexion')]"),
        ]
        clicked = False
        for by, expr in submit_candidates:
            try:
                btn = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((by, expr)))
                btn.click()
                clicked = True
                logger.info("Clicked submit candidate")
                break
            except TimeoutException:
                continue
            except Exception:
                continue
        if not clicked:
            password_input.send_keys("\n")
            logger.info("Submitted form by ENTER key")

        time.sleep(4)
        current_url = driver.current_url
        logger.info("Current URL after submit: %s", current_url)
        if "login" not in current_url.lower():
            logger.info("Probable login SUCCESS")
            return True

        logger.warning("Login did not redirect away from login page")
        dump_page_for_debug(driver, prefix="post_submit")
        return False

    except Exception:
        logger.exception("Error during login flow")
        dump_page_for_debug(driver, prefix="login_exception")
        return False

def main():
    logger.info(f"HEADLESS={os.environ.get('HEADLESS')}, CHROME_BIN={os.environ.get('CHROME_BIN')}")
    driver = build_driver()
    logger.info("Chrome WebDriver successfully started")
    try:
        ok = login_flow(driver)
        logger.info(f"Login flow result: {ok}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    main()
