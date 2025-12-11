# --- en-têtes et imports en haut du fichier --------------
logging.info('Retrying webdriver start with forced headless and additional flags...')
# reconstruire options
options = webdriver.ChromeOptions()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--disable-extensions')
options.add_argument('--disable-setuid-sandbox')
options.add_argument('--remote-debugging-port=0')
options.add_argument('--window-size=1920,1080')
options.binary_location = chrome_bin
time.sleep(1)
try:
driver = webdriver.Chrome(service=service, options=options)
return driver
except Exception as exc2:
logging.exception('Second attempt to start Chrome also failed: %s', exc2)
raise
else:
raise


# --- utilisation dans main --------------------------------


def main():
# ton code existant ...
driver = build_driver()
# ... suite du programme


if __name__ == '__main__':
main()
