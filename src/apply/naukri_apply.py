import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from src.utils.helpers import get_driver, random_sleep, slow_type

logger = logging.getLogger(__name__)

NAUKRI_LOGIN = "https://www.naukri.com/nlogin/login"


class NaukriApply:
    def __init__(self, settings):
        self.settings = settings
        self.driver   = get_driver(headless=settings.headless)
        self.wait     = WebDriverWait(self.driver, 15)
        self._login()

    def _login(self):
        try:
            self.driver.get(NAUKRI_LOGIN)
            random_sleep(2, 3)
            email_f = self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[placeholder*='email' i], input[type='text']")
                )
            )
            slow_type(email_f, self.settings.naukri_email)
            slow_type(
                self.driver.find_element(By.CSS_SELECTOR, "input[type='password']"),
                self.settings.naukri_password,
            )
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .loginButton").click()
            random_sleep(3, 5)
            logger.info("Naukri apply session: logged in")
        except Exception as exc:
            logger.error(f"Naukri apply login error: {exc}")

    def apply(self, job: dict) -> dict:
        if not job.get("url"):
            return {"success": False, "reason": "No URL"}
        try:
            self.driver.get(job["url"])
            random_sleep(2, 4)
            apply_btn = None
            for sel in ["button#apply-button","a#apply-button","button.apply-button","[id*='apply'][class*='btn']"]:
                btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if btns:
                    apply_btn = btns[0]
                    break
            if not apply_btn:
                all_btns = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(normalize-space(),'Apply') and not(contains(normalize-space(),'Already'))]",
                )
                if all_btns:
                    apply_btn = all_btns[0]
            if not apply_btn:
                return {"success": False, "reason": "Apply button not found"}
            if "already applied" in apply_btn.text.lower():
                return {"success": False, "reason": "Already applied"}
            apply_btn.click()
            random_sleep(2, 4)
            try:
                confirm_btns = self.wait.until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH,
                         "//button[contains(normalize-space(),'Apply') "
                         "or contains(normalize-space(),'Submit') "
                         "or contains(normalize-space(),'Confirm')]")
                    )
                )
                for btn in confirm_btns:
                    if any(kw in btn.text.lower() for kw in ("apply","submit","confirm")):
                        btn.click()
                        random_sleep(1, 2)
                        break
            except TimeoutException: pass
            return {"success": True}
        except Exception as exc:
            logger.error(f"Naukri apply error [{job.get('title')}]: {exc}")
            return {"success": False, "reason": str(exc)}

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except Exception: pass
