import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from src.utils.helpers import get_driver, random_sleep, scroll_down

logger = logging.getLogger(__name__)

NAUKRI_BASE  = "https://www.naukri.com"
NAUKRI_LOGIN = "https://www.naukri.com/nlogin/login"


class NaukriScraper:
    def __init__(self, settings):
        self.settings = settings
        self.driver   = None
        self.wait     = None

    def _init_driver(self):
        self.driver = get_driver(headless=self.settings.headless)
        self.wait   = WebDriverWait(self.driver, 15)

    def _login(self):
        if not self.settings.naukri_email:
            return False
        try:
            self.driver.get(NAUKRI_LOGIN)
            random_sleep(2, 3)
            email_f = self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[placeholder*='email' i], input[type='text']")
                )
            )
            email_f.clear()
            email_f.send_keys(self.settings.naukri_email)
            self.driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(
                self.settings.naukri_password
            )
            self.driver.find_element(
                By.CSS_SELECTOR, "button[type='submit'], .loginButton"
            ).click()
            random_sleep(3, 5)
            logger.info("Naukri scraper: login OK")
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
            title_elem = card.find_element(
                By.CSS_SELECTOR, ".title, a.title, .jobTitle, h2 a, [class*='title'] a"
            )
            title = title_elem.text.strip()
            url   = title_elem.get_attribute("href") or ""
            company = card.find_element(
                By.CSS_SELECTOR, ".comp-name, a.comp-name, [class*='company'] a, [class*='comp']"
            ).text.strip()
            exp_text, loc_text, skills_text = "", "Hyderabad", ""
            try:
                exp_text = card.find_element(By.CSS_SELECTOR, ".exp, .experience, [class*='exp']").text.strip()
            except Exception: pass
            try:
                loc_text = card.find_element(By.CSS_SELECTOR, ".location, [class*='location'], [class*='loc']").text.strip()
            except Exception: pass
            try:
                skills_text = card.find_element(By.CSS_SELECTOR, ".tags, .skill-list, [class*='skill'], [class*='tag']").text.strip()
            except Exception: pass
            job_id = url.split("-")[-1].split("?")[0] if url else title + company
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
        self._login()
        all_jobs, seen_ids = [], set()
        for slug in ["devops-engineer", "devops", "site-reliability-engineer"]:
            try:
                self.driver.get(self._build_search_url(slug))
                random_sleep(3, 5)
                scroll_down(self.driver)
                random_sleep(2, 3)
                cards = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "article.jobTuple, div.jobTuple, .srp-jobtuple-wrapper, "
                    ".cust-job-tuple, [class*='jobTuple'], [class*='job-tuple']",
                )
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
