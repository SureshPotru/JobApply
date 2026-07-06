import logging
import urllib.parse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from src.utils.helpers import get_driver, random_sleep, scroll_down

logger = logging.getLogger(__name__)

LINKEDIN_BASE  = "https://www.linkedin.com"
LINKEDIN_LOGIN = "https://www.linkedin.com/login"


class LinkedInScraper:
    def __init__(self, settings):
        self.settings = settings
        self.driver   = None
        self.wait     = None

    def _init_driver(self):
        self.driver = get_driver(headless=self.settings.headless)
        self.wait   = WebDriverWait(self.driver, 15)

    def _login(self):
        if not self.settings.linkedin_email:
            return False
        try:
            self.driver.get(LINKEDIN_LOGIN)
            random_sleep(2, 4)
            email_f = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            email_f.clear()
            email_f.send_keys(self.settings.linkedin_email)
            self.driver.find_element(By.ID, "password").send_keys(self.settings.linkedin_password)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            random_sleep(3, 5)
            logger.info("LinkedIn scraper: login OK")
            return True
        except Exception as exc:
            logger.error(f"LinkedIn login error: {exc}")
            return False

    def _build_search_url(self, keyword):
        params = {
            "keywords": keyword,
            "location": "Hyderabad, Telangana, India",
            "f_E":   "4,5,6",    # Mid-Senior / Director / Executive
            "f_TPR": "r86400",   # Past 24 hours
            "f_LF":  "f_AL",     # Easy Apply only
            "position": "1",
            "pageNum":  "0",
        }
        return f"{LINKEDIN_BASE}/jobs/search/?{urllib.parse.urlencode(params)}"

    def _parse_job_card(self, card):
        try:
            title_elem = card.find_element(
                By.CSS_SELECTOR, "h3.base-search-card__title, a.job-card-list__title"
            )
            title   = title_elem.text.strip()
            company = card.find_element(
                By.CSS_SELECTOR,
                "h4.base-search-card__subtitle, a.job-card-container__company-name",
            ).text.strip()
            location = card.find_element(
                By.CSS_SELECTOR,
                "span.job-search-card__location, span.job-card-container__metadata-item",
            ).text.strip()
            try:
                link   = card.find_element(By.CSS_SELECTOR, "a.base-card__full-link, a.job-card-list__title")
                url    = link.get_attribute("href").split("?")[0]
                job_id = url.split("/")[-1]
            except Exception:
                url = job_id = ""
            return {
                "job_id": job_id, "title": title, "company": company,
                "location": location, "url": url, "platform": "LinkedIn",
                "description": "", "experience": "", "skills": "",
            }
        except Exception as exc:
            logger.debug(f"LinkedIn card parse error: {exc}")
            return None

    def _get_job_details(self, job):
        if not job.get("url"):
            return job
        try:
            self.driver.get(job["url"])
            random_sleep(2, 3)
            try:
                desc = self.wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR,
                         "div.description__text, div.jobs-description-content__text")
                    )
                )
                job["description"] = desc.text[:3000]
            except Exception:
                pass
            try:
                for item in self.driver.find_elements(By.CSS_SELECTOR, "li.description__job-criteria-item"):
                    label = item.find_element(By.CSS_SELECTOR, "h3").text.lower()
                    value = item.find_element(By.CSS_SELECTOR, "span").text
                    if "experience" in label:
                        job["experience"] = value
            except Exception:
                pass
        except Exception as exc:
            logger.debug(f"LinkedIn detail error: {exc}")
        return job

    def search_jobs(self):
        self._init_driver()
        if not self._login():
            return []
        all_jobs, seen_ids = [], set()
        for keyword in self.settings.search_keywords[:3]:
            try:
                self.driver.get(self._build_search_url(keyword))
                random_sleep(3, 5)
                scroll_down(self.driver)
                random_sleep(2, 3)
                cards = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "div.job-search-card, li.jobs-search-results__list-item",
                )
                logger.info(f"LinkedIn '{keyword}': {len(cards)} cards")
                for card in cards[:20]:
                    try:
                        job = self._parse_job_card(card)
                        if job and job["job_id"] not in seen_ids:
                            job = self._get_job_details(job)
                            all_jobs.append(job)
                            seen_ids.add(job["job_id"])
                            random_sleep(1, 2)
                    except Exception as exc:
                        logger.debug(f"Card error: {exc}")
                random_sleep(3, 6)
            except Exception as exc:
                logger.error(f"LinkedIn search error '{keyword}': {exc}")
        logger.info(f"LinkedIn total: {len(all_jobs)} jobs")
        return all_jobs

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except Exception: pass
