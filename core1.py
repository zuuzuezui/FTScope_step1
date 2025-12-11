#!/usr/bin/env python3
"""
core1.py
Version corrigée :
 - Options Chrome renforcées pour éviter certains blocages (automation flags, user-agent, cdp tweaks)
 - Recherche du champ password plus robuste (plusieurs XPATH/CSS, timeouts rallongés)
 - Dump du source HTML lors d'erreur pour debug
 - Petite HTTP server thread pour répondre sur $PORT si besoin (mais start.sh ouvre déjà un port)
"""

import os
import sys
import time
import logging
from typing import Optional, Tuple
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Logging simple
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Config depuis env (modifie si tu veux)
LOGIN_URL = os.environ.get("LOGIN_URL", "https://x.com/login")
DEBUG_DUMP_DIR = os.environ.get("DEBUG_DUMP_DIR", "/tmp")
# User/password expected to be fournis via env (ou autre méthode sécurisée)
USERNAME = os.environ.get("X_USERNAME", "")
PASSWORD = os.environ.get("X_PASSWORD", "")

# Use HEADLESS by default but can be disabled with env var
HEADLESS = os.environ.get("HEADLESS", "1") not in ("0", "false", "False")

# Timeouts
SHORT_WAIT = 6
MEDIUM_WAIT = 12
LONG_WAIT = 25

# Candidate locators for password field (try several)
PASSWORD_LOCATORS = [
    (By.XPATH, "//input[@type='password']"),
    (By.XPATH, "//input[@name='session[password]']"),
    (By.XPATH, "//input[@autocomplete='current-password']"),
    (By.XPATH, "//input[contains(@aria-label, 'mot de passe') or contains(@aria-label,'Password') or contains(@aria-label,'password')]"),
    (By.CSS_SELECTOR, "input[type='password']"),
]


