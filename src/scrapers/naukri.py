import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
            email_f = self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='text'], input[placeholder*='Email' i]")
                )
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", email_f)
            random_sleep(0.5, 1)
            self.driver.execute_script(
                "arguments[0].value = arguments[1];", email_f, self.settings.naukri_email
            )
            email_f.click()
            time.sleep(0.3)
            for c in self.settings.naukri_email[-4:]:
                email_f.send_keys(c)
                time.sleep(0.05)

            pass_f = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", pass_f)
            self.driver.execute_script(
                "arguments[0].value = arguments[1];", pass_f, self.settings.naukri_password
            )
            pass_f.click()
            time.sleep(0.3)
            for c in self.settings.naukri_password[-4:]:
                pass_f.send_keys(c)
                time.sleep(0.05)

            login_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR,
                     "button[type='submit'], .loginButton, button.btn-dark-ot")
                )
            )
            login_btn.click()
            random_sleep(4, 6)
            logger.info(f"Naukri scraper: login OK ({self.driver.current_url})")
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

    def _extract_cards_js(self):
        """Extract all job card data in one JavaScript call to avoid stale-element issues."""
        script = """
        var results = [];
        var cardSelectors = [
            'article.jobTuple', 'div.jobTuple',
            '.srp-jobtuple-wrapper', '.cust-job-tuple',
            '[class*="jobTuple"]', '[class*="job-tuple"]'
        ];
        var cards = [];
        for (var s of cardSelectors) {
            cards = document.querySelectorAll(s);
            if (cards.length > 0) break;
        }
        cards.forEach(function(card) {
            var title = '', url = '', company = '', loc = '', exp = '', skills = '';

            var titleSelectors = [
                '.title a', 'a.title', '.jobTitle a',
                'h2 a', '[class*="title"] a', '.job-title a',
                'a[href*="naukri.com"]'
            ];
            for (var ts of titleSelectors) {
                var el = card.querySelector(ts);
                if (el && el.textContent.trim()) {
                    title = el.textContent.trim();
                    url   = el.href || '';
                    break;
                }
            }
            if (!title) {
                var anchors = card.querySelectorAll('a');
                for (var a of anchors) {
                    var t = a.textContent.trim();
                    if (t && t.length > 5 && t.length < 100 && !t.toLowerCase().includes('apply')) {
                        title = t; url = a.href || ''; break;
                    }
                }
            }

            var compSelectors = [
                '.comp-name', 'a.comp-name', '[class*="comp-name"]',
                '[class*="company"] a', '[class*="company"]'
            ];
            for (var cs of compSelectors) {
                var el = card.querySelector(cs);
                if (el && el.textContent.trim()) { company = el.textContent.trim(); break; }
            }

            var locSelectors = [
                '.location span', '[class*="location"]', '[class*="loc"]'
            ];
            for (var ls of locSelectors) {
                var el = card.querySelector(ls);
                if (el && el.textContent.trim()) { loc = el.textContent.trim(); break; }
            }

            var expSelectors = [
                '.expwdth', '.experience',
                '[class*="exp"]:not([class*="expand"]):not([class*="experience"])'
            ];
            for (var es of expSelectors) {
                var el = card.querySelector(es);
                if (el && el.textContent.trim()) { exp = el.textContent.trim(); break; }
            }

            var tagEls = card.querySelectorAll('.tags li, [class*="skill"] li, [class*="tag"] li');
            if (tagEls.length) {
                skills = Array.from(tagEls).map(function(e){ return e.textContent.trim(); }).join(', ');
            }

            if (title && url) {
                results.push({
                    title: title, url: url, company: company,
                    location: loc || 'Hyderabad', experience: exp, skills: skills
                });
            }
        });
        return results;
        """
        try:
            return self.driver.execute_script(script) or []
        except Exception as exc:
            logger.debug(f"_extract_cards_js error: {exc}")
            return []

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

                # Collect all card data via single JS call (no navigation = no stale refs)
                raw_cards = self._extract_cards_js()
                logger.info(f"Naukri '{slug}': {len(raw_cards)} cards parsed")

                for raw in raw_cards[:20]:
                    url    = raw.get("url", "")
                    job_id = (
                        url.split("-")[-1].split("?")[0]
                        if url
                        else (raw.get("title", "") + raw.get("company", ""))[:40]
                    )
                    if not job_id or job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    all_jobs.append({
                        "job_id":      job_id,
                        "title":       raw.get("title", ""),
                        "company":     raw.get("company", ""),
                        "location":    raw.get("location", "Hyderabad"),
                        "experience":  raw.get("experience", ""),
                        "skills":      raw.get("skills", ""),
                        "url":         url,
                        "platform":    "Naukri",
                        "description": raw.get("title", "") + " " + raw.get("skills", ""),
                    })

                random_sleep(3, 5)
            except Exception as exc:
                logger.error(f"Naukri search error '{slug}': {exc}")

        logger.info(f"Naukri total: {len(all_jobs)} jobs")
        return all_jobs

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except Exception: pass