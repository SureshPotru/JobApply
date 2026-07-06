import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class JobDatabase:
    def __init__(self, db_path="data/applied_jobs.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init()

    def _init(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS applied_jobs (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id     TEXT    NOT NULL,
                    platform   TEXT    NOT NULL,
                    title      TEXT,
                    company    TEXT,
                    location   TEXT,
                    url        TEXT,
                    applied_at TEXT    NOT NULL,
                    UNIQUE(job_id, platform)
                )
            """)
            conn.commit()

    def is_applied(self, job: dict) -> bool:
        job_id   = job.get("job_id") or job.get("url", "")
        platform = job.get("platform", "unknown")
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT 1 FROM applied_jobs WHERE job_id=? AND platform=?",
                (job_id, platform),
            )
            return cur.fetchone() is not None

    def mark_applied(self, job: dict):
        job_id   = job.get("job_id") or job.get("url", "")
        platform = job.get("platform", "unknown")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO applied_jobs
                    (job_id, platform, title, company, location, url, applied_at)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    job_id, platform,
                    job.get("title", ""), job.get("company", ""),
                    job.get("location", ""), job.get("url", ""),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def filter_new_jobs(self, jobs: list) -> list:
        return [j for j in jobs if not self.is_applied(j)]

    def get_all_applied(self) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM applied_jobs ORDER BY applied_at DESC")
            return [dict(r) for r in cur.fetchall()]
