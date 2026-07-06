import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class WhatsAppNotifier:
    def __init__(self, settings):
        self.settings = settings

    def send_summary(self, total_applied: int, top_jobs: list = None, errors: list = None):
        cfg = self.settings
        if not (cfg.twilio_account_sid and cfg.twilio_auth_token and cfg.whatsapp_to):
            logger.warning("Twilio credentials not set -- skipping WhatsApp")
            return
        try:
            from twilio.rest import Client
        except ImportError:
            logger.error("twilio not installed. It is in requirements.txt -- run pip install -r requirements.txt")
            return
        client = Client(cfg.twilio_account_sid, cfg.twilio_auth_token)
        msg = client.messages.create(
            body=self._build_message(total_applied, top_jobs or [], errors or []),
            from_=cfg.twilio_whatsapp_from,
            to=cfg.whatsapp_to,
        )
        logger.info(f"WhatsApp sent: {msg.sid}")

    def _build_message(self, total: int, top_jobs: list, errors: list) -> str:
        date_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
        lines = [
            "*DevOps Job Auto-Apply Report*",
            f"Date: {date_str}",
            "",
            f"Applied to *{total} job(s)*",
            "Location: Hyderabad, Telangana",
            "Experience: 5+ Years",
        ]
        if top_jobs:
            lines += ["", "*Top Applied Jobs:*"]
            icons = {"LinkedIn": "[LI]", "Naukri": "[NK]"}
            for i, job in enumerate(top_jobs[:5], 1):
                icon = icons.get(job.get("platform",""), "--")
                lines.append(
                    f"{i}. {icon} *{job.get('title','N/A')}*\n"
                    f"   Company: {job.get('company','N/A')}\n"
                    f"   Match: {job.get('skill_match_score',0):.0f}%"
                )
        if errors:
            lines += ["", f"Errors: {len(errors)} encountered during run"]
        if total == 0:
            lines += ["", "No new matching jobs found today. Will retry tomorrow!"]
        lines += ["", "_Auto-apply bot via GitHub Actions_"]
        return "\n".join(lines)
