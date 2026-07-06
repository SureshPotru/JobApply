#!/usr/bin/env python3
"""
DevOps Job Auto-Apply Pipeline

Searches LinkedIn & Naukri daily for DevOps jobs in Hyderabad (5+ yrs),
matches against target skills, auto-applies, then sends email + WhatsApp alerts.
"""

import os
import sys
import logging
from datetime import datetime

from src.scrapers.linkedin import LinkedInScraper
from src.scrapers.naukri import NaukriScraper
from src.matchers.job_matcher import JobMatcher
from src.apply.linkedin_apply import LinkedInApply
from src.apply.naukri_apply import NaukriApply
from src.notifications.email_notifier import EmailNotifier
from src.notifications.whatsapp_notifier import WhatsAppNotifier
from src.utils.db import JobDatabase
from config.settings import Settings

os.makedirs("data", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler("data/pipeline.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def run_platform(name, scraper_cls, apply_cls, settings, matcher, db):
    """Scrape -> match -> apply for one platform. Returns (applied_list, errors_list)."""
    applied, errors = [], []

    scraper = scraper_cls(settings)
    try:
        logger.info(f"[{name}] Searching jobs...")
        jobs = scraper.search_jobs()
        logger.info(f"[{name}] {len(jobs)} raw jobs found")
    finally:
        scraper.close()

    matched = matcher.filter_jobs(jobs)
    logger.info(f"[{name}] {len(matched)} jobs matched filters")

    new_jobs = db.filter_new_jobs(matched)
    logger.info(f"[{name}] {len(new_jobs)} new jobs to apply")

    if not new_jobs:
        return applied, errors

    applier = apply_cls(settings)
    try:
        for job in new_jobs[: settings.max_applications_per_run]:
            try:
                result = applier.apply(job)
                if result["success"]:
                    job["platform"] = name
                    db.mark_applied(job)
                    applied.append(job)
                    logger.info(f"  OK  {job['title']} @ {job['company']}")
                else:
                    logger.warning(f"  --  Skipped: {job['title']} -- {result.get('reason')}")
            except Exception as exc:
                logger.error(f"  !!  Error applying to {job.get('title')}: {exc}")
                errors.append(f"{name}: {exc}")
    finally:
        applier.close()

    return applied, errors


def run_pipeline():
    logger.info("=" * 65)
    logger.info("  DevOps Job Auto-Apply Pipeline -- START")
    logger.info(f"  {datetime.now().isoformat()}")
    logger.info("=" * 65)

    settings = Settings()
    db = JobDatabase(settings.db_path)
    matcher = JobMatcher(settings)

    all_applied, all_errors = [], []

    if settings.linkedin_email:
        jobs, errs = run_platform("LinkedIn", LinkedInScraper, LinkedInApply, settings, matcher, db)
        all_applied.extend(jobs)
        all_errors.extend(errs)
    else:
        logger.warning("LINKEDIN_EMAIL not set -- skipping LinkedIn")

    if settings.naukri_email:
        jobs, errs = run_platform("Naukri", NaukriScraper, NaukriApply, settings, matcher, db)
        all_applied.extend(jobs)
        all_errors.extend(errs)
    else:
        logger.warning("NAUKRI_EMAIL not set -- skipping Naukri")

    total = len(all_applied)
    logger.info(f"Pipeline summary: {total} application(s) submitted")

    if settings.enable_email_alerts:
        try:
            EmailNotifier(settings).send_summary(all_applied, all_errors)
        except Exception as exc:
            logger.error(f"Email failed: {exc}")
    else:
        logger.info("Email alerts disabled (ENABLE_EMAIL_ALERTS=false)")

    if settings.enable_whatsapp_alerts:
        try:
            WhatsAppNotifier(settings).send_summary(total, all_applied[:5], all_errors)
        except Exception as exc:
            logger.error(f"WhatsApp failed: {exc}")
    else:
        logger.info("WhatsApp alerts disabled (ENABLE_WHATSAPP_ALERTS=false)")

    logger.info("=" * 65)
    logger.info(f"  Pipeline COMPLETE -- {total} job(s) applied")
    logger.info("=" * 65)
    return total


if __name__ == "__main__":
    run_pipeline()