import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from src.utils.helpers import random_sleep

logger = logging.getLogger(__name__)

NAUKRI_LOGIN = "https://www.naukri.com/nlogin/login"


def get_chrome_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(5)
    return driver


class NaukriApply:
    def __init__(self, settings):
        self.settings = settings
        self.driver   = get_chrome_driver(headless=settings.headless)
        self.wait     = WebDriverWait(self.driver, 15)
        self._login()

    def _login(self):
        try:
            self.driver.get(NAUKRI_LOGIN)
            random_sleep(3, 4)
            email_f = self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='text'], input[placeholder*='Email' i]")
                )
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", email_f)
            self.driver.execute_script("arguments[0].value = arguments[1];", email_f, self.settings.naukri_email)
            email_f.click()
            time.sleep(0.3)
            for c in self.settings.naukri_email[-4:]:
                email_f.send_keys(c)
                time.sleep(0.05)

            pass_f = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            self.driver.execute_script("arguments[0].value = arguments[1];", pass_f, self.settings.naukri_password)
            pass_f.click()
            time.sleep(0.3)
            for c in self.settings.naukri_password[-4:]:
                pass_f.send_keys(c)
                time.sleep(0.05)

            login_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'], .loginButton, button.btn-dark-ot"))
            )
            login_btn.click()
            random_sleep(4, 6)
            logger.info("Naukri apply session: logged in")
        except Exception as exc:
            logger.error(f"Naukri apply login error: {exc}")

    def _js_click(self, element):
        """Click via JavaScript to bypass element-not-interactable issues."""
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        time.sleep(0.5)
        self.driver.execute_script("arguments[0].click();", element)

    def apply(self, job: dict) -> dict:
        if not job.get("url"):
            return {"success": False, "reason": "No URL"}
        try:
            self.driver.get(job["url"])
            random_sleep(3, 5)

            apply_btn = None

            # Try specific selectors first
            for sel in [
                "button#apply-button", "a#apply-button",
                "button.apply-button", "button[id*='apply']",
                "a[id*='apply']",
            ]:
                elems = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if elems:
                    apply_btn = elems[0]
                    break

            # Fallback: any button with Apply text
            if not apply_btn:
                all_btns = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(normalize-space(),'Apply') "
                    "and not(contains(normalize-space(),'Already')) "
                    "and not(contains(normalize-space(),'Applied'))]"
                )
                if all_btns:
                    apply_btn = all_btns[0]

            if not apply_btn:
                return {"success": False, "reason": "Apply button not found"}

            btn_text = apply_btn.text.lower()
            if "already applied" in btn_text or "applied" in btn_text:
                return {"success": False, "reason": "Already applied"}

            # Use JS click to avoid interactable issues
            self._js_click(apply_btn)
            random_sleep(3, 5)

            # Handle confirmation popup if present
            try:
                confirm_btns = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(normalize-space(),'Apply') "
                    "or contains(normalize-space(),'Submit') "
                    "or contains(normalize-space(),'Confirm')]"
                )
                for btn in confirm_btns:
                    if any(kw in btn.text.lower() for kw in ("apply", "submit", "confirm")):
                        self._js_click(btn)
                        random_sleep(1, 2)
                        break
            except Exception: pass

            return {"success": True}
        except Exception as exc:
            logger.error(f"Naukri apply error [{job.get('title')}]: {exc}")
            return {"success": False, "reason": str(exc)}

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except Exception: pass