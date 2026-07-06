import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from src.utils.helpers import random_sleep

logger = logging.getLogger(__name__)

LINKEDIN_LOGIN = "https://www.linkedin.com/login"


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
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.implicitly_wait(5)
    return driver


class LinkedInApply:
    def __init__(self, settings):
        self.settings = settings
        self.driver   = get_chrome_driver(headless=settings.headless)
        self.wait     = WebDriverWait(self.driver, 15)
        self._login()

    def _login(self):
        try:
            self.driver.get(LINKEDIN_LOGIN)
            random_sleep(3, 4)
            email_f = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            for c in self.settings.linkedin_email:
                email_f.send_keys(c)
                time.sleep(0.04)
            pass_f = self.driver.find_element(By.ID, "password")
            for c in self.settings.linkedin_password:
                pass_f.send_keys(c)
                time.sleep(0.04)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            random_sleep(4, 6)
            url = self.driver.current_url
            if "checkpoint" in url or "challenge" in url:
                logger.warning(f"LinkedIn security checkpoint: {url}")
            else:
                logger.info("LinkedIn apply session: logged in")
        except Exception as exc:
            logger.error(f"LinkedIn apply login error: {exc}")

    def _fill_form_fields(self):
        try:
            for inp in self.driver.find_elements(By.CSS_SELECTOR, "input[required]:not([type='hidden'])"):
                if inp.get_attribute("value"):
                    continue
                aria  = (inp.get_attribute("aria-label") or "").lower()
                itype = inp.get_attribute("type")
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", inp)
                time.sleep(0.2)
                if itype == "tel" or "phone" in aria:
                    inp.send_keys("9999999999")
                elif "year" in aria or "experience" in aria:
                    inp.send_keys("7")
                elif itype in ("text", "", None):
                    inp.send_keys("Yes")
                elif itype == "number":
                    inp.send_keys("7")
            for sel in self.driver.find_elements(By.CSS_SELECTOR, "select[required]"):
                try:
                    s = Select(sel)
                    if s.first_selected_option.text.strip() in ("", "Select an option", "Please select"):
                        opts = [o for o in s.options if o.text.strip() not in ("", "Select an option")]
                        if opts:
                            s.select_by_visible_text(opts[-1].text)
                except Exception: pass
        except Exception as exc:
            logger.debug(f"fill_form_fields error: {exc}")

    def _handle_modal(self) -> bool:
        for _ in range(12):
            random_sleep(1, 2)
            self._fill_form_fields()
            submit_btns = self.driver.find_elements(
                By.XPATH,
                "//button[contains(@aria-label,'Submit') or contains(normalize-space(),'Submit application')]",
            )
            if submit_btns:
                self.driver.execute_script("arguments[0].click();", submit_btns[0])
                random_sleep(2, 3)
                logger.info("Easy Apply: submitted")
                return True
            next_btns = self.driver.find_elements(By.CSS_SELECTOR, "button.artdeco-button--primary")
            if next_btns:
                self.driver.execute_script("arguments[0].click();", next_btns[-1])
                random_sleep(1, 2)
                continue
            logger.warning("Easy Apply: no navigation button found")
            return False
        return False

    def _dismiss_modal(self):
        try:
            close = self.driver.find_element(
                By.CSS_SELECTOR, "button[aria-label='Dismiss'], button.artdeco-modal__dismiss"
            )
            self.driver.execute_script("arguments[0].click();", close)
            random_sleep(1, 1.5)
            discard = self.driver.find_elements(By.XPATH, "//button[contains(normalize-space(),'Discard')]")
            if discard:
                self.driver.execute_script("arguments[0].click();", discard[0])
        except Exception: pass

    def apply(self, job: dict) -> dict:
        if not job.get("url"):
            return {"success": False, "reason": "No URL"}
        try:
            self.driver.get(job["url"])
            random_sleep(2, 4)
            try:
                btn = self.wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button.jobs-apply-button, button[aria-label*='Easy Apply']")
                    )
                )
            except TimeoutException:
                return {"success": False, "reason": "Easy Apply button not found"}
            if "apply" not in btn.text.lower():
                return {"success": False, "reason": "Not an apply button"}
            self.driver.execute_script("arguments[0].click();", btn)
            random_sleep(2, 3)
            success = self._handle_modal()
            if not success:
                self._dismiss_modal()
                return {"success": False, "reason": "Modal incomplete"}
            return {"success": True}
        except Exception as exc:
            logger.error(f"LinkedIn apply error [{job.get('title')}]: {exc}")
            return {"success": False, "reason": str(exc)}

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except Exception: pass