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

    # ------------------------------------------------------------------ #
    # Extract ALL card data via JavaScript in one shot so we never        #
    # navigate away before collecting all titles/URLs from a results page  #
    # ------------------------------------------------------------------ #
    def _extract_cards_js(self):
        """
        Use JavaScript to pull job data from every card on the current page.
        Returns a list of dicts: {title, company, url, location, exp, skills}.
        """
        script = """
        var results = [];
        // Try several card container selectors Naukri has used over the years
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

            // Title & URL
            var titleSelectors = [
                '.title a', 'a.title', '.jobTitle a',
                'h2 a', '[class*="title"] a', '.job-title a',
                'a[href*="naukri.com"]', 'a[class*="row1"]'
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
                // Fallback: first anchor with reasonable text
                var anchors = card.querySelectorAll('a');
                for (var a of anchors) {
                    var t = a.textContent.trim();
                    if (t && t.length > 3 && t.length < 100) {
                        title = t; url = a.href || ''; break;
                    }
                }
            }

            // Company
            var compSelectors = [
                '.comp-name', 'a.comp-name', '.companyInfo a',
                '[class*="comp-name"]', '[class*="company"] a',
                '[class*="company"]'
            ];
            for (var cs of compSelectors) {
                var el = card.querySelector(cs);
                if (el && el.textContent.trim()) {
                    company = el.textContent.trim(); break;
                }
            }

            // Location
            var locSelectors = [
                '.location span', '[class*="location"]', '[class*="loc"]', '.loc'
            ];
            for (var ls of locSelectors) {
                var el = card.querySelector(ls);
                if (el && el.textContent.trim()) {
                    loc = el.textContent.trim(); break;
                }
            }

            // Experience
            var expSelectors = [
                '.expwdth', '.experience', '[class*="exp"]:not([class*="expand"])'
            ];
            for (var es of expSelectors) {
                var el = card.querySelector(es);
                if (el && el.textContent.trim()) {
                    exp = el.textContent.trim(); break;
                }
            }

            // Skills / tags
            var tagEls = card.querySelectorAll('.tags li, [class*="skill"] li, [class*="tag"] li');
            if (tagEls.length) {
                skills = Array.from(tagEls).map(function(e){ return e.textContent.trim(); }).join(', ');
            }

            if (title) {
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

    def _get_job_description(self, url):
        if not url:
            return "", ""
        try:
            self.driver.get(url)
            random_sleep(2, 3)
            desc, skills = "", ""
            for sel in [
                ".job-desc", ".jd-desc", "#job-description",
                ".dang-inner-html", "[class*='job-desc']"
            ]:
                try:
                    el = self.driver.find_element(By.CSS_SELECTOR, sel)
                    desc = el.text[:3000]
                    break
                except Exception: pass
            key_skills = self.driver.find_elements(
                By.CSS_SELECTOR, ".key-skill span, .tags li, .skills span"
            )
            if key_skills:
                skills = ", ".join(s.text for s in key_skills if s.text)
            return desc, skills
        except Exception as exc:
            logger.debug(f"Naukri detail error: {exc}")
            return "", ""

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

                # --- Step 1: grab ALL card data in a single JS call ---
                raw_cards = self._extract_cards_js()

                # Fallback: count visible cards with DOM selectors for logging
                card_count = len(raw_cards)
                if card_count == 0:
                    for sel in [
                        "article.jobTuple", "div.jobTuple",
                        ".srp-jobtuple-wrapper", ".cust-job-tuple",
                        "[class*='jobTuple']", "[class*='job-tuple']",
                    ]:
                        elems = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        if elems:
                            card_count = len(elems)
                            break

                logger.info(f"Naukri '{slug}': {card_count} cards / {len(raw_cards)} parsed")

                # --- Step 2: deduplicate then fetch descriptions ---
                for raw in raw_cards[:20]:
                    url    = raw.get("url", "")
                    job_id = url.split("-")[-1].split("?")[0] if url else (raw.get("title","") + raw.get("company",""))[:40]
                    if not job_id or job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    # Navigate to job detail page to get full description
                    desc, extra_skills = self._get_job_description(url)
                    skills = extra_skills or raw.get("skills", "")

                    all_jobs.append({
                        "job_id":     job_id,
                        "title":      raw.get("title", ""),
                        "company":    raw.get("company", ""),
                        "location":   raw.get("location", "Hyderabad"),
                        "experience": raw.get("experience", ""),
                        "skills":     skills,
                        "url":        url,
                        "platform":   "Naukri",
                        "description": desc,
                    })
                    random_sleep(1, 2)

                random_sleep(3, 6)
            except Exception as exc:
                logger.error(f"Naukri search error '{slug}': {exc}")

        logger.info(f"Naukri total: {len(all_jobs)} jobs")
        return all_jobs

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except Exception: pass