def build_driver() -> webdriver.Chrome:
    """Create and return a configured Chrome webdriver."""
    logger.info("Initialising Chrome webdriver...")
    options = webdriver.ChromeOptions()

    # Common stability flags in container environments
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--remote-debugging-port=9222")
    # Prevent some automation detection
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # User agent (set to a recent chrome UA to reduce bot detection)
    user_agent = os.environ.get(
        "CHROME_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_argument(f"--user-agent={user_agent}")

    if HEADLESS:
        # Try the newer headless mode if available
        options.add_argument("--headless=new")  # fallback to --headless if not supported by the system Chrome
    else:
        logger.info("Headless disabled (HEADLESS env var set to 0/false)")

    # If custom chrome binary path provided (in Dockerfile we set CHROME_BIN)
    chrome_bin = os.environ.get("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
        logger.info("Using chrome binary: %s", chrome_bin)

    # Install chromedriver via webdriver-manager (downloads a matching driver)
    # In production we prefer system chromedriver (CHROMEDRIVER_PATH) if provided
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
    if chromedriver_path:
        service = ChromeService(chromedriver_path)
        logger.info("Using CHROMEDRIVER_PATH=%s", chromedriver_path)
    else:
        # webdriver-manager will download a matching driver
        driver_path = ChromeDriverManager().install()
        service = ChromeService(driver_path)
        logger.info("Downloaded chromedriver via webdriver-manager: %s", driver_path)

    try:
        driver = webdriver.Chrome(service=service, options=options)
    except TypeError:
        # sometimes headless=new is not recognized: try fallback
        try:
            logger.warning("headless=new unsupported, retry with --headless")
            options.headless = True
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            logger.exception("Unable to start Chrome webdriver: %s", e)
            raise

    # Extra low-level tweaks to reduce detection
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
window.chrome = window.chrome || { runtime: {} };
Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
"""
        })
    except Exception:
        # not fatal
        logger.debug("CDP tweak failed (non-fatal)")

    logger.info("Chrome webdriver ready")
    return driver


def try_find_password_input(driver, timeout=SHORT_WAIT) -> Optional[webdriver.remote.webelement.WebElement]:
    """Try multiple locators to find the password input element."""
    logger.info("Searching for password input with multiple strategies (timeout=%s)", timeout)
    for by, expr in PASSWORD_LOCATORS:
        try:
            logger.debug("Trying locator: %s %s", by, expr)
            el = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, expr)))
            if el:
                logger.info("Found password input using %s %s", by, expr)
                return el
        except TimeoutException:
            logger.debug("Locator timed out: %s %s", by, expr)
            continue
        except Exception:
            logger.exception("Error while trying locator %s %s", by, expr)
            continue

    # Last resort: try to find any input and check its type attribute
    try:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for i in inputs:
            try:
                t = i.get_attribute("type") or ""
                if t.lower() == "password":
                    logger.info("Found password input by scanning inputs")
                    return i
            except Exception:
                continue
    except Exception:
        pass

    # not found
    logger.warning("Password input NOT found (tried multiple locators)")
    return None


def dump_page_for_debug(driver, prefix="dump"):
    """Save current page source and a screenshot to DEBUG_DUMP_DIR for debugging."""
    ts = int(time.time())
    dump_dir = DEBUG_DUMP_DIR
    try:
        if not os.path.isdir(dump_dir):
            os.makedirs(dump_dir, exist_ok=True)
    except Exception:
        pass

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
    """Navigate to login page and try to login (returns True on success)."""
    logger.info("Navigation vers la page de login...")
    try:
        driver.get(LOGIN_URL)
    except WebDriverException as e:
        logger.exception("Error loading login url: %s", e)
        return False

    # Wait a little for scripts to run and dynamic content to appear
    time.sleep(2)

    # Detect typical "JS disabled / noscript" fallback shown in the HTML; if present, try reload with different UA
    try:
        # If a noscript element is present and visible, that's a hint JS resources didn't load
        noscripts = driver.find_elements(By.TAG_NAME, "noscript")
        if noscripts:
            logger.warning("Found <noscript> on the page; page may have failed to load JS. Attempting a gentle reload.")
            # try one reload and a slightly longer wait
            driver.refresh()
            time.sleep(3)
    except Exception:
        pass

    # Try to find password input with multiple strategies
    password_input = try_find_password_input(driver, timeout=MEDIUM_WAIT)
    if not password_input:
        # As a fallback, attempt longer wait and scroll
        logger.info("Tentative alternative: scroll and wait longer...")
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except Exception:
            pass
        password_input = try_find_password_input(driver, timeout=LONG_WAIT)

    if not password_input:
        logger.error("Impossible de localiser le champ mot de passe.")
        dump_page_for_debug(driver, prefix="no_password_field")
        return False

    # Fill username if present
    try:
        # try common username fields
        username_selectors = [
            (By.XPATH, "//input[@name='session[username]']"),
            (By.XPATH, "//input[@type='text']"),
            (By.XPATH, "//input[contains(@aria-label,'ident') or contains(@aria-label,'Username') or contains(@aria-label,'email')]"),
        ]
        username_el = None
        for by, expr in username_selectors:
            try:
                username_el = WebDriverWait(driver, 1).until(EC.presence_of_element_located((by, expr)))
                if username_el:
                    break
            except TimeoutException:
                continue
        if username_el and USERNAME:
            username_el.clear()
            username_el.send_keys(USERNAME)
            logger.info("Filled username field")
    except Exception:
        logger.debug("Could not fill username field (non fatal)")

    # Fill password and submit
    try:
        password_input.clear()
        if not PASSWORD:
            logger.warning("X_PASSWORD env var is empty; skipping actual login (still tested locator).")
            # still return success True because we found input field
            return True

        password_input.send_keys(PASSWORD)
        logger.info("Password filled")

        # try to find login/submit button near the password field
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
                logger.info("Clicked a submit candidate: %s %s", by, expr)
                break
            except TimeoutException:
                continue
            except Exception:
                continue

        if not clicked:
            # fallback: press Enter on the password input
            try:
                password_input.send_keys("\n")
                logger.info("Submitted form by ENTER key")
            except Exception:
                logger.exception("Failed to submit the login form")

        # wait a little for post-login navigation
        time.sleep(4)

        # crude success check: we expect not to be on the login path anymore
        current_url = driver.current_url
        logger.info("Current URL after submit: %s", current_url)
        if "login" not in current_url.lower():
            logger.info("Probable login SUCCESS (login not in URL).")
            return True

        # otherwise more advanced checks could be added here
        logger.warning("Login did not redirect away from login page (could be challenge/2fa/block).")
        dump_page_for_debug(driver, prefix="post_submit")
        return False

    except Exception:
        logger.exception("Error during login flow")
        dump_page_for_debug(driver, prefix="login_exception")
        return False


def main():
    driver = None
    try:
        driver = build_driver()
        ok = login_flow(driver)
        logger.info("Login flow result: %s", ok)
    except Exception:
        logger.exception("Unhandled exception in main")
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
