import os


class Settings:
    """All configuration loaded from environment variables."""

    search_keywords = [
        "DevOps Engineer",
        "Site Reliability Engineer",
        "Cloud Engineer",
        "Platform Engineer",
        "DevSecOps Engineer",
    ]
    location = "Hyderabad"
    min_experience = 5

    # Include role-level keywords so title-only cards still match
    target_skills = [
        "AWS", "Kubernetes", "Docker", "Terraform", "Git", "GitHub Actions",
        "EKS", "CI/CD", "Jenkins", "Prometheus", "Grafana", "Datadog",
        "Ansible", "Helm", "ArgoCD", "Linux", "Bash", "Python",
        "CloudWatch", "EC2", "S3", "VPC", "IAM",
        "PagerDuty", "ELK", "Elasticsearch", "Nagios", "Zabbix",
        # Role keywords so title match guarantees a non-zero score
        "DevOps", "SRE", "Site Reliability", "Cloud", "Platform", "DevSecOps",
        "Infra", "Infrastructure",
    ]

    # 10% = need just 1 keyword match — role name in title alone is sufficient
    min_skill_match = 10

    # Max applications per platform per run
    max_applications_per_run = 15

    def __init__(self):
        self.linkedin_email = os.environ.get("LINKEDIN_EMAIL", "")
        self.linkedin_password = os.environ.get("LINKEDIN_PASSWORD", "")

        self.naukri_email = os.environ.get("NAUKRI_EMAIL", "")
        self.naukri_password = os.environ.get("NAUKRI_PASSWORD", "")

        # Preferred SMTP secrets (works with Brevo/Outlook/custom providers)
        # Backward-compatible fallback to legacy Gmail secret names.
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "465"))
        self.smtp_use_ssl = os.environ.get("SMTP_USE_SSL", "true").lower() in ("1", "true", "yes")
        self.smtp_user = os.environ.get("SMTP_USER", os.environ.get("GMAIL_USER", ""))
        self.smtp_password = os.environ.get("SMTP_PASSWORD", os.environ.get("GMAIL_APP_PASSWORD", ""))
        self.smtp_from = os.environ.get("SMTP_FROM", self.smtp_user)
        self.alert_email = os.environ.get("ALERT_EMAIL", "")

        self.twilio_account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        self.twilio_whatsapp_from = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        self.whatsapp_to = os.environ.get("WHATSAPP_TO", "")

        self.db_path = "data/applied_jobs.db"
        self.headless = True