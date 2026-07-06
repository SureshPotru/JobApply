import time
import random
import logging

logger = logging.getLogger(__name__)


def get_driver(headless: bool = True):
    """Return Chrome WebDriver. Tries undetected_chromedriver first, falls back to Selenium."""
    chrome_args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--window-size=1920,1080",
        "--disable-blink-features=AutomationControlled",
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    try:
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        for arg in chrome_args:
            options.add_argument(arg)
        driver = uc.Chrome(options=options, use_subprocess=True)
        driver.implicitly_wait(5)
        logger.debug("Driver: undetected_chromedriver")
        return driver
    except Exception as exc:
        logger.warning(f"undetected_chromedriver failed ({exc}), falling back to Selenium")
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        for arg in chrome_args:
            options.add_argument(arg)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(5)
        logger.debug("Driver: standard Selenium + webdriver-manager")
        return driver


def random_sleep(min_s: float = 1.0, max_s: float = 3.0):
    time.sleep(random.uniform(min_s, max_s))


def scroll_down(driver, pixels: int = 2500):
    driver.execute_script(f"window.scrollTo(0, {pixels});")
    random_sleep(1.0, 1.5)
    driver.execute_script("window.scrollTo(0, 0);")
    random_sleep(0.3, 0.7)


def slow_type(element, text: str, delay: float = 0.05):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.02, delay))
