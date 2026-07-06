import re
import logging

logger = logging.getLogger(__name__)


class JobMatcher:
    """Filters and scores jobs by location, experience, and skills."""

    LOCATION_KEYWORDS = ["hyderabad", "telangana", "hyd", "remote", "work from home"]

    def __init__(self, settings):
        self.settings = settings
        self.target_skills_lower = [s.lower() for s in settings.target_skills]

    def _check_location(self, location: str) -> bool:
        if not location:
            return True
        return any(kw in location.lower() for kw in self.LOCATION_KEYWORDS)

    def _extract_min_exp(self, text: str) -> int:
        if not text:
            return 0
        for pattern in [
            r"(\d+)\s*[-\u2013]\s*\d+\s*year",
            r"(\d+)\+?\s*year",
            r"minimum\s+(\d+)\s*year",
            r"at\s+least\s+(\d+)\s*year",
        ]:
            m = re.search(pattern, text.lower())
            if m:
                return int(m.group(1))
        return 0

    def _skill_score(self, text: str) -> float:
        if not text:
            return 0.0
        lower = text.lower()
        matched = sum(1 for s in self.target_skills_lower if s in lower)
        return (matched / len(self.target_skills_lower)) * 100

    def _matched_skills(self, text: str) -> list:
        lower = text.lower()
        return [s for s in self.settings.target_skills if s.lower() in lower]

    def filter_jobs(self, jobs: list) -> list:
        results = []
        for job in jobs:
            if not self._check_location(job.get("location", "")):
                continue
            exp_text = (job.get("experience") or "") + " " + (job.get("description") or "")
            min_exp  = self._extract_min_exp(exp_text)
            if min_exp > 0 and min_exp > self.settings.min_experience + 5:
                logger.debug(f"Skipped (exp {min_exp}yr too high): {job.get('title')}")
                continue
            combined = " ".join([job.get("title",""), job.get("description",""), job.get("skills","")])
            score = self._skill_score(combined)
            if score < self.settings.min_skill_match:
                continue
            job["skill_match_score"] = round(score, 1)
            job["matched_skills"]    = self._matched_skills(combined)
            results.append(job)
        results.sort(key=lambda j: j.get("skill_match_score", 0), reverse=True)
        return results
