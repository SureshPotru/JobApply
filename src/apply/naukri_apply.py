import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
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
        self.driver = get_chrome_driver(headless=settings.headless)
        self.wait = WebDriverWait(self.driver, 15)
        self.logged_in = False
        self._login()

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _js_click(self, element):
        """Click via JavaScript to bypass element-not-interactable issues."""
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        time.sleep(0.4)
        self.driver.execute_script("arguments[0].click();", element)

    def _dismiss_overlays(self):
        """Close cookie banners, modals, and popups before interacting with page."""
        close_selectors = [
            "button[data-ga-track='close']",
            "span.crossIcon",
            "button.cookieConsent__Button",
            "div.overlay-close",
            "[class*='close'][class*='modal']",
            "[aria-label='Close']",
            "button.close",
            "i.nI-gNb-close",
        ]
        for sel in close_selectors:
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                self._js_click(btn)
                time.sleep(0.4)
            except Exception:
                pass
        try:
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.3)
        except Exception:
            pass

    def _is_logged_in(self) -> bool:
        """Return True if Naukri shows a logged-in profile state."""
        logged_in_selectors = [
            "a[href*='/mnjuser/homepage']",
            "a[href*='/mnjuser/profile']",
            "div.nI-gNb-drawer__social",
            "span.nI-gNb-user",
            "a.nI-gNb-login-email",
            ".user-name",
            ".logged-user",
        ]
        for sel in logged_in_selectors:
            try:
                self.driver.find_element(By.CSS_SELECTOR, sel)
                return True
            except NoSuchElementException:
                pass
        # Fallback: navigated away from login page means login succeeded
        if "nlogin" not in self.driver.current_url and "naukri.com" in self.driver.current_url:
            return True
        return False

    # ------------------------------------------------------------------ #
    #  Login
    # ------------------------------------------------------------------ #

    def _login(self):
        try:
            self.driver.get(NAUKRI_LOGIN)
            random_sleep(3, 5)
            self._dismiss_overlays()

            email_f = self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='text'], input[placeholder*='Email' i]")
                )
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", email_f)
            random_sleep(0.3, 0.6)
            self.driver.execute_script(
                "arguments[0].value = arguments[1];", email_f, self.settings.naukri_email
            )
            email_f.click()
            time.sleep(0.3)
            for c in self.settings.naukri_email[-4:]:
                email_f.send_keys(c)
                time.sleep(0.06)

            pass_f = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", pass_f)
            self.driver.execute_script(
                "arguments[0].value = arguments[1];", pass_f, self.settings.naukri_password
            )
            pass_f.click()
            time.sleep(0.3)
            for c in self.settings.naukri_password[-4:]:
                pass_f.send_keys(c)
                time.sleep(0.06)

            random_sleep(0.5, 1)

            # Use JS click to bypass any overlay covering the submit button
            login_btn = self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR,
                     "button[type='submit'], .loginButton, button.btn-dark-ot, button[class*='login']")
                )
            )
            self._js_click(login_btn)
            random_sleep(5, 8)

            if self._is_logged_in():
                self.logged_in = True
                logger.info("Naukri apply session: logged in successfully")
            else:
                logger.error(
                    "Naukri apply: login NOT confirmed after submit "
                    f"(URL: {self.driver.current_url}). "
                    "All apply() calls will be skipped to avoid fake DB entries."
                )
        except Exception as exc:
            logger.error(f"Naukri apply login error: {exc}")
            self.logged_in = False

    # ------------------------------------------------------------------ #
    #  Verify application was actually submitted
    # ------------------------------------------------------------------ #

    def _verify_applied(self) -> bool:
        """Return True only when Naukri confirms the application was submitted."""
        # Check success toast / badge selectors
        success_selectors = [
            "div[class*='toast'][class*='success']",
            "div[class*='success'][class*='message']",
            "button#apply-button[disabled]",
            "button.apply-button[disabled]",
            "span[class*='applied']",
            "div[class*='applied']",
            ".alreadyApplied",
        ]
        for sel in success_selectors:
            try:
                elem = self.driver.find_element(By.CSS_SELECTOR, sel)
                if elem.is_displayed():
                    return True
            except NoSuchElementException:
                pass

        # Check if Apply button changed to "Applied"
        try:
            btns = self.driver.find_elements(
                By.XPATH,
                "//button[contains(normalize-space(),'Applied') "
                "or contains(normalize-space(),'already applied')]"
            )
            if btns:
                return True
        except Exception:
            pass

        # Check page body text for confirmation phrases
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            if any(phrase in body_text for phrase in [
                "application submitted", "successfully applied",
                "your application has been", "applied successfully",
                "you have applied",
            ]):
                return True
        except Exception:
            pass

        return False

    # ------------------------------------------------------------------ #
    #  Apply
    # ------------------------------------------------------------------ #

    def apply(self, job: dict) -> dict:
        # Guard: skip if not logged in to prevent fake DB entries
        if not self.logged_in:
            return {
                "success": False,
                "reason": "Not logged in — skipping to avoid recording a fake application",
            }

        if not job.get("url"):
            return {"success": False, "reason": "No URL"}

        try:
            self.driver.get(job["url"])
            random_sleep(3, 5)
            self._dismiss_overlays()

            apply_btn = None

            for sel in [
                "button#apply-button",
                "a#apply-button",
                "button.apply-button",
                "button[id*='apply']",
                "a[id*='apply']",
            ]:
                elems = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if elems:
                    apply_btn = elems[0]
                    break

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
                return {"success": False, "reason": "Already applied (button)"}

            self._js_click(apply_btn)
            random_sleep(3, 5)

            # Handle confirmation modal if present
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
                        random_sleep(2, 3)
                        break
            except Exception:
                pass

            # Verify the application actually went through
            if self._verify_applied():
                logger.info(f"[CONFIRMED] Applied: {job.get('title')} @ {job.get('company')}")
                return {"success": True}

            # Give Naukri a moment and retry verification
            random_sleep(2, 3)
            if self._verify_applied():
                logger.info(f"[CONFIRMED] Applied: {job.get('title')} @ {job.get('company')}")
                return {"success": True}

            logger.warning(
                f"[NOT CONFIRMED] Could not verify application for "
                f"{job.get('title')} @ {job.get('company')}. Not recording in DB."
            )
            return {"success": False, "reason": "Application not confirmed on Naukri page"}

        except Exception as exc:
            logger.error(f"Naukri apply error [{job.get('title')}]: {exc}")
            return {"success": False, "reason": str(exc)}

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass