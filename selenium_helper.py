import time
import random
from selenium.webdriver.common.action_chains import ActionChains

def random_sleep(a=0.5, b=2.0):
    time.sleep(random.uniform(a, b))

def human_typing(element, text: str, min_delay=0.04, max_delay=0.16):
    for ch in text:
        element.send_keys(ch)
        time.sleep(random.uniform(min_delay, max_delay))

def random_mouse_movements(driver, iterations=3):
    actions = ActionChains(driver)
    elements = driver.find_elements("css selector", "a, button, div, span")
    if not elements:
        driver.execute_script("window.scrollBy(0, 100);")
        random_sleep(0.2, 0.6)
        return
    for _ in range(iterations):
        elem = random.choice(elements)
        try:
            actions.move_to_element(elem).perform()
            random_sleep(0.2, 0.8)
        except Exception:
            driver.execute_script("window.scrollBy(0, %s);" % random.randint(-200, 200))
            random_sleep(0.2, 0.6)

def progressive_scroll(driver, max_scrolls=5):
    for _ in range(random.randint(1, max_scrolls)):
        driver.execute_script(f"window.scrollBy(0, {random.randint(300, 900)});")
        random_sleep(0.8, 2.0)
