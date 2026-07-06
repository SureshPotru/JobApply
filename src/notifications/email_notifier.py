import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailNotifier:
    def __init__(self, settings):
        self.settings = settings

    def send_summary(self, applied_jobs: list, errors: list = None):
        if not (self.settings.gmail_user and self.settings.gmail_app_password):
            logger.warning("Gmail credentials not set -- skipping email")
            return
        if not self.settings.alert_email:
            logger.warning("ALERT_EMAIL not set -- skipping email")
            return
        total   = len(applied_jobs)
        subject = f"DevOps Job Report {datetime.now().strftime('%d %b %Y')} -- {total} Applied"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = self.settings.gmail_user
        msg["To"]      = self.settings.alert_email
        msg.attach(MIMEText(self._build_html(applied_jobs, errors), "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
            srv.login(self.settings.gmail_user, self.settings.gmail_app_password)
            srv.sendmail(self.settings.gmail_user, self.settings.alert_email, msg.as_string())
        logger.info(f"Email sent to {self.settings.alert_email}")

    def _build_html(self, jobs: list, errors: list = None) -> str:
        date_str     = datetime.now().strftime("%B %d, %Y at %I:%M %p IST")
        total        = len(jobs)
        linkedin_cnt = sum(1 for j in jobs if j.get("platform") == "LinkedIn")
        naukri_cnt   = sum(1 for j in jobs if j.get("platform") == "Naukri")

        rows = ""
        for job in jobs:
            skill_tags = "".join(
                f'<span style="background:#e8f4f8;padding:2px 6px;border-radius:3px;'
                f'font-size:11px;margin:2px;display:inline-block">{s}</span>'
                for s in job.get("matched_skills", [])[:6]
            )
            rows += (
                f"<tr>"
                f"<td style='padding:10px;border-bottom:1px solid #eee'>"
                f"<a href='{job.get('url','#')}' style='color:#0073b1;font-weight:bold;text-decoration:none'>"
                f"{job.get('title','N/A')}</a></td>"
                f"<td style='padding:10px;border-bottom:1px solid #eee'>{job.get('company','N/A')}</td>"
                f"<td style='padding:10px;border-bottom:1px solid #eee'>{job.get('platform','N/A')}</td>"
                f"<td style='padding:10px;border-bottom:1px solid #eee'>{job.get('location','N/A')}</td>"
                f"<td style='padding:10px;border-bottom:1px solid #eee;text-align:center'>"
                f"<strong>{job.get('skill_match_score',0):.0f}%</strong></td>"
                f"<td style='padding:10px;border-bottom:1px solid #eee'>{skill_tags}</td></tr>"
            )

        job_table = (
            "<h2 style='color:#333;border-bottom:2px solid #0073b1;padding-bottom:8px'>Applied Jobs</h2>"
            "<table style='width:100%;border-collapse:collapse'>"
            "<thead><tr style='background:#f5f5f5;font-size:13px'>"
            "<th style='padding:10px;text-align:left'>Title</th>"
            "<th style='padding:10px;text-align:left'>Company</th>"
            "<th style='padding:10px;text-align:left'>Platform</th>"
            "<th style='padding:10px;text-align:left'>Location</th>"
            "<th style='padding:10px;text-align:center'>Match %</th>"
            "<th style='padding:10px;text-align:left'>Matched Skills</th>"
            f"</tr></thead><tbody>{rows}</tbody></table>"
            if total
            else "<p style='color:#777;text-align:center;font-style:italic'>No new jobs applied today.</p>"
        )

        error_section = ""
        if errors:
            items = "".join(f"<li style='color:#c0392b'>{e}</li>" for e in errors)
            error_section = (
                "<div style='margin-top:20px;padding:15px;background:#fdf2f2;"
                "border-left:4px solid #e74c3c;border-radius:4px'>"
                "<h3 style='color:#c0392b;margin:0 0 8px'>Errors</h3>"
                f"<ul style='margin:0;padding-left:18px'>{items}</ul></div>"
            )

        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;max-width:960px;margin:0 auto;padding:20px;color:#333">
<div style="background:linear-gradient(135deg,#0073b1,#00a0dc);padding:28px;border-radius:10px;color:white;margin-bottom:24px">
<h1 style="margin:0;font-size:22px">DevOps Job Auto-Apply Report</h1>
<p style="margin:6px 0 0;opacity:.9;font-size:14px">{date_str}</p></div>
<div style="display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap">
<div style="flex:1;min-width:120px;padding:18px;background:#e8f8f0;border-radius:8px;text-align:center">
<div style="font-size:34px;font-weight:bold;color:#27ae60">{total}</div>
<div style="color:#555;font-size:13px">Total Applied</div></div>
<div style="flex:1;min-width:120px;padding:18px;background:#e8f4f8;border-radius:8px;text-align:center">
<div style="font-size:34px;font-weight:bold;color:#0073b1">{linkedin_cnt}</div>
<div style="color:#555;font-size:13px">LinkedIn</div></div>
<div style="flex:1;min-width:120px;padding:18px;background:#fef9e7;border-radius:8px;text-align:center">
<div style="font-size:34px;font-weight:bold;color:#f39c12">{naukri_cnt}</div>
<div style="color:#555;font-size:13px">Naukri</div></div></div>
{job_table}{error_section}
<div style="margin-top:20px;padding:14px;background:#f8f9fa;border-radius:8px;font-size:12px;color:#777">
<strong>Criteria:</strong> DevOps | Hyderabad, Telangana | 5+ Years | AWS, Kubernetes, Docker, Terraform, EKS, GitHub Actions
</div></body></html>"""
