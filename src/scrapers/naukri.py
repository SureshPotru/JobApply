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

from src.utils.helpers import random_sleep, scroll_down

logger = logging.getLogger(__name__)

NAUKRI_BASE  = "https://www.naukri.com"
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


class NaukriScraper:
    def __init__(self, settings):
        self.settings = settings
        self.driver   = None
        self.wait     = None

    def _init_driver(self):
        self.driver = get_chrome_driver(headless=self.settings.headless)
        self.wait   = WebDriverWait(self.driver, 20)

    def _login(self):
        if not self.settings.naukri_email:
            return False
        try:
            self.driver.get(NAUKRI_LOGIN)
            random_sleep(3, 4)

            # Wait for email field and use JavaScript to set value (avoids interactable issues)
            email_f = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], input[placeholder*='Email' i]"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", email_f)
            random_sleep(0.5, 1)
            self.driver.execute_script("arguments[0].value = arguments[1];", email_f, self.settings.naukri_email)
            email_f.click()
            time.sleep(0.3)
            # Also type it character by character as backup
            for c in self.settings.naukri_email[-4:]:
                email_f.send_keys(c)
                time.sleep(0.05)

            pass_f = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", pass_f)
            self.driver.execute_script("arguments[0].value = arguments[1];", pass_f, self.settings.naukri_password)
            pass_f.click()
            time.sleep(0.3)
            for c in self.settings.naukri_password[-4:]:
                pass_f.send_keys(c)
                time.sleep(0.05)

            # Click login button
            login_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'], .loginButton, button.btn-dark-ot"))
            )
            login_btn.click()
            random_sleep(4, 6)
            logger.info(f"Naukri scraper: login OK (URL: {self.driver.current_url})")
            return True
        except Exception as exc:
            logger.error(f"Naukri login error: {exc}")
            return False

    def _build_search_url(self, slug):
        exp = self.settings.min_experience
        return (
            f"{NAUKRI_BASE}/{slug}-jobs-in-hyderabad-{exp}"
            f"?experience={exp}&nignbevent_src=jobsearchDesk"
        )

    def _parse_job_card(self, card):
        try:
            # Try multiple title selectors
            title_elem = None
            for sel in [".title a", "a.title", ".jobTitle a", "h2 a", "[class*='title'] a", ".job-title a"]:
                elems = card.find_elements(By.CSS_SELECTOR, sel)
                if elems:
                    title_elem = elems[0]
                    break
            if not title_elem:
                return None
            title = title_elem.text.strip()
            url   = title_elem.get_attribute("href") or ""
            if not title:
                return None

            company = ""
            for sel in [".comp-name", "a.comp-name", ".companyInfo a", "[class*='company'] a", "[class*='comp-name']"]:
                elems = card.find_elements(By.CSS_SELECTOR, sel)
                if elems and elems[0].text.strip():
                    company = elems[0].text.strip()
                    break

            exp_text, loc_text, skills_text = "", "Hyderabad", ""
            try:
                exp_text = card.find_element(By.CSS_SELECTOR, ".exp, [class*='exp']:not([class*='expand'])").text.strip()
            except Exception: pass
            try:
                loc_text = card.find_element(By.CSS_SELECTOR, ".location, [class*='location'], [class*='loc']").text.strip()
            except Exception: pass
            try:
                skills_text = card.find_element(By.CSS_SELECTOR, ".tags li, [class*='skill'] li, [class*='tag'] li").text.strip()
            except Exception: pass

            job_id = url.split("-")[-1].split("?")[0] if url else (title + company)[:40]
            return {
                "job_id": job_id, "title": title, "company": company,
                "location": loc_text, "experience": exp_text,
                "skills": skills_text, "url": url,
                "platform": "Naukri", "description": "",
            }
        except Exception as exc:
            logger.debug(f"Naukri card parse error: {exc}")
            return None

    def _get_job_description(self, job):
        if not job.get("url"):
            return job
        try:
            self.driver.get(job["url"])
            random_sleep(2, 3)
            try:
                desc = self.wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR,
                         ".job-desc, .jd-desc, #job-description, .dang-inner-html, [class*='job-desc']")
                    )
                )
                job["description"] = desc.text[:3000]
            except Exception: pass
            try:
                key_skills = self.driver.find_elements(By.CSS_SELECTOR, ".key-skill span, .tags li, .skills span")
                if key_skills:
                    job["skills"] = ", ".join(s.text for s in key_skills if s.text)
            except Exception: pass
        except Exception as exc:
            logger.debug(f"Naukri detail error: {exc}")
        return job

    def search_jobs(self):
        self._init_driver()
        logged_in = self._login()
        if not logged_in:
            logger.warning("Naukri: proceeding without login (will scrape public listings)")

        all_jobs, seen_ids = [], set()
        for slug in ["devops-engineer", "devops", "site-reliability-engineer"]:
            try:
                self.driver.get(self._build_search_url(slug))
                random_sleep(3, 5)
                scroll_down(self.driver)
                random_sleep(2, 3)

                # Try multiple card selectors
                cards = []
                for sel in [
                    "article.jobTuple", "div.jobTuple",
                    ".srp-jobtuple-wrapper", ".cust-job-tuple",
                    "[class*='jobTuple']", "[class*='job-tuple']",
                    ".list li[type='joblist']",
                ]:
                    cards = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    if cards:
                        break

                logger.info(f"Naukri '{slug}': {len(cards)} cards")
                for card in cards[:20]:
                    try:
                        job = self._parse_job_card(card)
                        if job and job["job_id"] not in seen_ids:
                            job = self._get_job_description(job)
                            all_jobs.append(job)
                            seen_ids.add(job["job_id"])
                            random_sleep(1, 2)
                    except Exception as exc:
                        logger.debug(f"Card error: {exc}")
                random_sleep(3, 6)
            except Exception as exc:
                logger.error(f"Naukri search error '{slug}': {exc}")

        logger.info(f"Naukri total: {len(all_jobs)} jobs")
        return all_jobs

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except Exception: pass