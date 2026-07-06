import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from src.utils.helpers import get_driver, random_sleep, slow_type

logger = logging.getLogger(__name__)

LINKEDIN_LOGIN = "https://www.linkedin.com/login"


class LinkedInApply:
    def __init__(self, settings):
        self.settings = settings
        self.driver   = get_driver(headless=settings.headless)
        self.wait     = WebDriverWait(self.driver, 12)
        self._login()

    def _login(self):
        try:
            self.driver.get(LINKEDIN_LOGIN)
            random_sleep(2, 3)
            email_f = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            slow_type(email_f, self.settings.linkedin_email)
            slow_type(self.driver.find_element(By.ID, "password"), self.settings.linkedin_password)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            random_sleep(3, 5)
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
                submit_btns[0].click()
                random_sleep(2, 3)
                logger.info("Easy Apply: submitted")
                return True
            next_btns = self.driver.find_elements(By.CSS_SELECTOR, "button.artdeco-button--primary")
            if next_btns:
                next_btns[-1].click()
                random_sleep(1, 2)
                continue
            logger.warning("Easy Apply: no navigation button found")
            return False
        return False

    def _dismiss_modal(self):
        try:
            self.driver.find_element(
                By.CSS_SELECTOR, "button[aria-label='Dismiss'], button.artdeco-modal__dismiss"
            ).click()
            random_sleep(1, 1.5)
            discard = self.driver.find_elements(By.XPATH, "//button[contains(normalize-space(),'Discard')]")
            if discard:
                discard[0].click()
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
            btn.click()
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
